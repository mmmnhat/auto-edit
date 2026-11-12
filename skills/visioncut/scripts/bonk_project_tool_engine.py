import base64
import copy
import gzip
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")

TICKS_PER_SEC = 254016000000
TICKS_PER_FRAME = 10594584000  # 23.976 fps (254016000000 / 23.976023976)

FFMPEG = r"D:\AMZ\vendor\windows\bin\ffmpeg.exe" if os.path.exists(r"D:\AMZ\vendor\windows\bin\ffmpeg.exe") else "ffmpeg"
FFPROBE = r"D:\AMZ\vendor\windows\bin\ffprobe.exe" if os.path.exists(r"D:\AMZ\vendor\windows\bin\ffprobe.exe") else "ffprobe"

DONOR_KB27 = r"E:\Bonk funny moments\project\kb27\kb27.prproj"
DONOR_KB118 = r"E:\Bonk funny moments\project\kb36\kb36.prproj"
DONOR_KB116 = r"E:\ITV\Project\kb116\kb116.prproj"

BRAND_LOGO_V3 = r"E:\Video Asset\Brand - Bonk\Đổi_nền_trắng_202609081721.png"
BRAND_MARK_V4 = r"E:\Video Asset\Brand - Bonk\đổi_thành_dạng_monochrome_mark_202609081722 (1).jpeg"

INTERJECTION_DIR = r"E:\Video Asset\SFX\interjection"
BANNED_INTERJECTIONS = {
    f.lower() for f in os.listdir(INTERJECTION_DIR) if os.path.isfile(os.path.join(INTERJECTION_DIR, f))
} if os.path.isdir(INTERJECTION_DIR) else set()

_PROBE_CACHE = {}


def sec_to_frame_ticks(sec: float) -> int:
    frames = int(round(float(sec) * (TICKS_PER_SEC / TICKS_PER_FRAME)))
    return max(0, frames) * TICKS_PER_FRAME


def load_xml(prproj_path: str):
    raw = gzip.open(prproj_path, "rb").read()
    root = ET.fromstring(raw)
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


def clone_subgraph_into(
    start_kind,
    start_key,
    src_id,
    src_uid,
    dst_root,
    next_oid_fn,
    dst_by_id=None,
    dst_by_uid=None,
    stop_ids=None,
    stop_uids=None,
    uid_overrides=None,
):
    vis_ids, vis_uids = collect_subgraph(start_kind, start_key, src_id, src_uid, stop_ids, stop_uids)
    id_map = {old_id: str(next_oid_fn()) for old_id in vis_ids}
    uid_map = {old_uid: str(uuid.uuid4()) for old_uid in vis_uids}
    if uid_overrides:
        uid_map.update(uid_overrides)

    cloned_els = []
    for old_id in vis_ids:
        el = copy.deepcopy(src_id[old_id])
        el.attrib["ObjectID"] = id_map[old_id]
        cloned_els.append(el)
        if dst_by_id is not None:
            dst_by_id[id_map[old_id]] = el
    for old_uid in vis_uids:
        el = copy.deepcopy(src_uid[old_uid])
        el.attrib["ObjectUID"] = uid_map[old_uid]
        cloned_els.append(el)
        if dst_by_uid is not None:
            dst_by_uid[uid_map[old_uid]] = el

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


def ensure_silent_48k_stereo_if_no_audio(mp4_path: str):
    if not os.path.exists(mp4_path) or not mp4_path.lower().endswith(".mp4"):
        return
    try:
        res = subprocess.run(
            [FFPROBE, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate,channels", "-of", "json", mp4_path],
            capture_output=True, text=True, check=False,
        )
        streams = json.loads(res.stdout).get("streams", []) if (res.returncode == 0 and res.stdout) else []
        if streams and int(streams[0].get("sample_rate") or 0) == 48000 and int(streams[0].get("channels") or 0) == 2:
            return
        tmp_p = mp4_path + ".muxtmp.mp4"
        if not streams:
            cmd = [
                FFMPEG, "-y", "-v", "error", "-i", mp4_path,
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-shortest", tmp_p,
            ]
        else:
            cmd = [
                FFMPEG, "-y", "-v", "error", "-i", mp4_path,
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", tmp_p,
            ]
        r = subprocess.run(cmd, check=False)
        if r.returncode == 0 and os.path.exists(tmp_p) and os.path.getsize(tmp_p) > 5000:
            os.replace(tmp_p, mp4_path)
            _PROBE_CACHE.pop(os.path.normcase(os.path.abspath(mp4_path)), None)
        elif os.path.exists(tmp_p):
            os.remove(tmp_p)
    except Exception:
        pass


def probe_media(path: str) -> dict:
    k = os.path.normcase(os.path.abspath(path))
    if k in _PROBE_CACHE:
        return _PROBE_CACHE[k]
    meta = {"w": 1920, "h": 1080, "dur_sec": 10.0, "has_video": False, "has_audio": False}
    if os.path.exists(path):
        try:
            r = subprocess.run(
                [FFPROBE, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,duration", "-of", "json", path],
                capture_output=True, text=True, check=False,
            )
            if r.returncode == 0 and r.stdout:
                d = json.loads(r.stdout)
                fdur = float((d.get("format") or {}).get("duration") or 0.0)
                max_sdur = 0.0
                for s in d.get("streams", []):
                    sd = float(s.get("duration") or 0.0)
                    max_sdur = max(max_sdur, sd)
                    if s.get("codec_type") == "video":
                        meta["has_video"] = True
                        meta["w"] = int(s.get("width") or 1920)
                        meta["h"] = int(s.get("height") or 1080)
                    elif s.get("codec_type") == "audio":
                        meta["has_audio"] = True
                meta["dur_sec"] = max(fdur, max_sdur, 0.2)
        except Exception:
            pass
    _PROBE_CACHE[k] = meta
    return meta


def set_trackitem_timing(ti_el, dst_by_id, start_ticks: int, end_ticks: int, in_ticks: int, out_ticks: int = None):
    ti_inner = ti_el.find("./ClipTrackItem/TrackItem")
    if ti_inner is None:
        ti_inner = ti_el.find("TrackItem")
    if ti_inner is not None:
        st_el = ti_inner.find("Start")
        en_el = ti_inner.find("End")
        if start_ticks > 0:
            if st_el is None:
                st_el = ET.Element("Start")
                en_idx = list(ti_inner).index(en_el) if en_el is not None else 0
                ti_inner.insert(en_idx, st_el)
            st_el.text = str(int(start_ticks))
        else:
            if st_el is not None:
                ti_inner.remove(st_el)
        if en_el is None:
            en_el = ET.SubElement(ti_inner, "End")
        en_el.text = str(int(end_ticks))

    # Remove Disabled if present so item is active
    for dis_parent in (ti_el.find("ClipTrackItem"), ti_inner, ti_el):
        if dis_parent is not None:
            d_el = dis_parent.find("Disabled")
            if d_el is not None:
                dis_parent.remove(d_el)

    sc_ref = ti_el.find(".//SubClip")
    if sc_ref is not None and sc_ref.attrib.get("ObjectRef") in dst_by_id:
        sc_el = dst_by_id[sc_ref.attrib["ObjectRef"]]
        c_ref = sc_el.find(".//Clip")
        if c_ref is not None and c_ref.attrib.get("ObjectRef") in dst_by_id:
            c_el = dst_by_id[c_ref.attrib["ObjectRef"]]
            clip_inner = c_el.find("Clip") or c_el
            for tag_rm in ("PlaybackSpeed", "MaintainAudioPitch"):
                el_rm = clip_inner.find(tag_rm)
                if el_rm is not None:
                    clip_inner.remove(el_rm)
            for tag_rm in ("TimeInterpolationType", "AudioTimeScalerSettings"):
                el_rm = c_el.find(tag_rm)
                if el_rm is not None:
                    c_el.remove(el_rm)
            if c_el.tag == "VideoClip" and c_el.find("PosterFrame") is None:
                pf = ET.SubElement(c_el, "PosterFrame")
                pf.text = "0"
            ip_el = clip_inner.find("InPoint")
            op_el = clip_inner.find("OutPoint")
            eff_out = int(out_ticks) if out_ticks is not None else int(in_ticks + (end_ticks - start_ticks))
            if ip_el is None:
                ip_el = ET.SubElement(clip_inner, "InPoint")
            ip_el.text = str(int(in_ticks))
            if op_el is None:
                op_el = ET.SubElement(clip_inner, "OutPoint")
            op_el.text = str(eff_out)


def _set_scalar_param(prm: ET.Element, val: float):
    s_int = f"{float(val):.2f}".rstrip("0").rstrip(".")
    skf_val = f"{float(val):.2f}".rstrip("0")
    if skf_val.endswith("."):
        skf_str = skf_val
    else:
        skf_str = skf_val
    skf = prm.find("StartKeyframe")
    if skf is not None:
        skf.text = f"-91445760000000000,{skf_str},0,0,0,0,0,0"
    v_el = prm.find("Value")
    if v_el is not None:
        v_el.text = s_int
    cur = prm.find("CurrentValue")
    if cur is None:
        cur = ET.SubElement(prm, "CurrentValue")
    cur.text = s_int
    kfs_el = prm.find("Keyframes")
    if kfs_el is not None:
        kfs_el.text = None


def configure_v1_components(ti_el, dst_by_id, crop_lr_pct: float = 0.0, crop_tb_pct: float = 0.0, no_flip: bool = False):
    comps_ref = ti_el.find(".//Components")
    chain_el = dst_by_id.get(comps_ref.attrib.get("ObjectRef", "")) if comps_ref is not None else None
    if chain_el is None:
        return
    comps_el = chain_el.find("./ComponentChain/Components")
    if comps_el is None:
        return
    kept = []
    has_crop = (crop_lr_pct > 0.05 or crop_tb_pct > 0.05)
    for c_ref in list(comps_el):
        cid = c_ref.attrib["ObjectRef"]
        ce = dst_by_id.get(cid)
        if ce is None:
            continue
        mn = ce.findtext(".//MatchName") or ""
        if mn == "AE.ADBE Motion":
            for pref in ce.findall(".//Param"):
                pe = dst_by_id.get(pref.attrib.get("ObjectRef", ""))
                if pe is None:
                    continue
                pnm = pe.findtext("Name") or ""
                if pnm in ("Scale", "Scale Width"):
                    _set_scalar_param(pe, 400.0)
                elif pnm == "Position":
                    skf = pe.find("StartKeyframe")
                    if skf is not None:
                        skf.text = "-91445760000000000,0.5:0.5,0,0,0,0,0,0,5,4,0,0,0,0"
                    if pe.find("Keyframes") is not None:
                        pe.find("Keyframes").text = None
            kept.append(cid)
        elif mn == "AE.ADBE AECrop":
            if not has_crop:
                continue
            for pref in ce.findall(".//Param"):
                pe = dst_by_id.get(pref.attrib.get("ObjectRef", ""))
                if pe is None:
                    continue
                pnm = pe.findtext("Name") or ""
                if pnm in ("Left", "Right"):
                    _set_scalar_param(pe, crop_lr_pct)
                elif pnm in ("Top", "Bottom"):
                    _set_scalar_param(pe, crop_tb_pct)
            kept.append(cid)
        elif mn in ("AE.ADBE Geometry2", "AE.ADBE Geometry"):
            for pref in ce.findall(".//Param"):
                pe = dst_by_id.get(pref.attrib.get("ObjectRef", ""))
                if pe is None:
                    continue
                pnm = pe.findtext("Name") or ""
                if pnm in ("Scale", "Scale Height", "Scale Width"):
                    _set_scalar_param(pe, 100.0)
                elif pnm == "Rotation":
                    _set_scalar_param(pe, 0.0)
            kept.append(cid)
        elif mn == "AE.ADBE Horizontal Flip":
            if no_flip:
                continue
            kept.append(cid)
        else:
            # Keep AE.ADBE Lumetri (-2.0 exposure) & AE.Impact_Blur_FX (35 blur)
            kept.append(cid)

    comps_el.clear()
    comps_el.attrib["Version"] = "1"
    for idx, cid in enumerate(kept):
        ET.SubElement(comps_el, "Component", {"Index": str(idx), "ObjectRef": str(cid)})


def configure_v2_components(
    ti_el,
    dst_by_id,
    dst_by_uid,
    dst_root,
    next_oid,
    donor_motion_oid,
    kb27_id,
    kb27_uid,
    scale_pct: float = 100.0,
    pos_xy=(0.5, 0.5),
    crop_lr_pct: float = 0.0,
    crop_tb_pct: float = 0.0,
    no_flip: bool = False,
    is_vh: bool = False,
):
    comps_ref = ti_el.find(".//Components")
    chain_el = dst_by_id.get(comps_ref.attrib.get("ObjectRef", "")) if comps_ref is not None else None
    if chain_el is None:
        return
    dm = chain_el.find("DefaultMotion")
    if dm is not None:
        chain_el.remove(dm)
    comps_el = chain_el.find("./ComponentChain/Components")
    if comps_el is None:
        return

    eff_scale = max(120.0, float(scale_pct)) if is_vh else float(scale_pct)
    px, py = float(pos_xy[0]), float(pos_xy[1])

    # Clone intrinsic AE.ADBE Motion from kb27 donor_motion_oid ('22296') so Scale & Position are cleanly controlled
    mot_id, _, _ = clone_subgraph_into("id", donor_motion_oid, kb27_id, kb27_uid, dst_root, next_oid, dst_by_id, dst_by_uid)
    mot_ce = dst_by_id[mot_id]
    for pref in mot_ce.findall(".//Param"):
        pe = dst_by_id.get(pref.attrib.get("ObjectRef", ""))
        if pe is None:
            continue
        pnm = pe.findtext("Name") or ""
        if pnm in ("Scale", "Scale Width"):
            _set_scalar_param(pe, eff_scale)
        elif pnm == "Position":
            skf = pe.find("StartKeyframe")
            if skf is not None:
                skf.text = f"-91445760000000000,{px:.6f}:{py:.6f},0,0,0,0,0,0,5,4,0,0,0,0"
            if pe.find("Keyframes") is not None:
                pe.find("Keyframes").text = None

    kept = [mot_id]
    has_crop = (crop_lr_pct > 0.05 or crop_tb_pct > 0.05)
    added_crop = False

    for c_ref in list(comps_el):
        cid = c_ref.attrib["ObjectRef"]
        ce = dst_by_id.get(cid)
        if ce is None:
            continue
        mn = ce.findtext(".//MatchName") or ""
        if mn == "AE.ADBE Motion":
            continue
        elif mn == "AE.ADBE AECrop":
            if not has_crop or added_crop:
                continue
            for pref in ce.findall(".//Param"):
                pe = dst_by_id.get(pref.attrib.get("ObjectRef", ""))
                if pe is None:
                    continue
                pnm = pe.findtext("Name") or ""
                if pnm in ("Left", "Right"):
                    _set_scalar_param(pe, crop_lr_pct)
                elif pnm in ("Top", "Bottom"):
                    _set_scalar_param(pe, crop_tb_pct)
            kept.append(cid)
            added_crop = True
        elif mn in ("AE.ADBE Geometry2", "AE.ADBE Geometry"):
            for pref in ce.findall(".//Param"):
                pe = dst_by_id.get(pref.attrib.get("ObjectRef", ""))
                if pe is None:
                    continue
                pnm = pe.findtext("Name") or ""
                if pnm in ("Scale", "Scale Height", "Scale Width"):
                    _set_scalar_param(pe, 100.0)
                elif pnm == "Rotation":
                    _set_scalar_param(pe, 0.0)
            kept.append(cid)
        elif mn == "AE.ADBE Horizontal Flip":
            if no_flip:
                continue
            kept.append(cid)
        elif any(b in mn for b in ("Blur", "Impact_Blur")):
            # ViralHog Zero Blur Rule (and clean V2 base)
            continue
        else:
            # Keep AE.ADBE Lumetri Warmth/Pop + Sharpen ('7379')
            kept.append(cid)

    comps_el.clear()
    comps_el.attrib["Version"] = "1"
    for idx, cid in enumerate(kept):
        ET.SubElement(comps_el, "Component", {"Index": str(idx), "ObjectRef": str(cid)})


def set_emoji_keyframes(ti_el, dst_by_id, dur_ticks: int, scale_val: float, points: list):
    comps_ref = ti_el.find(".//Components")
    chain_el = dst_by_id.get(comps_ref.attrib.get("ObjectRef", "")) if comps_ref is not None else None
    if chain_el is None:
        return
    for cref in chain_el.iter("Component"):
        ce = dst_by_id.get(cref.attrib.get("ObjectRef", ""))
        if ce is not None and "AE.ADBE Motion" in (ce.findtext(".//MatchName") or ""):
            for pref in ce.findall(".//Param"):
                pe = dst_by_id.get(pref.attrib.get("ObjectRef", ""))
                if pe is None:
                    continue
                pnm = pe.findtext("Name") or ""
                if pnm in ("Scale", "Scale Width"):
                    _set_scalar_param(pe, scale_val)
                elif pnm == "Position":
                    x0, y0 = points[0]
                    iz = pe.find("IsTimeVarying")
                    if iz is None:
                        iz = ET.SubElement(pe, "IsTimeVarying")
                    iz.text = "true"
                    skf = pe.find("StartKeyframe")
                    if skf is None:
                        skf = ET.SubElement(pe, "StartKeyframe")
                    skf.text = f"-91445760000000000,{x0:.6f}:{y0:.6f},0,0,0,0,0,0,5,4,0,0,0,0"
                    kfs = pe.find("Keyframes")
                    if kfs is None:
                        kfs = ET.SubElement(pe, "Keyframes")
                    n_pts = len(points)
                    parts = []
                    for i, pt in enumerate(points):
                        if len(pt) == 3:
                            t_tick = int(round(float(pt[0]) * dur_ticks))
                            px, py = float(pt[1]), float(pt[2])
                        else:
                            t_tick = int(round(i * dur_ticks / max(1, n_pts - 1)))
                            px, py = float(pt[0]), float(pt[1])
                        parts.append(f"{t_tick},{px:.6f}:{py:.6f},0,0,0,0.16666666666666666,0,0.16666666666666666,5,4,0,0,0,0;")
                    kfs.text = "".join(parts)


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
        for attr in ("ID", "FrameRect", "NodeID", "ClipID", "ActionID"):
            if e.tag == attr and e.text:
                uval = e.text.strip()
                if len(uval) == 36 and uval.count("-") == 4 and uval != "00000000-0000-0000-0000-000000000000":
                    if uval in seen_uuids:
                        new_u = str(uuid.uuid4())
                        e.text = new_u
                        seen_uuids.add(new_u)
                    else:
                        seen_uuids.add(uval)
        if "UUID" in e.attrib:
            uval = e.attrib["UUID"]
            if uval != "00000000-0000-0000-0000-000000000000":
                if uval in seen_uuids:
                    new_u = str(uuid.uuid4())
                    e.attrib["UUID"] = new_u
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

    return new_root


def compile_bonk_project(kb_id: str, manifest: dict, out_prproj_path: str = None, out_plan_path: str = None):
    """
    Compile a complete 5-Video / 4-Audio Track Premiere Pro 2026 .prproj and *_premiere_mcp_plan.json
    satisfying 100% of Bonk Funny Moments E2E assertions (BONK-R1..R6) & 7-Point Hygiene.
    """
    kb_num = re.sub(r"\D+", "", kb_id)
    if out_prproj_path is None:
        proj_dir = rf"E:\Bonk funny moments\project tool\{kb_id}"
        out_prproj_path = os.path.join(proj_dir, f"{kb_id}.prproj")
    else:
        out_prproj_path = os.path.abspath(out_prproj_path)
        proj_dir = os.path.dirname(out_prproj_path)
    if out_plan_path is None:
        out_plan_path = os.path.join(proj_dir, f"{kb_id}_premiere_mcp_plan.json")

    dst_root, dst_by_id, dst_by_uid = load_xml(DONOR_KB27)
    donor27_root, donor27_id, donor27_uid = load_xml(DONOR_KB27)
    kb118_root, kb118_id, kb118_uid = load_xml(DONOR_KB118)

    bh_pool = {"1e94c302-dbb6-1add-07f5-a47d0000000e": "AfQ=\n\t\t"}
    for r_src in (dst_root, donor27_root, kb118_root):
        for e in r_src.iter():
            bh = e.attrib.get("BinaryHash")
            if bh and (e.text or "").strip():
                bh_pool[bh] = e.text

    max_oid = max(int(k) for k in dst_by_id.keys() if k.isdigit())
    curr_oid = [max_oid + 100]

    def next_oid():
        curr_oid[0] += 1
        return curr_oid[0]

    # Donor UIDs & OIDs in kb27 & kb118
    DONOR_MP4_MC_UID = "179d794f-bb3e-4b11-bdf7-c7401d72c6c0"
    DONOR_MP4_MED_UID = "0d02d8ce-208a-4676-9589-73d5fdd6919b"
    DONOR_V1_TI_OID = "6740"
    DONOR_V2_TI_OID = "5245"
    DONOR_A1_TI_OID = "5244"
    DONOR_MOTION_OID = "22296"

    DONOR_SFX_MC_UID = "e752ce5b-b918-4465-99c5-49d5bc16d726"
    DONOR_SFX_MED_UID = "6f37cf8e-b6bb-43a6-8691-7aecf9eb5be0"
    DONOR_SFX_TI_OID = "6930"

    DONOR_PNG_MC_UID = "d86f8007-e1ff-418a-95f0-0ee2310c2b43"
    DONOR_PNG_MED_UID = "482b79f1-b801-4b13-90c0-c5d78e0d8363"
    DONOR_PNG_TI_OID = "6835"

    DONOR_V3_MC_UID = "4ce87819-f990-44e3-a86d-46d65374d972"
    DONOR_V3_MED_UID = "8df53f2b-97a6-4f51-84a4-ea4cfe3520e9"
    DONOR_V3_TI_OID = "6831"

    DONOR_V4_MC_UID = "3d55bafb-92ee-4c97-9ad1-b144bde0f9d0"
    DONOR_V4_MED_UID = "6999eb30-2054-4616-bd78-8c59767e091d"
    DONOR_V4_TI_OID = "6833"

    DONOR_CPI_UID = "439a3f94-da67-4a0d-ba1d-93f7f8c6cfb0"

    KB118_GIF_TI_OID = "1723"
    KB118_GIF_MC_UID = "83e1b82d-3e44-4463-af17-88a2a9a3c108"
    KB118_GIF_MED_UID = "ca90bf14-6090-4072-a862-0850b0a54adf"

    # 1. Locate active Sequence in dst_root & rename to kb_id
    seqs = [s for s in dst_root.iter("Sequence") if "ObjectUID" in s.attrib and s.find("TrackGroups") is not None]
    seq_el = max(seqs, key=lambda s: len(ET.tostring(s)))
    seq_uid = seq_el.attrib["ObjectUID"]
    if seq_el.find("Name") is not None:
        seq_el.find("Name").text = kb_id
    # Clear stale kb27 Link pointers in PersistentGroupContainer so BFS garbage-collects 100% of donor kb27 items
    for links_el in seq_el.findall(".//Links"):
        links_el.clear()
        links_el.attrib["Version"] = "1"

    # Update Sequence MasterClip & ClipProjectItem in RootProjectItem, and clean bins
    seq_cpi = dst_by_uid["f1ad8013-a24c-44e3-96f0-98b512cb4281"]
    if seq_cpi.find(".//Name") is not None:
        seq_cpi.find(".//Name").text = kb_id
    seq_mc = dst_by_uid["52d83bdb-f4f1-41c1-bcb6-bccdfe913276"]
    if seq_mc.find("Name") is not None:
        seq_mc.find("Name").text = kb_id

    # Fix OpenSequenceGuidList & ScratchDisk paths on Project ObjectID=1
    proj_el = dst_by_id["1"]
    props_el = proj_el.find(".//Properties")
    if props_el is not None:
        for child in list(props_el):
            if child.tag.startswith("MZ.PrefixKey.OpenSequenceGuidList."):
                if child.tag == "MZ.PrefixKey.OpenSequenceGuidList.1":
                    child.text = seq_uid
                else:
                    props_el.remove(child)
    for e in dst_root.iter():
        if e.text and "E:\\Bonk funny moments\\project\\kb27" in e.text and e.tag not in ("FilePath", "ActualMediaFilePath"):
            e.text = e.text.replace("E:\\Bonk funny moments\\project\\kb27", proj_dir)

    # Set up the 4 clean Bins under RootProjectItem (removing unused 'SFX' bin!)
    bin_source = dst_by_uid["e1d01942-ab52-49d9-a169-742aec7aa3a5"]
    bin_script = dst_by_uid["ae6da1e9-cbe6-4d3c-9498-6b5704bc7203"]
    bin_sfx = dst_by_uid["80e8e320-e853-4056-bad9-44502a0480d6"]
    bin_brand = dst_by_uid["de9acb41-b4b0-4049-aa63-86898d35806f"]

    if bin_script.find(".//Name") is not None:
        bin_script.find(".//Name").text = f"Bonk-script-{kb_num}"

    root_pi = dst_by_uid[proj_el.find("RootProjectItem").attrib["ObjectURef"]]
    root_items = root_pi.find(".//Items")
    root_items.clear()
    root_items.attrib["Version"] = "1"
    for r_idx, uid_val in enumerate([
        seq_cpi.attrib["ObjectUID"],
        bin_source.attrib["ObjectUID"],
        bin_script.attrib["ObjectUID"],
        bin_sfx.attrib["ObjectUID"],
        bin_brand.attrib["ObjectUID"],
    ]):
        ET.SubElement(root_items, "Item", {"Index": str(r_idx), "ObjectURef": uid_val})

    bin_cpi_lists = {"source": [], "script": [], "sfx": [], "brand": []}
    media_registry = {}  # norm_path -> (mc_uid, med_uid, meta)

    def register_media(file_path: str, kind: str, min_ticks: int = 0, hint_meta: dict = None):
        abs_p = os.path.abspath(file_path)
        if not os.path.exists(abs_p):
            raise FileNotFoundError(f"[{kb_id}] Missing media file: {abs_p}")
        base_nm = os.path.basename(abs_p)
        if "\\interjection\\" in abs_p.lower() or base_nm.lower() in BANNED_INTERJECTIONS:
            raise ValueError(f"[{kb_id}] BANNED INTERJECTION SFX DETECTED: {abs_p}")

        norm_k = os.path.normcase(abs_p)
        if norm_k in media_registry:
            mc_u, med_u, meta = media_registry[norm_k]
            if min_ticks > meta["stream_ticks"]:
                meta["stream_ticks"] = min_ticks
                med_el = dst_by_uid[med_u]
                for st_tag in ("VideoStream", "AudioStream"):
                    sr = med_el.find(st_tag)
                    if sr is not None and sr.attrib.get("ObjectRef") in dst_by_id:
                        d_el = dst_by_id[sr.attrib["ObjectRef"]].find("Duration")
                        if d_el is not None:
                            d_el.text = str(min_ticks)
            return mc_u, med_u, meta

        if hint_meta is not None and "w" in hint_meta and "h" in hint_meta and "dur_sec" in hint_meta:
            pmeta = hint_meta
        else:
            if kind == "mp4":
                ensure_silent_48k_stereo_if_no_audio(abs_p)
            pmeta = probe_media(abs_p)
        if kind == "png":
            stream_ticks = max(10973491200000000, min_ticks + TICKS_PER_SEC)
        elif kind == "gif":
            stream_ticks = max(int(round(pmeta["dur_sec"] * TICKS_PER_SEC)), min_ticks + TICKS_PER_SEC, 30 * TICKS_PER_SEC)
        elif kind == "sfx":
            stream_ticks = max(int(round(pmeta["dur_sec"] * TICKS_PER_SEC)), TICKS_PER_FRAME * 2)
        else:
            stream_ticks = max(int(round(pmeta["dur_sec"] * TICKS_PER_SEC)), min_ticks + TICKS_PER_FRAME * 2)

        if kind == "mp4":
            src_id_m, src_uid_m, d_mc = donor27_id, donor27_uid, DONOR_MP4_MC_UID
            bin_key = "source" if "\\source\\" in abs_p.lower() else "script"
        elif kind == "sfx":
            src_id_m, src_uid_m, d_mc = donor27_id, donor27_uid, DONOR_SFX_MC_UID
            bin_key = "sfx"
        elif kind == "png":
            src_id_m, src_uid_m, d_mc = donor27_id, donor27_uid, DONOR_PNG_MC_UID
            bin_key = "brand"
        elif kind == "gif":
            src_id_m, src_uid_m, d_mc = kb118_id, kb118_uid, KB118_GIF_MC_UID
            bin_key = "brand"
        else:
            raise ValueError(f"Unknown media kind: {kind}")

        new_mc_uid, id_m, uid_m = clone_subgraph_into(
            "uid", d_mc, src_id_m, src_uid_m, dst_root, next_oid, dst_by_id, dst_by_uid
        )
        mc_el = dst_by_uid[new_mc_uid]
        if mc_el.find("Name") is not None:
            mc_el.find("Name").text = base_nm

        # Locate cloned Media in uid_m
        new_med_uid = None
        for old_u, new_u in uid_m.items():
            cand = dst_by_uid.get(new_u)
            if cand is not None and cand.tag == "Media":
                new_med_uid = new_u
                break
        assert new_med_uid is not None, f"Failed to locate Media for {abs_p}"
        med_el = dst_by_uid[new_med_uid]

        # 7-Point Hygiene: Strip .pek / ConformedAudioPath
        for pek_tag in ("PeakFilePath", "ConformedAudioPath"):
            for pek_el in list(med_el.findall(pek_tag)):
                med_el.remove(pek_el)

        for tag_nm in ("FilePath", "ActualMediaFilePath"):
            fp_el = med_el.find(tag_nm)
            if fp_el is not None:
                fp_el.text = abs_p
        for rp_el in med_el.findall("RelativePath"):
            try:
                rel_p = os.path.relpath(abs_p, proj_dir)
                if not rel_p.startswith("."):
                    rel_p = ".\\" + rel_p
                rp_el.text = rel_p
            except ValueError:
                rp_el.text = abs_p
        if med_el.find("Title") is not None:
            med_el.find("Title").text = base_nm
        if med_el.find("FileKey") is not None:
            med_el.find("FileKey").text = str(uuid.uuid4())
        if med_el.find("ImplementationID") is not None:
            med_el.find("ImplementationID").text = str(uuid.uuid4())

        # Sync VideoStream / AudioStream FrameRect & Duration
        vs_ref = med_el.find("VideoStream")
        if vs_ref is not None and vs_ref.attrib.get("ObjectRef") in dst_by_id:
            vs_el = dst_by_id[vs_ref.attrib["ObjectRef"]]
            if vs_el.find("FrameRect") is not None and kind in ("mp4", "gif", "png"):
                vs_el.find("FrameRect").text = f"0,0,{pmeta['w']},{pmeta['h']}"
            if vs_el.find("Duration") is not None and kind != "png":
                vs_el.find("Duration").text = str(stream_ticks)
        as_ref = med_el.find("AudioStream")
        if as_ref is not None and as_ref.attrib.get("ObjectRef") in dst_by_id:
            as_el = dst_by_id[as_ref.attrib["ObjectRef"]]
            if as_el.find("Duration") is not None:
                as_el.find("Duration").text = str(stream_ticks)

        # Sync MasterClip internal Clips OutPoint & OriginalDuration
        for old_i, new_i in id_m.items():
            ce = dst_by_id.get(new_i)
            if ce is None:
                continue
            for od in ce.findall(".//OriginalDuration"):
                od.text = str(stream_ticks)
            if ce.tag in ("VideoClip", "AudioClip"):
                op = ce.find(".//OutPoint")
                if op is not None:
                    op.text = str(stream_ticks)

        # Create 1 Binned ClipProjectItem (0 orphan MasterClips!)
        new_cpi_uid, _, _ = clone_subgraph_into(
            "uid", DONOR_CPI_UID, donor27_id, donor27_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={DONOR_MP4_MC_UID}, uid_overrides={DONOR_MP4_MC_UID: new_mc_uid},
        )
        cpi_el = dst_by_uid[new_cpi_uid]
        if cpi_el.find(".//Name") is not None:
            cpi_el.find(".//Name").text = base_nm
        bin_cpi_lists[bin_key].append(new_cpi_uid)

        meta = {
            "w": pmeta["w"],
            "h": pmeta["h"],
            "dur_sec": pmeta["dur_sec"],
            "stream_ticks": stream_ticks,
            "name": base_nm,
            "path": abs_p,
        }
        media_registry[norm_k] = (new_mc_uid, new_med_uid, meta)
        return new_mc_uid, new_med_uid, meta

    # 2. Locate the 5 Video Tracks and 4 Audio Tracks on seq_el
    v_tracks = []
    a_tracks = []
    for tg in seq_el.find("TrackGroups"):
        sec_ref = tg.find("Second")
        sec = dst_by_uid.get(sec_ref.attrib.get("ObjectURef", "")) or dst_by_id.get(sec_ref.attrib.get("ObjectRef", ""))
        if sec is None or sec.find("TrackGroup/Tracks") is None:
            continue
        if sec.tag == "VideoTrackGroup":
            for r in sec.find("TrackGroup/Tracks"):
                v_tracks.append(dst_by_uid.get(r.attrib.get("ObjectURef", "")) or dst_by_id.get(r.attrib.get("ObjectRef", "")))
        elif sec.tag == "AudioTrackGroup":
            for r in sec.find("TrackGroup/Tracks"):
                a_tracks.append(dst_by_uid.get(r.attrib.get("ObjectURef", "")) or dst_by_id.get(r.attrib.get("ObjectRef", "")))
    assert len(v_tracks) == 5 and len(a_tracks) == 4, f"Expected 5V/4A tracks, got {len(v_tracks)}V/{len(a_tracks)}A"

    v1_ids, v2_ids, v3_ids, v4_ids, v5_ids = [], [], [], [], []
    a1_ids, a2_ids, a3_ids, a4_ids = [], [], [], []

    # 3. Build V1, V2, A1 sequentially with ZERO black gaps!
    cur_ticks = 0
    clip_timeline_records = []  # for SFX/V5 clip-relative placement & MCP plan JSON

    for idx, cspec in enumerate(manifest["clips"]):
        cpath = cspec["path"]
        in_ticks = sec_to_frame_ticks(cspec.get("in_sec", 0.0))
        dur_ticks = max(TICKS_PER_FRAME * 12, sec_to_frame_ticks(cspec["dur_sec"]))
        speed_ratio = float(cspec.get("speed_ratio", 1.0))
        src_span_ticks = int(round(dur_ticks * speed_ratio / TICKS_PER_FRAME)) * TICKS_PER_FRAME
        out_ticks = in_ticks + src_span_ticks

        mc_uid, med_uid, meta = register_media(cpath, "mp4", min_ticks=out_ticks + TICKS_PER_FRAME * 2, hint_meta=cspec.get("hint_meta"))
        # Clamp in_ticks/out_ticks safely inside real stream duration if needed
        real_max_ticks = int(round(meta["dur_sec"] * TICKS_PER_SEC))
        if real_max_ticks > TICKS_PER_FRAME * 15 and out_ticks > real_max_ticks:
            overflow = out_ticks - real_max_ticks
            if in_ticks >= overflow:
                in_ticks -= overflow
                out_ticks = in_ticks + src_span_ticks
            else:
                in_ticks = 0
                src_span_ticks = max(TICKS_PER_FRAME * 12, (real_max_ticks // TICKS_PER_FRAME - 1) * TICKS_PER_FRAME)
                if abs(speed_ratio - 1.0) < 0.01:
                    dur_ticks = src_span_ticks
                out_ticks = src_span_ticks

        start_ticks = cur_ticks
        end_ticks = start_ticks + dur_ticks
        cur_ticks = end_ticks

        crop_lr = float(cspec.get("crop_lr_pct", 0.0))
        crop_tb = float(cspec.get("crop_tb_pct", 0.0))
        no_flip = bool(cspec.get("no_flip", False))
        is_vh = bool(cspec.get("is_vh", False))
        scale_pct = float(cspec.get("scale_pct", 120.0 if is_vh else 100.0))
        pos_xy = tuple(cspec.get("pos_xy", [0.5, 0.5]))
        mute_a1 = bool(cspec.get("mute_a1", False))
        display_name = cspec.get("name") or meta["name"]

        # Clone V1 item
        v1_oid, v1_idm, _ = clone_subgraph_into(
            "id", DONOR_V1_TI_OID, donor27_id, donor27_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={DONOR_MP4_MC_UID, DONOR_MP4_MED_UID},
            uid_overrides={DONOR_MP4_MC_UID: mc_uid, DONOR_MP4_MED_UID: med_uid},
        )
        v1_ti = dst_by_id[v1_oid]
        set_trackitem_timing(v1_ti, dst_by_id, start_ticks, end_ticks, in_ticks, out_ticks)
        configure_v1_components(v1_ti, dst_by_id, crop_lr_pct=crop_lr, crop_tb_pct=crop_tb, no_flip=no_flip)

        # Clone V2 item
        v2_oid, v2_idm, _ = clone_subgraph_into(
            "id", DONOR_V2_TI_OID, donor27_id, donor27_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={DONOR_MP4_MC_UID, DONOR_MP4_MED_UID},
            uid_overrides={DONOR_MP4_MC_UID: mc_uid, DONOR_MP4_MED_UID: med_uid},
        )
        v2_ti = dst_by_id[v2_oid]
        set_trackitem_timing(v2_ti, dst_by_id, start_ticks, end_ticks, in_ticks, out_ticks)
        configure_v2_components(
            v2_ti, dst_by_id, dst_by_uid, dst_root, next_oid, DONOR_MOTION_OID, donor27_id, donor27_uid,
            scale_pct=scale_pct, pos_xy=pos_xy, crop_lr_pct=crop_lr, crop_tb_pct=crop_tb,
            no_flip=no_flip, is_vh=is_vh,
        )

        # Sync SubClip Name, OriginalDuration, FrameRate speed, and ScaleToFramePolicy=1 on both V1 & V2
        for ti_curr in (v1_ti, v2_ti):
            sc_el = dst_by_id[ti_curr.find(".//SubClip").attrib["ObjectRef"]]
            if sc_el.find("Name") is not None:
                sc_el.find("Name").text = display_name
            vc_el = dst_by_id[sc_el.find("Clip").attrib["ObjectRef"]]
            pol_el = vc_el.find("ScaleToFramePolicy")
            if (meta["w"], meta["h"]) != (1920, 1080):
                if pol_el is None:
                    pol_el = ET.SubElement(vc_el, "ScaleToFramePolicy")
                pol_el.text = "1"
            elif pol_el is not None:
                vc_el.remove(pol_el)
            if abs(speed_ratio - 1.0) > 0.01:
                fr_el = vc_el.find(".//FrameRate")
                if fr_el is not None and (fr_el.text or "").isdigit():
                    fr_el.text = str(int(round(int(fr_el.text) / speed_ratio)))
            src_el = dst_by_id[vc_el.find(".//Source").attrib["ObjectRef"]]
            for od in src_el.findall(".//OriginalDuration"):
                od.text = str(meta["stream_ticks"])

        v1_ids.append(v1_oid)
        v2_ids.append(v2_oid)

        # Clone A1 item ONLY if audible (not silent Block 3 and not 'có nhạc'/'tắt tiếng')
        if not mute_a1:
            a1_oid, _, _ = clone_subgraph_into(
                "id", DONOR_A1_TI_OID, donor27_id, donor27_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
                stop_uids={DONOR_MP4_MC_UID, DONOR_MP4_MED_UID},
                uid_overrides={DONOR_MP4_MC_UID: mc_uid, DONOR_MP4_MED_UID: med_uid},
            )
            a1_ti = dst_by_id[a1_oid]
            set_trackitem_timing(a1_ti, dst_by_id, start_ticks, end_ticks, in_ticks, out_ticks)
            sc_a1 = dst_by_id[a1_ti.find(".//SubClip").attrib["ObjectRef"]]
            if sc_a1.find("Name") is not None:
                sc_a1.find("Name").text = display_name
            ac_el = dst_by_id[sc_a1.find("Clip").attrib["ObjectRef"]]
            src_a1 = dst_by_id[ac_el.find(".//Source").attrib["ObjectRef"]]
            for od in src_a1.findall(".//OriginalDuration"):
                od.text = str(meta["stream_ticks"])
            a1_ids.append(a1_oid)

        clip_timeline_records.append({
            "index": idx,
            "id": cspec.get("id", f"clip_{idx:03d}"),
            "name": display_name,
            "path": meta["path"],
            "start_ticks": start_ticks,
            "end_ticks": end_ticks,
            "start_sec": start_ticks / TICKS_PER_SEC,
            "end_sec": end_ticks / TICKS_PER_SEC,
            "in_sec": in_ticks / TICKS_PER_SEC,
            "out_sec": out_ticks / TICKS_PER_SEC,
            "dur_sec": dur_ticks / TICKS_PER_SEC,
            "mute_a1": mute_a1,
            "is_vh": is_vh,
            "no_flip": no_flip,
            "crop_lr_pct": crop_lr,
            "scale_pct": max(120.0, scale_pct) if is_vh else scale_pct,
        })

    total_seq_ticks = cur_ticks

    # 4. Build V3 & V4 Full-Span Brand Logos (100.0% coverage: 0 .. total_seq_ticks)
    v3_mc_u, v3_med_u, v3_meta = register_media(BRAND_LOGO_V3, "png", min_ticks=total_seq_ticks)
    v3_oid, _, _ = clone_subgraph_into(
        "id", DONOR_V3_TI_OID, donor27_id, donor27_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
        stop_uids={DONOR_V3_MC_UID, DONOR_V3_MED_UID},
        uid_overrides={DONOR_V3_MC_UID: v3_mc_u, DONOR_V3_MED_UID: v3_med_u},
    )
    set_trackitem_timing(dst_by_id[v3_oid], dst_by_id, 0, total_seq_ticks, 0, total_seq_ticks)
    v3_ids.append(v3_oid)

    v4_mc_u, v4_med_u, v4_meta = register_media(BRAND_MARK_V4, "png", min_ticks=total_seq_ticks)
    v4_oid, _, _ = clone_subgraph_into(
        "id", DONOR_V4_TI_OID, donor27_id, donor27_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
        stop_uids={DONOR_V4_MC_UID, DONOR_V4_MED_UID},
        uid_overrides={DONOR_V4_MC_UID: v4_mc_u, DONOR_V4_MED_UID: v4_med_u},
    )
    set_trackitem_timing(dst_by_id[v4_oid], dst_by_id, 0, total_seq_ticks, 0, total_seq_ticks)
    v4_ids.append(v4_oid)

    # Helper to resolve clip_index / clip_id / absolute start_sec
    rec_by_id = {r["id"]: r for r in clip_timeline_records}
    rec_by_name = {}
    for r in clip_timeline_records:
        rec_by_name.setdefault(r["name"], []).append(r)

    def resolve_clip_rec(spec: dict):
        if "clip_index" in spec and spec["clip_index"] is not None:
            ci = int(spec["clip_index"])
            if 0 <= ci < len(clip_timeline_records):
                return clip_timeline_records[ci]
        if "clip_id" in spec and spec["clip_id"] in rec_by_id:
            return rec_by_id[spec["clip_id"]]
        if "clip_name" in spec and spec["clip_name"] in rec_by_name:
            occ = int(spec.get("clip_occurrence", 0))
            lst = rec_by_name[spec["clip_name"]]
            return lst[min(occ, len(lst) - 1)]
        return None

    # 5. Build Track V5 Overlays (PNG note cards, safety disclaimers, & Keyframed Emoji GIFs)
    v5_occupied = []
    for gspec in manifest.get("v5_items", []):
        gpath = gspec["path"]
        gkind = "gif" if gpath.lower().endswith(".gif") else "png"
        crec = resolve_clip_rec(gspec)
        if crec is not None:
            off_ticks = sec_to_frame_ticks(gspec.get("offset_sec", 0.0))
            st_t = crec["start_ticks"] + off_ticks
            if "dur_sec" in gspec and gspec["dur_sec"] is not None:
                en_t = min(crec["end_ticks"], st_t + max(TICKS_PER_FRAME * 8, sec_to_frame_ticks(gspec["dur_sec"])))
            else:
                en_t = crec["end_ticks"]
        else:
            st_t = sec_to_frame_ticks(gspec["start_sec"])
            en_t = st_t + max(TICKS_PER_FRAME * 8, sec_to_frame_ticks(gspec["dur_sec"]))
        if en_t <= st_t:
            continue
        # Prevent overlap on V5
        for o_st, o_en in v5_occupied:
            if st_t < o_en and en_t > o_st:
                st_t = max(st_t, o_en)
        if en_t - st_t < TICKS_PER_FRAME * 4:
            continue
        v5_occupied.append((st_t, en_t))
        dur_t = en_t - st_t

        mc_u, med_u, gmeta = register_media(gpath, gkind, min_ticks=dur_t)
        if gkind == "png":
            g_oid, _, _ = clone_subgraph_into(
                "id", DONOR_PNG_TI_OID, donor27_id, donor27_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
                stop_uids={DONOR_PNG_MC_UID, DONOR_PNG_MED_UID},
                uid_overrides={DONOR_PNG_MC_UID: mc_u, DONOR_PNG_MED_UID: med_u},
            )
            g_ti = dst_by_id[g_oid]
            set_trackitem_timing(g_ti, dst_by_id, st_t, en_t, 0, dur_t)
        else:
            g_oid, _, _ = clone_subgraph_into(
                "id", KB118_GIF_TI_OID, kb118_id, kb118_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
                stop_uids={KB118_GIF_MC_UID, KB118_GIF_MED_UID},
                uid_overrides={KB118_GIF_MC_UID: mc_u, KB118_GIF_MED_UID: med_u},
            )
            g_ti = dst_by_id[g_oid]
            set_trackitem_timing(g_ti, dst_by_id, st_t, en_t, 0, dur_t)
            pts = gspec.get("keyframes")
            if not pts or len(pts) < 4:
                raise ValueError(f"[{kb_id}] GIF Emoji {gpath} MUST have >= 4 non-static keyframes!")
            set_emoji_keyframes(g_ti, dst_by_id, dur_t, float(gspec.get("scale_pct", 42.0)), pts)

        sc_g = dst_by_id[g_ti.find(".//SubClip").attrib["ObjectRef"]]
        if sc_g.find("Name") is not None:
            sc_g.find("Name").text = gmeta["name"]
        vc_g = dst_by_id[sc_g.find("Clip").attrib["ObjectRef"]]
        if vc_g.find("ScaleToFramePolicy") is not None:
            vc_g.remove(vc_g.find("ScaleToFramePolicy"))
        src_g = dst_by_id[vc_g.find(".//Source").attrib["ObjectRef"]]
        for od in src_g.findall(".//OriginalDuration"):
            od.text = str(gmeta["stream_ticks"])
        v5_ids.append(g_oid)

    # 6. Build Track A3 & Track A4 Peak-Aligned SFX (0 interjections, clamped OutPoint <= real_dur - 1f, non-overlapping per track)
    track_sfx_specs = {3: [], 4: []}
    for sspec in manifest.get("sfx_items", []):
        spath = sspec["path"]
        tr_num = int(sspec.get("track", 3))
        if tr_num not in (3, 4):
            tr_num = 3
        crec = resolve_clip_rec(sspec)
        mc_u, med_u, smeta = register_media(spath, "sfx")
        max_sfx_ticks = max(TICKS_PER_FRAME * 4, (int(round(smeta["dur_sec"] * TICKS_PER_SEC)) // TICKS_PER_FRAME - 1) * TICKS_PER_FRAME)
        req_dur_t = sec_to_frame_ticks(sspec["dur_sec"]) if "dur_sec" in sspec and sspec["dur_sec"] else max_sfx_ticks
        dur_t = min(req_dur_t, max_sfx_ticks)

        if crec is not None:
            if "impact_offset_sec" in sspec and sspec["impact_offset_sec"] is not None:
                peak_off = float(sspec.get("peak_offset_sec", 0.05))
                raw_st_sec = crec["start_sec"] + float(sspec["impact_offset_sec"]) - peak_off
                st_t = sec_to_frame_ticks(max(0.0, raw_st_sec))
            else:
                st_t = crec["start_ticks"] + sec_to_frame_ticks(sspec.get("offset_sec", 0.0))
        else:
            st_t = sec_to_frame_ticks(max(0.0, float(sspec["start_sec"])))

        st_t = min(st_t, max(0, total_seq_ticks - dur_t))
        en_t = min(total_seq_ticks, st_t + dur_t)
        dur_t = en_t - st_t
        if dur_t >= TICKS_PER_FRAME * 3:
            track_sfx_specs[tr_num].append((st_t, en_t, mc_u, med_u, smeta))

    for tr_num, target_list in ((3, a3_ids), (4, a4_ids)):
        items_sorted = sorted(track_sfx_specs[tr_num], key=lambda x: x[0])
        last_end = 0
        for st_t, en_t, mc_u, med_u, smeta in items_sorted:
            if st_t < last_end:
                # If minor overlap, trim or shift slightly; if collides heavily on A3, try A4 if free
                if last_end - st_t < TICKS_PER_FRAME * 8 and (en_t - last_end) >= TICKS_PER_FRAME * 6:
                    st_t = last_end
                else:
                    continue
            dur_t = en_t - st_t
            last_end = en_t
            s_oid, _, _ = clone_subgraph_into(
                "id", DONOR_SFX_TI_OID, donor27_id, donor27_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
                stop_uids={DONOR_SFX_MC_UID, DONOR_SFX_MED_UID},
                uid_overrides={DONOR_SFX_MC_UID: mc_u, DONOR_SFX_MED_UID: med_u},
            )
            s_ti = dst_by_id[s_oid]
            set_trackitem_timing(s_ti, dst_by_id, st_t, en_t, 0, dur_t)
            sc_s = dst_by_id[s_ti.find(".//SubClip").attrib["ObjectRef"]]
            if sc_s.find("Name") is not None:
                sc_s.find("Name").text = smeta["name"]
            ac_s = dst_by_id[sc_s.find("Clip").attrib["ObjectRef"]]
            src_s = dst_by_id[ac_s.find(".//Source").attrib["ObjectRef"]]
            for od in src_s.findall(".//OriginalDuration"):
                od.text = str(smeta["stream_ticks"])
            target_list.append(s_oid)

    # 7. Commit TrackItems & clear TransitionItems across all 5V / 4A tracks
    def commit_track(track_el, item_oids):
        cont = track_el.find("./ClipTrack/ClipItems/TrackItems")
        if cont is None:
            ci = track_el.find("./ClipTrack/ClipItems")
            if ci is None:
                ci = ET.SubElement(track_el.find("ClipTrack"), "ClipItems", {"Version": "3"})
            cont = ET.SubElement(ci, "TrackItems", {"Version": "1"})
        cont.clear()
        cont.attrib["Version"] = "1"
        for idx_i, oid_v in enumerate(item_oids):
            ET.SubElement(cont, "TrackItem", {"Index": str(idx_i), "ObjectRef": str(oid_v)})
        tr_cont = track_el.find("./ClipTrack/TransitionItems/TransitionItems")
        if tr_cont is not None:
            tr_cont.clear()

    commit_track(v_tracks[0], v1_ids)
    commit_track(v_tracks[1], v2_ids)
    commit_track(v_tracks[2], v3_ids)
    commit_track(v_tracks[3], v4_ids)
    commit_track(v_tracks[4], v5_ids)

    commit_track(a_tracks[0], a1_ids)
    commit_track(a_tracks[1], [])      # Track A2 strictly 100% empty (Zero-VO)
    commit_track(a_tracks[2], a3_ids)
    commit_track(a_tracks[3], a4_ids)

    # 8. Populate the 4 clean Bins with their exact active ClipProjectItems
    for bin_el, cpi_uids in (
        (bin_source, bin_cpi_lists["source"]),
        (bin_script, bin_cpi_lists["script"]),
        (bin_sfx, bin_cpi_lists["sfx"]),
        (bin_brand, bin_cpi_lists["brand"]),
    ):
        items_el = bin_el.find(".//Items")
        items_el.clear()
        items_el.attrib["Version"] = "1"
        for b_idx, c_uid in enumerate(cpi_uids):
            ET.SubElement(items_el, "Item", {"Index": str(b_idx), "ObjectURef": c_uid})

    # 9. Strip all PeakFilePath / ConformedAudioPath anywhere (including AudioStream) & BFS Canonicalize
    for par_el in dst_root.iter():
        for ch_el in list(par_el):
            if ch_el.tag in ("PeakFilePath", "ConformedAudioPath"):
                par_el.remove(ch_el)
    canonical_root = canonicalize_prproj(dst_root, bh_pool)

    os.makedirs(os.path.dirname(out_prproj_path), exist_ok=True)
    with gzip.GzipFile(out_prproj_path, "wb", mtime=0.0) as gz:
        gz.write(b'<?xml version="1.0" encoding="UTF-8" ?>\n')
        gz.write(ET.tostring(canonical_root, encoding="utf-8"))

    # 10. Save *_premiere_mcp_plan.json
    mcp_plan = {
        "channel": "bonk_funny_moments",
        "project_id": kb_id,
        "sequence_name": kb_id,
        "resolution": "1920x1080",
        "fps": 23.976,
        "total_duration_sec": round(total_seq_ticks / TICKS_PER_SEC, 3),
        "track_counts": {
            "V1_blur_bg": len(v1_ids),
            "V2_primary": len(v2_ids),
            "V3_top_right_logo": len(v3_ids),
            "V4_bottom_watermark": len(v4_ids),
            "V5_overlays_shields": len(v5_ids),
            "A1_camera_audio": len(a1_ids),
            "A2_zero_vo": 0,
            "A3_primary_foley_sfx": len(a3_ids),
            "A4_secondary_impact_sfx": len(a4_ids),
        },
        "clips": clip_timeline_records,
        "v5_items": manifest.get("v5_items", []),
        "sfx_items": manifest.get("sfx_items", []),
    }
    with open(out_plan_path, "w", encoding="utf-8") as fp:
        json.dump(mcp_plan, fp, indent=2, ensure_ascii=False)

    print(
        f"[✓] Compiled {kb_id}.prproj ({total_seq_ticks/TICKS_PER_SEC:.2f}s, {len(v2_ids)} clips, "
        f"V5={len(v5_ids)}, A1={len(a1_ids)}, A2=0, A3={len(a3_ids)}, A4={len(a4_ids)}, "
        f"UniqueMedia={len(media_registry)}) -> {out_prproj_path}",
        flush=True,
    )
    return mcp_plan
