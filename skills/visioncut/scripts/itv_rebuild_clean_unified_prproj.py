import base64
import gzip
import json
import os
import re
import shutil
import sys
import uuid
import xml.etree.ElementTree as ET

sys.path.insert(0, r"e:\ITV")
sys.path.insert(0, r"E:\.agents\skills\visioncut\scripts")

from rebuild_all_prproj import (
    COLORS_RGB,
    TICKS_PER_FRAME,
    TICKS_PER_SEC,
    build_komika_flatbuffer,
    canonicalize_prproj,
    clone_subgraph_into,
    set_clip_scale,
    set_subclip_name,
    set_trackitem_timing,
    strip_lumetri_from_ti,
    sync_clip_media_and_stream_duration,
)

BASE_TOOL_DIR = r"E:\ITV\Project tool"
CACHE_DIR = os.path.join(BASE_TOOL_DIR, "_shared_cache")
CFG_PATH = os.path.join(CACHE_DIR, "rebuilder_episode_configs_v3_unified.json")

EPISODES = ["kb133", "kb134", "kb135", "kb136", "kb137", "kb138", "kb139", "kb140"]


def get_ti_mc_and_media(ti_el, dst_by_id):
    sc_ref = ti_el.find(".//SubClip")
    sc_el = dst_by_id[sc_ref.attrib["ObjectRef"]]
    mc_uid = sc_el.find("MasterClip").attrib["ObjectURef"]
    cl_el = dst_by_id[sc_el.find(".//Clip").attrib["ObjectRef"]]
    src_oid = cl_el.find(".//Source").attrib["ObjectRef"]
    src_el = dst_by_id[src_oid]
    media_uid = src_el.find(".//Media").attrib["ObjectURef"]
    return sc_el, mc_uid, cl_el, src_oid, src_el, media_uid


def commit_track_items(track_el, item_ids):
    cont = track_el.find("./ClipTrack/ClipItems/TrackItems")
    if cont is None:
        return
    cont.clear()
    cont.attrib["Version"] = "1"
    for idx, oid in enumerate(item_ids):
        ET.SubElement(cont, "TrackItem", {"Index": str(idx), "ObjectRef": str(oid)})


def build_episode_from_donor(kb_id: str, cfg: dict):
    snum = cfg["snum"]
    proj_dir = os.path.join(BASE_TOOL_DIR, kb_id)
    os.makedirs(proj_dir, exist_ok=True)
    prproj_path = os.path.join(proj_dir, f"{kb_id}.prproj")
    donor_bak_path = os.path.join(proj_dir, f"{kb_id}.pre_m3_bak.prproj")
    orig_seed_bak = os.path.join(proj_dir, f"{kb_id}.seed_102_bak.prproj")
    if not os.path.exists(orig_seed_bak):
        shutil.copy2(donor_bak_path, orig_seed_bak)

    with gzip.open(orig_seed_bak, "rb") as f:
        xml_str = f.read().decode("utf-8")

    # Customize XML paths so any old ITV-Moments-script-<snum> folder reference points to source
    xml_str = xml_str.replace(f"ITV-Moments-script-{snum}", "source")

    dst_root = ET.fromstring(xml_str.encode("utf-8"))
    dst_by_id = {el.attrib["ObjectID"]: el for el in dst_root if "ObjectID" in el.attrib}
    dst_by_uid = {el.attrib["ObjectUID"]: el for el in dst_root if "ObjectUID" in el.attrib}

    bh_pool = {}
    for e in dst_root.iter():
        bh = e.attrib.get("BinaryHash")
        if bh and (e.text or "").strip():
            bh_pool[bh] = e.text

    max_oid = max(int(k) for k in dst_by_id.keys() if k.isdigit())
    curr_oid = [max_oid + 1]

    def next_oid():
        curr_oid[0] += 1
        return curr_oid[0]

    donor_motion_comp_id = None
    for el in dst_root:
        if el.tag not in ("VideoFilterComponent", "VideoComponent"):
            continue
        mname = (el.findtext("MatchName") or el.findtext(".//MatchName") or "").strip()
        if donor_motion_comp_id is None and mname == "AE.ADBE Motion":
            donor_motion_comp_id = el.attrib.get("ObjectID")
            break

    # Locate Sequence and TrackGroups
    seq_el = next(
        s for s in dst_root.iter("Sequence") if s.findtext("Name") == kb_id and s.find("TrackGroups") is not None
    )
    v_tracks, a_tracks = [], []
    for tg in seq_el.find("TrackGroups"):
        second_ref = tg.find("Second")
        second = dst_by_uid.get(second_ref.attrib.get("ObjectURef"))
        if second is None:
            second = dst_by_id.get(second_ref.attrib.get("ObjectRef"))
        if second.tag == "VideoTrackGroup":
            for r in second.find("TrackGroup/Tracks"):
                te = dst_by_uid.get(r.attrib.get("ObjectURef"))
                if te is None:
                    te = dst_by_id.get(r.attrib.get("ObjectRef"))
                v_tracks.append(te)
        elif second.tag == "AudioTrackGroup":
            for r in second.find("TrackGroup/Tracks"):
                te = dst_by_uid.get(r.attrib.get("ObjectURef"))
                if te is None:
                    te = dst_by_id.get(r.attrib.get("ObjectRef"))
                a_tracks.append(te)

    def get_track_item_ids(track_el):
        cont = track_el.find("./ClipTrack/ClipItems/TrackItems")
        return [r.attrib["ObjectRef"] for r in (cont if cont is not None else []) if r.attrib.get("ObjectRef") in dst_by_id]

    v1_ids = get_track_item_ids(v_tracks[0])
    v2_ids = get_track_item_ids(v_tracks[1])
    v3_ids = get_track_item_ids(v_tracks[2])
    v5_ids = get_track_item_ids(v_tracks[4])
    v6_ids = get_track_item_ids(v_tracks[5])
    v7_ids = get_track_item_ids(v_tracks[6])
    v8_ids = get_track_item_ids(v_tracks[7])
    v9_ids = get_track_item_ids(v_tracks[8])
    v10_ids = get_track_item_ids(v_tracks[9])

    a1_ids = get_track_item_ids(a_tracks[0])
    a2_ids = get_track_item_ids(a_tracks[1])
    a7_ids = get_track_item_ids(a_tracks[6])
    a8_ids = get_track_item_ids(a_tracks[7])

    with open(os.path.join(proj_dir, f"{kb_id}_manifest.json"), "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    with open(os.path.join(proj_dir, f"vo_subtitle_manifest_{kb_id}.json"), "r", encoding="utf-8") as f:
        vo_sub_data = json.load(f)
    with open(os.path.join(proj_dir, "intro_teaser_plan.json"), "r", encoding="utf-8") as f:
        intro_plan = json.load(f)

    manifest_by_name = {c["clip_name"]: c for c in manifest_data["clips"]}

    def clean_v3_native_16x9(ti_el):
        # Rule 3: 0 Blur, 0 Crop, 0 Lumetri, Scale = 100.0%, Position = (0.5, 0.5)
        strip_lumetri_from_ti(ti_el, dst_by_id, strip_blur=True, strip_crop=True)
        set_clip_scale(ti_el, dst_by_id, dst_by_uid, dst_root, next_oid, donor_motion_comp_id, 100.0, pos_xy=(0.5, 0.5))

    # 3. Retime all 88 Unified Body Clips on V3[14:102], V1[14:102], and ALL 88 Audible Body Clips on A1[13:101]
    old_silent_body_indices = {78, 79, 80, 81, 82, 84, 85, 86, 87}
    glitch_before_body_idx = {21: 0, 44: 1, 67: 2}
    curr_ticks = 375 * TICKS_PER_FRAME
    v3_clip_timeline_map = {}
    body_clip_refs = {}  # cname -> (mc_uid, media_uid, v_src_oid, a_src_oid, m_path, safe_ticks)
    glitch_intervals = []
    a1_body_item_ids = []
    aud_idx = 0

    _, donor_a1_mc_uid, _, _, _, donor_a1_media_uid = get_ti_mc_and_media(dst_by_id[a1_ids[13]], dst_by_id)

    for body_idx in range(88):
        u_slot = body_idx + 1
        cname = f"itv.{kb_id}.{u_slot}.mp4"
        v3_ti = dst_by_id[v3_ids[14 + body_idx]]
        v1_ti = dst_by_id[v1_ids[14 + body_idx]]

        if body_idx in glitch_before_body_idx:
            gi = glitch_before_body_idx[body_idx]
            g_st = curr_ticks
            g_en = curr_ticks + 9 * TICKS_PER_FRAME
            glitch_intervals.append((g_st, g_en))
            set_trackitem_timing(dst_by_id[v10_ids[gi]], dst_by_id, g_st, g_en, preserve_inpoint=False, explicit_in_ticks=0)
            set_trackitem_timing(dst_by_id[a8_ids[gi]], dst_by_id, g_st, g_en, preserve_inpoint=False, explicit_in_ticks=31 * TICKS_PER_FRAME)
            curr_ticks = g_en

        c_info = manifest_by_name[cname]
        m_path = c_info["source_path"]
        dur_sec = c_info["duration_sec"]
        safe_ticks = int(round(c_info.get("safe_stream_dur_sec", dur_sec) * TICKS_PER_SEC))
        dur_ticks = int(round(dur_sec * TICKS_PER_SEC))
        st_tick = curr_ticks
        en_tick = curr_ticks + dur_ticks

        set_subclip_name(v3_ti, dst_by_id, cname)
        set_trackitem_timing(v3_ti, dst_by_id, st_tick, en_tick, preserve_inpoint=False, explicit_in_ticks=0)
        clean_v3_native_16x9(v3_ti)
        sync_clip_media_and_stream_duration(v3_ti, dst_by_id, dst_by_uid, cname, m_path, safe_ticks, update_media_path=True, proj_dir=proj_dir)

        _, v3_mc_uid, _, v3_src_oid, _, v3_media_uid = get_ti_mc_and_media(v3_ti, dst_by_id)

        v1_sc_el, _, v1_cl_el, _, _, _ = get_ti_mc_and_media(v1_ti, dst_by_id)
        v1_sc_el.find("MasterClip").attrib["ObjectURef"] = v3_mc_uid
        v1_cl_el.find(".//Source").attrib["ObjectRef"] = v3_src_oid
        set_subclip_name(v1_ti, dst_by_id, cname)
        set_trackitem_timing(v1_ti, dst_by_id, st_tick, en_tick, preserve_inpoint=False, explicit_in_ticks=0)
        sync_clip_media_and_stream_duration(v1_ti, dst_by_id, dst_by_uid, cname, m_path, safe_ticks, update_media_path=True, proj_dir=proj_dir)

        if body_idx not in old_silent_body_indices:
            a1_id = a1_ids[13 + aud_idx]
            aud_idx += 1
            a1_ti = dst_by_id[a1_id]
        else:
            a1_id, _, _ = clone_subgraph_into(
                "id",
                a1_ids[13],
                dst_by_id,
                dst_by_uid,
                dst_root,
                next_oid,
                dst_by_id,
                dst_by_uid,
                stop_uids={donor_a1_mc_uid, donor_a1_media_uid},
            )
            a1_ti = dst_by_id[a1_id]

        a1_sc_el, _, _, _, a1_src_el, _ = get_ti_mc_and_media(a1_ti, dst_by_id)
        a1_sc_el.find("MasterClip").attrib["ObjectURef"] = v3_mc_uid
        a1_src_el.find(".//Media").attrib["ObjectURef"] = v3_media_uid
        set_subclip_name(a1_ti, dst_by_id, cname)
        set_trackitem_timing(a1_ti, dst_by_id, st_tick, en_tick, preserve_inpoint=False, explicit_in_ticks=0)
        sync_clip_media_and_stream_duration(a1_ti, dst_by_id, dst_by_uid, cname, m_path, safe_ticks, update_media_path=True, proj_dir=proj_dir)
        a1_body_item_ids.append(a1_id)

        _, _, _, a1_src_oid, _, _ = get_ti_mc_and_media(a1_ti, dst_by_id)
        body_clip_refs[cname] = (v3_mc_uid, v3_media_uid, v3_src_oid, a1_src_oid, m_path, safe_ticks)
        v3_clip_timeline_map[cname] = (st_tick, en_tick, v3_ids[14 + body_idx])
        curr_ticks = en_tick

    total_seq_ticks = curr_ticks

    # Commit 101 items on Track A1 (13 Intro Teasers + 88 Audible Body Clips)
    commit_track_items(a_tracks[0], a1_ids[:13] + a1_body_item_ids)

    # 4. Sync 13 Intro Teaser slots (V3[0:13], V1[0:13], A1[0:13]) from Top-40 -> 11 Hook Scenes in intro_teaser_plan.json
    teaser_13_slots = intro_plan["teaser_13_slots"]
    for i in range(13):
        t_slot = teaser_13_slots[i]
        cname = t_slot["clip_name"]
        sf = int(t_slot["timeline_start_frame"])
        ef = int(t_slot["timeline_end_frame"])
        in_ticks = int(round(float(t_slot["in_sec"]) * TICKS_PER_SEC))

        mc_uid, media_uid, body_v_src_oid, body_a_src_oid, m_path, safe_ticks = body_clip_refs[cname]

        v3_ti = dst_by_id[v3_ids[i]]
        v1_ti = dst_by_id[v1_ids[i]]
        a1_ti = dst_by_id[a1_ids[i]]

        for ti_el, target_src_oid in ((v3_ti, body_v_src_oid), (v1_ti, body_v_src_oid), (a1_ti, body_a_src_oid)):
            sc_el, _, cl_el, _, _, _ = get_ti_mc_and_media(ti_el, dst_by_id)
            sc_el.find("MasterClip").attrib["ObjectURef"] = mc_uid
            cl_el.find(".//Source").attrib["ObjectRef"] = target_src_oid
            set_subclip_name(ti_el, dst_by_id, cname)

        set_trackitem_timing(v3_ti, dst_by_id, sf * TICKS_PER_FRAME, ef * TICKS_PER_FRAME, preserve_inpoint=False, explicit_in_ticks=in_ticks)
        clean_v3_native_16x9(v3_ti)
        sync_clip_media_and_stream_duration(v3_ti, dst_by_id, dst_by_uid, cname, m_path, safe_ticks, update_media_path=True, proj_dir=proj_dir)

        set_trackitem_timing(v1_ti, dst_by_id, sf * TICKS_PER_FRAME, ef * TICKS_PER_FRAME, preserve_inpoint=False, explicit_in_ticks=in_ticks)
        sync_clip_media_and_stream_duration(v1_ti, dst_by_id, dst_by_uid, cname, m_path, safe_ticks, update_media_path=True, proj_dir=proj_dir)

        a1_en_f = 375 if i == 12 else ef
        set_trackitem_timing(a1_ti, dst_by_id, sf * TICKS_PER_FRAME, a1_en_f * TICKS_PER_FRAME, preserve_inpoint=False, explicit_in_ticks=in_ticks)
        sync_clip_media_and_stream_duration(a1_ti, dst_by_id, dst_by_uid, cname, m_path, safe_ticks, update_media_path=True, proj_dir=proj_dir)

    # 5. Update Intro VO stream duration on A2[0:4]
    intro_vo_fname = f"ElevenLabs_{kb_id}_intro_ITV_5_s0_v3.mp3"
    intro_vo_full = os.path.join(proj_dir, "voice", intro_vo_fname)
    intro_vo_ticks = max(int(round(float(intro_plan.get("vo_duration_sec", 12.0)) * TICKS_PER_SEC)), 340 * TICKS_PER_FRAME)
    for i in range(4):
        sync_clip_media_and_stream_duration(
            dst_by_id[a2_ids[i]], dst_by_id, dst_by_uid, intro_vo_fname, intro_vo_full, intro_vo_ticks, update_media_path=(i == 0), proj_dir=proj_dir
        )

    # 6. Update 9 Komika Axis V8 Intro Cards (V8[0:9])
    base_764_bytes = None
    for cand_v8_id in v8_ids[:9]:
        ti_el = dst_by_id[cand_v8_id]
        comps_ref = ti_el.find(".//Components")
        chain_el = dst_by_id.get(comps_ref.attrib.get("ObjectRef")) if comps_ref is not None else None
        if chain_el is not None:
            for c_ref in chain_el.findall(".//Component"):
                cel = dst_by_id.get(c_ref.attrib.get("ObjectRef"))
                if cel is not None and cel.tag == "VideoFilterComponent" and cel.findtext(".//DisplayName") == "Text":
                    p0_ref = cel.find(".//Param")
                    p0_el = dst_by_id.get(p0_ref.attrib.get("ObjectRef")) if p0_ref is not None else None
                    skv_el = p0_el.find("StartKeyframeValue") if p0_el is not None else None
                    if skv_el is not None:
                        b64_src = (skv_el.text or "").strip() or bh_pool.get(skv_el.attrib.get("BinaryHash"), "")
                        if b64_src:
                            raw_b = base64.b64decode(b64_src)
                            if len(raw_b) == 764:
                                base_764_bytes = raw_b
                                break
        if base_764_bytes is not None:
            break

    v8_cards_spec = intro_plan.get("v8_cards", [])
    for i in range(min(9, len(v8_cards_spec))):
        _, cs, ce, clause_txt = v8_cards_spec[i]
        card_ti = dst_by_id[v8_ids[i]]
        set_subclip_name(card_ti, dst_by_id, clause_txt)
        set_trackitem_timing(card_ti, dst_by_id, cs * TICKS_PER_FRAME, ce * TICKS_PER_FRAME, preserve_inpoint=True, explicit_in_ticks=None)
        if base_764_bytes is not None:
            new_fb = build_komika_flatbuffer(base_764_bytes, clause_txt, COLORS_RGB[i % len(COLORS_RGB)])
            new_b64 = base64.b64encode(new_fb).decode("ascii")
            comps_ref = card_ti.find(".//Components")
            chain_el = dst_by_id.get(comps_ref.attrib.get("ObjectRef")) if comps_ref is not None else None
            if chain_el is not None:
                for c_ref in chain_el.findall(".//Component"):
                    cel = dst_by_id.get(c_ref.attrib.get("ObjectRef"))
                    if cel is not None and cel.tag == "VideoFilterComponent" and cel.findtext(".//DisplayName") == "Text":
                        iname_el = cel.find(".//InstanceName")
                        if iname_el is not None and (iname_el.text or "").strip():
                            iname_el.text = clause_txt
                            p0_ref = cel.find(".//Param")
                            p0_el = dst_by_id.get(p0_ref.attrib.get("ObjectRef")) if p0_ref is not None else None
                            skv_el = p0_el.find("StartKeyframeValue") if p0_el is not None else None
                            if skv_el is not None:
                                new_bh = str(uuid.uuid4())
                                skv_el.attrib["BinaryHash"] = new_bh
                                skv_el.text = new_b64
                                bh_pool[new_bh] = new_b64

    # 7. Sync 15 Body VOs (A2[4:19]) & 15 MOGRT Subtitles (V5[0:15])
    for idx, vo in enumerate(vo_sub_data["body_vos"]):
        p_name = vo["parent_clip"]
        p_st, p_en, _ = v3_clip_timeline_map[p_name]
        off_s = float(vo["vo_start_offset_sec"])
        dur_s = float(vo["vo_duration_sec"])
        vo_st = p_st + int(round(off_s * TICKS_PER_SEC))
        vo_en = min(p_en - 2000, vo_st + int(round(dur_s * TICKS_PER_SEC)))
        vo_fname = vo["vo_file"]
        vo_fpath = os.path.join(proj_dir, "voice", vo_fname)

        a2_ti = dst_by_id[a2_ids[4 + idx]]
        set_subclip_name(a2_ti, dst_by_id, vo_fname)
        set_trackitem_timing(a2_ti, dst_by_id, vo_st, vo_en, preserve_inpoint=False, explicit_in_ticks=0)
        sync_clip_media_and_stream_duration(
            a2_ti, dst_by_id, dst_by_uid, vo_fname, vo_fpath, (vo_en - vo_st) + TICKS_PER_FRAME, update_media_path=True, proj_dir=proj_dir
        )

        v5_ti = dst_by_id[v5_ids[idx]]
        set_trackitem_timing(v5_ti, dst_by_id, vo_st, vo_en, preserve_inpoint=False, explicit_in_ticks=0)

    # 8. Rule 3 & Rule 6: Clear Track V4 (0 Emoji), Track A3 & A4 (0 SFX), Track A5 (0 BGM)
    commit_track_items(v_tracks[3], [])  # V4 = 0 Emoji
    commit_track_items(a_tracks[2], [])  # A3 = 0 SFX
    commit_track_items(a_tracks[3], [])  # A4 = 0 SFX
    commit_track_items(a_tracks[4], [])  # A5 = 0 BGM

    # 9. Sync 17 Track V8 Safety Disclaimers (V8[9:26]) on unified clip names
    safety_u_slots = [2, 5, 6, 9, 11, 14, 15, 19, 23, 29, 36, 43, 51, 61, 69, 75, 84]
    for idx, u_slot in enumerate(safety_u_slots):
        sc_name = f"itv.{kb_id}.{u_slot}.mp4"
        c_st, c_en, _ = v3_clip_timeline_map[sc_name]
        set_trackitem_timing(dst_by_id[v8_ids[9 + idx]], dst_by_id, c_st, c_en, preserve_inpoint=True, explicit_in_ticks=None)

    # 10. Sync 3 CTA items on Track V9 & Track A7 on unified clip names
    cta_u_slots = [17, 44, 67]
    for idx, u_slot in enumerate(cta_u_slots):
        cta_cname = f"itv.{kb_id}.{u_slot}.mp4"
        c_st, _, _ = v3_clip_timeline_map[cta_cname]
        cta_en = c_st + 89 * TICKS_PER_FRAME
        set_trackitem_timing(dst_by_id[v9_ids[idx]], dst_by_id, c_st, cta_en, preserve_inpoint=False, explicit_in_ticks=0)
        set_trackitem_timing(dst_by_id[a7_ids[idx]], dst_by_id, c_st, cta_en, preserve_inpoint=False, explicit_in_ticks=0)

    # 11. Sync Utility Tracks V2[3:7], V6[1:5], V7[1:5] around the 3 glitch_intervals and total_seq_ticks
    body_spans = [
        (375 * TICKS_PER_FRAME, glitch_intervals[0][0]),
        (glitch_intervals[0][1], glitch_intervals[1][0]),
        (glitch_intervals[1][1], glitch_intervals[2][0]),
        (glitch_intervals[2][1], total_seq_ticks),
    ]
    v2_base_in = 995000950944000
    v6_base_in = 931359284856000
    v7_base_in = 893833268328000
    for i, (u_st, u_en) in enumerate(body_spans):
        set_trackitem_timing(dst_by_id[v2_ids[3 + i]], dst_by_id, u_st, u_en, preserve_inpoint=False, explicit_in_ticks=v2_base_in + u_st)
        set_trackitem_timing(dst_by_id[v6_ids[1 + i]], dst_by_id, u_st, u_en, preserve_inpoint=False, explicit_in_ticks=v6_base_in + u_st)
        set_trackitem_timing(dst_by_id[v7_ids[1 + i]], dst_by_id, u_st, u_en, preserve_inpoint=False, explicit_in_ticks=v7_base_in + u_st)

    # 12. Rule 8 & Hygiene: Unify all 88 video ClipProjectItems into the single `source` Bin,
    # remove the secondary bin, prune unused emoji/SFX/BGM ClipProjectItems, and sync ClipName tags.
    active_mc_uids = set()
    for trk in list(v_tracks) + list(a_tracks):
        for ti_ref in trk.findall(".//ClipItems/TrackItems/TrackItem"):
            ti_el = dst_by_id.get(ti_ref.attrib.get("ObjectRef"))
            if ti_el is None:
                continue
            sc_ref = ti_el.find(".//SubClip")
            sc_el = dst_by_id.get(sc_ref.attrib.get("ObjectRef")) if sc_ref is not None else None
            mc_ref = sc_el.find("MasterClip") if sc_el is not None else None
            if mc_ref is not None and "ObjectURef" in mc_ref.attrib:
                active_mc_uids.add(mc_ref.attrib["ObjectURef"])

    media_bnm_by_uid = {}
    for m_el in dst_root.findall("Media"):
        fp_txt = (m_el.findtext("FilePath") or "").strip()
        if fp_txt:
            bnm = os.path.basename(fp_txt)
            if "ObjectUID" in m_el.attrib:
                media_bnm_by_uid[m_el.attrib["ObjectUID"]] = bnm
            for cn_el in m_el.iter("ClipName"):
                cn_el.text = bnm
            t_el = m_el.find("Title")
            if t_el is not None:
                t_el.text = bnm

    for src_tag in ("VideoMediaSource", "AudioMediaSource"):
        for ms_el in dst_root.findall(src_tag):
            m_ref = ms_el.find(".//Media")
            muid = m_ref.attrib.get("ObjectURef") if m_ref is not None else None
            if muid in media_bnm_by_uid:
                bnm = media_bnm_by_uid[muid]
                for cn_el in ms_el.iter("ClipName"):
                    cn_el.text = bnm

    for sc_el in dst_root.findall("SubClip"):
        sc_nm = (sc_el.findtext("Name") or "").strip()
        c_ref = sc_el.find(".//Clip")
        c_el = dst_by_id.get(c_ref.attrib.get("ObjectRef")) if c_ref is not None else None
        if sc_nm and c_el is not None:
            for cn_el in c_el.iter("ClipName"):
                cn_el.text = sc_nm

    mc_name_by_uid = {}
    for mc_el in dst_root.findall("MasterClip"):
        mc_uid = mc_el.attrib.get("ObjectUID")
        mc_nm = (mc_el.findtext("Name") or "").strip()
        if mc_uid and mc_nm:
            mc_name_by_uid[mc_uid] = mc_nm
        li_ref = mc_el.find("LoggingInfo")
        li_el = dst_by_id.get(li_ref.attrib.get("ObjectRef")) if li_ref is not None else None
        if mc_nm and li_el is not None:
            for cn_el in li_el.iter("ClipName"):
                cn_el.text = mc_nm

    for el in dst_root.iter():
        if el.tag in ("PeakFilePath", "ConformedAudioPath"):
            el.text = ""
        elif el.tag == "project.settings.lastknowngoodprojectpath":
            el.text = "\\\\?\\" + prproj_path

    ordered_88_mc_uids = [body_clip_refs[f"itv.{kb_id}.{i}.mp4"][0] for i in range(1, 89)]
    cpi_by_mc_uid = {}
    for c_el in dst_root.findall("ClipProjectItem"):
        c_uid = c_el.attrib.get("ObjectUID")
        mc_ref = c_el.find("MasterClip")
        mc_uid = mc_ref.attrib.get("ObjectURef") if mc_ref is not None else None
        if mc_uid in active_mc_uids:
            if mc_uid not in cpi_by_mc_uid:
                cpi_by_mc_uid[mc_uid] = c_uid
            if mc_uid in mc_name_by_uid:
                nm_el = c_el.find("./ProjectItem/Name")
                if nm_el is not None:
                    nm_el.text = mc_name_by_uid[mc_uid]

    source_bins = []
    recovered_bins = []
    for b_el in dst_root.findall("BinProjectItem"):
        bnm = (b_el.findtext("./ProjectItem/Name") or "").strip()
        if bnm == "source" or bnm.startswith("ITV-Moments-script-"):
            source_bins.append(b_el)
        elif bnm == "Recovered Clips":
            recovered_bins.append(b_el)

    primary_source_bin = source_bins[0]
    secondary_bin_uids = {b.attrib["ObjectUID"] for b in source_bins[1:] if "ObjectUID" in b.attrib}

    merged_source_urefs = [cpi_by_mc_uid[mc_uid] for mc_uid in ordered_88_mc_uids if mc_uid in cpi_by_mc_uid]

    p_items_el = primary_source_bin.find(".//ProjectItemContainer/Items")
    p_items_el.clear()
    p_items_el.attrib["Version"] = "1"
    for idx_i, uref in enumerate(merged_source_urefs):
        ET.SubElement(p_items_el, "Item", {"Index": str(idx_i), "ObjectURef": uref})

    # Remove secondary script bin from RootProjectItem while preserving all Sequence ClipProjectItems
    for root_bin_el in dst_root.findall("RootProjectItem"):
        items_el = root_bin_el.find(".//ProjectItemContainer/Items")
        if items_el is None:
            continue
        kept = [
            it.attrib.get("ObjectURef")
            for it in items_el.findall("Item")
            if it.attrib.get("ObjectURef") not in secondary_bin_uids
        ]
        items_el.clear()
        items_el.attrib["Version"] = "1"
        for idx_i, uref in enumerate(kept):
            ET.SubElement(items_el, "Item", {"Index": str(idx_i), "ObjectURef": uref})

    # Prune unused Emoji GIFs, SFX, and BGM from Recovered Clips bin
    unused_asset_names = {
        "[none] Greaser - TrackTribe.mp3",
        "gmod-fall-damage-1.mp3",
        "boin4.mp3",
        "metallic-bonk-and-rattle.mp3",
        "quick-car-crash.mp3",
        "oof.mp3",
        "splash.m4a",
        "body-impact.mp3",
        "slip-2.mp3",
        "bonk.mp3",
        "512 (6).gif",
        "512 (1).gif",
        "mnhat_emoji_37.gif",
        "512 (4).gif",
        "512 (7).gif",
    }
    for rec_bin in recovered_bins:
        items_el = rec_bin.find(".//ProjectItemContainer/Items")
        if items_el is None:
            continue
        kept = []
        for it in items_el.findall("Item"):
            uref = it.attrib.get("ObjectURef")
            c_el = dst_by_uid.get(uref)
            nm = (c_el.findtext("./ProjectItem/Name") or "").strip() if c_el is not None else ""
            if nm in unused_asset_names:
                continue
            kept.append(uref)
        items_el.clear()
        items_el.attrib["Version"] = "1"
        for idx_i, uref in enumerate(kept):
            ET.SubElement(items_el, "Item", {"Index": str(idx_i), "ObjectURef": uref})

    # 13. Canonicalize and write <kb>.prproj & <kb>.pre_m3_bak.prproj
    canonical_root, _ = canonicalize_prproj(dst_root, bh_pool)
    xml_bytes = b'<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(canonical_root, encoding="utf-8")
    for fn in (f"{kb_id}.prproj", f"{kb_id}.pre_m3_bak.prproj"):
        out_p = os.path.join(proj_dir, fn)
        with gzip.GzipFile(out_p, "wb", mtime=0.0) as f:
            f.write(xml_bytes)
    print(
        f"[✓] Built {proj_dir}\\{kb_id}.prproj "
        f"(seq_dur={total_seq_ticks/TICKS_PER_SEC:.2f}s / {total_seq_ticks/(TICKS_PER_SEC*60):.2f}m, "
        f"source_bin_clips={len(merged_source_urefs)}, A1_items={13+len(a1_body_item_ids)})"
    )


def main():
    with open(CFG_PATH, "r", encoding="utf-8") as f:
        all_cfgs = json.load(f)

    for kb in EPISODES:
        build_episode_from_donor(kb, all_cfgs[kb])
    print("ALL 8 UNIFIED EPISODES (kb133..kb140) BUILT SUCCESSFULLY IN E:\\ITV\\Project tool!")


if __name__ == "__main__":
    main()
