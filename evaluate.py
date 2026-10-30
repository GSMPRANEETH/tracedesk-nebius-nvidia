"""Real-model evaluation runner. Reference answers are never sent to the provider."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from tracedesk.core import Store, answer, load_runbook

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev", "heldout", "all"), default="dev")
    parser.add_argument("--memory", choices=("off", "on", "both"), default="both")
    parser.add_argument("--db", type=Path, default=ROOT / ".local" / "eval-memory.sqlite3")
    parser.add_argument("--out", type=Path, default=ROOT / ".local" / "evaluation.json")
    parser.add_argument("--limit", type=int, help="Limit questions for an initial connection check")
    args = parser.parse_args()
    if not os.environ.get("NEBIUS_API_KEY", "").strip():
        parser.exit(2, "Live evaluation blocked: NEBIUS_API_KEY is not set. No model results were generated.\n")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    cases = json.loads((ROOT / "data" / "eval_cases.json").read_text())
    cases = [c for c in cases if args.split == "all" or c["split"] == args.split][:args.limit]
    store = Store(args.db)
    sources = load_runbook()
    # Seed two source-only memories; no gold evaluation answer is used as a correction.
    for version in ("1.0", "2.0"):
        source = next(p for p in sources if p["version"] == version and p["id"].endswith("-auth"))
        store.save("RelayGate", version, "Authentication troubleshooting", source["text"], [source["id"]], True)
    modes = (False, True) if args.memory == "both" else (args.memory == "on",)
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "split": args.split,
        "source_sha256": hashlib.sha256((ROOT / "data" / "runbook.json").read_bytes()).hexdigest(),
        "model": os.environ.get("NEBIUS_MODEL", "nvidia/Nemotron-3_5-Lightning"),
        "method": "Same bounded runbook; memory-on adds two preapproved source excerpts. No weight updates.",
        "limitations": ["20 synthetic cases are not a reliability benchmark", "Keyword checks require human semantic review", "Provider errors count as failures, not abstentions"],
        "manual_review_required": True, "results": []}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    for case in cases:
        for memory in modes:
            try:
                result = answer(case["question"], "RelayGate", case["version"], store.list("RelayGate", case["version"]), memory)
                # Ponytail: keyword/citation heuristics flag regressions only; upgrade to independent human entailment scoring before accuracy claims.
                failures = []
                if result["status"] != case["status"]:
                    failures.append("unexpected status")
                if not set(case["citations"]) <= set(result["citations"]):
                    failures.append("expected evidence missing")
                text = result["answer"].casefold()
                failures.extend(f"missing phrase: {word}" for word in case["contains"] if word.casefold() not in text)
                failures.extend(f"forbidden phrase: {word}" for word in case["forbidden"] if word.casefold() in text)
                row = dict(case_id=case["id"], memory=memory, result=result, heuristic_pass=not failures, flags=failures, semantic_review="pending")
            except RuntimeError as error:
                row = dict(case_id=case["id"], memory=memory, provider_error=str(error), heuristic_pass=False, semantic_review="not-run")
            report["results"].append(row)
            report["heuristic_passes"] = sum(r["heuristic_pass"] for r in report["results"])
            report["attempts"] = len(report["results"])
            temporary = args.out.with_suffix(".tmp")
            temporary.write_text(json.dumps(report, indent=2) + "\n")
            temporary.replace(args.out)
            print(f"{case['id']} memory={memory}: {'heuristic pass; human review pending' if row['heuristic_pass'] else 'failed/flagged'}", flush=True)
            if "provider_error" in row:
                print("Stopping on provider failure to avoid spending more credits without a working runtime.", file=sys.stderr)
                return 1
    print(f"Report: {args.out}. Heuristic checks are not semantic accuracy scores.")
    return 0 if all(r["heuristic_pass"] for r in report["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
