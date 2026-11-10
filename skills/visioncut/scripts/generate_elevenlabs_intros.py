import glob
import json
import os
import subprocess
import sys
import urllib.request
from faster_whisper import WhisperModel
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
SCRATCH_DIR = r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\24f0c3b3-80bc-4398-9d17-003870b04d4b\scratch"
sys.path.insert(0, SCRATCH_DIR)
from step3_gen_body_vos_kb119_121 import get_elevenlabs_token

# Exact user-specified parameters for ITV 5
VOICE_ID = "ITLDKaHYPRfCyyrPpZu2"  # ITV 5
MODEL_ID = "eleven_v3"
TAG_PREFIX = "[sarcastic, dry humor, rushed, fast, shout, fast-paced, mooth delivery]"

# Target scripts for all 4 projects
# Each has:
# - ZERO "Hello everyone" or "Helloooo everyone"
# - NO "everyone" in the first 2.5s
# - Target duration > 10.0s (e.g. 10.5s - 12.5s)
# - Clear hook, middle, and cta clauses
INTROS = {
    "kb118": {
        "hook": "Here comes another round of chaos, so get ready to crack up at some of the wildest fails on the internet?!",
        "middle": "Today's lineup is packed with slip-ups, midair regrets, and moments you won't believe!",
        "cta": "Let's get started!",
    },
    "kb119": {
        "hook": "Oh boy, here we go again, so get comfy, sit back and brace yourself!",
        "middle": "The wildest, most unexpected on the clock disasters are about to roll right in!",
        "cta": "Let's go!",
    },
    "kb120": {
        "hook": "Fasten your seatbelts, folks, and get ready for today's funniest on the clock disasters?!",
        "middle": "Sit back, relax, and enjoy the pure chaos unfolding right in front of you!",
        "cta": "Let's jump right in!",
    },
    "kb121": {
        "hook": "Today's lineup is absolutely wild, and we've rounded up the week's funniest workplace moments!",
        "middle": "So brace yourself for slip-ups, spills, and total disasters guaranteed to drop your jaw!",
        "cta": "Let's dive right in!",
    },
}

def call_elevenlabs(token, prompt, out_mp3):
    raw_path = out_mp3 + ".raw.mp3"
    url = "https://api.us.elevenlabs.io/v1/text-to-dialogue"
    # lang=auto -> omit language_code
    body = json.dumps({
        "inputs": [
            {
                "text": prompt,
                "voice_id": VOICE_ID,
            }
        ],
        "model_id": MODEL_ID,
        "settings": {
            "stability": 0.0,
        },
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
            "Origin": "https://elevenlabs.io",
            "Referer": "https://elevenlabs.io/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        mp3_bytes = resp.read()

    with open(raw_path, "wb") as f:
        f.write(mp3_bytes)

    ff_cmd = [
        "ffmpeg", "-y", "-v", "error", "-i", raw_path,
        "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "44100", "-ac", "1", "-write_xing", "1",
        out_mp3,
    ]
    subprocess.run(ff_cmd, check=True)
    if os.path.exists(raw_path):
        os.remove(raw_path)

    dur_str = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", out_mp3
    ], text=True).strip()
    return float(dur_str)

if __name__ == "__main__":
    token = get_elevenlabs_token()
    assert token, "Could not obtain ElevenLabs token!"

    for pid, data in INTROS.items():
        script = f"{data['hook']} {data['middle']} {data['cta']}"
        prompt = f"{TAG_PREFIX} {script}"
        voice_dir = rf"E:\ITV\Project\{pid}\voice"
        os.makedirs(voice_dir, exist_ok=True)

        txt_path = os.path.join(voice_dir, f"intro_{pid}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(script + "\n")

        mp3_path = os.path.join(voice_dir, f"intro_{pid}.mp3")
        print(f"Generating ElevenLabs ITV 5 (eleven_v3) intro for {pid}...")
        dur = call_elevenlabs(token, prompt, mp3_path)
        print(f"  [{pid}] Generated {mp3_path}: dur={dur:.3f}s")
        assert dur > 10.0, f"Duration {dur:.3f}s <= 10.0s!"

        # Also copy to any other intro mp3 file in that dir
        for old_f in glob.glob(os.path.join(voice_dir, f"ElevenLabs_{pid}_intro_*.mp3")):
            if not old_f.endswith(".orig_hello_bak.mp3") and not old_f.endswith(".raw.mp3"):
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mp3_path, "-c", "copy", old_f], check=True)

    print("\nAll 4 Intro VOs successfully generated via ElevenLabs ITV 5 (eleven_v3) API!")
