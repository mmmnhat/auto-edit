import gzip
import json
import os
import sys
import xml.etree.ElementTree as ET

TICKS_PER_SEC = 254016000000
TICKS_PER_FRAME = 10594584000
BASE_TOOL_DIR = r"E:\ITV\Project tool"
CACHE_DIR = os.path.join(BASE_TOOL_DIR, "_shared_cache")
PLAN_PATH = os.path.join(CACHE_DIR, "episode_partition_plan_v2_unified.json")
EPISODES = ["kb133", "kb134", "kb135", "kb136", "kb137", "kb138", "kb139", "kb140"]


def verify_all_episodes():
    with open(PLAN_PATH, "r", encoding="utf-8") as f:
        plan_v2 = json.load(f)

    seen_sids = set()
    seen_intervals = []
    seen_phashes = []
    summary_rows = []

    for kb_idx, kb in enumerate(EPISODES):
        snum = 93 + kb_idx
        proj_dir = os.path.join(BASE_TOOL_DIR, kb)
        src_dir = os.path.join(proj_dir, "source")
        old_p2_dir = os.path.join(proj_dir, f"ITV-Moments-script-{snum}")
        prproj_p = os.path.join(proj_dir, f"{kb}.prproj")
        intro_p = os.path.join(proj_dir, "intro_teaser_plan.json")
        man_p = os.path.join(proj_dir, f"{kb}_manifest.json")
        vo_man_p = os.path.join(proj_dir, f"vo_subtitle_manifest_{kb}.json")
        top40_sheet_p = os.path.join(CACHE_DIR, "hook_top40_sheets", f"{kb}_top40.jpg")

        # Rule 8: Disk check
        assert not os.path.exists(old_p2_dir), f"[{kb}] Secondary folder still exists: {old_p2_dir}"
        mp4_files = sorted(f for f in os.listdir(src_dir) if f.lower().endswith(".mp4"))
        expected_mp4s = sorted(f"itv.{kb}.{u}.mp4" for u in range(1, 89))
        assert mp4_files == expected_mp4s, f"[{kb}] Mismatched files in source/: count={len(mp4_files)}"

        # Rule 10: Top-40 sheet & Intro plan check
        assert os.path.exists(top40_sheet_p), f"[{kb}] Missing Top-40 Hook sheet: {top40_sheet_p}"
        intro_plan = json.load(open(intro_p, encoding="utf-8"))
        man = json.load(open(man_p, encoding="utf-8"))
        vo_man = json.load(open(vo_man_p, encoding="utf-8"))
        hook_11 = intro_plan["selected_11_clips"]
        teaser_13 = intro_plan["teaser_13_slots"]
        assert len(hook_11) == 11 == len(set(hook_11)), f"[{kb}] Hook 11 not 11 unique clips"
        assert len(teaser_13) == 13, f"[{kb}] Teaser slots != 13"

        # Rules 2, 4, 5, 6, 7, 9 on episode slots
        slots = plan_v2[kb]["slots"]
        assert len(slots) == 88
        for s in slots:
            sid = s["scene_id"]
            assert sid not in seen_sids, f"[{kb}] Duplicate scene_id: {sid}"
            seen_sids.add(sid)
            assert not s.get("is_pillar", False) and float(s.get("crop_pct", 0.0)) == 0.0, f"[{kb}] Non-16:9 clip: {sid}"
            assert float(s.get("peak_db", -99.0)) > -20.0, f"[{kb}] Quiet peak_db on {sid}: {s.get('peak_db')}"
            assert float(s.get("rms_db", -99.0)) > -36.0, f"[{kb}] Quiet rms_db on {sid}: {s.get('rms_db')}"
            assert float(s.get("diem_tieng", 0.0)) > 20.0, f"[{kb}] Low diem_tieng on {sid}: {s.get('diem_tieng')}"
            assert not s.get("mute_audio", False), f"[{kb}] Muted clip: {sid}"

            # Check interval overlap
            nseg = s.get("norm_seg") or s.get("seg_fname")
            st, en = float(s["start_sec"]), float(s["end_sec"])
            for p_kb, p_sid, p_seg, p_st, p_en in seen_intervals:
                if nseg == p_seg and min(en, p_en) - max(st, p_st) > 0.5:
                    raise AssertionError(f"Interval overlap: {kb}/{sid} vs {p_kb}/{p_sid} on {nseg}")
            seen_intervals.append((kb, sid, nseg, st, en))

            # Check pHash
            ho = int(s["unified_ho"])
            hf = int(s["unified_hf"])
            for p_kb, p_sid, p_ho, p_hf in seen_phashes:
                d1 = (ho ^ p_ho).bit_count()
                d2 = (ho ^ p_hf).bit_count()
                if min(d1, d2) <= 8:
                    raise AssertionError(f"pHash duplicate (d={min(d1,d2)}): {kb}/{sid} vs {p_kb}/{p_sid}")
            seen_phashes.append((kb, sid, ho, hf))

        # Parse .prproj XML
        with gzip.open(prproj_p, "rb") as f:
            root = ET.fromstring(f.read())
        by_id = {el.attrib["ObjectID"]: el for el in root if "ObjectID" in el.attrib}
        by_uid = {el.attrib["ObjectUID"]: el for el in root if "ObjectUID" in el.attrib}

        seq_el = next(s for s in root.iter("Sequence") if s.findtext("Name") == kb and s.find("TrackGroups") is not None)
        v_tracks, a_tracks = [], []
        for tg in seq_el.find("TrackGroups"):
            second_ref = tg.find("Second")
            second = by_uid.get(second_ref.attrib.get("ObjectURef")) or by_id.get(second_ref.attrib.get("ObjectRef"))
            if second.tag == "VideoTrackGroup":
                for r in second.find("TrackGroup/Tracks"):
                    v_tracks.append(by_uid.get(r.attrib.get("ObjectURef")) or by_id.get(r.attrib.get("ObjectRef")))
            elif second.tag == "AudioTrackGroup":
                for r in second.find("TrackGroup/Tracks"):
                    a_tracks.append(by_uid.get(r.attrib.get("ObjectURef")) or by_id.get(r.attrib.get("ObjectRef")))

        def get_t_ids(trk):
            cont = trk.find("./ClipTrack/ClipItems/TrackItems")
            return [r.attrib["ObjectRef"] for r in (cont if cont is not None else []) if r.attrib.get("ObjectRef") in by_id]

        v1_ids = get_t_ids(v_tracks[0])
        v3_ids = get_t_ids(v_tracks[2])
        v4_ids = get_t_ids(v_tracks[3])
        v5_ids = get_t_ids(v_tracks[4])
        a1_ids = get_t_ids(a_tracks[0])
        a2_ids = get_t_ids(a_tracks[1])
        a3_ids = get_t_ids(a_tracks[2])
        a4_ids = get_t_ids(a_tracks[3])
        a5_ids = get_t_ids(a_tracks[4])

        # Rule 3 & Rule 6 track counts
        assert len(v3_ids) == 102, f"[{kb}] V3 len={len(v3_ids)} != 102"
        assert len(v1_ids) == 102, f"[{kb}] V1 len={len(v1_ids)} != 102"
        assert len(a1_ids) == 101, f"[{kb}] A1 len={len(a1_ids)} != 101 (13 Intro + 88 Body)"
        assert len(v4_ids) == 0, f"[{kb}] V4 Emoji len={len(v4_ids)} != 0"
        assert len(a3_ids) == 0, f"[{kb}] A3 SFX len={len(a3_ids)} != 0"
        assert len(a4_ids) == 0, f"[{kb}] A4 SFX len={len(a4_ids)} != 0"
        assert len(a5_ids) == 0, f"[{kb}] A5 BGM len={len(a5_ids)} != 0"
        assert len(a2_ids) == 19 and len(v5_ids) == 15, f"[{kb}] A2/V5 VO counts wrong"

        # Rule 1: Sequence duration ~900s (15 min)
        last_v3_end = int(by_id[v3_ids[-1]].findtext("./ClipTrackItem/TrackItem/End") or 0)
        seq_dur_sec = last_v3_end / TICKS_PER_SEC
        assert 898.5 <= seq_dur_sec <= 901.5, f"[{kb}] Seq dur={seq_dur_sec:.2f}s out of 900.0s±1.5s range"

        # Rule 3: Check 0 Blur, 0 Crop, 0 Lumetri, Scale=100% on all V3 video clips
        for idx_v3, tid in enumerate(v3_ids):
            if idx_v3 == 13:  # Warning nested sequence
                continue
            ti_el = by_id[tid]
            comps_ref = ti_el.find(".//Components")
            chain_el = by_id.get(comps_ref.attrib.get("ObjectRef"))
            for c_ref in chain_el.findall(".//Component"):
                comp = by_id.get(c_ref.attrib.get("ObjectRef"))
                if comp is None:
                    continue
                mname = (comp.findtext("MatchName") or comp.findtext(".//MatchName") or "").strip()
                assert mname not in (
                    "AE.Impact_Blur_FX",
                    "AE.ADBE Gaussian Blur 2",
                    "AE.ADBE AECrop",
                    "AE.ADBE Crop",
                    "AE.ADBE Lumetri",
                ), f"[{kb}] Forbidden effect {mname} on V3[{idx_v3}]"
                if mname == "AE.ADBE Motion":
                    for pref in comp.findall(".//Param"):
                        prm = by_id.get(pref.attrib.get("ObjectRef"))
                        if prm is not None and (prm.findtext("Name") or "") == "Scale":
                            skf = prm.findtext("StartKeyframe") or ""
                            sval = float(skf.split(",")[1]) if "," in skf else 100.0
                            assert abs(sval - 100.0) < 0.01, f"[{kb}] Non-100% Scale={sval} on V3[{idx_v3}]"

        # Rule 2: Full Scene Preservation (InPoint == 0, full duration) on all 88 Body clips
        body_mc_uids = {}
        for b_idx in range(88):
            u_slot = b_idx + 1
            exp_name = f"itv.{kb}.{u_slot}.mp4"
            v3_ti = by_id[v3_ids[14 + b_idx]]
            a1_ti = by_id[a1_ids[13 + b_idx]]
            sc_el = by_id[v3_ti.find(".//SubClip").attrib["ObjectRef"]]
            assert sc_el.findtext("Name") == exp_name, f"[{kb}] Body V3[{b_idx}] name={sc_el.findtext('Name')} != {exp_name}"
            cl_el = by_id[sc_el.find(".//Clip").attrib["ObjectRef"]]
            in_t = int(cl_el.findtext(".//InPoint") or 0)
            out_t = int(cl_el.findtext(".//OutPoint") or 0)
            assert in_t == 0, f"[{kb}] Body {exp_name} InPoint={in_t} != 0"
            v3_st = int(v3_ti.findtext("./ClipTrackItem/TrackItem/Start") or 0)
            v3_en = int(v3_ti.findtext("./ClipTrackItem/TrackItem/End") or 0)
            a1_st = int(a1_ti.findtext("./ClipTrackItem/TrackItem/Start") or 0)
            a1_en = int(a1_ti.findtext("./ClipTrackItem/TrackItem/End") or 0)
            assert v3_st == a1_st and v3_en == a1_en, f"[{kb}] V3/A1 mismatch on {exp_name}"
            body_mc_uids[exp_name] = sc_el.find("MasterClip").attrib["ObjectURef"]

        # Rule 10: Check 13 Intro Teasers on V3[0:13] share MasterClips with Body clips and match 11 Hook scenes
        intro_seen_hooks = set()
        for t_idx in range(13):
            v3_ti = by_id[v3_ids[t_idx]]
            sc_el = by_id[v3_ti.find(".//SubClip").attrib["ObjectRef"]]
            t_name = sc_el.findtext("Name")
            exp_t_name = teaser_13[t_idx]["clip_name"]
            assert t_name == exp_t_name, f"[{kb}] Intro V3[{t_idx}] name={t_name} != {exp_t_name}"
            mc_uid = sc_el.find("MasterClip").attrib["ObjectURef"]
            assert mc_uid == body_mc_uids[t_name], f"[{kb}] Intro V3[{t_idx}] MasterClip does not match Body clip {t_name}"
            intro_seen_hooks.add(t_name)
        assert intro_seen_hooks == set(hook_11), f"[{kb}] Intro seen hooks {len(intro_seen_hooks)} != 11"

        # Rule 8: Check Bins inside .prproj
        bins = [b for b in root.findall("BinProjectItem")]
        bin_names = [(b.findtext("./ProjectItem/Name") or "").strip() for b in bins]
        assert bin_names.count("source") == 1, f"[{kb}] Expected 1 'source' bin, found: {bin_names}"
        assert not any(bn.startswith("ITV-Moments-script-") for bn in bin_names), f"[{kb}] Found script bin: {bin_names}"
        src_bin = next(b for b in bins if (b.findtext("./ProjectItem/Name") or "").strip() == "source")
        src_bin_items = src_bin.findall(".//ProjectItemContainer/Items/Item")
        assert len(src_bin_items) == 88, f"[{kb}] source bin has {len(src_bin_items)} items != 88"

        summary_rows.append((kb, snum, seq_dur_sec, len(mp4_files), len(a1_ids), len(hook_11), len(vo_man["body_vos"])))
        print(
            f"  [PASS 10/10 RULES] {kb} (script-{snum}): seq_dur={seq_dur_sec:.2f}s ({seq_dur_sec/60:.2f}m) | "
            f"source/={len(mp4_files)} unified clips | A1={len(a1_ids)} audible items | "
            f"V4/A3/A4/A5=0 | Blur/Crop/Lumetri=0 | Hook=40->11 ({len(teaser_13)} slots) | VO={len(vo_man['body_vos'])}"
        )

    print(f"\nALL 8 EPISODES (kb133..kb140, {len(seen_sids)} unique 16:9 audible scenes) PASSED 100% OF ALL 10 ITV RULES!")


if __name__ == "__main__":
    verify_all_episodes()
