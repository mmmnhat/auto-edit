import os
import re
import sys
import csv
import gzip
import json
import time
import uuid
import shutil
import subprocess
import numpy as np
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")

from step3_build_aw234_videos import bpe, base, generate_fcp_xml, SOURCE_URL_MAP
from execute_clean_dedup_all_16 import build_clean_catalog, interleave_selected_clips
from trace_exact_catalog_on_disk import old_bonk_path_to_cat_idx, aud_cache

TICKS_PER_SEC = 254016000000
TICKS_PER_FRAME = 10594584000  # 23.976 fps
INTRO_DUR_TICKS = 1525620096000  # 144 frames = 6.006s
INTRO_OUT_TICKS = 1678182105600  # 1525620096000 * 1.1

STAGE_DIR = r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\2dfbcc6d-f671-49d0-93b6-6523695e0ca2\scratch\_aw_clean_stage"
DONOR_1506_BACKUP = r"E:\Animal Whoops\aw1\aw1_1\aw1_1_user_1506_backup.prproj"
DONOR_1506_SAFE = r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\2dfbcc6d-f671-49d0-93b6-6523695e0ca2\scratch\_aw_1506_donor.prproj"
INTRO_ASSET_PATH = r"E:\Video Asset\Animal Whoops\intro.mp4"
INTRO_CONCAT_MP4 = r"C:\Users\AMZ-HUY\.gemini\antigravity\brain\2dfbcc6d-f671-49d0-93b6-6523695e0ca2\scratch\_intro_1080p24_6s.mp4"

# Donor IDs and UIDs in _aw_1506_donor.prproj
SEQ_CPI_UID = "f1ad8013-a24c-44e3-96f0-98b512cb4281"
SEQ_MC_UID = "52d83bdb-f4f1-41c1-bcb6-bccdfe913276"
BIN_SOURCE_UID = "e1d01942-ab52-49d9-a169-742aec7aa3a5"
BIN_SFX_UID = "80e8e320-e853-4056-bad9-44502a0480d6"
BIN_BRAND_UID = "de9acb41-b4b0-4049-aa63-86898d35806f"

# Fixed Channel Assets already inside _aw_1506_donor.prproj
INTRO_MC_UID = "84b6c73f-4371-413f-a0f1-b8c705559f88"
INTRO_MED_UID = "914aaa3e-a725-4050-a96b-d374e9058aff"
INTRO_CPI_UID = "e5650fd0-86b4-4214-85e8-b87c982ffd37"
INTRO_V3_TI_OID = "1839"
INTRO_A1_TI_OID = "1838"

ADJ_MC_UID = "e50cc5e8-bc8b-4521-be90-7e7adecefdc1"
ADJ_MED_UID = "55ae112d-fe85-45e0-aaea-9120c9e9c4ac"
ADJ_CPI_UID = "32bb6751-4dc0-4d0b-93a1-136510578a06"
ADJ_V2_TI_OID = "2251"
ADJ_BASE_IN = 895221158832000

LOGO_MC_UID = "3f7f93f2-dc20-42c3-a829-6a4054063d88"
LOGO_MED_UID = "fe0a1bd1-f31e-4ca8-8fb8-7f5a27678329"
LOGO_CPI_UID = "38fa7888-501c-466e-a08b-40cd2d50bd71"
LOGO_V4_TI_OID = "2361"

WTM_MC_UID = "f709908f-02bf-4b99-8aa5-9a9d39ea8def"
WTM_MED_UID = "8b267040-30fb-4544-85a1-882a639f9ced"
WTM_CPI_UID = "d2f0927c-093d-4470-bf0d-9cc090fdf2cb"
WTM_V5_TI_OID = "2363"
WTM_BASE_IN = 911907628632000

# Episode MP4 & SFX Donors in _aw_1506_donor.prproj
DONOR_MP4_MC_UID = "8079bce7-52ee-4d43-90d3-64acea5c42db"
DONOR_MP4_MED_UID = "f79974b9-4638-4d07-8f7a-d938ea289b15"
DONOR_CPI_UID = "31321442-c41b-4291-8bd1-b6754a738268"
DONOR_V1_TI_OID = "2141"
DONOR_V3_TI_OID = "2282"
DONOR_A1_TI_OID = "2365"

# V3 FX Component OIDs on TI 2282 in _aw_1506_donor.prproj
DONOR_CROP_OID = "5498"     # AE.ADBE AECrop
DONOR_LUMETRI_OID = "5499"  # AE.ADBE Lumetri (Temp=30, Tint=-2, Exposure=0.2, Contrast=10, Highlights=-10, Saturation=105)
DONOR_GEOM_OID = "5500"     # AE.ADBE Geometry2 (Scale=120, Rotation=3)
DONOR_FLIP_OID = "5501"     # AE.ADBE Horizontal Flip

DONOR_SFX_MC_UID = "e003fd40-2306-47ea-8676-9f959a75fb5c"
DONOR_SFX_MED_UID = "3d3ee341-a363-400d-902a-b92a4441e32b"
DONOR_SFX_CPI_UID = "f7c81f8f-e0d8-492d-83fb-14b60212c7d1"
DONOR_SFX_TI_OID = "2550"


def dhash_at_time(mp4_path: str, t_sec: float) -> int:
    cmd = [
        "ffmpeg", "-v", "error", "-ss", f"{t_sec:.3f}", "-i", mp4_path,
        "-frames:v", "1", "-vf", "crop=iw*0.40:ih*0.76:iw*0.30:ih*0.12,scale=9:8,format=gray",
        "-f", "rawvideo", "-"
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if len(p.stdout) < 72:
        return 0
    arr = np.frombuffer(p.stdout[:72], dtype=np.uint8).reshape(8, 9)
    diff = arr[:, 1:] > arr[:, :-1]
    val = 0
    for bit in diff.flatten():
        val = (val << 1) | int(bit)
    return val


def screen_15_and_select_3_hooks(ordered_clips: list[dict]) -> tuple[list[dict], list[dict]]:
    pool = []
    n = len(ordered_clips)
    for body_idx, c in enumerate(ordered_clips):
        if body_idx < 8 or body_idx >= n - 4:
            continue
        dur = float(c["dur"])
        if dur < 3.8 or dur > 12.5:
            continue
        lap = float(c["st"]["center_lap"])
        peak_db = float(c.get("peak_db", -10.0))
        rms_db = float(c.get("rms_db", -20.0))
        is_169 = 1.0 if float(c["v2_crop_pct"]) == 0.0 else 0.0
        score = lap * 1.5 + max(-20.0, peak_db) * 0.4 + max(-35.0, rms_db) * 0.3 + is_169 * 2.5
        cand = dict(c)
        cand["body_pos"] = body_idx + 1
        cand["hook_score"] = round(score, 3)
        pool.append(cand)

    screened_15 = sorted(pool, key=lambda x: -x["hook_score"])[:15]

    selected_3 = []
    used_vcodes = set()
    used_pos = []
    for cand in screened_15:
        if len(selected_3) >= 3:
            break
        if cand["vcode"] in used_vcodes:
            continue
        if any(abs(cand["body_pos"] - p) < 8 for p in used_pos):
            continue
        selected_3.append(cand)
        used_vcodes.add(cand["vcode"])
        used_pos.append(cand["body_pos"])

    for cand in screened_15:
        if len(selected_3) >= 3:
            break
        if cand not in selected_3:
            selected_3.append(cand)

    return screened_15, selected_3[:3]


def set_item_start_end_in_out_106(ti_el, dst_by_id, start_ticks: int, end_ticks: int, in_ticks: int, out_ticks: int, is_speed_106: bool = True):
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
            clip_inner = c_el.find("Clip")
            if clip_inner is None:
                clip_inner = c_el
            ip_el = clip_inner.find("InPoint")
            op_el = clip_inner.find("OutPoint")
            if ip_el is None:
                ip_el = ET.SubElement(clip_inner, "InPoint")
            ip_el.text = str(int(in_ticks))
            if op_el is None:
                op_el = ET.SubElement(clip_inner, "OutPoint")
            op_el.text = str(int(out_ticks))

            if is_speed_106:
                ps_el = clip_inner.find("PlaybackSpeed")
                if ps_el is None:
                    ps_el = ET.SubElement(clip_inner, "PlaybackSpeed")
                ps_el.text = "1.06"
                if c_el.tag == "VideoClip":
                    if c_el.find("PosterFrame") is None:
                        pf = ET.SubElement(c_el, "PosterFrame")
                        pf.text = "0"
                    ti_type = c_el.find("TimeInterpolationType")
                    if ti_type is None:
                        ti_type = ET.SubElement(c_el, "TimeInterpolationType")
                    ti_type.text = "2"
                elif c_el.tag == "AudioClip":
                    mp_el = clip_inner.find("MaintainAudioPitch")
                    if mp_el is None:
                        mp_el = ET.SubElement(clip_inner, "MaintainAudioPitch")
                    mp_el.text = "true"
                    g_el = c_el.find("Gain")
                    if g_el is not None:
                        c_el.remove(g_el)
                    props_el = clip_inner.find("./Node/Properties")
                    if props_el is not None:
                        for ch in list(props_el):
                            if ch.tag.startswith("ESP.LoudnessSection"):
                                props_el.remove(ch)


def compile_animal_whoops_episode(
    ep_id: str,
    hook_specs: list[dict],
    body_specs: list[dict],
    sfx_specs: list[dict],
    donor_root: ET.Element,
    donor_id: dict,
    donor_uid: dict,
    donor_bh: dict,
    out_prproj_path: str,
    out_plan_path: str,
):
    dst_root, dst_by_id, dst_by_uid = bpe.load_xml(DONOR_1506_SAFE)
    bh_pool = dict(donor_bh)
    for e in dst_root.iter():
        bh = e.attrib.get("BinaryHash")
        if bh and (e.text or "").strip():
            bh_pool[bh] = e.text

    proj_dir = os.path.dirname(os.path.abspath(out_prproj_path))
    max_oid = max(int(k) for k in dst_by_id.keys() if k.isdigit())
    curr_oid = [max_oid + 100]

    def next_oid():
        curr_oid[0] += 1
        return curr_oid[0]

    seqs = [s for s in dst_root.iter("Sequence") if "ObjectUID" in s.attrib and s.find("TrackGroups") is not None]
    seq_el = max(seqs, key=lambda s: len(ET.tostring(s)))
    seq_uid = seq_el.attrib["ObjectUID"]
    if seq_el.find("Name") is not None:
        seq_el.find("Name").text = ep_id
    for links_el in seq_el.findall(".//Links"):
        links_el.clear()
        links_el.attrib["Version"] = "1"

    seq_cpi = dst_by_uid[SEQ_CPI_UID]
    if seq_cpi.find(".//Name") is not None:
        seq_cpi.find(".//Name").text = ep_id
    seq_mc = dst_by_uid[SEQ_MC_UID]
    if seq_mc.find("Name") is not None:
        seq_mc.find("Name").text = ep_id

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
        if e.text and ("E:\\Animal Whoops\\aw1\\aw1_1" in e.text or "E:\\Bonk funny moments\\project\\kb27" in e.text) and e.tag not in ("FilePath", "ActualMediaFilePath"):
            e.text = e.text.replace("E:\\Animal Whoops\\aw1\\aw1_1", proj_dir).replace("E:\\Bonk funny moments\\project\\kb27", proj_dir)

    bin_source = dst_by_uid[BIN_SOURCE_UID]
    bin_sfx = dst_by_uid[BIN_SFX_UID]
    bin_brand = dst_by_uid[BIN_BRAND_UID]
    if bin_brand.find(".//Name") is not None:
        bin_brand.find(".//Name").text = "Animal Whoops_Asset"

    if LOGO_MC_UID in dst_by_uid and dst_by_uid[LOGO_MC_UID].find("Name") is not None:
        dst_by_uid[LOGO_MC_UID].find("Name").text = "Logo Animal Whoops.png"
    if LOGO_CPI_UID in dst_by_uid and dst_by_uid[LOGO_CPI_UID].find(".//Name") is not None:
        dst_by_uid[LOGO_CPI_UID].find(".//Name").text = "Logo Animal Whoops.png"

    root_pi = dst_by_uid[proj_el.find("RootProjectItem").attrib["ObjectURef"]]
    root_items = root_pi.find(".//Items")
    root_items.clear()
    root_items.attrib["Version"] = "1"
    for r_idx, uid_val in enumerate([SEQ_CPI_UID, BIN_SOURCE_UID, BIN_BRAND_UID, BIN_SFX_UID]):
        ET.SubElement(root_items, "Item", {"Index": str(r_idx), "ObjectURef": uid_val})

    bin_cpi_lists = {
        "source": [],
        "brand": [INTRO_CPI_UID, LOGO_CPI_UID, WTM_CPI_UID, ADJ_CPI_UID],
        "sfx": [],
    }
    media_registry = {}

    def register_media(file_path: str, kind: str, min_ticks: int = 0, hint_meta: dict = None):
        abs_p = os.path.abspath(file_path)
        base_nm = os.path.basename(abs_p)
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

        pmeta = hint_meta if (hint_meta and "w" in hint_meta) else bpe.probe_media(abs_p)
        if kind == "sfx":
            stream_ticks = max(int(round(pmeta["dur_sec"] * TICKS_PER_SEC)), TICKS_PER_FRAME * 2)
            d_mc, d_cpi, bin_key = DONOR_SFX_MC_UID, DONOR_SFX_CPI_UID, "sfx"
        else:
            stream_ticks = max(int(round(pmeta["dur_sec"] * TICKS_PER_SEC)), min_ticks + TICKS_PER_FRAME * 2)
            d_mc, d_cpi, bin_key = DONOR_MP4_MC_UID, DONOR_CPI_UID, "source"

        new_mc_uid, id_m, uid_m = bpe.clone_subgraph_into(
            "uid", d_mc, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid
        )
        mc_el = dst_by_uid[new_mc_uid]
        if mc_el.find("Name") is not None:
            mc_el.find("Name").text = base_nm

        new_med_uid = None
        for old_u, new_u in uid_m.items():
            cand = dst_by_uid.get(new_u)
            if cand is not None and cand.tag == "Media":
                new_med_uid = new_u
                break
        med_el = dst_by_uid[new_med_uid]

        for pek_tag in ("PeakFilePath", "ConformedAudioPath", "ModificationState", "ContentAndMetadataState"):
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

        vs_ref = med_el.find("VideoStream")
        if vs_ref is not None and vs_ref.attrib.get("ObjectRef") in dst_by_id:
            vs_el = dst_by_id[vs_ref.attrib["ObjectRef"]]
            if vs_el.find("FrameRect") is not None and kind == "mp4":
                vs_el.find("FrameRect").text = f"0,0,{pmeta['w']},{pmeta['h']}"
            if vs_el.find("Duration") is not None:
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

        new_cpi_uid, _, _ = bpe.clone_subgraph_into(
            "uid", d_cpi, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={d_mc}, uid_overrides={d_mc: new_mc_uid},
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

    v_tracks, a_tracks = [], []
    for tg in seq_el.find("TrackGroups"):
        sec_ref = tg.find("Second")
        u_ref = sec_ref.attrib.get("ObjectURef", "")
        i_ref = sec_ref.attrib.get("ObjectRef", "")
        sec = dst_by_uid[u_ref] if u_ref in dst_by_uid else dst_by_id.get(i_ref)
        if sec is None or sec.find("TrackGroup/Tracks") is None:
            continue
        if sec.tag == "VideoTrackGroup":
            for r in sec.find("TrackGroup/Tracks"):
                ru = r.attrib.get("ObjectURef", "")
                ri = r.attrib.get("ObjectRef", "")
                v_tracks.append(dst_by_uid[ru] if ru in dst_by_uid else dst_by_id.get(ri))
        elif sec.tag == "AudioTrackGroup":
            for r in sec.find("TrackGroup/Tracks"):
                ru = r.attrib.get("ObjectURef", "")
                ri = r.attrib.get("ObjectRef", "")
                a_tracks.append(dst_by_uid[ru] if ru in dst_by_uid else dst_by_id.get(ri))

    v1_ids, v2_ids, v3_ids, v4_ids, v5_ids = [], [], [], [], []
    a1_ids, a2_ids, a3_ids, a4_ids = [], [], [], []

    for bspec in body_specs:
        tl_frames = max(12, int(float(bspec["dur_sec"]) / 1.06 * (TICKS_PER_SEC / TICKS_PER_FRAME)))
        dur_t = tl_frames * TICKS_PER_FRAME
        out_t = dur_t * 106 // 100
        register_media(bspec["path"], "mp4", min_ticks=out_t + TICKS_PER_FRAME * 2, hint_meta=bspec.get("hint_meta"))

    def add_clip_on_v1_v3_a1(cspec: dict, cur_ticks: int, role: str, rec_idx: int):
        cpath = cspec["path"]
        in_sec = float(cspec.get("in_sec", 0.0))
        in_ticks = int(round(in_sec * (TICKS_PER_SEC / TICKS_PER_FRAME))) * TICKS_PER_FRAME
        raw_dur_sec = float(cspec["dur_sec"])
        tl_frames = max(12, int((raw_dur_sec / 1.06) * (TICKS_PER_SEC / TICKS_PER_FRAME)))
        dur_ticks = tl_frames * TICKS_PER_FRAME
        src_span_ticks = dur_ticks * 106 // 100
        out_ticks = in_ticks + src_span_ticks

        mc_uid, med_uid, meta = register_media(cpath, "mp4", min_ticks=out_ticks + TICKS_PER_FRAME * 2, hint_meta=cspec.get("hint_meta"))
        real_max_ticks = int(round(meta["dur_sec"] * TICKS_PER_SEC)) - TICKS_PER_FRAME
        if out_ticks > real_max_ticks:
            if in_ticks > 0 and in_ticks >= (out_ticks - real_max_ticks):
                in_ticks -= (out_ticks - real_max_ticks)
                out_ticks = in_ticks + src_span_ticks
            else:
                in_ticks = 0
                tl_frames = max(12, int((real_max_ticks * 100 // 106) // TICKS_PER_FRAME))
                dur_ticks = tl_frames * TICKS_PER_FRAME
                src_span_ticks = dur_ticks * 106 // 100
                out_ticks = src_span_ticks

        start_ticks = cur_ticks
        end_ticks = start_ticks + dur_ticks
        display_name = cspec.get("name") or meta["name"]
        v2_crop_pct = float(cspec.get("v2_crop_pct", 0.0))

        v1_oid, _, _ = bpe.clone_subgraph_into(
            "id", DONOR_V1_TI_OID, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={DONOR_MP4_MC_UID, DONOR_MP4_MED_UID},
            uid_overrides={DONOR_MP4_MC_UID: mc_uid, DONOR_MP4_MED_UID: med_uid},
        )
        v1_ti = dst_by_id[v1_oid]
        set_item_start_end_in_out_106(v1_ti, dst_by_id, start_ticks, end_ticks, in_ticks, out_ticks, is_speed_106=True)
        v1_chain = dst_by_id[v1_ti.find(".//Components").attrib["ObjectRef"]]
        if v1_chain.find("DefaultMotion") is None:
            dm_el = ET.Element("DefaultMotion")
            dm_el.text = "true"
            v1_chain.insert(0, dm_el)
        v1_comps = v1_chain.find("./ComponentChain/Components")
        v1_comps.clear()
        v1_comps.attrib["Version"] = "1"

        v3_oid, _, _ = bpe.clone_subgraph_into(
            "id", DONOR_V3_TI_OID, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={DONOR_MP4_MC_UID, DONOR_MP4_MED_UID},
            uid_overrides={DONOR_MP4_MC_UID: mc_uid, DONOR_MP4_MED_UID: med_uid},
        )
        v3_ti = dst_by_id[v3_oid]
        set_item_start_end_in_out_106(v3_ti, dst_by_id, start_ticks, end_ticks, in_ticks, out_ticks, is_speed_106=True)
        v3_chain = dst_by_id[v3_ti.find(".//Components").attrib["ObjectRef"]]
        if v3_chain.find("DefaultMotion") is None:
            dm_el = ET.Element("DefaultMotion")
            dm_el.text = "true"
            v3_chain.insert(0, dm_el)
        v3_comps = v3_chain.find("./ComponentChain/Components")
        v3_fx_oids = []
        if v2_crop_pct > 0.0:
            crop_oid, _, _ = bpe.clone_subgraph_into("id", DONOR_CROP_OID, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid)
            crop_ce = dst_by_id[crop_oid]
            for pref in crop_ce.findall(".//Param"):
                pe = dst_by_id.get(pref.attrib.get("ObjectRef", ""))
                if pe is None:
                    continue
                pnm = pe.findtext("Name") or ""
                if pnm in ("Left", "Right"):
                    bpe._set_scalar_param(pe, v2_crop_pct)
                elif pnm in ("Top", "Bottom"):
                    bpe._set_scalar_param(pe, 0.0)
            v3_fx_oids.append(crop_oid)

        lum_oid, _, _ = bpe.clone_subgraph_into("id", DONOR_LUMETRI_OID, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid)
        v3_fx_oids.append(lum_oid)

        geom_oid, _, _ = bpe.clone_subgraph_into("id", DONOR_GEOM_OID, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid)
        geom_ce = dst_by_id[geom_oid]
        for pref in geom_ce.findall(".//Param"):
            pe = dst_by_id.get(pref.attrib.get("ObjectRef", ""))
            if pe is None:
                continue
            pnm = pe.findtext("Name") or ""
            if pnm in ("Scale", "Scale Height"):
                bpe._set_scalar_param(pe, 120.0)
            elif pnm == "Rotation":
                bpe._set_scalar_param(pe, 3.0)
        v3_fx_oids.append(geom_oid)

        flip_oid, _, _ = bpe.clone_subgraph_into("id", DONOR_FLIP_OID, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid)
        v3_fx_oids.append(flip_oid)

        v3_comps.clear()
        v3_comps.attrib["Version"] = "1"
        for idx_c, cid in enumerate(v3_fx_oids):
            ET.SubElement(v3_comps, "Component", {"Index": str(idx_c), "ObjectRef": str(cid)})

        for ti_curr in (v1_ti, v3_ti):
            sc_el = dst_by_id[ti_curr.find(".//SubClip").attrib["ObjectRef"]]
            if sc_el.find("Name") is not None:
                sc_el.find("Name").text = display_name
            vc_el = dst_by_id[sc_el.find("Clip").attrib["ObjectRef"]]
            src_el = dst_by_id[vc_el.find(".//Source").attrib["ObjectRef"]]
            for od in src_el.findall(".//OriginalDuration"):
                od.text = str(meta["stream_ticks"])

        a1_oid, _, _ = bpe.clone_subgraph_into(
            "id", DONOR_A1_TI_OID, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={DONOR_MP4_MC_UID, DONOR_MP4_MED_UID},
            uid_overrides={DONOR_MP4_MC_UID: mc_uid, DONOR_MP4_MED_UID: med_uid},
        )
        a1_ti = dst_by_id[a1_oid]
        set_item_start_end_in_out_106(a1_ti, dst_by_id, start_ticks, end_ticks, in_ticks, out_ticks, is_speed_106=True)
        sc_a1 = dst_by_id[a1_ti.find(".//SubClip").attrib["ObjectRef"]]
        if sc_a1.find("Name") is not None:
            sc_a1.find("Name").text = display_name
        ac_el = dst_by_id[sc_a1.find("Clip").attrib["ObjectRef"]]
        src_a1 = dst_by_id[ac_el.find(".//Source").attrib["ObjectRef"]]
        for od in src_a1.findall(".//OriginalDuration"):
            od.text = str(meta["stream_ticks"])

        v1_ids.append(v1_oid)
        v3_ids.append(v3_oid)
        a1_ids.append(a1_oid)

        rec = {
            "index": rec_idx,
            "role": role,
            "id": cspec.get("id", f"{role}_{rec_idx:03d}"),
            "name": display_name,
            "path": meta["path"],
            "start_ticks": start_ticks,
            "end_ticks": end_ticks,
            "start_sec": round(start_ticks / TICKS_PER_SEC, 4),
            "end_sec": round(end_ticks / TICKS_PER_SEC, 4),
            "in_sec": round(in_ticks / TICKS_PER_SEC, 4),
            "out_sec": round(out_ticks / TICKS_PER_SEC, 4),
            "dur_sec": round(dur_ticks / TICKS_PER_SEC, 4),
            "speed_pct": 106.0,
            "time_interpolation": "Optical Flow (2)",
            "v2_crop_pct": v2_crop_pct,
            "scale_pct": 120.0,
            "rotation_deg": 3.0,
            "horizontal_flip": True,
            "mute_a1": False,
        }
        return end_ticks, rec

    def add_v2_v4_v5_span(span_start_ticks: int, span_end_ticks: int):
        span_dur = span_end_ticks - span_start_ticks
        adj_oid, _, _ = bpe.clone_subgraph_into(
            "id", ADJ_V2_TI_OID, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={ADJ_MC_UID, ADJ_MED_UID},
        )
        set_item_start_end_in_out_106(
            dst_by_id[adj_oid], dst_by_id, span_start_ticks, span_end_ticks, ADJ_BASE_IN, ADJ_BASE_IN + span_dur, is_speed_106=False
        )
        v2_ids.append(adj_oid)

        logo_oid, _, _ = bpe.clone_subgraph_into(
            "id", LOGO_V4_TI_OID, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={LOGO_MC_UID, LOGO_MED_UID},
        )
        logo_ti = dst_by_id[logo_oid]
        set_item_start_end_in_out_106(logo_ti, dst_by_id, span_start_ticks, span_end_ticks, 0, span_dur, is_speed_106=False)
        sc_logo = dst_by_id[logo_ti.find(".//SubClip").attrib["ObjectRef"]]
        if sc_logo.find("Name") is not None:
            sc_logo.find("Name").text = "Logo Animal Whoops.png"
        v4_chain = dst_by_id[logo_ti.find(".//Components").attrib["ObjectRef"]]
        for cref in v4_chain.findall(".//Component"):
            ce = dst_by_id.get(cref.attrib["ObjectRef"])
            if ce is not None and (ce.findtext("MatchName") or "") == "AE.ADBE Motion":
                for pref in ce.findall(".//Param"):
                    pe = dst_by_id.get(pref.attrib["ObjectRef"])
                    if pe is not None and (pe.findtext("Name") or "") in ("Scale", "Scale Width"):
                        bpe._set_scalar_param(pe, 12.0)
        v4_ids.append(logo_oid)

        wtm_oid, _, _ = bpe.clone_subgraph_into(
            "id", WTM_V5_TI_OID, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
            stop_uids={WTM_MC_UID, WTM_MED_UID},
        )
        set_item_start_end_in_out_106(
            dst_by_id[wtm_oid], dst_by_id, span_start_ticks, span_end_ticks, WTM_BASE_IN, WTM_BASE_IN + span_dur, is_speed_106=False
        )
        v5_ids.append(wtm_oid)

    cur_ticks = 0
    timeline_records = []

    for hspec in hook_specs:
        cur_ticks, rec = add_clip_on_v1_v3_a1(hspec, cur_ticks, "hook", len(timeline_records))
        timeline_records.append(rec)
    hook_end_ticks = cur_ticks
    add_v2_v4_v5_span(0, hook_end_ticks)

    intro_start_ticks = hook_end_ticks
    intro_end_ticks = intro_start_ticks + INTRO_DUR_TICKS

    intro_v3_oid, _, _ = bpe.clone_subgraph_into(
        "id", INTRO_V3_TI_OID, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
        stop_uids={INTRO_MC_UID, INTRO_MED_UID},
    )
    set_item_start_end_in_out_106(
        dst_by_id[intro_v3_oid], dst_by_id, intro_start_ticks, intro_end_ticks, 0, INTRO_OUT_TICKS, is_speed_106=False
    )
    v3_ids.append(intro_v3_oid)

    intro_a1_oid, _, _ = bpe.clone_subgraph_into(
        "id", INTRO_A1_TI_OID, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
        stop_uids={INTRO_MC_UID, INTRO_MED_UID},
    )
    set_item_start_end_in_out_106(
        dst_by_id[intro_a1_oid], dst_by_id, intro_start_ticks, intro_end_ticks, 0, INTRO_OUT_TICKS, is_speed_106=False
    )
    a1_ids.append(intro_a1_oid)

    timeline_records.append({
        "index": len(timeline_records),
        "role": "intro",
        "id": "intro",
        "name": "intro.mp4",
        "path": INTRO_ASSET_PATH,
        "start_ticks": intro_start_ticks,
        "end_ticks": intro_end_ticks,
        "start_sec": round(intro_start_ticks / TICKS_PER_SEC, 4),
        "end_sec": round(intro_end_ticks / TICKS_PER_SEC, 4),
        "in_sec": 0.0,
        "out_sec": round(INTRO_OUT_TICKS / TICKS_PER_SEC, 4),
        "dur_sec": round(INTRO_DUR_TICKS / TICKS_PER_SEC, 4),
        "speed_pct": 110.0,
        "v2_crop_pct": 0.0,
        "scale_pct": 50.0,
        "rotation_deg": 0.0,
        "horizontal_flip": False,
        "mute_a1": False,
    })

    cur_ticks = intro_end_ticks
    for bspec in body_specs:
        cur_ticks, rec = add_clip_on_v1_v3_a1(bspec, cur_ticks, "body", len(timeline_records))
        timeline_records.append(rec)
    total_seq_ticks = cur_ticks
    add_v2_v4_v5_span(intro_end_ticks, total_seq_ticks)

    rec_by_id = {r["id"]: r for r in timeline_records}
    track_sfx = {2: [], 3: []}
    for sspec in sfx_specs:
        spath = sspec["path"]
        tr_num = 2 if int(sspec.get("track", 2)) == 2 else 3
        crec = rec_by_id.get(sspec["clip_id"])
        if crec is None:
            continue
        mc_u, med_u, smeta = register_media(spath, "sfx")
        max_sfx_t = max(TICKS_PER_FRAME * 4, (int(round(smeta["dur_sec"] * TICKS_PER_SEC)) // TICKS_PER_FRAME - 1) * TICKS_PER_FRAME)
        peak_off = float(sspec.get("peak_offset_sec", 0.05))
        raw_st_sec = crec["start_sec"] + float(sspec["impact_offset_sec"]) - peak_off
        st_t = bpe.sec_to_frame_ticks(max(0.0, raw_st_sec))
        st_t = min(st_t, max(0, total_seq_ticks - max_sfx_t))
        en_t = min(total_seq_ticks, st_t + max_sfx_t)
        if en_t - st_t >= TICKS_PER_FRAME * 3:
            track_sfx[tr_num].append((st_t, en_t, mc_u, med_u, smeta))

    for tr_num, target_list in ((2, a2_ids), (3, a3_ids)):
        last_end = 0
        for st_t, en_t, mc_u, med_u, smeta in sorted(track_sfx[tr_num], key=lambda x: x[0]):
            if st_t < last_end:
                continue
            dur_t = en_t - st_t
            last_end = en_t
            s_oid, _, _ = bpe.clone_subgraph_into(
                "id", DONOR_SFX_TI_OID, donor_id, donor_uid, dst_root, next_oid, dst_by_id, dst_by_uid,
                stop_uids={DONOR_SFX_MC_UID, DONOR_SFX_MED_UID},
                uid_overrides={DONOR_SFX_MC_UID: mc_u, DONOR_SFX_MED_UID: med_u},
            )
            s_ti = dst_by_id[s_oid]
            set_item_start_end_in_out_106(s_ti, dst_by_id, st_t, en_t, 0, dur_t, is_speed_106=False)
            sc_s = dst_by_id[s_ti.find(".//SubClip").attrib["ObjectRef"]]
            if sc_s.find("Name") is not None:
                sc_s.find("Name").text = smeta["name"]
            ac_s = dst_by_id[sc_s.find("Clip").attrib["ObjectRef"]]
            src_s = dst_by_id[ac_s.find(".//Source").attrib["ObjectRef"]]
            for od in src_s.findall(".//OriginalDuration"):
                od.text = str(smeta["stream_ticks"])
            target_list.append(s_oid)

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
    commit_track(a_tracks[1], a2_ids)
    commit_track(a_tracks[2], a3_ids)
    commit_track(a_tracks[3], a4_ids)

    for bin_el, cpi_uids in (
        (bin_source, bin_cpi_lists["source"]),
        (bin_brand, bin_cpi_lists["brand"]),
        (bin_sfx, bin_cpi_lists["sfx"]),
    ):
        items_el = bin_el.find(".//Items")
        items_el.clear()
        items_el.attrib["Version"] = "1"
        for b_idx, c_uid in enumerate(cpi_uids):
            ET.SubElement(items_el, "Item", {"Index": str(b_idx), "ObjectURef": c_uid})

    for par_el in dst_root.iter():
        for ch_el in list(par_el):
            if ch_el.tag in ("PeakFilePath", "ConformedAudioPath", "ModificationState", "ContentAndMetadataState"):
                par_el.remove(ch_el)

    canonical_root = bpe.canonicalize_prproj(dst_root, bh_pool)
    os.makedirs(os.path.dirname(out_prproj_path), exist_ok=True)
    with gzip.GzipFile(out_prproj_path, "wb", mtime=0.0) as gz:
        gz.write(b'<?xml version="1.0" encoding="UTF-8" ?>\n')
        gz.write(ET.tostring(canonical_root, encoding="utf-8"))

    mcp_plan = {
        "channel": "animal_whoops",
        "project_id": ep_id,
        "sequence_name": ep_id,
        "resolution": "1920x1080",
        "fps": 23.976,
        "hook_end_ticks": hook_end_ticks,
        "intro_end_ticks": intro_end_ticks,
        "total_duration_ticks": total_seq_ticks,
        "total_duration_sec": round(total_seq_ticks / TICKS_PER_SEC, 3),
        "track_counts": {
            "V5_wtm": len(v5_ids),
            "V4_logo": len(v4_ids),
            "V3_primary": len(v3_ids),
            "V2_adjustment_layer": len(v2_ids),
            "V1_bg_og_no_fx": len(v1_ids),
            "A1_original_audio": len(a1_ids),
            "A2_sfx": len(a2_ids),
            "A3_sfx": len(a3_ids),
            "A4_empty": len(a4_ids),
        },
        "hook_clips": [r for r in timeline_records if r["role"] == "hook"],
        "clips": timeline_records,
        "sfx_items": sfx_specs,
    }
    with open(out_plan_path, "w", encoding="utf-8") as fp:
        json.dump(mcp_plan, fp, indent=2, ensure_ascii=False)
    return mcp_plan


def main():
    t0 = time.time()
    catalog, ep_orig_indices, same_ep_dup_mat, same_batch_dup_mat = build_clean_catalog()

    # Map known audio levels onto catalog items
    for old_p, aud in aud_cache.items():
        if old_p in old_bonk_path_to_cat_idx:
            cidx = old_bonk_path_to_cat_idx[old_p]
            catalog[cidx]["peak_db"] = aud["peak_db"]
            catalog[cidx]["rms_db"] = aud["rms_db"]

    by_sid_clean = {}
    for item in catalog:
        if not item["blur"]:
            by_sid_clean.setdefault(item["sid"], []).append(item)

    os.makedirs(STAGE_DIR, exist_ok=True)
    size_sid_to_cidx = {}
    cidx_to_stage_path = {}

    for b in ("aw1", "aw2", "aw3", "aw4"):
        for i in range(1, 5):
            ep = f"{b}_{i}"
            sdir = rf"E:\Animal Whoops\{b}\{ep}\source"
            for fn in os.listdir(sdir):
                if not fn.endswith(".mp4"):
                    continue
                fp = os.path.join(sdir, fn)
                m = re.search(r"_f(\d+)\.mp4", fn)
                if not m:
                    continue
                sid = int(m.group(1))
                fsize = os.path.getsize(fp)
                key = (sid, fsize)
                if key in size_sid_to_cidx:
                    cidx = size_sid_to_cidx[key]
                else:
                    cands = by_sid_clean.get(sid, [])
                    if not cands:
                        continue
                    if len(cands) == 1:
                        cidx = cands[0]["idx"]
                    else:
                        best_c = None
                        best_h = 999
                        for c in cands:
                            t_25 = max(0.15, c["dur"] * 0.25)
                            dh = dhash_at_time(fp, t_25)
                            h = min(bin(dh ^ int(c["dhs"][0][0])).count("1"), bin(dh ^ int(c["dhs"][0][1])).count("1"))
                            if h < best_h:
                                best_h = h
                                best_c = c
                        cidx = best_c["idx"]
                    size_sid_to_cidx[key] = cidx

                if catalog[cidx].get("peak_db", -12.0) <= -20.0:
                    continue
                if cidx not in cidx_to_stage_path:
                    st_p = os.path.join(STAGE_DIR, f"cidx_{cidx}_f{sid}.mp4")
                    shutil.copy2(fp, st_p)
                    cidx_to_stage_path[cidx] = st_p
                    catalog[cidx]["stage_path"] = st_p
                    if "peak_db" not in catalog[cidx]:
                        catalog[cidx]["peak_db"] = -12.0
                        catalog[cidx]["rms_db"] = -22.0

    print(f"Staged {len(cidx_to_stage_path)} unique sharp & audible (> -20dB) catalog clips", flush=True)
    avail_cidxs = sorted(cidx_to_stage_path.keys(), key=lambda k: -catalog[k]["st"]["center_lap"])

    donor_root, donor_id, donor_uid = bpe.load_xml(DONOR_1506_SAFE)
    donor_bh = {}
    for e in donor_root.iter():
        bh = e.attrib.get("BinaryHash")
        if bh and (e.text or "").strip():
            donor_bh[bh] = e.text

    for b_idx, b in enumerate(("aw1", "aw2", "aw3", "aw4"), start=1):
        batch_used = []
        ep_kept_map = {}
        for i in range(1, 5):
            ep = f"{b}_{i}"
            orig_idxs = [idx for idx in ep_orig_indices[(b, ep)] if idx in cidx_to_stage_path]
            kept = []
            for idx in sorted(orig_idxs, key=lambda k: -catalog[k]["st"]["center_lap"]):
                if any(same_ep_dup_mat[idx, k] for k in kept):
                    continue
                if any(same_batch_dup_mat[idx, u] for u in batch_used):
                    continue
                kept.append(idx)
            kept_set = set(kept)
            seen_k = set()
            ep_sel = []
            for idx in orig_idxs:
                if idx in kept_set and idx not in seen_k:
                    seen_k.add(idx)
                    ep_sel.append(idx)
            ep_kept_map[ep] = ep_sel
            batch_used.extend(ep_sel)

        for i in range(1, 5):
            ep = f"{b}_{i}"
            ep_num = f"{b_idx}{i}"
            ep_t0 = time.time()
            ep_sel = list(ep_kept_map[ep])
            cur_raw = sum(catalog[k]["dur"] for k in ep_sel)

            ordered_donors = [d for d in avail_cidxs if catalog[d]["orig_batch"] == b] + [d for d in avail_cidxs if catalog[d]["orig_batch"] != b]
            for d in ordered_donors:
                if cur_raw >= 1002.0:
                    break
                if cur_raw + catalog[d]["dur"] > 1014.0 and cur_raw >= 996.0:
                    continue
                if any(same_ep_dup_mat[d, k] for k in ep_sel):
                    continue
                if any(same_batch_dup_mat[d, u] for u in batch_used):
                    continue
                ep_sel.append(d)
                batch_used.append(d)
                cur_raw += catalog[d]["dur"]

            selected_dicts = [dict(catalog[idx]) for idx in ep_sel]
            ordered_clips = interleave_selected_clips(selected_dicts)
            same_adj = sum(1 for k in range(len(ordered_clips) - 1) if ordered_clips[k]["vcode"] == ordered_clips[k + 1]["vcode"])

            pdir = rf"E:\Animal Whoops\{b}\{ep}"
            src_dir = os.path.join(pdir, "source")
            vid_dir = rf"E:\Animal Whoops\{b}\VIDEO"
            os.makedirs(src_dir, exist_ok=True)
            os.makedirs(vid_dir, exist_ok=True)

            for fn in os.listdir(src_dir):
                if fn.lower().endswith(".mp4"):
                    try:
                        os.remove(os.path.join(src_dir, fn))
                    except OSError:
                        pass

            body_specs = []
            sheet_rows_csv = [["", "nội dung", "link", "time", "check", "stt", "cre", "cmt"]]
            amz_footages = []

            for idx_c, sc in enumerate(ordered_clips, start=1):
                fname = f"{ep}.{idx_c}_f{sc['sid']}.mp4"
                out_mp4 = os.path.join(src_dir, fname)
                shutil.copy2(sc["stage_path"], out_mp4)
                sc["final_name"] = fname
                sc["final_path"] = out_mp4

                t_str = f"{base.fmt_mmss(sc['bat_dau'])} - {base.fmt_mmss(sc['bat_dau'] + sc['dur'])}"
                sheet_rows_csv.append(["", sc["desc"], sc["url"], t_str, "TRUE", str(idx_c), sc["chan"], ""])
                amz_footages.append({
                    "sortOrder": idx_c,
                    "note": "",
                    "footage": {
                        "id": sc["sid"],
                        "title": sc["desc"],
                        "channel": sc["chan"],
                        "sourceUrl": sc["url"],
                    },
                })
                body_specs.append({
                    "id": f"body_{idx_c:03d}",
                    "name": fname,
                    "path": out_mp4,
                    "in_sec": 0.0,
                    "dur_sec": sc["dur"],
                    "crop_lr_pct": sc["crop_lr_pct"],
                    "v2_crop_pct": sc["v2_crop_pct"],
                    "url": sc["url"],
                    "chan": sc["chan"],
                    "desc": sc["desc"],
                    "hint_meta": {"w": 1920, "h": 1080, "dur_sec": sc["file_dur"], "has_audio": True},
                })

            screened_15, selected_3 = screen_15_and_select_3_hooks(ordered_clips)
            hook_specs = []
            for h_i, hsc in enumerate(selected_3, start=1):
                full_dur = float(hsc["dur"])
                if full_dur <= 5.4:
                    h_in_sec = 0.0
                    h_dur_sec = full_dur
                else:
                    h_dur_sec = 5.0
                    h_in_sec = round(min(1.2, max(0.2, (full_dur - h_dur_sec) * 0.35)), 2)
                hook_specs.append({
                    "id": f"hook_{h_i:02d}",
                    "name": hsc["final_name"],
                    "path": hsc["final_path"],
                    "in_sec": h_in_sec,
                    "dur_sec": h_dur_sec,
                    "crop_lr_pct": hsc["crop_lr_pct"],
                    "v2_crop_pct": hsc["v2_crop_pct"],
                    "body_pos": hsc["body_pos"],
                    "sid": hsc["sid"],
                    "hook_score": hsc["hook_score"],
                    "hint_meta": {"w": 1920, "h": 1080, "dur_sec": hsc["file_dur"], "has_audio": True},
                })

            sfx_specs = []
            for sfx_i, b_idx_sfx in enumerate(range(5, len(body_specs) - 3, 10)):
                bspec = body_specs[b_idx_sfx]
                cdur = bspec["dur_sec"] / 1.06
                s_pool = base.FOLEY_POOL if (sfx_i % 2 == 0) else base.IMPACT_POOL
                s_name = s_pool[(b_idx + i + sfx_i) % len(s_pool)]
                s_path, pk_off = base.get_sfx(s_name)
                tr_num = 2 if (sfx_i % 2 == 0) else 3
                t_imp = round(min(max(0.8, cdur * 0.48), cdur - 0.5), 2)
                sfx_specs.append({
                    "clip_id": bspec["id"],
                    "track": tr_num,
                    "path": s_path,
                    "impact_offset_sec": t_imp,
                    "peak_offset_sec": pk_off,
                })

            csv_path = os.path.join(pdir, f"sheet_KB{ep_num}.csv")
            with open(csv_path, "w", encoding="utf-8", newline="") as fp:
                csv.writer(fp).writerows(sheet_rows_csv)

            json_path = os.path.join(pdir, f"{ep}_s{ep_num}.json")
            with open(json_path, "w", encoding="utf-8") as fp:
                json.dump({"data": {"footages": amz_footages, "screened_15_hook_candidates": [x["final_name"] for x in screened_15], "selected_3_hooks": [x["final_name"] for x in selected_3]}}, fp, indent=2, ensure_ascii=False)

            out_prproj = os.path.join(pdir, f"{ep}.prproj")
            out_plan = os.path.join(pdir, f"{ep}_premiere_mcp_plan.json")
            mcp_plan = compile_animal_whoops_episode(
                ep, hook_specs, body_specs, sfx_specs,
                donor_root, donor_id, donor_uid, donor_bh,
                out_prproj, out_plan,
            )

            fcp_clips = []
            for r in mcp_plan["clips"]:
                fcp_clips.append({
                    "name": r["name"],
                    "file_path": r["path"],
                    "timeline_start": round(r["start_sec"], 3),
                    "timeline_end": round(r["end_sec"], 3),
                    "source_in": round(r["in_sec"], 3),
                    "source_out": round(r["out_sec"], 3),
                })
            out_xml = os.path.join(pdir, f"{ep}.xml")
            with open(out_xml, "w", encoding="utf-8") as fp:
                fp.write(generate_fcp_xml({"sequence_name": ep, "fps": 24, "width": 1920, "height": 1080, "clips": fcp_clips}))

            concat_txt = os.path.join(pdir, "concat_list.txt")
            with open(concat_txt, "w", encoding="utf-8") as fp:
                for hspec in hook_specs:
                    safe_p = hspec["path"].replace("\\", "/").replace("'", "'\\''")
                    in_s = float(hspec["in_sec"])
                    out_s = in_s + float(hspec["dur_sec"])
                    fp.write(f"file '{safe_p}'\n")
                    fp.write(f"inpoint {in_s:.3f}\n")
                    fp.write(f"outpoint {out_s:.3f}\n")
                safe_intro = INTRO_CONCAT_MP4.replace("\\", "/").replace("'", "'\\''")
                fp.write(f"file '{safe_intro}'\n")
                fp.write("inpoint 0.000\n")
                fp.write("outpoint 6.006\n")
                for bspec in body_specs:
                    safe_p = bspec["path"].replace("\\", "/").replace("'", "'\\''")
                    out_s = float(bspec["dur_sec"])
                    fp.write(f"file '{safe_p}'\n")
                    fp.write("inpoint 0.000\n")
                    fp.write(f"outpoint {out_s:.3f}\n")

            out_master_mp4 = os.path.join(vid_dir, f"{ep}.mp4")
            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", "-movflags", "+faststart", out_master_mp4],
                check=True,
            )

            min_lap = min(x["st"]["center_lap"] for x in ordered_clips)
            min_db = min(x.get("peak_db", -12.0) for x in ordered_clips)
            dups_in_ep = sum(1 for a in range(len(ep_sel)) for b_i in range(a + 1, len(ep_sel)) if same_ep_dup_mat[ep_sel[a], ep_sel[b_i]])
            hooks_str = ", ".join(x["name"] for x in hook_specs)
            tot_s = mcp_plan["total_duration_sec"]
            print(
                f"[{ep}] DONE in {time.time()-ep_t0:.1f}s | body={len(body_specs)} (+3 hook + intro) | tl_dur={tot_s:.2f}s ({tot_s/60:.2f}m) | min_lap={min_lap:.2f} | min_peak_db={min_db:.1f}dB | dups={dups_in_ep} | SameLinkAdj={same_adj} | hooks=[{hooks_str}]",
                flush=True,
            )

    shutil.rmtree(STAGE_DIR, ignore_errors=True)
    print(f"\nALL 16 EPISODES REBUILT TO 100% ANIMAL WHOOPS CHANNEL SPEC in {time.time()-t0:.1f}s!", flush=True)


if __name__ == "__main__":
    main()
