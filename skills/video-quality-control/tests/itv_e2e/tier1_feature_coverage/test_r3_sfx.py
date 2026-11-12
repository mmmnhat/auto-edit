r"""
Test Suite for Requirement R3: SFX Placement Rules & Strict Interjection Ban.
Assertions:
- TEST-R3-01: 0 collision SFX on audible Track A1 clips (Part 1 live camera audio).
- TEST-R3-02: 100% SFX coverage on silent montage under Track A5 BGM.
- TEST-R3-03: 0 overlap between Track A3/A4 SFX and Track A2 Voiceover.
- TEST-R3-04: Strict Ban on Interjection SFX (0 files from E:\Video Asset\SFX\interjection).
"""

import json
import os
from typing import List, Set
import pytest

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult
from tests.core.timeline_math import intervals_overlap_seconds

PHYSICAL_COLLISION_SFX = {
    "sword-hit.mp3",
    "slip-2.mp3",
    "bone-crack.mp3",
    "metallic-bonk-and-rattle.mp3",
    "bone-fracture.mp3",
    "gmod-fall-damage-1.mp3",
    "bonk.mp3",
    "cartoonsplash.mp3",
    "car-brake.mp3",
    "goosh.mp3",
    "quick-car-crash.mp3",
    "body-impact.mp3",
    "splash.m4a",
    "oof.mp3",
    "bamboo-hit.mp3",
    "crash-metal-shatter.mp3",
    "boin4.mp3",
    "slip.mp3",
    "tree_fall_small.mp3",
    "body-fall-sound-effect.mp3",
}


def verify_r3_no_collision_sfx_on_a1(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R3-01: 0 collision SFX on audible Track A1 clips (Part 1)."""
    v3_clips = parsed_seq.get_video_track(2)
    part1_clips = [c for c in v3_clips if c.name.startswith("itv.")]
    part1_intervals = [(c.start_frame, c.end_frame) for c in part1_clips]

    a3_clips = parsed_seq.get_audio_track(2)
    a4_clips = parsed_seq.get_audio_track(3)

    colliding_sfx = []
    for sfx in a3_clips + a4_clips:
        sfx_nm = sfx.name.lower()
        if any(c_sfx in sfx_nm for c_sfx in PHYSICAL_COLLISION_SFX):
            # Check if it overlaps any Part 1 clip
            for ps_f, pe_f in part1_intervals:
                if not (sfx.end_frame <= ps_f or sfx.start_frame >= pe_f):
                    colliding_sfx.append(f"{sfx.name} at {sfx.start_sec:.2f}s over Part 1")
                    break

    passed = len(colliding_sfx) == 0
    return AssertionResult(
        assertion_id="TEST-R3-01",
        requirement="R3 SFX",
        description="Zero collision SFX on audible Track A1 camera audio (Part 1)",
        passed=passed,
        observed_value=f"{len(colliding_sfx)} collision SFX on Part 1",
        expected_threshold="0 collision SFX on live camera audio",
        error_message=f"{len(colliding_sfx)} collision SFX placed over live camera audio" if not passed else "",
        affected_items=colliding_sfx,
    )


def verify_r3_silent_montage_sfx_coverage(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R3-02: 100% SFX coverage on silent montage under Track A5 BGM."""
    a5_clips = parsed_seq.get_audio_track(4)
    v3_clips = parsed_seq.get_video_track(2)
    a3_clips = parsed_seq.get_audio_track(2)
    a4_clips = parsed_seq.get_audio_track(3)

    if not a5_clips:
        return AssertionResult(
            assertion_id="TEST-R3-02",
            requirement="R3 SFX",
            description="100% SFX coverage on silent montage under Track A5 BGM",
            passed=True,
            observed_value="No A5 BGM track",
            expected_threshold="100% coverage",
        )

    # Clips occurring during A5 BGM
    a5_start_f = min(c.start_frame for c in a5_clips)
    a5_end_f = max(c.end_frame for c in a5_clips)

    silent_v3 = [c for c in v3_clips if c.start_frame >= a5_start_f and c.end_frame <= a5_end_f + 10]
    sfx_items = a3_clips + a4_clips

    uncovered_clips = []
    for c in silent_v3:
        # Check if any SFX falls within clip range
        has_sfx = any(not (s.end_frame <= c.start_frame or s.start_frame >= c.end_frame) for s in sfx_items)
        if not has_sfx:
            uncovered_clips.append(f"{c.name} at {c.start_sec:.2f}s")

    coverage_pct = 100.0
    if silent_v3:
        coverage_pct = ((len(silent_v3) - len(uncovered_clips)) / float(len(silent_v3))) * 100.0

    passed = len(uncovered_clips) == 0
    return AssertionResult(
        assertion_id="TEST-R3-02",
        requirement="R3 SFX",
        description="100% SFX coverage on silent clips under Track A5 BGM",
        passed=passed,
        observed_value=f"{coverage_pct:.1f}% ({len(uncovered_clips)}/{len(silent_v3)} uncovered)",
        expected_threshold="100% SFX coverage",
        error_message=f"{len(uncovered_clips)} silent montage clips lack physical SFX" if not passed else "",
        affected_items=uncovered_clips,
    )


def verify_r3_zero_a2_vo_overlap(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R3-03: Zero overlap between Track A3/A4 SFX and Track A2 Voiceover."""
    a2_clips = parsed_seq.get_audio_track(1)
    a3_clips = parsed_seq.get_audio_track(2)
    a4_clips = parsed_seq.get_audio_track(3)

    a2_ints = [(c.start_frame, c.end_frame) for c in a2_clips]
    sfx_ints = [(c.start_frame, c.end_frame) for c in a3_clips + a4_clips]

    overlap_sec = intervals_overlap_seconds(a2_ints, sfx_ints)
    passed = overlap_sec < 0.04  # < 1 frame tolerance

    return AssertionResult(
        assertion_id="TEST-R3-03",
        requirement="R3 SFX",
        description="Zero overlap between Track A3/A4 SFX and Track A2 Voiceover",
        passed=passed,
        observed_value=f"{overlap_sec:.3f}s overlap",
        expected_threshold="0.000s overlap",
        error_message=f"SFX collides with Voiceover on Track A2 ({overlap_sec:.3f}s)" if not passed else "",
    )


def verify_r3_strict_interjection_ban(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R3-04: Strict ban on SFX from E:\\Video Asset\\SFX\\interjection (all 37 files)."""
    banned_files = truth.banned_sfx_files
    a3_clips = parsed_seq.get_audio_track(2)
    a4_clips = parsed_seq.get_audio_track(3)

    found_banned = []
    for c in a3_clips + a4_clips:
        nm_clean = c.name.lower().strip()
        if nm_clean in banned_files or any(b in nm_clean for b in ["what the", "ouch", "oops", "whoa, hold on"]):
            found_banned.append(f"{c.name} at {c.start_sec:.2f}s on A{c.track_index+1}")

    # Also check catalog files
    catalog_path = r"E:\.agents\skills\visioncut\resources\sfx_full_catalog.json"
    profiles_path = r"E:\.agents\skills\visioncut\resources\channel_profiles.json"
    catalog_violations = []
    for cp in (catalog_path, profiles_path):
        if os.path.exists(cp):
            with open(cp, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().lower()
            for b in banned_files:
                if b in content:
                    catalog_violations.append(f"{os.path.basename(cp)}: contains '{b}'")
                    break

    passed = len(found_banned) == 0 and len(catalog_violations) == 0
    return AssertionResult(
        assertion_id="TEST-R3-04",
        requirement="R3 SFX",
        description="Strict ban on interjection SFX on timeline and in configs",
        passed=passed,
        observed_value=f"{len(found_banned)} timeline items, {len(catalog_violations)} catalog violations",
        expected_threshold="0 interjection SFX entries",
        error_message="Detected banned interjection SFX on timeline or in configs" if not passed else "",
        affected_items=found_banned + catalog_violations,
    )


# Pytest test cases
@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r3_no_collision_sfx_on_a1(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r3_no_collision_sfx_on_a1(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r3_silent_montage_sfx_coverage(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r3_silent_montage_sfx_coverage(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r3_zero_a2_vo_overlap(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r3_zero_a2_vo_overlap(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r3_strict_interjection_ban(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r3_strict_interjection_ban(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"
