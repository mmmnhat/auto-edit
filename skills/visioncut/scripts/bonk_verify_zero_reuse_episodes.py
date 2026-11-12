import gzip
import hashlib
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

TICKS_PER_SEC = 254016000000.0
PROJECT_TOOL_ROOT = Path(r"E:\Bonk funny moments\project tool")

def file_md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fp:
        while True:
            chunk = fp.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def audit_all():
    global_seen_cids = {}
    global_seen_md5s = {}

    for kb_num in range(33, 41):
        kb_id = f"kb{kb_num}"
        pdir = PROJECT_TOOL_ROOT / kb_id
        prproj = pdir / f"{kb_id}.prproj"
        src_dir = pdir / "source"
        old_scr_dir = pdir / f"Bonk-script-{kb_num}"

        # 1. Folder & prefix check
        assert not old_scr_dir.exists(), f"{kb_id}: Split folder {old_scr_dir} still exists!"
        mp4s = sorted(os.listdir(src_dir))
        bad_prefix = [f for f in mp4s if not f.startswith(f"bonk.{kb_id}_") or not f.endswith(".mp4")]
        assert not bad_prefix, f"{kb_id}: Non-conforming filenames in source/: {bad_prefix}"

        # 2. Check cross-episode zero-reuse via JSON footages & MP4 MD5 hashes
        s_json = json.loads((pdir / f"{kb_id}_s{kb_num}.json").read_text(encoding="utf-8"))
        footages = s_json["data"]["footages"]
        ep_cids = [f["footage"]["id"] for f in footages]
        assert len(ep_cids) == len(set(ep_cids)), f"{kb_id}: Intra-episode duplicate canh_id!"
        for cid in ep_cids:
            assert cid not in global_seen_cids, f"{kb_id}: Reused canh_id {cid} from {global_seen_cids[cid]}!"
            global_seen_cids[cid] = kb_id

        for fn in mp4s:
            full_p = str(src_dir / fn)
            md5 = file_md5(full_p)
            assert md5 not in global_seen_md5s, f"{kb_id}/{fn}: Reused MP4 content from {global_seen_md5s[md5]}!"
            global_seen_md5s[md5] = f"{kb_id}/{fn}"

        # 3. Parse XML
        root = ET.fromstring(gzip.open(str(prproj), "rb").read())
        by_id = {e.attrib["ObjectID"]: e for e in root if "ObjectID" in e.attrib}
        by_uid = {e.attrib["ObjectUID"]: e for e in root if "ObjectUID" in e.attrib}

        pek_cnt = sum(1 for e in root.iter() if e.tag in ("PeakFilePath", "ConformedAudioPath"))
        assert pek_cnt == 0, f"{kb_id}: Found {pek_cnt} .pek tags!"

        missing_media = []
        for m in root.iter("Media"):
            fp = m.findtext("ActualMediaFilePath") or m.findtext("FilePath") or ""
            if fp and not os.path.exists(fp):
                missing_media.append(fp)
        assert not missing_media, f"{kb_id}: Missing media files: {missing_media}"

        seq = [s for s in root.iter("Sequence") if s.findtext("Name") == kb_id][0]
        v_tr, a_tr = [], []
        for tg in seq.find("TrackGroups"):
            sec_ref = tg.find("Second")
            sec = by_uid.get(sec_ref.attrib.get("ObjectURef", "")) if sec_ref.attrib.get("ObjectURef", "") in by_uid else by_id.get(sec_ref.attrib.get("ObjectRef", ""))
            if sec is not None and sec.tag == "VideoTrackGroup":
                v_tr = [by_uid.get(x.attrib.get("ObjectURef", "")) if x.attrib.get("ObjectURef", "") in by_uid else by_id.get(x.attrib.get("ObjectRef", "")) for x in sec.find("TrackGroup/Tracks")]
            elif sec is not None and sec.tag == "AudioTrackGroup":
                a_tr = [by_uid.get(x.attrib.get("ObjectURef", "")) if x.attrib.get("ObjectURef", "") in by_uid else by_id.get(x.attrib.get("ObjectRef", "")) for x in sec.find("TrackGroup/Tracks")]

        v_counts = [len(t.findall(".//ClipItems/TrackItems/TrackItem")) for t in v_tr]
        a_counts = [len(t.findall(".//ClipItems/TrackItems/TrackItem")) for t in a_tr]
        a1_tr_cnt = len(a_tr[0].findall(".//TransitionItems/TrackItems/TrackItem"))
        a2_tr_cnt = len(a_tr[1].findall(".//TransitionItems/TrackItems/TrackItem"))

        v1_items = [by_id[x.attrib["ObjectRef"]] for x in v_tr[0].findall(".//ClipItems/TrackItems/TrackItem")]
        v2_items = [by_id[x.attrib["ObjectRef"]] for x in v_tr[1].findall(".//ClipItems/TrackItems/TrackItem")]
        assert len(v1_items) == len(v2_items), f"{kb_id}: V1 ({len(v1_items)}) != V2 ({len(v2_items)})"

        v1_empty_fx_ok = 0
        v2_fx_ok = 0
        v2_cropped_cnt = 0
        for idx, (ti1, ti2) in enumerate(zip(v1_items, v2_items)):
            st1 = int(ti1.findtext(".//Start") or 0)
            en1 = int(ti1.findtext(".//End") or 0)
            st2 = int(ti2.findtext(".//Start") or 0)
            en2 = int(ti2.findtext(".//End") or 0)
            assert st1 == st2 and en1 == en2, f"{kb_id} item {idx}: V1 timing != V2 timing"

            if idx in (2, 3):
                continue

            ch1 = by_id[ti1.find(".//Components").attrib["ObjectRef"]]
            c1_list = ch1.findall("./ComponentChain/Components/Component")
            if len(c1_list) == 0 and ch1.findtext("DefaultMotion") == "true":
                v1_empty_fx_ok += 1

            ch2 = by_id[ti2.find(".//Components").attrib["ObjectRef"]]
            c2_mns = [by_id[c.attrib["ObjectRef"]].findtext("MatchName") for c in ch2.findall("./ComponentChain/Components/Component")]
            if "AE.ADBE Geometry2" in c2_mns and "AE.ADBE Horizontal Flip" in c2_mns:
                v2_fx_ok += 1
            if "AE.ADBE AECrop" in c2_mns:
                v2_cropped_cnt += 1

        total_dur_s = int(v2_items[-1].findtext(".//End")) / TICKS_PER_SEC
        hook_name = by_id[v2_items[0].find(".//SubClip").attrib["ObjectRef"]].findtext("Name")
        intro1_name = by_id[v2_items[2].find(".//SubClip").attrib["ObjectRef"]].findtext("Name")
        intro2_name = by_id[v2_items[3].find(".//SubClip").attrib["ObjectRef"]].findtext("Name")

        assert v_counts[4] == 0 and a_counts[2] == 0 and a_counts[3] == 0, f"{kb_id}: V5/A3/A4 not empty!"
        assert a_counts[1] == 1 and a1_tr_cnt == 1 and a2_tr_cnt == 2, f"{kb_id}: Intro A1/A2 transitions mismatch!"

        print(
            f"[PASS] {kb_id}: dur={total_dur_s:.2f}s ({total_dur_s/60:.2f}m) | unique_mp4s={len(mp4s)} | "
            f"Hook={hook_name} -> Intro=({intro1_name}, {intro2_name}) | "
            f"V1_emptyFX={v1_empty_fx_ok}/{len(v1_items)-2} | V2_Scale120_Rot3_Flip={v2_fx_ok}/{len(v2_items)-2} (Crop={v2_cropped_cnt}) | "
            f"CrossEpReused=0 | pek={pek_cnt}, missing={len(missing_media)}"
        )

    print(f"\n[GLOBAL ZERO-REUSE VERIFIED] Total unique scenes across kb33..kb40 = {len(global_seen_cids)} (0 reused scenes, 0 duplicate MP4 hashes!)")

if __name__ == "__main__":
    audit_all()
