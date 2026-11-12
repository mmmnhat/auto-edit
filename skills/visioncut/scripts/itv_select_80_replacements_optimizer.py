import os, json, cv2, subprocess
import numpy as np

PT_DIR = r"E:\ITV\Project tool"
SC_DIR = os.path.join(PT_DIR, "_shared_cache")
PLAN_PATH = os.path.join(SC_DIR, "episode_partition_plan_v2_unified.json")
MREP_PATH = r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\dc105d59-214c-4e37-b645-224e5f7f5dfa\scratch\master_replace_list.json"
POOL_PATH = r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\dc105d59-214c-4e37-b645-224e5f7f5dfa\scratch\verified_unique_pool_80plus.json"
OUT_DIR = r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\dc105d59-214c-4e37-b645-224e5f7f5dfa\scratch\dup_sheets"

with open(PLAN_PATH, "r", encoding="utf-8") as f:
    plan = json.load(f)
with open(MREP_PATH, "r", encoding="utf-8") as f:
    mrep = json.load(f)["master_replace"]
with open(POOL_PATH, "r", encoding="utf-8") as f:
    pool = json.load(f)

def probe_safe_dur(p):
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=duration:format=duration", "-of", "default=noprint_wrappers=1:nokey=1", p],
        capture_output=True, text=True, stdin=subprocess.DEVNULL
    )
    vals = [float(x) for x in res.stdout.strip().splitlines() if x.strip() and x.strip() != "N/A"]
    min_d = min(vals) if vals else 8.0
    safe_frames = max(1, int(min_d * 24000.0 / 1001.0))
    return round(safe_frames * 1001.0 / 24000.0, 3)

for c in pool:
    c["safe_dur"] = probe_safe_dur(c["staged_path"])

# Identify the 6 VO slots
vo_targets = [
    ("kb133", 14, 3, "Premise"),
    ("kb134", 6, 1, "Premise"),
    ("kb137", 54, 10, "Aftermath"),
    ("kb138", 42, 8, "Aftermath"),
    ("kb138", 54, 10, "Aftermath"),
    ("kb139", 60, 11, "Aftermath"),
]

# Pick 6 human-fail clips with safe_dur in [8.5, 12.2] for the 6 VO slots
human_vo_cands = [c for c in pool if not str(c["scene_id"]).startswith("pet_") and 8.5 <= c["safe_dur"] <= 12.5]
picked_vo6 = human_vo_cands[:6]
picked_vo6_ids = {c["scene_id"] for c in picked_vo6}

vo_assignments = {}
rows_img = []
for (kb, slot, vo_num, role), cand in zip(vo_targets, picked_vo6):
    vo_assignments[f"{kb}_{slot}"] = {
        "kb": kb,
        "slot": slot,
        "vo_num": vo_num,
        "role": role,
        "cand": cand,
    }
    cap = cv2.VideoCapture(cand["staged_path"])
    nf = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 100)
    thumbs = []
    for p, tag in [(0.15, "15% Setup"), (0.40, "40% Action"), (0.65, "65% Climax"), (0.88, "88% React")]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(1, min(nf - 2, int(nf * p))))
        ok, frm = cap.read()
        if not ok or frm is None:
            frm = np.zeros((158, 280, 3), dtype=np.uint8)
        else:
            frm = cv2.resize(frm, (280, 158))
        cv2.rectangle(frm, (0, 0), (280, 24), (0, 0, 0), -1)
        cv2.putText(frm, f"{kb} #{slot} VO{vo_num:02d} ({role}) | {cand['scene_id']} ({cand['safe_dur']:.1f}s) {tag}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.37, (0, 255, 255), 1, cv2.LINE_AA)
        thumbs.append(frm)
    cap.release()
    rows_img.append(np.hstack(thumbs))

vo_sheet_path = os.path.join(OUT_DIR, "vo6_replacements_sheet.jpg")
cv2.imwrite(vo_sheet_path, np.vstack(rows_img), [int(cv2.IMWRITE_JPEG_QUALITY), 90])
print(f"Saved {vo_sheet_path}")

# Now optimize the remaining 74 non-VO slots across kb133..kb140 so every episode hits 900.0s!
rem_pool = [c for c in pool if c["scene_id"] not in picked_vo6_ids]
print(f"Remaining pool size for 74 non-VO slots: {len(rem_pool)}")

intro_plus_glitch = round((375 + 27) * 1001.0 / 24000.0, 3) # 16.767s
target_body_dur = 900.0 - intro_plus_glitch # 883.233s

ep_kept_dur = {}
ep_nonvo_slots = {}
for kb_num in range(133, 141):
    kb = f"kb{kb_num}"
    kept_sum = 0.0
    nonvo = []
    for s in plan[kb]["slots"]:
        sl = s["slot_idx"]
        key = f"{kb}_{sl}"
        if key in vo_assignments:
            kept_sum += vo_assignments[key]["cand"]["safe_dur"]
        elif key in mrep:
            nonvo.append(sl)
        else:
            mp4_p = os.path.join(PT_DIR, kb, "source", s["clip_name"])
            kept_sum += probe_safe_dur(mp4_p)
    ep_kept_dur[kb] = kept_sum
    ep_nonvo_slots[kb] = nonvo
    need = target_body_dur - kept_sum
    print(f"  {kb}: kept+VO_sum={kept_sum:.2f}s, non-VO slots={len(nonvo)}, need_sum={need:.2f}s (avg={need/len(nonvo):.2f}s/slot)")

# Initial greedy assignment + local swap optimization with the 86 rem_pool candidates
import random
random.seed(42)

# Sort episodes by constrainedness (fewest slots or extreme average needed duration)
used_idx = set()
assigned = {kb: [] for kb in ep_nonvo_slots}

# First pass: greedy per episode
for kb in sorted(ep_nonvo_slots.keys(), key=lambda k: len(ep_nonvo_slots[k])):
    n_slots = len(ep_nonvo_slots[k if False else kb])
    need = target_body_dur - ep_kept_dur[kb]
    cur_sum = 0.0
    for step in range(n_slots):
        rem_steps = n_slots - step
        want_d = (need - cur_sum) / rem_steps
        best_i = min((i for i in range(len(rem_pool)) if i not in used_idx), key=lambda i: abs(rem_pool[i]["safe_dur"] - want_d))
        used_idx.add(best_i)
        assigned[kb].append(best_i)
        cur_sum += rem_pool[best_i]["safe_dur"]

# Second pass: iterative swap optimization (both between episodes and with unused pool items)
for _iter in range(5000):
    improved = False
    # Try swapping an assigned candidate in kb with an unused candidate in rem_pool
    unused_indices = [i for i in range(len(rem_pool)) if i not in used_idx]
    for kb in ep_nonvo_slots:
        cur_tot = ep_kept_dur[kb] + sum(rem_pool[i]["safe_dur"] for i in assigned[kb])
        cur_err = abs(cur_tot - target_body_dur)
        if cur_err <= 0.08:
            continue
        for pos, ci in enumerate(assigned[kb]):
            for ui in unused_indices:
                new_tot = cur_tot - rem_pool[ci]["safe_dur"] + rem_pool[ui]["safe_dur"]
                new_err = abs(new_tot - target_body_dur)
                if new_err < cur_err - 0.01:
                    used_idx.remove(ci)
                    used_idx.add(ui)
                    assigned[kb][pos] = ui
                    cur_tot = new_tot
                    cur_err = new_err
                    unused_indices = [i for i in range(len(rem_pool)) if i not in used_idx]
                    improved = True
                    break
    # Try swapping between two episodes kb1, kb2
    kbs = list(ep_nonvo_slots.keys())
    for a_i in range(len(kbs)):
        for b_i in range(a_i + 1, len(kbs)):
            k1, k2 = kbs[a_i], kbs[b_i]
            t1 = ep_kept_dur[k1] + sum(rem_pool[i]["safe_dur"] for i in assigned[k1])
            t2 = ep_kept_dur[k2] + sum(rem_pool[i]["safe_dur"] for i in assigned[k2])
            e0 = abs(t1 - target_body_dur) + abs(t2 - target_body_dur)
            if e0 <= 0.15:
                continue
            for p1, c1 in enumerate(assigned[k1]):
                for p2, c2 in enumerate(assigned[k2]):
                    d1, d2 = rem_pool[c1]["safe_dur"], rem_pool[c2]["safe_dur"]
                    nt1 = t1 - d1 + d2
                    nt2 = t2 - d2 + d1
                    ne = abs(nt1 - target_body_dur) + abs(nt2 - target_body_dur)
                    if ne < e0 - 0.01:
                        assigned[k1][p1] = c2
                        assigned[k2][p2] = c1
                        t1, t2, e0 = nt1, nt2, ne
                        improved = True
                        break
    if not improved:
        break

print("\nFinal Optimized Episode Sequence Durations:")
full_assignment = dict(vo_assignments)
for kb in sorted(ep_nonvo_slots.keys()):
    slots = ep_nonvo_slots[kb]
    cands = [rem_pool[i] for i in assigned[kb]]
    tot_body = ep_kept_dur[kb] + sum(c["safe_dur"] for c in cands)
    tot_seq = intro_plus_glitch + tot_body
    print(f"  {kb}: total_seq={tot_seq:.3f}s (diff={tot_seq - 900.0:+.3f}s)")
    for sl, c in zip(slots, cands):
        full_assignment[f"{kb}_{sl}"] = {
            "kb": kb,
            "slot": sl,
            "vo_num": None,
            "role": None,
            "cand": c,
        }

out_assign_path = r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\dc105d59-214c-4e37-b645-224e5f7f5dfa\scratch\final_80_slot_assignments.json"
with open(out_assign_path, "w", encoding="utf-8") as f:
    json.dump(full_assignment, f, indent=2, ensure_ascii=False)
print(f"Saved {out_assign_path} ({len(full_assignment)} slots)")
