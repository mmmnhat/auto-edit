"""Tier 4 Real-World Project End-to-End Audit: kb119."""

import pytest
from tests.core.project_auditor import audit_full_project


def test_full_audit_kb119():
    report = audit_full_project("kb119")
    failed = [r for r in report.results if not r.passed]
    assert report.failed_assertions == 0, (
        f"[kb119] {report.failed_assertions}/{report.total_assertions} assertions failed:\n"
        + "\n".join(f" - [{f.assertion_id}] {f.description}: {f.error_message}" for f in failed)
    )
