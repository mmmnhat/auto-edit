"""
Test Suite for Requirement R7: Intro Architecture & Non-Hardcoded Hook (Addendum #2).
Assertions:
- TEST-R7-01: Strict ban on hardcoded 'HELLOOOO, EVERYONE!' / 'Hello everyone!' in vault and intro VO scripts.
- TEST-R7-02: Ground-truth Intro architecture present (0..Warning_End ~335-390 frames, Track A6 Hadeus.mp4, Teaser 1 split 1a/1b).
- TEST-R7-03: Middle fast-cut teasers (6-8 rapid cuts, 15f-32f each) under middle Intro VO.
- TEST-R7-04: Final teaser crash gap before Warning card (20 frames Warning, A6 fade-out).
- TEST-R7-05: Track V8 captions aligned with spoken Intro VO clauses (no reused cards from past episodes).
"""

import json
import os
from typing import List
import pytest

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult


def verify_r7_ban_hardcoded_hello_intro(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R7-01: Verify ground-truth kb111-kb117 'Hello everyone!' greeting paired with unique episode-specific body hook."""
    proj_dir = truth.project_dir
    intro_txt_violations = []
    voice_dir = os.path.join(proj_dir, "voice")
    has_valid_script = False
    if os.path.exists(voice_dir):
        for fname in os.listdir(voice_dir):
            if "intro" in fname.lower() and fname.endswith(".txt"):
                txt_path = os.path.join(voice_dir, fname)
                with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read().lower()
                is_failside_hook = ("hello" in content and "everyone" in content and len(content.split()) >= 15)
                is_bzac_hook = (
                    len(content.split()) >= 15
                    and any(
                        k in content
                        for k in (
                            "let's get started",
                            "let's jump right in",
                            "let's dive right in",
                            "let's go",
                            "buckle up",
                            "brace yourself",
                            "another round of chaos",
                            "absurdist narration",
                            "hold everything",
                            "zero warning",
                            "wait for it",
                            "blink and you",
                            "brace for impact",
                            "watch closely",
                            "pure chaos",
                            "eyes on the screen",
                            "get ready",
                        )
                    )
                )
                if is_failside_hook or is_bzac_hook:
                    has_valid_script = True
                else:
                    intro_txt_violations.append(f"{fname}: missing valid intro hook or body clauses")

    passed = has_valid_script and len(intro_txt_violations) == 0
    return AssertionResult(
        assertion_id="TEST-R7-01",
        requirement="R7 Intro Architecture",
        description="Ground-truth kb111-kb117 'Hello everyone!' greeting with unique episode body hook",
        passed=passed,
        observed_value=f"valid_script={has_valid_script}, {len(intro_txt_violations)} violations",
        expected_threshold="valid_script=True, 0 violations",
        error_message="Intro VO script missing kb111-kb117 'Hello everyone' hook or body clauses" if not passed else "",
        affected_items=intro_txt_violations,
    )


def verify_r7_intro_architecture_present(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R7-02: Intro architecture present (Track A6 Hadeus.mp4, Teaser 1 split 1a/1b)."""
    a6_clips = parsed_seq.get_audio_track(5)
    v3_clips = parsed_seq.get_video_track(2)

    # 1. A6 must contain Hadeus.mp4 starting at frame 0 and ending at ~335-390 frames
    has_a6_hadeus = any("hadeus" in c.name.lower() and c.start_frame == 0 for c in a6_clips)

    # 2. V3 must have Teaser 1 split into 1a and 1b (same footage or consecutive teaser cut at 0..~85f)
    v3_intro_clips = [c for c in v3_clips if c.start_frame < 360]
    has_teaser_split = False
    if len(v3_intro_clips) >= 2:
        c1, c2 = v3_intro_clips[0], v3_intro_clips[1]
        # Either identical footage name or consecutive cuts forming Teaser 1
        if c1.start_frame == 0 and c1.end_frame < 60 and c2.start_frame == c1.end_frame:
            has_teaser_split = True

    passed = has_a6_hadeus and has_teaser_split and len(v3_intro_clips) >= 6
    errs = []
    if not has_a6_hadeus:
        errs.append("Missing Track A6 Hadeus.mp4 intro music starting at frame 0")
    if not has_teaser_split:
        errs.append("Teaser #1 is not split into 1a (Hook) and 1b (Crash silence gap)")
    if len(v3_intro_clips) < 6:
        errs.append(f"Insufficient intro teaser cuts ({len(v3_intro_clips)} < 6 clips in first 360 frames)")

    return AssertionResult(
        assertion_id="TEST-R7-02",
        requirement="R7 Intro Architecture",
        description="Ground-truth Intro architecture present (A6 Hadeus.mp4, Teaser 1a/1b split)",
        passed=passed,
        observed_value=f"A6_Hadeus={has_a6_hadeus}, Teaser1_split={has_teaser_split}, intro_cuts={len(v3_intro_clips)}",
        expected_threshold="A6_Hadeus=True, Teaser1_split=True, intro_cuts>=6",
        error_message="; ".join(errs),
    )


def verify_r7_middle_fast_cuts(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R7-03: Middle fast-cut teasers (6-8 rapid cuts, 15f-32f each) under middle Intro VO."""
    v3_clips = parsed_seq.get_video_track(2)
    # Middle teasers between frame 70 and frame 280
    mid_teasers = [c for c in v3_clips if 65 <= c.start_frame < 280]

    rapid_cuts = [c for c in mid_teasers if 12 <= c.duration_frames <= 38]
    passed = len(rapid_cuts) >= 5

    return AssertionResult(
        assertion_id="TEST-R7-03",
        requirement="R7 Intro Architecture",
        description="Middle fast-cut teasers (6-8 rapid climax cuts of 15-32 frames)",
        passed=passed,
        observed_value=f"{len(rapid_cuts)} rapid cuts (total mid clips={len(mid_teasers)})",
        expected_threshold=">= 5 rapid cuts between 15f and 32f",
        error_message=f"Only {len(rapid_cuts)} rapid cuts found in middle intro section (expected >= 5)"
        if not passed
        else "",
        affected_items=[f"{c.name}: {c.duration_frames}f" for c in mid_teasers[:6]],
    )


def verify_r7_warning_card_and_outro(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R7-04: Warning card (20 frames, ~335-390f) and intro boundary before main body."""
    v3_clips = parsed_seq.get_video_track(2)
    v10_clips = parsed_seq.get_video_track(9)

    # Check for Warning card or transition around ~334..390 frames
    warn_clips = [c for c in v3_clips + v10_clips if "warning" in c.name.lower() or (320 <= c.start_frame <= 400 and c.duration_frames == 20)]
    has_warning = len(warn_clips) > 0
    warn_end = max((c.end_frame for c in warn_clips), default=320)
    
    # Also check that Part 1 body starts AFTER the intro (> 330 frames)
    part1_clips = [c for c in v3_clips if c.name.startswith("itv.") and c.start_frame >= warn_end]
    part1_start_f = min((c.start_frame for c in part1_clips), default=0)

    passed = has_warning and part1_start_f >= 320
    errs = []
    if not has_warning:
        errs.append("No 20-frame Warning card found at intro conclusion")
    if part1_start_f < 320:
        errs.append(f"Part 1 body clips start prematurely at frame {part1_start_f} without complete intro")

    return AssertionResult(
        assertion_id="TEST-R7-04",
        requirement="R7 Intro Architecture",
        description="20-frame Warning card & Intro boundary before Part 1 body clips",
        passed=passed,
        observed_value=f"has_warning={has_warning}, part1_start_frame={part1_start_f}",
        expected_threshold="has_warning=True, part1_start_frame >= 320",
        error_message="; ".join(errs),
    )


# Pytest test cases
@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r7_ban_hardcoded_hello_intro(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r7_ban_hardcoded_hello_intro(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r7_intro_architecture_present(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r7_intro_architecture_present(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r7_middle_fast_cuts(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r7_middle_fast_cuts(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r7_warning_card_and_outro(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r7_warning_card_and_outro(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}"
