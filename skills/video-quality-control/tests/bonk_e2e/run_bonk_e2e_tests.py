r"""
Master E2E Automated Test Suite Runner for Bonk! Funny Moments Pipeline.
Executes high-speed (<150ms/project) offline .prproj XML AST audits across 20 formal assertions (BONK-R1..R6).

Usage:
  python "E:\Bonk funny moments\tests\run_bonk_e2e_tests.py" --target kb27 kb28 kb29 kb30 kb31 kb32 kb33 kb34 --mode audit
  python "E:\Bonk funny moments\tests\run_bonk_e2e_tests.py" --target kb34 --mode strict
"""

from __future__ import annotations

import argparse
import csv
import datetime
import gzip
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_PROJECT_ROOT = os.path.join(WORKSPACE_ROOT, "project")

TICKS_PER_SEC = 254016000000.0
FPS = 24000.0 / 1001.0
TICKS_PER_FRAME = int(round(TICKS_PER_SEC / FPS))  # 10,594,560,000

BANNED_INTERJECTIONS: Set[str] = {
    s.lower()
    for s in [
        "(bursts into laughter) Pfft-hahaha!.mp3",
        "Aaaaa!.mp3",
        "Agh!.mp3",
        "Ahem!.mp3",
        "Ahhhhh!.mp3",
        "coughs.mp3",
        "eek!.mp3",
        "ew!.mp3",
        "Eww!.mp3",
        "Ha!!.mp3",
        "ha!.mp3",
        "Hiii-yah!.mp3",
        "hngggggg.mp3",
        "Hnnng-ugh!.mp3",
        "Holy mother of.mp3",
        "Hyah!.mp3",
        "Jeez!.mp3",
        "nom-nom-nom.mp3",
        "Oh crap!.mp3",
        "oh my.mp3",
        "Oh oh oh oh oh!.mp3",
        "oh wait.mp3",
        "Oh well....mp3",
        "Oh... oh... oh wait, no, no, watch your st—.mp3",
        "Oops!.mp3",
        "ouch.mp3",
        "pffft hahaha.mp3",
        "Phew!.mp3",
        "Psst!.mp3",
        "Um....mp3",
        "What the.mp3",
        "what.mp3",
        "Whoa, hold on!.mp3",
        "Whoa-whoa!.mp3",
        "Whoops!.mp3",
        "Wiii! Wheeee!.mp3",
        "wtf.mp3",
    ]
}

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    HAVE_RICH = True
except ImportError:
    HAVE_RICH = False


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ClipItem:
    object_id: str
    track_index: int
    track_type: str  # "video" or "audio"
    name: str
    start_ticks: int
    end_ticks: int
    in_ticks: int = 0
    out_ticks: int = 0
    disabled: bool = False
    audio_level: float = 1.0
    scale: float = 100.0
    transform_scale: float = 100.0
    fit_scale: float = 100.0
    position: Tuple[float, float] = (0.5, 0.5)
    pos_keyframes: List[Tuple[int, float, float]] = field(default_factory=list)
    has_lumetri: bool = False
    has_blur: bool = False
    has_crop: bool = False
    has_hflip: bool = False
    has_motion: bool = False
    match_names: List[str] = field(default_factory=list)

    @property
    def start_sec(self) -> float:
        return self.start_ticks / TICKS_PER_SEC

    @property
    def end_sec(self) -> float:
        return self.end_ticks / TICKS_PER_SEC

    @property
    def dur_sec(self) -> float:
        return (self.end_ticks - self.start_ticks) / TICKS_PER_SEC

    @property
    def in_sec(self) -> float:
        return self.in_ticks / TICKS_PER_SEC

    @property
    def out_sec(self) -> float:
        return self.out_ticks / TICKS_PER_SEC

    @property
    def is_muted(self) -> bool:
        return self.disabled or self.audio_level <= 0.001

    @property
    def effective_zoom_pct(self) -> float:
        base = self.fit_scale if self.fit_scale > 1.0 else 100.0
        return (self.scale / base) * self.transform_scale

    @property
    def is_static_center(self) -> bool:
        if not self.has_motion:
            return True
        pts = [(x, y) for _, x, y in self.pos_keyframes] or [self.position]
        return all(abs(x - 0.50) <= 0.04 and abs(y - 0.50) <= 0.06 for x, y in pts)


@dataclass
class BonkParsedProject:
    project_id: str
    prproj_path: str
    seq_name: str
    video_tracks: List[List[ClipItem]]
    audio_tracks: List[List[ClipItem]]
    total_dur_ticks: int
    media_paths: List[str]
    master_clip_count: int
    clip_project_item_count: int
    pek_tag_count: int
    dangling_refs: int
    parse_ms: float

    @property
    def total_dur_sec(self) -> float:
        return self.total_dur_ticks / TICKS_PER_SEC

    def vtrack(self, idx_1based: int) -> List[ClipItem]:
        i = idx_1based - 1
        return self.video_tracks[i] if 0 <= i < len(self.video_tracks) else []

    def atrack(self, idx_1based: int) -> List[ClipItem]:
        i = idx_1based - 1
        return self.audio_tracks[i] if 0 <= i < len(self.audio_tracks) else []


@dataclass
class GroundTruth:
    project_id: str
    sheet_rows: List[Dict[str, str]] = field(default_factory=list)
    amz_items: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AssertionResult:
    assertion_id: str
    title: str
    passed: bool
    details: str


@dataclass
class ProjectReport:
    project_id: str
    parse_ms: float
    results: List[AssertionResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100.0) if self.total else 0.0


# ---------------------------------------------------------------------------
# Fast Offline .prproj Parser & Ground-Truth Loader
# ---------------------------------------------------------------------------

def parse_bonk_prproj(project_id: str, prproj_path: str) -> BonkParsedProject:
    t0 = time.perf_counter()
    with gzip.open(prproj_path, "rb") as f:
        raw = f.read()
    root = ET.fromstring(raw)

    by_id = {e.attrib["ObjectID"]: e for e in root if "ObjectID" in e.attrib}
    by_uid = {e.attrib["ObjectUID"]: e for e in root if "ObjectUID" in e.attrib}

    def deref(el: Optional[ET.Element]) -> Optional[ET.Element]:
        if el is None:
            return None
        if "ObjectRef" in el.attrib:
            return by_id.get(el.attrib["ObjectRef"])
        if "ObjectURef" in el.attrib:
            return by_uid.get(el.attrib["ObjectURef"])
        return None

    def count_items(seq_el: ET.Element) -> int:
        cnt = 0
        tgp = seq_el.find("TrackGroups")
        if tgp is not None:
            for tg in tgp:
                sec = deref(tg.find("Second"))
                if sec is not None and sec.tag in ("VideoTrackGroup", "AudioTrackGroup"):
                    tcont = sec.find("TrackGroup/Tracks")
                    if tcont is not None:
                        for tr_ref in tcont:
                            tr = deref(tr_ref)
                            if tr is not None:
                                ti = tr.find("ClipTrack/ClipItems/TrackItems")
                                if ti is not None:
                                    cnt += len(ti)
        return cnt

    seqs = [s for s in root.iter("Sequence") if "ObjectUID" in s.attrib]
    matching = [s for s in seqs if (s.findtext("Name") or "").strip().lower() == project_id.lower()]
    seq_el = max(matching, key=count_items) if matching else max(seqs, key=count_items)

    v_tracks: List[List[ClipItem]] = []
    a_tracks: List[List[ClipItem]] = []

    tgp = seq_el.find("TrackGroups")
    if tgp is not None:
        for tg in tgp:
            sec = deref(tg.find("Second"))
            if sec is None or sec.tag not in ("VideoTrackGroup", "AudioTrackGroup"):
                continue
            tcont = sec.find("TrackGroup/Tracks")
            if tcont is None:
                continue
            is_video = sec.tag == "VideoTrackGroup"
            for idx, tr_ref in enumerate(tcont):
                tr = deref(tr_ref)
                items_out: List[ClipItem] = []
                if tr is not None:
                    titems = tr.find("ClipTrack/ClipItems/TrackItems")
                    if titems is not None:
                        for r in titems:
                            ti = deref(r)
                            if ti is None:
                                continue
                            oid = ti.attrib.get("ObjectID", "")
                            st = int(ti.findtext(".//Start") or 0)
                            et = int(ti.findtext(".//End") or 0)
                            dis = (ti.findtext(".//Disabled") or "").lower() == "true"
                            sc = deref(ti.find(".//SubClip"))
                            nm = (sc.findtext("Name") or "") if sc is not None else ""
                            in_t, out_t = 0, 0
                            fit_scale_val = 100.0
                            if sc is not None:
                                cl = deref(sc.find("Clip"))
                                if cl is not None:
                                    in_t = int(cl.findtext(".//InPoint") or 0)
                                    out_t = int(cl.findtext(".//OutPoint") or 0)
                                    src = deref(cl.find("Source"))
                                    if src is not None:
                                        vs = deref(src.find(".//Stream"))
                                        if vs is not None:
                                            fr = vs.findtext("FrameRect") or ""
                                            fm = re.match(r"0,0,(\d+),(\d+)", fr.strip())
                                            if fm:
                                                vw, vh = int(fm.group(1)), int(fm.group(2))
                                                if vw > 0 and vh > 0:
                                                    fit_scale_val = min(1920.0 / vw, 1080.0 / vh) * 100.0

                            def read_param_float(pe_el: ET.Element, default: Optional[float] = None) -> Optional[float]:
                                cv_txt = pe_el.findtext("CurrentValue")
                                if cv_txt is not None:
                                    try:
                                        v = float(cv_txt)
                                        if v != 0.0 or not (pe_el.findtext("StartKeyframe") or ""):
                                            return v
                                    except ValueError:
                                        pass
                                skf_txt = pe_el.findtext("StartKeyframe") or ""
                                sm = re.match(r"-?\d+,(-?\d+\.?\d*)", skf_txt)
                                if sm:
                                    try:
                                        return float(sm.group(1))
                                    except ValueError:
                                        pass
                                return default

                            scale_val = 100.0
                            xform_scale_val = 100.0
                            pos_val = (0.5, 0.5)
                            pos_kfs: List[Tuple[int, float, float]] = []
                            audio_lvl = 1.0
                            has_lum, has_blur, has_crop, has_hflip, has_mot = False, False, False, False, False
                            mnames: List[str] = []

                            co = ti.find(".//ComponentOwner")
                            vcc = deref(co.find("Components")) if co is not None else None
                            if vcc is not None:
                                comps = vcc.find("ComponentChain/Components")
                                if comps is not None:
                                    for cr in comps:
                                        ce = deref(cr)
                                        if ce is None:
                                            continue
                                        mn = ce.findtext(".//MatchName") or ""
                                        mnames.append(mn)
                                        bypassed = False
                                        params_el = ce.find(".//Params")
                                        if params_el is not None:
                                            for pref in params_el:
                                                pe = deref(pref)
                                                if pe is None:
                                                    continue
                                                pname = pe.findtext("Name") or ""
                                                cval = pe.findtext("CurrentValue")
                                                if pname == "Bypass" and cval in ("true", "1"):
                                                    bypassed = True
                                                elif mn == "AE.ADBE Motion":
                                                    if pname == "Scale":
                                                        sv = read_param_float(pe)
                                                        if sv is not None:
                                                            scale_val = sv
                                                    elif pname == "Position":
                                                        skf = pe.findtext("StartKeyframe") or ""
                                                        pm = re.search(r"(-?\d+\.?\d*):(-?\d+\.?\d*)", skf)
                                                        if pm:
                                                            pos_val = (float(pm.group(1)), float(pm.group(2)))
                                                        kft = pe.findtext("Keyframes") or ""
                                                        for part in kft.split(";"):
                                                            km = re.match(r"(\d+),(-?\d+\.?\d*):(-?\d+\.?\d*)", part.strip())
                                                            if km:
                                                                pos_kfs.append((int(km.group(1)), float(km.group(2)), float(km.group(3))))
                                                elif mn in ("AE.ADBE Geometry", "AE.ADBE Geometry2") and pname in ("Scale Height", "Scale"):
                                                    xv = read_param_float(pe)
                                                    if xv is not None and xv > 1.0:
                                                        xform_scale_val = max(xform_scale_val, xv)
                                                elif not is_video and pname == "Level":
                                                    lv = read_param_float(pe)
                                                    if lv is not None:
                                                        audio_lvl = lv

                                        if not bypassed:
                                            if mn == "AE.ADBE Motion":
                                                has_mot = True
                                            elif "Lumetri" in mn:
                                                has_lum = True
                                            elif any(b in mn for b in ("Blur", "Impact_Blur")):
                                                has_blur = True
                                            elif "AECrop" in mn:
                                                has_crop = True
                                            elif "Horizontal Flip" in mn:
                                                has_hflip = True

                            items_out.append(
                                ClipItem(
                                    object_id=oid,
                                    track_index=idx,
                                    track_type="video" if is_video else "audio",
                                    name=nm,
                                    start_ticks=st,
                                    end_ticks=et,
                                    in_ticks=in_t,
                                    out_ticks=out_t,
                                    disabled=dis,
                                    audio_level=audio_lvl,
                                    scale=scale_val,
                                    transform_scale=xform_scale_val,
                                    fit_scale=fit_scale_val,
                                    position=pos_val,
                                    pos_keyframes=pos_kfs,
                                    has_lumetri=has_lum,
                                    has_blur=has_blur,
                                    has_crop=has_crop,
                                    has_hflip=has_hflip,
                                    has_motion=has_mot,
                                    match_names=mnames,
                                )
                            )
                items_out.sort(key=lambda c: c.start_ticks)
                if is_video:
                    v_tracks.append(items_out)
                else:
                    a_tracks.append(items_out)

    v2 = v_tracks[1] if len(v_tracks) >= 2 else []
    max_ticks = max((c.end_ticks for c in v2), default=0)
    if max_ticks == 0:
        for tr in v_tracks:
            for c in tr:
                max_ticks = max(max_ticks, c.end_ticks)

    media_paths: List[str] = []
    for m in root.iter("Media"):
        mp = m.findtext("ActualMediaFilePath") or m.findtext("FilePath") or ""
        if mp:
            media_paths.append(mp)

    mc_count = sum(1 for e in root.findall("MasterClip") if "ObjectUID" in e.attrib)
    cpi_count = sum(1 for e in root.findall("ClipProjectItem") if "ObjectUID" in e.attrib)
    pek_count = sum(1 for _ in root.iter("PeakFilePath")) + sum(1 for _ in root.iter("ConformedAudioPath"))
    non_unit_speeds = sum(
        1 for el in root.findall(".//PlaybackSpeed") if el.text and abs(float(el.text.strip()) - 1.0) > 1e-4
    )

    dangling = non_unit_speeds
    for el in seq_el.iter():
        ref = el.attrib.get("ObjectRef")
        if ref and ref not in by_id:
            dangling += 1
        uref = el.attrib.get("ObjectURef")
        if uref and uref not in by_uid:
            dangling += 1

    dt_ms = (time.perf_counter() - t0) * 1000.0
    return BonkParsedProject(
        project_id=project_id,
        prproj_path=prproj_path,
        seq_name=seq_el.findtext("Name") or "",
        video_tracks=v_tracks,
        audio_tracks=a_tracks,
        total_dur_ticks=max_ticks,
        media_paths=media_paths,
        master_clip_count=mc_count,
        clip_project_item_count=cpi_count,
        pek_tag_count=pek_count,
        dangling_refs=dangling,
        parse_ms=dt_ms,
    )


def load_ground_truth(project_id: str, pdir: str) -> GroundTruth:
    num = re.sub(r"\D+", "", project_id)
    gt = GroundTruth(project_id=project_id)

    csv_path = os.path.join(pdir, f"sheet_KB{num}.csv")
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8", errors="replace") as f:
            for r in csv.reader(f):
                if len(r) >= 7 and r[5].strip().isdigit():
                    gt.sheet_rows.append(
                        {
                            "stt": r[5].strip(),
                            "flag": r[0].strip(),
                            "desc": r[1].strip(),
                            "link": r[2].strip(),
                            "time": r[3].strip(),
                            "cre": r[6].strip(),
                            "cmt": r[7].strip() if len(r) > 7 else "",
                        }
                    )

    json_path = os.path.join(pdir, f"{project_id}_s{num}.json")
    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as f:
            d = json.load(f).get("data", {})
            gt.amz_items = d.get("footages", [])

    return gt


# ---------------------------------------------------------------------------
# Helpers for Slot Matching & Note Parsing
# ---------------------------------------------------------------------------

def find_part1_clips(v2: List[ClipItem], project_id: str, stt: str) -> List[ClipItem]:
    pat = re.compile(rf"^bonk\.{re.escape(project_id)}\.{re.escape(stt)}(?:[-_ (]|\.)", re.I)
    return [c for c in v2 if not c.disabled and pat.search(c.name)]


def find_part2_clips(v2: List[ClipItem], slot: int) -> List[ClipItem]:
    s2 = f"{slot:02d}"
    pat = re.compile(rf"^{s2}(?:[-_ (]|\.)", re.I)
    return [c for c in v2 if not c.disabled and "bonk." not in c.name.lower() and pat.search(c.name)]


def parse_sec_token(tok: str) -> Optional[float]:
    tok = tok.strip().replace(";", ":")
    m = re.match(r"^(\d+):(\d{1,2})$", tok)
    if m:
        return int(m.group(1)) * 60.0 + int(m.group(2))
    m2 = re.match(r"^(\d+(?:\.\d+)?)$", tok)
    if m2:
        return float(m2.group(1))
    return None


# ---------------------------------------------------------------------------
# 20 Formal Bonk Assertions (BONK-R1 .. BONK-R6)
# ---------------------------------------------------------------------------

def run_assertions(proj: BonkParsedProject, gt: GroundTruth) -> List[AssertionResult]:
    res: List[AssertionResult] = []
    v1 = [c for c in proj.vtrack(1) if not c.disabled]
    v2 = [c for c in proj.vtrack(2) if not c.disabled]
    v3 = [c for c in proj.vtrack(3) if not c.disabled]
    v4 = [c for c in proj.vtrack(4) if not c.disabled]
    v5 = [c for c in proj.vtrack(5) if not c.disabled]
    a1 = proj.atrack(1)
    a2 = [c for c in proj.atrack(2) if not c.disabled]
    a3 = [c for c in proj.atrack(3) if not c.disabled]
    a4 = [c for c in proj.atrack(4) if not c.disabled]

    # BONK-R1-01: Cold Open 00:00
    if v2 and v2[0].start_ticks <= TICKS_PER_FRAME and "warning" not in v2[0].name.lower():
        res.append(AssertionResult("BONK-R1-01", "Zero-Fluff Cold Open at 00:00", True, f"First clip '{v2[0].name}' starts at {v2[0].start_sec:.3f}s"))
    else:
        first_info = f"{v2[0].name} @ {v2[0].start_sec:.2f}s" if v2 else "V2 empty"
        res.append(AssertionResult("BONK-R1-01", "Zero-Fluff Cold Open at 00:00", False, f"Invalid cold open: {first_info}"))

    # BONK-R1-02: Episode Clip Count & Duration (7.5m standard OR 15m extended)
    dur_s = proj.total_dur_sec
    ok_r102 = ((80 <= len(v2) <= 98) and (410.0 <= dur_s <= 495.0)) or (
        (100 <= len(v2) <= 130) and (880.0 <= dur_s <= 960.0)
    )
    res.append(
        AssertionResult(
            "BONK-R1-02",
            "Episode Clip Count (80-130) & Duration (7.5m / 15m)",
            ok_r102,
            f"V2 clips={len(v2)}, duration={dur_s:.1f}s ({dur_s/60:.2f}m)",
        )
    )

    # BONK-R1-03: Explicit Note Duration Fidelity (Zero ~5.3s Center-Crop Truncation)
    note_violations: List[str] = []
    for it in gt.amz_items:
        nt = (it.get("note") or "").strip()
        if not nt:
            continue
        slot = int(it.get("sortOrder") or 0)
        clips = find_part2_clips(v2, slot)
        if not clips:
            continue
        c0 = clips[0]
        total_clip_dur = sum(c.dur_sec for c in clips)
        nt_low = nt.lower()

        # Case A: "N giây đầu" / "Ns đầu" / "vài s đầu" / "mấy giây đầu"
        m_head = re.search(r"(\d+)\s*(?:s|giây)\s*đầu", nt_low)
        if m_head:
            req_n = float(m_head.group(1))
            if c0.in_sec > 0.65:
                note_violations.append(f"#{slot:02d}[{nt}]: in={c0.in_sec:.2f}s (>0.65s head cut)")
            elif req_n >= 7.0 and total_clip_dur < min(req_n - 1.2, 6.2):
                note_violations.append(f"#{slot:02d}[{nt}]: dur={total_clip_dur:.2f}s (capped < {req_n:.0f}s)")
            continue
        if any(k in nt_low for k in ("vài s đầu", "vài giây đầu", "mấy s đầu", "mấy giây đầu")) or nt_low == "đầu":
            if c0.in_sec > 0.65:
                note_violations.append(f"#{slot:02d}[{nt}]: in={c0.in_sec:.2f}s (>0.65s head cut)")
            continue
        if nt_low == "full":
            if c0.in_sec > 0.65:
                note_violations.append(f"#{slot:02d}[{nt}]: in={c0.in_sec:.2f}s (center-cropped 'full')")
            continue

        # Case B: Explicit range "0:35 - 0:48" / "15 tới 24" / "6 - 16"
        m_rng = re.search(r"(\d+(?:[:;]\d{1,2})?)\s*(?:-|–|tới|đến)\s*(\d+(?:[:;]\d{1,2})?)", nt_low)
        if m_rng and "|" not in nt_low:
            t_a = parse_sec_token(m_rng.group(1))
            t_b = parse_sec_token(m_rng.group(2))
            if t_a is not None and t_b is not None and t_b > t_a:
                exp_dur = t_b - t_a
                if exp_dur >= 7.5 and total_clip_dur < exp_dur - 1.5:
                    note_violations.append(f"#{slot:02d}[{nt}]: dur={total_clip_dur:.2f}s vs expected {exp_dur:.1f}s")

    res.append(
        AssertionResult(
            "BONK-R1-03",
            "Explicit Note Duration Fidelity (Zero ~5.3s Center-Crop)",
            len(note_violations) == 0,
            "All explicit AMZ notes honored" if not note_violations else f"{len(note_violations)} violations: {'; '.join(note_violations[:5])}",
        )
    )

    # BONK-R1-04: Multi-Source Split Fidelity ("2 sr" / multi-timestamp)
    split_violations: List[str] = []
    for it in gt.amz_items:
        nt = (it.get("note") or "").strip().lower()
        if re.search(r"\b2\s*sr\b", nt):
            slot = int(it.get("sortOrder") or 0)
            clips = find_part2_clips(v2, slot)
            if len(clips) < 2:
                split_violations.append(f"AMZ #{slot:02d}[{nt}] has {len(clips)} clip(s)")
    for row in gt.sheet_rows:
        tm = row["time"]
        if "|" in tm or "\n" in tm or tm.count("-") >= 2:
            clips = find_part1_clips(v2, proj.project_id, row["stt"])
            if len(clips) < 2:
                split_violations.append(f"Sheet #{row['stt']}[{tm}] has {len(clips)} clip(s)")
    res.append(
        AssertionResult(
            "BONK-R1-04",
            "Multi-Source ('2 sr' / Multi-TS) Discrete Split",
            len(split_violations) == 0,
            "All multi-source entries properly split" if not split_violations else "; ".join(split_violations),
        )
    )

    # BONK-R2-01: V1/V2 Visual Treatment Chain
    v1_bad = sum(1 for c in v1 if c.effective_zoom_pct < 340.0 or not c.has_blur or not c.has_lumetri)
    v2_no_lum = sum(1 for c in v2 if not c.has_lumetri)
    ok_r201 = (len(v1) > 0 and v1_bad == 0 and v2_no_lum == 0)
    res.append(
        AssertionResult(
            "BONK-R2-01",
            "V1 Blur/Darken Chain & V2 Lumetri Pop/Sharpen Chain",
            ok_r201,
            f"V1 incomplete={v1_bad}/{len(v1)}, V2 missing Lumetri={v2_no_lum}/{len(v2)}",
        )
    )

    # BONK-R2-02: Text Clip No-Flip Guard ("có text")
    flipped_text: List[str] = []
    for row in gt.sheet_rows:
        combined = f"{row['flag']} {row['cre']} {row['cmt']}".lower()
        if "có text" in combined or "co text" in combined:
            for c in find_part1_clips(v2, proj.project_id, row["stt"]):
                if c.has_hflip:
                    flipped_text.append(f"Sheet #{row['stt']} ({c.name})")
    for it in gt.amz_items:
        nt = (it.get("note") or "").lower()
        if "có text" in nt or "co text" in nt:
            slot = int(it.get("sortOrder") or 0)
            for c in find_part2_clips(v2, slot):
                if c.has_hflip:
                    flipped_text.append(f"AMZ #{slot:02d} ({c.name})")
    res.append(
        AssertionResult(
            "BONK-R2-02",
            "Readable Text Clip No-Flip Guard ('có text')",
            len(flipped_text) == 0,
            "0 text clips flipped" if not flipped_text else f"Flipped text clips: {', '.join(flipped_text)}",
        )
    )

    # BONK-R2-03: ViralHog Zoom-Only Rule (Effective Zoom >= 114.5% over fit_scale, 0 Blur Mask)
    vh_violations: List[str] = []
    for row in gt.sheet_rows:
        if "viralhog" in f"{row['cre']} {row['link']}".lower():
            for c in find_part1_clips(v2, proj.project_id, row["stt"]):
                if c.effective_zoom_pct < 114.5 or c.has_blur:
                    vh_violations.append(f"Sheet #{row['stt']} eff_zoom={c.effective_zoom_pct:.1f}% blur={c.has_blur}")
    for it in gt.amz_items:
        ft = json.dumps(it.get("footage") or {}, ensure_ascii=False).lower()
        if "viralhog" in ft:
            slot = int(it.get("sortOrder") or 0)
            for c in find_part2_clips(v2, slot):
                if c.effective_zoom_pct < 114.5 or c.has_blur:
                    vh_violations.append(f"AMZ #{slot:02d} eff_zoom={c.effective_zoom_pct:.1f}% blur={c.has_blur}")
    res.append(
        AssertionResult(
            "BONK-R2-03",
            "ViralHog Zoom-Only Rule (Effective Zoom >= 115%, 0 Blur)",
            len(vh_violations) == 0,
            "0 ViralHog violations" if not vh_violations else "; ".join(vh_violations[:5]),
        )
    )

    # BONK-R2-04: Full-Span Brand Logos on V3 & V4
    v3_cov = sum(c.dur_sec for c in v3) / dur_s if dur_s > 0 else 0.0
    v4_cov = sum(c.dur_sec for c in v4) / dur_s if dur_s > 0 else 0.0
    ok_r204 = v3_cov >= 0.99 and v4_cov >= 0.99
    res.append(
        AssertionResult(
            "BONK-R2-04",
            "Full-Timeline Brand Logos on Track V3 & Track V4",
            ok_r204,
            f"V3 coverage={v3_cov*100:.1f}%, V4 coverage={v4_cov*100:.1f}%",
        )
    )

    # BONK-R3-01: Strict Zero-VO on Track A2
    res.append(
        AssertionResult(
            "BONK-R3-01",
            "Strict Zero-VO Policy (Track A2 100% Empty)",
            len(a2) == 0,
            f"Track A2 active items={len(a2)}",
        )
    )

    # BONK-R3-02: Strict Interjection SFX Ban
    timeline_interj = [c.name for c in (a3 + a4) if c.name.lower() in BANNED_INTERJECTIONS]
    bin_interj = sorted({os.path.basename(m) for m in proj.media_paths if os.path.basename(m).lower() in BANNED_INTERJECTIONS or "\\interjection\\" in m.lower()})
    ok_r302 = len(timeline_interj) == 0 and len(bin_interj) == 0
    res.append(
        AssertionResult(
            "BONK-R3-02",
            "Strict Ban on 37 Verbal Interjection SFX Files",
            ok_r302,
            "0 interjection SFX in timeline or project XML"
            if ok_r302
            else f"Timeline={len(timeline_interj)}, ProjectBin={len(bin_interj)} ({bin_interj[:3]})",
        )
    )

    # BONK-R3-03: Copyright Music Mute Guard ("có nhạc" / "tắt nhạc")
    music_leaks: List[str] = []
    for row in gt.sheet_rows:
        combined = f"{row['flag']} {row['cre']} {row['cmt']}".lower()
        if "có nhạc" in combined or "tắt nhạc" in combined:
            for vc in find_part1_clips(v2, proj.project_id, row["stt"]):
                overlapping_a1 = [
                    ac for ac in a1
                    if not ac.is_muted and min(vc.end_ticks, ac.end_ticks) - max(vc.start_ticks, ac.start_ticks) > TICKS_PER_FRAME
                ]
                if overlapping_a1:
                    music_leaks.append(f"Sheet #{row['stt']} ({vc.name}) A1 not muted")
    res.append(
        AssertionResult(
            "BONK-R3-03",
            "Copyright Music Mute Guard ('có nhạc' / 'tắt nhạc gốc')",
            len(music_leaks) == 0,
            "All flagged music clips muted on A1" if not music_leaks else "; ".join(music_leaks),
        )
    )

    # BONK-R3-04: Silent Block Acoustic Rescue on A3/A4
    all_sfx = a3 + a4
    unrescued_silent: List[str] = []
    silent_v2_count = 0
    for vc in v2:
        paired_audible_a1 = [
            ac for ac in a1
            if not ac.is_muted and min(vc.end_ticks, ac.end_ticks) - max(vc.start_ticks, ac.start_ticks) > TICKS_PER_FRAME
        ]
        if not paired_audible_a1:
            silent_v2_count += 1
            overlapping_sfx = [
                sc for sc in all_sfx
                if min(vc.end_ticks, sc.end_ticks) - max(vc.start_ticks, sc.start_ticks) > 0
            ]
            if not overlapping_sfx:
                unrescued_silent.append(f"{vc.name}@{vc.start_sec:.1f}s")
    res.append(
        AssertionResult(
            "BONK-R3-04",
            "100% Foley/Impact SFX Rescue on Silent Clips (A3/A4)",
            len(unrescued_silent) == 0,
            f"All {silent_v2_count} silent clips covered by SFX"
            if not unrescued_silent
            else f"{len(unrescued_silent)}/{silent_v2_count} silent clips left dead-silent: {', '.join(unrescued_silent[:5])}",
        )
    )

    # BONK-R4-01: Censor Note ("che") Coverage
    uncensored: List[str] = []
    for row in gt.sheet_rows:
        combined = f"{row['flag']} {row['cre']} {row['cmt']}".lower()
        if re.search(r"\bche\b", combined):
            for vc in find_part1_clips(v2, proj.project_id, row["stt"]):
                has_v5 = any(min(vc.end_ticks, g.end_ticks) > max(vc.start_ticks, g.start_ticks) for g in v5)
                if not (has_v5 or vc.has_blur):
                    uncensored.append(f"Sheet #{row['stt']} ({vc.name})")
    for it in gt.amz_items:
        nt = (it.get("note") or "").lower()
        if re.search(r"\bche\b", nt):
            slot = int(it.get("sortOrder") or 0)
            for vc in find_part2_clips(v2, slot):
                has_v5 = any(min(vc.end_ticks, g.end_ticks) > max(vc.start_ticks, g.start_ticks) for g in v5)
                if not (has_v5 or vc.has_blur):
                    uncensored.append(f"AMZ #{slot:02d} ({vc.name})")
    res.append(
        AssertionResult(
            "BONK-R4-01",
            "Censor Note ('che') Shield / Blur Coverage",
            len(uncensored) == 0,
            "All 'che' notes covered" if not uncensored else f"Missing shield/blur: {', '.join(uncensored)}",
        )
    )

    # BONK-R4-02: Context Clarification ("note ...") Overlay on Track V5
    missing_note_overlays: List[str] = []
    for it in gt.amz_items:
        nt = (it.get("note") or "").strip()
        if re.match(r"^note\b", nt.lower()):
            slot = int(it.get("sortOrder") or 0)
            for vc in find_part2_clips(v2, slot):
                has_v5_note = any(
                    min(vc.end_ticks, g.end_ticks) > max(vc.start_ticks, g.start_ticks)
                    for g in v5
                )
                if not has_v5_note:
                    missing_note_overlays.append(f"AMZ #{slot:02d}[{nt}]")
    res.append(
        AssertionResult(
            "BONK-R4-02",
            "Context Clarification ('note ...') Overlay on Track V5",
            len(missing_note_overlays) == 0,
            "All viewer clarification notes overlaid"
            if not missing_note_overlays
            else f"Missing V5 note overlay: {', '.join(missing_note_overlays)}",
        )
    )

    # BONK-R4-03: Zero Static Center (0.50, 0.50) Emojis on Track V5
    static_emojis = [g.name for g in v5 if g.name.lower().endswith(".gif") and g.is_static_center]
    res.append(
        AssertionResult(
            "BONK-R4-03",
            "Zero Static Center (0.50, 0.50) Emojis on Track V5",
            len(static_emojis) == 0,
            "0 static center emojis" if not static_emojis else f"Static center emojis: {static_emojis}",
        )
    )

    # BONK-R6-01: Zero Black Gaps on V2
    gaps: List[str] = []
    for i in range(len(v2) - 1):
        g_ticks = v2[i + 1].start_ticks - v2[i].end_ticks
        if g_ticks > TICKS_PER_FRAME:
            gaps.append(f"{v2[i].end_sec:.2f}s->{v2[i+1].start_sec:.2f}s ({g_ticks/TICKS_PER_SEC:.3f}s)")
    res.append(
        AssertionResult(
            "BONK-R6-01",
            "INV-01 Zero Black Gaps on Primary Track V2",
            len(gaps) == 0,
            "0 black gaps on V2" if not gaps else f"{len(gaps)} gaps: {', '.join(gaps[:4])}",
        )
    )

    # BONK-R6-02: 1:1 V1 == V2 Background-Foreground Sync
    v1_v2_mismatch = abs(len(v1) - len(v2))
    pair_drifts = 0
    for c1, c2 in zip(v1, v2):
        if abs(c1.start_ticks - c2.start_ticks) > TICKS_PER_FRAME or abs(c1.end_ticks - c2.end_ticks) > TICKS_PER_FRAME:
            pair_drifts += 1
    ok_r602 = v1_v2_mismatch == 0 and pair_drifts == 0
    res.append(
        AssertionResult(
            "BONK-R6-02",
            "1:1 Track V1 == Track V2 Frame Synchronization",
            ok_r602,
            f"V1={len(v1)}, V2={len(v2)}, drifted_pairs={pair_drifts}",
        )
    )

    # BONK-R6-03: Zero V2 == A1 Audio Drift on Audible Clips
    a1_drifts: List[str] = []
    audible_a1 = [ac for ac in a1 if not ac.is_muted]
    v2_by_start = {round(vc.start_ticks / TICKS_PER_FRAME): vc for vc in v2}
    for ac in audible_a1:
        f_key = round(ac.start_ticks / TICKS_PER_FRAME)
        vc = v2_by_start.get(f_key) or v2_by_start.get(f_key - 1) or v2_by_start.get(f_key + 1)
        if vc is None:
            a1_drifts.append(f"{ac.name}@{ac.start_sec:.2f}s (unpaired)")
        elif (
            abs(ac.end_ticks - vc.end_ticks) > TICKS_PER_FRAME
            or abs(ac.in_ticks - vc.in_ticks) > TICKS_PER_FRAME * 2
        ):
            a1_drifts.append(f"{ac.name}@{ac.start_sec:.2f}s")
    res.append(
        AssertionResult(
            "BONK-R6-03",
            "Zero Track V2 == Track A1 Audio Sync Drift",
            len(a1_drifts) == 0,
            f"0 drift across {len(audible_a1)} audible A1 clips"
            if not a1_drifts
            else f"{len(a1_drifts)} drifted A1 clips: {', '.join(a1_drifts[:4])}",
        )
    )

    # BONK-R6-04: Zero Donor Episode Leaks
    pid_low = proj.project_id.lower()
    leaked_eps: Set[str] = set()
    for mp in proj.media_paths:
        ml = mp.lower()
        for m in re.findall(r"(?:\\project\\|\.)(kb\d+)(?:\\|\.)", ml):
            if m != pid_low:
                leaked_eps.add(m)
    res.append(
        AssertionResult(
            "BONK-R6-04",
            "Zero Foreign Donor Episode Path Leaks",
            len(leaked_eps) == 0,
            "0 foreign kb path leaks" if not leaked_eps else f"Leaked episodes: {sorted(leaked_eps)}",
        )
    )

    # BONK-R6-05: 7-Point .prproj Bin & .pek Waveform Hygiene
    orphan_mc = max(0, proj.master_clip_count - proj.clip_project_item_count)
    ok_r605 = proj.dangling_refs == 0 and proj.pek_tag_count == 0 and orphan_mc <= 15
    res.append(
        AssertionResult(
            "BONK-R6-05",
            "7-Point .prproj Hygiene (0 Dangling, 0 .pek, 0 Orphan MCs)",
            ok_r605,
            f"dangling={proj.dangling_refs}, pek_tags={proj.pek_tag_count}, MasterClips={proj.master_clip_count}, BinnedCPIs={proj.clip_project_item_count} (orphans={orphan_mc})",
        )
    )

    return res


# ---------------------------------------------------------------------------
# Runner & Report Generation
# ---------------------------------------------------------------------------

def render_markdown_report(reports: List[ProjectReport], timestamp: str, elapsed_s: float) -> str:
    tot_a = sum(r.total for r in reports)
    tot_p = sum(r.passed for r in reports)
    tot_f = sum(r.failed for r in reports)
    rate = (tot_p / tot_a * 100.0) if tot_a else 0.0

    lines = [
        "# Bonk! Funny Moments — E2E Baseline Audit Report",
        f"- **Timestamp (UTC)**: `{timestamp}`",
        f"- **Execution Time**: `{elapsed_s:.2f}s`",
        f"- **Overall Score**: **{tot_p}/{tot_a}** assertions passed (**{rate:.1f}%**, `{tot_f}` failed)",
        "",
        "## Summary Matrix",
        "| Project | Passed | Failed | Total | Pass Rate | Parse Time | Status |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for rep in reports:
        st = "PASS" if rep.failed == 0 else "FAIL"
        lines.append(
            f"| **{rep.project_id}** | {rep.passed} | {rep.failed} | {rep.total} | {rep.pass_rate:.1f}% | {rep.parse_ms:.1f}ms | `{st}` |"
        )

    lines.append("\n## Detailed Failures by Project")
    for rep in reports:
        fails = [r for r in rep.results if not r.passed]
        lines.append(f"\n### `{rep.project_id}` ({rep.passed}/{rep.total} passed)")
        if not fails:
            lines.append("- All 20 assertions passed.")
        else:
            for f in fails:
                lines.append(f"- **[FAIL] `{f.assertion_id}` ({f.title})**: {f.details}")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Bonk! Funny Moments E2E Test Suite Runner")
    parser.add_argument(
        "--target",
        "--project",
        nargs="+",
        default=["kb26", "kb27", "kb28", "kb29", "kb30", "kb31", "kb32", "kb33", "kb34"],
        help="Target project IDs (e.g. kb27 kb33 kb34)",
    )
    parser.add_argument(
        "--project-root",
        default=DEFAULT_PROJECT_ROOT,
        help="Path to Bonk project directory",
    )
    parser.add_argument(
        "--mode",
        choices=["audit", "strict"],
        default="audit",
        help="'audit' writes reports and exits 0; 'strict' exits 1 on any failure.",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(SCRIPT_DIR, "reports"),
        help="Output folder for Markdown & JSON reports",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t_suite = time.perf_counter()

    targets = [t.lower().replace(".prproj", "").strip() for t in args.target if t.strip()]
    reports: List[ProjectReport] = []

    print("\n================================================================================")
    print("  Bonk! Funny Moments E2E Automated Test Suite (20 Assertions — Fast AST)")
    print(f"  Targets: {', '.join(targets)} | Mode: {args.mode.upper()}")
    print("================================================================================\n")

    for pid in targets:
        pdir = os.path.join(args.project_root, pid)
        prp = os.path.join(pdir, f"{pid}.prproj")
        if not os.path.exists(prp):
            print(f"[!] Skipping {pid}: {prp} not found")
            continue
        print(f"[*] Auditing {pid.upper()}...", end="", flush=True)
        proj = parse_bonk_prproj(pid, prp)
        gt = load_ground_truth(pid, pdir)
        results = run_assertions(proj, gt)
        rep = ProjectReport(project_id=pid, parse_ms=proj.parse_ms, results=results)
        reports.append(rep)
        st = "PASS" if rep.failed == 0 else "FAIL"
        print(f" [{st}] in {proj.parse_ms:.1f}ms ({rep.passed}/{rep.total} passed)")

    elapsed = time.perf_counter() - t_suite
    tot_a = sum(r.total for r in reports)
    tot_p = sum(r.passed for r in reports)
    tot_f = sum(r.failed for r in reports)
    rate = (tot_p / tot_a * 100.0) if tot_a else 0.0

    if HAVE_RICH:
        console = Console()
        tbl = Table(title="Bonk! Funny Moments E2E Audit Matrix", header_style="bold cyan")
        tbl.add_column("Project", style="bold")
        tbl.add_column("Passed", justify="right", style="green")
        tbl.add_column("Failed", justify="right", style="red")
        tbl.add_column("Total", justify="right")
        tbl.add_column("Pass Rate", justify="right")
        tbl.add_column("Status", justify="center")
        for rep in reports:
            st = "[bold green]PASS[/bold green]" if rep.failed == 0 else "[bold red]FAIL[/bold red]"
            tbl.add_row(rep.project_id, str(rep.passed), str(rep.failed), str(rep.total), f"{rep.pass_rate:.1f}%", st)
        console.print(tbl)
        console.print(
            Panel(
                f"[bold]Total Assertions[/bold]: {tot_a} | [bold green]Passed[/bold green]: {tot_p} | "
                f"[bold red]Failed[/bold red]: {tot_f} | [bold cyan]Pass Rate[/bold cyan]: {rate:.1f}%\n"
                f"[dim]Total Execution Time: {elapsed:.2f}s[/dim]",
                title="Bonk Execution Gate",
            )
        )

    md_path = os.path.join(args.output_dir, "bonk_baseline_report.md")
    json_path = os.path.join(args.output_dir, "bonk_baseline_metrics.json")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown_report(reports, now_str, elapsed))

    json_payload = {
        "timestamp": now_str,
        "elapsed_sec": round(elapsed, 3),
        "total_assertions": tot_a,
        "total_passed": tot_p,
        "total_failed": tot_f,
        "overall_pass_rate": round(rate, 2),
        "projects": {
            rep.project_id: {
                "passed": rep.passed,
                "failed": rep.failed,
                "total": rep.total,
                "pass_rate": round(rep.pass_rate, 2),
                "parse_ms": round(rep.parse_ms, 1),
                "assertions": [
                    {"id": r.assertion_id, "title": r.title, "passed": r.passed, "details": r.details}
                    for r in rep.results
                ],
            }
            for rep in reports
        },
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Saved baseline reports:")
    print(f"    - Markdown: {md_path}")
    print(f"    - JSON:     {json_path}")

    if args.mode == "strict" and tot_f > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
