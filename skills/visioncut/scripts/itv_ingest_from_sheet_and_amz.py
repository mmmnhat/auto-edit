"""
ITV Automated End-to-End Ingest & Pre-Cut Pipeline:
1. Connects to Cốc Cốc CDP (with automatic 'Cho phép' UIA clicker via coccoc_auto_allow.py)
   to fetch:
   - Google Sheet CSV (`KB0<N>`) from spreadsheet `1CIGzoztnlND2TU9Yg14OOQKR02BX4XZf1aHlqoNrt1s`
   - AMZTool Script JSON (`/api/scripts/<script_id>`) & Footage ZIP (`/api/scripts/<script_id>/download`
     or per-slot `/api/drive/video/<driveFileId>`) from `https://ft.amzcollab.com`
2. Extracts AMZTool footage (`01.mp4 .. 70.mp4`) into:
   `E:\\ITV\\Project\\kb<N+40>\\ITV-Moments-script-<N>\\`
3. Downloads each unique YouTube / Facebook link in Google Sheet `KB0<N>` once via `yt-dlp`
   and cuts each row (`stt = 1..20`) to the exact `time` range (`MM:SS - MM:SS`) into:
   `E:\\ITV\\Project\\kb<N+40>\\source\\itv.kb<N+40>.<stt>.mp4`
"""
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")

SHEET_ID = "1CIGzoztnlND2TU9Yg14OOQKR02BX4XZf1aHlqoNrt1s"
DEVTOOLS_PORT_FILE = r"C:\Users\AMZ-HUY\AppData\Local\CocCoc\Browser\User Data\DevToolsActivePort"


def get_video_duration(video_path: str) -> float:
    """Read video duration in seconds via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 0.0


def parse_time_str(t_str: str) -> float:
    """Parse 'M:SS', 'H:MM:SS', 'M.SS', or float seconds into float seconds."""
    s = t_str.strip()
    if ":" in s:
        parts = [float(p) for p in s.split(":")]
    elif "." in s:
        parts = [float(p) for p in s.split(".")]
    else:
        return float(s)

    if len(parts) == 2:
        return parts[0] * 60.0 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600.0 + parts[1] * 60.0 + parts[2]
    return float(parts[0])


EXCLUDE_MARKER_RE = re.compile(r"(?:bỏ\s*đoạn|bo\s*doan|bỏ|bo|trừ|tru)", re.I)
INCLUDE_MARKER_RE = re.compile(r"(?:lấy\s*từ|lay\s*tu|lấy|lay)", re.I)


def _subtract_range(inc: tuple[float, float | None], exc: tuple[float, float | None]) -> list[tuple[float, float | None]]:
    """Subtract excluded range from included range."""
    inc_s, inc_e = inc[0], (float("inf") if inc[1] is None else inc[1])
    exc_s, exc_e = exc[0], (float("inf") if exc[1] is None else exc[1])
    if exc_e <= inc_s or exc_s >= inc_e:
        return [inc]
    res: list[tuple[float, float | None]] = []
    if exc_s > inc_s:
        res.append((inc_s, min(exc_s, inc_e) if inc[1] is not None else exc_s))
    if exc_e < inc_e:
        res.append((exc_e, inc[1]))
    return [r for r in res if r[1] is None or r[1] > r[0]]


def parse_time_ranges(range_str: str, total_dur: float | None = None) -> list[tuple[float, float | None]]:
    """
    Parse one or more time ranges from a Google Sheet time column or AMZTool note:
    - '0:33 - 0:38\n0:58 - 1:03' -> [(33.0, 38.0), (58.0, 63.0)]
    - '4:53 - 5:09 | 5:20 - 5:23' -> [(293.0, 309.0), (320.0, 323.0)]
    - '0:33 - 0:40' -> [(33.0, 40.0)]
    - '0.33 - 0.40' -> [(33.0, 40.0)]
    - 'lấy 0:10 - 0:40 bỏ đoạn 0:20 - 0:25' -> [(10.0, 20.0), (25.0, 40.0)]
    - '15 giây cuối' / '15s cuối' -> [(st, total_dur)]
    - '15 giây đầu' / '15s đầu' / '10s đầu' -> [(0.0, 15.0)] / [(0.0, 10.0)]
    - '2:25 - hết' / '2:25 - đến hết' -> [(145.0, total_dur)]
    - 'N về sau / tới hết' -> [(start, total_dur)]
    Never merges via min/max.
    """
    if not range_str:
        return []
    s = range_str.strip().replace("–", "-").replace("—", "-")

    # 0. Multi-line / pipe-separated clauses without exclude markers (e.g. '11s đầu\n25 - 31')
    if not EXCLUDE_MARKER_RE.search(s) and re.search(r"[\r\n|]", s):
        parts = [p.strip() for p in re.split(r"[\r\n|]+", s) if p.strip()]
        if len(parts) > 1:
            combined: list[tuple[float, float | None]] = []
            for part in parts:
                combined.extend(parse_time_ranges(part, total_dur=total_dur))
            if combined:
                return combined

    # 1. Ranges with start - end and include/exclude context
    token_re = re.compile(
        r"(?P<start>(?:\d+[:.]\d+(?:[:.]\d+)?|\d+))\s*(?:-|tới|toi|to)\s*(?P<end>(?:\d+[:.]\d+(?:[:.]\d+)?|\d+|đến\s*hết|den\s*het|hết|het|end|cuối|cuoi))",
        re.I,
    )
    candidates = list(token_re.finditer(s))
    if candidates:
        includes: list[tuple[float, float | None]] = []
        excludes: list[tuple[float, float | None]] = []
        mode = "include"
        prev_end = 0
        for m in candidates:
            ctx = s[prev_end : m.start()]
            last_inc = max((x.start() for x in INCLUDE_MARKER_RE.finditer(ctx)), default=-1)
            last_exc = max((x.start() for x in EXCLUDE_MARKER_RE.finditer(ctx)), default=-1)
            if last_exc > last_inc:
                mode = "exclude"
            elif last_inc > last_exc:
                mode = "include"

            st = parse_time_str(m.group("start"))
            end_tok = m.group("end").strip().lower()
            if re.match(r"^\d", end_tok):
                en: float | None = parse_time_str(end_tok)
                if en <= st:
                    prev_end = m.end()
                    continue
            else:
                en = total_dur

            if mode == "exclude":
                excludes.append((st, en))
            else:
                includes.append((st, en))
            prev_end = m.end()

        if not includes and excludes:
            includes = [(0.0, total_dur)]

        resolved: list[tuple[float, float | None]] = []
        for inc in includes:
            pending = [inc]
            for exc in excludes:
                nxt: list[tuple[float, float | None]] = []
                for seg in pending:
                    nxt.extend(_subtract_range(seg, exc))
                pending = nxt
            resolved.extend(pending)
        if resolved:
            return resolved

    # 2. '15 giây cuối' / '15s cuối' / '15 giay cuoi' / '15s cuoi' / '15s trở về cuối'
    m_last = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:giây|giay|s)\s*(?:cuối|cuoi|trở về cuối|tro ve cuoi)",
        s,
        flags=re.I,
    )
    if m_last:
        dur = float(m_last.group(1))
        st = max(0.0, total_dur - dur) if total_dur is not None else 0.0
        return [(st, total_dur)]

    # 3. '15 giây đầu' / '15s đầu' / '15 giay dau' / '15s dau' / '15s đổ lại'
    m_first = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:giây|giay|s)\s*(?:đầu|dau|đổ lại|do lai)",
        s,
        flags=re.I,
    )
    if m_first:
        return [(0.0, float(m_first.group(1)))]

    # 4. '2:25 về sau' / '2:25 tới hết' / '2:25 trở đi' / '5 về sau'
    m_after = re.search(
        r"((?:\d+[:.]\d+(?:[:.]\d+)?|\d+))\s*(?:về sau|ve sau|tới hết|toi het|trở đi|tro di)",
        s,
        flags=re.I,
    )
    if m_after:
        st = parse_time_str(m_after.group(1))
        return [(st, total_dur)]

    return []


def parse_time_range(range_str):
    """Backwards compatible single-range parser."""
    ranges = parse_time_ranges(range_str)
    return ranges[0] if ranges else None


def normalize_source_url(url):
    url = url.strip()
    if "youtu.be/" in url or "youtube.com/" in url:
        url = re.sub(r"[?&]si=[^&]+", "", url)
        url = url.rstrip("?&")
    return url


def fetch_sheet_via_gsheets_cli(sheet_tab: str, out_csv_path: str):
    """
    Fetches Google Sheet tab directly via `gsheets` OAuth CLI (strictly no browser on Google Workspace).
    """
    gsheets_bin = shutil.which("gsheets") or "gsheets.cmd"
    cmd = [
        gsheets_bin, "readonly", "read",
        SHEET_ID,
        f"'{sheet_tab}'!A1:Z100",
        "--json",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
    payload = json.loads(res.stdout)
    rows = payload if isinstance(payload, list) else payload.get("values", [])
    with open(out_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for r in rows:
            writer.writerow(r)
    print(f"[gsheets CLI] Saved Google Sheet {sheet_tab} -> {out_csv_path} ({len(rows)} rows)")


def fetch_from_coccoc_cdp(script_id, sheet_tab, out_json_path, out_csv_path, out_folder):
    """
    Fetches Google Sheet CSV via `gsheets` CLI (OAuth) and connects to Cốc Cốc CDP ONLY for
    AMZTool (`ft.amzcollab.com`) to fetch /api/scripts/<script_id> and download 01.mp4..70.mp4 slots.
    """
    if not os.path.exists(out_csv_path):
        fetch_sheet_via_gsheets_cli(sheet_tab, out_csv_path)

    if not script_id:
        return

    from coccoc_auto_allow import spawn_auto_allow
    from playwright.sync_api import sync_playwright

    with open(DEVTOOLS_PORT_FILE, "r", encoding="utf-8") as f:
        lines = [x.strip() for x in f.read().splitlines() if x.strip()]
    ws_url = f"ws://127.0.0.1:{lines[0]}{lines[1]}"

    helper = spawn_auto_allow()
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(ws_url)
            ctx = browser.contexts[0]

            # Fetch AMZTool Script JSON & Download Footage
            if script_id:
                amz_page = next((pg for pg in ctx.pages if "amzcollab.com" in pg.url), None)
                if amz_page is None:
                    amz_page = ctx.new_page()
                    amz_page.goto(f"https://ft.amzcollab.com/workspace/scripts/{script_id}", wait_until="domcontentloaded")
                data = amz_page.evaluate(f"""async () => {{
                    const r = await fetch('/api/scripts/{script_id}');
                    return await r.json();
                }}""")
                with open(out_json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                os.makedirs(out_folder, exist_ok=True)
                items = data.get("items") or data.get("data", {}).get("footages", [])
                print(f"[CDP] Script {script_id}: {len(items)} slots. Downloading footage to {out_folder} ...")
                cookies = ctx.cookies("https://ft.amzcollab.com")
                cookie_hdr = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

                for slot in items:
                    if slot.get("scriptStatus") == "replaced":
                        continue
                    order = slot.get("sortOrder")
                    ft = slot.get("footage") or {}
                    fid = ft.get("driveFileId")
                    if not order or not fid:
                        continue
                    target_mp4 = os.path.join(out_folder, f"{int(order):02d}.mp4")
                    if os.path.exists(target_mp4) and os.path.getsize(target_mp4) > 10000:
                        continue
                    dl_url = f"https://ft.amzcollab.com/api/drive/video/{fid}"
                    cmd = [
                        "curl.exe", "-s", "-L",
                        "-H", f"Cookie: {cookie_hdr}",
                        "-o", target_mp4,
                        dl_url,
                    ]
                    subprocess.run(cmd, check=True)
                    print(f"  [AMZTool] Downloaded {int(order):02d}.mp4 ({os.path.getsize(target_mp4)//1024} KB)")
    finally:
        helper.terminate()


def download_and_slice_sheet_part1(csv_path, kb_name, project_dir):
    source_dir = os.path.join(project_dir, "source")
    cache_dir = os.path.join(project_dir, "_raw_cache")
    os.makedirs(source_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    rows = list(csv.reader(open(csv_path, encoding="utf-8")))
    tasks = []
    last_stt = None
    for r in rows[1:]:
        if not any(x.strip() for x in r):
            continue
        r = list(r) + [""] * max(0, 8 - len(r))
        note_col0 = r[0].strip()
        desc = r[1].strip()
        link = r[2].strip()
        time_col = r[3].strip()
        stt = r[5].strip()

        if stt.isdigit():
            last_stt = int(stt)
            is_backup = False
        elif ("dự phòng" in link.lower() or "du phong" in link.lower()) and last_stt is not None:
            link = re.sub(r"^.*?https://", "https://", link, flags=re.I)
            is_backup = True
        else:
            continue

        if not link.startswith("http"):
            continue

        ranges = parse_time_ranges(time_col)
        clean_url = normalize_source_url(link)
        if len(ranges) > 1:
            for r_idx, r in enumerate(ranges, 1):
                base_name = f"itv.{kb_name}.{last_stt}" if not is_backup else f"itv.{kb_name}.{last_stt}-2"
                out_name = f"{base_name}_{r_idx}.mp4"
                tasks.append({
                    "stt": last_stt,
                    "sub_idx": r_idx,
                    "out_name": out_name,
                    "link": clean_url,
                    "raw_link": link,
                    "time_col": time_col,
                    "ranges": [r],
                    "desc": f"{desc} [part {r_idx}]",
                    "note_col0": note_col0,
                })
        else:
            out_name = f"itv.{kb_name}.{last_stt}.mp4" if not is_backup else f"itv.{kb_name}.{last_stt}-2.mp4"
            tasks.append({
                "stt": last_stt,
                "sub_idx": None,
                "out_name": out_name,
                "link": clean_url,
                "raw_link": link,
                "time_col": time_col,
                "ranges": ranges,
                "desc": desc,
                "note_col0": note_col0,
            })

    url_to_cache = {}
    for t in tasks:
        u = t["link"]
        if u not in url_to_cache:
            url_to_cache[u] = os.path.join(cache_dir, f"src_{len(url_to_cache)+1:02d}.mp4")

    for t in tasks:
        out_path = os.path.join(source_dir, t["out_name"])
        if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
            print(f"[Sheet Skip Existing] {t['out_name']}")
            continue

        u = t["link"]
        cache_file = url_to_cache[u]
        if not (os.path.exists(cache_file) and os.path.getsize(cache_file) > 10000):
            print(f"[Sheet Download] Fetching {u} -> {os.path.basename(cache_file)} ...")
            cmd = [
                "yt-dlp",
                "-N", "16",
                "-f", "bestvideo[height<=1080][vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
                "--merge-output-format", "mp4",
                "-o", cache_file,
                t["raw_link"],
            ]
            try:
                subprocess.run(cmd, check=True)
            except Exception as e_dl:
                print(f"[WARN] yt-dlp failed for {t['out_name']} ({u}): {e_dl}")
                continue

        src_file = url_to_cache[u]
        if not (os.path.exists(src_file) and os.path.getsize(src_file) > 10000):
            print(f"[WARN] Missing source cache for {t['out_name']}, skipping.")
            continue
        ranges = t.get("ranges") or []
        if ranges:
            st_sec, en_sec = ranges[0]
            en_sec = en_sec if en_sec is not None else 999999.0
            dur_sec = max(0.5, en_sec - st_sec)
            print(f"[Sheet Slice] {t['out_name']}: {st_sec:.2f}s .. {en_sec:.2f}s ({dur_sec:.2f}s) | {t['desc']}")
            ff_cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-ss", f"{st_sec:.3f}", "-i", src_file, "-t", f"{dur_sec:.3f}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "19",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                out_path,
            ]
            subprocess.run(ff_cmd, check=True)
        else:
            print(f"[Sheet Copy Full] {t['out_name']} (full clip) | {t['desc']}")
            ff_cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-i", src_file,
                "-c:v", "libx264", "-preset", "fast", "-crf", "19",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                out_path,
            ]
            subprocess.run(ff_cmd, check=True)


def slice_amz_part2_clips(json_path: str, out_folder: str):
    """
    Slices Part 2 clips based on AMZTool script JSON:
    - Multi-timestamp notes (e.g. '0:33 - 0:38\n0:58 - 1:03', '4:53 - 5:09 | 5:20 - 5:23')
      are split into discrete files: {order:02d}_1.mp4, {order:02d}_2.mp4.
      Zero concat jumpcuts! Zero min/max merging!
    - Single timestamp notes are sliced to 100% of note duration.
    - Clips without notes preserve 100% of raw file duration (zero 5.5s..6.2s clamp!).
    """
    if not os.path.exists(json_path) or not os.path.exists(out_folder):
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items") or data.get("data", {}).get("footages", [])
    for slot in items:
        order = slot.get("sortOrder")
        if not order:
            continue
        order_int = int(order)
        raw_mp4 = os.path.join(out_folder, f"{order_int:02d}.mp4")
        if not os.path.exists(raw_mp4):
            continue

        note = (slot.get("note") or "").strip()
        orig_bak = raw_mp4[:-4] + ".orig.mp4" if raw_mp4.endswith(".mp4") else raw_mp4 + ".orig.mp4"
        src_for_dur = orig_bak if (os.path.exists(orig_bak) and os.path.getsize(orig_bak) > 10000) else raw_mp4
        tot_dur = get_video_duration(src_for_dur)
        ranges = parse_time_ranges(note, total_dur=tot_dur if tot_dur > 0 else None)
        if not ranges:
            # 100% raw file duration preserved, no clamp
            continue

        if not os.path.exists(orig_bak) or os.path.getsize(orig_bak) < 10000:
            shutil.copy2(raw_mp4, orig_bak)
        alt_bak = raw_mp4 + ".orig.mp4"
        if not os.path.exists(alt_bak) or os.path.getsize(alt_bak) < 10000:
            shutil.copy2(orig_bak, alt_bak)

        if len(ranges) > 1:
            print(f"[Part 2 Multi-Split] Slot {order_int:02d} has {len(ranges)} ranges: {ranges}")
            for r_idx, (st_sec, en_sec) in enumerate(ranges, 1):
                sub_mp4 = os.path.join(out_folder, f"{order_int:02d}_{r_idx}.mp4")
                dur_sec = max(0.5, (en_sec or 999999.0) - st_sec)
                cmd = [
                    "ffmpeg", "-y", "-v", "error",
                    "-ss", f"{st_sec:.3f}", "-i", orig_bak, "-t", f"{dur_sec:.3f}",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "19",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    sub_mp4,
                ]
                try:
                    subprocess.run(cmd, check=True)
                except Exception as e_slice:
                    print(f"Warning: ffmpeg multi-split slice failed for {sub_mp4}: {e_slice}")
                print(f"  ✓ {os.path.basename(sub_mp4)}: [{st_sec:.2f}..{en_sec:.2f}s] ({dur_sec:.2f}s)")
        elif len(ranges) == 1:
            st_sec, en_sec = ranges[0]
            dur_sec = max(0.5, (en_sec or 999999.0) - st_sec)
            print(f"[Part 2 Note Slice] Slot {order_int:02d}: [{st_sec:.2f}..{en_sec:.2f}s] ({dur_sec:.2f}s)")
            tmp_sliced = raw_mp4 + ".tmp.mp4"
            cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-ss", f"{st_sec:.3f}", "-i", orig_bak, "-t", f"{dur_sec:.3f}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "19",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                tmp_sliced,
            ]
            try:
                subprocess.run(cmd, check=True)
                shutil.move(tmp_sliced, raw_mp4)
            except Exception as e_slice:
                print(f"Warning: ffmpeg note slice failed for {raw_mp4}: {e_slice}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ITV Automated Ingest & Pre-Cut from Sheet + AMZTool")
    parser.add_argument("--kb", required=True, help="e.g. kb111")
    parser.add_argument("--script-num", type=int, required=True, help="e.g. 71")
    parser.add_argument("--script-id", type=int, required=False, help="AMZTool script ID, e.g. 364")
    parser.add_argument("--sheet-csv", required=False, help="Path to exported Google Sheet CSV")
    parser.add_argument("--amz-json", required=False, help="Path to exported AMZTool script JSON")
    parser.add_argument("--amz-zip", required=False, help="Path to downloaded AMZTool footage ZIP")
    args = parser.parse_args()

    proj_dir = rf"E:\ITV\Project\{args.kb}"
    os.makedirs(proj_dir, exist_ok=True)
    sheet_tab = f"KB{args.script_num:03d}"
    csv_path = args.sheet_csv or os.path.join(proj_dir, f"sheet_{sheet_tab}.csv")
    json_path = args.amz_json or os.path.join(proj_dir, f"{args.kb}_s{args.script_num}.json")
    out_folder = os.path.join(proj_dir, f"ITV-Moments-script-{args.script_num}")

    if args.amz_zip and os.path.exists(args.amz_zip):
        os.makedirs(out_folder, exist_ok=True)
        import zipfile
        with zipfile.ZipFile(args.amz_zip, "r") as zf:
            zf.extractall(out_folder)

    if not os.path.exists(csv_path) or (args.script_id and not os.path.exists(out_folder)):
        fetch_from_coccoc_cdp(args.script_id, sheet_tab, json_path, csv_path, out_folder)

    if os.path.exists(csv_path):
        download_and_slice_sheet_part1(csv_path, args.kb, proj_dir)

    if os.path.exists(json_path):
        slice_amz_part2_clips(json_path, out_folder)
