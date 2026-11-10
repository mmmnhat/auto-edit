import json
import os
import re
import subprocess
import sys
import numpy as np
from itv_vo_comment_generator import (
    KNOWN_IMPACTS,
    detect_audio_transient,
    compute_dynamic_vo_timing,
)

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"E:\ITV")
sys.path.insert(0, r"E:\.agents\skills\visioncut\scripts")
from tests.core.ground_truth_loader import GroundTruthLoader


def probe_dur(fpath):
    if not os.path.exists(fpath):
        return 0.0
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        fpath,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 0.0


def load_audio_np(fp):
    cmd = ["ffmpeg", "-v", "error", "-i", fp, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def main():
    whisper_model = None
    print("=== Task 4: Dynamic VO & Subtitle Artifact Generation (U-Shaped 3-Anchor + Real t_impact) ===")

    for pid in ["kb118", "kb119", "kb120", "kb121"]:
        print(f"\n==================== {pid} ====================")
        truth = GroundTruthLoader.load_project_truth(pid)
        voice_dir = os.path.join(truth.project_dir, "voice")
        p1_dir = os.path.join(truth.project_dir, "source")
        p2_dir_name = [d for d in os.listdir(truth.project_dir) if d.startswith("ITV-Moments-script-")][0]
        p2_dir = os.path.join(truth.project_dir, p2_dir_name)

        manifest_path = os.path.join(truth.project_dir, f"vo_subtitle_manifest_{pid}.json")
        cached_texts = {}
        if os.path.exists(manifest_path):
            try:
                old_m = json.load(open(manifest_path, encoding="utf-8"))
                for b in old_m.get("body_vos", []):
                    if b.get("vo_file") and b.get("vo_text"):
                        cached_texts[b["vo_file"]] = b["vo_text"]
            except Exception:
                pass

        vo_files = sorted([f for f in os.listdir(voice_dir) if re.search(r"vo\d{2}", f, re.I) and f.endswith(".mp3")])
        print(f"Found {len(vo_files)} body VO files in {pid}/voice")

        vo_artifacts = []
        offsets = []

        for f in vo_files:
            m = re.search(r"vo(\d{2})_(?:itv_[a-z0-9]+_(\d+)|(\d+))", f, re.I)
            if not m:
                continue
            vo_idx = int(m.group(1))
            p1_stt = int(m.group(2)) if m.group(2) else None
            p2_slot = int(m.group(3)) if m.group(3) else None

            if p1_stt:
                clip_name = f"itv.{pid}.{p1_stt}.mp4"
                clip_path = os.path.join(p1_dir, clip_name)
            else:
                alt_split_2 = os.path.join(p2_dir, f"{p2_slot:02d}_2.mp4")
                raw_clip = os.path.join(p2_dir, f"{p2_slot:02d}.mp4")
                if os.path.exists(alt_split_2):
                    clip_name = f"{p2_slot:02d}_2.mp4"
                    clip_path = alt_split_2
                elif os.path.exists(raw_clip):
                    clip_name = f"{p2_slot:02d}.mp4"
                    clip_path = raw_clip
                else:
                    alt_name = f"{p2_slot}.mp4"
                    clip_path = os.path.join(p2_dir, alt_name)
                    clip_name = alt_name

            vo_path = os.path.join(voice_dir, f)
            vo_dur = probe_dur(vo_path)
            clip_dur = probe_dur(clip_path)

            if f in cached_texts:
                vo_text = cached_texts[f]
            else:
                if whisper_model is None:
                    from faster_whisper import WhisperModel
                    whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
                audio_np = load_audio_np(vo_path)
                segments, _ = whisper_model.transcribe(audio_np)
                vo_text = " ".join(s.text.strip() for s in segments)

            impact_sec = KNOWN_IMPACTS.get(clip_name, detect_audio_transient(clip_path, in_sec=0.0, clip_dur=clip_dur))
            offset_sec, mode = compute_dynamic_vo_timing(clip_dur, vo_dur, impact_sec, vo_text)
            offsets.append(offset_sec)

            vo_end_offset = round(offset_sec + vo_dur, 3)

            v5_mogrt = {
                "text": vo_text,
                "start_offset_sec": offset_sec,
                "end_offset_sec": vo_end_offset,
                "duration_sec": round(vo_dur, 3),
                "mogrt_template": "Essential Graphics ITV Subtitle",
            }

            item_entry = {
                "vo_index": vo_idx,
                "vo_file": f,
                "vo_text": vo_text,
                "vo_duration_sec": round(vo_dur, 3),
                "parent_clip": clip_name,
                "parent_clip_duration_sec": round(clip_dur, 3),
                "impact_sec": impact_sec,
                "placement_mode": mode,
                "placement_role": mode,
                "vo_start_offset_sec": offset_sec,
                "vo_end_offset_sec": vo_end_offset,
                "v5_subtitle_sync": v5_mogrt,
            }
            vo_artifacts.append(item_entry)
            print(
                f"  VO #{vo_idx:02d} [{mode:9s}]: offset={offset_sec:5.2f}s..{vo_end_offset:5.2f}s "
                f"(impact={impact_sec:5.2f}s, dur={vo_dur:4.2f}s, parent={clip_name} {clip_dur:.2f}s) | '{vo_text[:40]}...'"
            )

        fixed_1_5s = [off for off in offsets if abs(off - 1.50) < 0.06]
        variance = float(np.var(offsets)) if len(offsets) > 1 else 0.0
        print(f"  -> Fixed 1.50s count: {len(fixed_1_5s)}/{len(offsets)} (requirement <= 3)")
        print(f"  -> Offset variance: {variance:.3f} s^2 (requirement > 0.35)")
        assert len(fixed_1_5s) <= 3, f"Too many fixed 1.5s offsets: {len(fixed_1_5s)}"
        assert variance > 0.35, f"Variance too low: {variance}"

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "project": pid,
                    "placement_preset": "u_shaped_3anchor_vo_placement",
                    "total_body_vos": len(vo_artifacts),
                    "offset_variance": round(variance, 3),
                    "fixed_1_5s_count": len(fixed_1_5s),
                    "body_vos": vo_artifacts,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        print(f"  ✓ Saved {os.path.basename(manifest_path)}")

    print("\nDynamic VO & Subtitle Artifact Generation Complete!")


if __name__ == "__main__":
    main()
