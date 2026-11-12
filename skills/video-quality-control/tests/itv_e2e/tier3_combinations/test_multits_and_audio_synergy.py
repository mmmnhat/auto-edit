"""
Tier 3: Combination Testing — Multi-Timestamp Splitting & Audio Track A1 Synergy.
When a source is split into multiple physical clips (e.g. 46_1.mp4, 46_2.mp4):
1. Both video clips must exist independently on Track V3.
2. Both corresponding audio clips must exist independently on Track A1.
3. Neither video nor audio may overlap with each other, and both must preserve full distinct time ranges.
"""

import pytest

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult


def verify_combo_multits_video_audio_synergy(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """Verify that multi-timestamp split creates paired independent video (V3) and audio (A1) track items."""
    v3_all = parsed_seq.get_video_track(2)
    intro_end_f = max((c.end_frame for c in v3_all if "warning" in c.name.lower()), default=330)
    v3_clips = [c for c in v3_all if c.start_frame >= intro_end_f]
    a1_clips = [c for c in parsed_seq.get_audio_track(0) if c.start_frame >= intro_end_f]

    v3_names = [c.name for c in v3_clips]
    a1_names = [c.name for c in a1_clips]

    unpaired_splits = []
    checked = 0

    for p2 in truth.part2_items:
        if p2.is_multi_ts:
            checked += 1
            slot = p2.slot_num
            v_splits = [n for n in v3_names if f"{slot}_" in n or f"{slot:02d}_" in n]
            a_splits = [n for n in a1_names if f"{slot}_" in n or f"{slot:02d}_" in n]

            if len(v_splits) < 2 or len(a_splits) < 2 or len(v_splits) != len(a_splits):
                unpaired_splits.append(
                    f"Slot {slot}: V3 splits={len(v_splits)}, A1 splits={len(a_splits)}"
                )

    passed = len(unpaired_splits) == 0
    return AssertionResult(
        assertion_id="COMBO-MULTITS-A1-01",
        requirement="R1 Multi-TS Synergy",
        description="Multi-TS discrete splitting produces paired V3 video and A1 audio track items",
        passed=passed,
        observed_value=f"{len(unpaired_splits)}/{checked} unpaired multi-ts sources",
        expected_threshold="0 unpaired sources",
        error_message=f"{len(unpaired_splits)} multi-ts sources lacked paired V3/A1 split items" if not passed else "",
        affected_items=unpaired_splits,
    )


# Pytest test cases
@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_combo_multits_video_audio_synergy(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_combo_multits_video_audio_synergy(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"
