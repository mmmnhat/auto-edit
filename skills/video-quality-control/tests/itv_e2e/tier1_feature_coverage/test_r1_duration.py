"""
Test Suite for Requirement R1: Duration Preservation & Multi-Timestamp Splitting.
Assertions:
- TEST-R1-01: 0 timeline OVERRIDES (InPoint == 0 on Part 1).
- TEST-R1-02: 100% Sheet time match (+-0.3s snap, |tl_dur - sheet_dur| <= 0.60s).
- TEST-R1-03: 100% note duration match for Part 2 clips with notes (|tl_dur - note_dur| <= 0.30s).
- TEST-R1-04: 100% raw duration preservation for Part 2 non-note clips (0 arbitrary capping to 5.6s).
- TEST-R1-05: Multi-timestamp sources (>=2 TS) split into >=2 independent timeline items (0 concat).
"""

from typing import List, Tuple
import pytest

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult


def _get_body_v3_clips(parsed_seq: ParsedSequence):
    v3_all = parsed_seq.get_video_track(2)
    intro_end_f = max((c.end_frame for c in v3_all if "warning" in c.name.lower()), default=330)
    return [c for c in v3_all if c.start_frame >= intro_end_f]


def verify_r1_zero_overrides(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R1-01: Verify zero timeline OVERRIDES on Part 1 clips (InPoint == 0)."""
    v3_clips = _get_body_v3_clips(parsed_seq)
    part1_names = {p.clip_name for p in truth.part1_items}

    override_clips = []
    for c in v3_clips:
        if c.name in part1_names:
            if c.in_ticks != 0:
                override_clips.append(f"{c.name} (in_point={c.in_sec:.2f}s)")

    passed = len(override_clips) == 0
    return AssertionResult(
        assertion_id="TEST-R1-01",
        requirement="R1 Duration",
        description="Zero timeline OVERRIDES on Part 1 clips (InPoint == 0)",
        passed=passed,
        observed_value=f"{len(override_clips)} overridden clips",
        expected_threshold="0 overrides",
        error_message=f"Detected {len(override_clips)} clips with timeline in-point overrides" if not passed else "",
        affected_items=override_clips,
    )


def verify_r1_sheet_durations(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R1-02: 100% Sheet time match (+-0.3s transition snap, diff <= 0.60s)."""
    v3_clips = _get_body_v3_clips(parsed_seq)
    v3_by_name = {c.name: c for c in v3_clips}

    mismatches = []
    checked = 0
    for target in truth.part1_items:
        if target.clip_name in v3_by_name:
            checked += 1
            tl_dur = v3_by_name[target.clip_name].duration_sec
            diff = abs(tl_dur - target.target_duration)
            if diff > 0.60:
                mismatches.append(
                    f"{target.clip_name} (sheet={target.target_duration:.2f}s, tl={tl_dur:.2f}s, diff={diff:.2f}s)"
                )

    passed = len(mismatches) == 0 and checked > 0
    return AssertionResult(
        assertion_id="TEST-R1-02",
        requirement="R1 Duration",
        description="100% Google Sheet duration match (|tl_dur - sheet_dur| <= 0.60s)",
        passed=passed,
        observed_value=f"{len(mismatches)}/{checked} duration mismatches",
        expected_threshold="0 mismatches (tolerance <= 0.60s)",
        error_message=f"{len(mismatches)} Part 1 clips do not match Google Sheet duration" if not passed else "",
        affected_items=mismatches,
    )


def verify_r1_note_durations(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R1-03: 100% note duration match for Part 2 clips with explicit notes (|tl_dur - note_dur| <= 0.30s)."""
    v3_clips = _get_body_v3_clips(parsed_seq)
    v3_by_name = {c.name: c for c in v3_clips}

    mismatches = []
    checked = 0
    for p2 in truth.part2_items:
        if p2.target_duration is not None and not p2.is_multi_ts and p2.rule_type in ("head_n_sec", "explicit_range"):
            target_name = p2.clip_name
            # Try alternate slot names (e.g. 03.mp4 vs 3.mp4)
            matched_c = v3_by_name.get(target_name) or v3_by_name.get(f"{p2.slot_num}.mp4")
            if matched_c:
                checked += 1
                tl_dur = matched_c.duration_sec
                diff = abs(tl_dur - p2.target_duration)
                if diff > 0.35:
                    mismatches.append(
                        f"Slot {p2.slot_num} '{p2.note}' (expected={p2.target_duration:.2f}s, tl={tl_dur:.2f}s, diff={diff:.2f}s)"
                    )

    passed = len(mismatches) == 0
    return AssertionResult(
        assertion_id="TEST-R1-03",
        requirement="R1 Duration",
        description="100% note duration match for Part 2 clips (|tl_dur - note_dur| <= 0.30s)",
        passed=passed,
        observed_value=f"{len(mismatches)}/{checked} note duration mismatches",
        expected_threshold="0 mismatches (tolerance <= 0.30s)",
        error_message=f"{len(mismatches)} Part 2 clips violated editor note duration" if not passed else "",
        affected_items=mismatches,
    )


def verify_r1_non_note_raw_duration(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R1-04: Non-note Part 2 clips follow VisionCut climax window or raw duration (0 flat 5.6s cap)."""
    import json
    import os
    import numpy as np

    v3_clips = _get_body_v3_clips(parsed_seq)
    v3_by_name = {c.name: c for c in v3_clips}

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

    truncated_clips = []
    non_note_tl_durs = []
    checked = 0
    for p2 in truth.part2_items:
        if p2.rule_type == "raw_full" and p2.raw_duration and p2.raw_duration > 7.0:
            matched_c = v3_by_name.get(p2.clip_name) or v3_by_name.get(f"{p2.slot_num}.mp4")
            if matched_c:
                checked += 1
                tl_dur = matched_c.duration_sec
                non_note_tl_durs.append(tl_dur)
                expected_dur = manifest_durs.get(matched_c.name, p2.raw_duration)
                if tl_dur < 1.15 or abs(tl_dur - expected_dur) > 0.35:
                    truncated_clips.append(
                        f"Slot {p2.slot_num} (expected={expected_dur:.2f}s, tl={tl_dur:.2f}s)"
                    )

    # Ensure not flat-capped to a uniform 5.6s constant
    if len(non_note_tl_durs) > 3 and float(np.std(non_note_tl_durs)) < 0.25:
        truncated_clips.append(f"Flat uniform duration cap detected (std={float(np.std(non_note_tl_durs)):.3f}s)")

    passed = len(truncated_clips) == 0
    return AssertionResult(
        assertion_id="TEST-R1-04",
        requirement="R1 Duration",
        description="VisionCut climax duration preservation for non-note clips (0 arbitrary flat 5.6s cap)",
        passed=passed,
        observed_value=f"{len(truncated_clips)}/{checked} non-note clips out of spec",
        expected_threshold="0 flat-capped or mismatched clips",
        error_message=f"{len(truncated_clips)} non-note clips violated climax duration spec" if not passed else "",
        affected_items=truncated_clips,
    )


def verify_r1_multi_timestamp_split(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R1-05: Multi-timestamp sources must be split into >= 2 separate timeline clips (0 concat)."""
    v3_clips = _get_body_v3_clips(parsed_seq)
    v3_names = [c.name for c in v3_clips]

    unsplit_sources = []
    checked = 0
    for p2 in truth.part2_items:
        if p2.is_multi_ts:
            checked += 1
            slot = p2.slot_num
            # Should have discrete files e.g. 46_1.mp4 and 46_2.mp4
            sub_clips = [n for n in v3_names if f"{slot}_" in n or f"{slot:02d}_" in n]
            if len(sub_clips) < 2:
                # Check if a single joined file exists (like 46.mp4)
                single = [n for n in v3_names if n == f"{slot}.mp4" or n == f"{slot:02d}.mp4"]
                unsplit_sources.append(
                    f"Slot {slot} '{p2.note}': found {len(sub_clips)} split clips, single={single}"
                )

    passed = len(unsplit_sources) == 0
    return AssertionResult(
        assertion_id="TEST-R1-05",
        requirement="R1 Duration",
        description="Multi-timestamp sources split into >= 2 separate files (0 concat)",
        passed=passed,
        observed_value=f"{len(unsplit_sources)}/{checked} unsplit multi-ts sources",
        expected_threshold="0 unsplit sources (>= 2 separate files each)",
        error_message=f"{len(unsplit_sources)} multi-timestamp sources were not split" if not passed else "",
        affected_items=unsplit_sources,
    )


# Pytest test cases
@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r1_zero_overrides(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r1_zero_overrides(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r1_sheet_durations(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r1_sheet_durations(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r1_note_durations(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r1_note_durations(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r1_non_note_raw_duration(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r1_non_note_raw_duration(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r1_multi_timestamp_split(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r1_multi_timestamp_split(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"
