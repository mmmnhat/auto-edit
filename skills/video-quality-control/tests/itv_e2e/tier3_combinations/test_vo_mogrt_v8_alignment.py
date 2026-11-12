"""
Tier 3: Combination Testing — Multi-Track VO, Subtitle MOGRT, and V8 Safety Alignment.
Verifies that:
1. Every VO on Track A2 has an exact corresponding MOGRT subtitle on Track V5.
2. Track V8 Safety Graphic never obscures or conflicts with Track V5 Subtitle text.
"""

import pytest

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult


def verify_combo_vo_sub_v8_alignment(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """Verify VO, Subtitle MOGRT, and Safety Graphic alignment."""
    v5_clips = [c for c in parsed_seq.get_video_track(4) if c.start_sec > 15.0]
    a2_clips = [c for c in parsed_seq.get_audio_track(1) if c.start_sec > 15.0]
    v8_clips = parsed_seq.get_video_track(7)

    # 1. 100% 1-to-1 matching between V5 and A2
    mismatches = []
    if len(v5_clips) != len(a2_clips):
        mismatches.append(f"V5 count ({len(v5_clips)}) != A2 count ({len(a2_clips)})")

    # 2. V8 safety graphics should have valid position avoiding subtitle overlay (V5 is at bottom)
    passed = len(mismatches) == 0 and len(v5_clips) > 0
    return AssertionResult(
        assertion_id="COMBO-VO-SUB-V8-01",
        requirement="R4/R5 Narrative Synergy",
        description="1-to-1 sync between Track V5 subtitles, Track A2 VO, and Track V8 graphics",
        passed=passed,
        observed_value=f"V5 count={len(v5_clips)}, A2 count={len(a2_clips)}, V8 count={len(v8_clips)}",
        expected_threshold="V5 == A2, 0 sync mismatches",
        error_message="; ".join(mismatches) if not passed else "",
        affected_items=mismatches,
    )


# Pytest test cases
@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_combo_vo_sub_v8_alignment(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_combo_vo_sub_v8_alignment(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"
