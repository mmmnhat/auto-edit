import os
import re
import sys
import csv
import gzip
import json
import time
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
import numpy as np
from PIL import Image, ImageDraw
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\2dfbcc6d-f671-49d0-93b6-6523695e0ca2\scratch")
sys.path.insert(0, r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\f0297a3b-b356-40ae-9784-0a64bcbc74d4\scratch")

from step3_build_aw1_4_videos import slice_aw1_clip_worker
from step3_build_aw234_videos import bpe, base, generate_fcp_xml
from execute_clean_dedup_all_16 import interleave_selected_clips
from build_all_16_animal_whoops_rules import (
    DONOR_1506_SAFE,
    INTRO_CONCAT_MP4,
    screen_15_and_select_3_hooks,
    compile_animal_whoops_episode,
)

POOL_JSON = r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\f0297a3b-b356-40ae-9784-0a64bcbc74d4\scratch\master_clean_pool_final.json"
STAGE_DIR = r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\f0297a3b-b356-40ae-9784-0a64bcbc74d4\scratch\_aw234_stage"

EPISODES_12 = [
    ("aw2", "aw2_1", "21", 2, 1),
    ("aw2", "aw2_2", "22", 2, 2),
    ("aw2", "aw2_3", "23", 2, 3),
    ("aw2", "aw2_4", "24", 2, 4),
    ("aw3", "aw3_1", "31", 3, 1),
    ("aw3", "aw3_2", "32", 3, 2),
    ("aw3", "aw3_3", "33", 3, 3),
    ("aw3", "aw3_4", "34", 3, 4),
    ("aw4", "aw4_1", "41", 4, 1),
    ("aw4", "aw4_2", "42", 4, 2),
    ("aw4", "aw4_3", "43", 4, 3),
    ("aw4", "aw4_4", "44", 4, 4),
]


def harvest_existing_encoded_slices(pool_scenes: list[dict]):
    """
    Before cleaning E:\\Animal Whoops\\aw2..aw4\\aw*_*\\source, harvest any already-encoded .mp4 clip
    whose (vcode, start_mmss, dur_sec) matches a scene in `pool_scenes`.
    """
    os.makedirs(STAGE_DIR, exist_ok=True)
    # Build lookup index by vcode -> list of pool scenes
    by_vc = {}
    for sc in pool_scenes:
        by_vc.setdefault(sc["vcode"], []).append(sc)

    reused_cnt = 0
    for b, ep, ep_num, _, _ in EPISODES_12:
        pdir = rf"E:\Animal Whoops\{b}\{ep}"
        csv_p = os.path.join(pdir, f"sheet_KB{ep_num}.csv")
        plan_p = os.path.join(pdir, f"{ep}_premiere_mcp_plan.json")
        if not os.path.exists(csv_p) or not os.path.exists(plan_p):
            continue
        rows = list(csv.reader(open(csv_p, encoding="utf-8")))[1:]
        pl = json.load(open(plan_p, encoding="utf-8"))
        body_clips = [c for c in pl.get("clips", []) if c.get("role") == "body"]
        if len(rows) != len(body_clips):
            continue
        for r, bc in zip(rows, body_clips):
            fp = bc["path"]
            if not os.path.exists(fp) or os.path.getsize(fp) < 30_000:
                continue
            vc = r[2].split("v=")[-1].strip()
            m = re.match(r"(\d+):(\d+)\s*-\s*(\d+):(\d+)", r[3].strip())
            if not m:
                continue
            st_mmss = int(m.group(1)) * 60 + int(m.group(2))
            dur_c = float(bc["dur_sec"])
            for sc in by_vc.get(vc, []):
                if "stage_path" in sc and os.path.exists(sc["stage_path"]):
                    continue
                if abs(int(sc["bat_dau"]) - st_mmss) <= 1 and abs(float(sc["dur"]) - dur_c) <= 0.06:
                    st_p = os.path.join(STAGE_DIR, f"uid_{sc['uid']}.mp4")
                    if not os.path.exists(st_p):
                        shutil.copy2(fp, st_p)
                    sc["stage_path"] = st_p
                    reused_cnt += 1
                    break
    print(f"Harvested {reused_cnt}/{len(pool_scenes)} already-encoded CFR 1080p slices from disk.", flush=True)


def render_storyboard(ep_id: str, mp4_p: str, sb_out: str):
    probe = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", mp4_p],
        text=True,
    ).strip()
    dur_s = float(probe or 900.0)
    cap = cv2.VideoCapture(mp4_p)
    cols, rows = 4, 3
    tw, th = 480, 270
    canvas = Image.new("RGB", (cols * tw, rows * th + 44), (18, 18, 22))
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (14, 10),
        f"{ep_id}.mp4 — Animal Whoops Verification ({int(dur_s//60)}m{int(dur_s%60):02d}s, CFR 23.976fps, 0 Cross-Episode Reuse)",
        fill=(255, 230, 90),
    )
    sample_times = [round(dur_s * (k + 0.5) / 12.0, 1) for k in range(12)]
    for idx, t_sec in enumerate(sample_times):
        cap.set(cv2.CAP_PROP_POS_MSEC, t_sec * 1000.0)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        rgb = cv2.cvtColor(cv2.resize(frame, (tw, th)), cv2.COLOR_BGR2RGB)
        pil_im = Image.fromarray(rgb)
        d_im = ImageDraw.Draw(pil_im)
        mm = int(t_sec // 60)
        ss = int(t_sec % 60)
        d_im.rectangle([6, 6, 220, 32], fill=(0, 0, 0))
        d_im.text((10, 10), f"{mm:02d}:{ss:02d} | {ep_id}", fill=(80, 255, 120))
        c = idx % cols
        r = idx // cols
        canvas.paste(pil_im, (c * tw, 44 + r * th))
    cap.release()
    os.makedirs(os.path.dirname(sb_out), exist_ok=True)
    canvas.save(sb_out, quality=88)


def main():
    t0 = time.time()
    pool_data = json.load(open(POOL_JSON, encoding="utf-8"))
    pool_scenes = pool_data["scenes"]
    print(f"Loaded {len(pool_scenes)} globally deduplicated scenes ({pool_data['total_dur']/60:.1f}m) from {POOL_JSON}", flush=True)

    # 1. Partition scenes across the 12 episodes using snake-draft per vcode so every episode gets:
    #    - 0 shared/reused scenes (strict 1-to-1 assignment)
    #    - Balanced duration and clip count
    #    - Balanced diversity of vcodes (0 SameLinkAdj)
    by_vc = {}
    for sc in pool_scenes:
        by_vc.setdefault(sc["vcode"], []).append(sc)
    for vc in by_vc:
        by_vc[vc].sort(key=lambda x: -float(x["st"]["center_lap"]))

    ep_buckets = [[] for _ in range(12)]
    ep_durs = [0.0 for _ in range(12)]

    # Flatten scenes in snake order across vcodes (largest vcode pools first)
    vc_order = sorted(by_vc.keys(), key=lambda k: -len(by_vc[k]))
    max_len = max(len(v) for v in by_vc.values())
    round_scenes = []
    for r_i in range(max_len):
        for vc in vc_order:
            if r_i < len(by_vc[vc]):
                round_scenes.append(by_vc[vc][r_i])

    # Assign each scene to the episode with the lowest current duration (that doesn't exceed target cap)
    target_cap = 1005.0
    for sc in round_scenes:
        # Pick the episode among 0..11 with minimum current duration (and fewer clips as tie-breaker)
        cand_eps = [e_i for e_i in range(12) if ep_durs[e_i] < target_cap]
        if not cand_eps:
            break
        best_e = min(cand_eps, key=lambda e_i: (len(ep_buckets[e_i]) // 15, ep_durs[e_i]))
        ep_buckets[best_e].append(sc)
        ep_durs[best_e] += float(sc["dur"])

    selected_all = [sc for bkt in ep_buckets for sc in bkt]
    print(f"Assigned {len(selected_all)} unique scenes across 12 episodes (0 reuse):", flush=True)
    for e_i, (_, ep, _, _, _) in enumerate(EPISODES_12):
        raw_d = ep_durs[e_i]
        tl_d = raw_d / 1.06 + 20.5
        print(f"  {ep}: {len(ep_buckets[e_i])} scenes, raw={raw_d:.1f}s -> est_timeline={tl_d:.1f}s ({tl_d/60:.2f}m)", flush=True)

    # 2. Harvest already-encoded slices from disk, then encode only the missing slices
    harvest_existing_encoded_slices(selected_all)

    to_encode = []
    for sc in selected_all:
        st_p = os.path.join(STAGE_DIR, f"uid_{sc['uid']}.mp4")
        sc["stage_path"] = st_p
        if not os.path.exists(st_p) or os.path.getsize(st_p) < 30_000:
            to_encode.append({
                "key": sc["uid"],
                "src_mp4": sc["file"],
                "out_mp4": st_p,
                "st": sc["bat_dau"],
                "dur": sc["dur"],
                "crop_lr_pct": sc["crop_lr_pct"],
            })

    print(f"Encoding {len(to_encode)} new CFR 1080p slices across 12 workers...", flush=True)
    t_enc = time.time()
    if to_encode:
        done_enc = 0
        with ThreadPoolExecutor(max_workers=12) as ex:
            futs = [ex.submit(slice_aw1_clip_worker, task) for task in to_encode]
            for fut in as_completed(futs):
                fut.result()
                done_enc += 1
                if done_enc % 50 == 0 or done_enc == len(to_encode):
                    print(f"  [Encoded] {done_enc}/{len(to_encode)} slices ({time.time()-t_enc:.1f}s)", flush=True)

    # 3. Load donor template once and compile all 12 episodes
    donor_root, donor_id, donor_uid = bpe.load_xml(DONOR_1506_SAFE)
    donor_bh = {}
    for e in donor_root.iter():
        bh = e.attrib.get("BinaryHash")
        if bh and (e.text or "").strip():
            donor_bh[bh] = e.text

    for e_i, (b, ep, ep_num, b_idx, i_idx) in enumerate(EPISODES_12):
        ep_t0 = time.time()
        ordered_clips = interleave_selected_clips([dict(x) for x in ep_buckets[e_i]])
        same_adj = sum(1 for k in range(len(ordered_clips) - 1) if ordered_clips[k]["vcode"] == ordered_clips[k + 1]["vcode"])

        pdir = rf"E:\Animal Whoops\{b}\{ep}"
        src_dir = os.path.join(pdir, "source")
        vid_dir = rf"E:\Animal Whoops\{b}\VIDEO"
        verify_dir = rf"E:\Animal Whoops\{b}\state\verify"
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(vid_dir, exist_ok=True)
        os.makedirs(verify_dir, exist_ok=True)

        # Clean old mp4s in source_dir
        for fn in os.listdir(src_dir):
            if fn.lower().endswith(".mp4"):
                try:
                    os.remove(os.path.join(src_dir, fn))
                except OSError:
                    pass

        body_specs = []
        sheet_rows_csv = [["", "nội dung", "link", "time", "check", "stt", "cre", "cmt"]]
        amz_footages = []

        for idx_c, sc in enumerate(ordered_clips, start=1):
            uid = sc["uid"]
            fname = f"{ep}.{idx_c}_f{uid}.mp4"
            out_mp4 = os.path.join(src_dir, fname)
            shutil.copy2(sc["stage_path"], out_mp4)
            sc["sid"] = uid
            sc["final_name"] = fname
            sc["final_path"] = out_mp4

            t_str = f"{base.fmt_mmss(sc['bat_dau'])} - {base.fmt_mmss(sc['bat_dau'] + sc['dur'])}"
            sheet_rows_csv.append(["", sc["desc"], sc["url"], t_str, "TRUE", str(idx_c), sc["chan"], ""])
            amz_footages.append({
                "sortOrder": idx_c,
                "note": "",
                "footage": {
                    "id": uid,
                    "title": sc["desc"],
                    "channel": sc["chan"],
                    "sourceUrl": sc["url"],
                },
            })
            body_specs.append({
                "id": f"body_{idx_c:03d}",
                "name": fname,
                "path": out_mp4,
                "in_sec": 0.0,
                "dur_sec": sc["dur"],
                "crop_lr_pct": sc["crop_lr_pct"],
                "v2_crop_pct": sc["v2_crop_pct"],
                "url": sc["url"],
                "chan": sc["chan"],
                "desc": sc["desc"],
                "hint_meta": {"w": 1920, "h": 1080, "dur_sec": sc["file_dur"], "has_audio": True},
            })

        screened_15, selected_3 = screen_15_and_select_3_hooks(ordered_clips)
        hook_specs = []
        for h_i, hsc in enumerate(selected_3, start=1):
            full_dur = float(hsc["dur"])
            if full_dur <= 5.4:
                h_in_sec = 0.0
                h_dur_sec = full_dur
            else:
                h_dur_sec = 5.0
                h_in_sec = round(min(1.2, max(0.2, (full_dur - h_dur_sec) * 0.35)), 2)
            hook_specs.append({
                "id": f"hook_{h_i:02d}",
                "name": hsc["final_name"],
                "path": hsc["final_path"],
                "in_sec": h_in_sec,
                "dur_sec": h_dur_sec,
                "crop_lr_pct": hsc["crop_lr_pct"],
                "v2_crop_pct": hsc["v2_crop_pct"],
                "body_pos": hsc["body_pos"],
                "sid": hsc["sid"],
                "hook_score": hsc["hook_score"],
                "hint_meta": {"w": 1920, "h": 1080, "dur_sec": hsc["file_dur"], "has_audio": True},
            })

        sfx_specs = []
        for sfx_i, b_idx_sfx in enumerate(range(5, len(body_specs) - 3, 10)):
            bspec = body_specs[b_idx_sfx]
            cdur = bspec["dur_sec"] / 1.06
            s_pool = base.FOLEY_POOL if (sfx_i % 2 == 0) else base.IMPACT_POOL
            s_name = s_pool[(b_idx + i_idx + sfx_i) % len(s_pool)]
            s_path, pk_off = base.get_sfx(s_name)
            tr_num = 2 if (sfx_i % 2 == 0) else 3
            t_imp = round(min(max(0.8, cdur * 0.48), cdur - 0.5), 2)
            sfx_specs.append({
                "clip_id": bspec["id"],
                "track": tr_num,
                "path": s_path,
                "impact_offset_sec": t_imp,
                "peak_offset_sec": pk_off,
            })

        csv_path = os.path.join(pdir, f"sheet_KB{ep_num}.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as fp:
            csv.writer(fp).writerows(sheet_rows_csv)

        json_path = os.path.join(pdir, f"{ep}_s{ep_num}.json")
        with open(json_path, "w", encoding="utf-8") as fp:
            json.dump({"data": {"footages": amz_footages, "screened_15_hook_candidates": [x["final_name"] for x in screened_15], "selected_3_hooks": [x["final_name"] for x in selected_3]}}, fp, indent=2, ensure_ascii=False)

        out_prproj = os.path.join(pdir, f"{ep}.prproj")
        out_plan = os.path.join(pdir, f"{ep}_premiere_mcp_plan.json")
        mcp_plan = compile_animal_whoops_episode(
            ep, hook_specs, body_specs, sfx_specs,
            donor_root, donor_id, donor_uid, donor_bh,
            out_prproj, out_plan,
        )

        fcp_clips = []
        for r in mcp_plan["clips"]:
            fcp_clips.append({
                "name": r["name"],
                "file_path": r["path"],
                "timeline_start": round(r["start_sec"], 3),
                "timeline_end": round(r["end_sec"], 3),
                "source_in": round(r["in_sec"], 3),
                "source_out": round(r["out_sec"], 3),
            })
        out_xml = os.path.join(pdir, f"{ep}.xml")
        with open(out_xml, "w", encoding="utf-8") as fp:
            fp.write(generate_fcp_xml({"sequence_name": ep, "fps": 24, "width": 1920, "height": 1080, "clips": fcp_clips}))

        concat_txt = os.path.join(pdir, "concat_list.txt")
        with open(concat_txt, "w", encoding="utf-8") as fp:
            for hspec in hook_specs:
                safe_p = hspec["path"].replace("\\", "/").replace("'", "'\\''")
                in_s = float(hspec["in_sec"])
                out_s = in_s + float(hspec["dur_sec"])
                fp.write(f"file '{safe_p}'\n")
                fp.write(f"inpoint {in_s:.3f}\n")
                fp.write(f"outpoint {out_s:.3f}\n")
            safe_intro = INTRO_CONCAT_MP4.replace("\\", "/").replace("'", "'\\''")
            fp.write(f"file '{safe_intro}'\n")
            fp.write("inpoint 0.000\n")
            fp.write("outpoint 6.006\n")
            for bspec in body_specs:
                safe_p = bspec["path"].replace("\\", "/").replace("'", "'\\''")
                out_s = float(bspec["dur_sec"])
                fp.write(f"file '{safe_p}'\n")
                fp.write("inpoint 0.000\n")
                fp.write(f"outpoint {out_s:.3f}\n")

        out_master_mp4 = os.path.join(vid_dir, f"{ep}.mp4")
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", "-movflags", "+faststart", out_master_mp4],
            check=True,
        )

        sb_out = os.path.join(verify_dir, f"{ep}_storyboard.jpg")
        render_storyboard(ep, out_master_mp4, sb_out)

        min_lap = min(x["st"]["center_lap"] for x in ordered_clips)
        min_db = min(x.get("peak_db", -12.0) for x in ordered_clips)
        tot_s = mcp_plan["total_duration_sec"]
        hooks_str = ", ".join(x["name"] for x in hook_specs)
        print(
            f"[{ep}] DONE in {time.time()-ep_t0:.1f}s | body={len(body_specs)} (+3 hook + intro) | tl_dur={tot_s:.2f}s ({tot_s/60:.2f}m) | min_lap={min_lap:.2f} | min_peak_db={min_db:.1f}dB | SameLinkAdj={same_adj} | hooks=[{hooks_str}]",
            flush=True,
        )

    shutil.rmtree(STAGE_DIR, ignore_errors=True)
    print(f"\nALL 12 EPISODES (AW2..AW4) REBUILT WITH ZERO CROSS-EPISODE REUSE in {time.time()-t0:.1f}s!", flush=True)


if __name__ == "__main__":
    main()
