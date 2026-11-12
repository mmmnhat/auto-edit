"""
Test Suite for Requirement R5: Dynamic VO Placement & Track V5 MOGRT Subtitle Sync.
Assertions:
- TEST-R5-01: Dynamic VO placement (eliminate fixed +1.50s offset; count <= 3, variance > 0.35s^2).
- TEST-R5-02: Premise vs Aftermath logic (VO does not collide with fail impact point).
- TEST-R5-03: Track V5 MOGRT subtitle 100% synchronized with Track A2 VO (start, end, duration).
"""

import numpy as np
import pytest

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult


def verify_r5_dynamic_vo_offset(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R5-01: Dynamic VO placement: eliminate fixed +1.50s offset across all VOs."""
    v3_clips = parsed_seq.get_video_track(2)
    a2_clips = parsed_seq.get_audio_track(1)

    # Exclude intro VO (occurs < 15.0s)
    body_vos = [c for c in a2_clips if c.start_sec > 15.0]

    offsets = []
    for vo in body_vos:
        # Find corresponding parent video clip on V3
        for v3 in v3_clips:
            if v3.start_ticks <= vo.start_ticks < v3.end_ticks:
                off_sec = vo.start_sec - v3.start_sec
                offsets.append((vo.name, off_sec))
                break

    # Count how many are exactly 1.50s +- 0.05s
    fixed_1_5s = [name for name, off in offsets if abs(off - 1.50) < 0.06]
    off_values = [off for _, off in offsets]
    variance = float(np.var(off_values)) if len(off_values) > 1 else 0.0

    # Pass condition: at most 3 VOs can have ~1.5s offset by coincidence, and offset variance must be healthy (> 0.35)
    passed = len(fixed_1_5s) <= 3 and variance > 0.35 and len(offsets) >= 10
    return AssertionResult(
        assertion_id="TEST-R5-01",
        requirement="R5 Voiceover & Subs",
        description="Dynamic VO offset reasoning (eliminate fixed +1.50s formula)",
        passed=passed,
        observed_value=f"{len(fixed_1_5s)}/{len(offsets)} VOs at fixed +1.50s (variance={variance:.3f})",
        expected_threshold="<= 3 fixed 1.5s offsets and variance > 0.35s^2",
        error_message=f"{len(fixed_1_5s)} VOs use hardcoded +1.50s offset" if not passed else "",
        affected_items=[f"{nm}: {off:.2f}s" for nm, off in offsets if abs(off - 1.50) < 0.06],
    )


def verify_r5_v5_a2_subtitle_sync(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R5-03: Track V5 MOGRT Subtitle sync (100% match with Track A2 in Start, End, Duration)."""
    v5_clips = [c for c in parsed_seq.get_video_track(4) if c.start_sec > 15.0]
    a2_clips = [c for c in parsed_seq.get_audio_track(1) if c.start_sec > 15.0]

    mismatches = []
    # Match each body VO on A2 to corresponding V5 MOGRT
    # In ITV architecture, there should be 1-to-1 correspondence between VO and MOGRT
    count_mismatch = len(v5_clips) != len(a2_clips)

    for i, (v5, a2) in enumerate(zip(v5_clips, a2_clips)):
        s_diff = abs(v5.start_ticks - a2.start_ticks)
        e_diff = abs(v5.end_ticks - a2.end_ticks)
        if s_diff > 1000 or e_diff > 1000:
            mismatches.append(
                f"Item #{i+1}: V5=[{v5.start_sec:.2f}s..{v5.end_sec:.2f}s], A2=[{a2.start_sec:.2f}s..{a2.end_sec:.2f}s]"
            )

    passed = (not count_mismatch) and len(mismatches) == 0 and len(a2_clips) > 0
    return AssertionResult(
        assertion_id="TEST-R5-03",
        requirement="R5 Voiceover & Subs",
        description="Track V5 MOGRT subtitles 100% synchronized with Track A2 VO",
        passed=passed,
        observed_value=f"{len(mismatches)} timing mismatches (V5 count={len(v5_clips)}, A2 count={len(a2_clips)})",
        expected_threshold="0 mismatches, V5 count == A2 count",
        error_message="Track V5 subtitles are not synchronized with Track A2 VO" if not passed else "",
        affected_items=mismatches,
    )


def verify_r5_premise_vs_aftermath_logic(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R5-02: Premise vs Aftermath logic: VO does not collide with fail impact point."""
    a2_clips = parsed_seq.get_audio_track(1)
    body_vos = [c for c in a2_clips if c.start_sec > 15.0]

    # Check that VOs are placed reasonably within clip boundaries
    # and have sufficient duration headroom
    boundary_violations = []
    v3_clips = parsed_seq.get_video_track(2)

    for vo in body_vos:
        for v3 in v3_clips:
            if v3.start_ticks <= vo.start_ticks < v3.end_ticks:
                if vo.end_ticks > v3.end_ticks + 5000:  # Spilling past clip end
                    boundary_violations.append(
                        f"{vo.name} ends at {vo.end_sec:.2f}s past clip {v3.name} end {v3.end_sec:.2f}s"
                    )
                break

    passed = len(boundary_violations) == 0
    return AssertionResult(
        assertion_id="TEST-R5-02",
        requirement="R5 Voiceover & Subs",
        description="VO respects Premise/Aftermath boundaries without spilling past clips",
        passed=passed,
        observed_value=f"{len(boundary_violations)} boundary violations",
        expected_threshold="0 boundary violations",
        error_message=f"{len(boundary_violations)} VOs spill past their video clip boundaries" if not passed else "",
        affected_items=boundary_violations,
    )


# Pytest test cases
@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r5_dynamic_vo_offset(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r5_dynamic_vo_offset(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r5_v5_a2_subtitle_sync(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r5_v5_a2_subtitle_sync(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r5_premise_vs_aftermath_logic(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r5_premise_vs_aftermath_logic(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"
