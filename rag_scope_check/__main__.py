"""Command-line entry point for RAG scope checks."""

import argparse
import json
import sys

from .core import InputError, evaluate, load_cases


def format_text(report):
    count = report["case_count"]
    lines = [f'RAG scope check: {report["verdict"]} ({count} {"case" if count == 1 else "cases"})']
    for cohort in report["cohorts"]:
        recall = cohort["mean_authorized_recall"]
        recall_text = f"{recall:.2f}" if recall is not None else "unscored"
        lines.append(
            f'{cohort["tenant"]}/{cohort["cohort"]}: authorized recall={recall_text} ({cohort["scored_cases"]} scored), '
            f'underfill={cohort["underfill_rate"]:.2f}, leaking cases={cohort["leaking_cases"]}'
        )
    for case in report["cases"]:
        if case["underfilled_top_k"]:
            stage = "candidate generation" if case["candidate_underfill"] else "final ranking" if case["ranker_underfill"] else "unknown stage"
            lines.append(f'! {case["id"]}: top-k underfilled at {stage}')
        if case["unauthorized_candidate_ids"]:
            lines.append(f'! {case["id"]}: unauthorized candidates observed before final context')
        if case["authorized_recall"] is not None and case["authorized_recall"] < 1:
            lines.append(f'! {case["id"]}: authorized recall={case["authorized_recall"]:.2f}')
    lines += [f"- {failure}" for failure in report["failures"]]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gate RAG retrieval by permission cohort")
    parser.add_argument("cases", help="JSONL file of retrieval cases")
    parser.add_argument("--min-cohort-recall", type=float, help="minimum mean authorized recall per cohort (0-1)")
    parser.add_argument("--max-underfill-rate", type=float, help="maximum top-k underfill rate per cohort (0-1)")
    parser.add_argument("--max-policy-age-hours", type=float, help="maximum age of the independent policy snapshot")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    try:
        report = evaluate(
            load_cases(args.cases), args.min_cohort_recall,
            args.max_underfill_rate, args.max_policy_age_hours,
        )
    except (InputError, OSError, UnicodeError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2) if args.format == "json" else format_text(report))
    return 1 if report["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
