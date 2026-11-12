"""
Report Generator for ITV E2E Test Suite.
Generates structured Markdown reports, Rich console outputs, and JSON summaries.
"""

from __future__ import annotations
import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AssertionResult:
    assertion_id: str
    requirement: str
    description: str
    passed: bool
    observed_value: Any
    expected_threshold: str
    error_message: str = ""
    affected_items: List[str] = field(default_factory=list)


@dataclass
class ProjectTestReport:
    project_id: str
    total_assertions: int = 0
    passed_assertions: int = 0
    failed_assertions: int = 0
    duration_ms: float = 0.0
    results: List[AssertionResult] = field(default_factory=list)

    @property
    def pass_rate_percent(self) -> float:
        if self.total_assertions == 0:
            return 0.0
        return (self.passed_assertions / float(self.total_assertions)) * 100.0


@dataclass
class SuiteSummaryReport:
    timestamp: str
    projects: Dict[str, ProjectTestReport] = field(default_factory=dict)
    total_assertions: int = 0
    total_passed: int = 0
    total_failed: int = 0
    overall_pass_rate: float = 0.0

    def add_project_report(self, report: ProjectTestReport):
        self.projects[report.project_id] = report
        self.total_assertions += report.total_assertions
        self.total_passed += report.passed_assertions
        self.total_failed += report.failed_assertions
        if self.total_assertions > 0:
            self.overall_pass_rate = (self.total_passed / float(self.total_assertions)) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_assertions": self.total_assertions,
            "total_passed": self.total_passed,
            "total_failed": self.total_failed,
            "overall_pass_rate_percent": round(self.overall_pass_rate, 2),
            "projects": {k: asdict(v) for k, v in self.projects.items()},
        }

    def to_markdown(self) -> str:
        lines = [
            f"# ITV E2E Test Execution Report — {self.timestamp}",
            "",
            "## Executive Summary",
            f"- **Overall Pass Rate**: {self.overall_pass_rate:.1f}% ({self.total_passed}/{self.total_assertions} passed, {self.total_failed} failed)",
            "",
            "| Project | Passed | Failed | Pass Rate | Status |",
            "|---|---|---|---|---|",
        ]
        for pid, prep in self.projects.items():
            status = "✅ PASS" if prep.failed_assertions == 0 else "❌ FAIL"
            lines.append(
                f"| **{pid}** | {prep.passed_assertions} | {prep.failed_assertions} | {prep.pass_rate_percent:.1f}% | {status} |"
            )
        lines.append("")

        for pid, prep in self.projects.items():
            lines.append(f"## Project {pid} Assertions Detail")
            lines.append("")
            lines.append("| ID | Req | Description | Result | Observed | Expected |")
            lines.append("|---|---|---|---|---|---|")
            for res in prep.results:
                badge = "PASS" if res.passed else "**FAIL**"
                obs = str(res.observed_value).replace("|", "\\|")
                exp = str(res.expected_threshold).replace("|", "\\|")
                lines.append(
                    f"| `{res.assertion_id}` | {res.requirement} | {res.description} | {badge} | {obs} | {exp} |"
                )
            lines.append("")

            # Failed items breakdown
            fails = [r for r in prep.results if not r.passed]
            if fails:
                lines.append(f"### {pid} Failure Diagnoses ({len(fails)} failures)")
                for f in fails:
                    lines.append(f"- **[{f.assertion_id}] {f.description}**:")
                    lines.append(f"  * Error: `{f.error_message}`")
                    if f.affected_items:
                        sample = ", ".join(f.affected_items[:8])
                        suffix = f"... ({len(f.affected_items)} total)" if len(f.affected_items) > 8 else ""
                        lines.append(f"  * Affected items: {sample}{suffix}")
                lines.append("")

        return "\n".join(lines)
