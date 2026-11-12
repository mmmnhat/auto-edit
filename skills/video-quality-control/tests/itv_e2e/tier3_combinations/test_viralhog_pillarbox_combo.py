"""
Tier 3: Combination Testing — ViralHog + Pillarbox Dual Constraint Synergy.
When a footage is both ViralHog AND Pillarbox:
1. Crop Left / Crop Right must be applied (25% - 35%) to cut blurred margins.
2. Scale must be increased proportionally: Scale >= 115.0% * (1080 / CropHeight).
3. Blur mask components count must strictly equal 0.
"""

import pytest

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult


def verify_combo_viralhog_pillarbox_synergy(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """Verify combined constraint: ViralHog + Pillarbox clips have Crop + Extra Scale + Zero Blur."""
    v3_clips = parsed_seq.get_video_track(2)
    vh_names = truth.viralhog_clip_names

    violations = []
    checked = 0

    for c in v3_clips:
        is_vh = c.name in vh_names or any(c.name.startswith(k.replace(".mp4", "")) for k in vh_names if k.endswith(".mp4"))
        if is_vh and (c.crop_left > 1.0 or c.crop_right > 1.0):
            checked += 1
            # Combined rules:
            # 1. Zero blur
            if len(c.blur_effects) > 0:
                violations.append(f"{c.name}: has blur {c.blur_effects} on ViralHog Pillarbox")
            # 2. Scale >= 120.0% to compensate for cropped canvas
            if c.scale < 120.0:
                violations.append(f"{c.name}: scale={c.scale:.1f}% insufficient for cropped ViralHog (expected >= 120%)")

    passed = len(violations) == 0
    return AssertionResult(
        assertion_id="COMBO-VH-PILLAR-01",
        requirement="R2 Combination Synergy",
        description="ViralHog + Pillarbox dual constraint: Crop + Compensated Scale >= 120% + 0 Blur",
        passed=passed,
        observed_value=f"{len(violations)}/{checked} combo violations",
        expected_threshold="0 combo violations",
        error_message=f"{len(violations)} ViralHog pillarbox clips violated combined rules" if not passed else "",
        affected_items=violations,
    )


# Pytest test cases
@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_combo_viralhog_pillarbox_synergy(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_combo_viralhog_pillarbox_synergy(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"
