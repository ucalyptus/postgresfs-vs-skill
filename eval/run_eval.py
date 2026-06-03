"""
Main evaluation runner: runs both agents on all questions N times,
reports median latency and accuracy per question and tier.

Usage:
  python -m eval.run_eval --dsn "postgresql://..." --runs 10
"""

import argparse
import json
import statistics
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

from agent import run_postgresfs_agent, run_skill_agent
from eval.questions import QUESTIONS

console = Console()


def run_all(dsn: str, runs: int, questions: list[dict], output_file: str | None = None):
    results = []

    for q in questions:
        console.print(f"\n[bold cyan]{q['id']}[/] ({q['tier']}): {q['question'][:70]}...")
        for arm, runner in [("postgresfs", run_postgresfs_agent), ("skill", run_skill_agent)]:
            latencies, tool_counts = [], []
            answers = []
            for i in range(runs):
                try:
                    out = runner(q["question"], dsn)
                    latencies.append(out["latency_s"])
                    tool_counts.append(out["tool_calls"])
                    answers.append(out["answer"])
                    console.print(f"  [{arm}] run {i+1}/{runs}: {out['latency_s']:.1f}s, {out['tool_calls']} calls")
                except Exception as e:
                    console.print(f"  [{arm}] run {i+1}/{runs}: ERROR — {e}")

            results.append({
                "question_id": q["id"],
                "tier": q["tier"],
                "arm": arm,
                "latency_median": statistics.median(latencies) if latencies else None,
                "tool_calls_median": statistics.median(tool_counts) if tool_counts else None,
                "answers": answers,
            })

    _print_summary(results)

    if output_file:
        Path(output_file).write_text(json.dumps(results, indent=2))
        console.print(f"\nResults saved to [green]{output_file}[/]")

    return results


def _print_summary(results: list[dict]):
    table = Table(title="Results Summary", show_header=True, header_style="bold magenta")
    table.add_column("Q", style="dim")
    table.add_column("Tier")
    table.add_column("Arm")
    table.add_column("Latency (s)", justify="right")
    table.add_column("Tool calls", justify="right")

    for r in results:
        table.add_row(
            r["question_id"],
            r["tier"],
            r["arm"],
            f"{r['latency_median']:.1f}" if r["latency_median"] else "—",
            f"{r['tool_calls_median']:.0f}" if r["tool_calls_median"] else "—",
        )

    console.print(table)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", required=True, help="Postgres DSN")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--output", default="eval_results.json")
    parser.add_argument("--questions", nargs="+", help="Filter to specific question IDs (e.g. q1 q2)")
    args = parser.parse_args()

    questions = QUESTIONS
    if args.questions:
        questions = [q for q in QUESTIONS if q["id"] in args.questions]

    run_all(args.dsn, args.runs, questions, args.output)


if __name__ == "__main__":
    main()
