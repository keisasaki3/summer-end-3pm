"""計算トピックの具体的な問題を生成して data/questions/数学.json に書き込む。

使い方: python3 scripts/math_problems/build.py [--check]
  --check を付けると書き込まずに検証だけする。

各 gen_*.py は GENERATORS = {topic_id: fn(rng) -> list[dict]} を持つ。
問題 dict の形:
  数字入力: {"format":"数字入力","prompt":str,"answer":str,"accept":[str,...](任意),"explain":str}
  4択:     {"format":"4択","prompt":str,"options":[4つの文字列],"answer":正解のindex,"explain":str}
"""
import importlib
import json
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "questions" / "数学.json"
MODULES = ["gen_number", "gen_quantity_stats", "gen_algebra", "gen_functions_trig", "gen_advanced"]
PER_TOPIC_MIN = 12
NUMERIC = re.compile(r"^-?\d+(\.\d+)?(/\d+)?$")


def validate(tid, qs):
    errs = []
    if len(qs) < PER_TOPIC_MIN:
        errs.append(f"{tid}: {len(qs)}問しかない（{PER_TOPIC_MIN}問以上必要）")
    prompts = set()
    for i, q in enumerate(qs):
        where = f"{tid}#{i}"
        if q.get("prompt") in prompts:
            errs.append(f"{where}: 問題文が重複 {q.get('prompt')}")
        prompts.add(q.get("prompt"))
        if not q.get("prompt") or not q.get("explain"):
            errs.append(f"{where}: prompt/explain が空")
        fmt = q.get("format")
        if fmt == "数字入力":
            ans = q.get("answer")
            if not isinstance(ans, str) or not NUMERIC.match(ans):
                errs.append(f"{where}: 数字入力の答えが数値文字列でない {ans!r}")
            for a in q.get("accept", []):
                if not isinstance(a, str) or not NUMERIC.match(a):
                    errs.append(f"{where}: accept が数値文字列でない {a!r}")
        elif fmt == "4択":
            opts = q.get("options")
            if not isinstance(opts, list) or len(opts) != 4 or len(set(opts)) != 4:
                errs.append(f"{where}: 4択の選択肢が4つの異なる文字列でない {opts!r}")
            if not isinstance(q.get("answer"), int) or not 0 <= q["answer"] < 4:
                errs.append(f"{where}: 4択の answer が 0〜3 でない")
        else:
            errs.append(f"{where}: 未知の format {fmt!r}")
    return errs


def main():
    check_only = "--check" in sys.argv
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    gens = {}
    for name in MODULES:
        try:
            mod = importlib.import_module(name)
        except ModuleNotFoundError:
            print(f"skip {name}（まだ無い）")
            continue
        for tid, fn in mod.GENERATORS.items():
            if tid in gens:
                sys.exit(f"{tid} が複数のモジュールにある")
            gens[tid] = fn

    data = json.loads(DATA.read_text(encoding="utf-8"))
    calc_ids = {t["topic_id"] for t in data["topics"] if t["type"] == "calc"}
    unknown = set(gens) - calc_ids
    if unknown:
        sys.exit(f"数学.json の calc に無い topic_id: {sorted(unknown)}")

    errors = []
    for t in data["topics"]:
        fn = gens.get(t["topic_id"])
        if not fn:
            continue
        qs = fn(random.Random(t["topic_id"]))
        errors += validate(t["topic_id"], qs)
        t["questions"] = [{"id": i + 1, **q} for i, q in enumerate(qs)]

    missing = sorted(calc_ids - set(gens))
    print(f"生成 {len(gens)}/{len(calc_ids)} トピック, 未対応 {len(missing)}")
    for e in errors:
        print("NG", e)
    if errors:
        sys.exit(1)
    if not check_only:
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("書き込み完了", DATA)


if __name__ == "__main__":
    main()
