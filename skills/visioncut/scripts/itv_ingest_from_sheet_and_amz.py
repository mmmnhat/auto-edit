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
import subprocess
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")

SHEET_ID = "1CIGzoztnlND2TU9Yg14OOQKR02BX4XZf1aHlqoNrt1s"
DEVTOOLS_PORT_FILE = r"C:\Users\AMZ-HUY\AppData\Local\CocCoc\Browser\User Data\DevToolsActivePort"


def parse_time_str(t_str):
    """Parse 'M:SS' or 'H:MM:SS' into float seconds."""
    parts = [float(p) for p in t_str.strip().split(":")]
    if len(parts) == 2:
        return parts[0] * 60.0 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600.0 + parts[1] * 60.0 + parts[2]
    return float(parts[0])


def parse_time_range(range_str):
    """
    Parse a Google Sheet/AMZTool time range like '0:33 - 0:40' or '0:24 -0:29' or '15 giây đầu'.
    Returns (start_sec, end_sec) or None if not a simple time range.
    """
    if not range_str:
        return None
    m = re.search(r"(\d+:\d+(?::\d+)?)\s*-\s*(\d+:\d+(?::\d+)?)", range_str)
    if m:
        return parse_time_str(m.group(1)), parse_time_str(m.group(2))
    m_first = re.search(r"(\d+)\s*giây\s*đầu", range_str, flags=re.I)
    if m_first:
        return 0.0, float(m_first.group(1))
    return None


def normalize_source_url(url):
    url = url.strip()
    if "youtu.be/" in url or "youtube.com/" in url:
        url = re.sub(r"[?&]si=[^&]+", "", url)
        url = url.rstrip("?&")
    return url


def fetch_from_coccoc_cdp(script_id, sheet_tab, out_json_path, out_csv_path, out_folder):
    """
    Connects to Cốc Cốc CDP, auto-allows the remote debugging prompt,
    fetches /api/scripts/<script_id> and Google Sheet CSV, and downloads missing 01.mp4..70.mp4 slots.
    """
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

            # 1. Fetch Google Sheet CSV
            sheet_page = next((pg for pg in ctx.pages if SHEET_ID in pg.url), None)
            if sheet_page is None:
                sheet_page = ctx.new_page()
                sheet_page.goto(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit", wait_until="domcontentloaded")
            csv_text = sheet_page.evaluate(f"""async () => {{
                const url = 'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=' + encodeURIComponent('{sheet_tab}');
                const r = await fetch(url);
                return await r.text();
            }}""")
            with open(out_csv_path, "w", encoding="utf-8") as f:
                f.write(csv_text)
            print(f"[CDP] Saved Google Sheet {sheet_tab} -> {out_csv_path} ({len(csv_text)} bytes)")

            # 2. Fetch AMZTool Script JSON & Download Footage
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
        if len(r) < 6:
            continue
        note_col0 = r[0].strip()
        desc = r[1].strip()
        link = r[2].strip()
        time_col = r[3].strip()
        stt = r[5].strip()

        if stt.isdigit():
            last_stt = int(stt)
            out_name = f"itv.{kb_name}.{last_stt}.mp4"
        elif "dự phòng" in link.lower() and last_stt is not None:
            link = re.sub(r"^.*?https://", "https://", link, flags=re.I)
            out_name = f"itv.{kb_name}.{last_stt}-2.mp4"
        else:
            continue

        if not link.startswith("http"):
            continue
        tasks.append({
            "stt": last_stt,
            "out_name": out_name,
            "link": normalize_source_url(link),
            "raw_link": link,
            "time_col": time_col,
            "desc": desc,
            "note_col0": note_col0,
        })

    url_to_cache = {}
    for t in tasks:
        out_path = os.path.join(source_dir, t["out_name"])
        if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
            print(f"[Sheet Skip Existing] {t['out_name']}")
            continue

        u = t["link"]
        if u not in url_to_cache:
            cache_file = os.path.join(cache_dir, f"src_{len(url_to_cache)+1:02d}.mp4")
            url_to_cache[u] = cache_file
            if not (os.path.exists(cache_file) and os.path.getsize(cache_file) > 10000):
                print(f"[Sheet Download] Fetching {u} -> {os.path.basename(cache_file)} ...")
                cmd = [
                    "yt-dlp",
                    "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
                    "--merge-output-format", "mp4",
                    "-o", cache_file,
                    t["raw_link"],
                ]
                subprocess.run(cmd, check=True)

        src_file = url_to_cache[u]
        tr = parse_time_range(t["time_col"])
        if tr is not None:
            st_sec, en_sec = tr
            dur_sec = max(0.5, en_sec - st_sec)
            print(f"[Sheet Slice] {t['out_name']}: {st_sec:.2f}s .. {en_sec:.2f}s ({dur_sec:.2f}s) | {t['desc']}")
            ff_cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-ss", f"{st_sec:.3f}", "-i", src_file, "-t", f"{dur_sec:.3f}",
                "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "19",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                out_path,
            ]
            subprocess.run(ff_cmd, check=True)
        else:
            print(f"[Sheet Copy Full] {t['out_name']} (full clip) | {t['desc']}")
            ff_cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-i", src_file,
                "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "19",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                out_path,
            ]
            subprocess.run(ff_cmd, check=True)


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
        with zipfile.ZipFile(args.amz_zip, "r") as zf:
            zf.extractall(out_folder)

    if not os.path.exists(csv_path) or (args.script_id and not os.path.exists(out_folder)):
        fetch_from_coccoc_cdp(args.script_id, sheet_tab, json_path, csv_path, out_folder)

    download_and_slice_sheet_part1(csv_path, args.kb, proj_dir)
