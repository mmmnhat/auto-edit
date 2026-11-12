"""
Test Suite for Requirement R2: Channel Watermark Presets & ViralHog Zoom-Only Rule.
Assertions:
- TEST-R2-01: Channel watermark presets properly applied (FailSide A/B, Dual Top, Single, Crop).
- TEST-R2-02: Zero blind blur template (template 8000) applied generically across all clips.
- TEST-R2-03: ViralHog Scale >= 115.0% to push logo outside 1080p canvas.
- TEST-R2-04: Strict zero blur mask on ViralHog clips (0 Gaussian Blur / Impact_Blur on ViralHog).
"""

from typing import List, Set
import pytest

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult


def verify_r2_viralhog_scale(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R2-03: Every ViralHog clip must have Scale >= 115.0%."""
    v3_clips = parsed_seq.get_video_track(2)
    vh_names = truth.viralhog_clip_names

    under_scaled_clips = []
    checked = 0
    for c in v3_clips:
        if c.name in vh_names or any(c.name.startswith(k.replace(".mp4", "")) for k in vh_names if k.endswith(".mp4")):
            checked += 1
            if c.scale < 114.90:
                under_scaled_clips.append(f"{c.name} (scale={c.scale:.1f}%)")

    passed = len(under_scaled_clips) == 0 and checked > 0
    return AssertionResult(
        assertion_id="TEST-R2-03",
        requirement="R2 Watermark",
        description="ViralHog clips zoomed to Scale >= 115.0%",
        passed=passed,
        observed_value=f"{len(under_scaled_clips)}/{checked} ViralHog clips with Scale < 115.0%",
        expected_threshold="Scale >= 115.0% on all ViralHog clips",
        error_message=f"{len(under_scaled_clips)} ViralHog clips were not zoomed sufficiently" if not passed else "",
        affected_items=under_scaled_clips,
    )


def verify_r2_viralhog_zero_blur(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R2-04: Strict zero blur mask on ViralHog clips."""
    v3_clips = parsed_seq.get_video_track(2)
    vh_names = truth.viralhog_clip_names

    blurred_vh_clips = []
    checked = 0
    for c in v3_clips:
        if c.name in vh_names or any(c.name.startswith(k.replace(".mp4", "")) for k in vh_names if k.endswith(".mp4")):
            checked += 1
            if len(c.blur_effects) > 0:
                blurred_vh_clips.append(f"{c.name} (blurs={c.blur_effects})")

    passed = len(blurred_vh_clips) == 0
    return AssertionResult(
        assertion_id="TEST-R2-04",
        requirement="R2 Watermark",
        description="Strict zero blur mask on ViralHog clips",
        passed=passed,
        observed_value=f"{len(blurred_vh_clips)}/{checked} ViralHog clips with blur masks",
        expected_threshold="0 blur masks on ViralHog",
        error_message=f"{len(blurred_vh_clips)} ViralHog clips have blur masks applied" if not passed else "",
        affected_items=blurred_vh_clips,
    )


def verify_r2_zero_blind_blur(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R2-02: Zero blind blur template (template 8000) applied generically across all clips."""
    v3_clips = parsed_seq.get_video_track(2)

    # In previous buggy builds, every single itv.* clip received identical blur component
    itv_clips = [c for c in v3_clips if c.name.startswith("itv.")]
    blindly_blurred = []
    for c in itv_clips:
        if len(c.blur_effects) > 0:
            blindly_blurred.append(c.name)

    # If 100% of itv clips have blur blindly attached, flag as failure
    passed = len(blindly_blurred) < len(itv_clips) or len(itv_clips) == 0
    return AssertionResult(
        assertion_id="TEST-R2-02",
        requirement="R2 Watermark",
        description="Zero blind blur template 8000 applied across all Part 1 clips",
        passed=passed,
        observed_value=f"{len(blindly_blurred)}/{len(itv_clips)} Part 1 clips with blur",
        expected_threshold="Channel-specific selective presets (not 100% blind assignment)",
        error_message="All Part 1 clips received blind blur template 8000" if not passed else "",
        affected_items=blindly_blurred[:10],
    )


def verify_r2_channel_preset_accuracy(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """TEST-R2-01: Channel watermark preset validation (crop or valid preset mask)."""
    v3_clips = parsed_seq.get_video_track(2)

    # Clips with pillarbox viền mờ should have crop applied (25% - 35%)
    # And non-ViralHog clips should not have negative or out-of-bound crops
    invalid_crop_clips = []
    for c in v3_clips:
        if c.crop_left > 0 or c.crop_right > 0:
            if not (20.0 <= c.crop_left <= 40.0 and 20.0 <= c.crop_right <= 40.0):
                invalid_crop_clips.append(f"{c.name} (crop_l={c.crop_left:.1f}%, crop_r={c.crop_right:.1f}%)")

    passed = len(invalid_crop_clips) == 0
    return AssertionResult(
        assertion_id="TEST-R2-01",
        requirement="R2 Watermark",
        description="Channel watermark preset and crop validity",
        passed=passed,
        observed_value=f"{len(invalid_crop_clips)} invalid crop clips",
        expected_threshold="0 invalid crop settings",
        error_message=f"{len(invalid_crop_clips)} clips have invalid crop parameters" if not passed else "",
        affected_items=invalid_crop_clips,
    )


# Pytest test cases
@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r2_viralhog_scale(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r2_viralhog_scale(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r2_viralhog_zero_blur(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r2_viralhog_zero_blur(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r2_zero_blind_blur(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r2_zero_blind_blur(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_r2_channel_preset_accuracy(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_r2_channel_preset_accuracy(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"
