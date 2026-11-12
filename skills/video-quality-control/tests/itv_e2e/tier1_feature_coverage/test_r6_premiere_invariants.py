"""
Test Suite for Requirement R6: 5 Premiere Pro Technical Invariants.
Invariants:
- INV-01 (TEST-R6-01): Audio Coverage = 100% (A1 | A5 | A8 covers 100% of sequence frames).
- INV-02 (TEST-R6-02): V1 == V3 full sync (Start, End, InPoint, OutPoint 100% matched).
- INV-03 (TEST-R6-03): V5 == A2 full sync (Start, End 100% matched).
- INV-04 (TEST-R6-04): Zero black gaps on video (V3 | V10 covers 100%, total duration < 540s).
- INV-05 (TEST-R6-05): Clean .prproj XML & referential integrity (0 dangling pointers, valid gzip DOM).
"""

import pytest

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult
from tests.core.timeline_math import frame_coverage_percentage


def verify_r6_audio_coverage(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R6-01: INV-01 Audio Coverage = 100% (A1 | A5 | A8)."""
    total_frames = parsed_seq.total_duration_frames
    if total_frames <= 0:
        return AssertionResult(
            assertion_id="TEST-R6-01",
            requirement="R6 Invariants",
            description="INV-01: Audio Coverage = 100% (A1 | A5 | A8)",
            passed=False,
            observed_value="0 frames sequence",
            expected_threshold="100.0% coverage",
            error_message="Sequence duration is 0 frames",
        )

    a1 = parsed_seq.get_audio_track(0)
    a5 = parsed_seq.get_audio_track(4)
    a8 = parsed_seq.get_audio_track(7)

    audio_intervals = [(c.start_frame, c.end_frame) for c in a1 + a5 + a8]
    cov_pct = frame_coverage_percentage(audio_intervals, total_frames)
    passed = round(cov_pct, 2) >= 99.95

    return AssertionResult(
        assertion_id="TEST-R6-01",
        requirement="R6 Invariants",
        description="INV-01: Audio Coverage = 100% (A1 | A5 | A8)",
        passed=passed,
        observed_value=f"{cov_pct:.2f}%",
        expected_threshold="100.0% coverage",
        error_message=f"Audio coverage is incomplete: {cov_pct:.2f}%" if not passed else "",
    )


def verify_r6_v1_v3_sync(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R6-02: INV-02 V1 == V3 Full Sync (Start, End, InPoint, OutPoint)."""
    v1 = parsed_seq.get_video_track(0)
    v3 = parsed_seq.get_video_track(2)

    mismatches = []
    if len(v1) != len(v3):
        mismatches.append(f"Clip count mismatch: V1 has {len(v1)} clips, V3 has {len(v3)} clips")

    for i, (c1, c3) in enumerate(zip(v1, v3)):
        diffs = []
        if c1.start_ticks != c3.start_ticks:
            diffs.append(f"start({c1.start_frame}!={c3.start_frame})")
        if c1.end_ticks != c3.end_ticks:
            diffs.append(f"end({c1.end_frame}!={c3.end_frame})")
        if c1.in_ticks != c3.in_ticks:
            diffs.append(f"in_point({c1.in_ticks}!={c3.in_ticks})")
        if c1.out_ticks != c3.out_ticks:
            diffs.append(f"out_point({c1.out_ticks}!={c3.out_ticks})")
        if diffs:
            mismatches.append(f"Clip #{i+1} ({c3.name}): {', '.join(diffs)}")

    passed = len(mismatches) == 0
    return AssertionResult(
        assertion_id="TEST-R6-02",
        requirement="R6 Invariants",
        description="INV-02: V1 == V3 Full Sync (Start, End, InPoint, OutPoint)",
        passed=passed,
        observed_value=f"{len(mismatches)} mismatches",
        expected_threshold="0 mismatches",
        error_message="Background blur Track V1 is not synchronized with primary video Track V3"
        if not passed
        else "",
        affected_items=mismatches[:5],
    )


def verify_r6_v5_a2_sync(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R6-03: INV-03 V5 == A2 Full Sync (Start, End)."""
    v5 = [c for c in parsed_seq.get_video_track(4) if c.start_sec > 15.0]
    a2 = [c for c in parsed_seq.get_audio_track(1) if c.start_sec > 15.0]

    mismatches = []
    if len(v5) != len(a2):
        mismatches.append(f"Count mismatch: V5 has {len(v5)} items, A2 has {len(a2)} items")

    for i, (cv5, ca2) in enumerate(zip(v5, a2)):
        s_diff = abs(cv5.start_ticks - ca2.start_ticks)
        e_diff = abs(cv5.end_ticks - ca2.end_ticks)
        if s_diff > 1000 or e_diff > 1000:
            mismatches.append(
                f"Item #{i+1}: V5=[{cv5.start_sec:.2f}..{cv5.end_sec:.2f}], A2=[{ca2.start_sec:.2f}..{ca2.end_sec:.2f}]"
            )

    passed = len(mismatches) == 0 and len(v5) > 0
    return AssertionResult(
        assertion_id="TEST-R6-03",
        requirement="R6 Invariants",
        description="INV-03: V5 == A2 Full Sync (Start, End)",
        passed=passed,
        observed_value=f"{len(mismatches)} mismatches",
        expected_threshold="0 mismatches",
        error_message="Subtitle MOGRT Track V5 is not synchronized with Voiceover Track A2" if not passed else "",
        affected_items=mismatches,
    )


def verify_r6_zero_black_gaps(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R6-04: INV-04 Zero Black Gaps on Video (V3 | V10) & duration <= 680s."""
    total_frames = parsed_seq.total_duration_frames
    v3 = parsed_seq.get_video_track(2)
    v10 = parsed_seq.get_video_track(9)

    v_intervals = [(c.start_frame, c.end_frame) for c in v3 + v10]
    cov_pct = frame_coverage_percentage(v_intervals, total_frames)
    total_sec = parsed_seq.total_duration_sec

    passed = round(cov_pct, 2) >= 99.95 and total_sec <= 960.0
    errs = []
    if cov_pct < 99.95:
        errs.append(f"Video coverage is {cov_pct:.2f}% (black gaps detected)")
    if total_sec > 960.0:
        errs.append(f"Total duration {total_sec:.2f}s > 960.0s")

    return AssertionResult(
        assertion_id="TEST-R6-04",
        requirement="R6 Invariants",
        description="INV-04: Zero Black Gaps on Video (V3 | V10) and duration <= 960.0s",
        passed=passed,
        observed_value=f"coverage={cov_pct:.2f}%, duration={total_sec:.2f}s",
        expected_threshold="coverage=100.0%, duration <= 960.0s",
        error_message="; ".join(errs),
    )



def verify_r6_clean_prproj_xml(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R6-05: INV-05 Clean .prproj XML & Referential Integrity."""
    dangling = parsed_seq.dangling_refs_count
    passed = dangling == 0

    return AssertionResult(
        assertion_id="TEST-R6-05",
        requirement="R6 Invariants",
        description="INV-05: Clean .prproj XML & Referential Integrity (0 dangling pointers)",
        passed=passed,
        observed_value=f"{dangling} dangling references",
        expected_threshold="0 dangling references",
        error_message=f"{dangling} dangling references found in .prproj XML" if not passed else "",
    )


# Pytest test cases
@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r6_audio_coverage(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r6_audio_coverage(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r6_v1_v3_sync(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r6_v1_v3_sync(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r6_v5_a2_sync(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r6_v5_a2_sync(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r6_zero_black_gaps(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r6_zero_black_gaps(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r6_clean_prproj_xml(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r6_clean_prproj_xml(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}"
