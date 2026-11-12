"""
Fast Offline Premiere Pro (.prproj) XML AST Parser.
Parses gzipped Premiere Pro XML project files in <250ms, extracting full track
and clip hierarchies, Component chains (Scale, Crop, Blur, Mask, Text), and timing.
"""

from __future__ import annotations
import gzip
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import xml.etree.ElementTree as ET

from .timeline_math import (
    FPS,
    TICKS_PER_FRAME,
    TICKS_PER_SEC,
    ticks_to_frame,
    ticks_to_sec,
)


@dataclass
class ClipComponent:
    object_id: str
    match_name: str
    display_name: str
    params: Dict[str, Any] = field(default_factory=dict)
    instance_names: List[str] = field(default_factory=list)


@dataclass
class TrackClipItem:
    object_id: str
    track_index: int
    track_type: str  # "video" or "audio"
    name: str
    start_ticks: int
    end_ticks: int
    in_ticks: int = 0
    out_ticks: int = 0
    media_path: str = ""
    scale: float = 100.0
    position: Tuple[float, float] = (0.5, 0.5)
    position_keyframes: List[Tuple[int, float, float]] = field(default_factory=list)
    crop_left: float = 0.0
    crop_right: float = 0.0
    crop_top: float = 0.0
    crop_bottom: float = 0.0
    blur_effects: List[str] = field(default_factory=list)
    text_instance_names: List[str] = field(default_factory=list)
    components: List[ClipComponent] = field(default_factory=list)

    @property
    def start_sec(self) -> float:
        return ticks_to_sec(self.start_ticks)

    @property
    def end_sec(self) -> float:
        return ticks_to_sec(self.end_ticks)

    @property
    def duration_sec(self) -> float:
        return ticks_to_sec(self.end_ticks - self.start_ticks)

    @property
    def start_frame(self) -> int:
        return ticks_to_frame(self.start_ticks)

    @property
    def end_frame(self) -> int:
        return ticks_to_frame(self.end_ticks)

    @property
    def duration_frames(self) -> int:
        return self.end_frame - self.start_frame

    @property
    def in_sec(self) -> float:
        return ticks_to_sec(self.in_ticks)

    @property
    def out_sec(self) -> float:
        return ticks_to_sec(self.out_ticks)

    @property
    def is_static_center(self) -> bool:
        """Check if all position keyframes or start position are concentrated around (0.50, 0.50)."""
        pts = [(x, y) for _, x, y in self.position_keyframes]
        if not pts:
            pts = [self.position]
        for x, y in pts:
            if abs(x - 0.50) > 0.04 or abs(y - 0.50) > 0.06:
                return False
        return True


@dataclass
class ParsedSequence:
    name: str
    sequence_uid: str
    video_tracks: List[List[TrackClipItem]] = field(default_factory=list)
    audio_tracks: List[List[TrackClipItem]] = field(default_factory=list)
    total_duration_ticks: int = 0
    parse_time_ms: float = 0.0
    dangling_refs_count: int = 0

    @property
    def total_duration_sec(self) -> float:
        return ticks_to_sec(self.total_duration_ticks)

    @property
    def total_duration_frames(self) -> int:
        return ticks_to_frame(self.total_duration_ticks)

    def get_video_track(self, index: int) -> List[TrackClipItem]:
        """0-indexed: 0=V1, 1=V2, 2=V3, 3=V4, 4=V5, 5=V6, 6=V7, 7=V8, 8=V9, 9=V10"""
        if 0 <= index < len(self.video_tracks):
            return self.video_tracks[index]
        return []

    def get_audio_track(self, index: int) -> List[TrackClipItem]:
        """0-indexed: 0=A1, 1=A2, 2=A3, 3=A4, 4=A5, 5=A6, 6=A7, 7=A8"""
        if 0 <= index < len(self.audio_tracks):
            return self.audio_tracks[index]
        return []


class PrprojFastParser:
    """High-speed offline reader for Adobe Premiere Pro .prproj (gzipped XML)."""

    def __init__(self, prproj_path: str):
        self.prproj_path = prproj_path
        self.by_id: Dict[str, ET.Element] = {}
        self.by_uid: Dict[str, ET.Element] = {}
        self.root: Optional[ET.Element] = None
        self.parse_time_ms: float = 0.0

    def parse(self, target_sequence_name: Optional[str] = None) -> ParsedSequence:
        t0 = time.perf_counter()
        if not os.path.exists(self.prproj_path):
            raise FileNotFoundError(f"Project file not found: {self.prproj_path}")

        with gzip.open(self.prproj_path, "rb") as f:
            raw_bytes = f.read()

        self.root = ET.fromstring(raw_bytes)
        self.by_id = {e.attrib["ObjectID"]: e for e in self.root if "ObjectID" in e.attrib}
        self.by_uid = {e.attrib["ObjectUID"]: e for e in self.root if "ObjectUID" in e.attrib}

        # Sequence resolution: match target_sequence_name, or filename without .prproj
        if not target_sequence_name:
            target_sequence_name = os.path.splitext(os.path.basename(self.prproj_path))[0]

        def _count_seq_items(s: ET.Element) -> int:
            cnt = 0
            tgp = s.find("TrackGroups")
            if tgp is not None:
                for tg in tgp:
                    sec = self._deref(tg.find("Second"))
                    if sec is not None:
                        tc = sec.find("TrackGroup/Tracks")
                        if tc is not None:
                            for tr_ref in tc:
                                tr = self._deref(tr_ref)
                                if tr is not None:
                                    ti = tr.find("ClipTrack/ClipItems/TrackItems")
                                    if ti is not None:
                                        cnt += len(ti)
            return cnt

        seq_el = None
        sequences = [s for s in self.root.iter("Sequence") if "ObjectUID" in s.attrib]
        if target_sequence_name:
            matching = [s for s in sequences if s.findtext("Name") == target_sequence_name]
            if matching:
                seq_el = max(matching, key=_count_seq_items)
        if seq_el is None and sequences:
            # Prefer sequence matching kb* or longest duration
            named_kb = [s for s in sequences if (s.findtext("Name") or "").startswith("kb")]
            seq_el = max(named_kb, key=_count_seq_items) if named_kb else max(sequences, key=_count_seq_items)

        if seq_el is None:
            raise ValueError(f"No valid Sequence found in {self.prproj_path}")

        seq_name = seq_el.findtext("Name") or ""
        seq_uid = seq_el.attrib.get("ObjectUID", "")

        # Extract tracks
        v_track_elements: List[ET.Element] = []
        a_track_elements: List[ET.Element] = []

        tg_parent = seq_el.find("TrackGroups")
        if tg_parent is not None:
            for tg in tg_parent:
                second = self._deref(tg.find("Second"))
                if second is not None:
                    if second.tag == "VideoTrackGroup":
                        tracks_cont = second.find("TrackGroup/Tracks")
                        if tracks_cont is not None:
                            v_track_elements = [self._deref(r) for r in tracks_cont if self._deref(r) is not None]
                    elif second.tag == "AudioTrackGroup":
                        tracks_cont = second.find("TrackGroup/Tracks")
                        if tracks_cont is not None:
                            a_track_elements = [self._deref(r) for r in tracks_cont if self._deref(r) is not None]

        video_tracks = [self._parse_track_items(tr, idx, "video") for idx, tr in enumerate(v_track_elements)]
        audio_tracks = [self._parse_track_items(tr, idx, "audio") for idx, tr in enumerate(a_track_elements)]

        # Calculate sequence duration from V3 (primary video) or all video
        max_ticks = 0
        if len(video_tracks) >= 3 and video_tracks[2]:
            max_ticks = max(item.end_ticks for item in video_tracks[2])
        else:
            for tr in video_tracks:
                for item in tr:
                    if item.end_ticks > max_ticks:
                        max_ticks = item.end_ticks

        dangling_refs = self._check_dangling_references(seq_el)

        t1 = time.perf_counter()
        parse_ms = (t1 - t0) * 1000.0
        self.parse_time_ms = parse_ms

        return ParsedSequence(
            name=seq_name,
            sequence_uid=seq_uid,
            video_tracks=video_tracks,
            audio_tracks=audio_tracks,
            total_duration_ticks=max_ticks,
            parse_time_ms=parse_ms,
            dangling_refs_count=dangling_refs,
        )

    def _deref(self, el: Optional[ET.Element]) -> Optional[ET.Element]:
        if el is None:
            return None
        if "ObjectRef" in el.attrib:
            return self.by_id.get(el.attrib["ObjectRef"])
        if "ObjectURef" in el.attrib:
            return self.by_uid.get(el.attrib["ObjectURef"])
        return None

    def _parse_track_items(self, track_el: ET.Element, track_idx: int, track_type: str) -> List[TrackClipItem]:
        items_cont = track_el.find("./ClipTrack/ClipItems/TrackItems")
        if items_cont is None:
            return []

        out: List[TrackClipItem] = []
        for r in items_cont:
            ti = self._deref(r)
            if ti is None:
                continue

            obj_id = ti.attrib.get("ObjectID", "")
            s_ticks = int(ti.findtext(".//Start") or 0)
            e_ticks = int(ti.findtext(".//End") or 0)

            # SubClip info
            sc = self._deref(ti.find(".//SubClip"))
            name = sc.findtext("Name") if sc is not None else ""

            # InPoint / OutPoint
            in_ticks = 0
            out_ticks = 0
            if sc is not None:
                cl = self._deref(sc.find("Clip"))
                if cl is not None:
                    in_ticks = int(cl.findtext(".//InPoint") or 0)
                    out_ticks = int(cl.findtext(".//OutPoint") or 0)

            # Component Chain analysis
            scale_val = 100.0
            pos_val = (0.5, 0.5)
            pos_keyframes: List[Tuple[int, float, float]] = []
            crop_l, crop_r, crop_t, crop_b = 0.0, 0.0, 0.0, 0.0
            blur_effects: List[str] = []
            text_instances: List[str] = []
            components: List[ClipComponent] = []

            co = ti.find(".//ComponentOwner")
            vcc = self._deref(co.find("Components")) if co is not None else None
            if vcc is not None:
                cc = vcc.find("ComponentChain")
                comps_el = cc.find("Components") if cc is not None else None
                if comps_el is not None:
                    for comp_ref in comps_el:
                        comp_el = self._deref(comp_ref)
                        if comp_el is None:
                            continue
                        mname = comp_el.findtext(".//MatchName") or ""
                        dname = comp_el.findtext(".//DisplayName") or ""
                        c_oid = comp_el.attrib.get("ObjectID", "")

                        # Collect blur effects
                        if any(k in mname for k in ["Blur", "Impact_Blur", "GaussianBlur", "FastBlur"]):
                            blur_effects.append(mname)

                        # Collect text instance names
                        for iname in comp_el.findall(".//InstanceName"):
                            if iname.text and iname.text.strip():
                                text_instances.append(iname.text.strip())

                        # Parse Motion Component parameters
                        if mname == "AE.ADBE Motion":
                            params_el = comp_el.find(".//Params")
                            if params_el is not None:
                                for pref in params_el:
                                    prm = self._deref(pref)
                                    if prm is None:
                                        continue
                                    pname = prm.findtext("Name") or ""
                                    if pname == "Scale":
                                        try:
                                            scale_val = float(prm.findtext("CurrentValue") or 100.0)
                                        except (ValueError, TypeError):
                                            pass
                                    elif pname == "Position":
                                        skf = prm.findtext("StartKeyframe") or ""
                                        pos_m = re.search(r"(-?\d+\.?\d*):(-?\d+\.?\d*)", skf)
                                        if pos_m:
                                            pos_val = (float(pos_m.group(1)), float(pos_m.group(2)))
                                        # Keyframes
                                        kfs_text = prm.findtext("Keyframes") or ""
                                        if kfs_text:
                                            for part in kfs_text.split(";"):
                                                part = part.strip()
                                                if not part:
                                                    continue
                                                kf_m = re.match(r"(\d+),(-?\d+\.?\d*):(-?\d+\.?\d*)", part)
                                                if kf_m:
                                                    pos_keyframes.append(
                                                        (int(kf_m.group(1)), float(kf_m.group(2)), float(kf_m.group(3)))
                                                    )
                                    elif pname == "Crop Left":
                                        try:
                                            crop_l = float(prm.findtext("CurrentValue") or 0.0)
                                        except (ValueError, TypeError):
                                            pass
                                    elif pname == "Crop Right":
                                        try:
                                            crop_r = float(prm.findtext("CurrentValue") or 0.0)
                                        except (ValueError, TypeError):
                                            pass
                                    elif pname == "Crop Top":
                                        try:
                                            crop_t = float(prm.findtext("CurrentValue") or 0.0)
                                        except (ValueError, TypeError):
                                            pass
                                    elif pname == "Crop Bottom":
                                        try:
                                            crop_b = float(prm.findtext("CurrentValue") or 0.0)
                                        except (ValueError, TypeError):
                                            pass

                        components.append(
                            ClipComponent(
                                object_id=c_oid,
                                match_name=mname,
                                display_name=dname,
                                instance_names=list(text_instances),
                            )
                        )

            clip_item = TrackClipItem(
                object_id=obj_id,
                track_index=track_idx,
                track_type=track_type,
                name=name,
                start_ticks=s_ticks,
                end_ticks=e_ticks,
                in_ticks=in_ticks,
                out_ticks=out_ticks,
                scale=scale_val,
                position=pos_val,
                position_keyframes=pos_keyframes,
                crop_left=crop_l,
                crop_right=crop_r,
                crop_top=crop_t,
                crop_bottom=crop_b,
                blur_effects=blur_effects,
                text_instance_names=text_instances,
                components=components,
            )
            out.append(clip_item)

        return out

    def _check_dangling_references(self, subtree_root: ET.Element) -> int:
        """Count references in subtree that point to missing ObjectIDs or ObjectUIDs."""
        dangling = 0
        for el in subtree_root.iter():
            ref = el.attrib.get("ObjectRef")
            if ref and ref not in self.by_id:
                dangling += 1
            uref = el.attrib.get("ObjectURef")
            if uref and uref not in self.by_uid:
                dangling += 1
        return dangling
