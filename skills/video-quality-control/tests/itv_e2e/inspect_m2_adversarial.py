"""
Independent Adversarial Inspection Script for Milestone 2
Challenger 1
"""
import csv
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"E:\ITV")

from tests.core.ground_truth_loader import GroundTruthLoader
from tests.core.timeline_math import parse_note_specification, parse_time_range, parse_time_str_to_sec


def probe_dur(fpath: str) -> float:
    if not os.path.exists(fpath):
        return 0.0
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        fpath,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 0.0


def parse_target_dur(note: str, raw_dur: float | None = None):
    if not note or not note.strip():
        return None
    cleaned = note.strip().lower()

    # 1. head_n_sec: '6s đầu', '13S ĐẦU'
    m_head = re.search(r"(\d+(?:\.\d+)?)\s*(?:s|giây)?\s*đầu", cleaned)
    if m_head:
        dur = float(m_head.group(1))
        return {"expected_dur": dur, "rule": "head_n_sec"}

    # 2. tail_from_n_sec: '5 về sau', '3 về sau'
    m_tail = re.search(r"(\d+(?:\.\d+)?)\s*(?:về sau|tới hết|đến hết)", cleaned)
    if m_tail:
        st = float(m_tail.group(1))
        if raw_dur and raw_dur > st:
            return {"expected_dur": raw_dur - st, "rule": "tail_from_n_sec"}

    # 3. Explicit mm:ss - mm:ss: '3:02 - 3:17', '0:04 - 0:16'
    m_ts = re.search(r"(\d+[:.]\d+)\s*-\s*(\d+[:.]\d+)", cleaned)
    if m_ts:
        st = parse_time_str_to_sec(m_ts.group(1))
        en = parse_time_str_to_sec(m_ts.group(2))
        if st is not None and en is not None and en > st:
            return {"expected_dur": en - st, "rule": "explicit_range"}

    # 4. Integer range: '10 - 24', '0 tới 14', '8 - 18, crop...'
    m_int = re.match(r"^(\d+(?:\.\d+)?)\s*(?:-|tới|toi|to)\s*(\d+(?:\.\d+)?)(?:,\s*.*)?$", cleaned)
    if m_int:
        st = float(m_int.group(1))
        en = float(m_int.group(2))
        if en > st:
            return {"expected_dur": en - st, "rule": "int_range"}

    return None


def run_all_checks():
    projects = ["kb118", "kb119", "kb120", "kb121"]
    summary = {}

    for pid in projects:
        print(f"\n=======================================================")
        print(f"               INSPECTING PROJECT {pid}")
        print(f"=======================================================")
        summary[pid] = {
            "p1_inpoint_errors": [],
            "p1_duration_mismatches": [],
            "p2_note_matches": [],
            "p2_note_mismatches": [],
            "p2_non_note_truncated": [],
            "manifest_vs_disk_mismatches": [],
            "unhandled_notes": [],
        }

        truth = GroundTruthLoader.load_project_truth(pid)
        manifest_path = os.path.join(truth.project_dir, f"{pid}_manifest.json")
        if not os.path.exists(manifest_path):
            print(f"ERROR: Missing manifest {manifest_path}")
            continue

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        clips = manifest_data.get("clips", [])
        p1_clips = [c for c in clips if c.get("section") == "part1"]
        p2_clips = [c for c in clips if c.get("section") == "part2"]
        p2_clips_by_slot = {}
        for c in p2_clips:
            p2_clips_by_slot.setdefault(c.get("slot_num"), []).append(c)

        # ---------------------------------------------------------
        # Check A: Manifest InPoint and Manifest vs Disk Sync
        # ---------------------------------------------------------
        print(f"\n--- Check A: Manifest vs Disk & InPoint Verification ---")
        for c in clips:
            cname = c.get("clip_name")
            inp = c.get("in_point_sec")
            outp = c.get("out_point_sec")
            mdur = c.get("duration_sec")
            spath = c.get("source_path")
            ddur = probe_dur(spath)

            if inp != 0.0:
                summary[pid]["p1_inpoint_errors"].append(f"{cname}: in_point={inp}")

            if abs(outp - mdur) > 0.05:
                summary[pid]["p1_inpoint_errors"].append(f"{cname}: out_point({outp}) != dur({mdur})")

            if abs(mdur - ddur) > 0.15:
                summary[pid]["manifest_vs_disk_mismatches"].append(
                    f"{cname}: manifest_dur={mdur:.3f}s != disk_dur={ddur:.3f}s (diff={abs(mdur-ddur):.3f}s)"
                )

        print(f"Total clips in manifest: {len(clips)}")
        print(f"InPoint != 0 errors: {len(summary[pid]['p1_inpoint_errors'])}")
        print(f"Manifest vs Disk mismatches (>0.15s): {len(summary[pid]['manifest_vs_disk_mismatches'])}")

        # ---------------------------------------------------------
        # Check B: Part 1 Sheet Durations
        # ---------------------------------------------------------
        print(f"\n--- Check B: Part 1 Sheet Durations ---")
        # Load Sheet CSV with STT mapping
        with open(truth.sheet_csv_path, "r", encoding="utf-8", errors="replace") as f:
            sheet_rows = list(csv.reader(f))

        stt_to_sheet = {}
        row_sheet_ranges = []
        for r_idx, r in enumerate(sheet_rows[1:], 1):
            desc = r[1] if len(r) > 1 else ""
            link = r[2] if len(r) > 2 else ""
            tstr = r[3].strip() if len(r) > 3 else ""
            tclean = tstr.replace(";", ":")
            rng = parse_time_range(tclean)
            stt_val = r[5].strip() if len(r) > 5 else ""
            if stt_val.isdigit():
                stt_to_sheet[int(stt_val)] = (tclean, rng, desc, link)
            if rng:
                row_sheet_ranges.append((r_idx, tclean, rng, desc, link))

        for c in p1_clips:
            cname = c["clip_name"]
            mdur = c["duration_sec"]
            # Extract index from itv.{pid}.{idx}.mp4
            m = re.match(rf"itv\.{pid}\.(\d+)\.mp4", cname)
            if not m:
                continue
            idx = int(m.group(1))

            # Try STT mapping first, then sequential row mapping
            target_info = stt_to_sheet.get(idx)
            if not target_info and idx <= len(row_sheet_ranges):
                target_info = row_sheet_ranges[idx - 1][1:]

            if target_info and target_info[1]:
                sheet_tstr = target_info[0]
                sheet_dur = target_info[1][1] - target_info[1][0]
                diff = abs(mdur - sheet_dur)
                # Tolerance +-0.30s transition snap per cut (start & end) = 0.60s max
                if diff > 0.60:
                    summary[pid]["p1_duration_mismatches"].append(
                        f"{cname}: sheet={sheet_tstr} ({sheet_dur:.2f}s), manifest={mdur:.2f}s, diff={diff:.2f}s"
                    )
                else:
                    # Snapped within tolerance
                    pass
            else:
                summary[pid]["p1_duration_mismatches"].append(
                    f"{cname}: No valid sheet range found"
                )

        print(f"Part 1 clips: {len(p1_clips)}")
        print(f"Part 1 Duration mismatches (>0.60s snap): {len(summary[pid]['p1_duration_mismatches'])}")
        for mm in summary[pid]["p1_duration_mismatches"][:5]:
            print(f"  ❌ {mm}")

        # ---------------------------------------------------------
        # Check C: Part 2 Note Durations
        # ---------------------------------------------------------
        print(f"\n--- Check C: Part 2 Note Durations ---")
        with open(truth.amz_json_path, "r", encoding="utf-8") as f:
            amz_data = json.load(f)
        amz_items = amz_data.get("items") or amz_data.get("data", {}).get("footages", [])

        for it in amz_items:
            order = it.get("sortOrder")
            note = (it.get("note") or "").strip()
            ft = it.get("footage") or {}
            raw_dur = ft.get("duration")

            # Check if this note has explicit duration instructions
            target = parse_target_dur(note, raw_dur)
            if not target:
                # Check for unhandled patterns
                cleaned = note.lower()
                if any(k in cleaned for k in ["s đầu", "giây đầu", "về sau", "tới hết", " - "]) and not any(k in cleaned for k in ["2 sr", "2 source", "lấy cmt", "vài s", "mấy s"]):
                    summary[pid]["unhandled_notes"].append(f"Slot {order:02d}: note='{note}'")
                continue

            exp_dur = target["expected_dur"]
            m_clips = p2_clips_by_slot.get(order, [])
            if not m_clips:
                summary[pid]["p2_note_mismatches"].append(
                    f"Slot {order:02d} '{note}': clip not found in manifest"
                )
                continue

            actual_dur = m_clips[0]["duration_sec"]
            diff = abs(actual_dur - exp_dur)
            if diff > 0.35:
                summary[pid]["p2_note_mismatches"].append(
                    f"Slot {order:02d} '{note}': expected={exp_dur:.2f}s, manifest={actual_dur:.2f}s, diff={diff:.2f}s"
                )
            else:
                summary[pid]["p2_note_matches"].append(
                    f"Slot {order:02d} '{note}': expected={exp_dur:.2f}s, actual={actual_dur:.2f}s"
                )

        print(f"Part 2 note clips matching 100%: {len(summary[pid]['p2_note_matches'])}")
        print(f"Part 2 note duration mismatches: {len(summary[pid]['p2_note_mismatches'])}")
        for mm in summary[pid]["p2_note_mismatches"]:
            print(f"  ❌ {mm}")

        # ---------------------------------------------------------
        # Check D: Part 2 Non-Note Clips Truncation
        # ---------------------------------------------------------
        print(f"\n--- Check D: Part 2 Non-Note Clips (No 5.5s-6.2s Truncation) ---")
        for it in amz_items:
            order = it.get("sortOrder")
            note = (it.get("note") or "").strip()
            ft = it.get("footage") or {}
            raw_dur = ft.get("duration")

            target = parse_target_dur(note, raw_dur)
            if target:
                continue  # This is a note clip

            # Check if this is a multi-timestamp split slot
            m_clips = p2_clips_by_slot.get(order, [])
            if not m_clips:
                continue

            # Check if any non-note clip was truncated to 5.5s..6.2s
            for mc in m_clips:
                mdur = mc["duration_sec"]
                cname = mc["clip_name"]
                spath = mc["source_path"]

                # If raw_dur exists and is significantly larger (>7.0s)
                # Or if .orig.mp4 exists with larger duration
                orig_path = spath + ".orig.mp4"
                check_raw_dur = raw_dur
                if os.path.exists(orig_path):
                    orig_probe = probe_dur(orig_path)
                    if orig_probe > (check_raw_dur or 0.0):
                        check_raw_dur = orig_probe

                if check_raw_dur and check_raw_dur > 7.0:
                    cut_amount = check_raw_dur - mdur
                    if cut_amount > 1.0 and (5.4 <= mdur <= 6.3):
                        summary[pid]["p2_non_note_truncated"].append(
                            f"Slot {order:02d} {cname} (note='{note}'): raw={check_raw_dur:.2f}s, manifest={mdur:.2f}s, capped to ~5.6s"
                        )

        print(f"Part 2 non-note truncated clips: {len(summary[pid]['p2_non_note_truncated'])}")
        for tr in summary[pid]["p2_non_note_truncated"]:
            print(f"  ❌ {tr}")

    return summary


if __name__ == "__main__":
    run_all_checks()
