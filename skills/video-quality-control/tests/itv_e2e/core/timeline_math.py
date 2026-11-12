"""
Timeline Math & Timecode Utilities for Premiere Pro Projects.
Standard tick rate: 254,016,000,000 ticks/second.
At 23.976 fps (24000/1001), 1 frame = 10,594,584,000 ticks.
"""

from __future__ import annotations
import math
import re
from typing import Iterable, List, Optional, Set, Tuple

TICKS_PER_SEC: int = 254016000000
TICKS_PER_FRAME: int = 10594584000
FPS: float = 24000.0 / 1001.0  # 23.976023976023978


def ticks_to_sec(ticks: int) -> float:
    return float(ticks) / float(TICKS_PER_SEC)


def sec_to_ticks(sec: float) -> int:
    return int(round(float(sec) * float(TICKS_PER_SEC)))


def ticks_to_frame(ticks: int) -> int:
    return int(round(float(ticks) / float(TICKS_PER_FRAME)))


def frame_to_ticks(frame: int) -> int:
    return int(frame) * TICKS_PER_FRAME


def sec_to_frame(sec: float) -> int:
    return int(round(float(sec) * FPS))


def frame_to_sec(frame: int) -> float:
    return float(frame) / FPS


def parse_time_str_to_sec(time_str: str) -> Optional[float]:
    """Parse time string like '1:04', '0:33', '1:20:15', '45.5', or '10s' to float seconds."""
    if not time_str:
        return None
    s = time_str.strip().lower().replace("s", "").replace(";", ":")
    parts = s.split(":")
    try:
        if len(parts) == 1:
            return float(parts[0])
        elif len(parts) == 2:
            sec_part = float(parts[1])
            if sec_part >= 60.0 and parts[1].strip().endswith("0") and len(parts[1].strip()) == 3:
                sec_part = float(parts[1].strip()[:-1])
            return int(parts[0]) * 60 + sec_part
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except (ValueError, TypeError):
        return None
    return None


def parse_time_range(range_str: str) -> Optional[Tuple[float, float]]:
    """
    Parse a range string like '1:04 - 1:17' or '0:33-0:38' into (start_sec, end_sec).
    Returns None if format is invalid.
    """
    if not range_str:
        return None
    cleaned = range_str.strip().replace(";", ":")
    # Normalize separators
    for sep in [" - ", " – ", " — ", " tới ", " toi ", " to ", "-", "–", "—"]:
        if sep in cleaned:
            parts = cleaned.split(sep, 1)
            t1 = parse_time_str_to_sec(parts[0])
            t2 = parse_time_str_to_sec(parts[1])
            if t1 is not None and t2 is not None and t2 > t1:
                return (t1, t2)
    return None


def parse_multi_time_ranges(text: str) -> List[Tuple[float, float]]:
    """
    Parse text that might contain multiple time ranges separated by newline, comma, or pipe.
    E.g. '0:33 - 0:38\n0:58 - 1:03' -> [(33.0, 38.0), (58.0, 63.0)],
    or '11s đầu\n25 - 31' -> [(0.0, 11.0), (25.0, 31.0)].
    """
    if not text:
        return []
    lines = [l.strip() for l in re.split(r"[\n|;,]+", text) if l.strip()]
    results = []
    for line in lines:
        rng = parse_time_range(line)
        if rng:
            results.append(rng)
            continue
        m_head = re.search(r"^(\d+(?:\.\d+)?)\s*(?:s|giây|giay)?\s*(?:đầu|dau)$", line.strip(), re.I)
        if m_head:
            results.append((0.0, float(m_head.group(1))))
    return results


def parse_note_specification(note: str, raw_duration: Optional[float] = None) -> dict:
    """
    Parse AMZTool note field to determine target duration requirements:
    - 'Ns đầu' (e.g. '6s đầu', '7s đầu', '10s đầu') -> duration = N
    - 'N về sau' / 'N tới hết' -> duration = raw_duration - N
    - 'MM:SS - MM:SS' -> time range
    - '2 source lun' / '2 sr' / multi-timestamp -> is_multi_ts = True
    """
    result = {
        "is_multi_ts": False,
        "multi_ranges": [],
        "target_duration": None,
        "time_range": None,
        "is_non_note": False,
        "rule_type": "none",
    }
    if not note or not note.strip():
        result["is_non_note"] = True
        result["rule_type"] = "raw_full"
        result["target_duration"] = raw_duration
        return result

    cleaned = note.strip().lower()

    # Multi-timestamp check
    multi_ranges = parse_multi_time_ranges(note)
    if len(multi_ranges) >= 2:
        result["is_multi_ts"] = True
        result["multi_ranges"] = multi_ranges
        result["rule_type"] = "multi_timestamp"
        return result

    if any(k in cleaned for k in ["2 sr", "2 source", "hai source", "2 đoạn"]):
        result["is_multi_ts"] = True
        result["rule_type"] = "multi_source_note"

    # Explicit time range e.g. "3:02 - 3:17" or single range with comments e.g. "8 - 18, crop..."
    explicit_lines = [parse_time_range(l.strip()) for l in re.split(r"[\n|;,]+", cleaned) if l.strip()]
    explicit_lines = [r for r in explicit_lines if r is not None]
    rng = parse_time_range(cleaned) or (explicit_lines[0] if len(explicit_lines) == 1 else None)
    if rng:
        result["time_range"] = rng
        result["target_duration"] = rng[1] - rng[0]
        result["rule_type"] = "explicit_range"
        return result

    # "Ns đầu" pattern e.g. "6s đầu", "7s dau", "10 giây đầu"
    m_head = re.search(r"(\d+(?:\.\d+)?)\s*(?:s|giây)?\s*đầu", cleaned)
    if m_head:
        dur = float(m_head.group(1))
        if "tua nhanh" in cleaned and dur >= 20.0:
            dur = round(dur * 0.4, 2)
        result["target_duration"] = dur
        result["rule_type"] = "head_n_sec"
        return result

    # "N về sau" / "N tới hết" / "N - hết" pattern e.g. "4 về sau", "18 tới hết", "2 - hết"
    m_tail = re.search(r"(\d+(?:\.\d+)?)\s*(?:-\s*)?(?:về sau|tới hết|đến hết|hết)", cleaned)
    if m_tail:
        start_sec = float(m_tail.group(1))
        if raw_duration is not None and raw_duration > start_sec:
            result["target_duration"] = raw_duration - start_sec
        result["rule_type"] = "tail_from_n_sec"
        return result

    # If note is conversational or empty
    if any(w in cleaned for w in ["source đẹp", "ngắn thui", "lấy cmt", "full", "trẻ em"]):
        result["is_non_note"] = True
        result["rule_type"] = "raw_full"
        result["target_duration"] = raw_duration
        return result

    return result


def frame_coverage_percentage(intervals: Iterable[Tuple[int, int]], total_frames: int) -> float:
    """Compute percentage of frames [0, total_frames) covered by intervals."""
    if total_frames <= 0:
        return 0.0
    covered: Set[int] = set()
    for s_f, e_f in intervals:
        for f in range(max(0, s_f), min(total_frames, e_f)):
            covered.add(f)
    return (len(covered) / float(total_frames)) * 100.0


def intervals_overlap_seconds(
    intervals1: Iterable[Tuple[int, int]], intervals2: Iterable[Tuple[int, int]]
) -> float:
    """Compute total overlap in seconds between two sets of frame intervals."""
    set1: Set[int] = set()
    for s, e in intervals1:
        for f in range(s, e):
            set1.add(f)
    overlap_frames = 0
    for s, e in intervals2:
        for f in range(s, e):
            if f in set1:
                overlap_frames += 1
    return float(overlap_frames) / FPS
