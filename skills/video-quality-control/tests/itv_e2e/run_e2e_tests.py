"""
Master E2E Test Suite Runner for ITV Premiere Pro Pipeline.
Executes high-speed offline XML AST audits across all 4 tiers and formal assertions R1-R7.

Usage:
  python tests/run_e2e_tests.py --target kb118 kb119 kb120 kb121 --mode audit
  python tests/run_e2e_tests.py --target kb118 --mode strict
  python tests/run_e2e_tests.py --format markdown
"""

import argparse
import datetime
import json
import os
import sys
import time

# Ensure e:\ITV is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.core.project_auditor import audit_full_project
from tests.core.report_generator import SuiteSummaryReport

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    HAVE_RICH = True
except ImportError:
    HAVE_RICH = False


def run_e2e_suite(
    target_projects: list[str],
    mode: str = "audit",
    output_dir: str = "",
    report_format: str = "all",
) -> int:
    t_start = time.perf_counter()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if not output_dir:
        output_dir = os.path.join(SCRIPT_DIR, "reports")
    os.makedirs(output_dir, exist_ok=True)

    summary = SuiteSummaryReport(timestamp=now_str)
    print(f"\n================================================================================")
    print(f"  ITV E2E Automated Test Suite Runner (v2.0 — Fast AST Parser)")
    print(f"  Targets: {', '.join(target_projects)} | Mode: {mode.upper()} | Time: {now_str}")
    print(f"================================================================================\n")

    for pid in target_projects:
        print(f"[*] Auditing project {pid.upper()}...", end="", flush=True)
        t0 = time.perf_counter()
        prep = audit_full_project(pid, base_dir=os.path.join(PROJECT_ROOT, "Project"))
        t1 = time.perf_counter()
        dur_ms = (t1 - t0) * 1000.0
        prep.duration_ms = dur_ms
        summary.add_project_report(prep)

        status_str = "PASS" if prep.failed_assertions == 0 else "FAIL"
        print(f" [{status_str}] in {dur_ms:.1f}ms ({prep.passed_assertions}/{prep.total_assertions} passed)")

    t_end = time.perf_counter()
    total_elapsed = t_end - t_start

    # Render results table
    if HAVE_RICH:
        console = Console()
        table = Table(title="ITV E2E Test Suite Summary Matrix", show_header=True, header_style="bold cyan")
        table.add_column("Project", style="bold")
        table.add_column("Passed", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Total", justify="right")
        table.add_column("Pass Rate", justify="right")
        table.add_column("Status", justify="center")

        for pid, prep in summary.projects.items():
            st = "[bold green]PASS[/bold green]" if prep.failed_assertions == 0 else "[bold red]FAIL[/bold red]"
            table.add_row(
                pid,
                str(prep.passed_assertions),
                str(prep.failed_assertions),
                str(prep.total_assertions),
                f"{prep.pass_rate_percent:.1f}%",
                st,
            )
        console.print(table)
        console.print(
            Panel(
                f"[bold]Total Assertions[/bold]: {summary.total_assertions} | "
                f"[bold green]Passed[/bold green]: {summary.total_passed} | "
                f"[bold red]Failed[/bold red]: {summary.total_failed} | "
                f"[bold cyan]Overall Pass Rate[/bold cyan]: {summary.overall_pass_rate:.1f}%\n"
                f"[dim]Total Audit Execution Time: {total_elapsed:.2f}s (< 250ms/project parsing)[/dim]",
                title="Execution Gate",
            )
        )
    else:
        print("\n--------------------------------------------------------------------------------")
        print(f"{'Project':<10} | {'Passed':<8} | {'Failed':<8} | {'Pass Rate':<10} | Status")
        print("--------------------------------------------------------------------------------")
        for pid, prep in summary.projects.items():
            st = "PASS" if prep.failed_assertions == 0 else "FAIL"
            print(f"{pid:<10} | {prep.passed_assertions:<8} | {prep.failed_assertions:<8} | {prep.pass_rate_percent:<9.1f}% | {st}")
        print("--------------------------------------------------------------------------------")
        print(f"Overall: {summary.total_passed}/{summary.total_assertions} passed ({summary.overall_pass_rate:.1f}%). Time: {total_elapsed:.2f}s\n")

    # Save reports
    md_content = summary.to_markdown()
    json_data = summary.to_dict()

    md_path = os.path.join(output_dir, "baseline_report.md")
    json_path = os.path.join(output_dir, "baseline_metrics.json")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Generated reports in {output_dir}:")
    print(f"    - Markdown: {md_path}")
    print(f"    - JSON:     {json_path}")

    # Return exit code
    if mode == "strict" and summary.total_failed > 0:
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description="ITV Automated E2E Test Suite Runner")
    parser.add_argument(
        "--target",
        "--project",
        nargs="+",
        default=["kb118", "kb119", "kb120", "kb121"],
        help="Target project identifiers to test (e.g. kb118 kb119 kb120 kb121)",
    )
    parser.add_argument(
        "--mode",
        choices=["audit", "strict"],
        default="audit",
        help="Execution mode: 'audit' records baseline without non-zero exit; 'strict' enforces 100%% pass gate.",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Directory to save generated test reports",
    )
    parser.add_argument(
        "--format",
        choices=["rich", "markdown", "json", "all"],
        default="all",
        help="Report output format",
    )
    args = parser.parse_args()

    # Normalize targets
    targets = []
    for t in args.target:
        clean = t.lower().replace(".prproj", "").strip()
        if clean:
            targets.append(clean)

    exit_code = run_e2e_suite(
        target_projects=targets,
        mode=args.mode,
        output_dir=args.output_dir,
        report_format=args.format,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
