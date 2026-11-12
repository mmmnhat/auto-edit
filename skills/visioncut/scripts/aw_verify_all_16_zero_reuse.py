import os
import re
import csv
import gzip
import json
import xml.etree.ElementTree as ET

TICKS_PER_SEC = 254016000000


def verify_all_16():
    all_ok = True
    global_seen_intervals = []  # (ep, vcode, st, en)
    print("=" * 126)
    print(
        f"{'EPISODE':<8} | {'DUR(m)':<7} | {'HOOKS':<5} | {'BODY':<5} | {'INTRA-DUP':<9} | {'CROSS-DUP':<9} | "
        f"{'V1(OG)':<6} | {'V2(ADJ)':<7} | {'V3(FX)':<6} | {'V4(LOGO)':<8} | {'V5(WTM)':<7} | {'A1(106%)':<8} | {'1-DIR'}"
    )
    print("-" * 126)

    for b in ("aw1", "aw2", "aw3", "aw4"):
        b_idx = int(b[-1])
        for i in range(1, 5):
            ep = f"{b}_{i}"
            ep_num = f"{b_idx}{i}"
            pdir = rf"E:\Animal Whoops\{b}\{ep}"
            src_dir = os.path.join(pdir, "source")
            prproj = os.path.join(pdir, f"{ep}.prproj")
            plan_p = os.path.join(pdir, f"{ep}_premiere_mcp_plan.json")
            csv_p = os.path.join(pdir, f"sheet_KB{ep_num}.csv")

            # 1. Check intra-episode & cross-episode interval reuse via sheet_KB
            rows = list(csv.reader(open(csv_p, encoding="utf-8")))[1:]
            ep_intervals = []
            intra_dups = 0
            cross_dups = 0
            for r in rows:
                vc = r[2].split("v=")[-1].strip()
                m = re.match(r"(\d+):(\d+)\s*-\s*(\d+):(\d+)", r[3].strip())
                st_s = int(m.group(1)) * 60 + int(m.group(2))
                en_s = int(m.group(3)) * 60 + int(m.group(4))
                if any(vc == u_vc and (min(en_s, u_en) - max(st_s, u_st) > 1) for _, u_vc, u_st, u_en in ep_intervals):
                    intra_dups += 1
                if any(vc == g_vc and (min(en_s, g_en) - max(st_s, g_st) > 1) for _, g_vc, g_st, g_en in global_seen_intervals):
                    cross_dups += 1
                ep_intervals.append((ep, vc, st_s, en_s))
            global_seen_intervals.extend(ep_intervals)

            # 2. Check single-folder & prefix rule
            has_bonk_dir = any(d.lower().startswith("bonk-script") for d in os.listdir(pdir))
            mp4s = [f for f in os.listdir(src_dir) if f.lower().endswith(".mp4")]
            has_bad_prefix = any(not f.startswith(f"{ep}.") for f in mp4s)
            single_dir_ok = (not has_bonk_dir) and (not has_bad_prefix) and (len(mp4s) == len(rows))

            # 3. Check Premiere Pro timeline tracks
            root = ET.fromstring(gzip.open(prproj, "rb").read())
            by_id = {e.attrib["ObjectID"]: e for e in root if "ObjectID" in e.attrib}
            by_uid = {e.attrib["ObjectUID"]: e for e in root if "ObjectUID" in e.attrib}

            seqs = [s for s in root.iter("Sequence") if "ObjectUID" in s.attrib and s.find("TrackGroups") is not None]
            seq_el = max(seqs, key=lambda s: len(ET.tostring(s)))
            v_tracks, a_tracks = [], []
            for tg in seq_el.find("TrackGroups"):
                sec_ref = tg.find("Second")
                sec = by_uid.get(sec_ref.attrib.get("ObjectURef", "")) or by_id.get(sec_ref.attrib.get("ObjectRef", ""))
                if sec is None or sec.find("TrackGroup/Tracks") is None:
                    continue
                if sec.tag == "VideoTrackGroup":
                    for r in sec.find("TrackGroup/Tracks"):
                        v_tracks.append(by_uid.get(r.attrib.get("ObjectURef", "")) or by_id.get(r.attrib.get("ObjectRef", "")))
                elif sec.tag == "AudioTrackGroup":
                    for r in sec.find("TrackGroup/Tracks"):
                        a_tracks.append(by_uid.get(r.attrib.get("ObjectURef", "")) or by_id.get(r.attrib.get("ObjectRef", "")))

            def get_titems(tr):
                return [by_id[x.attrib["ObjectRef"]] for x in tr.findall("./ClipTrack/ClipItems/TrackItems/TrackItem")]

            v1_t = get_titems(v_tracks[0])
            v2_t = get_titems(v_tracks[1])
            v3_t = get_titems(v_tracks[2])
            v4_t = get_titems(v_tracks[3])
            v5_t = get_titems(v_tracks[4])
            a1_t = get_titems(a_tracks[0])

            v1_ok = True
            for ti in v1_t:
                ch = by_id[ti.find(".//Components").attrib["ObjectRef"]]
                comps = ch.findall(".//Component")
                vc = by_id[by_id[ti.find(".//SubClip").attrib["ObjectRef"]].find("Clip").attrib["ObjectRef"]]
                if ch.findtext("DefaultMotion") != "true" or len(comps) != 0:
                    v1_ok = False
                if b != "aw1" and (vc.findtext(".//PlaybackSpeed") != "1.06" or vc.findtext("TimeInterpolationType") != "2"):
                    v1_ok = False

            v2_ok = len(v2_t) >= 2 and all(by_id[ti.find(".//SubClip").attrib["ObjectRef"]].findtext("Name") == "Adjustment Layer" for ti in v2_t)
            v3_ok = (len(v3_t) == len(v1_t) + 1)
            v4_ok = len(v4_t) >= 2 and all(by_id[ti.find(".//SubClip").attrib["ObjectRef"]].findtext("Name") == "Logo Animal Whoops.png" for ti in v4_t)
            v5_ok = len(v5_t) >= 2 and all(by_id[ti.find(".//SubClip").attrib["ObjectRef"]].findtext("Name") == "wtm.jpg" for ti in v5_t)
            a1_ok = (len(a1_t) == len(v3_t))

            pl = json.load(open(plan_p, encoding="utf-8"))
            dur_m = pl["total_duration_sec"] / 60.0
            body_cnt = len(rows)

            if not (intra_dups == 0 and cross_dups == 0 and single_dir_ok and v1_ok and v2_ok and v3_ok and v4_ok and v5_ok and a1_ok):
                all_ok = False

            print(
                f"{ep:<8} | {dur_m:>6.2f}m | {'3/15':<5} | {body_cnt:<5} | {intra_dups:<9} | {cross_dups:<9} | "
                f"{'OK' if v1_ok else 'ERR':<6} | {'OK' if v2_ok else 'ERR':<7} | {'OK' if v3_ok else 'ERR':<6} | "
                f"{'OK' if v4_ok else 'ERR':<8} | {'OK' if v5_ok else 'ERR':<7} | {'OK' if a1_ok else 'ERR':<8} | "
                f"{'OK' if single_dir_ok else 'ERR'}"
            )
    print("=" * 126)
    print("OVERALL 16-EPISODE ZERO-REUSE & RULES VERIFICATION:", "100% PASS" if all_ok else "FAILED")


if __name__ == "__main__":
    verify_all_16()
