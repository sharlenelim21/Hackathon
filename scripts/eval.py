"""Run services/catalog/eval.json through check_action with the real LLM and report a pass rate.
Run: .venv/Scripts/python -m scripts.eval [--limit N] [--sleep SECONDS]"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import services  # noqa: E402
from services.config import CATALOG_DIR  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=4.0, help="pause between checks (free-tier rate limits)")
    args = ap.parse_args()
    cases = json.loads((CATALOG_DIR / "eval.json").read_text(encoding="utf-8"))
    if args.limit:
        cases = cases[:args.limit]
    passed, times = 0, []
    for i, case in enumerate(cases):
        if i:
            time.sleep(args.sleep)
        t = time.perf_counter()
        try:
            r = services.check_action(case["action_text"])
        except services.ServiceError as e:
            print(f"#{case['id']:>2} ERROR {e.code}: {e.message}")
            continue
        dt = time.perf_counter() - t
        times.append(dt)
        found = {c["section_key"] for c in r["conditions"]}
        keys_ok = set(case["expected_keys"]) <= found and (
            not case.get("expected_any") or bool(found & set(case["expected_any"])))
        level_ok = r["status"] in case["accept_levels"]
        ok = keys_ok and level_ok
        passed += ok
        print(f"#{case['id']:>2} {'PASS' if ok else 'FAIL'} {dt:5.1f}s status={r['status']:7s} "
              f"expected={case['expected_keys']} found={sorted(found)} dropped={r['dropped_unverified']} "
              f"model={r.get('llm_model')}")
    n = len(cases)
    avg = sum(times) / len(times) if times else 0
    print(f"\nPassed {passed}/{n} ({100 * passed / max(n, 1):.0f}%), average {avg:.1f}s per check")


if __name__ == "__main__":
    main()
