r"""
Challenger 2 Adversarial Empirical Verification Suite for Milestone 1 Gate.
Tests:
1. Complete search across all .json, .py, .md files in:
   - E:\ITV\youtube_source_cutter
   - E:\.agents\skills\visioncut
   - C:\Users\AMZ-HUY\.agents\skills\visioncut
   Asserts ZERO occurrences of any of the 37 banned interjection filenames from E:\Video Asset\SFX\interjection.
2. Stress-test of select_v8_disclaimer_for_clip and Track V8 safety graphics logic:
   - index % 4 == 1 deadness
   - Harmless clips get 0 disclaimers
   - Vehicle accidents select *THE DRIVER IS OKAY (2247)
   - Female solo falls select *SHE'S FINE (2244)
   - Male solo falls select *HE'S FINE (2245)
   - Dangerous stunts select *DON'T TRY (2246)
   - Multiple people select *NOBODY GOT HURT (2239) / *ALL SAFE (2240)
   - Neutral / general heavy falls select *ALL GOOD (2238)
   - End-to-end integration test: does the caller in itv_10track_finisher actually apply the selected template?
"""

import importlib.util
import json
import os
import sys

# 1. Load the 37 banned interjections directly from disk
BANNED_DIR = r"E:\Video Asset\SFX\interjection"
assert os.path.exists(BANNED_DIR), f"Banned directory {BANNED_DIR} does not exist!"

BANNED_FILES = sorted(os.listdir(BANNED_DIR))
assert len(BANNED_FILES) == 37, f"Expected 37 files, found {len(BANNED_FILES)}"

SEARCH_DIRS = [
    r"E:\ITV\youtube_source_cutter",
    r"E:\.agents\skills\visioncut",
    r"C:\Users\AMZ-HUY\.agents\skills\visioncut",
]

EXTENSIONS = (".json", ".py", ".md")


def test_banned_interjections_zero_occurrences():
    print(f"\n[TEST 1] Searching for 37 banned interjections across target directories...")
    scanned_files = []
    for d in SEARCH_DIRS:
        for root, dirs, files in os.walk(d):
            for f in files:
                if f.lower().endswith(EXTENSIONS):
                    scanned_files.append(os.path.join(root, f))

    print(f"Total files to scan: {len(scanned_files)}")

    filename_violations = []
    path_mentions = []
    # Normalize banned filenames for case-insensitive search
    banned_map = {f.lower(): f for f in BANNED_FILES}

    for path in scanned_files:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
        except Exception as e:
            filename_violations.append((path, "READ_ERROR", str(e)))
            continue

        # Check for any banned filename
        for b_lower, b_orig in banned_map.items():
            if b_lower in content:
                filename_violations.append((path, b_orig, "Banned filename found in content"))

        # Also check for explicit references to the banned folder path
        for kw in ["sfx/interjection", "sfx\\interjection", "sfx\\\\interjection"]:
            if kw in content:
                path_mentions.append((path, kw, "Path reference in policy description"))

    if filename_violations:
        print(f"FAILED: Found {len(filename_violations)} banned interjection filename occurrences:")
        for v in filename_violations:
            print(f"  - {v[0]}: {v[1]} ({v[2]})")
    else:
        print(f"PASSED: 0 occurrences of the 37 banned interjection filenames across all {len(scanned_files)} files.")

    if path_mentions:
        print(f"INFO: Found {len(path_mentions)} path mentions in policy descriptions:")
        for v in path_mentions:
            print(f"  - {v[0]}: {v[1]} ({v[2]})")

    return filename_violations, path_mentions


def test_v8_disclaimer_selection():
    print(f"\n[TEST 2] Stress-testing select_v8_disclaimer_for_clip across accident types & subjects...")

    # Load module dynamically
    finisher_path = r"E:\.agents\skills\visioncut\scripts\itv_10track_finisher.py"
    spec = importlib.util.spec_from_file_location("finisher", finisher_path)
    mod = importlib.util.module_from_spec(spec)
    
    with open(finisher_path, "r", encoding="utf-8") as f:
        src = f.read()

    # Extract only the definition of V8_GRAPHIC_SEMANTIC_MAP and select_v8_disclaimer_for_clip
    map_idx = src.find("V8_GRAPHIC_SEMANTIC_MAP = {")
    assert map_idx != -1, "V8_GRAPHIC_SEMANTIC_MAP not found"
    end_fn_idx = src.find("PHYSICAL_COLLISION_SFX = {", map_idx)
    assert end_fn_idx != -1, "End of select_v8_disclaimer_for_clip not found"

    fn_code = src[map_idx:end_fn_idx]
    namespace = {}
    exec(compile(fn_code, finisher_path, "exec"), namespace)
    select_v8 = namespace["select_v8_disclaimer_for_clip"]
    semantic_map = namespace["V8_GRAPHIC_SEMANTIC_MAP"]

    print(f"Loaded select_v8_disclaimer_for_clip successfully. Semantic map: {semantic_map}")

    results = []

    # Case A: Harmless clips (is_heavy_accident=False)
    harmless_samples = [
        ("cute_puppy_walking.mp4", "cute dog wagging tail"),
        ("cooking_pasta.mp4", "boiling water"),
        ("laughing_baby.mp4", "baby smiles"),
        ("guy_dancing_smoothly.mp4", "smooth salsa dancing"),
        ("car_driving_calmly.mp4", "peaceful scenic road trip"),
    ]
    for name, text in harmless_samples:
        res = select_v8(name, text, is_heavy_accident=False)
        passed = (res is None)
        results.append(("Harmless (accident=False)", name, res, None, passed))

    # Case B: Vehicle accidents -> *THE DRIVER IS OKAY (2247)
    vehicle_samples = [
        ("car_highway_crash.mp4", "car hit median barrier"),
        ("auto_spinout_turn4.mp4", "vehicle flipped on track"),
        ("motorcycle_lowside_slide.mp4", "bike dropped at 40mph"),
        ("truck_t_bone_intersection.mp4", "driver walked away unscathed"),
        ("scooter_curb_hit.mp4", "scooter rider crashed into bush"),
        ("kart_drift_fail.mp4", "go kart overturned on corner"),
        ("boat_dock_collision.mp4", "boat slammed into wooden pier"),
    ]
    for name, text in vehicle_samples:
        res = select_v8(name, text, is_heavy_accident=True)
        passed = (res == "2247")
        results.append(("Vehicle accident", name, res, "2247", passed))

    # Case C: Dangerous stunts -> *DON'T TRY (2246)
    stunt_samples = [
        ("backflip_roof_jump.mp4", "dangerous roof stunt into pool"),
        ("fire_breathing_mishap.mp4", "fire stunt backfire"),
        ("ladder_slip_high_climb.mp4", "guy on tall ladder fixing gutter"),
        ("diy_chainsaw_tree_cut.mp4", "axe and saw stunt gone wrong"),
        ("workshop_press_blast.mp4", "diy workshop power tool slip"),
        ("electricity_wire_spark.mp4", "stunt touching electric fence"),
    ]
    for name, text in stunt_samples:
        res = select_v8(name, text, is_heavy_accident=True)
        passed = (res == "2246")
        results.append(("Dangerous stunt", name, res, "2246", passed))

    # Case D: Female solo falls -> *SHE'S FINE (2244)
    female_samples = [
        ("gymnast_girl_beam_slip.mp4", "girl slipped off balance beam"),
        ("woman_ice_skating_tumble.mp4", "woman fell backwards on ice"),
        ("lady_treadmill_wipeout.mp4", "lady tripped on treadmill"),
        ("female_runner_hurdle_fall.mp4", "she tripped over hurdle"),
        ("mom_trampoline_double_bounce.mp4", "mom fell onto foam pad"),
    ]
    for name, text in female_samples:
        res = select_v8(name, text, is_heavy_accident=True)
        passed = (res == "2244")
        results.append(("Female solo fall", name, res, "2244", passed))

    # Case E: Male solo falls -> *HE'S FINE (2245)
    male_samples = [
        ("skater_boy_rail_grind_slip.mp4", "boy slipped off handrail"),
        ("guy_slipping_on_frozen_lake.mp4", "man lost footing on ice"),
        ("male_pole_vault_mat_miss.mp4", "worker tripped over wheelbarrow"),
        ("dad_hoverboard_wipeout.mp4", "dad fell backwards on carpet"),
        ("bro_dumbbell_drop.mp4", "bro dropped bar on rack"),
    ]
    for name, text in male_samples:
        res = select_v8(name, text, is_heavy_accident=True)
        passed = (res == "2245")
        results.append(("Male solo fall", name, res, "2245", passed))

    # Case F: Multiple people accidents -> *NOBODY GOT HURT (2239) / *ALL SAFE (2240)
    multiple_samples = [
        ("crowd_stage_collapse.mp4", "people fell when stage gave way"),
        ("cheerleader_team_pyramid_fall.mp4", "team pyramid collapsed"),
        ("couple_swing_rope_snap.mp4", "couple fell into river"),
        ("friends_couch_sled_crash.mp4", "three friends on sled hit snow bank"),
    ]
    for name, text in multiple_samples:
        res = select_v8(name, text, is_heavy_accident=True)
        passed = (res in ("2239", "2240"))
        results.append(("Multiple people accident", name, res, "2239/2240", passed))

    # Case G: General / neutral heavy accident -> *ALL GOOD (2238)
    neutral_samples = [
        ("slip_on_banana_peel.mp4", "heavy slip and fall on wet floor"),
        ("trampoline_bounce_off.mp4", "high bounce off bouncy castle"),
        ("chair_leg_collapse.mp4", "heavy fall when stool broke"),
    ]
    for name, text in neutral_samples:
        res = select_v8(name, text, is_heavy_accident=True)
        passed = (res == "2238")
        results.append(("General fall", name, res, "2238", passed))

    # Verify results
    failed_tests = [r for r in results if not r[4]]
    print(f"Total test cases evaluated: {len(results)}. Failures: {len(failed_tests)}")
    for r in results:
        status = "PASS" if r[4] else "FAIL"
        print(f"  [{status}] {r[0]}: '{r[1]}' -> got '{r[2]}', expected '{r[3]}'")

    return failed_tests


def test_v8_disclaimer_caller_integration():
    """
    Empirical check on caller in itv_10track_finisher.py:
    Check line 1260-1284 to verify:
    1. Is index % 4 == 1 present?
    2. Is tmpl_choice actually used to select tmpl_g_id or is it overridden by a modulo loop?
    """
    print(f"\n[TEST 3] Inspecting caller integration in itv_10track_finisher.py (Section 8)...")
    finisher_path = r"E:\.agents\skills\visioncut\scripts\itv_10track_finisher.py"
    with open(finisher_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    section8_lines = []
    in_section8 = False
    for i, line in enumerate(lines, 1):
        if "8. Populate Track V8" in line:
            in_section8 = True
        elif in_section8 and "9. Populate Track A3" in line:
            in_section8 = False
            break
        if in_section8:
            section8_lines.append((i, line))

    print(f"Found Section 8 ({len(section8_lines)} lines).")

    # Check 1: Is index % 4 == 1 present?
    modulo_4_active = any("index\"] % 4 == 1" in l[1] or "index % 4 == 1" in l[1] for l in section8_lines if not l[1].strip().startswith("#"))
    print(f"Active index % 4 == 1 check: {modulo_4_active}")

    # Check 2: How is tmpl_g_id selected?
    tmpl_g_id_lines = [l for l in section8_lines if "tmpl_g_id" in l[1]]
    tmpl_choice_lines = [l for l in section8_lines if "tmpl_choice" in l[1]]

    print("tmpl_choice lines in Section 8:")
    for l in tmpl_choice_lines:
        print(f"  Line {l[0]}: {l[1].strip()}")

    print("tmpl_g_id lines in Section 8:")
    for l in tmpl_g_id_lines:
        print(f"  Line {l[0]}: {l[1].strip()}")

    # Determine if tmpl_choice determines tmpl_g_id
    uses_tmpl_choice_for_g_id = any("tmpl_choice" in l[1] and "tmpl_g_id" in l[1] for l in section8_lines)
    uses_modulo_loop_for_g_id = any("% len(V8_GRAPHIC_TEMPLATES" in l[1] for l in section8_lines)

    print(f"Uses tmpl_choice for tmpl_g_id: {uses_tmpl_choice_for_g_id}")
    print(f"Uses blind modulo loop for tmpl_g_id: {uses_modulo_loop_for_g_id}")

    caller_issues = []
    if modulo_4_active:
        caller_issues.append("Active index % 4 == 1 found in Section 8")
    if not uses_tmpl_choice_for_g_id:
        caller_issues.append("CRITICAL: tmpl_choice is computed but NEVER assigned to tmpl_g_id! tmpl_g_id is set by modulo loop over V8_GRAPHIC_TEMPLATES_100!")
    if uses_modulo_loop_for_g_id:
        caller_issues.append("CRITICAL: Section 8 still uses blind modulo loop `V8_GRAPHIC_TEMPLATES_100[(cinfo['index'] * 3 + v8_added) % len(V8_GRAPHIC_TEMPLATES_100)]`")

    return caller_issues


if __name__ == "__main__":
    t1_fails, t1_paths = test_banned_interjections_zero_occurrences()
    t2_fails = test_v8_disclaimer_selection()
    t3_fails = test_v8_disclaimer_caller_integration()

    print("\n=======================================================")
    print("EMPIRICAL CHALLENGER 2 SUMMARY REPORT")
    print("=======================================================")
    print(f"1. Banned Interjections Scan: {'FAIL (' + str(len(t1_fails)) + ')' if t1_fails else 'PASS (0 occurrences)'}")
    print(f"2. select_v8_disclaimer_for_clip Logic: {'FAIL (' + str(len(t2_fails)) + ')' if t2_fails else 'PASS (100% accurate)'}")
    print(f"3. Caller Integration in itv_10track_finisher.py: {'FAIL (' + str(len(t3_fails)) + ')' if t3_fails else 'PASS'}")
    if t3_fails:
        for f in t3_fails:
            print(f"   * {f}")
    print("=======================================================")
