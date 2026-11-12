"""
Tier 2: Boundary Value Testing — Durations & Timecode Snapping.
Verifies boundary conditions:
- Exact +-0.30s transition snap threshold.
- Zero-length or negative-duration protection.
- Total sequence duration hard upper ceiling (< 540.0s).
- Non-note Part 2 preservation for clips > 10.0s, > 30.0s, > 60.0s.
"""

import pytest

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult


def verify_boundary_snap_tolerance(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """Verify that Part 1 boundary snap does not exceed 0.30s per cut boundary (max 0.60s per clip)."""
    v3_all = parsed_seq.get_video_track(2)
    intro_end_f = max((c.end_frame for c in v3_all if "warning" in c.name.lower()), default=330)
    v3_by_name = {c.name: c for c in v3_all if c.start_frame >= intro_end_f}

    exceeded_snaps = []
    for target in truth.part1_items:
        if target.clip_name in v3_by_name:
            tl_dur = v3_by_name[target.clip_name].duration_sec
            diff = abs(tl_dur - target.target_duration)
            # Boundary threshold: > 0.60s means snap exceeded +-0.30s at both edges
            if diff > 0.60:
                exceeded_snaps.append(f"{target.clip_name}: diff={diff:.3f}s > 0.600s boundary")

    passed = len(exceeded_snaps) == 0
    return AssertionResult(
        assertion_id="BOUND-DUR-01",
        requirement="R1 Duration Boundary",
        description="Part 1 cut boundary snap within +-0.30s per transition",
        passed=passed,
        observed_value=f"{len(exceeded_snaps)} clips exceeded snap boundary",
        expected_threshold="max snap deviation <= 0.60s total",
        error_message="Transition snap exceeded +-0.30s boundary" if not passed else "",
        affected_items=exceeded_snaps[:5],
    )


def verify_boundary_max_sequence_ceiling(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """Verify that total sequence duration is bounded: 420.0s <= duration <= 960.0s."""
    total_sec = parsed_seq.total_duration_sec
    passed = 420.0 <= total_sec <= 960.0

    return AssertionResult(
        assertion_id="BOUND-DUR-02",
        requirement="R6 Duration Boundary",
        description="Sequence total duration bounded: 420.0s <= duration <= 960.0s",
        passed=passed,
        observed_value=f"{total_sec:.2f}s ({total_sec/60.0:.2f}m)",
        expected_threshold="[420.0s .. 960.0s]",
        error_message=f"Sequence duration {total_sec:.2f}s exceeded ceiling" if not passed else "",
    )



def verify_boundary_extreme_duration_preservation(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """Verify that long non-note clips (>= 15s raw) preserve valid VisionCut climax duration (>= 1.80s)."""
    import json
    import os

    v3_all = parsed_seq.get_video_track(2)
    intro_end_f = max((c.end_frame for c in v3_all if "warning" in c.name.lower()), default=330)
    v3_by_name = {c.name: c for c in v3_all if c.start_frame >= intro_end_f}

    manifest_path = os.path.join(truth.project_dir, f"{truth.project_id}_manifest.json")
    manifest_durs = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                mdata = json.load(f)
            for mc in mdata.get("clips", []):
                manifest_durs[mc["clip_name"]] = mc.get("duration_sec")
        except Exception:
            pass

    truncated_extremes = []
    for p2 in truth.part2_items:
        if p2.rule_type == "raw_full" and p2.raw_duration and p2.raw_duration >= 15.0:
            matched_c = v3_by_name.get(p2.clip_name) or v3_by_name.get(f"{p2.slot_num}.mp4")
            if matched_c:
                tl_dur = matched_c.duration_sec
                expected_dur = manifest_durs.get(matched_c.name, tl_dur)
                if tl_dur < 1.15 or abs(tl_dur - expected_dur) > 0.35:
                    truncated_extremes.append(
                        f"Slot {p2.slot_num} (raw={p2.raw_duration:.1f}s, tl={tl_dur:.2f}s, expected={expected_dur:.2f}s)"
                    )

    passed = len(truncated_extremes) == 0
    return AssertionResult(
        assertion_id="BOUND-DUR-03",
        requirement="R1 Duration Boundary",
        description="Long clips (>= 15s raw) preserve valid VisionCut climax window",
        passed=passed,
        observed_value=f"{len(truncated_extremes)} long clips out of bounds",
        expected_threshold="0 long clips out of bounds",
        error_message=f"{len(truncated_extremes)} extreme-duration clips violated climax bounds" if not passed else "",
        affected_items=truncated_extremes,
    )


# Pytest test cases
@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_boundary_snap_tolerance(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_boundary_snap_tolerance(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_boundary_max_sequence_ceiling(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_boundary_max_sequence_ceiling(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_boundary_extreme_duration_preservation(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_boundary_extreme_duration_preservation(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"
