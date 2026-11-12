"""
Tier 2: Boundary Value Testing — SFX Acoustic Timing & Overlap Boundaries.
Verifies boundary conditions:
- Track A2 Voiceover and Track A3/A4 SFX overlap boundary == 0.000s (tolerance < 1 frame = 0.0417s).
- Track A1 live camera and Track A5 BGM overlap boundary == 0.000s.
"""

import pytest

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult
from tests.core.timeline_math import intervals_overlap_seconds


def verify_boundary_sfx_vo_zero_overlap(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """Verify that overlap between Track A2 (VO) and Track A3/A4 (SFX) is strictly 0.0s."""
    a2_clips = parsed_seq.get_audio_track(1)
    a3_clips = parsed_seq.get_audio_track(2)
    a4_clips = parsed_seq.get_audio_track(3)

    a2_ints = [(c.start_frame, c.end_frame) for c in a2_clips]
    sfx_ints = [(c.start_frame, c.end_frame) for c in a3_clips + a4_clips]

    overlap_sec = intervals_overlap_seconds(a2_ints, sfx_ints)
    passed = overlap_sec < 0.0417  # strictly less than 1 frame at 23.976 fps

    return AssertionResult(
        assertion_id="BOUND-SFX-01",
        requirement="R3 SFX Boundary",
        description="A2 Voiceover and A3/A4 SFX overlap boundary strictly < 1 frame",
        passed=passed,
        observed_value=f"{overlap_sec:.4f}s overlap",
        expected_threshold="< 0.0417s (0 frames)",
        error_message=f"Overlap {overlap_sec:.4f}s exceeded zero-overlap boundary" if not passed else "",
    )


def verify_boundary_a1_a5_bgm_zero_overlap(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """Verify that overlap between Track A1 (camera) and Track A5 (silent BGM) is strictly 0.0s."""
    a1_clips = parsed_seq.get_audio_track(0)
    a5_clips = parsed_seq.get_audio_track(4)

    a1_ints = [(c.start_frame, c.end_frame) for c in a1_clips]
    a5_ints = [(c.start_frame, c.end_frame) for c in a5_clips]

    overlap_sec = intervals_overlap_seconds(a1_ints, a5_ints)
    passed = overlap_sec < 0.0417

    return AssertionResult(
        assertion_id="BOUND-SFX-02",
        requirement="R6 Audio Boundary",
        description="A1 camera audio and A5 BGM overlap strictly < 1 frame",
        passed=passed,
        observed_value=f"{overlap_sec:.4f}s overlap",
        expected_threshold="< 0.0417s (0 frames)",
        error_message=f"A1/A5 audio overlap {overlap_sec:.4f}s detected" if not passed else "",
    )


# Pytest test cases
@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_boundary_sfx_vo_zero_overlap(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_boundary_sfx_vo_zero_overlap(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_boundary_a1_a5_bgm_zero_overlap(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_boundary_a1_a5_bgm_zero_overlap(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}"
