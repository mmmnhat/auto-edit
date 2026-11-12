"""
Milestone 1 Iteration 2 Challenger 1 Test Suite
Adversarial Verification of:
1. parse_time_ranges edge cases and real editor note support
2. Module import robustness in clean subshells
3. slice_amz_part2_clips execution and shutil dependency
4. ffmpeg fallback index safety in download_and_slice_sheet_part1
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
import pytest

VC_DIR = r"E:\.agents\skills\visioncut\scripts"
YS_DIR = r"E:\ITV\youtube_source_cutter\scripts"

if VC_DIR not in sys.path:
    sys.path.insert(0, VC_DIR)
if YS_DIR not in sys.path:
    sys.path.insert(0, YS_DIR)

import itv_ingest_from_sheet_and_amz as ingest
import youtube_sheet_slicer as slicer


def test_clean_subshell_imports():
    """All 4 modules must import cleanly in isolated subshells."""
    modules = [
        ("itv_10track_finisher", VC_DIR),
        ("itv_ingest_from_sheet_and_amz", VC_DIR),
        ("youtube_sheet_slicer", YS_DIR),
        ("itv_vo_comment_generator", VC_DIR),
    ]
    for mod_name, mod_path in modules:
        code = f"import sys; sys.path.insert(0, r'{mod_path}'); import {mod_name}; print('{mod_name} OK')"
        res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert res.returncode == 0, f"Import of {mod_name} failed: {res.stderr}"
        assert f"{mod_name} OK" in res.stdout


def test_slice_amz_part2_clips_execution():
    """slice_amz_part2_clips must execute with 0 NameError and create proper backups and sliced files."""
    temp_dir = tempfile.mkdtemp(prefix="test_slice_amz_")
    try:
        # Create a 4.0s dummy clip
        dummy_mp4 = os.path.join(temp_dir, "raw.mp4")
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=4:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=duration=4",
            "-c:v", "libx264", "-c:a", "aac",
            dummy_mp4,
        ]
        subprocess.run(cmd, check=True)

        # Slot 1: single note, Slot 2: multi note, Slot 3: no note
        f1 = os.path.join(temp_dir, "01.mp4")
        f2 = os.path.join(temp_dir, "02.mp4")
        f3 = os.path.join(temp_dir, "03.mp4")
        shutil.copy2(dummy_mp4, f1)
        shutil.copy2(dummy_mp4, f2)
        shutil.copy2(dummy_mp4, f3)

        data = {
            "items": [
                {"sortOrder": "1", "note": "0:01 - 0:03"},
                {"sortOrder": "2", "note": "0:00 - 0:01\n0:02 - 0:03"},
                {"sortOrder": "3", "note": ""},
            ]
        }
        json_path = os.path.join(temp_dir, "script.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        ingest.slice_amz_part2_clips(json_path, temp_dir)

        # Verify backups
        assert os.path.exists(os.path.join(temp_dir, "01.orig.mp4")), "Missing 01.orig.mp4"
        assert os.path.exists(os.path.join(temp_dir, "01.mp4.orig.mp4")), "Missing 01.mp4.orig.mp4"
        assert os.path.exists(os.path.join(temp_dir, "02_1.mp4")), "Missing 02_1.mp4"
        assert os.path.exists(os.path.join(temp_dir, "02_2.mp4")), "Missing 02_2.mp4"

        def get_dur(p):
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", p],
                capture_output=True, text=True,
            )
            return float(r.stdout.strip())

        assert 1.8 <= get_dur(f1) <= 2.2, f"Expected ~2.0s, got {get_dur(f1)}"
        assert 0.8 <= get_dur(os.path.join(temp_dir, "02_1.mp4")) <= 1.2
        assert 0.8 <= get_dur(os.path.join(temp_dir, "02_2.mp4")) <= 1.2
        assert 3.8 <= get_dur(f3) <= 4.2, f"Slot 3 should remain untrimmed at ~4.0s, got {get_dur(f3)}"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_parse_time_ranges_unicode_dashes():
    """parse_time_ranges should support unicode en-dash and em-dash."""
    dash_en = "0:33 – 0:40"  # en-dash U+2013
    dash_em = "0:33 — 0:40"  # em-dash U+2014

    r_en_ingest = ingest.parse_time_ranges(dash_en, 60.0)
    r_em_ingest = ingest.parse_time_ranges(dash_em, 60.0)
    r_en_slicer = slicer.parse_time_ranges(dash_en, 60.0)
    r_em_slicer = slicer.parse_time_ranges(dash_em, 60.0)

    # Document empirical behavior
    assert r_en_ingest == [(33.0, 40.0)], f"En-dash failed on ingest: {r_en_ingest}"
    assert r_en_slicer == [(33.0, 40.0)], f"En-dash failed on slicer: {r_en_slicer}"
    assert r_em_ingest == [(33.0, 40.0)], f"Em-dash failed on ingest: {r_em_ingest}"
    assert r_em_slicer == [(33.0, 40.0)], f"Em-dash failed on slicer: {r_em_slicer}"


def test_parse_time_ranges_integer_seconds():
    """parse_time_ranges should parse pure integer second notes used in kb118..kb121."""
    cases = [
        ("10 - 18", 60.0, [(10.0, 18.0)]),
        ("5 - 16", 60.0, [(5.0, 16.0)]),
        ("0 tới 14", 60.0, [(0.0, 14.0)]),
        ("12 tới 22", 60.0, [(12.0, 22.0)]),
        ("5 về sau", 60.0, [(5.0, 60.0)]),
    ]
    for note, dur, expected in cases:
        r_ingest = ingest.parse_time_ranges(note, dur)
        r_slicer = slicer.parse_time_ranges(note, dur)
        assert r_ingest == expected, f"Integer note '{note}' failed on ingest: got {r_ingest}, expected {expected}"
        assert r_slicer == expected, f"Integer note '{note}' failed on slicer: got {r_slicer}, expected {expected}"


def test_download_and_slice_sheet_part1_fallback_bug():
    """
    In itv_ingest_from_sheet_and_amz.py line 369:
    ff_cmd[9] = 'libx264' overwrites the duration parameter -t instead of -c:v,
    corrupting the ffmpeg command.
    """
    with open(os.path.join(VC_DIR, "itv_ingest_from_sheet_and_amz.py"), encoding="utf-8") as f:
        content = f.read()
    assert "ff_cmd[9] = \"libx264\"" not in content, (
        "Fatal Bug: line 369 still uses hardcoded ff_cmd[9] = 'libx264', which mutates '-t' instead of '-c:v'!"
    )


if __name__ == "__main__":
    pytest.main(["-v", __file__])
