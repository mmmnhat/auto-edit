"""
Ground Truth Loader for ITV E2E Test Suite.
Loads Google Sheets CSVs, AMZTool JSONs, SFX catalogs, and channel profile definitions.
Provides authoritative target metrics and invariants.
"""

from __future__ import annotations
import csv
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .timeline_math import parse_note_specification, parse_time_range


BANNED_INTERJECTION_DIR = r"E:\Video Asset\SFX\interjection"
KNOWN_37_INTERJECTIONS = {
    "(bursts into laughter) pfft-hahaha!.mp3",
    "aaaaa!.mp3",
    "agh!.mp3",
    "ahem!.mp3",
    "ahhhhh!.mp3",
    "coughs.mp3",
    "eek!.mp3",
    "ew!.mp3",
    "eww!.mp3",
    "ha!!.mp3",
    "ha!.mp3",
    "hiii-yah!.mp3",
    "hngggggg.mp3",
    "hnnng-ugh!.mp3",
    "holy mother of.mp3",
    "hyah!.mp3",
    "jeez!.mp3",
    "nom-nom-nom.mp3",
    "oh crap!.mp3",
    "oh my.mp3",
    "oh oh oh oh oh!.mp3",
    "oh wait.mp3",
    "oh well....mp3",
    "oh... oh... oh wait, no, no, watch your st-.mp3",
    "oops!.mp3",
    "ouch.mp3",
    "pffft hahaha.mp3",
    "phew!.mp3",
    "psst!.mp3",
    "um....mp3",
    "what the.mp3",
    "what.mp3",
    "whoa, hold on!.mp3",
    "whoa-whoa!.mp3",
    "whoops!.mp3",
    "wiii! wheeee!.mp3",
    "wtf.mp3",
}

V8_TEMPLATE_TEXT_MAP = {
    "2238": "*ALL GOOD",
    "2239": "*NOBODY GOT HURT",
    "2240": "*ALL SAFE",
    "2241": "*ALL GOOD",
    "2242": "*NOBODY GOT HURT",
    "2243": "*ALL SAFE",
    "2244": "*SHE'S FINE",
    "2245": "*HE'S FINE",
    "2246": "*DON'T TRY",
    "2247": "*THE DRIVER IS OKAY",
    "2248": "*ALL GOOD",
}


@dataclass
class Part1TargetItem:
    index: int
    clip_name: str
    sheet_start_sec: float
    sheet_end_sec: float
    target_duration: float
    raw_time_str: str


@dataclass
class Part2TargetItem:
    slot_num: int
    clip_name: str
    note: str
    raw_duration: Optional[float]
    target_duration: Optional[float]
    rule_type: str
    is_multi_ts: bool
    multi_ranges: List[Tuple[float, float]]
    is_viralhog: bool
    license_provider: str


@dataclass
class ProjectGroundTruth:
    project_id: str
    project_dir: str
    sheet_csv_path: str
    amz_json_path: str
    prproj_path: str
    part1_items: List[Part1TargetItem] = field(default_factory=list)
    part2_items: List[Part2TargetItem] = field(default_factory=list)
    viralhog_clip_names: Set[str] = field(default_factory=set)
    banned_sfx_files: Set[str] = field(default_factory=set)
    v8_template_map: Dict[str, str] = field(default_factory=lambda: dict(V8_TEMPLATE_TEXT_MAP))


class GroundTruthLoader:
    """Loads and standardizes ground-truth specifications for kb118..kb121."""

    PROJECT_CONFIGS = {
        "kb118": {"kb_num": 78, "csv": "sheet_KB078.csv", "json": "kb118_s78.json"},
        "kb119": {"kb_num": 79, "csv": "sheet_KB079.csv", "json": "kb119_s79.json"},
        "kb120": {"kb_num": 80, "csv": "sheet_KB080.csv", "json": "kb120_s80.json"},
        "kb121": {"kb_num": 81, "csv": "sheet_KB081.csv", "json": "kb121_s81.json"},
        "kb122": {"kb_num": 82, "csv": "sheet_KB082.csv", "json": "kb122_s82.json"},
        "kb123": {"kb_num": 83, "csv": "sheet_KB083.csv", "json": "kb123_s83.json"},
        "kb124": {"kb_num": 84, "csv": "sheet_KB084.csv", "json": "kb124_s84.json"},
        "kb125": {"kb_num": 85, "csv": "sheet_KB085.csv", "json": "kb125_s85.json"},
        "kb126": {"kb_num": 86, "csv": "sheet_KB086.csv", "json": "kb126_s86.json"},
        "kb127": {"kb_num": 87, "csv": "sheet_KB087.csv", "json": "kb127_s87.json"},
        "kb128": {"kb_num": 88, "csv": "sheet_KB088.csv", "json": "kb128_s88.json"},
        "kb129": {"kb_num": 89, "csv": "sheet_KB089.csv", "json": "kb129_s89.json"},
        "kb130": {"kb_num": 90, "csv": "sheet_KB090.csv", "json": "kb130_s90.json"},
        "kb131": {"kb_num": 91, "csv": "sheet_KB091.csv", "json": "kb131_s91.json"},
        "kb132": {"kb_num": 92, "csv": "sheet_KB092.csv", "json": "kb132_s92.json"},
        "kb133": {"kb_num": 93, "csv": "sheet_KB093.csv", "json": "kb133_s93.json"},
        "kb134": {"kb_num": 94, "csv": "sheet_KB094.csv", "json": "kb134_s94.json"},
        "kb135": {"kb_num": 95, "csv": "sheet_KB095.csv", "json": "kb135_s95.json"},
        "kb136": {"kb_num": 96, "csv": "sheet_KB096.csv", "json": "kb136_s96.json"},
        "kb137": {"kb_num": 97, "csv": "sheet_KB097.csv", "json": "kb137_s97.json"},
        "kb138": {"kb_num": 98, "csv": "sheet_KB098.csv", "json": "kb138_s98.json"},
        "kb139": {"kb_num": 99, "csv": "sheet_KB099.csv", "json": "kb139_s99.json"},
        "kb140": {"kb_num": 100, "csv": "sheet_KB100.csv", "json": "kb140_s100.json"},
        "TEST_AUTO_WORKFAIL_9_11": {"kb_num": 99, "csv": "sheet_KB099.csv", "json": "TEST_AUTO_WORKFAIL_9_11_s99.json"},
    }

    @classmethod
    def get_banned_interjection_files(cls) -> Set[str]:
        if os.path.exists(BANNED_INTERJECTION_DIR):
            try:
                files = set(f.lower() for f in os.listdir(BANNED_INTERJECTION_DIR))
                if files:
                    return files
            except Exception:
                pass
        return set(KNOWN_37_INTERJECTIONS)

    @classmethod
    def load_project_truth(cls, project_id: str, base_dir: str = r"E:\ITV\Project") -> ProjectGroundTruth:
        if os.environ.get("ITV_BASE_DIR"):
            base_dir = os.environ["ITV_BASE_DIR"]
        else:
            std_prproj = os.path.join(base_dir, project_id, f"{project_id}.prproj")
            tool_prproj = os.path.join(r"E:\ITV\Project tool", project_id, f"{project_id}.prproj")
            if os.path.exists(tool_prproj) and (
                not os.path.exists(std_prproj) or os.path.getmtime(tool_prproj) >= os.path.getmtime(std_prproj)
            ):
                base_dir = r"E:\ITV\Project tool"
        if project_id not in cls.PROJECT_CONFIGS:
            matched = next((k for k in cls.PROJECT_CONFIGS if k.lower() == project_id.lower()), None)
            if matched:
                project_id = matched
            else:
                raise ValueError(f"Unknown project: {project_id}. Valid: {list(cls.PROJECT_CONFIGS.keys())}")

        cfg = cls.PROJECT_CONFIGS[project_id]
        proj_dir = os.path.join(base_dir, project_id)
        csv_path = os.path.join(proj_dir, cfg["csv"])
        json_path = os.path.join(proj_dir, cfg["json"])
        prproj_path = os.path.join(proj_dir, f"{project_id}.prproj")

        banned_sfx = cls.get_banned_interjection_files()

        # 1. Parse Part 1 Sheet CSV
        part1_items: List[Part1TargetItem] = []
        if os.path.exists(csv_path):
            import subprocess
            with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                idx = 0
                for row in reader:
                    if len(row) > 3:
                        title = row[1].strip() if len(row) > 1 else ""
                        if title.lower() == "nội dung":
                            continue
                        link = row[2].strip().lower() if len(row) > 2 else ""
                        stt = row[5].strip() if len(row) > 5 else ""
                        if stt.isdigit():
                            cur_idx = int(stt)
                            idx = cur_idx
                        elif title and "du phong" not in link and "dự phòng" not in link:
                            idx += 1
                            cur_idx = idx
                        else:
                            continue

                        time_str = row[3].strip().replace(";", ":")
                        rng = parse_time_range(time_str)
                        if rng:
                            dur = rng[1] - rng[0]
                            cname = f"itv.{project_id}.{cur_idx}.mp4"
                            mp4_path = os.path.join(proj_dir, "source", cname)
                            if os.path.exists(mp4_path):
                                try:
                                    res = subprocess.run(
                                        [
                                            "ffprobe",
                                            "-v",
                                            "error",
                                            "-show_entries",
                                            "stream=duration:format=duration",
                                            "-of",
                                            "default=noprint_wrappers=1:nokey=1",
                                            mp4_path,
                                        ],
                                        capture_output=True,
                                        text=True,
                                    )
                                    vals = [
                                        float(x)
                                        for x in res.stdout.strip().splitlines()
                                        if x.strip() and x.strip() != "N/A"
                                    ]
                                    if vals:
                                        min_stream_d = min(vals)
                                        safe_frames = int(min_stream_d * 24000.0 / 1001.0)
                                        safe_dur = round(safe_frames * 1001.0 / 24000.0, 3)
                                        if safe_dur > 0:
                                            dur = safe_dur
                                except Exception:
                                    pass
                            part1_items.append(
                                Part1TargetItem(
                                    index=cur_idx,
                                    clip_name=cname,
                                    sheet_start_sec=rng[0],
                                    sheet_end_sec=rng[0] + dur,
                                    target_duration=dur,
                                    raw_time_str=time_str,
                                )
                            )

        # 2. Parse Part 2 AMZTool JSON
        part2_items: List[Part2TargetItem] = []
        viralhog_clips: Set[str] = set()

        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            footages = data.get("data", {}).get("footages", [])
            for item in footages:
                if item.get("scriptStatus") == "replaced":
                    continue
                sort_order = item.get("sortOrder")
                if not sort_order:
                    continue
                slot_name = f"{sort_order:02d}.mp4"
                slot_alt = f"{sort_order}.mp4"
                note = item.get("note") or ""
                ft = item.get("footage") or {}
                raw_dur = ft.get("duration")
                lp = ft.get("licenseProvider") or ft.get("sourceProvider") or ""
                is_vh = lp.lower() == "viralhog"
                if is_vh:
                    viralhog_clips.add(slot_name)

                note_spec = parse_note_specification(note, raw_dur)
                part2_items.append(
                    Part2TargetItem(
                        slot_num=sort_order,
                        clip_name=slot_name,
                        note=note,
                        raw_duration=raw_dur,
                        target_duration=note_spec.get("target_duration"),
                        rule_type=note_spec.get("rule_type", "none"),
                        is_multi_ts=note_spec.get("is_multi_ts", False),
                        multi_ranges=note_spec.get("multi_ranges", []),
                        is_viralhog=is_vh,
                        license_provider=lp,
                    )
                )

        return ProjectGroundTruth(
            project_id=project_id,
            project_dir=proj_dir,
            sheet_csv_path=csv_path,
            amz_json_path=json_path,
            prproj_path=prproj_path,
            part1_items=part1_items,
            part2_items=part2_items,
            viralhog_clip_names=viralhog_clips,
            banned_sfx_files=banned_sfx,
        )
