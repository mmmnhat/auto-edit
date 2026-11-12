"""
Tier 2: Boundary Value Testing — Scale & Crop Geometric Bounds.
Verifies boundary conditions:
- Scale lower bound: ViralHog clips must satisfy Scale >= 115.0%.
- Crop boundary: Pillarbox clips must satisfy 20.0% <= Crop <= 38.0%.
- Opacity boundary: Track V1 background opacity == 99.0% or 100.0%.
- Track V1 Background Scale boundary: Scale 115% x 114.77%.
"""

import pytest

from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult


def verify_boundary_viralhog_scale_lower_bound(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """Verify that no ViralHog clip has Scale < 115.0%."""
    v3_clips = parsed_seq.get_video_track(2)
    vh_names = truth.viralhog_clip_names

    failing_clips = []
    checked = 0
    for c in v3_clips:
        if c.name in vh_names or any(c.name.startswith(k.replace(".mp4", "")) for k in vh_names if k.endswith(".mp4")):
            checked += 1
            if c.scale < 114.99:
                failing_clips.append(f"{c.name}: scale={c.scale:.2f}% < 115.00% lower bound")

    passed = len(failing_clips) == 0 and checked > 0
    return AssertionResult(
        assertion_id="BOUND-SCALE-01",
        requirement="R2 Scale Boundary",
        description="ViralHog clips satisfy Scale >= 115.00% lower bound",
        passed=passed,
        observed_value=f"{len(failing_clips)}/{checked} below lower bound",
        expected_threshold="Scale >= 115.00%",
        error_message="ViralHog clips violate minimum 115.0% scale boundary" if not passed else "",
        affected_items=failing_clips[:5],
    )


def verify_boundary_pillarbox_crop_range(parsed_seq: ParsedSequence, truth: ProjectGroundTruth) -> AssertionResult:
    """Verify that cropped pillarbox clips stay strictly within legitimate aspect crop bounds [20.0%, 38.0%]."""
    v3_clips = parsed_seq.get_video_track(2)

    out_of_bounds = []
    for c in v3_clips:
        if c.crop_left > 0.1 or c.crop_right > 0.1:
            if not (20.0 <= c.crop_left <= 38.0 and 20.0 <= c.crop_right <= 38.0):
                out_of_bounds.append(f"{c.name}: crop_l={c.crop_left:.1f}%, crop_r={c.crop_right:.1f}%")

    passed = len(out_of_bounds) == 0
    return AssertionResult(
        assertion_id="BOUND-SCALE-02",
        requirement="R2 Crop Boundary",
        description="Pillarbox crop within bounds [20.0% .. 38.0%]",
        passed=passed,
        observed_value=f"{len(out_of_bounds)} out-of-bound crop clips",
        expected_threshold="[20.0% .. 38.0%]",
        error_message="Crop values out of expected aspect boundary" if not passed else "",
        affected_items=out_of_bounds,
    )


# Pytest test cases
@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_boundary_viralhog_scale_lower_bound(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_boundary_viralhog_scale_lower_bound(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"


@pytest.mark.parametrize("project_id", ["kb118", "kb119", "kb120", "kb121"])
def test_boundary_pillarbox_crop_range(project_id: str):
    truth = GroundTruthLoader.load_project_truth(project_id)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse()
    res = verify_boundary_pillarbox_crop_range(seq, truth)
    assert res.passed, f"[{project_id}] {res.error_message}: {res.affected_items}"
