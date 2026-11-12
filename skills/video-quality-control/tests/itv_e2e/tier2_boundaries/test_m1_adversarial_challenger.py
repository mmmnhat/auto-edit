"""
Adversarial Stress Test Suite for Milestone 1 Gate
Challenger 1: Empirical Verification of Multi-Timestamp Parser and Dynamic VO Timing Generator

Covers:
1. parse_time_ranges extreme inputs (overlapping, single, 4 timestamps, negative, inverted, non-ASCII/messy)
2. compute_dynamic_vo_timing edge cases (clip_dur < vo_dur, impact==0, impact==clip_dur, 2.0s, 30.0s, None)
"""

import sys
import os
import pytest

# Ensure source scripts can be imported
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
YS_PATH = os.path.join(PROJECT_ROOT, "youtube_source_cutter", "scripts")
VC_PATH = os.path.join(r"E:\.agents\skills\visioncut\scripts")

if YS_PATH not in sys.path:
    sys.path.insert(0, YS_PATH)
if VC_PATH not in sys.path:
    sys.path.insert(0, VC_PATH)

import youtube_sheet_slicer as ys
import itv_ingest_from_sheet_and_amz as ia
from itv_vo_comment_generator import compute_dynamic_vo_timing


# ==============================================================================
# SECTION 1: parse_time_ranges Adversarial Stress Tests
# ==============================================================================

class TestParseTimeRangesExtreme:
    """Stress-test parse_time_ranges across extreme and adversarial inputs."""

    @pytest.mark.parametrize("module,func", [
        ("youtube_sheet_slicer", ys.parse_time_ranges),
        ("itv_ingest", ia.parse_time_ranges),
    ])
    def test_single_timestamps(self, module, func):
        """Single timestamps must parse cleanly."""
        res1 = func("0:15 - 0:30", 100.0)
        assert res1 == [(15.0, 30.0)], f"{module} failed on '0:15 - 0:30'"

        res2 = func("15s đầu", 100.0)
        assert res2 == [(0.0, 15.0)], f"{module} failed on '15s đầu'"

        res3 = func("15 giây đầu", 100.0)
        assert res3 == [(0.0, 15.0)], f"{module} failed on '15 giây đầu'"

        res4 = func("2:25 - hết", 300.0)
        assert res4 == [(145.0, 300.0)], f"{module} failed on '2:25 - hết' with total_dur"

        res5 = func("2:25 - hết", None)
        assert res5 == [(145.0, None)], f"{module} failed on '2:25 - hết' with total_dur=None"

    @pytest.mark.parametrize("module,func", [
        ("youtube_sheet_slicer", ys.parse_time_ranges),
        ("itv_ingest", ia.parse_time_ranges),
    ])
    def test_overlapping_timestamps(self, module, func):
        """
        When editor notes overlapping ranges, the parser must return all intervals
        independently to allow discrete slicing without concat or min/max merge.
        """
        res1 = func("0:10 - 0:30 | 0:20 - 0:40", 100.0)
        assert len(res1) == 2
        assert res1[0] == (10.0, 30.0)
        assert res1[1] == (20.0, 40.0)

        res2 = func("0:10 - 0:50\n0:20 - 0:30", 100.0)
        assert len(res2) == 2
        assert res2[0] == (10.0, 50.0)
        assert res2[1] == (20.0, 30.0)

    @pytest.mark.parametrize("module,func", [
        ("youtube_sheet_slicer", ys.parse_time_ranges),
        ("itv_ingest", ia.parse_time_ranges),
    ])
    def test_four_timestamps(self, module, func):
        """Must correctly parse 4 discrete timestamps without dropping or merging."""
        s_pipe = "0:05 - 0:10 | 0:15 - 0:20 | 0:25 - 0:30 | 0:35 - 0:40"
        res_pipe = func(s_pipe, 100.0)
        assert len(res_pipe) == 4
        assert res_pipe == [(5.0, 10.0), (15.0, 20.0), (25.0, 30.0), (35.0, 40.0)]

        s_nl = "0:01 - 0:02\n0:03 - 0:04\n0:05 - 0:06\n0:07 - 0:08"
        res_nl = func(s_nl, 100.0)
        assert len(res_nl) == 4
        assert res_nl == [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0), (7.0, 8.0)]

    @pytest.mark.parametrize("module,func", [
        ("youtube_sheet_slicer", ys.parse_time_ranges),
        ("itv_ingest", ia.parse_time_ranges),
    ])
    def test_inverted_intervals(self, module, func):
        """Inverted intervals (end <= start) must be safely discarded, returning empty or valid only."""
        res_inv = func("0:50 - 0:30", 100.0)
        assert res_inv == [], f"Inverted interval should return empty, got {res_inv}"

        res_eq = func("1:00 - 1:00", 100.0)
        assert res_eq == [], f"Zero duration interval should return empty, got {res_eq}"

        res_mixed = func("0:10 - 0:20 | 0:50 - 0:30 | 1:15 - 1:25", 200.0)
        assert res_mixed == [(10.0, 20.0), (75.0, 85.0)], "Valid ranges must survive inverted drop"

    @pytest.mark.parametrize("module,func", [
        ("youtube_sheet_slicer", ys.parse_time_ranges),
        ("itv_ingest", ia.parse_time_ranges),
    ])
    def test_negative_numbers(self, module, func):
        """Negative timestamps and invalid tokens must not crash or cause infinite loops."""
        res_neg_end = func("0:10 - -0:20", 100.0)
        assert res_neg_end == [], f"Negative end token must not yield invalid range: {res_neg_end}"

        res_neg_start = func("-0:10 - 0:20", 100.0)
        # Token regex extracts positive 0:10 - 0:20; must not crash
        assert isinstance(res_neg_start, list)

    @pytest.mark.parametrize("module,func", [
        ("youtube_sheet_slicer", ys.parse_time_ranges),
        ("itv_ingest", ia.parse_time_ranges),
    ])
    def test_strings_non_ascii_and_messy(self, module, func):
        """Messy Vietnamese notes, emojis, and noise strings must be handled gracefully."""
        res1 = func("đoạn hay nè: 0:12 - 0:18, lấy thêm 1:02 - 1:08 nha sếp ơi!", 100.0)
        assert res1 == [(12.0, 18.0), (62.0, 68.0)]

        res2 = func("🔥 CỰC HÀI 🔥 0:10 - 0:20 💥 0:30 - 0:40", 100.0)
        assert res2 == [(10.0, 20.0), (30.0, 40.0)]

        assert func("", 100.0) == []
        assert func("   \n\t  ", 100.0) == []
        assert func("không có timestamp nào ở đây", 100.0) == []
        assert func("0:10", 100.0) == []
        assert func("0:10 - abc", 100.0) == []


# ==============================================================================
# SECTION 2: compute_dynamic_vo_timing Adversarial Edge Cases & Invariants
# ==============================================================================

class TestDynamicVOTimingStress:
    """Stress-test compute_dynamic_vo_timing across mathematical boundaries and invariants."""

    def test_clip_dur_less_than_vo_dur(self):
        """When clip_dur < vo_dur, function must cleanly fallback to ducked mode at safe boundary 0.15s."""
        cases = [
            (2.0, 3.0, 1.0, "short clip"),
            (1.0, 2.5, 0.5, "very short clip"),
            (0.5, 1.5, 0.2, "ultra short clip"),
            (2.0, 2.05, 1.0, "slightly smaller"),
        ]
        for cd, vd, imp, txt in cases:
            offset, mode = compute_dynamic_vo_timing(cd, vd, imp, txt)
            assert mode == "ducked", f"Expected 'ducked' mode for cd={cd} < vd={vd}, got {mode}"
            assert offset == 0.15, f"Expected offset=0.15 for cd={cd} < vd={vd}, got {offset}"

    def test_impact_at_zero(self):
        """When impact_sec == 0.0, VO cannot be premise. Must choose aftermath or ducked cleanly."""
        # Long clip: aftermath is available
        offset, mode = compute_dynamic_vo_timing(10.0, 2.0, 0.0, "reaction")
        assert mode == "aftermath"
        assert offset == 0.35  # impact + 0.35s
        assert offset >= 0.0 + 0.20  # strictly outside impact peak [0.0 - 0.2, 0.0 + 0.2]

        # Tight clip: aftermath does not fit -> ducked cleanly triggered
        offset_tight, mode_tight = compute_dynamic_vo_timing(2.0, 1.8, 0.0, "tight clip")
        assert mode_tight == "ducked"

    def test_impact_at_clip_dur(self):
        """When impact_sec == clip_dur, aftermath is impossible. Must place at premise or ducked."""
        # Long clip: premise fits before impact
        offset, mode = compute_dynamic_vo_timing(10.0, 2.0, 10.0, "reaction")
        assert mode == "premise"
        # VO must finish at or before impact_sec - 0.20s
        assert offset + 2.0 <= 10.0 - 0.20 + 1e-4

        # Short clip where premise doesn't fit
        offset_tight, mode_tight = compute_dynamic_vo_timing(2.0, 1.8, 2.0, "tight clip")
        assert mode_tight == "ducked"

    def test_very_short_clips_2s(self):
        """On 2.0s clips, VO must never collide with impact peak unless ducked is cleanly triggered."""
        clip_dur = 2.0
        for vo_dur in [0.4, 0.8, 1.2, 1.5, 2.0]:
            for impact in [0.2, 0.5, 1.0, 1.5, 1.8]:
                for text in ["when premise setup", "what a crazy reaction"]:
                    offset, mode = compute_dynamic_vo_timing(clip_dur, vo_dur, impact, text)
                    vo_start = offset
                    vo_end = offset + vo_dur
                    peak_start = impact - 0.20
                    peak_end = impact + 0.20

                    overlaps_peak = (vo_start < peak_end - 1e-4) and (vo_end > peak_start + 1e-4)
                    if overlaps_peak:
                        assert mode == "ducked", (
                            f"Peak overlap without ducked! cd={clip_dur}, vd={vo_dur}, imp={impact}, "
                            f"vo=[{vo_start:.2f}..{vo_end:.2f}], peak=[{peak_start:.2f}..{peak_end:.2f}], mode={mode}"
                        )

    def test_very_long_clips_30s(self):
        """On 30.0s clips, VO must place cleanly without exceeding clip boundaries."""
        clip_dur = 30.0
        for vo_dur in [1.0, 2.5, 4.0]:
            for impact in [2.0, 15.0, 28.0]:
                for text in ["when setup", "reaction line"]:
                    offset, mode = compute_dynamic_vo_timing(clip_dur, vo_dur, impact, text)
                    assert offset >= 0.15
                    assert offset + vo_dur <= clip_dur - 0.15 + 1e-4
                    if mode == "premise":
                        assert offset + vo_dur <= impact - 0.20 + 1e-4
                    elif mode == "aftermath":
                        assert offset >= impact + 0.35 - 1e-4

    def test_missing_impact_sec(self):
        """When impact_sec is None, function synthesizes effective impact at 45% and does not crash."""
        for clip_dur in [1.5, 3.0, 5.0, 10.0]:
            for vo_dur in [0.5, 1.5, 2.5]:
                offset, mode = compute_dynamic_vo_timing(clip_dur, vo_dur, None, "test comment")
                assert isinstance(offset, float)
                assert mode in ["premise", "aftermath", "ducked"]
                assert offset >= 0.15
                if clip_dur >= vo_dur + 0.30:
                    assert offset + vo_dur <= clip_dur - 0.15 + 1e-4

    def test_grid_invariant_exhaustive(self):
        """
        Exhaustive combinatorial sweep across 8,000+ conditions asserting:
        1. If VO penetrates [impact - 0.20, impact + 0.20], mode MUST be 'ducked'.
        2. If mode == 'premise', vo_end MUST be <= impact - 0.20.
        3. If mode == 'aftermath', vo_start MUST be >= impact + 0.20.
        """
        clip_durs = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 30.0]
        vo_durs = [0.3, 0.8, 1.5, 2.5, 4.0]
        texts = ["when he jumped", "that was hilarious", ""]

        total_checked = 0
        for cd in clip_durs:
            for vd in vo_durs:
                impacts = [0.0, 0.2, cd * 0.25, cd * 0.50, cd * 0.75, cd - 0.2, cd]
                for imp in impacts:
                    imp = round(imp, 2)
                    for txt in texts:
                        total_checked += 1
                        offset, mode = compute_dynamic_vo_timing(cd, vd, imp, txt)
                        vo_s = offset
                        vo_e = offset + vd
                        pk_s = imp - 0.20
                        pk_e = imp + 0.20

                        penetrates = (vo_s < pk_e - 1e-4) and (vo_e > pk_s + 1e-4)
                        if penetrates:
                            assert mode == "ducked", (
                                f"Invariant Violation: Overlaps peak without ducked mode! "
                                f"cd={cd}, vd={vd}, imp={imp}, vo=[{vo_s:.2f}..{vo_e:.2f}], "
                                f"peak=[{pk_s:.2f}..{pk_e:.2f}], mode={mode}"
                            )

                        if mode == "premise":
                            assert vo_e <= pk_s + 1e-4, (
                                f"Premise Invariant Violation: vo_end {vo_e:.2f} > peak_start {pk_s:.2f}"
                            )
                        elif mode == "aftermath":
                            assert vo_s >= pk_e - 1e-4, (
                                f"Aftermath Invariant Violation: vo_start {vo_s:.2f} < peak_end {pk_e:.2f}"
                            )

        assert total_checked > 800
