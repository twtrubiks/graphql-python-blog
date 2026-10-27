"""
變異測試執行器（Mutation Testing Runner）

在 backend/ 目錄下執行（需先啟動 PostgreSQL，並安裝 requirements-test.txt）：

  python mutation/runner.py all              # 一次跑完 gen -> setup -> coverage -> run -> report
  python mutation/runner.py gen              # 產生變異體 -> .cache/mutants.jsonl
  python mutation/runner.py setup [-j N]     # 建立 N 個 worker 工作目錄
  python mutation/runner.py coverage         # 以 coverage context 跑全套測試，建立「行號 -> 測試」對照表
  python mutation/runner.py run [-j N]       # 執行變異測試（可中斷後續跑）
  python mutation/runner.py report [survived|no_coverage|error] [檔案關鍵字]
  python mutation/runner.py report diff <舊的 results.jsonl>   # 與先前結果比較
  python mutation/runner.py verify <ID>      # 單獨重跑某個變異體並印出 pytest 輸出

設計重點：
- 每個 worker 有自己的 backend 副本與測試資料庫（TEST_DB_NAME=test_blog_w{i}），可安全平行執行
- PYTHONDONTWRITEBYTECODE=1 且副本不含 __pycache__：.pyc 以 mtime+size 判斷是否過期，
  同一秒內寫入、長度相同的變異（例如 == -> !=）可能沿用舊的位元組碼而造成假性存活
- coverage 需設定 concurrency = greenlet：SQLAlchemy async 以 greenlet 切換執行，
  預設的 thread 追蹤會漏掉第一個 await 之後的所有行
- 每個變異體只執行涵蓋該行的測試（依耗時由短到長排序，搭配 -x 一失敗就停）
- import 時期執行的變異（類別層級常數、permission_classes 等）沒有 per-test coverage，改跑全套
- 測試以 plugins/mut_speedup.py 將 bcrypt cost 降為 4（僅加速，不影響語意）
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
PLUGINS = HERE / "plugins"
CACHE = HERE / ".cache"
WORK = CACHE / "work"
MUTANTS = CACHE / "mutants.jsonl"
RESULTS = CACHE / "results.jsonl"
TESTMAP = CACHE / "testmap.json"
DURATIONS = CACHE / "durations.json"
COVFILE = CACHE / ".coverage.ctx"
PY = sys.executable

sys.path.insert(0, str(HERE))
from mutgen import apply, collect_all  # noqa: E402

BASE_PYTEST = [
    PY, "-m", "pytest",
    "-o", "addopts=",
    "-p", "no:cacheprovider",
    "-p", "mut_speedup",
    "-q", "-x", "-rfE", "--no-header", "-W", "ignore",
]


def worker_dir(i: int) -> Path:
    return WORK / f"w{i}" / "backend"


def worker_env(i: int) -> dict:
    env = os.environ.copy()
    env["TEST_DB_NAME"] = f"test_blog_w{i}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(PLUGINS)
    return env


def cmd_gen():
    CACHE.mkdir(exist_ok=True)
    ms = collect_all(BACKEND)
    MUTANTS.write_text("\n".join(json.dumps(asdict(m), ensure_ascii=False) for m in ms))
    print(f"{len(ms)} mutants -> {MUTANTS}")


def cmd_setup(n: int):
    for i in range(n):
        d = worker_dir(i)
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        for name in ("app", "tests", "alembic"):  # alembic：test_migrations.py 會跑 migration
            shutil.copytree(BACKEND / name, d / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("pytest.ini", ".env"):
            shutil.copy2(BACKEND / name, d / name)
    print(f"{n} workers ready under {WORK}")


def cmd_coverage():
    d = worker_dir(0)
    env = worker_env(0)
    env["COVERAGE_FILE"] = str(COVFILE)
    env["MUT_DURATIONS_FILE"] = str(DURATIONS)
    cmd = [PY, "-m", "pytest", "-o", "addopts=", "-p", "no:cacheprovider", "-p", "mut_speedup",
           "-p", "mut_durations", "-q", "--no-header", "-W", "ignore",
           "--cov=app", "--cov-context=test", "--cov-report=", f"--cov-config={HERE / 'coveragerc'}", "tests"]
    t = time.time()
    r = subprocess.run(cmd, cwd=d, env=env)
    print("coverage run rc=", r.returncode, f"{time.time() - t:.0f}s")
    if r.returncode != 0:
        sys.exit("基準測試未全數通過，無法進行變異測試")

    import coverage
    data = coverage.CoverageData(basename=str(COVFILE))
    data.read()
    testmap: dict[str, dict[str, list[str]]] = {}
    for f in data.measured_files():
        rel = Path(f).resolve().relative_to(d.resolve()).as_posix()
        # context 形如 "tests/x.py::TestA::test_b|run"；空字串代表 import 時期
        testmap[rel] = {
            str(ln): sorted({c.rsplit("|", 1)[0] for c in ctxs if c})
            for ln, ctxs in data.contexts_by_lineno(f).items()
        }
    TESTMAP.write_text(json.dumps(testmap))
    print("testmap files:", len(testmap))


def load_mutants() -> list[dict]:
    return [json.loads(l) for l in MUTANTS.read_text().splitlines() if l.strip()]


def select_tests(m: dict, testmap: dict, durations: dict) -> tuple[str, list[str]]:
    """回傳 (挑選方式, 測試清單)"""
    fm = testmap.get(m["file"], {})
    if m.get("func_body_line"):
        # 函式預設值：選擇涵蓋該函式本體第一行的測試
        tests = set(fm.get(str(m["func_body_line"]), []))
        return ("func_default", sorted(tests, key=lambda t: durations.get(t, 1.0))) if tests else ("no_coverage", [])

    tests: set[str] = set()
    executed = False
    for ln in m["stmt_lines"]:
        if str(ln) in fm:
            executed = True
            tests.update(fm[str(ln)])
    if tests and not m["import_time"]:
        return "covered", sorted(tests, key=lambda t: durations.get(t, 1.0))
    if m["import_time"] and executed:
        # 模組/類別層級：影響範圍無法以 coverage 推斷，跑全套
        return "full_suite", sorted(durations, key=lambda t: durations[t])
    if tests:
        return "covered", sorted(tests, key=lambda t: durations.get(t, 1.0))
    return "no_coverage", []


def _run_pytest(d: Path, i: int, argsfile: Path, timeout: float) -> tuple[str | None, int | None, str]:
    """執行一次 pytest，回傳 (timeout 時為 "timeout" 否則 None, returncode, 輸出)"""
    p = subprocess.Popen(BASE_PYTEST + [f"@{argsfile}"], cwd=d, env=worker_env(i),
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        out = p.communicate(timeout=timeout)[0]
        return None, p.returncode, out.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        return "timeout", None, p.communicate()[0].decode("utf-8", "replace")


def _is_infra_failure(rc: int | None, out: str) -> bool:
    """測試根本沒有執行（例如 conftest 建立測試資料庫失敗後 pytest.exit(returncode=1)）。

    這種 rc=1 與「測試失敗」無法以 returncode 區分；已知成因是 setup_test_database 的
    pg_terminate_backend 碰到 autovacuum worker（superuser）而 permission denied。
    """
    return rc == 1 and "no tests ran" in out


def run_mutant(m: dict, i: int, tests: list[str], durations: dict, attempts: int = 3) -> dict:
    d = worker_dir(i)
    target = d / m["file"]
    orig = (BACKEND / m["file"]).read_bytes()
    target.write_bytes(apply(orig, m))
    expected = sum(durations.get(t, 1.0) for t in tests)
    timeout = max(60.0, expected * 3 + 30)
    argsfile = d / f".mut_args_{i}.txt"
    argsfile.write_text("\n".join(tests))
    t0 = time.time()
    try:
        for attempt in range(attempts):
            status, rc, out = _run_pytest(d, i, argsfile, timeout)
            if not _is_infra_failure(rc, out):
                break
            time.sleep(2 * (attempt + 1))
    finally:
        target.write_bytes(orig)
    if status is None:
        if _is_infra_failure(rc, out):
            status = "error_infra"
        else:
            status = {0: "survived", 1: "killed"}.get(rc, f"error_rc{rc}")
    # FAILED（測試本體失敗）或 ERROR（fixture setup/teardown 失敗）
    failed = [l.split(" ", 1)[1].split(" - ")[0] for l in out.splitlines()
              if l.startswith(("FAILED ", "ERROR tests/"))]
    return {
        "id": m["id"], "status": status, "rc": rc, "secs": round(time.time() - t0, 1),
        "n_tests": len(tests), "killer": failed[0] if failed else None,
        "tail": "" if status == "survived" else out[-1500:],
    }


def cmd_run(n: int, only: list[str] | None):
    mutants = load_mutants()
    testmap = json.loads(TESTMAP.read_text())
    durations = json.loads(DURATIONS.read_text())
    done = set()
    if RESULTS.exists():
        done = {json.loads(l)["id"] for l in RESULTS.read_text().splitlines() if l.strip()}
    todo = []
    for m in mutants:
        if only and m["id"] not in only:
            continue
        if m["id"] in done and not only:
            continue
        kind, tests = select_tests(m, testmap, durations)
        todo.append((m, kind, tests))

    # 沒有任何測試涵蓋的變異體直接記錄，不需執行
    with RESULTS.open("a") as fh:
        for m, kind, _ in todo:
            if kind == "no_coverage":
                fh.write(json.dumps({"id": m["id"], "status": "no_coverage", "rc": None, "secs": 0,
                                     "n_tests": 0, "killer": None, "tail": "", "selection": kind}) + "\n")
    todo = [t for t in todo if t[1] != "no_coverage"]
    # 跑全套的放最後
    todo.sort(key=lambda t: (t[1] == "full_suite", sum(durations.get(x, 1.0) for x in t[2])))
    total = len(todo)
    print(f"to run: {total}  (full_suite: {sum(1 for t in todo if t[1] == 'full_suite')})", flush=True)

    free = list(range(n))
    lock = threading.Lock()
    counter = {"n": 0, "killed": 0, "survived": 0, "other": 0}
    t_start = time.time()

    def job(item):
        m, kind, tests = item
        with lock:
            wi = free.pop()
        try:
            res = run_mutant(m, wi, tests, durations)
        finally:
            with lock:
                free.append(wi)
        res["selection"] = kind
        with lock:
            with RESULTS.open("a") as fh:
                fh.write(json.dumps(res, ensure_ascii=False) + "\n")
            counter["n"] += 1
            counter[res["status"] if res["status"] in ("killed", "survived") else "other"] += 1
            if counter["n"] % 25 == 0 or counter["n"] == total:
                el = time.time() - t_start
                eta = el / counter["n"] * (total - counter["n"])
                print(f"[{counter['n']}/{total}] killed={counter['killed']} survived={counter['survived']} "
                      f"other={counter['other']} elapsed={el / 60:.1f}m eta={eta / 60:.1f}m", flush=True)

    with ThreadPoolExecutor(max_workers=n) as ex:
        list(ex.map(job, todo))
    print("done", flush=True)


def cmd_verify(mid: str):
    m = {m["id"]: m for m in load_mutants()}[mid]
    testmap = json.loads(TESTMAP.read_text())
    durations = json.loads(DURATIONS.read_text())
    kind, tests = select_tests(m, testmap, durations)
    print(json.dumps({k: m[k] for k in ("file", "line", "op", "original", "replacement")}, ensure_ascii=False))
    print("selection:", kind, len(tests))
    res = run_mutant(m, 0, tests, durations)
    print(res["status"], res["secs"], res["killer"])
    print(res["tail"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="graphql-python-blog 後端變異測試")
    ap.add_argument("cmd", choices=["all", "gen", "setup", "coverage", "run", "report", "verify"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("-j", type=int, default=os.cpu_count() or 4, help="平行 worker 數")
    ap.add_argument("--only", help="只跑指定 ID（逗號分隔）")
    a = ap.parse_args()
    if a.cmd in ("all", "gen"):
        cmd_gen()
    if a.cmd in ("all", "setup"):
        cmd_setup(a.j)
    if a.cmd in ("all", "coverage"):
        cmd_coverage()
    if a.cmd in ("all", "run"):
        if a.cmd == "all" and RESULTS.exists():
            RESULTS.unlink()
        cmd_run(a.j, a.only.split(",") if a.only else None)
    if a.cmd in ("all", "report"):
        import analyze
        analyze.main(a.args if a.cmd == "report" else [])
    if a.cmd == "verify":
        cmd_verify(a.args[0])
