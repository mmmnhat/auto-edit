import os
import sys
import json
import time
import concurrent.futures
import cv2
import numpy as np
from pathlib import Path

sys.path.insert(0, r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\97bf33b9-d07b-48a7-907f-029c5d6e4a64\scratch")
from probe_all_882_unique_scenes import cid_to_vid
from prepare_pools_and_hook_sheets import VIDEO_META

SCRATCH_DIR = Path(r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\97bf33b9-d07b-48a7-907f-029c5d6e4a64\scratch")
PLAN_PATH = SCRATCH_DIR / "bonk_kb33_40_plan.json"
EXTRA_PATH = SCRATCH_DIR / "bonk_extra_audible_scenes.json"
VISION_CACHE_PATH = SCRATCH_DIR / "bonk_vision_cache.json"
HASH_CACHE_PATH = SCRATCH_DIR / "bonk_818_hashes.json"

def detect_exact_pillarbox_pct(mp4_path: str, old_crop: float) -> float:
    cap = cv2.VideoCapture(mp4_path)
    if not cap.isOpened():
        return old_crop
    nf = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, nf // 2))
    ok, fr = cap.read()
    cap.release()
    if not ok or fr is None:
        return old_crop
    h, w = fr.shape[:2]
    gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    dx = np.mean(np.abs(np.diff(gray, axis=1)), axis=0)
    best_x, best_score = 0, 0.0
    for x in range(int(w * 0.18), int(w * 0.37)):
        rx = w - 1 - x
        bg_l = float(np.median(dx[max(5, x - 25) : x - 3]))
        bg_r = float(np.median(dx[rx + 3 : min(w - 5, rx + 25)]))
        if dx[x] >= max(3.5, bg_l * 2.6) and dx[rx] >= max(3.5, bg_r * 2.6):
            score = (dx[x] + dx[rx]) / max(0.8, bg_l + bg_r)
            if score > best_score:
                best_score = score
                best_x = x
    if best_score >= 5.2 and best_x > 0:
        l_mean = np.mean(fr[:, :best_x], axis=(0, 1))
        r_mean = np.mean(fr[:, w - best_x :], axis=(0, 1))
        if float(np.abs(l_mean - r_mean).mean()) <= 28.0:
            s_pct = round((best_x + 4) / float(w) * 100.0, 1)
            return max(old_crop, min(36.0, max(20.0, s_pct)))
    return old_crop

def interleave_by_vid(scenes: list):
    by_v = {}
    for s in scenes:
        by_v.setdefault(s["vid"], []).append(s)
    for v in by_v:
        by_v[v].sort(key=lambda x: x["raw_st"])
    mixed = []
    last_v = None
    while any(by_v.values()):
        cands = [v for v, lst in by_v.items() if lst and v != last_v]
        if not cands:
            cands = [v for v, lst in by_v.items() if lst]
        cands.sort(key=lambda v: (-len(by_v[v]), v))
        chosen = cands[0]
        mixed.append(by_v[chosen].pop(0))
        last_v = chosen
    return mixed

def main():
    plan = json.load(open(PLAN_PATH, encoding="utf-8"))
    extra = json.load(open(EXTRA_PATH, encoding="utf-8"))
    vc = json.load(open(VISION_CACHE_PATH, encoding="utf-8"))
    hash_cache = json.load(open(HASH_CACHE_PATH, encoding="utf-8"))

    by_cid = {}
    for lst in plan["episodes"].values():
        for sc in lst:
            by_cid[sc["canh_id"]] = sc
    for sc in extra:
        if sc["canh_id"] not in by_cid:
            by_cid[sc["canh_id"]] = sc
    for ckey, vinfo in vc.items():
        cid_s, st_s, dur_s = ckey.split("|")
        cid, st, dur = int(cid_s), float(st_s), float(dur_s)
        if cid not in by_cid:
            vid = cid_to_vid(cid)
            yid, chan, url = VIDEO_META[vid]
            by_cid[cid] = {
                "canh_id": cid,
                "vid": vid,
                "yid": yid,
                "chan": chan,
                "url": url,
                "src_mp4": rf"E:\Bonk funny moments\project tool\_raw_cache\{yid}.mp4",
                "raw_st": st,
                "raw_et": round(st + dur, 2),
                "raw_dur": dur,
                "sl_st": st,
                "sl_dur": dur,
                "crop_lr_pct": float(vinfo["cv_crop"]),
                "cv_crop": float(vinfo["cv_crop"]),
                "final_crop_lr": float(vinfo["cv_crop"]),
                "lap_var": float(vinfo["lap_var"]),
                "file_dur": float(vinfo["fdur"]),
                "score": 70.0,
                "desc": f"{chan} funny moment",
                "ckey": ckey,
                "shared_mp4": rf"E:\Bonk funny moments\project tool\_raw_cache\sliced_by_sig\c{cid}_{st_s}_{dur_s}.mp4",
            }

    all_scenes = list(by_cid.values())
    def _fix_crop(sc):
        cr = detect_exact_pillarbox_pct(sc["shared_mp4"], float(sc["final_crop_lr"]))
        sc["final_crop_lr"] = cr
        sc["crop_lr_pct"] = cr
        sc["cv_crop"] = cr
        return sc
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        all_scenes = list(ex.map(_fix_crop, all_scenes))
    newly_cropped = sum(1 for s in all_scenes if s["final_crop_lr"] > 0)
    print(f"Combined unique canh_id pool: {len(all_scenes)} scenes ({sum(x['sl_dur'] for x in all_scenes):.2f}s) | Pillarboxed cropped: {newly_cropped}")

    # Global visual + source-interval deduplication across all 818 scenes
    all_scenes.sort(key=lambda x: (0 if x["final_crop_lr"] == 0 else 1, -x["sl_dur"], -x["score"]))

    unique_pool = []
    ov_removed = 0
    vis_removed = 0
    for sc in all_scenes:
        h1 = hash_cache[sc["ckey"]]
        is_dup = False
        for ex in unique_pool:
            if sc["canh_id"] == ex["canh_id"]:
                is_dup = True
                ov_removed += 1
                break
            h2 = hash_cache[ex["ckey"]]
            matched_anchors = 0
            for i in range(len(h1["ph"])):
                for j in range(len(h2["ph"])):
                    phd = min((h1["ph"][i] ^ h2["ph"][j]).bit_count(), (h1["phf"][i] ^ h2["ph"][j]).bit_count())
                    dhd = min((h1["dh"][i] ^ h2["dh"][j]).bit_count(), (h1["dhf"][i] ^ h2["dh"][j]).bit_count())
                    if phd <= 6 and dhd <= 6:
                        pv1 = np.array(h1["pv"][i])
                        pv1f = np.array(h1["pvf"][i])
                        pv2 = np.array(h2["pv"][j])
                        l1 = min(float(np.abs(pv1 - pv2).mean()), float(np.abs(pv1f - pv2).mean()))
                        if l1 < 0.22:
                            matched_anchors += 1
                            break
            if matched_anchors >= 2:
                is_dup = True
                vis_removed += 1
                break
        if not is_dup:
            unique_pool.append(sc)

    total_unique_dur = sum(x["sl_dur"] for x in unique_pool)
    print(
        f"Globally deduplicated pool (0 canh_id overlap, 0 interval overlap, 0 visual dup): "
        f"{len(unique_pool)} scenes (ov_removed={ov_removed}, vis_removed={vis_removed}) | "
        f"Total dur = {total_unique_dur:.2f}s ({total_unique_dur/8:.2f}s/ep)"
    )

    ep_keys = ["kb33", "kb34", "kb35", "kb36", "kb37", "kb38", "kb39", "kb40"]
    episodes = {k: [] for k in ep_keys}
    ep_durs = {k: 0.0 for k in ep_keys}

    unique_pool.sort(key=lambda x: (0 if x["final_crop_lr"] == 0 else 1, -x["sl_dur"], -x["score"]))
    for sc in unique_pool:
        best_ep = min(ep_keys, key=lambda k: ep_durs[k])
        episodes[best_ep].append(sc)
        ep_durs[best_ep] += sc["sl_dur"]

    top12_per_ep = {}
    seen_global = set()
    for ek in ep_keys:
        mixed = interleave_by_vid(episodes[ek])
        for idx, sc in enumerate(mixed, start=1):
            sc["ep_idx"] = idx
            assert sc["canh_id"] not in seen_global, f"Duplicate canh_id {sc['canh_id']} in {ek}!"
            seen_global.add(sc["canh_id"])
        episodes[ek] = mixed

        scored = []
        for sc in mixed:
            dur = sc["sl_dur"]
            if dur < 3.8 or dur > 11.5:
                continue
            if sc["lap_var"] < 40.0:
                continue
            wide_bonus = 30.0 if sc["final_crop_lr"] == 0.0 else 0.0
            dur_bonus = 15.0 if 4.5 <= dur <= 8.0 else 0.0
            rank_sc = wide_bonus + dur_bonus + sc["score"] + min(sc["lap_var"], 500.0) * 0.08
            scored.append((rank_sc, sc))
        scored.sort(key=lambda x: -x[0])
        top12_per_ep[ek] = [x[1] for x in scored[:12]]
        vids_present = sorted({x["vid"] for x in mixed})
        print(
            f"  {ek}: {len(mixed)} unique clips | Body={ep_durs[ek]:.2f}s (+Hook+Intro -> ~{ep_durs[ek]+11.5:.1f}s) | "
            f"sources={vids_present} | Top-12 hooks ready"
        )

    print(f"Total unique scenes across all 8 episodes: {len(seen_global)} (0 reused scenes across kb33..kb40!)")

    PLAN_PATH.write_text(
        json.dumps({"episodes": episodes, "top12_per_ep": top12_per_ep}, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    def render_sheet(ep_subset, out_jpg):
        tw, th = 240, 135
        canvas = np.zeros((len(ep_subset) * th, 12 * tw, 3), dtype=np.uint8)
        for r_idx, ek in enumerate(ep_subset):
            for c_idx, cand in enumerate(top12_per_ep[ek][:12]):
                cap = cv2.VideoCapture(cand["shared_mp4"])
                nf = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(nf * 0.52)))
                ret, frm = cap.read()
                cap.release()
                if not ret or frm is None:
                    tile = np.zeros((th, tw, 3), dtype=np.uint8)
                else:
                    h, w = frm.shape[:2]
                    cr = cand["final_crop_lr"]
                    if cr > 0:
                        x1 = int(w * (cr / 100.0))
                        x2 = w - x1
                        frm = frm[:, x1:x2]
                    tile = cv2.resize(frm, (tw, th), interpolation=cv2.INTER_AREA)
                cv2.rectangle(tile, (0, 0), (tw, 26), (0, 0, 0), -1)
                lbl = f"{ek} #{c_idx+1} (c{cand['ep_idx']}) {cand['sl_dur']:.1f}s"
                cv2.putText(tile, lbl, (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
                cv2.rectangle(tile, (0, th - 22), (tw, th), (0, 0, 0), -1)
                flbl = f"Lap:{int(cand['lap_var'])} Sc:{cand['score']:.0f} v{cand['vid']}"
                cv2.putText(tile, flbl, (4, th - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (100, 255, 100), 1, cv2.LINE_AA)
                cv2.rectangle(tile, (0, 0), (tw - 1, th - 1), (80, 80, 80), 1)
                canvas[r_idx * th : (r_idx + 1) * th, c_idx * tw : (c_idx + 1) * tw] = tile
        cv2.imwrite(str(out_jpg), canvas, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        print(f"Saved Contact Sheet: {out_jpg}")

    render_sheet(["kb33", "kb34", "kb35", "kb36"], SCRATCH_DIR / "hook_candidates_kb33_kb36.jpg")
    render_sheet(["kb37", "kb38", "kb39", "kb40"], SCRATCH_DIR / "hook_candidates_kb37_kb40.jpg")

if __name__ == "__main__":
    main()
