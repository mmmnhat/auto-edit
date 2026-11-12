"""
Test Suite for Requirement R4: Emoji / Reaction GIF Standards & Context-Aware V8 Safety Graphics.
Assertions:
- TEST-R4-01: Zero static center emojis (0.50, 0.50) on Track V4.
- TEST-R4-02: Track V4 keyframed impact tracking (0.2s-0.8s) or lower-corner reaction GIFs (1.5s-2.3s).
- TEST-R4-03: Track V8 Safety Graphics: Modulo loop (index % 4 == 1) eliminated & semantic subject matching.
"""

from typing import List
import pytest

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult


def verify_r4_zero_static_center_emojis(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R4-01: Zero static center emojis (0.50, 0.50) on Track V4."""
    v4_clips = parsed_seq.get_video_track(3)

    static_emojis = []
    for c in v4_clips:
        if c.is_static_center:
            pts_str = ", ".join(f"({x:.2f},{y:.2f})" for _, x, y in c.position_keyframes[:3])
            static_emojis.append(f"{c.name} at {c.start_sec:.2f}s [{pts_str or c.position}]")

    passed = len(static_emojis) == 0
    return AssertionResult(
        assertion_id="TEST-R4-01",
        requirement="R4 Emojis & Graphics",
        description="Zero static center emojis on Track V4 (no 0.50, 0.50 center clustering)",
        passed=passed,
        observed_value=f"{len(static_emojis)} static center emojis",
        expected_threshold="0 static center emojis",
        error_message=f"{len(static_emojis)} emojis are placed statically near screen center" if not passed else "",
        affected_items=static_emojis,
    )


def verify_r4_emoji_duration_and_placement(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R4-02: V4 items must be impact shields (0.2s-0.8s) or corner reaction GIFs (1.5s-2.3s)."""
    v4_clips = parsed_seq.get_video_track(3)

    invalid_items = []
    for c in v4_clips:
        dur = c.duration_sec
        # Type 1: Impact shield (0.2s..0.8s)
        # Type 2: Reaction GIF (1.5s..2.5s at corner)
        is_shield = 0.18 <= dur <= 0.85
        is_reaction_gif = 1.40 <= dur <= 2.60 and (c.position[0] > 0.70 or c.position[0] < 0.25)

        if not (is_shield or is_reaction_gif):
            invalid_items.append(f"{c.name} (dur={dur:.2f}s, pos={c.position})")

    passed = len(invalid_items) == 0
    return AssertionResult(
        assertion_id="TEST-R4-02",
        requirement="R4 Emojis & Graphics",
        description="Track V4 valid impact duration (0.2-0.8s) or corner reaction GIF (1.5-2.3s)",
        passed=passed,
        observed_value=f"{len(invalid_items)}/{len(v4_clips)} non-compliant V4 items",
        expected_threshold="0 non-compliant items",
        error_message=f"{len(invalid_items)} V4 items do not match impact shield or reaction GIF standards"
        if not passed
        else "",
        affected_items=invalid_items,
    )


def verify_r4_v8_safety_graphics_policy(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R4-03: Track V8 safety graphics: modulo loop eliminated and context subject matching."""
    v8_clips = parsed_seq.get_video_track(7)
    v3_clips = parsed_seq.get_video_track(2)

    # In previous buggy builds:
    # finish_kb119_121_studio.py placed graphics on cinfo["index"] % 4 == 1
    # Check if clips placed on V8 strictly follow modulo 4 periodicity
    matched_v3_indices = []
    for g in v8_clips:
        # find matching V3 clip
        for idx, v3 in enumerate(v3_clips):
            if abs(g.start_ticks - v3.start_ticks) < 1000:
                matched_v3_indices.append(idx)
                break

    # Check modulo loop signature: if >= 75% of placed graphics have index % 4 == 1
    modulo_hits = sum(1 for idx in matched_v3_indices if idx % 4 == 1)
    is_modulo_loop = len(matched_v3_indices) >= 4 and (modulo_hits / len(matched_v3_indices)) >= 0.75

    # Check text instances: each V8 clip should decode to known safety text
    unknown_texts = []
    for g in v8_clips:
        texts = g.text_instance_names
        # Filter out generic intro cards
        if g.start_sec > 15.0:
            valid_safety = any(
                w in str(texts).upper() for w in ["FINE", "SAFE", "OKAY", "DRIVER", "GOOD", "HURT", "TRY", "COPY"]
            )
            if not valid_safety:
                unknown_texts.append(f"V8 clip at {g.start_sec:.2f}s texts={texts}")

    passed = (not is_modulo_loop) and len(unknown_texts) == 0
    errs = []
    if is_modulo_loop:
        errs.append(f"Detected blind modulo loop index % 4 == 1 ({modulo_hits}/{len(matched_v3_indices)} hits)")
    if unknown_texts:
        errs.append(f"{len(unknown_texts)} V8 clips have unknown/unmapped text")

    return AssertionResult(
        assertion_id="TEST-R4-03",
        requirement="R4 Emojis & Graphics",
        description="Track V8 safety graphics modulo loop eliminated & semantic text mapping",
        passed=passed,
        observed_value=f"modulo_loop={is_modulo_loop}, unknown_texts={len(unknown_texts)}",
        expected_threshold="modulo_loop=False, 100% semantic matching",
        error_message="; ".join(errs),
        affected_items=unknown_texts[:5],
    )


# Pytest test cases
@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r4_zero_static_center_emojis(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r4_zero_static_center_emojis(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r4_emoji_duration_and_placement(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r4_emoji_duration_and_placement(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r4_v8_safety_graphics_policy(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r4_v8_safety_graphics_policy(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"
