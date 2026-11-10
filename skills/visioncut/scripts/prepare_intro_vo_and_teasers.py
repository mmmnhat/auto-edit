import json
import os
import subprocess
import sys
import numpy as np
from faster_whisper import WhisperModel

sys.stdout.reconfigure(encoding="utf-8")

INTRO_CONFIG = {
    "kb118": {
        "hook": "Here comes another round of chaos, so get ready to crack up at some of the wildest fails on the internet?!",
        "middle": "Today's lineup is packed with slip-ups, midair regrets, and moments you won't believe!",
        "cta": "Let's get started!",
        "teaser1_clip": "itv.kb118.1.mp4",
        "middle_teasers": [
            {"clip": "05.mp4", "in_sec": 1.0, "dur_sec": 1.0},
            {"clip": "07.mp4", "in_sec": 2.0, "dur_sec": 0.8},
            {"clip": "08.mp4", "in_sec": 1.5, "dur_sec": 1.1},
            {"clip": "11.mp4", "in_sec": 0.5, "dur_sec": 0.9},
            {"clip": "13.mp4", "in_sec": 2.0, "dur_sec": 1.0},
            {"clip": "14.mp4", "in_sec": 1.0, "dur_sec": 0.8},
            {"clip": "itv.kb118.4.mp4", "in_sec": 3.0, "dur_sec": 1.0},
        ],
        "final_teaser_clip": "itv.kb118.6.mp4",
    },
    "kb119": {
        "hook": "Oh boy, here we go again, so get comfy, sit back and brace yourself!",
        "middle": "The wildest, most unexpected on the clock disasters are about to roll right in!",
        "cta": "Let's go!",
        "teaser1_clip": "itv.kb119.1.mp4",
        "middle_teasers": [
            {"clip": "01.mp4", "in_sec": 1.0, "dur_sec": 1.0},
            {"clip": "03.mp4", "in_sec": 2.0, "dur_sec": 0.8},
            {"clip": "04.mp4", "in_sec": 1.5, "dur_sec": 1.1},
            {"clip": "07.mp4", "in_sec": 0.5, "dur_sec": 0.9},
            {"clip": "09.mp4", "in_sec": 2.0, "dur_sec": 1.0},
            {"clip": "14.mp4", "in_sec": 1.0, "dur_sec": 0.8},
            {"clip": "itv.kb119.3.mp4", "in_sec": 3.0, "dur_sec": 1.0},
        ],
        "final_teaser_clip": "itv.kb119.5.mp4",
    },
    "kb120": {
        "hook": "Fasten your seatbelts, folks, and get ready for today's funniest on the clock disasters?!",
        "middle": "Sit back, relax, and enjoy the pure chaos unfolding right in front of you!",
        "cta": "Let's jump right in!",
        "teaser1_clip": "itv.kb120.1.mp4",
        "middle_teasers": [
            {"clip": "02.mp4", "in_sec": 1.0, "dur_sec": 1.0},
            {"clip": "03.mp4", "in_sec": 2.0, "dur_sec": 0.8},
            {"clip": "06.mp4", "in_sec": 1.5, "dur_sec": 1.1},
            {"clip": "08.mp4", "in_sec": 0.5, "dur_sec": 0.9},
            {"clip": "14.mp4", "in_sec": 2.0, "dur_sec": 1.0},
            {"clip": "16.mp4", "in_sec": 1.0, "dur_sec": 0.8},
            {"clip": "itv.kb120.5.mp4", "in_sec": 2.5, "dur_sec": 1.0},
        ],
        "final_teaser_clip": "itv.kb120.7.mp4",
    },
    "kb121": {
        "hook": "Today's lineup is absolutely wild, and we've rounded up the week's funniest workplace moments!",
        "middle": "So brace yourself for slip-ups, spills, and total disasters guaranteed to drop your jaw!",
        "cta": "Let's dive right in!",
        "teaser1_clip": "itv.kb121.1.mp4",
        "middle_teasers": [
            {"clip": "02.mp4", "in_sec": 1.0, "dur_sec": 1.0},
            {"clip": "03.mp4", "in_sec": 2.0, "dur_sec": 0.8},
            {"clip": "04.mp4", "in_sec": 1.5, "dur_sec": 1.1},
            {"clip": "09.mp4", "in_sec": 0.5, "dur_sec": 0.9},
            {"clip": "10.mp4", "in_sec": 2.0, "dur_sec": 1.0},
            {"clip": "14.mp4", "in_sec": 1.0, "dur_sec": 0.8},
            {"clip": "itv.kb121.7.mp4", "in_sec": 2.0, "dur_sec": 1.0},
        ],
        "final_teaser_clip": "itv.kb121.8.mp4",
    },
}

def load_audio_np(fp):
    cmd = ['ffmpeg', '-v', 'error', '-i', fp, '-f', 's16le', '-ac', '1', '-ar', '16000', '-']
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

whisper_model = WhisperModel("base", device="cpu", compute_type="int8")

print("=== Generating Dynamically Aligned Intro VO & Teaser Plans ===")

for pid, cfg in INTRO_CONFIG.items():
    print(f"\n==================== {pid} ====================")
    voice_dir = rf"E:\ITV\Project\{pid}\voice"
    intro_mp3 = os.path.join(voice_dir, f"intro_{pid}.mp3")
    intro_txt = os.path.join(voice_dir, f"intro_{pid}.txt")
    
    full_script = f"{cfg['hook']} {cfg['middle']} {cfg['cta']}"
    with open(intro_txt, "w", encoding="utf-8") as f:
        f.write(full_script + "\n")
    print(f"  ✓ Verified script in {os.path.basename(intro_txt)}")

    # Probe duration
    p_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", intro_mp3]
    dur = float(subprocess.run(p_cmd, capture_output=True, text=True).stdout.strip())
    print(f"  ✓ Intro audio {os.path.basename(intro_mp3)}: duration={dur:.2f}s")
    assert dur > 10.0, f"Intro audio duration {dur:.2f}s <= 10.0s!"

    # Transcribe audio for exact word/clause timestamps
    audio_np = load_audio_np(intro_mp3)
    segments, _ = whisper_model.transcribe(audio_np, word_timestamps=True)
    
    word_tokens = []
    for seg in segments:
        for w in seg.words:
            word_tokens.append({"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)})
            
    print(f"  ✓ Extracted {len(word_tokens)} word timestamps via Whisper")
    
    # 1. Dynamic Hook Alignment
    clean_hook = cfg["hook"].replace("?!", "").replace("!", "").replace(",", "").replace(".", "").split()
    hook_word_count = len(clean_hook)
    hook_idx = min(hook_word_count - 1, len(word_tokens) - 1)
    hook_end_token = word_tokens[hook_idx]
    segment_1a_hook_end_sec = round(hook_end_token["end"], 3)
    print(f"  ✓ Dynamic Hook Alignment: '{clean_hook[-1]}' at token #{hook_idx} -> end={segment_1a_hook_end_sec}s")

    # 2. Dynamic CTA Spoken Duration
    clean_cta = cfg["cta"].replace("?!", "").replace("!", "").replace(",", "").replace(".", "").split()
    cta_word_count = len(clean_cta)
    cta_tokens = word_tokens[-cta_word_count:]
    part_a_cta_dur_sec = round(cta_tokens[-1]["end"] - cta_tokens[0]["start"], 2)
    print(f"  ✓ Dynamic CTA Duration: '{cfg['cta']}' ({len(cta_tokens)} tokens: {cta_tokens[0]['start']}s..{cta_tokens[-1]['end']}s) -> dur={part_a_cta_dur_sec}s")

    # 3. Assemble and save intro teaser plan
    plan = {
        "project": pid,
        "script": full_script,
        "hook": cfg["hook"],
        "cta": cfg["cta"],
        "intro_vo_path": intro_mp3,
        "intro_vo_duration": dur,
        "word_tokens": word_tokens,
        "teaser1": {
            "clip": cfg["teaser1_clip"],
            "segment_1a_hook_end_sec": segment_1a_hook_end_sec,
            "segment_1b_crash_gap_dur_sec": 1.80,
        },
        "middle_teasers": cfg["middle_teasers"],
        "final_teaser": {
            "clip": cfg["final_teaser_clip"],
            "part_a_cta_dur_sec": part_a_cta_dur_sec,
            "part_b_pre_warning_gap_dur_sec": 1.80,
        },
        "warning_card_frames": 20,
    }
    
    plan_path = rf"E:\ITV\Project\{pid}\intro_teaser_plan.json"
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Saved {os.path.basename(plan_path)}")

print("\nDynamic Intro VO & Teaser Preparation Complete!")
