import copy
import csv
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

TICKS_PER_SEC = 254016000000
TICKS_PER_FRAME = 10594584000  # 23.976 fps

PROJECT_TOOL_ROOT = Path(r"E:\Bonk funny moments\project tool")
SCRATCH_DIR = Path(r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\97bf33b9-d07b-48a7-907f-029c5d6e4a64\scratch")
PLAN_JSON = SCRATCH_DIR / "bonk_kb33_40_plan.json"

DONOR_SNAPSHOT = r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\2dfbcc6d-f671-49d0-93b6-6523695e0ca2\scratch\_v2_donor_snapshot.prproj"
DONOR_KB30 = r"E:\Bonk funny moments\project tool\kb30\kb30.prproj"

BRAND_LOGO_V3 = r"E:\Video Asset\Brand - Bonk\Đổi_nền_trắng_202609081721.png"
BRAND_MARK_V4 = r"E:\Video Asset\Brand - Bonk\đổi_thành_dạng_monochrome_mark_202609081722 (1).jpeg"
INTRO_8_MP4 = r"E:\Video Asset\Brand - Bonk\intro\8.mp4"
INTRO_RENDER_MP4 = r"E:\Video Asset\Brand - Bonk\intro\RENDER.mp4"
INTRO_STATIC_MP4 = r"E:\Video Asset\Brand - Bonk\TV Static Sound Effect - Bzz.mp4"
INTRO_MUSIC_MP3 = r"E:\Video Asset\Brand - Bonk\New folder\Capture It.mp3"

# Visually verified #1 Hook choice (0-based index into top12_per_ep[kb_id]) from AI Vision Contact Sheets:
# kb33: #5 (idx 4, c45, 7.5s, Lap:780, Panda costume jump-scare)
# kb34: #9 (idx 8, c39, 6.9s, Lap:196, Sc:92, Inflatable suit doorway fail)
# kb35: #11 (idx 10, c64, 4.7s, Lap:134, Sc:90, Outdoor dumpster fall)
# kb36: #2 (idx 1, c86, 7.8s, Lap:361, Sc:79, Backyard jump-scare reaction)
# kb37: #1 (idx 0, c7, 7.7s, Lap:246, Sc:96, Balcony glass/furniture crash)
# kb38: #1 (idx 0, c2, 6.3s, Lap:96, Sc:101, Patio water barrel fail)
# kb39: #5 (idx 4, c13, 4.2s, Lap:429, Sc:86, Gym exercise ball fail)
# kb40: #2 (idx 1, c5, 5.3s, Lap:363, Sc:84, Garden path slip & fall)
SELECTED_HOOK_IDX = {
    "kb33": 7,
    "kb34": 4,
    "kb35": 5,
    "kb36": 1,
    "kb37": 7,
    "kb38": 6,
    "kb39": 2,
    "kb40": 1,
}

# Exact Donor OIDs & UIDs in _v2_donor_snapshot.prproj
SNAP_MP4_MC_UID = "87f8c84c-e65c-472e-b0a4-84faac578bdb"
SNAP_MP4_MED_UID = "2ab64126-1e0d-4920-abd7-2c1076716057"
SNAP_V1_TI_OID = "2109"
SNAP_V2_TI_OID = "2235"
SNAP_A1_TI_OID = "2368"
SNAP_V3_MC_UID = "479e6e76-3ce0-4d59-8895-19313a76974e"
SNAP_V3_MED_UID = "d376c2e9-4a9f-4fa5-b567-2f9d7f95662e"
SNAP_V3_TI_OID = "2361"
SNAP_V4_MC_UID = "3e040b6a-9577-4993-ac70-a30db47e9c5f"
SNAP_V4_MED_UID = "90855b24-e19f-42d5-9063-1cc288a65ec1"
SNAP_V4_TI_OID = "2362"
SNAP_CPI_UID = "e04fb7ee-c39f-4b76-978d-6821dc74e89d"

SNAP_CROP_OID = "3906"     # AE.ADBE AECrop
SNAP_GEOM_OID = "3908"     # AE.ADBE Geometry2 (Scale=120., Rotation=3.)
SNAP_FLIP_OID = "3909"     # AE.ADBE Horizontal Flip

# Exact Donor OIDs & UIDs in kb30.prproj (sequence kb32 Intro)
KB30_HOOK_A1_DUCK_OID = "4966"  # A1 Part 2 of Hook with ducked Gain (0.5972222)
KB30_HOOK_MC_UID = "80f77172-f5b3-4235-b2ab-fac62845b4b6"
KB30_HOOK_MED_UID = "06262cc7-3d13-4fc7-bf4c-4e148a686e77"

KB30_8MP4_V_OID = "4967"
KB30_8MP4_A_OID = "4968"
KB30_8MP4_TAIL_TRANS_OID = "5511"
KB30_8MP4_MC_UID = "26325669-c845-4a95-a1b2-2da84656c236"
KB30_8MP4_MED_UID = "e243b9c9-a7ac-4438-acaf-38a59ab67648"

KB30_RENDER_V_OID = "4969"
KB30_RENDER_MC_UID = "3b50b1d8-250a-4d2a-bfc0-8c574a3c9b3b"
KB30_RENDER_MED_UID = "78fee803-089a-4fce-9c93-a756aaf54fca"

KB30_STATIC_A_OID = "4970"
KB30_STATIC_MC_UID = "c5abc936-53a0-4f2d-a74c-647ea0758637"
KB30_STATIC_MED_UID = "acd0a313-2491-4341-a019-7e109629646c"

KB30_MUSIC_A2_OID = "5731"
KB30_MUSIC_HEAD_TRANS_OID = "5732"
KB30_MUSIC_TAIL_TRANS_OID = "5733"
KB30_MUSIC_MC_UID = "2964dee0-454b-442b-ae60-bb5fab8fbfcf"
KB30_MUSIC_MED_UID = "24d6c5d8-62c9-4f1b-9e12-1d475c596994"


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


def _set_scalar_param(prm: ET.Element, val: float):
    s_int = f"{float(val):.2f}".rstrip("0").rstrip(".")
    skf_str = f"{float(val):.2f}".rstrip("0")
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


def set_trackitem_timing(ti_el, dst_by_id, start_ticks: int, end_ticks: int, in_ticks: int, out_ticks: int = None, preserve_speed: bool = False):
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
            if not preserve_speed:
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


def ensure_default_motion_and_opacity(chain_el: ET.Element):
    if chain_el.find("DefaultMotion") is None:
        dm = ET.Element("DefaultMotion")
        dm.text = "true"
        chain_el.insert(0, dm)
    else:
        chain_el.find("DefaultMotion").text = "true"
    if chain_el.find("DefaultOpacity") is None:
        do = ET.Element("DefaultOpacity")
        do.text = "true"
        chain_el.insert(1, do)
    else:
        chain_el.find("DefaultOpacity").text = "true"


def configure_v1_clean_duplicate(ti_el: ET.Element, dst_by_id: dict):
    """Track V1: Exact 1:1 duplicate of V2 with FX left completely empty (DefaultMotion=true, DefaultOpacity=true, 0 extra FX)."""
    comps_ref = ti_el.find(".//Components")
    chain_el = dst_by_id.get(comps_ref.attrib.get("ObjectRef", "")) if comps_ref is not None else None
    if chain_el is None:
        return
    ensure_default_motion_and_opacity(chain_el)
    comps_el = chain_el.find("./ComponentChain/Components")
    if comps_el is not None:
        comps_el.clear()
        comps_el.attrib["Version"] = "1"


def configure_v2_signature_fx(
    ti_el: ET.Element,
    dst_by_id: dict,
    dst_by_uid: dict,
    dst_root: ET.Element,
    next_oid_fn,
    snap_id: dict,
    snap_uid: dict,
    crop_lr_pct: float = 0.0,
):
    """Track V2: DefaultMotion=true, DefaultOpacity=true + Crop blurred sidebars (if crop_lr_pct > 0) + Transform (Scale=120, Rotate=3) + Horizontal Flip."""
    comps_ref = ti_el.find(".//Components")
    chain_el = dst_by_id.get(comps_ref.attrib.get("ObjectRef", "")) if comps_ref is not None else None
    if chain_el is None:
        return
    ensure_default_motion_and_opacity(chain_el)
    comps_el = chain_el.find("./ComponentChain/Components")
    if comps_el is None:
        return

    new_cids = []
    if crop_lr_pct > 0.5:
        crop_id, _, _ = clone_subgraph_into("id", SNAP_CROP_OID, snap_id, snap_uid, dst_root, next_oid_fn, dst_by_id, dst_by_uid)
        crop_ce = dst_by_id[crop_id]
        for pref in crop_ce.findall(".//Param"):
            pe = dst_by_id.get(pref.attrib.get("ObjectRef", ""))
            if pe is None:
                continue
            pnm = (pe.findtext("Name") or "").strip()
            if pnm in ("Left", "Right"):
                _set_scalar_param(pe, crop_lr_pct)
            elif pnm in ("Top", "Bottom", "Edge Feather", "Zoom"):
                _set_scalar_param(pe, 0.0)
        new_cids.append(crop_id)

    geom_id, _, _ = clone_subgraph_into("id", SNAP_GEOM_OID, snap_id, snap_uid, dst_root, next_oid_fn, dst_by_id, dst_by_uid)
    geom_ce = dst_by_id[geom_id]
    for pref in geom_ce.findall(".//Param"):
        pe = dst_by_id.get(pref.attrib.get("ObjectRef", ""))
        if pe is None:
            continue
        pnm = (pe.findtext("Name") or "").strip()
        if pnm in ("Scale", "Scale Height", "Scale Width"):
            _set_scalar_param(pe, 120.0)
        elif pnm == "Rotation":
            _set_scalar_param(pe, 3.0)
    new_cids.append(geom_id)

    flip_id, _, _ = clone_subgraph_into("id", SNAP_FLIP_OID, snap_id, snap_uid, dst_root, next_oid_fn, dst_by_id, dst_by_uid)
    new_cids.append(flip_id)

    comps_el.clear()
    comps_el.attrib["Version"] = "1"
    for idx, cid in enumerate(new_cids):
        ET.SubElement(comps_el, "Component", {"Index": str(idx), "ObjectRef": str(cid)})


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


def build_episode(kb_id: str, ep_scenes: list, hook_scene: dict, snap_data, kb30_data):
    t_ep = time.time()
    kb_num = re.sub(r"\D+", "", kb_id)
    pdir = PROJECT_TOOL_ROOT / kb_id
    src_dir = pdir / "source"
    old_scr_dir = pdir / f"Bonk-script-{kb_num}"
    src_dir.mkdir(parents=True, exist_ok=True)

    # 1. Remove old split Bonk-script-<N> folder and stray PNG overlays
    if old_scr_dir.exists():
        shutil.rmtree(old_scr_dir, ignore_errors=True)
    for png_fn in ("harmless_prank_note_overlay.png", "everyone_safe_disclaimer.png", "hes_fine_disclaimer.png"):
        png_p = pdir / png_fn
        if png_p.exists():
            try:
                png_p.unlink()
            except OSError:
                pass

    # 2. Consolidate 100% of episode clips into 1 unified folder `source/` with prefix `bonk` (bonk.kb33_1.mp4, ...)
    valid_mp4_paths = set()
    body_specs = []
    hook_body_spec = None

    sheet_rows_csv = [["", "nội dung", "link", "time", "check", "stt", "cre", "cmt"]]
    amz_footages = []

    def fmt_mmss(sec: float) -> str:
        m, s = divmod(int(round(sec)), 60)
        return f"{m}:{s:02d}"

    for idx, sc in enumerate(ep_scenes, start=1):
        fname = f"bonk.{kb_id}_{idx}.mp4"
        out_mp4 = src_dir / fname
        shutil.copy2(sc["shared_mp4"], out_mp4)
        abs_mp4 = str(out_mp4.resolve())
        valid_mp4_paths.add(os.path.normcase(abs_mp4))

        spec = {
            "idx": idx,
            "canh_id": sc["canh_id"],
            "name": fname,
            "path": abs_mp4,
            "dur_sec": float(sc["sl_dur"]),
            "file_dur": float(sc["file_dur"]),
            "crop_lr_pct": float(sc["final_crop_lr"]),
            "url": sc["url"],
            "chan": sc["chan"],
            "desc": sc["desc"],
            "raw_st": float(sc["raw_st"]),
        }
        body_specs.append(spec)
        if sc["canh_id"] == hook_scene["canh_id"]:
            hook_body_spec = spec

        t_str = f"{fmt_mmss(sc['raw_st'])} - {fmt_mmss(sc['raw_st'] + sc['sl_dur'])}"
        sheet_rows_csv.append(["", sc["desc"], sc["url"], t_str, "TRUE", str(idx), sc["chan"], ""])
        amz_footages.append({
            "sortOrder": idx,
            "note": "",
            "footage": {
                "id": sc["canh_id"],
                "title": sc["desc"],
                "channel": sc["chan"],
                "sourceUrl": sc["url"],
            },
        })

    assert hook_body_spec is not None, f"Hook scene {hook_scene['canh_id']} not found in {kb_id} body!"

    # Purge any obsolete .mp4 files in source/
    for fn in os.listdir(src_dir):
        if fn.lower().endswith(".mp4"):
            fp_full = os.path.normcase(os.path.abspath(str(src_dir / fn)))
            if fp_full not in valid_mp4_paths:
                try:
                    os.remove(fp_full)
                except OSError:
                    pass

    # Save updated CSV and JSON metadata
    with open(pdir / f"sheet_KB{kb_num}.csv", "w", encoding="utf-8", newline="") as fp:
        csv.writer(fp).writerows(sheet_rows_csv)
    with open(pdir / f"{kb_id}_s{kb_num}.json", "w", encoding="utf-8") as fp:
        json.dump({"data": {"footages": amz_footages}}, fp, indent=2, ensure_ascii=False)

    # 3. Compile .prproj from _v2_donor_snapshot.prproj + kb30.prproj
    snap_root_orig, snap_id_orig, snap_uid_orig = snap_data
    kb30_root, kb30_id, kb30_uid = kb30_data

    dst_root = copy.deepcopy(snap_root_orig)
    dst_by_id = {el.attrib["ObjectID"]: el for el in dst_root if "ObjectID" in el.attrib}
    dst_by_uid = {el.attrib["ObjectUID"]: el for el in dst_root if "ObjectUID" in el.attrib}

    bh_pool = {"1e94c302-dbb6-1add-07f5-a47d0000000e": "AfQ=\n\t\t"}
    for r_src in (dst_root, snap_root_orig, kb30_root):
        for e in r_src.iter():
            bh = e.attrib.get("BinaryHash")
            if bh and (e.text or "").strip():
                bh_pool[bh] = e.text

    max_oid = max(int(k) for k in dst_by_id.keys() if k.isdigit())
    curr_oid = [max_oid + 500]

    def next_oid():
        curr_oid[0] += 1
        return curr_oid[0]

    # Locate active Sequence & rename to kb_id
    seqs = [s for s in dst_root.iter("Sequence") if "ObjectUID" in s.attrib and s.find("TrackGroups") is not None]
    seq_el = max(seqs, key=lambda s: len(ET.tostring(s)))
    seq_uid = seq_el.attrib["ObjectUID"]
    if seq_el.find("Name") is not None:
        seq_el.find("Name").text = kb_id
    for links_el in seq_el.findall(".//Links"):
        links_el.clear()
        links_el.attrib["Version"] = "1"

    seq_cpi = dst_by_uid["f1ad8013-a24c-44e3-96f0-98b512cb4281"]
    if seq_cpi.find(".//Name") is not None:
        seq_cpi.find(".//Name").text = kb_id
    seq_mc = dst_by_uid["52d83bdb-f4f1-41c1-bcb6-bccdfe913276"]
    if seq_mc.find("Name") is not None:
        seq_mc.find("Name").text = kb_id

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
        if e.text and e.tag not in ("FilePath", "ActualMediaFilePath"):
            for old_str in (r"E:\Bonk funny moments\project\kb27", r"E:\Animal Whoops\aw1\aw1_3"):
                if old_str in e.text:
                    e.text = e.text.replace(old_str, str(pdir))

    # Set up ONLY 2 clean bins under RootProjectItem: `source` and `Brand - Bonk` (unified 1 folder!)
    bin_source = dst_by_uid["e1d01942-ab52-49d9-a169-742aec7aa3a5"]
    bin_brand = dst_by_uid["de9acb41-b4b0-4049-aa63-86898d35806f"]
    if bin_source.find(".//Name") is not None:
        bin_source.find(".//Name").text = "source"
    if bin_brand.find(".//Name") is not None:
        bin_brand.find(".//Name").text = "Brand - Bonk"

    root_pi = dst_by_uid[proj_el.find("RootProjectItem").attrib["ObjectURef"]]
    root_items = root_pi.find(".//Items")
    root_items.clear()
    root_items.attrib["Version"] = "1"
    for r_idx, uid_val in enumerate([
        seq_cpi.attrib["ObjectUID"],
        bin_source.attrib["ObjectUID"],
        bin_brand.attrib["ObjectUID"],
    ]):
        ET.SubElement(root_items, "Item", {"Index": str(r_idx), "ObjectURef": uid_val})

    bin_cpi_lists = {"source": [], "brand": []}
    media_registry = {}

    def sanitize_and_bin_media(new_mc_uid, id_m, uid_m, abs_p: str, bin_key: str, w: int = None, h: int = None, stream_ticks: int = None):
        base_nm = os.path.basename(abs_p)
        mc_el = dst_by_uid[new_mc_uid]
        if mc_el.find("Name") is not None:
            mc_el.find("Name").text = base_nm

        new_med_uid = None
        for old_u, new_u in uid_m.items():
            cand = dst_by_uid.get(new_u)
            if cand is not None and cand.tag == "Media":
                new_med_uid = new_u
                break
        assert new_med_uid is not None, f"Failed to locate Media for {abs_p}"
        med_el = dst_by_uid[new_med_uid]

        for pek_tag in ("PeakFilePath", "ConformedAudioPath"):
            for pek_el in list(med_el.findall(pek_tag)):
                med_el.remove(pek_el)

        for tag_nm in ("FilePath", "ActualMediaFilePath"):
            fp_el = med_el.find(tag_nm)
            if fp_el is not None:
                fp_el.text = abs_p
        for rp_el in med_el.findall("RelativePath"):
            try:
                rel_p = os.path.relpath(abs_p, str(pdir))
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

        if stream_ticks is not None:
            vs_ref = med_el.find("VideoStream")
            if vs_ref is not None and vs_ref.attrib.get("ObjectRef") in dst_by_id:
                vs_el = dst_by_id[vs_ref.attrib["ObjectRef"]]
                if w and h and vs_el.find("FrameRect") is not None:
                    vs_el.find("FrameRect").text = f"0,0,{w},{h}"
                if vs_el.find("Duration") is not None and stream_ticks < 5000000000000000:
                    vs_el.find("Duration").text = str(stream_ticks)
            as_ref = med_el.find("AudioStream")
            if as_ref is not None and as_ref.attrib.get("ObjectRef") in dst_by_id:
                as_el = dst_by_id[as_ref.attrib["ObjectRef"]]
                if as_el.find("Duration") is not None:
                    as_el.find("Duration").text = str(stream_ticks)

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

        new_cpi_uid, _, _ = clone_subgraph_into(
            "uid", SNAP_CPI_UID, snap_id_orig, snap_uid_orig, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={SNAP_MP4_MC_UID}, uid_overrides={SNAP_MP4_MC_UID: new_mc_uid},
        )
        cpi_el = dst_by_uid[new_cpi_uid]
        if cpi_el.find(".//Name") is not None:
            cpi_el.find(".//Name").text = base_nm
        bin_cpi_lists[bin_key].append(new_cpi_uid)
        return new_med_uid

    def register_episode_mp4(spec: dict):
        abs_p = spec["path"]
        norm_k = os.path.normcase(abs_p)
        if norm_k in media_registry:
            return media_registry[norm_k]
        dur_ticks = sec_to_frame_ticks(spec["dur_sec"])
        stream_ticks = max(int(round(spec["file_dur"] * TICKS_PER_SEC)), dur_ticks + TICKS_PER_FRAME * 2)
        new_mc_uid, id_m, uid_m = clone_subgraph_into(
            "uid", SNAP_MP4_MC_UID, snap_id_orig, snap_uid_orig, dst_root, next_oid, dst_by_id, dst_by_uid
        )
        new_med_uid = sanitize_and_bin_media(new_mc_uid, id_m, uid_m, abs_p, "source", 1920, 1080, stream_ticks)
        meta = {"w": 1920, "h": 1080, "dur_sec": spec["file_dur"], "stream_ticks": stream_ticks, "name": spec["name"], "path": abs_p}
        media_registry[norm_k] = (new_mc_uid, new_med_uid, meta)
        return new_mc_uid, new_med_uid, meta

    def register_kb30_brand_media(donor_mc_uid: str, abs_p: str):
        norm_k = os.path.normcase(abs_p)
        if norm_k in media_registry:
            return media_registry[norm_k]
        new_mc_uid, id_m, uid_m = clone_subgraph_into(
            "uid", donor_mc_uid, kb30_id, kb30_uid, dst_root, next_oid, dst_by_id, dst_by_uid
        )
        new_med_uid = sanitize_and_bin_media(new_mc_uid, id_m, uid_m, abs_p, "brand")
        meta = {"name": os.path.basename(abs_p), "path": abs_p}
        media_registry[norm_k] = (new_mc_uid, new_med_uid, meta)
        return new_mc_uid, new_med_uid, meta

    # Locate 5V / 4A tracks
    v_tracks, a_tracks = [], []
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

    v1_ids, v2_ids, v3_ids, v4_ids, v5_ids = [], [], [], [], []
    a1_ids, a2_ids, a3_ids, a4_ids = [], [], [], []
    a1_trans_ids, a2_trans_ids = [], []
    clip_timeline_records = []

    # =========================================================================
    # PHASE 1: DUPLICATED HOOK CLIP AT 0.00s (Split at T_hook - 3.10s for music fade-in)
    # =========================================================================
    hook_mc_uid, hook_med_uid, hook_meta = register_episode_mp4(hook_body_spec)
    t_hook_ticks = sec_to_frame_ticks(hook_body_spec["dur_sec"])
    duck_tail_ticks = 787449600000  # Exact 3.1000s from kb32 (74.325 frames -> let's snap to frame ticks: 74 * TICKS_PER_FRAME = 783999216000)
    duck_tail_ticks = sec_to_frame_ticks(3.10)
    if t_hook_ticks <= duck_tail_ticks + TICKS_PER_FRAME * 12:
        t_split_ticks = t_hook_ticks // 2
    else:
        t_split_ticks = t_hook_ticks - duck_tail_ticks

    # Hook Part 1 (0 .. t_split_ticks) & Hook Part 2 (t_split_ticks .. t_hook_ticks)
    for part_idx, (st_t, en_t, in_t, out_t) in enumerate([
        (0, t_split_ticks, 0, t_split_ticks),
        (t_split_ticks, t_hook_ticks, t_split_ticks, t_hook_ticks),
    ], start=1):
        # V1 (clean duplicate, 0 FX)
        v1_oid, _, _ = clone_subgraph_into(
            "id", SNAP_V1_TI_OID, snap_id_orig, snap_uid_orig, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={SNAP_MP4_MC_UID, SNAP_MP4_MED_UID},
            uid_overrides={SNAP_MP4_MC_UID: hook_mc_uid, SNAP_MP4_MED_UID: hook_med_uid},
        )
        v1_ti = dst_by_id[v1_oid]
        set_trackitem_timing(v1_ti, dst_by_id, st_t, en_t, in_t, out_t)
        configure_v1_clean_duplicate(v1_ti, dst_by_id)

        # V2 (Crop + Scale 120 Rotate 3 + Flip)
        v2_oid, _, _ = clone_subgraph_into(
            "id", SNAP_V2_TI_OID, snap_id_orig, snap_uid_orig, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={SNAP_MP4_MC_UID, SNAP_MP4_MED_UID},
            uid_overrides={SNAP_MP4_MC_UID: hook_mc_uid, SNAP_MP4_MED_UID: hook_med_uid},
        )
        v2_ti = dst_by_id[v2_oid]
        set_trackitem_timing(v2_ti, dst_by_id, st_t, en_t, in_t, out_t)
        configure_v2_signature_fx(
            v2_ti, dst_by_id, dst_by_uid, dst_root, next_oid, snap_id_orig, snap_uid_orig,
            crop_lr_pct=hook_body_spec["crop_lr_pct"],
        )

        for ti_curr in (v1_ti, v2_ti):
            sc_el = dst_by_id[ti_curr.find(".//SubClip").attrib["ObjectRef"]]
            if sc_el.find("Name") is not None:
                sc_el.find("Name").text = hook_body_spec["name"]
            vc_el = dst_by_id[sc_el.find(".//Clip").attrib["ObjectRef"]]
            src_el = dst_by_id[vc_el.find(".//Source").attrib["ObjectRef"]]
            for od in src_el.findall(".//OriginalDuration"):
                od.text = str(hook_meta["stream_ticks"])

        v1_ids.append(v1_oid)
        v2_ids.append(v2_oid)

        # A1: Part 1 normal audio, Part 2 ducked Gain (cloned from kb30 OID 4966)
        if part_idx == 1:
            a1_oid, _, _ = clone_subgraph_into(
                "id", SNAP_A1_TI_OID, snap_id_orig, snap_uid_orig, dst_root, next_oid, dst_by_id, dst_by_uid,
                stop_uids={SNAP_MP4_MC_UID, SNAP_MP4_MED_UID},
                uid_overrides={SNAP_MP4_MC_UID: hook_mc_uid, SNAP_MP4_MED_UID: hook_med_uid},
            )
        else:
            a1_oid, _, _ = clone_subgraph_into(
                "id", KB30_HOOK_A1_DUCK_OID, kb30_id, kb30_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
                stop_uids={KB30_HOOK_MC_UID, KB30_HOOK_MED_UID},
                uid_overrides={KB30_HOOK_MC_UID: hook_mc_uid, KB30_HOOK_MED_UID: hook_med_uid},
            )
        a1_ti = dst_by_id[a1_oid]
        set_trackitem_timing(a1_ti, dst_by_id, st_t, en_t, in_t, out_t)
        sc_a1 = dst_by_id[a1_ti.find(".//SubClip").attrib["ObjectRef"]]
        if sc_a1.find("Name") is not None:
            sc_a1.find("Name").text = hook_body_spec["name"]
        ac_el = dst_by_id[sc_a1.find(".//Clip").attrib["ObjectRef"]]
        src_a1 = dst_by_id[ac_el.find(".//Source").attrib["ObjectRef"]]
        for od in src_a1.findall(".//OriginalDuration"):
            od.text = str(hook_meta["stream_ticks"])
        a1_ids.append(a1_oid)

    clip_timeline_records.append({
        "index": 0,
        "id": "hook_00",
        "role": "hook_duplicate",
        "source_clip_idx": hook_body_spec["idx"],
        "name": hook_body_spec["name"],
        "path": hook_body_spec["path"],
        "start_sec": 0.0,
        "end_sec": round(t_hook_ticks / TICKS_PER_SEC, 3),
        "dur_sec": round(t_hook_ticks / TICKS_PER_SEC, 3),
    })

    # =========================================================================
    # PHASE 2: INTRO FROM kb32 (8.mp4 + Capture It.mp3 + RENDER.mp4 + TV Static)
    # =========================================================================
    dur_8mp4_ticks = 1083801600000   # Exact 4.2667s from kb32
    dur_static_ticks = 143942400000  # Exact 0.5667s from kb32
    t_8mp4_end = t_hook_ticks + dur_8mp4_ticks
    t_intro_end = t_8mp4_end + dur_static_ticks

    # 2A. 8.mp4 (t_hook_ticks .. t_8mp4_end) on V1, V2, and A1 (with Constant Power TailTransition 5511)
    mc_8, med_8, _ = register_kb30_brand_media(KB30_8MP4_MC_UID, INTRO_8_MP4)
    for target_v_list in (v1_ids, v2_ids):
        v8_oid, _, _ = clone_subgraph_into(
            "id", KB30_8MP4_V_OID, kb30_id, kb30_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={KB30_8MP4_MC_UID, KB30_8MP4_MED_UID},
            uid_overrides={KB30_8MP4_MC_UID: mc_8, KB30_8MP4_MED_UID: med_8},
        )
        set_trackitem_timing(dst_by_id[v8_oid], dst_by_id, t_hook_ticks, t_8mp4_end, 0, dur_8mp4_ticks, preserve_speed=True)
        target_v_list.append(v8_oid)

    a8_oid, _, _ = clone_subgraph_into(
        "id", KB30_8MP4_A_OID, kb30_id, kb30_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
        stop_uids={KB30_8MP4_MC_UID, KB30_8MP4_MED_UID},
        uid_overrides={KB30_8MP4_MC_UID: mc_8, KB30_8MP4_MED_UID: med_8},
    )
    a8_ti = dst_by_id[a8_oid]
    set_trackitem_timing(a8_ti, dst_by_id, t_hook_ticks, t_8mp4_end, 0, dur_8mp4_ticks, preserve_speed=True)

    # Clone Constant Power TailTransition (5511) for 8.mp4 on A1
    tr_5511_oid, _, _ = clone_subgraph_into("id", KB30_8MP4_TAIL_TRANS_OID, kb30_id, kb30_uid, dst_root, next_oid, dst_by_id, dst_by_uid)
    tr_5511_el = dst_by_id[tr_5511_oid]
    tr_5511_ti = tr_5511_el.find(".//TrackItem")
    tr_5511_ti.find("Start").text = str(t_8mp4_end - 127008000000)
    tr_5511_ti.find("End").text = str(t_8mp4_end)
    ET.SubElement(a8_ti.find("ClipTrackItem"), "TailTransition", {"ObjectRef": str(tr_5511_oid)})
    a1_ids.append(a8_oid)
    a1_trans_ids.append(tr_5511_oid)

    # 2B. RENDER.mp4 (t_8mp4_end .. t_intro_end, PlaybackSpeed=4) on V1 & V2 + TV Static Sound Effect - Bzz.mp4 on A1
    mc_ren, med_ren, _ = register_kb30_brand_media(KB30_RENDER_MC_UID, INTRO_RENDER_MP4)
    for target_v_list in (v1_ids, v2_ids):
        vren_oid, _, _ = clone_subgraph_into(
            "id", KB30_RENDER_V_OID, kb30_id, kb30_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={KB30_RENDER_MC_UID, KB30_RENDER_MED_UID},
            uid_overrides={KB30_RENDER_MC_UID: mc_ren, KB30_RENDER_MED_UID: med_ren},
        )
        set_trackitem_timing(
            dst_by_id[vren_oid], dst_by_id, t_8mp4_end, t_intro_end,
            1092268800000, 1668038400000, preserve_speed=True
        )
        target_v_list.append(vren_oid)

    mc_stat, med_stat, _ = register_kb30_brand_media(KB30_STATIC_MC_UID, INTRO_STATIC_MP4)
    astat_oid, _, _ = clone_subgraph_into(
        "id", KB30_STATIC_A_OID, kb30_id, kb30_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
        stop_uids={KB30_STATIC_MC_UID, KB30_STATIC_MED_UID},
        uid_overrides={KB30_STATIC_MC_UID: mc_stat, KB30_STATIC_MED_UID: med_stat},
    )
    set_trackitem_timing(
        dst_by_id[astat_oid], dst_by_id, t_8mp4_end, t_intro_end,
        465696000000, 609638400000, preserve_speed=True
    )
    a1_ids.append(astat_oid)

    # 2C. Capture It.mp3 on Track A2 (t_split_ticks .. t_8mp4_end, with HeadTransition 5732 & TailTransition 5733)
    mc_mus, med_mus, _ = register_kb30_brand_media(KB30_MUSIC_MC_UID, INTRO_MUSIC_MP3)
    amus_oid, _, _ = clone_subgraph_into(
        "id", KB30_MUSIC_A2_OID, kb30_id, kb30_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
        stop_uids={KB30_MUSIC_MC_UID, KB30_MUSIC_MED_UID},
        uid_overrides={KB30_MUSIC_MC_UID: mc_mus, KB30_MUSIC_MED_UID: med_mus},
    )
    amus_ti = dst_by_id[amus_oid]
    mus_dur_ticks = t_8mp4_end - t_split_ticks
    mus_in_ticks = 2734905600000
    mus_out_ticks = mus_in_ticks + mus_dur_ticks
    set_trackitem_timing(amus_ti, dst_by_id, t_split_ticks, t_8mp4_end, mus_in_ticks, mus_out_ticks, preserve_speed=True)

    tr_5732_oid, _, _ = clone_subgraph_into("id", KB30_MUSIC_HEAD_TRANS_OID, kb30_id, kb30_uid, dst_root, next_oid, dst_by_id, dst_by_uid)
    tr_5732_ti = dst_by_id[tr_5732_oid].find(".//TrackItem")
    tr_5732_ti.find("Start").text = str(t_split_ticks)
    tr_5732_ti.find("End").text = str(t_split_ticks + 406425600000)

    tr_5733_oid, _, _ = clone_subgraph_into("id", KB30_MUSIC_TAIL_TRANS_OID, kb30_id, kb30_uid, dst_root, next_oid, dst_by_id, dst_by_uid)
    tr_5733_ti = dst_by_id[tr_5733_oid].find(".//TrackItem")
    tr_5733_ti.find("Start").text = str(t_8mp4_end - 127008000000)
    tr_5733_ti.find("End").text = str(t_8mp4_end)

    amus_cti = amus_ti.find("ClipTrackItem")
    ET.SubElement(amus_cti, "HeadTransition", {"ObjectRef": str(tr_5732_oid)})
    ET.SubElement(amus_cti, "TailTransition", {"ObjectRef": str(tr_5733_oid)})
    a2_ids.append(amus_oid)
    a2_trans_ids.extend([tr_5732_oid, tr_5733_oid])

    # =========================================================================
    # PHASE 3: FULL-LENGTH MIXED BODY CLIPS (t_intro_end .. total_seq_ticks)
    # =========================================================================
    cur_ticks = t_intro_end
    for bspec in body_specs:
        mc_uid, med_uid, meta = register_episode_mp4(bspec)
        dur_ticks = max(TICKS_PER_FRAME * 12, sec_to_frame_ticks(bspec["dur_sec"]))
        in_ticks = 0
        out_ticks = dur_ticks
        start_ticks = cur_ticks
        end_ticks = start_ticks + dur_ticks
        cur_ticks = end_ticks

        # V1: 1:1 duplicate of V2 with empty FX
        v1_oid, _, _ = clone_subgraph_into(
            "id", SNAP_V1_TI_OID, snap_id_orig, snap_uid_orig, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={SNAP_MP4_MC_UID, SNAP_MP4_MED_UID},
            uid_overrides={SNAP_MP4_MC_UID: mc_uid, SNAP_MP4_MED_UID: med_uid},
        )
        v1_ti = dst_by_id[v1_oid]
        set_trackitem_timing(v1_ti, dst_by_id, start_ticks, end_ticks, in_ticks, out_ticks)
        configure_v1_clean_duplicate(v1_ti, dst_by_id)

        # V2: Crop (if blurred sidebars) + Transform(Scale=120, Rotate=3) + Flip
        v2_oid, _, _ = clone_subgraph_into(
            "id", SNAP_V2_TI_OID, snap_id_orig, snap_uid_orig, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={SNAP_MP4_MC_UID, SNAP_MP4_MED_UID},
            uid_overrides={SNAP_MP4_MC_UID: mc_uid, SNAP_MP4_MED_UID: med_uid},
        )
        v2_ti = dst_by_id[v2_oid]
        set_trackitem_timing(v2_ti, dst_by_id, start_ticks, end_ticks, in_ticks, out_ticks)
        configure_v2_signature_fx(
            v2_ti, dst_by_id, dst_by_uid, dst_root, next_oid, snap_id_orig, snap_uid_orig,
            crop_lr_pct=bspec["crop_lr_pct"],
        )

        for ti_curr in (v1_ti, v2_ti):
            sc_el = dst_by_id[ti_curr.find(".//SubClip").attrib["ObjectRef"]]
            if sc_el.find("Name") is not None:
                sc_el.find("Name").text = bspec["name"]
            vc_el = dst_by_id[sc_el.find(".//Clip").attrib["ObjectRef"]]
            src_el = dst_by_id[vc_el.find(".//Source").attrib["ObjectRef"]]
            for od in src_el.findall(".//OriginalDuration"):
                od.text = str(meta["stream_ticks"])

        v1_ids.append(v1_oid)
        v2_ids.append(v2_oid)

        # A1: 100% audible camera audio
        a1_oid, _, _ = clone_subgraph_into(
            "id", SNAP_A1_TI_OID, snap_id_orig, snap_uid_orig, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={SNAP_MP4_MC_UID, SNAP_MP4_MED_UID},
            uid_overrides={SNAP_MP4_MC_UID: mc_uid, SNAP_MP4_MED_UID: med_uid},
        )
        a1_ti = dst_by_id[a1_oid]
        set_trackitem_timing(a1_ti, dst_by_id, start_ticks, end_ticks, in_ticks, out_ticks)
        sc_a1 = dst_by_id[a1_ti.find(".//SubClip").attrib["ObjectRef"]]
        if sc_a1.find("Name") is not None:
            sc_a1.find("Name").text = bspec["name"]
        ac_el = dst_by_id[sc_a1.find(".//Clip").attrib["ObjectRef"]]
        src_a1 = dst_by_id[ac_el.find(".//Source").attrib["ObjectRef"]]
        for od in src_a1.findall(".//OriginalDuration"):
            od.text = str(meta["stream_ticks"])
        a1_ids.append(a1_oid)

        clip_timeline_records.append({
            "index": bspec["idx"],
            "id": f"clip_{bspec['idx']:03d}",
            "role": "body",
            "name": bspec["name"],
            "path": bspec["path"],
            "start_sec": round(start_ticks / TICKS_PER_SEC, 3),
            "end_sec": round(end_ticks / TICKS_PER_SEC, 3),
            "dur_sec": round(dur_ticks / TICKS_PER_SEC, 3),
            "crop_lr_pct": bspec["crop_lr_pct"],
        })

    total_seq_ticks = cur_ticks

    # =========================================================================
    # PHASE 4: V3 & V4 BRAND LOGOS (Hook 0..t_hook_ticks & Body t_intro_end..total_seq_ticks, paused during Intro)
    # =========================================================================
    v3_mc_u, v3_idm, v3_uidm = clone_subgraph_into(
        "uid", SNAP_V3_MC_UID, snap_id_orig, snap_uid_orig, dst_root, next_oid, dst_by_id, dst_by_uid
    )
    v3_med_u = sanitize_and_bin_media(v3_mc_u, v3_idm, v3_uidm, BRAND_LOGO_V3, "brand")

    v4_mc_u, v4_idm, v4_uidm = clone_subgraph_into(
        "uid", SNAP_V4_MC_UID, snap_id_orig, snap_uid_orig, dst_root, next_oid, dst_by_id, dst_by_uid
    )
    v4_med_u = sanitize_and_bin_media(v4_mc_u, v4_idm, v4_uidm, BRAND_MARK_V4, "brand")

    for span_st, span_en in [(0, t_hook_ticks), (t_intro_end, total_seq_ticks)]:
        span_dur = span_en - span_st
        v3_oid, _, _ = clone_subgraph_into(
            "id", SNAP_V3_TI_OID, snap_id_orig, snap_uid_orig, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={SNAP_V3_MC_UID, SNAP_V3_MED_UID},
            uid_overrides={SNAP_V3_MC_UID: v3_mc_u, SNAP_V3_MED_UID: v3_med_u},
        )
        set_trackitem_timing(dst_by_id[v3_oid], dst_by_id, span_st, span_en, 0, span_dur)
        v3_ids.append(v3_oid)

        v4_oid, _, _ = clone_subgraph_into(
            "id", SNAP_V4_TI_OID, snap_id_orig, snap_uid_orig, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={SNAP_V4_MC_UID, SNAP_V4_MED_UID},
            uid_overrides={SNAP_V4_MC_UID: v4_mc_u, SNAP_V4_MED_UID: v4_med_u},
        )
        set_trackitem_timing(dst_by_id[v4_oid], dst_by_id, span_st, span_en, 0, span_dur)
        v4_ids.append(v4_oid)

    # =========================================================================
    # PHASE 5: COMMIT ALL 5V / 4A TRACKS (V5=0, A3=0, A4=0)
    # =========================================================================
    def commit_track(track_el, item_oids, trans_oids=None):
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

        tr_wrap = track_el.find("./ClipTrack/TransitionItems")
        if tr_wrap is not None:
            for ch in list(tr_wrap):
                if ch.tag in ("TrackItems", "TransitionItems"):
                    tr_wrap.remove(ch)
            if trans_oids:
                tr_ti_cont = ET.SubElement(tr_wrap, "TrackItems", {"Version": "1"})
                for idx_t, t_oid in enumerate(trans_oids):
                    ET.SubElement(tr_ti_cont, "TrackItem", {"Index": str(idx_t), "ObjectRef": str(t_oid)})
            else:
                ET.SubElement(tr_wrap, "TransitionItems", {"Version": "1"})

    commit_track(v_tracks[0], v1_ids)
    commit_track(v_tracks[1], v2_ids)
    commit_track(v_tracks[2], v3_ids)
    commit_track(v_tracks[3], v4_ids)
    commit_track(v_tracks[4], [])  # Track V5 strictly empty (0 Emoji, 0 Note Overlay)

    commit_track(a_tracks[0], a1_ids, a1_trans_ids)
    commit_track(a_tracks[1], a2_ids, a2_trans_ids)  # Track A2 has Capture It.mp3 during Hook/Intro only
    commit_track(a_tracks[2], [])  # Track A3 strictly empty (0 SFX)
    commit_track(a_tracks[3], [])  # Track A4 strictly empty (0 SFX)

    # Populate the 2 bins (`source` and `Brand - Bonk`)
    for bin_el, cpi_uids in (
        (bin_source, bin_cpi_lists["source"]),
        (bin_brand, bin_cpi_lists["brand"]),
    ):
        items_el = bin_el.find(".//Items")
        items_el.clear()
        items_el.attrib["Version"] = "1"
        for b_idx, c_uid in enumerate(cpi_uids):
            ET.SubElement(items_el, "Item", {"Index": str(b_idx), "ObjectURef": c_uid})

    # Strip all PeakFilePath / ConformedAudioPath & BFS Canonicalize
    for par_el in dst_root.iter():
        for ch_el in list(par_el):
            if ch_el.tag in ("PeakFilePath", "ConformedAudioPath"):
                par_el.remove(ch_el)
    canonical_root = canonicalize_prproj(dst_root, bh_pool)

    out_prproj_path = str(pdir / f"{kb_id}.prproj")
    with gzip.GzipFile(out_prproj_path, "wb", mtime=0.0) as gz:
        gz.write(b'<?xml version="1.0" encoding="UTF-8" ?>\n')
        gz.write(ET.tostring(canonical_root, encoding="utf-8"))

    out_plan_path = str(pdir / f"{kb_id}_premiere_mcp_plan.json")
    mcp_plan = {
        "channel": "bonk_funny_moments",
        "project_id": kb_id,
        "sequence_name": kb_id,
        "resolution": "1920x1080",
        "fps": 23.976,
        "total_duration_sec": round(total_seq_ticks / TICKS_PER_SEC, 3),
        "hook": {
            "duplicated_from_clip_idx": hook_body_spec["idx"],
            "canh_id": hook_body_spec["canh_id"],
            "name": hook_body_spec["name"],
            "dur_sec": round(t_hook_ticks / TICKS_PER_SEC, 3),
            "split_duck_sec": round(t_split_ticks / TICKS_PER_SEC, 3),
        },
        "intro_kb32": {
            "start_sec": round(t_hook_ticks / TICKS_PER_SEC, 3),
            "end_sec": round(t_intro_end / TICKS_PER_SEC, 3),
            "dur_sec": round((t_intro_end - t_hook_ticks) / TICKS_PER_SEC, 3),
            "assets": [INTRO_8_MP4, INTRO_RENDER_MP4, INTRO_STATIC_MP4, INTRO_MUSIC_MP3],
        },
        "track_counts": {
            "V1_clean_duplicate": len(v1_ids),
            "V2_crop_scale120_rot3_flip": len(v2_ids),
            "V3_top_right_logo": len(v3_ids),
            "V4_bottom_watermark": len(v4_ids),
            "V5_empty": 0,
            "A1_camera_and_intro": len(a1_ids),
            "A2_intro_music": len(a2_ids),
            "A3_empty_sfx": 0,
            "A4_empty_sfx": 0,
        },
        "clips": clip_timeline_records,
    }
    with open(out_plan_path, "w", encoding="utf-8") as fp:
        json.dump(mcp_plan, fp, indent=2, ensure_ascii=False)

    print(
        f"[✓] {kb_id}.prproj built in {time.time()-t_ep:.1f}s | Total={total_seq_ticks/TICKS_PER_SEC:.2f}s ({total_seq_ticks/TICKS_PER_SEC/60:.2f}m) | "
        f"Hook=bonk.{kb_id}_{hook_body_spec['idx']}.mp4 ({t_hook_ticks/TICKS_PER_SEC:.2f}s) + kb32 Intro (4.83s) + {len(body_specs)} full-length clips | "
        f"V1={len(v1_ids)}, V2={len(v2_ids)}, V3={len(v3_ids)}, V4={len(v4_ids)}, V5=0, A1={len(a1_ids)}, A2={len(a2_ids)}, A3=0, A4=0",
        flush=True,
    )


def main():
    t0 = time.time()
    plan_data = json.loads(PLAN_JSON.read_text(encoding="utf-8"))
    episodes = plan_data["episodes"]
    top12_per_ep = plan_data["top12_per_ep"]

    print("Loading donor templates (_v2_donor_snapshot.prproj & kb30.prproj)...", flush=True)
    snap_data = load_xml(DONOR_SNAPSHOT)
    kb30_data = load_xml(DONOR_KB30)

    for kb_id in ["kb33", "kb34", "kb35", "kb36", "kb37", "kb38", "kb39", "kb40"]:
        hook_choice_idx = SELECTED_HOOK_IDX[kb_id]
        hook_scene = top12_per_ep[kb_id][hook_choice_idx]
        build_episode(kb_id, episodes[kb_id], hook_scene, snap_data, kb30_data)

    print(f"\nALL 8 BONK EPISODES (kb33..kb40) REBUILT IN {time.time()-t0:.1f}s!", flush=True)


if __name__ == "__main__":
    main()
