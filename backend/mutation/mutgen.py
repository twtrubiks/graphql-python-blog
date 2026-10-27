"""
AST-based 變異產生器（為 graphql-python-blog 後端客製）

與 mutmut 3 的差異：
- 會變異 @strawberry.field / mutation / subscription 等 decorator 包住的 resolver
- 加入 SQLAlchemy 語意相關的變異（and_/or_、is_/is_not、in_/not_in、desc/asc、ilike/like、| / &）
- 加入 GraphQL 權限移除變異（permission_classes=[...] -> []）

每個變異體 = 原始碼 bytes 上的一段 (start, end) 替換，其餘位元組不變。
注意：ast 的 col_offset 是 UTF-8 byte offset（原始碼含中文），因此全程以 bytes 操作。
"""
from __future__ import annotations

import ast
import copy
import hashlib
from dataclasses import dataclass, asdict, field
from pathlib import Path

CMP_SWAP = {
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
    ast.Lt: ast.LtE, ast.LtE: ast.Lt,
    ast.Gt: ast.GtE, ast.GtE: ast.Gt,
    ast.Is: ast.IsNot, ast.IsNot: ast.Is,
    ast.In: ast.NotIn, ast.NotIn: ast.In,
}
BIN_SWAP = {
    ast.Add: ast.Sub, ast.Sub: ast.Add,
    ast.Mult: ast.Div, ast.Div: ast.Mult,
    ast.FloorDiv: ast.Div, ast.Mod: ast.Div,
    ast.BitOr: ast.BitAnd, ast.BitAnd: ast.BitOr,
}
# 呼叫名稱替換（函式）
NAME_CALL_SWAP = {"and_": "or_", "or_": "and_", "min": "max", "max": "min", "desc": "asc", "asc": "desc"}
# 方法名稱替換（SQLAlchemy 運算子）
ATTR_CALL_SWAP = {
    "is_": "is_not", "is_not": "is_", "isnot": "is_",
    "in_": "not_in", "not_in": "in_",
    "desc": "asc", "asc": "desc",
    "ilike": "like",
}
# 這些 keyword 參數只影響效能/文件/連線池，變異必為等價變異，略過
SKIP_KWARGS = {"index", "description", "echo", "pool_size", "max_overflow", "pool_pre_ping", "future", "name"}
LOG_FUNCS = {"print"}
LOG_OBJS = {"logging", "logger"}


@dataclass
class Mutant:
    id: str
    file: str            # 相對 backend/ 的路徑
    line: int
    end_line: int
    col: int
    op: str              # 變異運算子類別
    original: str        # 原始片段
    replacement: str     # 替換片段
    start: int           # byte offset
    end: int
    stmt_lines: list = field(default_factory=list)  # 用於對應 coverage 的行號
    func_body_line: int | None = None  # 若為函式預設值，對應函式第一行（用於挑選測試）
    import_time: bool = False          # 是否位於模組/類別層級（import 時執行）
    in_function: bool = False


def _is_docstring(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str)


def _is_log_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    if isinstance(f, ast.Name) and f.id in LOG_FUNCS:
        return True
    if isinstance(f, ast.Attribute):
        v = f.value
        if isinstance(v, ast.Name) and v.id in LOG_OBJS:
            return True
    return False


class MutantCollector:
    def __init__(self, rel_path: str, source: bytes, *, mutate_strings_in_functions=True,
                 skip_class_body_constants=False):
        self.rel_path = rel_path
        self.src = source
        self.tree = ast.parse(source)
        self.line_starts = [0]
        for i, b in enumerate(source):
            if b == 0x0A:
                self.line_starts.append(i + 1)
        self.mutants: list[Mutant] = []
        self.mutate_strings_in_functions = mutate_strings_in_functions
        self.skip_class_body_constants = skip_class_body_constants
        # 父節點
        for parent in ast.walk(self.tree):
            for child in ast.iter_child_nodes(parent):
                child._parent = parent  # type: ignore[attr-defined]

    # ---------- 位置工具 ----------
    def _off(self, lineno: int, col: int) -> int:
        return self.line_starts[lineno - 1] + col

    def _span(self, node: ast.AST) -> tuple[int, int]:
        return self._off(node.lineno, node.col_offset), self._off(node.end_lineno, node.end_col_offset)

    # ---------- 上下文判斷 ----------
    def _ancestors(self, node):
        p = getattr(node, "_parent", None)
        while p is not None:
            yield p
            p = getattr(p, "_parent", None)

    def _enclosing_stmt(self, node) -> ast.stmt | None:
        if isinstance(node, ast.stmt):
            return node
        for a in self._ancestors(node):
            if isinstance(a, ast.stmt):
                return a
        return None

    def _in_annotation(self, node) -> bool:
        child = node
        for a in self._ancestors(node):
            if isinstance(a, ast.arg) and a.annotation is child:
                return True
            if isinstance(a, (ast.FunctionDef, ast.AsyncFunctionDef)) and a.returns is child:
                return True
            if isinstance(a, ast.AnnAssign) and a.annotation is child:
                return True
            child = a
        return False

    def _in_skipped_kwarg(self, node) -> bool:
        for a in self._ancestors(node):
            if isinstance(a, ast.keyword) and a.arg in SKIP_KWARGS:
                return True
            if _is_log_call(a):
                return True
        return False

    def _in_type_checking_block(self, node) -> bool:
        for a in self._ancestors(node):
            if isinstance(a, ast.If) and isinstance(a.test, ast.Name) and a.test.id == "TYPE_CHECKING":
                return True
        return False

    def _in_string_length_call(self, node) -> bool:
        p = getattr(node, "_parent", None)
        return isinstance(p, ast.Call) and isinstance(p.func, ast.Name) and p.func.id == "String"

    def _executes_at_runtime(self, node) -> bool:
        """節點是否在函式本體內（呼叫時執行），而非 import / def 時執行"""
        child = node
        for a in self._ancestors(node):
            if isinstance(a, ast.Lambda):
                return child is a.body
            if isinstance(a, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return child in a.body
            child = a
        return False

    def _function_default_owner(self, node):
        """若節點在函式預設值中，回傳該函式"""
        child = node
        for a in self._ancestors(node):
            if isinstance(a, ast.arguments):
                fn = getattr(a, "_parent", None)
                if child in a.defaults or child in [d for d in a.kw_defaults if d is not None]:
                    return fn
                return None
            if isinstance(a, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef, ast.Module)):
                return None
            child = a
        return None

    @staticmethod
    def _first_code_line(fn) -> int:
        """函式本體第一個非 docstring 敘述的行號（coverage 不記錄 docstring 行）"""
        body = [s for s in fn.body if not _is_docstring(s)]
        return (body or fn.body)[0].lineno

    def _stmt_lines(self, node) -> list[int]:
        """mutant 所在敘述的行號範圍（給 coverage 對應使用）"""
        stmt = self._enclosing_stmt(node)
        if stmt is None:
            return [node.lineno]
        start = stmt.lineno
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and stmt.decorator_list:
            start = min(d.lineno for d in stmt.decorator_list)
        body = getattr(stmt, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.stmt):
            end = max(start, body[0].lineno - 1)
        else:
            end = stmt.end_lineno
        return list(range(start, end + 1))

    # ---------- 產生 ----------
    def _add(self, node: ast.AST, op: str, replacement: str, *, span: tuple[int, int] | None = None):
        s, e = span or self._span(node)
        original = self.src[s:e].decode("utf-8")
        new_src = self.src[:s] + replacement.encode("utf-8") + self.src[e:]
        try:
            new_tree = ast.parse(new_src)
            compile(new_src, self.rel_path, "exec")
        except SyntaxError:
            return
        if ast.dump(new_tree) == ast.dump(self.tree):
            return
        fdo = self._function_default_owner(node)
        runtime = self._executes_at_runtime(node)
        mid_src = f"{self.rel_path}:{s}:{e}:{op}:{replacement}"
        m = Mutant(
            id=hashlib.sha1(mid_src.encode()).hexdigest()[:10],
            file=self.rel_path,
            line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            col=node.col_offset,
            op=op,
            original=original,
            replacement=replacement,
            start=s,
            end=e,
            stmt_lines=self._stmt_lines(node),
            func_body_line=(self._first_code_line(fdo) if fdo is not None and not isinstance(fdo, ast.Lambda) else None),
            import_time=not runtime,
            in_function=runtime,
        )
        self.mutants.append(m)

    def _expr_replace(self, node: ast.expr, new_node: ast.expr, op: str):
        self._add(node, op, "(" + ast.unparse(new_node) + ")")

    def _should_skip(self, node) -> bool:
        return (
            self._in_annotation(node)
            or self._in_skipped_kwarg(node)
            or self._in_type_checking_block(node)
        )

    def collect(self) -> list[Mutant]:
        docstrings = set()
        for n in ast.walk(self.tree):
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if n.body and _is_docstring(n.body[0]):
                    docstrings.add(id(n.body[0].value))

        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.expr) and self._should_skip(node):
                continue

            runtime = self._executes_at_runtime(node) if isinstance(node, (ast.expr, ast.stmt)) else False

            # 1) 比較運算子
            if isinstance(node, ast.Compare):
                for i, opn in enumerate(node.ops):
                    if type(opn) in CMP_SWAP:
                        nn = copy.deepcopy(node)
                        nn.ops[i] = CMP_SWAP[type(opn)]()
                        self._expr_replace(node, nn, "compare")

            # 2) 布林運算子
            elif isinstance(node, ast.BoolOp):
                nn = copy.deepcopy(node)
                nn.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
                self._expr_replace(node, nn, "boolop")

            # 3) not x -> x
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
                self._expr_replace(node, node.operand, "remove_not")

            # 4) 二元運算子
            elif isinstance(node, ast.BinOp) and type(node.op) in BIN_SWAP:
                # 字串格式化 "%" 不變異
                if isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                    pass
                else:
                    nn = copy.deepcopy(node)
                    nn.op = BIN_SWAP[type(node.op)]()
                    self._expr_replace(node, nn, "binop")

            # 5) 常數
            elif isinstance(node, ast.Constant):
                v = node.value
                parent = getattr(node, "_parent", None)
                if self.skip_class_body_constants and not runtime:
                    pass
                elif isinstance(v, bool):
                    self._add(node, "bool", "(" + repr(not v) + ")")
                elif isinstance(v, int) and not self._in_string_length_call(node):
                    self._add(node, "number", "(" + repr(v + 1) + ")")
                elif isinstance(v, str):
                    if id(node) in docstrings:
                        continue
                    if isinstance(parent, ast.JoinedStr) or isinstance(parent, ast.FormattedValue):
                        continue
                    if not (runtime and self.mutate_strings_in_functions):
                        continue
                    self._add(node, "string", "(" + repr("XX" + v + "XX") + ")")

            # 6) 呼叫名稱 / 方法名稱
            elif isinstance(node, ast.Call):
                f = node.func
                if isinstance(f, ast.Name) and f.id in NAME_CALL_SWAP:
                    self._add(f, "sql_name" if f.id in ("and_", "or_", "desc", "asc") else "name_swap", NAME_CALL_SWAP[f.id])
                elif isinstance(f, ast.Attribute) and f.attr in ATTR_CALL_SWAP:
                    nn = copy.deepcopy(f)
                    nn.attr = ATTR_CALL_SWAP[f.attr]
                    self._expr_replace(f, nn, "sql_method")
                # permission_classes=[...] -> []
                for kw in node.keywords:
                    if kw.arg == "permission_classes" and isinstance(kw.value, ast.List) and kw.value.elts:
                        self._add(kw.value, "remove_permission", "[]")

            # 7) 敘述刪除 / return None
            if isinstance(node, ast.stmt) and runtime:
                if isinstance(node, ast.Expr) and not _is_docstring(node):
                    inner = node.value.value if isinstance(node.value, ast.Await) else node.value
                    if isinstance(inner, ast.Call) and not _is_log_call(inner):
                        self._add(node, "delete_stmt", "pass")
                elif isinstance(node, ast.Assign) and all(isinstance(t, (ast.Attribute, ast.Subscript)) for t in node.targets):
                    self._add(node, "delete_stmt", "pass")
                elif isinstance(node, ast.AugAssign):
                    if type(node.op) in BIN_SWAP:
                        nn = copy.deepcopy(node)
                        nn.op = BIN_SWAP[type(node.op)]()
                        self._add(node, "binop", ast.unparse(nn))
                elif isinstance(node, (ast.Raise, ast.Delete)):
                    self._add(node, "delete_stmt", "pass")
                elif isinstance(node, ast.Return) and node.value is not None:
                    if not (isinstance(node.value, ast.Constant) and node.value.value is None):
                        self._add(node, "return_none", "return None")

        # 依位置排序、去重
        seen = set()
        uniq = []
        for m in sorted(self.mutants, key=lambda m: (m.start, m.end, m.op, m.replacement)):
            if m.id in seen:
                continue
            seen.add(m.id)
            uniq.append(m)
        return uniq


def apply(source: bytes, m: Mutant | dict) -> bytes:
    d = m if isinstance(m, dict) else asdict(m)
    return source[: d["start"]] + d["replacement"].encode("utf-8") + source[d["end"]:]


# 檔案層級設定
EXCLUDE_FILES = {"app/__init__.py"}
FILE_OPTS = {
    # Settings 的類別層級預設值皆被 .env 覆寫，變異必為等價，只變異 validator 函式
    "app/core/config.py": dict(skip_class_body_constants=True),
}


def collect_all(backend: Path) -> list[Mutant]:
    out = []
    for p in sorted((backend / "app").rglob("*.py")):
        rel = p.relative_to(backend).as_posix()
        if rel in EXCLUDE_FILES:
            continue
        src = p.read_bytes()
        if not src.strip():
            continue
        out.extend(MutantCollector(rel, src, **FILE_OPTS.get(rel, {})).collect())
    return out


if __name__ == "__main__":
    import json, sys
    from collections import Counter
    backend = Path(sys.argv[1])
    ms = collect_all(backend)
    print(len(ms), "mutants")
    print(Counter(m.op for m in ms).most_common())
    print(Counter(m.file for m in ms).most_common())
    print("import_time:", sum(m.import_time for m in ms), "func_default:", sum(m.func_body_line is not None for m in ms))
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text("\n".join(json.dumps(asdict(m), ensure_ascii=False) for m in ms))
