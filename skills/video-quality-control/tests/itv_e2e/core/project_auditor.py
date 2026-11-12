"""
Full Project Auditor.
Executes all formal assertions across R1-R7 and Tiers 1-3 on a specific project,
producing a unified ProjectTestReport.
"""

from typing import List
from tests.core.ground_truth_loader import GroundTruthLoader, ProjectGroundTruth
from tests.core.prproj_parser import ParsedSequence, PrprojFastParser
from tests.core.report_generator import AssertionResult, ProjectTestReport

from tests.tier1_feature_coverage.test_r1_duration import (
    verify_r1_zero_overrides,
    verify_r1_sheet_durations,
    verify_r1_note_durations,
    verify_r1_non_note_raw_duration,
    verify_r1_multi_timestamp_split,
)
from tests.tier1_feature_coverage.test_r2_watermarks import (
    verify_r2_viralhog_scale,
    verify_r2_viralhog_zero_blur,
    verify_r2_zero_blind_blur,
    verify_r2_channel_preset_accuracy,
)
from tests.tier1_feature_coverage.test_r3_sfx import (
    verify_r3_no_collision_sfx_on_a1,
    verify_r3_silent_montage_sfx_coverage,
    verify_r3_zero_a2_vo_overlap,
    verify_r3_strict_interjection_ban,
)
from tests.tier1_feature_coverage.test_r4_emojis_graphics import (
    verify_r4_zero_static_center_emojis,
    verify_r4_emoji_duration_and_placement,
    verify_r4_v8_safety_graphics_policy,
)
from tests.tier1_feature_coverage.test_r5_voiceover import (
    verify_r5_dynamic_vo_offset,
    verify_r5_v5_a2_subtitle_sync,
    verify_r5_premise_vs_aftermath_logic,
)
from tests.tier1_feature_coverage.test_r6_premiere_invariants import (
    verify_r6_audio_coverage,
    verify_r6_v1_v3_sync,
    verify_r6_v5_a2_sync,
    verify_r6_zero_black_gaps,
    verify_r6_clean_prproj_xml,
)
from tests.tier1_feature_coverage.test_r7_intro import (
    verify_r7_ban_hardcoded_hello_intro,
    verify_r7_intro_architecture_present,
    verify_r7_middle_fast_cuts,
    verify_r7_warning_card_and_outro,
)
from tests.tier2_boundaries.test_duration_boundaries import (
    verify_boundary_snap_tolerance,
    verify_boundary_max_sequence_ceiling,
    verify_boundary_extreme_duration_preservation,
)
from tests.tier2_boundaries.test_scale_crop_boundaries import (
    verify_boundary_viralhog_scale_lower_bound,
    verify_boundary_pillarbox_crop_range,
)
from tests.tier2_boundaries.test_sfx_timing_boundaries import (
    verify_boundary_sfx_vo_zero_overlap,
    verify_boundary_a1_a5_bgm_zero_overlap,
)
from tests.tier2_boundaries.test_intro_frame_boundaries import (
    verify_boundary_intro_total_frames,
    verify_boundary_warning_card_20_frames,
)
from tests.tier3_combinations.test_viralhog_pillarbox_combo import (
    verify_combo_viralhog_pillarbox_synergy,
)
from tests.tier3_combinations.test_multits_and_audio_synergy import (
    verify_combo_multits_video_audio_synergy,
)
from tests.tier3_combinations.test_vo_mogrt_v8_alignment import (
    verify_combo_vo_sub_v8_alignment,
)


def audit_full_project(project_id: str, base_dir: str = r"E:\ITV\Project") -> ProjectTestReport:
    truth = GroundTruthLoader.load_project_truth(project_id, base_dir=base_dir)
    parser = PrprojFastParser(truth.prproj_path)
    seq = parser.parse(target_sequence_name=project_id)

    validators = [
        # Tier 1 R1
        verify_r1_zero_overrides,
        verify_r1_sheet_durations,
        verify_r1_note_durations,
        verify_r1_non_note_raw_duration,
        verify_r1_multi_timestamp_split,
        # Tier 1 R2
        verify_r2_viralhog_scale,
        verify_r2_viralhog_zero_blur,
        verify_r2_zero_blind_blur,
        verify_r2_channel_preset_accuracy,
        # Tier 1 R3
        verify_r3_no_collision_sfx_on_a1,
        verify_r3_silent_montage_sfx_coverage,
        verify_r3_zero_a2_vo_overlap,
        verify_r3_strict_interjection_ban,
        # Tier 1 R4
        verify_r4_zero_static_center_emojis,
        verify_r4_emoji_duration_and_placement,
        verify_r4_v8_safety_graphics_policy,
        # Tier 1 R5
        verify_r5_dynamic_vo_offset,
        verify_r5_v5_a2_subtitle_sync,
        verify_r5_premise_vs_aftermath_logic,
        # Tier 1 R6
        verify_r6_audio_coverage,
        verify_r6_v1_v3_sync,
        verify_r6_v5_a2_sync,
        verify_r6_zero_black_gaps,
        verify_r6_clean_prproj_xml,
        # Tier 1 R7
        verify_r7_ban_hardcoded_hello_intro,
        verify_r7_intro_architecture_present,
        verify_r7_middle_fast_cuts,
        verify_r7_warning_card_and_outro,
        # Tier 2 Boundaries
        verify_boundary_snap_tolerance,
        verify_boundary_max_sequence_ceiling,
        verify_boundary_extreme_duration_preservation,
        verify_boundary_viralhog_scale_lower_bound,
        verify_boundary_pillarbox_crop_range,
        verify_boundary_sfx_vo_zero_overlap,
        verify_boundary_a1_a5_bgm_zero_overlap,
        verify_boundary_intro_total_frames,
        verify_boundary_warning_card_20_frames,
        # Tier 3 Combinations
        verify_combo_viralhog_pillarbox_synergy,
        verify_combo_multits_video_audio_synergy,
        verify_combo_vo_sub_v8_alignment,
    ]

    results: List[AssertionResult] = []
    passed_count = 0
    failed_count = 0

    for val_fn in validators:
        res = val_fn(seq, truth)
        results.append(res)
        if res.passed:
            passed_count += 1
        else:
            failed_count += 1

    return ProjectTestReport(
        project_id=project_id,
        total_assertions=len(results),
        passed_assertions=passed_count,
        failed_assertions=failed_count,
        duration_ms=seq.parse_time_ms,
        results=results,
    )
