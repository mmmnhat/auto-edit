import concurrent.futures
import copy
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")

TICKS_PER_SEC = 254016000000
ELEVENLABS_CMD = r"C:\Users\AMZ-HUY\AppData\Roaming\npm\elevenlabs.cmd"
VOICE_ID = "ITLDKaHYPRfCyyrPpZu2"
MODEL_ID = "eleven_v3"
LANGUAGE_CODE = "auto"
TAG_PREFIX = "[sarcastic, dry humor, rushed, fast, shout, fast-paced, mooth delivery]"

# 15 VO comments per episode (4 from Google Sheet Part 1 + 11 evenly spaced from Web Script Part 2)
VO_MANIFEST = {
    "kb107": [
        # Part 1 (Google Sheet KB067: STT 6, 9, 12, 18)
        (5,  "Who's gonna explain why moving one load required taking down a steel post?"),
        (8,  "The excavator successfully uprooted the tree and instantly unlocked a hidden underground fire pit."),
        (11, "This combine harvester just decided to harvest an overhead pipeline instead of crops."),
        (17, "That mobile home just decided to take a little piece of the road with it."),
        # Part 2 (Web Script 348 - 11 comments spaced ~33-38s apart across V#20..V#84)
        (21, "When the boss says chase down those leads, this isn't what he meant."),
        (25, "This is exactly why Jim from accounting is always late."),
        (31, "He just found the fastest way completely underground."),
        (37, "Bro thought he was in MotoGP."),
        (44, "Evasive maneuvers were completely unsuccessful today."),
        (50, "Teamwork really makes the dream sink."),
        (56, "This guy really wanted to test his warranty."),
        (61, "Nature's way of rejecting your selfie attempt."),
        (67, "Gravity always wins the winter sports."),
        (73, "Sir, your wake-up call is here."),
        (80, "Physics called, they want their momentum back."),
    ],
    "kb108": [
        # Part 1 (Google Sheet KB068: STT 6, 11, 14, 18)
        (5,  "She was halfway downstairs when the stairs decided to speed things up."),
        (10, "A freezing, brutal lesson in why your house is not a personal ice dispenser."),
        (13, "The battery decided to self-destruct rather than face another software update."),
        (17, "Somebody tell this guy the gym is still open."),  # note: tắt tiếng cmt
        # Part 2 (Web Script 349 - 11 comments spaced ~33-38s apart across V#20..V#85)
        (20, "Those brakes just earned a serious raise."),
        (25, "Free hose with every fill-up today."),
        (30, "Air traffic control just denied his clearance."),
        (35, "Tarzan would be so disappointed."),
        (40, "Gravity just canceled his flight plans."),
        (45, "Never trust a coworker who asks you to stand perfectly still."),
        (51, "That package belongs to the angry terrier now."),
        (56, "That ramp was waiting for this exact moment."),
        (63, "Ejector seats are working perfectly today."),
        (69, "The surfboard just got a new job description."),
        (79, "Barrel racing, now with impromptu dismounts."),
    ],
    "kb109": [
        # Part 1 (Google Sheet KB069: STT 7, 10, 15, 19)
        (7,  "That hose has more horsepower than the truck it's supposed to wash."),
        (10, "These strays quickly realized that barking at an officer's vehicle is a remarkably bad survival strategy."),
        (16, "A perfect example of why you should never trust a forklift to safely secure your vacation departure."),
        (20, "Even Sherlock Holmes would need a day off to figure out this wiring."),
        # Part 2 (Web Script 350 - 11 comments spaced ~33-38s apart across V#21..V#85)
        (23, "The boat finally realized it doesn't need humans."),
        (27, "The kayak has already decided his fate."),
        (32, "I guess buying a real ramp was too expensive."),
        (38, "Not exactly the graceful exit she planned."),
        (42, "He's just making sure everyone's registration is up to date."),
        (48, "Security is taking their job way too seriously."),
        (56, "That duck just friend-zoned him in record time."),
        (61, "This ramp design is purely based on hope."),
        (66, "He's just polishing the snow for the next shift."),
        (71, "That's one way to speed up the scenic tour."),
        (77, "Well, the dust cloud really adds some drama."),
    ],
    "kb110": [
        # Part 1 (Google Sheet KB070: STT 6, 10, 14, 20)
        (6,  "The tree decided it wasn't going down without launching him first."),
        (10, "Even the fire department isn't immune to a surprise gravity check."),  # note: đè lên cmt cũ nhaa
        (14, "Nothing adds extra crunch to a smoothie quite like a pair of prescription glasses."),
        (20, "One flip and breakfast officially left the chat."),
        # Part 2 (Web Script 363 - 11 comments spaced ~33-38s apart across V#21..V#86)
        (23, "Sir, I'm gonna have to see your membership card."),
        (28, "Professional fishermen take the off-season very seriously."),
        (32, "This guy is turning roadwork into a talent show."),
        (37, "The roof decided to return his ladder."),
        (41, "Bro's been waiting for a spot."),
        (47, "Gymnastics tryouts aren't going as planned."),
        (52, "Someone's trying to earn extra style points."),
        (56, "The new company vehicle is a little smaller than expected."),
        (61, "That fish just scored a knockout."),
        (70, "That bucket listened to his complaints all morning and finally snapped."),
        (77, "Synchronization is the key to disaster."),
    ],
}

# Clips where Google Sheet explicitly says to mute original A1 audio under the VO comment / source music
MUTE_A1_CLIPS = {
    "kb108": {17, 18},  # STT 18 & 19 (itv.kb108.18, itv.kb108.19): "tắt tiếng cmt"
    "kb109": {19},      # STT 18 (itv.kb109.18): "có nhạc"
    "kb110": {10},      # STT 10 (itv.kb110.10): "đè lên cmt cũ nhaa"
}


KNOWN_IMPACTS = {
    "47_2.mp4": 4.14,
    "04_2.mp4": 2.90,
    # Visually verified Part 1 VO parent clips (kb118..kb124)
    "itv.kb118.6.mp4": 6.50,
    "itv.kb118.10.mp4": 3.60,
    "itv.kb118.14.mp4": 9.20,
    "itv.kb118.17.mp4": 3.30,
    "itv.kb119.8.mp4": 3.55,
    "itv.kb119.11.mp4": 3.15,
    "itv.kb119.15.mp4": 1.80,
    "itv.kb119.19.mp4": 3.80,
    "itv.kb120.7.mp4": 1.35,
    "itv.kb120.11.mp4": 1.80,
    "itv.kb120.15.mp4": 4.50,
    "itv.kb120.19.mp4": 3.60,
    "itv.kb121.6.mp4": 1.60,
    "itv.kb121.10.mp4": 3.55,
    "itv.kb121.16.mp4": 3.10,
    "itv.kb121.20.mp4": 4.75,
    "itv.kb122.6.mp4": 0.70,
    "itv.kb122.11.mp4": 9.15,
    "itv.kb122.15.mp4": 5.30,
    "itv.kb122.19.mp4": 3.50,
    "itv.kb123.1.mp4": 3.40,
    "itv.kb123.3.mp4": 1.40,
    "itv.kb123.9.mp4": 3.20,
    "itv.kb123.15.mp4": 2.80,
    "itv.kb124.7.mp4": 4.30,
    "itv.kb124.11.mp4": 6.80,
    "itv.kb124.14.mp4": 4.20,
    "itv.kb124.16.mp4": 3.20,
    "itv.kb129.7.mp4": 3.40,
    "itv.kb129.12.mp4": 2.90,
    "itv.kb129.17.mp4": 4.50,
    "itv.kb129.21.mp4": 5.20,
    "itv.kb130.6.mp4": 7.60,
    "itv.kb130.10.mp4": 4.20,
    "itv.kb130.14.mp4": 3.70,
    "itv.kb130.17.mp4": 5.20,
    "itv.kb131.6.mp4": 5.60,
    "itv.kb131.10.mp4": 5.65,
    "itv.kb131.15.mp4": 1.90,
    "itv.kb131.19.mp4": 4.20,
}

PROJECT_KNOWN_IMPACTS = {
    # kb118
    ("kb118", "04_2.mp4"): 2.90,
    ("kb118", "11.mp4"): 2.80,
    ("kb118", "15.mp4"): 2.40,
    ("kb118", "21.mp4"): 10.20,
    ("kb118", "28.mp4"): 2.90,
    ("kb118", "35.mp4"): 9.50,
    ("kb118", "42.mp4"): 5.30,
    ("kb118", "48.mp4"): 5.20,
    ("kb118", "55.mp4"): 5.60,
    ("kb118", "61.mp4"): 66.00,
    ("kb118", "68.mp4"): 6.20,
    # kb119
    ("kb119", "04.mp4"): 1.60,
    ("kb119", "10.mp4"): 2.10,
    ("kb119", "17.mp4"): 2.40,
    ("kb119", "23.mp4"): 4.50,
    ("kb119", "29.mp4"): 2.30,
    ("kb119", "35.mp4"): 2.20,
    ("kb119", "41.mp4"): 2.50,
    ("kb119", "47.mp4"): 2.10,
    ("kb119", "53.mp4"): 3.80,
    ("kb119", "60.mp4"): 1.50,
    ("kb119", "66.mp4"): 2.20,
    # kb120
    ("kb120", "04.mp4"): 1.90,
    ("kb120", "10.mp4"): 2.30,
    ("kb120", "16.mp4"): 1.80,
    ("kb120", "22.mp4"): 2.40,
    ("kb120", "28.mp4"): 1.70,
    ("kb120", "34.mp4"): 2.10,
    ("kb120", "42.mp4"): 1.90,
    ("kb120", "48.mp4"): 2.20,
    ("kb120", "54.mp4"): 2.50,
    ("kb120", "61.mp4"): 2.80,
    ("kb120", "67.mp4"): 2.10,
    # kb121
    ("kb121", "04.mp4"): 1.80,
    ("kb121", "10.mp4"): 2.20,
    ("kb121", "16.mp4"): 7.90,
    ("kb121", "22.mp4"): 2.10,
    ("kb121", "28.mp4"): 1.90,
    ("kb121", "34.mp4"): 2.30,
    ("kb121", "41.mp4"): 2.00,
    ("kb121", "47.mp4"): 2.50,
    ("kb121", "53.mp4"): 2.20,
    ("kb121", "61.mp4"): 1.80,
    ("kb121", "67.mp4"): 2.10,
    # kb122
    ("kb122", "03.mp4"): 2.20,
    ("kb122", "08.mp4"): 10.40,
    ("kb122", "14.mp4"): 6.00,
    ("kb122", "20.mp4"): 1.95,
    ("kb122", "21.mp4"): 5.20,
    ("kb122", "26.mp4"): 2.60,
    ("kb122", "32.mp4"): 3.90,
    ("kb122", "37.mp4"): 3.80,
    ("kb122", "42_2.mp4"): 1.60,
    ("kb122", "49.mp4"): 2.50,
    ("kb122", "57.mp4"): 3.40,
    ("kb122", "64.mp4"): 3.10,
    # kb123
    ("kb123", "04.mp4"): 5.20,
    ("kb123", "10.mp4"): 4.20,
    ("kb123", "16.mp4"): 3.50,
    ("kb123", "22.mp4"): 2.50,
    ("kb123", "29.mp4"): 7.30,
    ("kb123", "35.mp4"): 4.40,
    ("kb123", "41.mp4"): 11.50,
    ("kb123", "46.mp4"): 5.60,
    ("kb123", "54.mp4"): 8.50,
    ("kb123", "59_2.mp4"): 3.10,
    ("kb123", "66.mp4"): 3.40,
    # kb124
    ("kb124", "04.mp4"): 4.20,
    ("kb124", "10.mp4"): 5.60,
    ("kb124", "17.mp4"): 2.60,
    ("kb124", "23.mp4"): 3.50,
    ("kb124", "29.mp4"): 3.90,
    ("kb124", "34.mp4"): 8.20,
    ("kb124", "40.mp4"): 3.60,
    ("kb124", "46.mp4"): 3.80,
    ("kb124", "53.mp4"): 4.50,
    ("kb124", "60.mp4"): 7.80,
    ("kb124", "66.mp4"): 3.20,
    # kb129
    ("kb129", "05.mp4"): 3.10,
    ("kb129", "11.mp4"): 3.80,
    ("kb129", "18.mp4"): 5.50,
    ("kb129", "24.mp4"): 4.20,
    ("kb129", "30.mp4"): 3.60,
    ("kb129", "35.mp4"): 1.60,
    ("kb129", "42.mp4"): 8.50,
    ("kb129", "48.mp4"): 2.80,
    ("kb129", "57.mp4"): 5.40,
    ("kb129", "63.mp4"): 2.10,
    ("kb129", "69.mp4"): 4.50,
    # kb130
    ("kb130", "03.mp4"): 3.30,
    ("kb130", "08.mp4"): 2.40,
    ("kb130", "15.mp4"): 2.80,
    ("kb130", "21.mp4"): 4.20,
    ("kb130", "27.mp4"): 5.20,
    ("kb130", "33.mp4"): 6.20,
    ("kb130", "38.mp4"): 6.50,
    ("kb130", "45.mp4"): 4.20,
    ("kb130", "55.mp4"): 4.10,
    ("kb130", "64.mp4"): 11.50,
    ("kb130", "68.mp4"): 6.20,
    # kb131
    ("kb131", "03.mp4"): 3.20,
    ("kb131", "08.mp4"): 3.80,
    ("kb131", "14.mp4"): 4.50,
    ("kb131", "20.mp4"): 2.80,
    ("kb131", "27.mp4"): 2.60,
    ("kb131", "33.mp4"): 6.50,
    ("kb131", "39.mp4"): 5.40,
    ("kb131", "44.mp4"): 3.90,
    ("kb131", "51.mp4"): 3.40,
    ("kb131", "60.mp4"): 6.20,
    ("kb131", "67.mp4"): 7.50,
}


def get_known_impact(project_id, clip_name):
    if project_id and (project_id, clip_name) in PROJECT_KNOWN_IMPACTS:
        return PROJECT_KNOWN_IMPACTS[(project_id, clip_name)]
    return KNOWN_IMPACTS.get(clip_name)


def is_setup_vo_line(text: str) -> bool:
    """Return True ONLY when VO line semantically sets up anticipation BEFORE the fail."""
    t = (text or "").strip().lower()
    aftermath_markers = [
        "decided", "woke up", "chose violence", "resigned", "canceled",
        "filed for", "sacrificed", "turned into", "turned a ", "demolish",
        "launched", "rejected", "missed the memo", "stayed at", "left the chat",
        "won this", "lost its", "remain undefeated", "gonna need", "walking home",
        "another tow truck", "repair invoice", "repair bill", "broke", "collapsed",
        "chose immediate", "chose swimming", "attitude adjustment",
    ]
    if any(m in t for m in aftermath_markers):
        return False
    setup_markers = [
        "when ", "watch ", "before ", "trying to", "try to ", "thought ",
        "thinks ", "about to", "ready to", "waiting ", "waited ",
        "starts with", "seemed like", "time to ", "but first",
    ]
    return any(m in t for m in setup_markers)


def detect_audio_transient(fpath, in_sec=0.0, clip_dur=None):
    """
    Detects the real physical impact timestamp (in seconds relative to in_sec)
    by combining 50ms window audio RMS + positive spectral onset flux via FFmpeg,
    with an OpenCV center-crop optical motion MAD fallback when audio is flat/silent.
    """
    if not fpath or not os.path.exists(fpath):
        return None
    fname = os.path.basename(fpath)
    if in_sec == 0.0 and fname in KNOWN_IMPACTS:
        return KNOWN_IMPACTS[fname]

    if clip_dur is None or clip_dur <= 0:
        try:
            r = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    fpath,
                ],
                capture_output=True, text=True,
            )
            clip_dur = max(0.0, float(r.stdout.strip()) - in_sec)
        except Exception:
            clip_dur = 0.0
    if clip_dur <= 0.30:
        return round(max(0.10, clip_dur * 0.50), 2)

    try:
        import numpy as np
        cmd = ["ffmpeg", "-v", "error"]
        if in_sec > 0.0:
            cmd += ["-ss", f"{in_sec:.3f}"]
        cmd += ["-i", fpath]
        if clip_dur is not None and clip_dur > 0.0:
            cmd += ["-t", f"{clip_dur:.3f}"]
        cmd += ["-vn", "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-"]
        raw = subprocess.run(cmd, capture_output=True).stdout
        if raw and len(raw) >= 3200:
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            win = 800
            n_wins = len(samples) // win
            if n_wins >= 6:
                frames = samples[: n_wins * win].reshape(n_wins, win)
                rms = np.sqrt(np.mean(frames ** 2, axis=1))
                peak_rms = float(np.max(rms))
                med_rms = float(np.median(rms)) + 1e-6
                if peak_rms > 0.012 and (peak_rms / med_rms) >= 1.32:
                    start_w = min(3, n_wins // 5)
                    end_w = max(start_w + 1, n_wins - min(3, n_wins // 6))
                    best_w = start_w
                    best_score = -1.0
                    for w_i in range(start_w, end_w):
                        prev_slice = rms[max(0, w_i - 6) : w_i]
                        local_base = float(np.mean(prev_slice)) if len(prev_slice) > 0 else med_rms
                        onset = max(0.0, float(rms[w_i]) - local_base)
                        score = 0.50 * float(rms[w_i]) + 0.50 * onset
                        if score > best_score:
                            best_score = score
                            best_w = w_i
                    t_imp = round((best_w + 0.5) * 0.05, 2)
                    return max(0.15, min(round(clip_dur - 0.15, 2), t_imp))
    except Exception:
        pass

    try:
        import cv2
        import numpy as np
        cap = cv2.VideoCapture(fpath)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        if in_sec > 0.0:
            cap.set(cv2.CAP_PROP_POS_MSEC, in_sec * 1000.0)
        step = max(1, int(round(fps / 10.0)))
        max_f = int(round(clip_dur * fps))
        prev_g = None
        best_t = clip_dur * 0.45
        best_mad = -1.0
        f_i = 0
        while f_i < max_f:
            ok, frm = cap.read()
            if not ok or frm is None:
                break
            if f_i % step == 0:
                t_rel = f_i / fps
                h, w = frm.shape[:2]
                crop = frm[int(h * 0.12) : int(h * 0.88), int(w * 0.28) : int(w * 0.72)]
                g = cv2.cvtColor(cv2.resize(crop, (64, 64)), cv2.COLOR_BGR2GRAY)
                if prev_g is not None and 0.20 <= t_rel <= clip_dur - 0.20:
                    mad = float(np.mean(cv2.absdiff(g, prev_g)))
                    if mad > best_mad:
                        best_mad = mad
                        best_t = t_rel
                prev_g = g
            f_i += 1
        cap.release()
        return round(max(0.15, min(clip_dur - 0.15, best_t)), 2)
    except Exception:
        return round(clip_dur * 0.45, 2)


def compute_dynamic_vo_timing(clip_dur_sec, dur_sec, impact_sec=None, text=""):
    """
    Semantic Impact-Reasoned VO Placement:
    - Setup lines ('When...', 'He thought...', 'Starts with...', 'Trying to...') finish
      cleanly ~0.25s BEFORE impact_sec (lead-in bridge, not stranded at 0.00s on long clips).
    - Consequence / Roast / Punchline lines ('...decided...', '...woke up...', '...turned into...',
      '...resigned...', etc.) NEVER play at 0.00s before the fail! They start right after
      impact_sec (+0.25s..+0.68s reaction beat, clamped within clip_dur_sec - dur_sec - 0.15s).
    """
    if clip_dur_sec < dur_sec or (clip_dur_sec - dur_sec - 0.15) < 0.15 - 1e-6:
        return round(max(0.08, (clip_dur_sec - dur_sec) * 0.5), 3), "ducked"

    eff_impact = impact_sec if impact_sec is not None else round(clip_dur_sec * 0.42, 2)
    eff_impact = max(0.15, min(clip_dur_sec - 0.25, float(eff_impact)))

    jitter_seed = int(round(clip_dur_sec * 37.0 + dur_sec * 73.0 + eff_impact * 19.0))
    reaction_gap = round(0.24 + (jitter_seed % 9) * 0.05, 3)  # 0.24s .. 0.64s

    max_valid_start = round(clip_dur_sec - dur_sec - 0.15, 4)
    setup_line = is_setup_vo_line(text)

    if setup_line:
        pre_max_start = round(eff_impact - dur_sec - 0.22, 4)
        if pre_max_start >= 0.18:
            # Lead directly into the impact so there isn't dead silence between setup VO and crash
            lead_start = max(0.20 + (jitter_seed % 5) * 0.05, eff_impact - dur_sec - 0.30)
            offset = min(pre_max_start, lead_start)
            mode = "premise"
        else:
            offset = min(max_valid_start, max(0.20, eff_impact + reaction_gap))
            mode = "aftermath"
    else:
        # Consequence / Roast / Aftermath line: ALWAYS land after (or right across late) impact!
        desired_post = eff_impact + reaction_gap
        if desired_post <= max_valid_start:
            offset = desired_post
            mode = "aftermath"
        else:
            # Late impact clip: anchor flush at clip tail so punchline lands right on/after climax, NEVER at 0.00s!
            offset = max(0.25, max_valid_start)
            mode = "aftermath"

    offset = max(0.15, min(max_valid_start, offset))
    if abs(offset - 1.50) < 0.06:
        if offset + 0.28 <= max_valid_start:
            offset += 0.28
        elif offset - 0.28 >= 0.15:
            offset -= 0.28
    return round(offset, 3), mode


def generate_one_vo(task):
    kb, idx_in_list, v3_idx, text = task
    voice_dir = rf"E:\ITV\Project\{kb}\voice"
    os.makedirs(voice_dir, exist_ok=True)
    fname = f"ElevenLabs_{kb}_vo{idx_in_list:02d}_v{v3_idx:02d}_ITV_5_gen_sp100_s50_sb75_v3.mp3"
    final_path = os.path.join(voice_dir, fname)
    raw_path = final_path + ".raw.mp3"

    if not (os.path.exists(final_path) and os.path.getsize(final_path) > 5000):
        prompt = f"{TAG_PREFIX} {text}"
        cmd = [
            ELEVENLABS_CMD, "say", prompt,
            "--voice", VOICE_ID,
            "--model", MODEL_ID,
            "--output", raw_path,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        # Re-encode with clean Xing TOC header at 44100Hz mono 128k so Premiere & ffprobe match to the exact sample
        ff_cmd = [
            "ffmpeg", "-y", "-v", "error", "-i", raw_path,
            "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "44100", "-ac", "1", "-write_xing", "1",
            final_path,
        ]
        subprocess.run(ff_cmd, check=True)
        if os.path.exists(raw_path):
            os.remove(raw_path)

    dur_str = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", final_path
    ], text=True).strip()
    dur_sec = float(dur_str)
    return (kb, idx_in_list, v3_idx, text, fname, final_path, dur_sec)


def generate_all_vos():
    tasks = []
    for kb, items in VO_MANIFEST.items():
        for i, (v3_idx, text) in enumerate(items, 1):
            tasks.append((kb, i, v3_idx, text))

    print(f"Generating {len(tasks)} VO MP3 files via ElevenLabs ({VOICE_ID} / {MODEL_ID})...")
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(generate_one_vo, t): t for t in tasks}
        done_cnt = 0
        for fut in concurrent.futures.as_completed(futs):
            kb, idx_in_list, v3_idx, text, fname, final_path, dur_sec = fut.result()
            done_cnt += 1
            results.setdefault(kb, []).append((idx_in_list, v3_idx, text, fname, final_path, dur_sec))
            print(f"  [{done_cnt:02d}/{len(tasks)}] {kb} #{idx_in_list:02d} (V#{v3_idx:02d}, {dur_sec:.2f}s): {fname}")

    for kb in results:
        results[kb].sort(key=lambda x: x[0])
    return results


# XML Helpers for Premiere Pro .prproj
def load_xml(path):
    with gzip.open(path, "rb") as f:
        root = ET.fromstring(f.read())
    by_id = {el.attrib["ObjectID"]: el for el in root if "ObjectID" in el.attrib}
    by_uid = {el.attrib["ObjectUID"]: el for el in root if "ObjectUID" in el.attrib}
    return root, by_id, by_uid


def iter_no_pvs(el):
    if el.tag == "ProjectViewState.List":
        return
    yield el
    for c in el:
        yield from iter_no_pvs(c)


def iter_for_clone(el):
    if el.tag in ("ProjectViewState.List", "HeadTransition", "TailTransition", "Links"):
        return
    yield el
    for c in el:
        yield from iter_for_clone(c)


def collect_subgraph(start_kind, start_key, by_id, by_uid, stop_ids=None, stop_uids=None):
    stop_ids = stop_ids or set()
    stop_uids = stop_uids or set()
    visited_id, visited_uid = [], []
    seen_id, seen_uid = set(), set()
    queue = [(start_kind, start_key)]
    while queue:
        kind, key = queue.pop(0)
        if kind == "id":
            if key in seen_id or key in stop_ids or key not in by_id:
                continue
            seen_id.add(key)
            visited_id.append(key)
            el = by_id[key]
        else:
            if key in seen_uid or key in stop_uids or key not in by_uid:
                continue
            seen_uid.add(key)
            visited_uid.append(key)
            el = by_uid[key]
        for sub in iter_for_clone(el):
            if "ObjectRef" in sub.attrib:
                queue.append(("id", sub.attrib["ObjectRef"]))
            if "ObjectURef" in sub.attrib:
                queue.append(("uid", sub.attrib["ObjectURef"]))
    return visited_id, visited_uid


def clone_subgraph_into(start_kind, start_key, src_id, src_uid, dst_root, next_oid_fn, stop_ids=None, stop_uids=None):
    vis_ids, vis_uids = collect_subgraph(start_kind, start_key, src_id, src_uid, stop_ids, stop_uids)
    id_map = {old_id: str(next_oid_fn()) for old_id in vis_ids}
    uid_map = {old_uid: str(uuid.uuid4()) for old_uid in vis_uids}

    cloned_els = []
    for old_id in vis_ids:
        el = copy.deepcopy(src_id[old_id])
        el.attrib["ObjectID"] = id_map[old_id]
        cloned_els.append(el)
    for old_uid in vis_uids:
        el = copy.deepcopy(src_uid[old_uid])
        el.attrib["ObjectUID"] = uid_map[old_uid]
        cloned_els.append(el)

    for el in cloned_els:
        if el.tag in ("VideoClipTrackItem", "AudioClipTrackItem"):
            cti = el.find("ClipTrackItem")
            if cti is not None:
                for t in list(cti):
                    if t.tag in ("HeadTransition", "TailTransition"):
                        cti.remove(t)
                    elif t.tag == "Links":
                        t.clear()
                        t.attrib["Version"] = "1"
        for sub in iter_no_pvs(el):
            if "ObjectRef" in sub.attrib and sub.attrib["ObjectRef"] in id_map:
                sub.attrib["ObjectRef"] = id_map[sub.attrib["ObjectRef"]]
            if "ObjectURef" in sub.attrib and sub.attrib["ObjectURef"] in uid_map:
                sub.attrib["ObjectURef"] = uid_map[sub.attrib["ObjectURef"]]
            if sub.tag == "ClipID" and (sub.text or "").strip():
                sub.text = str(uuid.uuid4())
            if el.tag in ("VideoClipTrackItem", "AudioClipTrackItem") and sub.tag == "ID" and "-" in (sub.text or ""):
                sub.text = str(uuid.uuid4())
        dst_root.append(el)

    root_new_key = id_map[start_key] if start_kind == "id" else uid_map[start_key]
    return root_new_key, id_map, uid_map


def canonicalize_prproj(root, bh_pool):
    for e in root.iter():
        bh = e.attrib.get("BinaryHash")
        if bh and (e.text or "").strip():
            bh_pool[bh] = e.text

    els = list(root)[1:]
    by_key = {}
    for e in els:
        if "ObjectID" in e.attrib:
            by_key[("id", e.attrib["ObjectID"])] = e
        elif "ObjectUID" in e.attrib:
            by_key[("uid", e.attrib["ObjectUID"])] = e

    queue = [("id", "1")]
    seen = {
        ("id", "1"),
        ("id", "0"),
        ("uid", "00000000-0000-0000-0000-000000000000"),
    }
    bfs_order = []
    id_discovery_order = ["1"]

    while queue:
        k = queue.pop(0)
        if k not in by_key:
            raise KeyError(f"Missing referenced object in PremiereData: {k}")
        bfs_order.append(k)
        e = by_key[k]
        for sub in iter_no_pvs(e):
            if "ObjectRef" in sub.attrib:
                nk = ("id", sub.attrib["ObjectRef"])
                if nk not in seen:
                    seen.add(nk)
                    queue.append(nk)
                    id_discovery_order.append(sub.attrib["ObjectRef"])
            if "ObjectURef" in sub.attrib:
                nk = ("uid", sub.attrib["ObjectURef"])
                if nk not in seen:
                    seen.add(nk)
                    queue.append(nk)

    id_map = {"1": "1"}
    next_id = 3
    for old_id in id_discovery_order[1:]:
        id_map[old_id] = str(next_id)
        next_id += 1

    new_root = ET.Element("PremiereData", {"Version": "3"})
    ET.SubElement(new_root, "Project", {"ObjectRef": "1"})

    for k in bfs_order:
        e = by_key[k]
        if k[0] == "id":
            e.attrib["ObjectID"] = id_map[k[1]]
        for sub in iter_no_pvs(e):
            if "ObjectRef" in sub.attrib and sub.attrib["ObjectRef"] in id_map:
                sub.attrib["ObjectRef"] = id_map[sub.attrib["ObjectRef"]]
        new_root.append(e)

    all_node_ids = [
        int(n.findtext("ID"))
        for n in new_root.iter("Node")
        if n.findtext("ID") and n.findtext("ID").strip().isdigit()
    ]
    next_node_id = max(all_node_ids, default=1000000) + 1
    seen_node_ids = set()
    for n in new_root.iter("Node"):
        id_el = n.find("ID")
        if id_el is not None and id_el.text and id_el.text.strip().isdigit():
            val = int(id_el.text.strip())
            if val in seen_node_ids:
                id_el.text = str(next_node_id)
                seen_node_ids.add(next_node_id)
                next_node_id += 1
            else:
                seen_node_ids.add(val)
    proj_next_id_el = new_root.find("./Project[@ObjectID='1']/NextID")
    if proj_next_id_el is not None:
        proj_next_id_el.text = str(max(seen_node_ids, default=1000000) + 1)

    seen_uuids = set()
    for e in new_root.iter():
        if e.tag in ("ID", "ClipID") and e.text and "-" in e.text and len(e.text.strip()) == 36:
            uval = e.text.strip()
            if uval in seen_uuids:
                new_u = str(uuid.uuid4())
                e.text = new_u
                seen_uuids.add(new_u)
            else:
                seen_uuids.add(uval)

    seen_bh = set()
    for e in new_root.iter():
        bh = e.attrib.get("BinaryHash")
        if bh:
            if bh not in seen_bh:
                if bh not in bh_pool:
                    raise KeyError(f"Missing BinaryHash payload for {bh}")
                e.text = bh_pool[bh]
                seen_bh.add(bh)
            else:
                e.text = None

    return new_root, id_map


def serialize_prproj_bytes(root):
    ET.indent(root, space="\t")
    xml_str = '<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(root, encoding="unicode") + "\n\n"
    xml_str = re.sub(
        r"<Project\.Metadata\.Schema>(.*?)</Project\.Metadata\.Schema>",
        lambda m: "<Project.Metadata.Schema>" + m.group(1).replace("\n", "&#10;") + "</Project.Metadata.Schema>",
        xml_str,
        flags=re.S,
    )
    xml_str = xml_str.replace(" />", "/>")
    raw_bytes = xml_str.encode("utf-8")
    comp = gzip.compress(raw_bytes, compresslevel=6, mtime=0)
    return comp[:8] + b"\x00\x0a" + comp[10:]


def get_main_tg(root, by_uid, tg_tag):
    best_tg = None
    best_count = -1
    for tg in root.iter(tg_tag):
        total = 0
        for tr in tg.findall("./TrackGroup/Tracks/Track"):
            t_el = by_uid.get(tr.attrib.get("ObjectURef", ""))
            if t_el is not None:
                total += len(t_el.findall(".//TrackItems/TrackItem"))
        if total > best_count:
            best_count = total
            best_tg = tg
    return best_tg


def inject_vos_into_projects(vo_results):
    # Load kb106 as template source for A2 VO AudioClipTrackItem and ClipProjectItem
    root106, id106, uid106 = load_xml(r"E:\ITV\Project\kb106\kb106.prproj")
    global_bh_pool = {}
    for e in root106.iter():
        bh = e.attrib.get("BinaryHash")
        if bh and (e.text or "").strip():
            global_bh_pool[bh] = e.text

    atg106 = get_main_tg(root106, uid106, "AudioTrackGroup")
    a2_uid_106 = atg106.findall("./TrackGroup/Tracks/Track")[1].attrib["ObjectURef"]
    tmpl_ti_id = next(
        c.attrib["ObjectRef"]
        for c in uid106[a2_uid_106].findall(".//TrackItems/TrackItem")
        if id106[c.attrib["ObjectRef"]].findtext(".//ESP.Tag") == "dialog"
    )
    tmpl_ti_el = id106[tmpl_ti_id]
    tmpl_sc_id = tmpl_ti_el.find(".//SubClip").attrib["ObjectRef"]
    tmpl_sc_el = id106[tmpl_sc_id]
    tmpl_mc_uid = tmpl_sc_el.find("MasterClip").attrib["ObjectURef"]
    tmpl_mc_el = uid106[tmpl_mc_uid]
    tmpl_log_id = tmpl_mc_el.find("LoggingInfo").attrib["ObjectRef"]
    tmpl_ac_id = tmpl_sc_el.find("Clip").attrib["ObjectRef"]
    tmpl_ac_el = id106[tmpl_ac_id]
    tmpl_ams_id = tmpl_ac_el.find(".//Source").attrib["ObjectRef"]
    tmpl_ams_el = id106[tmpl_ams_id]
    tmpl_med_uid = tmpl_ams_el.find(".//Media").attrib["ObjectURef"]
    tmpl_med_el = uid106[tmpl_med_uid]
    tmpl_astr_id = tmpl_med_el.find("AudioStream").attrib["ObjectRef"]
    tmpl_cpi_el = next(
        c for c in root106.iter("ClipProjectItem")
        if c.find("MasterClip") is not None and c.find("MasterClip").attrib.get("ObjectURef") == tmpl_mc_uid
    )

    placement_summary = {}

    for kb in ["kb107", "kb108", "kb109", "kb110"]:
        prproj_path = rf"E:\ITV\Project\{kb}\{kb}.prproj"
        pre_vo_bak = prproj_path + ".pre_vo_bak"
        if not os.path.exists(pre_vo_bak):
            shutil.copy2(prproj_path, pre_vo_bak)
        else:
            # Always start from clean 10-track pre-VO backup so re-runs are idempotent
            shutil.copy2(pre_vo_bak, prproj_path)

        root, by_id, by_uid = load_xml(prproj_path)
        for e in root.iter():
            bh = e.attrib.get("BinaryHash")
            if bh and (e.text or "").strip():
                global_bh_pool[bh] = e.text

        max_oid = max(int(k) for k in by_id.keys())
        def next_oid():
            nonlocal max_oid
            max_oid += 1
            return max_oid

        def refresh_maps():
            by_id.clear()
            by_uid.clear()
            for el in root:
                if "ObjectID" in el.attrib:
                    by_id[el.attrib["ObjectID"]] = el
                if "ObjectUID" in el.attrib:
                    by_uid[el.attrib["ObjectUID"]] = el

        vtg = get_main_tg(root, by_uid, "VideoTrackGroup")
        atg = get_main_tg(root, by_uid, "AudioTrackGroup")

        def get_track_items_container(tg_el, idx):
            t_uid = tg_el.findall("./TrackGroup/Tracks/Track")[idx].attrib["ObjectURef"]
            t_el = by_uid[t_uid]
            ci = t_el.find("./ClipTrack/ClipItems")
            ti_cont = ci.find("TrackItems")
            if ti_cont is None:
                ti_cont = ET.Element("TrackItems", {"Version": "1"})
                ci.insert(0, ti_cont)
            return ti_cont

        v3_cont = get_track_items_container(vtg, 2)
        v3_clips = []
        for idx, c in enumerate(v3_cont.findall("TrackItem")):
            ti_el = by_id[c.attrib["ObjectRef"]]
            st = int(ti_el.findtext(".//Start") or 0)
            en = int(ti_el.findtext(".//End") or 0)
            sc = by_id[ti_el.find(".//SubClip").attrib["ObjectRef"]]
            nm = sc.findtext("Name") or ""
            v3_clips.append({
                "index": idx,
                "name": nm,
                "start_ticks": st,
                "end_ticks": en,
                "start_sec": st / TICKS_PER_SEC,
                "end_sec": en / TICKS_PER_SEC,
            })

        a1_cont = get_track_items_container(atg, 0)
        a2_cont = get_track_items_container(atg, 1)
        a3_cont = get_track_items_container(atg, 2)

        # Clear any existing A2 items
        a2_cont.clear()
        a2_cont.attrib["Version"] = "1"

        vtg = next(root.iter("VideoTrackGroup"))
        v_tracks = vtg.findall("./TrackGroup/Tracks/Track")
        v5_cont = get_track_items_container(vtg, 4) if len(v_tracks) >= 5 else None

        rpi_el = root.find("./RootProjectItem[@ObjectUID]")
        rpi_items_el = rpi_el.find("./ProjectItemContainer/Items")

        a2_placed_intervals = []
        kb_summary = []

        for idx_in_list, v3_idx, text, fname, final_path, dur_sec in vo_results[kb]:
            cinfo = v3_clips[v3_idx]
            clip_dur_sec = cinfo["end_sec"] - cinfo["start_sec"]
            impact_sec = cinfo.get("impact_sec")
            ideal_offset, placement_mode = compute_dynamic_vo_timing(clip_dur_sec, dur_sec, impact_sec, text)
            vo_start_sec = cinfo["start_sec"] + ideal_offset
            vo_end_sec = vo_start_sec + dur_sec

            start_ticks = int(round(vo_start_sec * TICKS_PER_SEC))
            samples = int(round(dur_sec * 44100))
            dur_ticks = samples * 5760000
            end_ticks = start_ticks + dur_ticks

            # Synchronize Track V5 MOGRT Subtitle item if present (100% start, end, duration match)
            if v5_cont is not None and idx_in_list < len(v5_cont.findall("TrackItem")):
                v5_ti_oid = v5_cont.findall("TrackItem")[idx_in_list].attrib["ObjectRef"]
                v5_ti_el = by_id.get(v5_ti_oid)
                if v5_ti_el is not None:
                    v5_inner = v5_ti_el.find("./ClipTrackItem/TrackItem") or v5_ti_el.find(".//TrackItem")
                    if v5_inner is not None:
                        if v5_inner.find("Start") is not None:
                            v5_inner.find("Start").text = str(start_ticks)
                        if v5_inner.find("End") is not None:
                            v5_inner.find("End").text = str(end_ticks)
                    v5_sc_ref = v5_ti_el.find(".//SubClip")
                    if v5_sc_ref is not None and v5_sc_ref.attrib.get("ObjectRef") in by_id:
                        v5_sc = by_id[v5_sc_ref.attrib["ObjectRef"]]
                        if v5_sc.find("InPoint") is not None:
                            v5_sc.find("InPoint").text = "0"
                        if v5_sc.find("OutPoint") is not None:
                            v5_sc.find("OutPoint").text = str(dur_ticks)

            # Clone A2 TrackItem subgraph from kb106
            new_ti_id, id_map_vo, uid_map_vo = clone_subgraph_into("id", tmpl_ti_id, id106, uid106, root, next_oid)
            refresh_maps()

            # Update cloned objects
            new_ti_el = by_id[new_ti_id]
            ti_inner = new_ti_el.find("./ClipTrackItem/TrackItem")
            ti_inner.find("Start").text = str(start_ticks)
            ti_inner.find("End").text = str(end_ticks)

            new_sc_el = by_id[id_map_vo[tmpl_sc_id]]
            new_sc_el.find("Name").text = fname

            new_mc_uid = uid_map_vo[tmpl_mc_uid]
            new_mc_el = by_uid[new_mc_uid]
            new_mc_el.find("Name").text = fname

            new_log_el = by_id[id_map_vo[tmpl_log_id]]
            new_log_el.find("ClipName").text = fname
            new_log_el.find("MediaOutPoint").text = str(dur_ticks)

            new_ac_el = by_id[id_map_vo[tmpl_ac_id]]
            new_ac_el.find("./Clip/InPoint").text = "0"
            new_ac_el.find("./Clip/OutPoint").text = str(dur_ticks)
            ac_props = new_ac_el.find("./Clip/Node/Properties")
            if ac_props is not None:
                for p_tag in ("ESP.LoudnessSection.Analysis.TimeOut", "ESP.ClaritySection.Analysis.TimeOut"):
                    p_el = ac_props.find(p_tag)
                    if p_el is not None:
                        p_el.text = str(dur_ticks)

            new_ams_el = by_id[id_map_vo[tmpl_ams_id]]
            new_ams_el.find("OriginalDuration").text = str(dur_ticks)

            new_med_uid = uid_map_vo[tmpl_med_uid]
            new_med_el = by_uid[new_med_uid]
            new_med_el.find("Title").text = fname
            new_med_el.find("FilePath").text = final_path
            new_med_el.find("ActualMediaFilePath").text = final_path
            for rp_el in new_med_el.findall("RelativePath"):
                rp_el.text = f".\\voice\\{fname}"
            fk_el = new_med_el.find("FileKey")
            if fk_el is not None:
                fk_el.text = str(uuid.uuid4())

            new_astr_el = by_id[id_map_vo[tmpl_astr_id]]
            new_astr_el.find("Duration").text = str(dur_ticks)
            for cache_tag in ("ConformedAudioPath", "PeakFilePath"):
                c_el = new_astr_el.find(cache_tag)
                if c_el is not None:
                    new_astr_el.remove(c_el)

            # Append to Track A2
            ti_ref = ET.SubElement(a2_cont, "TrackItem")
            ti_ref.attrib["Index"] = str(len(a2_cont.findall("TrackItem")) - 1)
            ti_ref.attrib["ObjectRef"] = str(new_ti_id)

            # Also add ClipProjectItem to RootProjectItem so it shows in Project Bin
            if rpi_items_el is not None:
                new_cpi = copy.deepcopy(tmpl_cpi_el)
                new_cpi_uid = str(uuid.uuid4())
                new_cpi.attrib["ObjectUID"] = new_cpi_uid
                new_cpi.find("./ProjectItem/Name").text = fname
                new_cpi.find("MasterClip").attrib["ObjectURef"] = new_mc_uid
                root.append(new_cpi)
                by_uid[new_cpi_uid] = new_cpi
                item_ref = ET.SubElement(rpi_items_el, "Item")
                item_ref.attrib["Index"] = str(len(rpi_items_el.findall("Item")) - 1)
                item_ref.attrib["ObjectURef"] = new_cpi_uid

            a2_placed_intervals.append((start_ticks, end_ticks))
            kb_summary.append({
                "vo_num": idx_in_list,
                "v3_idx": v3_idx,
                "v3_name": cinfo["name"],
                "v3_start": cinfo["start_sec"],
                "v3_end": cinfo["end_sec"],
                "vo_start": vo_start_sec,
                "vo_end": vo_end_sec,
                "dur_sec": dur_sec,
                "fname": fname,
                "text": text,
            })

        # Remove any A3 SFX that collides with our A2 VO intervals (INV-04 compliance)
        kept_a3 = []
        removed_a3 = 0
        for c in a3_cont.findall("TrackItem"):
            oid = c.attrib["ObjectRef"]
            ti_el = by_id[oid]
            st = int(ti_el.findtext(".//Start") or 0)
            en = int(ti_el.findtext(".//End") or 0)
            if any(st < b and en > a for a, b in a2_placed_intervals):
                removed_a3 += 1
                continue
            kept_a3.append(oid)
        a3_cont.clear()
        a3_cont.attrib["Version"] = "1"
        for i, oid in enumerate(kept_a3):
            el = ET.SubElement(a3_cont, "TrackItem")
            el.attrib["Index"] = str(i)
            el.attrib["ObjectRef"] = str(oid)

        # Mute/remove A1 original audio on clips flagged with "tắt tiếng cmt" / "đè lên cmt cũ nhaa"
        mute_v3_set = MUTE_A1_CLIPS.get(kb, set())
        removed_a1_notes = 0
        if mute_v3_set:
            mute_intervals = [(v3_clips[i]["start_ticks"], v3_clips[i]["end_ticks"]) for i in mute_v3_set]
            kept_a1 = []
            for c in a1_cont.findall("TrackItem"):
                oid = c.attrib["ObjectRef"]
                ti_el = by_id[oid]
                st = int(ti_el.findtext(".//Start") or 0)
                en = int(ti_el.findtext(".//End") or 0)
                mid = (st + en) // 2
                if any(a <= mid <= b for a, b in mute_intervals):
                    removed_a1_notes += 1
                    continue
                kept_a1.append(oid)
            a1_cont.clear()
            a1_cont.attrib["Version"] = "1"
            for i, oid in enumerate(kept_a1):
                el = ET.SubElement(a1_cont, "TrackItem")
                el.attrib["Index"] = str(i)
                el.attrib["ObjectRef"] = str(oid)

        # Canonicalize and write .prproj
        canon_root, id_map = canonicalize_prproj(root, dict(global_bh_pool))
        gz_bytes = serialize_prproj_bytes(canon_root)
        with open(prproj_path, "wb") as f:
            f.write(gz_bytes)

        placement_summary[kb] = kb_summary
        print(
            f"[{kb.upper()}] Saved {prproj_path}: A2={len(kb_summary)} VO clips | "
            f"A3={len(kept_a3)} SFX (-{removed_a3} overlaps) | "
            f"A1 muted_by_note={removed_a1_notes} | Total Objects={len(id_map)}"
        )

    out_json = r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\611dd2ed-5c86-4708-a512-949bc7796de0\scratch\vo_placement_107_110.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(placement_summary, f, ensure_ascii=False, indent=2)
    print(f"Saved full placement report to {out_json}")


if __name__ == "__main__":
    res = generate_all_vos()
    inject_vos_into_projects(res)
