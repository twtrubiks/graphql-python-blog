"""彙整變異測試結果（由 runner.py report 呼叫，也可直接執行）"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

CACHE = Path(__file__).resolve().parent / ".cache"


def load():
    ms = {}
    for l in (CACHE / "mutants.jsonl").read_text().splitlines():
        m = json.loads(l)
        ms[m["id"]] = m
    rs = {}
    for l in (CACHE / "results.jsonl").read_text().splitlines():
        r = json.loads(l)
        rs[r["id"]] = r  # 後寫入（重跑）的結果覆蓋先前的
    return ms, rs


def bucket(r):
    s = r["status"]
    if s in ("killed", "timeout"):
        return "killed"
    if s == "error_infra":
        return "infra"
    if s.startswith("error"):
        return "error"
    return s


def score(ids, rs):
    """回傳 (計數, 覆蓋範圍內分數, 含未覆蓋的整體分數)

    error（變異造成 import/收集失敗）視同被殺；infra（測試根本沒跑起來）不列入計分。
    """
    c = Counter(bucket(rs[i]) for i in ids)
    killed = c["killed"] + c["error"]
    covered = killed + c["survived"]
    total = covered + c["no_coverage"]
    return c, (killed / covered if covered else 0.0), (killed / total if total else 0.0)


def _row(name, ids, rs, width):
    c, s1, s2 = score(ids, rs)
    return (f"{name:{width}} n={len(ids):4} killed={c['killed'] + c['error']:4} survived={c['survived']:4} "
            f"nocov={c['no_coverage']:4}  score={s1:4.0%}  overall={s2:4.0%}")


def summary(ms, rs):
    ids = [i for i in ms if i in rs]
    c, s1, s2 = score(ids, rs)
    print(f"results {len(rs)}/{len(ms)}  {dict(c)}")
    print(f"mutation score（僅計有測試涵蓋者）= {s1:.1%}   overall（含未涵蓋）= {s2:.1%}")
    for title, key, width in (("operator", "op", 18), ("file", "file", 48)):
        print(f"\n== by {title} ==")
        groups = defaultdict(list)
        for i in ids:
            groups[ms[i][key]].append(i)
        for name, g in sorted(groups.items(), key=lambda kv: (score(kv[1], rs)[1], -len(kv[1]))):
            print(_row(name, g, rs, width))


def listing(ms, rs, mode, filt=""):
    ids = [i for i in ms if i in rs and bucket(rs[i]) == mode and filt in ms[i]["file"]]
    for i in sorted(ids, key=lambda i: (ms[i]["file"], ms[i]["line"])):
        m, r = ms[i], rs[i]
        o = " ".join(m["original"].split())
        print(f"{i} {m['file']}:{m['line']} [{m['op']}] {o[:70]!r} -> {m['replacement'][:50]!r} "
              f"({r.get('selection')},{r['n_tests']}t)")
        if mode == "error":
            print("   ", r["tail"][-300:].replace("\n", " | "))


def diff(ms, rs, before_path):
    """與先前的結果比較，列出狀態改變的變異體（例如補測試後由存活轉為被殺）"""
    before = {}
    for l in Path(before_path).read_text().splitlines():
        r = json.loads(l)
        before[r["id"]] = r
    _, s_before, _ = score([i for i in ms if i in before], before)
    _, s_after, _ = score([i for i in ms if i in rs], rs)
    print(f"mutation score: {s_before:.1%} -> {s_after:.1%}")
    changes = defaultdict(list)
    for i, m in ms.items():
        if i in before and i in rs and bucket(before[i]) != bucket(rs[i]):
            changes[(bucket(before[i]), bucket(rs[i]))].append(i)
    for (old, new), ids in sorted(changes.items()):
        print(f"\n== {old} -> {new}: {len(ids)} ==")
        for i in sorted(ids, key=lambda i: (ms[i]["file"], ms[i]["line"])):
            m = ms[i]
            o = " ".join(m["original"].split())
            print(f"{i} {m['file']}:{m['line']} [{m['op']}] {o[:60]!r} -> {m['replacement'][:40]!r}"
                  f"  killer={rs[i].get('killer')}")


def main(argv):
    ms, rs = load()
    if not argv:
        summary(ms, rs)
    elif argv[0] == "diff":
        diff(ms, rs, argv[1])
    else:
        listing(ms, rs, argv[0], argv[1] if len(argv) > 1 else "")


if __name__ == "__main__":
    main(sys.argv[1:])
