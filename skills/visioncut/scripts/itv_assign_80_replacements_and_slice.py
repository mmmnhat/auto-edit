import os, json, re, shutil, subprocess, time, cv2
import numpy as np
import concurrent.futures
import sys
sys.path.insert(0, r"E:\.agents\skills\clean-cut\scripts")
from phash_utils import compute_phash

t0 = time.time()
PT_DIR = r"E:\ITV\Project tool"
SC_DIR = os.path.join(PT_DIR, "_shared_cache")
STAGE_DIR = os.path.join(SC_DIR, "_reusable_mp4_stage")
os.makedirs(STAGE_DIR, exist_ok=True)

with open(r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\dc105d59-214c-4e37-b645-224e5f7f5dfa\scratch\fast_repl_candidates.json", "r", encoding="utf-8") as f:
    c_repl = {c["cand_num"]: c for c in json.load(f)}
with open(r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\dc105d59-214c-4e37-b645-224e5f7f5dfa\scratch\fast_g12_candidates.json", "r", encoding="utf-8") as f:
    c_g12 = {i + 1: c for i, c in enumerate(json.load(f))}
with open(r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\dc105d59-214c-4e37-b645-224e5f7f5dfa\scratch\fast_extra_candidates.json", "r", encoding="utf-8") as f:
    c_ext = {i + 1: c for i, c in enumerate(json.load(f))}
with open(r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\dc105d59-214c-4e37-b645-224e5f7f5dfa\scratch\fast_full_rest.json", "r", encoding="utf-8") as f:
    c_full = {i + 1: c for i, c in enumerate(json.load(f))}

# Visually verified 100% 16:9 widescreen candidates (AI Vision First):
approved_human = []
for k in [1, 2, 3, 4, 5, 6, 7, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 29, 30, 31, 32, 34, 35, 36]:
    approved_human.append(c_repl[k])
for k in [11, 12, 21, 22, 37]:
    approved_human.append(c_g12[k])
for k in [1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 16, 19, 26]:
    approved_human.append(c_ext[k])
for k in [26, 27, 28, 29, 30, 32, 34, 35, 37]:
    approved_human.append(c_full[k])

approved_pet = []
for k in range(39, 74):
    approved_pet.append(c_repl[k])

all_approved = []
seen_iv = set()
for c in approved_human + approved_pet:
    iv_key = (c["yt_id"], round(float(c["true_st"]), 1))
    if iv_key not in seen_iv:
        seen_iv.add(iv_key)
        all_approved.append(c)

print(f"Total unique visually approved 16:9 audible candidates: {len(all_approved)} (human={len(approved_human)}, pet={len(approved_pet)})", flush=True)

# 1. Slice all approved candidates to STAGE_DIR using ffmpeg
def slice_cand(c):
    sid = c["scene_id"]
    out_p = os.path.join(STAGE_DIR, f"{sid}.mp4")
    if os.path.exists(out_p) and os.path.getsize(out_p) > 50000:
        c["staged_path"] = out_p
        return c
    sp = c["source_path"]
    st, dur = float(c["start_sec"]), float(c["duration"])
    cmd = [
        "ffmpeg", "-y", "-nostdin", "-v", "error",
        "-ss", f"{st:.3f}", "-t", f"{dur:.3f}", "-i", sp,
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30",
        "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", out_p
    ]
    rv = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if rv.returncode != 0 or not os.path.exists(out_p) or os.path.getsize(out_p) < 20000:
        cmd_cpu = [
            "ffmpeg", "-y", "-nostdin", "-v", "error",
            "-ss", f"{st:.3f}", "-t", f"{dur:.3f}", "-i", sp,
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", out_p
        ]
        subprocess.run(cmd_cpu, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    c["staged_path"] = out_p
    return c

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    sliced_cands = list(ex.map(slice_cand, all_approved))

print(f"Sliced {len(sliced_cands)} candidates in {time.time()-t0:.2f}s", flush=True)

# 2. Compute 5-anchor active-core visual signatures on all 712 kept clips + sliced_cands
with open(os.path.join(PT_DIR, "kb132", "kb132_manifest.json"), "r", encoding="utf-8") as f:
    m132 = json.load(f)
with open(os.path.join(SC_DIR, "episode_partition_plan_v2_unified.json"), "r", encoding="utf-8") as f:
    plan = json.load(f)
with open(r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\dc105d59-214c-4e37-b645-224e5f7f5dfa\scratch\master_replace_list.json", "r", encoding="utf-8") as f:
    mrep = json.load(f)

master_replace = set(mrep["master_replace"].keys())

def compute_dhash(img_gray):
    r = cv2.resize(img_gray, (9, 8), interpolation=cv2.INTER_AREA)
    diff = r[:, 1:] > r[:, :-1]
    val = 0
    for b in diff.flatten():
        val = (val << 1) | int(b)
    return val

def scan_mp4_5anchor(cpath):
    cap = cv2.VideoCapture(cpath)
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    dur = n_frames / fps if fps > 0 else 0.0
    pcts = [0.15, 0.32, 0.50, 0.68, 0.85]
    po, pf, do, df, patches_o, patches_f = [], [], [], [], [], []
    for p in pcts:
        f_idx = max(1, min(n_frames - 2, int(n_frames * p)))
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ok, frm = cap.read()
        if not ok or frm is None:
            continue
        h, w = frm.shape[:2]
        core = frm[int(h * 0.10) : int(h * 0.90), int(w * 0.10) : int(w * 0.90)]
        small = cv2.resize(core, (160, 90))
        small_f = cv2.flip(small, 1)
        g_o = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        g_f = cv2.cvtColor(small_f, cv2.COLOR_BGR2GRAY)
        po.append(int(compute_phash(small)))
        pf.append(int(compute_phash(small_f)))
        do.append(int(compute_dhash(g_o)))
        df.append(int(compute_dhash(g_f)))
        p_o = cv2.resize(g_o, (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32)
        p_f = cv2.resize(g_f, (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32)
        p_o = (p_o - np.mean(p_o)) / (np.std(p_o) + 1.0)
        p_f = (p_f - np.mean(p_f)) / (np.std(p_f) + 1.0)
        patches_o.append(p_o)
        patches_f.append(p_f)
    cap.release()
    return (dur, po, pf, do, df, patches_o, patches_f)

kept_paths = []
for c in m132["clips"]:
    kept_paths.append(("kb132/" + c["clip_name"], c["source_path"]))
for kb_num in range(133, 141):
    kb = f"kb{kb_num}"
    for s in plan[kb]["slots"]:
        key = f"{kb}/{s['clip_name']}"
        if key not in master_replace:
            kept_paths.append((key, os.path.join(PT_DIR, kb, "source", s["clip_name"])))

print(f"Scanning 5-anchor signatures for {len(kept_paths)} kept clips + {len(sliced_cands)} candidates...", flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
    kept_sigs = list(ex.map(lambda x: (x[0], scan_mp4_5anchor(x[1])), kept_paths))
    cand_sigs = list(ex.map(lambda c: (c, scan_mp4_5anchor(c["staged_path"])), sliced_cands))

def is_5anchor_dup(sig1, sig2):
    _, po1, pf1, do1, df1, pto1, ptf1 = sig1
    _, po2, pf2, do2, df2, pto2, ptf2 = sig2
    best_p, best_d, best_l1 = 64, 64, 999.0
    for a in range(len(po1)):
        for b in range(len(po2)):
            dp = (po1[a] ^ po2[b]).bit_count()
            dd = (do1[a] ^ do2[b]).bit_count()
            if dp <= 12 and dd <= 12:
                l1 = float(np.mean(np.abs(pto1[a] - pto2[b])))
                if l1 < best_l1:
                    best_l1, best_p, best_d = l1, dp, dd
            dpf = (po1[a] ^ pf2[b]).bit_count()
            ddf = (do1[a] ^ df2[b]).bit_count()
            if dpf <= 12 and ddf <= 12:
                l1f = float(np.mean(np.abs(pto1[a] - ptf2[b])))
                if l1f < best_l1:
                    best_l1, best_p, best_d = l1f, dpf, ddf
    return (best_p <= 8 and best_d <= 8) or (best_p <= 10 and best_d <= 10 and best_l1 < 0.35)

# Verify no kept_sigs are duplicates of each other!
kept_dup_pairs = []
for i in range(len(kept_sigs)):
    if kept_sigs[i][0].startswith("kb132/"):
        for j in range(i + 1, len(kept_sigs)):
            if not kept_sigs[j][0].startswith("kb132/") and is_5anchor_dup(kept_sigs[i][1], kept_sigs[j][1]):
                kept_dup_pairs.append((kept_sigs[i][0], kept_sigs[j][0]))
    else:
        for j in range(i + 1, len(kept_sigs)):
            if is_5anchor_dup(kept_sigs[i][1], kept_sigs[j][1]):
                kept_dup_pairs.append((kept_sigs[i][0], kept_sigs[j][0]))

print(f"Kept-vs-Kept 5-anchor duplicates remaining: {len(kept_dup_pairs)}", flush=True)
for pair in kept_dup_pairs:
    print("  KEPT_DUP:", pair, flush=True)

# Filter cand_sigs against all kept_sigs and previously accepted cand_sigs
accepted_cands = []
known_sigs = [s for _, s in kept_sigs]
for c, sig in cand_sigs:
    dur = sig[0]
    if dur < 3.2:
        continue
    if any(is_5anchor_dup(sig, ks) for ks in known_sigs):
        print(f"  Dropped candidate {c['scene_id']} (5-anchor visual dup)", flush=True)
        continue
    known_sigs.append(sig)
    c["probed_dur"] = round(dur, 3)
    accepted_cands.append(c)

print(f"Total 100% unique 5-anchor verified replacement candidates: {len(accepted_cands)}", flush=True)
with open(r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\dc105d59-214c-4e37-b645-224e5f7f5dfa\scratch\verified_unique_pool_80plus.json", "w", encoding="utf-8") as f:
    json.dump(accepted_cands, f, indent=2, ensure_ascii=False)
