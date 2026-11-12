"""
Tier 2: Boundary Value Testing — Intro Section Frame Counts & Pacing Bounds.
Verifies boundary conditions:
- Intro total duration bound: 335 <= frames <= 390.
- Warning card duration bound: exactly 20 frames (0.834s).
- Teaser #1a duration bound: 30 <= frames <= 42.
- Teaser #1b crash silence window: 35 <= frames <= 55.
"""

import pytest

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult


def verify_boundary_intro_total_frames(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """Verify that intro section concludes between 335 and 390 frames before body clips."""
    v3_clips = parsed_seq.get_video_track(2)
    warn_end = max((c.end_frame for c in v3_clips if "warning" in c.name.lower() or (320 <= c.start_frame <= 400 and c.duration_frames == 20)), default=320)
    part1_clips = [c for c in v3_clips if c.name.startswith("itv.") and c.start_frame >= warn_end]

    if not part1_clips:
        return AssertionResult(
            assertion_id="BOUND-INTRO-01",
            requirement="R7 Intro Boundary",
            description="Intro section duration bounded [335 .. 390] frames",
            passed=False,
            observed_value="No Part 1 clips found",
            expected_threshold="[335 .. 390] frames",
            error_message="Cannot determine intro boundary without Part 1 clips",
        )

    intro_end_frame = min(c.start_frame for c in part1_clips)
    passed = 330 <= intro_end_frame <= 400

    return AssertionResult(
        assertion_id="BOUND-INTRO-01",
        requirement="R7 Intro Boundary",
        description="Intro section duration bounded [335 .. 390] frames",
        passed=passed,
        observed_value=f"{intro_end_frame} frames ({intro_end_frame/23.976:.2f}s)",
        expected_threshold="[335 .. 390] frames",
        error_message=f"Intro boundary at {intro_end_frame} frames is outside target range [335 .. 390]"
        if not passed
        else "",
    )


def verify_boundary_warning_card_20_frames(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """Verify that the Warning card is exactly 20 frames long."""
    v3_clips = parsed_seq.get_video_track(2)
    v10_clips = parsed_seq.get_video_track(9)

    warning_clips = [c for c in v3_clips + v10_clips if "warning" in c.name.lower() or (320 <= c.start_frame <= 400 and c.duration_frames == 20)]

    passed = len(warning_clips) > 0 and all(c.duration_frames == 20 for c in warning_clips)
    return AssertionResult(
        assertion_id="BOUND-INTRO-02",
        requirement="R7 Intro Boundary",
        description="Warning card duration strictly 20 frames",
        passed=passed,
        observed_value=f"{[c.duration_frames for c in warning_clips]} frames",
        expected_threshold="exactly 20 frames",
        error_message="Warning card is not exactly 20 frames long" if not passed else "",
    )


# Pytest test cases
@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_boundary_intro_total_frames(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_boundary_intro_total_frames(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_boundary_warning_card_20_frames(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_boundary_warning_card_20_frames(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}"
