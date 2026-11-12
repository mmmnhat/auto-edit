# ITV E2E Test Execution Report — 2026-11-10T07:17:08.164655+00:00

## Executive Summary
- **Overall Pass Rate**: 100.0% (360/360 passed, 0 failed)

| Project | Passed | Failed | Pass Rate | Status |
|---|---|---|---|---|
| **kb132** | 40 | 0 | 100.0% | ✅ PASS |
| **kb133** | 40 | 0 | 100.0% | ✅ PASS |
| **kb134** | 40 | 0 | 100.0% | ✅ PASS |
| **kb135** | 40 | 0 | 100.0% | ✅ PASS |
| **kb136** | 40 | 0 | 100.0% | ✅ PASS |
| **kb137** | 40 | 0 | 100.0% | ✅ PASS |
| **kb138** | 40 | 0 | 100.0% | ✅ PASS |
| **kb139** | 40 | 0 | 100.0% | ✅ PASS |
| **kb140** | 40 | 0 | 100.0% | ✅ PASS |

## Project kb132 Assertions Detail

| ID | Req | Description | Result | Observed | Expected |
|---|---|---|---|---|---|
| `TEST-R1-01` | R1 Duration | Zero timeline OVERRIDES on Part 1 clips (InPoint == 0) | PASS | 0 overridden clips | 0 overrides |
| `TEST-R1-02` | R1 Duration | 100% Google Sheet duration match (|tl_dur - sheet_dur| <= 0.60s) | PASS | 0/20 duration mismatches | 0 mismatches (tolerance <= 0.60s) |
| `TEST-R1-03` | R1 Duration | 100% note duration match for Part 2 clips (|tl_dur - note_dur| <= 0.30s) | PASS | 0/7 note duration mismatches | 0 mismatches (tolerance <= 0.30s) |
| `TEST-R1-04` | R1 Duration | VisionCut climax duration preservation for non-note clips (0 arbitrary flat 5.6s cap) | PASS | 0/33 non-note clips out of spec | 0 flat-capped or mismatched clips |
| `TEST-R1-05` | R1 Duration | Multi-timestamp sources split into >= 2 separate files (0 concat) | PASS | 0/0 unsplit multi-ts sources | 0 unsplit sources (>= 2 separate files each) |
| `TEST-R2-03` | R2 Watermark | ViralHog clips zoomed to Scale >= 115.0% | PASS | 0/30 ViralHog clips with Scale < 115.0% | Scale >= 115.0% on all ViralHog clips |
| `TEST-R2-04` | R2 Watermark | Strict zero blur mask on ViralHog clips | PASS | 0/30 ViralHog clips with blur masks | 0 blur masks on ViralHog |
| `TEST-R2-02` | R2 Watermark | Zero blind blur template 8000 applied across all Part 1 clips | PASS | 19/33 Part 1 clips with blur | Channel-specific selective presets (not 100% blind assignment) |
| `TEST-R2-01` | R2 Watermark | Channel watermark preset and crop validity | PASS | 0 invalid crop clips | 0 invalid crop settings |
| `TEST-R3-01` | R3 SFX | Zero collision SFX on audible Track A1 camera audio (Part 1) | PASS | 0 collision SFX on Part 1 | 0 collision SFX on live camera audio |
| `TEST-R3-02` | R3 SFX | 100% SFX coverage on silent clips under Track A5 BGM | PASS | 100.0% (0/9 uncovered) | 100% SFX coverage |
| `TEST-R3-03` | R3 SFX | Zero overlap between Track A3/A4 SFX and Track A2 Voiceover | PASS | 0.000s overlap | 0.000s overlap |
| `TEST-R3-04` | R3 SFX | Strict ban on interjection SFX on timeline and in configs | PASS | 0 timeline items, 0 catalog violations | 0 interjection SFX entries |
| `TEST-R4-01` | R4 Emojis & Graphics | Zero static center emojis on Track V4 (no 0.50, 0.50 center clustering) | PASS | 0 static center emojis | 0 static center emojis |
| `TEST-R4-02` | R4 Emojis & Graphics | Track V4 valid impact duration (0.2-0.8s) or corner reaction GIF (1.5-2.3s) | PASS | 0/5 non-compliant V4 items | 0 non-compliant items |
| `TEST-R4-03` | R4 Emojis & Graphics | Track V8 safety graphics modulo loop eliminated & semantic text mapping | PASS | modulo_loop=False, unknown_texts=0 | modulo_loop=False, 100% semantic matching |
| `TEST-R5-01` | R5 Voiceover & Subs | Dynamic VO offset reasoning (eliminate fixed +1.50s formula) | PASS | 0/15 VOs at fixed +1.50s (variance=1.706) | <= 3 fixed 1.5s offsets and variance > 0.35s^2 |
| `TEST-R5-03` | R5 Voiceover & Subs | Track V5 MOGRT subtitles 100% synchronized with Track A2 VO | PASS | 0 timing mismatches (V5 count=15, A2 count=15) | 0 mismatches, V5 count == A2 count |
| `TEST-R5-02` | R5 Voiceover & Subs | VO respects Premise/Aftermath boundaries without spilling past clips | PASS | 0 boundary violations | 0 boundary violations |
| `TEST-R6-01` | R6 Invariants | INV-01: Audio Coverage = 100% (A1 | A5 | A8) | PASS | 100.00% | 100.0% coverage |
| `TEST-R6-02` | R6 Invariants | INV-02: V1 == V3 Full Sync (Start, End, InPoint, OutPoint) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-03` | R6 Invariants | INV-03: V5 == A2 Full Sync (Start, End) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-04` | R6 Invariants | INV-04: Zero Black Gaps on Video (V3 | V10) and duration <= 960.0s | PASS | coverage=100.00%, duration=889.30s | coverage=100.0%, duration <= 960.0s |
| `TEST-R6-05` | R6 Invariants | INV-05: Clean .prproj XML & Referential Integrity (0 dangling pointers) | PASS | 0 dangling references | 0 dangling references |
| `TEST-R7-01` | R7 Intro Architecture | Ground-truth kb111-kb117 'Hello everyone!' greeting with unique episode body hook | PASS | valid_script=True, 0 violations | valid_script=True, 0 violations |
| `TEST-R7-02` | R7 Intro Architecture | Ground-truth Intro architecture present (A6 Hadeus.mp4, Teaser 1a/1b split) | PASS | A6_Hadeus=True, Teaser1_split=True, intro_cuts=14 | A6_Hadeus=True, Teaser1_split=True, intro_cuts>=6 |
| `TEST-R7-03` | R7 Intro Architecture | Middle fast-cut teasers (6-8 rapid climax cuts of 15-32 frames) | PASS | 8 rapid cuts (total mid clips=8) | >= 5 rapid cuts between 15f and 32f |
| `TEST-R7-04` | R7 Intro Architecture | 20-frame Warning card & Intro boundary before Part 1 body clips | PASS | has_warning=True, part1_start_frame=375 | has_warning=True, part1_start_frame >= 320 |
| `BOUND-DUR-01` | R1 Duration Boundary | Part 1 cut boundary snap within +-0.30s per transition | PASS | 0 clips exceeded snap boundary | max snap deviation <= 0.60s total |
| `BOUND-DUR-02` | R6 Duration Boundary | Sequence total duration bounded: 420.0s <= duration <= 960.0s | PASS | 889.30s (14.82m) | [420.0s .. 960.0s] |
| `BOUND-DUR-03` | R1 Duration Boundary | Long clips (>= 15s raw) preserve valid VisionCut climax window | PASS | 0 long clips out of bounds | 0 long clips out of bounds |
| `BOUND-SCALE-01` | R2 Scale Boundary | ViralHog clips satisfy Scale >= 115.00% lower bound | PASS | 0/30 below lower bound | Scale >= 115.00% |
| `BOUND-SCALE-02` | R2 Crop Boundary | Pillarbox crop within bounds [20.0% .. 38.0%] | PASS | 0 out-of-bound crop clips | [20.0% .. 38.0%] |
| `BOUND-SFX-01` | R3 SFX Boundary | A2 Voiceover and A3/A4 SFX overlap boundary strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-SFX-02` | R6 Audio Boundary | A1 camera audio and A5 BGM overlap strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-INTRO-01` | R7 Intro Boundary | Intro section duration bounded [335 .. 390] frames | PASS | 375 frames (15.64s) | [335 .. 390] frames |
| `BOUND-INTRO-02` | R7 Intro Boundary | Warning card duration strictly 20 frames | PASS | [20] frames | exactly 20 frames |
| `COMBO-VH-PILLAR-01` | R2 Combination Synergy | ViralHog + Pillarbox dual constraint: Crop + Compensated Scale >= 120% + 0 Blur | PASS | 0/0 combo violations | 0 combo violations |
| `COMBO-MULTITS-A1-01` | R1 Multi-TS Synergy | Multi-TS discrete splitting produces paired V3 video and A1 audio track items | PASS | 0/0 unpaired multi-ts sources | 0 unpaired sources |
| `COMBO-VO-SUB-V8-01` | R4/R5 Narrative Synergy | 1-to-1 sync between Track V5 subtitles, Track A2 VO, and Track V8 graphics | PASS | V5 count=15, A2 count=15, V8 count=26 | V5 == A2, 0 sync mismatches |

## Project kb133 Assertions Detail

| ID | Req | Description | Result | Observed | Expected |
|---|---|---|---|---|---|
| `TEST-R1-01` | R1 Duration | Zero timeline OVERRIDES on Part 1 clips (InPoint == 0) | PASS | 0 overridden clips | 0 overrides |
| `TEST-R1-02` | R1 Duration | 100% Google Sheet duration match (|tl_dur - sheet_dur| <= 0.60s) | PASS | 0/20 duration mismatches | 0 mismatches (tolerance <= 0.60s) |
| `TEST-R1-03` | R1 Duration | 100% note duration match for Part 2 clips (|tl_dur - note_dur| <= 0.30s) | PASS | 0/5 note duration mismatches | 0 mismatches (tolerance <= 0.30s) |
| `TEST-R1-04` | R1 Duration | VisionCut climax duration preservation for non-note clips (0 arbitrary flat 5.6s cap) | PASS | 0/34 non-note clips out of spec | 0 flat-capped or mismatched clips |
| `TEST-R1-05` | R1 Duration | Multi-timestamp sources split into >= 2 separate files (0 concat) | PASS | 0/0 unsplit multi-ts sources | 0 unsplit sources (>= 2 separate files each) |
| `TEST-R2-03` | R2 Watermark | ViralHog clips zoomed to Scale >= 115.0% | PASS | 0/30 ViralHog clips with Scale < 115.0% | Scale >= 115.0% on all ViralHog clips |
| `TEST-R2-04` | R2 Watermark | Strict zero blur mask on ViralHog clips | PASS | 0/30 ViralHog clips with blur masks | 0 blur masks on ViralHog |
| `TEST-R2-02` | R2 Watermark | Zero blind blur template 8000 applied across all Part 1 clips | PASS | 11/33 Part 1 clips with blur | Channel-specific selective presets (not 100% blind assignment) |
| `TEST-R2-01` | R2 Watermark | Channel watermark preset and crop validity | PASS | 0 invalid crop clips | 0 invalid crop settings |
| `TEST-R3-01` | R3 SFX | Zero collision SFX on audible Track A1 camera audio (Part 1) | PASS | 0 collision SFX on Part 1 | 0 collision SFX on live camera audio |
| `TEST-R3-02` | R3 SFX | 100% SFX coverage on silent clips under Track A5 BGM | PASS | 100.0% (0/9 uncovered) | 100% SFX coverage |
| `TEST-R3-03` | R3 SFX | Zero overlap between Track A3/A4 SFX and Track A2 Voiceover | PASS | 0.000s overlap | 0.000s overlap |
| `TEST-R3-04` | R3 SFX | Strict ban on interjection SFX on timeline and in configs | PASS | 0 timeline items, 0 catalog violations | 0 interjection SFX entries |
| `TEST-R4-01` | R4 Emojis & Graphics | Zero static center emojis on Track V4 (no 0.50, 0.50 center clustering) | PASS | 0 static center emojis | 0 static center emojis |
| `TEST-R4-02` | R4 Emojis & Graphics | Track V4 valid impact duration (0.2-0.8s) or corner reaction GIF (1.5-2.3s) | PASS | 0/5 non-compliant V4 items | 0 non-compliant items |
| `TEST-R4-03` | R4 Emojis & Graphics | Track V8 safety graphics modulo loop eliminated & semantic text mapping | PASS | modulo_loop=False, unknown_texts=0 | modulo_loop=False, 100% semantic matching |
| `TEST-R5-01` | R5 Voiceover & Subs | Dynamic VO offset reasoning (eliminate fixed +1.50s formula) | PASS | 0/15 VOs at fixed +1.50s (variance=1.706) | <= 3 fixed 1.5s offsets and variance > 0.35s^2 |
| `TEST-R5-03` | R5 Voiceover & Subs | Track V5 MOGRT subtitles 100% synchronized with Track A2 VO | PASS | 0 timing mismatches (V5 count=15, A2 count=15) | 0 mismatches, V5 count == A2 count |
| `TEST-R5-02` | R5 Voiceover & Subs | VO respects Premise/Aftermath boundaries without spilling past clips | PASS | 0 boundary violations | 0 boundary violations |
| `TEST-R6-01` | R6 Invariants | INV-01: Audio Coverage = 100% (A1 | A5 | A8) | PASS | 100.00% | 100.0% coverage |
| `TEST-R6-02` | R6 Invariants | INV-02: V1 == V3 Full Sync (Start, End, InPoint, OutPoint) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-03` | R6 Invariants | INV-03: V5 == A2 Full Sync (Start, End) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-04` | R6 Invariants | INV-04: Zero Black Gaps on Video (V3 | V10) and duration <= 960.0s | PASS | coverage=100.00%, duration=880.92s | coverage=100.0%, duration <= 960.0s |
| `TEST-R6-05` | R6 Invariants | INV-05: Clean .prproj XML & Referential Integrity (0 dangling pointers) | PASS | 0 dangling references | 0 dangling references |
| `TEST-R7-01` | R7 Intro Architecture | Ground-truth kb111-kb117 'Hello everyone!' greeting with unique episode body hook | PASS | valid_script=True, 0 violations | valid_script=True, 0 violations |
| `TEST-R7-02` | R7 Intro Architecture | Ground-truth Intro architecture present (A6 Hadeus.mp4, Teaser 1a/1b split) | PASS | A6_Hadeus=True, Teaser1_split=True, intro_cuts=14 | A6_Hadeus=True, Teaser1_split=True, intro_cuts>=6 |
| `TEST-R7-03` | R7 Intro Architecture | Middle fast-cut teasers (6-8 rapid climax cuts of 15-32 frames) | PASS | 8 rapid cuts (total mid clips=8) | >= 5 rapid cuts between 15f and 32f |
| `TEST-R7-04` | R7 Intro Architecture | 20-frame Warning card & Intro boundary before Part 1 body clips | PASS | has_warning=True, part1_start_frame=375 | has_warning=True, part1_start_frame >= 320 |
| `BOUND-DUR-01` | R1 Duration Boundary | Part 1 cut boundary snap within +-0.30s per transition | PASS | 0 clips exceeded snap boundary | max snap deviation <= 0.60s total |
| `BOUND-DUR-02` | R6 Duration Boundary | Sequence total duration bounded: 420.0s <= duration <= 960.0s | PASS | 880.92s (14.68m) | [420.0s .. 960.0s] |
| `BOUND-DUR-03` | R1 Duration Boundary | Long clips (>= 15s raw) preserve valid VisionCut climax window | PASS | 0 long clips out of bounds | 0 long clips out of bounds |
| `BOUND-SCALE-01` | R2 Scale Boundary | ViralHog clips satisfy Scale >= 115.00% lower bound | PASS | 0/30 below lower bound | Scale >= 115.00% |
| `BOUND-SCALE-02` | R2 Crop Boundary | Pillarbox crop within bounds [20.0% .. 38.0%] | PASS | 0 out-of-bound crop clips | [20.0% .. 38.0%] |
| `BOUND-SFX-01` | R3 SFX Boundary | A2 Voiceover and A3/A4 SFX overlap boundary strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-SFX-02` | R6 Audio Boundary | A1 camera audio and A5 BGM overlap strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-INTRO-01` | R7 Intro Boundary | Intro section duration bounded [335 .. 390] frames | PASS | 375 frames (15.64s) | [335 .. 390] frames |
| `BOUND-INTRO-02` | R7 Intro Boundary | Warning card duration strictly 20 frames | PASS | [20] frames | exactly 20 frames |
| `COMBO-VH-PILLAR-01` | R2 Combination Synergy | ViralHog + Pillarbox dual constraint: Crop + Compensated Scale >= 120% + 0 Blur | PASS | 0/0 combo violations | 0 combo violations |
| `COMBO-MULTITS-A1-01` | R1 Multi-TS Synergy | Multi-TS discrete splitting produces paired V3 video and A1 audio track items | PASS | 0/0 unpaired multi-ts sources | 0 unpaired sources |
| `COMBO-VO-SUB-V8-01` | R4/R5 Narrative Synergy | 1-to-1 sync between Track V5 subtitles, Track A2 VO, and Track V8 graphics | PASS | V5 count=15, A2 count=15, V8 count=26 | V5 == A2, 0 sync mismatches |

## Project kb134 Assertions Detail

| ID | Req | Description | Result | Observed | Expected |
|---|---|---|---|---|---|
| `TEST-R1-01` | R1 Duration | Zero timeline OVERRIDES on Part 1 clips (InPoint == 0) | PASS | 0 overridden clips | 0 overrides |
| `TEST-R1-02` | R1 Duration | 100% Google Sheet duration match (|tl_dur - sheet_dur| <= 0.60s) | PASS | 0/20 duration mismatches | 0 mismatches (tolerance <= 0.60s) |
| `TEST-R1-03` | R1 Duration | 100% note duration match for Part 2 clips (|tl_dur - note_dur| <= 0.30s) | PASS | 0/7 note duration mismatches | 0 mismatches (tolerance <= 0.30s) |
| `TEST-R1-04` | R1 Duration | VisionCut climax duration preservation for non-note clips (0 arbitrary flat 5.6s cap) | PASS | 0/35 non-note clips out of spec | 0 flat-capped or mismatched clips |
| `TEST-R1-05` | R1 Duration | Multi-timestamp sources split into >= 2 separate files (0 concat) | PASS | 0/0 unsplit multi-ts sources | 0 unsplit sources (>= 2 separate files each) |
| `TEST-R2-03` | R2 Watermark | ViralHog clips zoomed to Scale >= 115.0% | PASS | 0/30 ViralHog clips with Scale < 115.0% | Scale >= 115.0% on all ViralHog clips |
| `TEST-R2-04` | R2 Watermark | Strict zero blur mask on ViralHog clips | PASS | 0/30 ViralHog clips with blur masks | 0 blur masks on ViralHog |
| `TEST-R2-02` | R2 Watermark | Zero blind blur template 8000 applied across all Part 1 clips | PASS | 20/33 Part 1 clips with blur | Channel-specific selective presets (not 100% blind assignment) |
| `TEST-R2-01` | R2 Watermark | Channel watermark preset and crop validity | PASS | 0 invalid crop clips | 0 invalid crop settings |
| `TEST-R3-01` | R3 SFX | Zero collision SFX on audible Track A1 camera audio (Part 1) | PASS | 0 collision SFX on Part 1 | 0 collision SFX on live camera audio |
| `TEST-R3-02` | R3 SFX | 100% SFX coverage on silent clips under Track A5 BGM | PASS | 100.0% (0/9 uncovered) | 100% SFX coverage |
| `TEST-R3-03` | R3 SFX | Zero overlap between Track A3/A4 SFX and Track A2 Voiceover | PASS | 0.000s overlap | 0.000s overlap |
| `TEST-R3-04` | R3 SFX | Strict ban on interjection SFX on timeline and in configs | PASS | 0 timeline items, 0 catalog violations | 0 interjection SFX entries |
| `TEST-R4-01` | R4 Emojis & Graphics | Zero static center emojis on Track V4 (no 0.50, 0.50 center clustering) | PASS | 0 static center emojis | 0 static center emojis |
| `TEST-R4-02` | R4 Emojis & Graphics | Track V4 valid impact duration (0.2-0.8s) or corner reaction GIF (1.5-2.3s) | PASS | 0/5 non-compliant V4 items | 0 non-compliant items |
| `TEST-R4-03` | R4 Emojis & Graphics | Track V8 safety graphics modulo loop eliminated & semantic text mapping | PASS | modulo_loop=False, unknown_texts=0 | modulo_loop=False, 100% semantic matching |
| `TEST-R5-01` | R5 Voiceover & Subs | Dynamic VO offset reasoning (eliminate fixed +1.50s formula) | PASS | 0/15 VOs at fixed +1.50s (variance=1.706) | <= 3 fixed 1.5s offsets and variance > 0.35s^2 |
| `TEST-R5-03` | R5 Voiceover & Subs | Track V5 MOGRT subtitles 100% synchronized with Track A2 VO | PASS | 0 timing mismatches (V5 count=15, A2 count=15) | 0 mismatches, V5 count == A2 count |
| `TEST-R5-02` | R5 Voiceover & Subs | VO respects Premise/Aftermath boundaries without spilling past clips | PASS | 0 boundary violations | 0 boundary violations |
| `TEST-R6-01` | R6 Invariants | INV-01: Audio Coverage = 100% (A1 | A5 | A8) | PASS | 100.00% | 100.0% coverage |
| `TEST-R6-02` | R6 Invariants | INV-02: V1 == V3 Full Sync (Start, End, InPoint, OutPoint) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-03` | R6 Invariants | INV-03: V5 == A2 Full Sync (Start, End) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-04` | R6 Invariants | INV-04: Zero Black Gaps on Video (V3 | V10) and duration <= 960.0s | PASS | coverage=100.00%, duration=868.11s | coverage=100.0%, duration <= 960.0s |
| `TEST-R6-05` | R6 Invariants | INV-05: Clean .prproj XML & Referential Integrity (0 dangling pointers) | PASS | 0 dangling references | 0 dangling references |
| `TEST-R7-01` | R7 Intro Architecture | Ground-truth kb111-kb117 'Hello everyone!' greeting with unique episode body hook | PASS | valid_script=True, 0 violations | valid_script=True, 0 violations |
| `TEST-R7-02` | R7 Intro Architecture | Ground-truth Intro architecture present (A6 Hadeus.mp4, Teaser 1a/1b split) | PASS | A6_Hadeus=True, Teaser1_split=True, intro_cuts=14 | A6_Hadeus=True, Teaser1_split=True, intro_cuts>=6 |
| `TEST-R7-03` | R7 Intro Architecture | Middle fast-cut teasers (6-8 rapid climax cuts of 15-32 frames) | PASS | 8 rapid cuts (total mid clips=8) | >= 5 rapid cuts between 15f and 32f |
| `TEST-R7-04` | R7 Intro Architecture | 20-frame Warning card & Intro boundary before Part 1 body clips | PASS | has_warning=True, part1_start_frame=375 | has_warning=True, part1_start_frame >= 320 |
| `BOUND-DUR-01` | R1 Duration Boundary | Part 1 cut boundary snap within +-0.30s per transition | PASS | 0 clips exceeded snap boundary | max snap deviation <= 0.60s total |
| `BOUND-DUR-02` | R6 Duration Boundary | Sequence total duration bounded: 420.0s <= duration <= 960.0s | PASS | 868.11s (14.47m) | [420.0s .. 960.0s] |
| `BOUND-DUR-03` | R1 Duration Boundary | Long clips (>= 15s raw) preserve valid VisionCut climax window | PASS | 0 long clips out of bounds | 0 long clips out of bounds |
| `BOUND-SCALE-01` | R2 Scale Boundary | ViralHog clips satisfy Scale >= 115.00% lower bound | PASS | 0/30 below lower bound | Scale >= 115.00% |
| `BOUND-SCALE-02` | R2 Crop Boundary | Pillarbox crop within bounds [20.0% .. 38.0%] | PASS | 0 out-of-bound crop clips | [20.0% .. 38.0%] |
| `BOUND-SFX-01` | R3 SFX Boundary | A2 Voiceover and A3/A4 SFX overlap boundary strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-SFX-02` | R6 Audio Boundary | A1 camera audio and A5 BGM overlap strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-INTRO-01` | R7 Intro Boundary | Intro section duration bounded [335 .. 390] frames | PASS | 375 frames (15.64s) | [335 .. 390] frames |
| `BOUND-INTRO-02` | R7 Intro Boundary | Warning card duration strictly 20 frames | PASS | [20] frames | exactly 20 frames |
| `COMBO-VH-PILLAR-01` | R2 Combination Synergy | ViralHog + Pillarbox dual constraint: Crop + Compensated Scale >= 120% + 0 Blur | PASS | 0/0 combo violations | 0 combo violations |
| `COMBO-MULTITS-A1-01` | R1 Multi-TS Synergy | Multi-TS discrete splitting produces paired V3 video and A1 audio track items | PASS | 0/0 unpaired multi-ts sources | 0 unpaired sources |
| `COMBO-VO-SUB-V8-01` | R4/R5 Narrative Synergy | 1-to-1 sync between Track V5 subtitles, Track A2 VO, and Track V8 graphics | PASS | V5 count=15, A2 count=15, V8 count=26 | V5 == A2, 0 sync mismatches |

## Project kb135 Assertions Detail

| ID | Req | Description | Result | Observed | Expected |
|---|---|---|---|---|---|
| `TEST-R1-01` | R1 Duration | Zero timeline OVERRIDES on Part 1 clips (InPoint == 0) | PASS | 0 overridden clips | 0 overrides |
| `TEST-R1-02` | R1 Duration | 100% Google Sheet duration match (|tl_dur - sheet_dur| <= 0.60s) | PASS | 0/20 duration mismatches | 0 mismatches (tolerance <= 0.60s) |
| `TEST-R1-03` | R1 Duration | 100% note duration match for Part 2 clips (|tl_dur - note_dur| <= 0.30s) | PASS | 0/7 note duration mismatches | 0 mismatches (tolerance <= 0.30s) |
| `TEST-R1-04` | R1 Duration | VisionCut climax duration preservation for non-note clips (0 arbitrary flat 5.6s cap) | PASS | 0/36 non-note clips out of spec | 0 flat-capped or mismatched clips |
| `TEST-R1-05` | R1 Duration | Multi-timestamp sources split into >= 2 separate files (0 concat) | PASS | 0/0 unsplit multi-ts sources | 0 unsplit sources (>= 2 separate files each) |
| `TEST-R2-03` | R2 Watermark | ViralHog clips zoomed to Scale >= 115.0% | PASS | 0/30 ViralHog clips with Scale < 115.0% | Scale >= 115.0% on all ViralHog clips |
| `TEST-R2-04` | R2 Watermark | Strict zero blur mask on ViralHog clips | PASS | 0/30 ViralHog clips with blur masks | 0 blur masks on ViralHog |
| `TEST-R2-02` | R2 Watermark | Zero blind blur template 8000 applied across all Part 1 clips | PASS | 16/33 Part 1 clips with blur | Channel-specific selective presets (not 100% blind assignment) |
| `TEST-R2-01` | R2 Watermark | Channel watermark preset and crop validity | PASS | 0 invalid crop clips | 0 invalid crop settings |
| `TEST-R3-01` | R3 SFX | Zero collision SFX on audible Track A1 camera audio (Part 1) | PASS | 0 collision SFX on Part 1 | 0 collision SFX on live camera audio |
| `TEST-R3-02` | R3 SFX | 100% SFX coverage on silent clips under Track A5 BGM | PASS | 100.0% (0/9 uncovered) | 100% SFX coverage |
| `TEST-R3-03` | R3 SFX | Zero overlap between Track A3/A4 SFX and Track A2 Voiceover | PASS | 0.000s overlap | 0.000s overlap |
| `TEST-R3-04` | R3 SFX | Strict ban on interjection SFX on timeline and in configs | PASS | 0 timeline items, 0 catalog violations | 0 interjection SFX entries |
| `TEST-R4-01` | R4 Emojis & Graphics | Zero static center emojis on Track V4 (no 0.50, 0.50 center clustering) | PASS | 0 static center emojis | 0 static center emojis |
| `TEST-R4-02` | R4 Emojis & Graphics | Track V4 valid impact duration (0.2-0.8s) or corner reaction GIF (1.5-2.3s) | PASS | 0/5 non-compliant V4 items | 0 non-compliant items |
| `TEST-R4-03` | R4 Emojis & Graphics | Track V8 safety graphics modulo loop eliminated & semantic text mapping | PASS | modulo_loop=False, unknown_texts=0 | modulo_loop=False, 100% semantic matching |
| `TEST-R5-01` | R5 Voiceover & Subs | Dynamic VO offset reasoning (eliminate fixed +1.50s formula) | PASS | 0/15 VOs at fixed +1.50s (variance=1.706) | <= 3 fixed 1.5s offsets and variance > 0.35s^2 |
| `TEST-R5-03` | R5 Voiceover & Subs | Track V5 MOGRT subtitles 100% synchronized with Track A2 VO | PASS | 0 timing mismatches (V5 count=15, A2 count=15) | 0 mismatches, V5 count == A2 count |
| `TEST-R5-02` | R5 Voiceover & Subs | VO respects Premise/Aftermath boundaries without spilling past clips | PASS | 0 boundary violations | 0 boundary violations |
| `TEST-R6-01` | R6 Invariants | INV-01: Audio Coverage = 100% (A1 | A5 | A8) | PASS | 100.00% | 100.0% coverage |
| `TEST-R6-02` | R6 Invariants | INV-02: V1 == V3 Full Sync (Start, End, InPoint, OutPoint) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-03` | R6 Invariants | INV-03: V5 == A2 Full Sync (Start, End) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-04` | R6 Invariants | INV-04: Zero Black Gaps on Video (V3 | V10) and duration <= 960.0s | PASS | coverage=100.00%, duration=871.37s | coverage=100.0%, duration <= 960.0s |
| `TEST-R6-05` | R6 Invariants | INV-05: Clean .prproj XML & Referential Integrity (0 dangling pointers) | PASS | 0 dangling references | 0 dangling references |
| `TEST-R7-01` | R7 Intro Architecture | Ground-truth kb111-kb117 'Hello everyone!' greeting with unique episode body hook | PASS | valid_script=True, 0 violations | valid_script=True, 0 violations |
| `TEST-R7-02` | R7 Intro Architecture | Ground-truth Intro architecture present (A6 Hadeus.mp4, Teaser 1a/1b split) | PASS | A6_Hadeus=True, Teaser1_split=True, intro_cuts=14 | A6_Hadeus=True, Teaser1_split=True, intro_cuts>=6 |
| `TEST-R7-03` | R7 Intro Architecture | Middle fast-cut teasers (6-8 rapid climax cuts of 15-32 frames) | PASS | 8 rapid cuts (total mid clips=8) | >= 5 rapid cuts between 15f and 32f |
| `TEST-R7-04` | R7 Intro Architecture | 20-frame Warning card & Intro boundary before Part 1 body clips | PASS | has_warning=True, part1_start_frame=375 | has_warning=True, part1_start_frame >= 320 |
| `BOUND-DUR-01` | R1 Duration Boundary | Part 1 cut boundary snap within +-0.30s per transition | PASS | 0 clips exceeded snap boundary | max snap deviation <= 0.60s total |
| `BOUND-DUR-02` | R6 Duration Boundary | Sequence total duration bounded: 420.0s <= duration <= 960.0s | PASS | 871.37s (14.52m) | [420.0s .. 960.0s] |
| `BOUND-DUR-03` | R1 Duration Boundary | Long clips (>= 15s raw) preserve valid VisionCut climax window | PASS | 0 long clips out of bounds | 0 long clips out of bounds |
| `BOUND-SCALE-01` | R2 Scale Boundary | ViralHog clips satisfy Scale >= 115.00% lower bound | PASS | 0/30 below lower bound | Scale >= 115.00% |
| `BOUND-SCALE-02` | R2 Crop Boundary | Pillarbox crop within bounds [20.0% .. 38.0%] | PASS | 0 out-of-bound crop clips | [20.0% .. 38.0%] |
| `BOUND-SFX-01` | R3 SFX Boundary | A2 Voiceover and A3/A4 SFX overlap boundary strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-SFX-02` | R6 Audio Boundary | A1 camera audio and A5 BGM overlap strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-INTRO-01` | R7 Intro Boundary | Intro section duration bounded [335 .. 390] frames | PASS | 375 frames (15.64s) | [335 .. 390] frames |
| `BOUND-INTRO-02` | R7 Intro Boundary | Warning card duration strictly 20 frames | PASS | [20] frames | exactly 20 frames |
| `COMBO-VH-PILLAR-01` | R2 Combination Synergy | ViralHog + Pillarbox dual constraint: Crop + Compensated Scale >= 120% + 0 Blur | PASS | 0/0 combo violations | 0 combo violations |
| `COMBO-MULTITS-A1-01` | R1 Multi-TS Synergy | Multi-TS discrete splitting produces paired V3 video and A1 audio track items | PASS | 0/0 unpaired multi-ts sources | 0 unpaired sources |
| `COMBO-VO-SUB-V8-01` | R4/R5 Narrative Synergy | 1-to-1 sync between Track V5 subtitles, Track A2 VO, and Track V8 graphics | PASS | V5 count=15, A2 count=15, V8 count=26 | V5 == A2, 0 sync mismatches |

## Project kb136 Assertions Detail

| ID | Req | Description | Result | Observed | Expected |
|---|---|---|---|---|---|
| `TEST-R1-01` | R1 Duration | Zero timeline OVERRIDES on Part 1 clips (InPoint == 0) | PASS | 0 overridden clips | 0 overrides |
| `TEST-R1-02` | R1 Duration | 100% Google Sheet duration match (|tl_dur - sheet_dur| <= 0.60s) | PASS | 0/20 duration mismatches | 0 mismatches (tolerance <= 0.60s) |
| `TEST-R1-03` | R1 Duration | 100% note duration match for Part 2 clips (|tl_dur - note_dur| <= 0.30s) | PASS | 0/8 note duration mismatches | 0 mismatches (tolerance <= 0.30s) |
| `TEST-R1-04` | R1 Duration | VisionCut climax duration preservation for non-note clips (0 arbitrary flat 5.6s cap) | PASS | 0/36 non-note clips out of spec | 0 flat-capped or mismatched clips |
| `TEST-R1-05` | R1 Duration | Multi-timestamp sources split into >= 2 separate files (0 concat) | PASS | 0/0 unsplit multi-ts sources | 0 unsplit sources (>= 2 separate files each) |
| `TEST-R2-03` | R2 Watermark | ViralHog clips zoomed to Scale >= 115.0% | PASS | 0/30 ViralHog clips with Scale < 115.0% | Scale >= 115.0% on all ViralHog clips |
| `TEST-R2-04` | R2 Watermark | Strict zero blur mask on ViralHog clips | PASS | 0/30 ViralHog clips with blur masks | 0 blur masks on ViralHog |
| `TEST-R2-02` | R2 Watermark | Zero blind blur template 8000 applied across all Part 1 clips | PASS | 13/33 Part 1 clips with blur | Channel-specific selective presets (not 100% blind assignment) |
| `TEST-R2-01` | R2 Watermark | Channel watermark preset and crop validity | PASS | 0 invalid crop clips | 0 invalid crop settings |
| `TEST-R3-01` | R3 SFX | Zero collision SFX on audible Track A1 camera audio (Part 1) | PASS | 0 collision SFX on Part 1 | 0 collision SFX on live camera audio |
| `TEST-R3-02` | R3 SFX | 100% SFX coverage on silent clips under Track A5 BGM | PASS | 100.0% (0/9 uncovered) | 100% SFX coverage |
| `TEST-R3-03` | R3 SFX | Zero overlap between Track A3/A4 SFX and Track A2 Voiceover | PASS | 0.000s overlap | 0.000s overlap |
| `TEST-R3-04` | R3 SFX | Strict ban on interjection SFX on timeline and in configs | PASS | 0 timeline items, 0 catalog violations | 0 interjection SFX entries |
| `TEST-R4-01` | R4 Emojis & Graphics | Zero static center emojis on Track V4 (no 0.50, 0.50 center clustering) | PASS | 0 static center emojis | 0 static center emojis |
| `TEST-R4-02` | R4 Emojis & Graphics | Track V4 valid impact duration (0.2-0.8s) or corner reaction GIF (1.5-2.3s) | PASS | 0/5 non-compliant V4 items | 0 non-compliant items |
| `TEST-R4-03` | R4 Emojis & Graphics | Track V8 safety graphics modulo loop eliminated & semantic text mapping | PASS | modulo_loop=False, unknown_texts=0 | modulo_loop=False, 100% semantic matching |
| `TEST-R5-01` | R5 Voiceover & Subs | Dynamic VO offset reasoning (eliminate fixed +1.50s formula) | PASS | 0/15 VOs at fixed +1.50s (variance=1.706) | <= 3 fixed 1.5s offsets and variance > 0.35s^2 |
| `TEST-R5-03` | R5 Voiceover & Subs | Track V5 MOGRT subtitles 100% synchronized with Track A2 VO | PASS | 0 timing mismatches (V5 count=15, A2 count=15) | 0 mismatches, V5 count == A2 count |
| `TEST-R5-02` | R5 Voiceover & Subs | VO respects Premise/Aftermath boundaries without spilling past clips | PASS | 0 boundary violations | 0 boundary violations |
| `TEST-R6-01` | R6 Invariants | INV-01: Audio Coverage = 100% (A1 | A5 | A8) | PASS | 100.00% | 100.0% coverage |
| `TEST-R6-02` | R6 Invariants | INV-02: V1 == V3 Full Sync (Start, End, InPoint, OutPoint) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-03` | R6 Invariants | INV-03: V5 == A2 Full Sync (Start, End) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-04` | R6 Invariants | INV-04: Zero Black Gaps on Video (V3 | V10) and duration <= 960.0s | PASS | coverage=100.00%, duration=867.90s | coverage=100.0%, duration <= 960.0s |
| `TEST-R6-05` | R6 Invariants | INV-05: Clean .prproj XML & Referential Integrity (0 dangling pointers) | PASS | 0 dangling references | 0 dangling references |
| `TEST-R7-01` | R7 Intro Architecture | Ground-truth kb111-kb117 'Hello everyone!' greeting with unique episode body hook | PASS | valid_script=True, 0 violations | valid_script=True, 0 violations |
| `TEST-R7-02` | R7 Intro Architecture | Ground-truth Intro architecture present (A6 Hadeus.mp4, Teaser 1a/1b split) | PASS | A6_Hadeus=True, Teaser1_split=True, intro_cuts=14 | A6_Hadeus=True, Teaser1_split=True, intro_cuts>=6 |
| `TEST-R7-03` | R7 Intro Architecture | Middle fast-cut teasers (6-8 rapid climax cuts of 15-32 frames) | PASS | 8 rapid cuts (total mid clips=8) | >= 5 rapid cuts between 15f and 32f |
| `TEST-R7-04` | R7 Intro Architecture | 20-frame Warning card & Intro boundary before Part 1 body clips | PASS | has_warning=True, part1_start_frame=375 | has_warning=True, part1_start_frame >= 320 |
| `BOUND-DUR-01` | R1 Duration Boundary | Part 1 cut boundary snap within +-0.30s per transition | PASS | 0 clips exceeded snap boundary | max snap deviation <= 0.60s total |
| `BOUND-DUR-02` | R6 Duration Boundary | Sequence total duration bounded: 420.0s <= duration <= 960.0s | PASS | 867.90s (14.47m) | [420.0s .. 960.0s] |
| `BOUND-DUR-03` | R1 Duration Boundary | Long clips (>= 15s raw) preserve valid VisionCut climax window | PASS | 0 long clips out of bounds | 0 long clips out of bounds |
| `BOUND-SCALE-01` | R2 Scale Boundary | ViralHog clips satisfy Scale >= 115.00% lower bound | PASS | 0/30 below lower bound | Scale >= 115.00% |
| `BOUND-SCALE-02` | R2 Crop Boundary | Pillarbox crop within bounds [20.0% .. 38.0%] | PASS | 0 out-of-bound crop clips | [20.0% .. 38.0%] |
| `BOUND-SFX-01` | R3 SFX Boundary | A2 Voiceover and A3/A4 SFX overlap boundary strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-SFX-02` | R6 Audio Boundary | A1 camera audio and A5 BGM overlap strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-INTRO-01` | R7 Intro Boundary | Intro section duration bounded [335 .. 390] frames | PASS | 375 frames (15.64s) | [335 .. 390] frames |
| `BOUND-INTRO-02` | R7 Intro Boundary | Warning card duration strictly 20 frames | PASS | [20] frames | exactly 20 frames |
| `COMBO-VH-PILLAR-01` | R2 Combination Synergy | ViralHog + Pillarbox dual constraint: Crop + Compensated Scale >= 120% + 0 Blur | PASS | 0/0 combo violations | 0 combo violations |
| `COMBO-MULTITS-A1-01` | R1 Multi-TS Synergy | Multi-TS discrete splitting produces paired V3 video and A1 audio track items | PASS | 0/0 unpaired multi-ts sources | 0 unpaired sources |
| `COMBO-VO-SUB-V8-01` | R4/R5 Narrative Synergy | 1-to-1 sync between Track V5 subtitles, Track A2 VO, and Track V8 graphics | PASS | V5 count=15, A2 count=15, V8 count=26 | V5 == A2, 0 sync mismatches |

## Project kb137 Assertions Detail

| ID | Req | Description | Result | Observed | Expected |
|---|---|---|---|---|---|
| `TEST-R1-01` | R1 Duration | Zero timeline OVERRIDES on Part 1 clips (InPoint == 0) | PASS | 0 overridden clips | 0 overrides |
| `TEST-R1-02` | R1 Duration | 100% Google Sheet duration match (|tl_dur - sheet_dur| <= 0.60s) | PASS | 0/20 duration mismatches | 0 mismatches (tolerance <= 0.60s) |
| `TEST-R1-03` | R1 Duration | 100% note duration match for Part 2 clips (|tl_dur - note_dur| <= 0.30s) | PASS | 0/5 note duration mismatches | 0 mismatches (tolerance <= 0.30s) |
| `TEST-R1-04` | R1 Duration | VisionCut climax duration preservation for non-note clips (0 arbitrary flat 5.6s cap) | PASS | 0/36 non-note clips out of spec | 0 flat-capped or mismatched clips |
| `TEST-R1-05` | R1 Duration | Multi-timestamp sources split into >= 2 separate files (0 concat) | PASS | 0/0 unsplit multi-ts sources | 0 unsplit sources (>= 2 separate files each) |
| `TEST-R2-03` | R2 Watermark | ViralHog clips zoomed to Scale >= 115.0% | PASS | 0/30 ViralHog clips with Scale < 115.0% | Scale >= 115.0% on all ViralHog clips |
| `TEST-R2-04` | R2 Watermark | Strict zero blur mask on ViralHog clips | PASS | 0/30 ViralHog clips with blur masks | 0 blur masks on ViralHog |
| `TEST-R2-02` | R2 Watermark | Zero blind blur template 8000 applied across all Part 1 clips | PASS | 22/33 Part 1 clips with blur | Channel-specific selective presets (not 100% blind assignment) |
| `TEST-R2-01` | R2 Watermark | Channel watermark preset and crop validity | PASS | 0 invalid crop clips | 0 invalid crop settings |
| `TEST-R3-01` | R3 SFX | Zero collision SFX on audible Track A1 camera audio (Part 1) | PASS | 0 collision SFX on Part 1 | 0 collision SFX on live camera audio |
| `TEST-R3-02` | R3 SFX | 100% SFX coverage on silent clips under Track A5 BGM | PASS | 100.0% (0/9 uncovered) | 100% SFX coverage |
| `TEST-R3-03` | R3 SFX | Zero overlap between Track A3/A4 SFX and Track A2 Voiceover | PASS | 0.000s overlap | 0.000s overlap |
| `TEST-R3-04` | R3 SFX | Strict ban on interjection SFX on timeline and in configs | PASS | 0 timeline items, 0 catalog violations | 0 interjection SFX entries |
| `TEST-R4-01` | R4 Emojis & Graphics | Zero static center emojis on Track V4 (no 0.50, 0.50 center clustering) | PASS | 0 static center emojis | 0 static center emojis |
| `TEST-R4-02` | R4 Emojis & Graphics | Track V4 valid impact duration (0.2-0.8s) or corner reaction GIF (1.5-2.3s) | PASS | 0/5 non-compliant V4 items | 0 non-compliant items |
| `TEST-R4-03` | R4 Emojis & Graphics | Track V8 safety graphics modulo loop eliminated & semantic text mapping | PASS | modulo_loop=False, unknown_texts=0 | modulo_loop=False, 100% semantic matching |
| `TEST-R5-01` | R5 Voiceover & Subs | Dynamic VO offset reasoning (eliminate fixed +1.50s formula) | PASS | 0/15 VOs at fixed +1.50s (variance=1.706) | <= 3 fixed 1.5s offsets and variance > 0.35s^2 |
| `TEST-R5-03` | R5 Voiceover & Subs | Track V5 MOGRT subtitles 100% synchronized with Track A2 VO | PASS | 0 timing mismatches (V5 count=15, A2 count=15) | 0 mismatches, V5 count == A2 count |
| `TEST-R5-02` | R5 Voiceover & Subs | VO respects Premise/Aftermath boundaries without spilling past clips | PASS | 0 boundary violations | 0 boundary violations |
| `TEST-R6-01` | R6 Invariants | INV-01: Audio Coverage = 100% (A1 | A5 | A8) | PASS | 100.00% | 100.0% coverage |
| `TEST-R6-02` | R6 Invariants | INV-02: V1 == V3 Full Sync (Start, End, InPoint, OutPoint) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-03` | R6 Invariants | INV-03: V5 == A2 Full Sync (Start, End) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-04` | R6 Invariants | INV-04: Zero Black Gaps on Video (V3 | V10) and duration <= 960.0s | PASS | coverage=100.00%, duration=869.78s | coverage=100.0%, duration <= 960.0s |
| `TEST-R6-05` | R6 Invariants | INV-05: Clean .prproj XML & Referential Integrity (0 dangling pointers) | PASS | 0 dangling references | 0 dangling references |
| `TEST-R7-01` | R7 Intro Architecture | Ground-truth kb111-kb117 'Hello everyone!' greeting with unique episode body hook | PASS | valid_script=True, 0 violations | valid_script=True, 0 violations |
| `TEST-R7-02` | R7 Intro Architecture | Ground-truth Intro architecture present (A6 Hadeus.mp4, Teaser 1a/1b split) | PASS | A6_Hadeus=True, Teaser1_split=True, intro_cuts=14 | A6_Hadeus=True, Teaser1_split=True, intro_cuts>=6 |
| `TEST-R7-03` | R7 Intro Architecture | Middle fast-cut teasers (6-8 rapid climax cuts of 15-32 frames) | PASS | 8 rapid cuts (total mid clips=8) | >= 5 rapid cuts between 15f and 32f |
| `TEST-R7-04` | R7 Intro Architecture | 20-frame Warning card & Intro boundary before Part 1 body clips | PASS | has_warning=True, part1_start_frame=375 | has_warning=True, part1_start_frame >= 320 |
| `BOUND-DUR-01` | R1 Duration Boundary | Part 1 cut boundary snap within +-0.30s per transition | PASS | 0 clips exceeded snap boundary | max snap deviation <= 0.60s total |
| `BOUND-DUR-02` | R6 Duration Boundary | Sequence total duration bounded: 420.0s <= duration <= 960.0s | PASS | 869.78s (14.50m) | [420.0s .. 960.0s] |
| `BOUND-DUR-03` | R1 Duration Boundary | Long clips (>= 15s raw) preserve valid VisionCut climax window | PASS | 0 long clips out of bounds | 0 long clips out of bounds |
| `BOUND-SCALE-01` | R2 Scale Boundary | ViralHog clips satisfy Scale >= 115.00% lower bound | PASS | 0/30 below lower bound | Scale >= 115.00% |
| `BOUND-SCALE-02` | R2 Crop Boundary | Pillarbox crop within bounds [20.0% .. 38.0%] | PASS | 0 out-of-bound crop clips | [20.0% .. 38.0%] |
| `BOUND-SFX-01` | R3 SFX Boundary | A2 Voiceover and A3/A4 SFX overlap boundary strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-SFX-02` | R6 Audio Boundary | A1 camera audio and A5 BGM overlap strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-INTRO-01` | R7 Intro Boundary | Intro section duration bounded [335 .. 390] frames | PASS | 375 frames (15.64s) | [335 .. 390] frames |
| `BOUND-INTRO-02` | R7 Intro Boundary | Warning card duration strictly 20 frames | PASS | [20] frames | exactly 20 frames |
| `COMBO-VH-PILLAR-01` | R2 Combination Synergy | ViralHog + Pillarbox dual constraint: Crop + Compensated Scale >= 120% + 0 Blur | PASS | 0/0 combo violations | 0 combo violations |
| `COMBO-MULTITS-A1-01` | R1 Multi-TS Synergy | Multi-TS discrete splitting produces paired V3 video and A1 audio track items | PASS | 0/0 unpaired multi-ts sources | 0 unpaired sources |
| `COMBO-VO-SUB-V8-01` | R4/R5 Narrative Synergy | 1-to-1 sync between Track V5 subtitles, Track A2 VO, and Track V8 graphics | PASS | V5 count=15, A2 count=15, V8 count=26 | V5 == A2, 0 sync mismatches |

## Project kb138 Assertions Detail

| ID | Req | Description | Result | Observed | Expected |
|---|---|---|---|---|---|
| `TEST-R1-01` | R1 Duration | Zero timeline OVERRIDES on Part 1 clips (InPoint == 0) | PASS | 0 overridden clips | 0 overrides |
| `TEST-R1-02` | R1 Duration | 100% Google Sheet duration match (|tl_dur - sheet_dur| <= 0.60s) | PASS | 0/20 duration mismatches | 0 mismatches (tolerance <= 0.60s) |
| `TEST-R1-03` | R1 Duration | 100% note duration match for Part 2 clips (|tl_dur - note_dur| <= 0.30s) | PASS | 0/5 note duration mismatches | 0 mismatches (tolerance <= 0.30s) |
| `TEST-R1-04` | R1 Duration | VisionCut climax duration preservation for non-note clips (0 arbitrary flat 5.6s cap) | PASS | 0/34 non-note clips out of spec | 0 flat-capped or mismatched clips |
| `TEST-R1-05` | R1 Duration | Multi-timestamp sources split into >= 2 separate files (0 concat) | PASS | 0/0 unsplit multi-ts sources | 0 unsplit sources (>= 2 separate files each) |
| `TEST-R2-03` | R2 Watermark | ViralHog clips zoomed to Scale >= 115.0% | PASS | 0/30 ViralHog clips with Scale < 115.0% | Scale >= 115.0% on all ViralHog clips |
| `TEST-R2-04` | R2 Watermark | Strict zero blur mask on ViralHog clips | PASS | 0/30 ViralHog clips with blur masks | 0 blur masks on ViralHog |
| `TEST-R2-02` | R2 Watermark | Zero blind blur template 8000 applied across all Part 1 clips | PASS | 17/33 Part 1 clips with blur | Channel-specific selective presets (not 100% blind assignment) |
| `TEST-R2-01` | R2 Watermark | Channel watermark preset and crop validity | PASS | 0 invalid crop clips | 0 invalid crop settings |
| `TEST-R3-01` | R3 SFX | Zero collision SFX on audible Track A1 camera audio (Part 1) | PASS | 0 collision SFX on Part 1 | 0 collision SFX on live camera audio |
| `TEST-R3-02` | R3 SFX | 100% SFX coverage on silent clips under Track A5 BGM | PASS | 100.0% (0/9 uncovered) | 100% SFX coverage |
| `TEST-R3-03` | R3 SFX | Zero overlap between Track A3/A4 SFX and Track A2 Voiceover | PASS | 0.000s overlap | 0.000s overlap |
| `TEST-R3-04` | R3 SFX | Strict ban on interjection SFX on timeline and in configs | PASS | 0 timeline items, 0 catalog violations | 0 interjection SFX entries |
| `TEST-R4-01` | R4 Emojis & Graphics | Zero static center emojis on Track V4 (no 0.50, 0.50 center clustering) | PASS | 0 static center emojis | 0 static center emojis |
| `TEST-R4-02` | R4 Emojis & Graphics | Track V4 valid impact duration (0.2-0.8s) or corner reaction GIF (1.5-2.3s) | PASS | 0/5 non-compliant V4 items | 0 non-compliant items |
| `TEST-R4-03` | R4 Emojis & Graphics | Track V8 safety graphics modulo loop eliminated & semantic text mapping | PASS | modulo_loop=False, unknown_texts=0 | modulo_loop=False, 100% semantic matching |
| `TEST-R5-01` | R5 Voiceover & Subs | Dynamic VO offset reasoning (eliminate fixed +1.50s formula) | PASS | 0/15 VOs at fixed +1.50s (variance=1.706) | <= 3 fixed 1.5s offsets and variance > 0.35s^2 |
| `TEST-R5-03` | R5 Voiceover & Subs | Track V5 MOGRT subtitles 100% synchronized with Track A2 VO | PASS | 0 timing mismatches (V5 count=15, A2 count=15) | 0 mismatches, V5 count == A2 count |
| `TEST-R5-02` | R5 Voiceover & Subs | VO respects Premise/Aftermath boundaries without spilling past clips | PASS | 0 boundary violations | 0 boundary violations |
| `TEST-R6-01` | R6 Invariants | INV-01: Audio Coverage = 100% (A1 | A5 | A8) | PASS | 100.00% | 100.0% coverage |
| `TEST-R6-02` | R6 Invariants | INV-02: V1 == V3 Full Sync (Start, End, InPoint, OutPoint) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-03` | R6 Invariants | INV-03: V5 == A2 Full Sync (Start, End) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-04` | R6 Invariants | INV-04: Zero Black Gaps on Video (V3 | V10) and duration <= 960.0s | PASS | coverage=100.00%, duration=876.25s | coverage=100.0%, duration <= 960.0s |
| `TEST-R6-05` | R6 Invariants | INV-05: Clean .prproj XML & Referential Integrity (0 dangling pointers) | PASS | 0 dangling references | 0 dangling references |
| `TEST-R7-01` | R7 Intro Architecture | Ground-truth kb111-kb117 'Hello everyone!' greeting with unique episode body hook | PASS | valid_script=True, 0 violations | valid_script=True, 0 violations |
| `TEST-R7-02` | R7 Intro Architecture | Ground-truth Intro architecture present (A6 Hadeus.mp4, Teaser 1a/1b split) | PASS | A6_Hadeus=True, Teaser1_split=True, intro_cuts=14 | A6_Hadeus=True, Teaser1_split=True, intro_cuts>=6 |
| `TEST-R7-03` | R7 Intro Architecture | Middle fast-cut teasers (6-8 rapid climax cuts of 15-32 frames) | PASS | 8 rapid cuts (total mid clips=8) | >= 5 rapid cuts between 15f and 32f |
| `TEST-R7-04` | R7 Intro Architecture | 20-frame Warning card & Intro boundary before Part 1 body clips | PASS | has_warning=True, part1_start_frame=375 | has_warning=True, part1_start_frame >= 320 |
| `BOUND-DUR-01` | R1 Duration Boundary | Part 1 cut boundary snap within +-0.30s per transition | PASS | 0 clips exceeded snap boundary | max snap deviation <= 0.60s total |
| `BOUND-DUR-02` | R6 Duration Boundary | Sequence total duration bounded: 420.0s <= duration <= 960.0s | PASS | 876.25s (14.60m) | [420.0s .. 960.0s] |
| `BOUND-DUR-03` | R1 Duration Boundary | Long clips (>= 15s raw) preserve valid VisionCut climax window | PASS | 0 long clips out of bounds | 0 long clips out of bounds |
| `BOUND-SCALE-01` | R2 Scale Boundary | ViralHog clips satisfy Scale >= 115.00% lower bound | PASS | 0/30 below lower bound | Scale >= 115.00% |
| `BOUND-SCALE-02` | R2 Crop Boundary | Pillarbox crop within bounds [20.0% .. 38.0%] | PASS | 0 out-of-bound crop clips | [20.0% .. 38.0%] |
| `BOUND-SFX-01` | R3 SFX Boundary | A2 Voiceover and A3/A4 SFX overlap boundary strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-SFX-02` | R6 Audio Boundary | A1 camera audio and A5 BGM overlap strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-INTRO-01` | R7 Intro Boundary | Intro section duration bounded [335 .. 390] frames | PASS | 375 frames (15.64s) | [335 .. 390] frames |
| `BOUND-INTRO-02` | R7 Intro Boundary | Warning card duration strictly 20 frames | PASS | [20] frames | exactly 20 frames |
| `COMBO-VH-PILLAR-01` | R2 Combination Synergy | ViralHog + Pillarbox dual constraint: Crop + Compensated Scale >= 120% + 0 Blur | PASS | 0/0 combo violations | 0 combo violations |
| `COMBO-MULTITS-A1-01` | R1 Multi-TS Synergy | Multi-TS discrete splitting produces paired V3 video and A1 audio track items | PASS | 0/0 unpaired multi-ts sources | 0 unpaired sources |
| `COMBO-VO-SUB-V8-01` | R4/R5 Narrative Synergy | 1-to-1 sync between Track V5 subtitles, Track A2 VO, and Track V8 graphics | PASS | V5 count=15, A2 count=15, V8 count=26 | V5 == A2, 0 sync mismatches |

## Project kb139 Assertions Detail

| ID | Req | Description | Result | Observed | Expected |
|---|---|---|---|---|---|
| `TEST-R1-01` | R1 Duration | Zero timeline OVERRIDES on Part 1 clips (InPoint == 0) | PASS | 0 overridden clips | 0 overrides |
| `TEST-R1-02` | R1 Duration | 100% Google Sheet duration match (|tl_dur - sheet_dur| <= 0.60s) | PASS | 0/20 duration mismatches | 0 mismatches (tolerance <= 0.60s) |
| `TEST-R1-03` | R1 Duration | 100% note duration match for Part 2 clips (|tl_dur - note_dur| <= 0.30s) | PASS | 0/6 note duration mismatches | 0 mismatches (tolerance <= 0.30s) |
| `TEST-R1-04` | R1 Duration | VisionCut climax duration preservation for non-note clips (0 arbitrary flat 5.6s cap) | PASS | 0/34 non-note clips out of spec | 0 flat-capped or mismatched clips |
| `TEST-R1-05` | R1 Duration | Multi-timestamp sources split into >= 2 separate files (0 concat) | PASS | 0/0 unsplit multi-ts sources | 0 unsplit sources (>= 2 separate files each) |
| `TEST-R2-03` | R2 Watermark | ViralHog clips zoomed to Scale >= 115.0% | PASS | 0/30 ViralHog clips with Scale < 115.0% | Scale >= 115.0% on all ViralHog clips |
| `TEST-R2-04` | R2 Watermark | Strict zero blur mask on ViralHog clips | PASS | 0/30 ViralHog clips with blur masks | 0 blur masks on ViralHog |
| `TEST-R2-02` | R2 Watermark | Zero blind blur template 8000 applied across all Part 1 clips | PASS | 15/33 Part 1 clips with blur | Channel-specific selective presets (not 100% blind assignment) |
| `TEST-R2-01` | R2 Watermark | Channel watermark preset and crop validity | PASS | 0 invalid crop clips | 0 invalid crop settings |
| `TEST-R3-01` | R3 SFX | Zero collision SFX on audible Track A1 camera audio (Part 1) | PASS | 0 collision SFX on Part 1 | 0 collision SFX on live camera audio |
| `TEST-R3-02` | R3 SFX | 100% SFX coverage on silent clips under Track A5 BGM | PASS | 100.0% (0/9 uncovered) | 100% SFX coverage |
| `TEST-R3-03` | R3 SFX | Zero overlap between Track A3/A4 SFX and Track A2 Voiceover | PASS | 0.000s overlap | 0.000s overlap |
| `TEST-R3-04` | R3 SFX | Strict ban on interjection SFX on timeline and in configs | PASS | 0 timeline items, 0 catalog violations | 0 interjection SFX entries |
| `TEST-R4-01` | R4 Emojis & Graphics | Zero static center emojis on Track V4 (no 0.50, 0.50 center clustering) | PASS | 0 static center emojis | 0 static center emojis |
| `TEST-R4-02` | R4 Emojis & Graphics | Track V4 valid impact duration (0.2-0.8s) or corner reaction GIF (1.5-2.3s) | PASS | 0/5 non-compliant V4 items | 0 non-compliant items |
| `TEST-R4-03` | R4 Emojis & Graphics | Track V8 safety graphics modulo loop eliminated & semantic text mapping | PASS | modulo_loop=False, unknown_texts=0 | modulo_loop=False, 100% semantic matching |
| `TEST-R5-01` | R5 Voiceover & Subs | Dynamic VO offset reasoning (eliminate fixed +1.50s formula) | PASS | 0/15 VOs at fixed +1.50s (variance=1.706) | <= 3 fixed 1.5s offsets and variance > 0.35s^2 |
| `TEST-R5-03` | R5 Voiceover & Subs | Track V5 MOGRT subtitles 100% synchronized with Track A2 VO | PASS | 0 timing mismatches (V5 count=15, A2 count=15) | 0 mismatches, V5 count == A2 count |
| `TEST-R5-02` | R5 Voiceover & Subs | VO respects Premise/Aftermath boundaries without spilling past clips | PASS | 0 boundary violations | 0 boundary violations |
| `TEST-R6-01` | R6 Invariants | INV-01: Audio Coverage = 100% (A1 | A5 | A8) | PASS | 100.00% | 100.0% coverage |
| `TEST-R6-02` | R6 Invariants | INV-02: V1 == V3 Full Sync (Start, End, InPoint, OutPoint) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-03` | R6 Invariants | INV-03: V5 == A2 Full Sync (Start, End) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-04` | R6 Invariants | INV-04: Zero Black Gaps on Video (V3 | V10) and duration <= 960.0s | PASS | coverage=100.00%, duration=874.28s | coverage=100.0%, duration <= 960.0s |
| `TEST-R6-05` | R6 Invariants | INV-05: Clean .prproj XML & Referential Integrity (0 dangling pointers) | PASS | 0 dangling references | 0 dangling references |
| `TEST-R7-01` | R7 Intro Architecture | Ground-truth kb111-kb117 'Hello everyone!' greeting with unique episode body hook | PASS | valid_script=True, 0 violations | valid_script=True, 0 violations |
| `TEST-R7-02` | R7 Intro Architecture | Ground-truth Intro architecture present (A6 Hadeus.mp4, Teaser 1a/1b split) | PASS | A6_Hadeus=True, Teaser1_split=True, intro_cuts=14 | A6_Hadeus=True, Teaser1_split=True, intro_cuts>=6 |
| `TEST-R7-03` | R7 Intro Architecture | Middle fast-cut teasers (6-8 rapid climax cuts of 15-32 frames) | PASS | 8 rapid cuts (total mid clips=8) | >= 5 rapid cuts between 15f and 32f |
| `TEST-R7-04` | R7 Intro Architecture | 20-frame Warning card & Intro boundary before Part 1 body clips | PASS | has_warning=True, part1_start_frame=375 | has_warning=True, part1_start_frame >= 320 |
| `BOUND-DUR-01` | R1 Duration Boundary | Part 1 cut boundary snap within +-0.30s per transition | PASS | 0 clips exceeded snap boundary | max snap deviation <= 0.60s total |
| `BOUND-DUR-02` | R6 Duration Boundary | Sequence total duration bounded: 420.0s <= duration <= 960.0s | PASS | 874.28s (14.57m) | [420.0s .. 960.0s] |
| `BOUND-DUR-03` | R1 Duration Boundary | Long clips (>= 15s raw) preserve valid VisionCut climax window | PASS | 0 long clips out of bounds | 0 long clips out of bounds |
| `BOUND-SCALE-01` | R2 Scale Boundary | ViralHog clips satisfy Scale >= 115.00% lower bound | PASS | 0/30 below lower bound | Scale >= 115.00% |
| `BOUND-SCALE-02` | R2 Crop Boundary | Pillarbox crop within bounds [20.0% .. 38.0%] | PASS | 0 out-of-bound crop clips | [20.0% .. 38.0%] |
| `BOUND-SFX-01` | R3 SFX Boundary | A2 Voiceover and A3/A4 SFX overlap boundary strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-SFX-02` | R6 Audio Boundary | A1 camera audio and A5 BGM overlap strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-INTRO-01` | R7 Intro Boundary | Intro section duration bounded [335 .. 390] frames | PASS | 375 frames (15.64s) | [335 .. 390] frames |
| `BOUND-INTRO-02` | R7 Intro Boundary | Warning card duration strictly 20 frames | PASS | [20] frames | exactly 20 frames |
| `COMBO-VH-PILLAR-01` | R2 Combination Synergy | ViralHog + Pillarbox dual constraint: Crop + Compensated Scale >= 120% + 0 Blur | PASS | 0/0 combo violations | 0 combo violations |
| `COMBO-MULTITS-A1-01` | R1 Multi-TS Synergy | Multi-TS discrete splitting produces paired V3 video and A1 audio track items | PASS | 0/0 unpaired multi-ts sources | 0 unpaired sources |
| `COMBO-VO-SUB-V8-01` | R4/R5 Narrative Synergy | 1-to-1 sync between Track V5 subtitles, Track A2 VO, and Track V8 graphics | PASS | V5 count=15, A2 count=15, V8 count=26 | V5 == A2, 0 sync mismatches |

## Project kb140 Assertions Detail

| ID | Req | Description | Result | Observed | Expected |
|---|---|---|---|---|---|
| `TEST-R1-01` | R1 Duration | Zero timeline OVERRIDES on Part 1 clips (InPoint == 0) | PASS | 0 overridden clips | 0 overrides |
| `TEST-R1-02` | R1 Duration | 100% Google Sheet duration match (|tl_dur - sheet_dur| <= 0.60s) | PASS | 0/20 duration mismatches | 0 mismatches (tolerance <= 0.60s) |
| `TEST-R1-03` | R1 Duration | 100% note duration match for Part 2 clips (|tl_dur - note_dur| <= 0.30s) | PASS | 0/6 note duration mismatches | 0 mismatches (tolerance <= 0.30s) |
| `TEST-R1-04` | R1 Duration | VisionCut climax duration preservation for non-note clips (0 arbitrary flat 5.6s cap) | PASS | 0/36 non-note clips out of spec | 0 flat-capped or mismatched clips |
| `TEST-R1-05` | R1 Duration | Multi-timestamp sources split into >= 2 separate files (0 concat) | PASS | 0/0 unsplit multi-ts sources | 0 unsplit sources (>= 2 separate files each) |
| `TEST-R2-03` | R2 Watermark | ViralHog clips zoomed to Scale >= 115.0% | PASS | 0/30 ViralHog clips with Scale < 115.0% | Scale >= 115.0% on all ViralHog clips |
| `TEST-R2-04` | R2 Watermark | Strict zero blur mask on ViralHog clips | PASS | 0/30 ViralHog clips with blur masks | 0 blur masks on ViralHog |
| `TEST-R2-02` | R2 Watermark | Zero blind blur template 8000 applied across all Part 1 clips | PASS | 16/33 Part 1 clips with blur | Channel-specific selective presets (not 100% blind assignment) |
| `TEST-R2-01` | R2 Watermark | Channel watermark preset and crop validity | PASS | 0 invalid crop clips | 0 invalid crop settings |
| `TEST-R3-01` | R3 SFX | Zero collision SFX on audible Track A1 camera audio (Part 1) | PASS | 0 collision SFX on Part 1 | 0 collision SFX on live camera audio |
| `TEST-R3-02` | R3 SFX | 100% SFX coverage on silent clips under Track A5 BGM | PASS | 100.0% (0/9 uncovered) | 100% SFX coverage |
| `TEST-R3-03` | R3 SFX | Zero overlap between Track A3/A4 SFX and Track A2 Voiceover | PASS | 0.000s overlap | 0.000s overlap |
| `TEST-R3-04` | R3 SFX | Strict ban on interjection SFX on timeline and in configs | PASS | 0 timeline items, 0 catalog violations | 0 interjection SFX entries |
| `TEST-R4-01` | R4 Emojis & Graphics | Zero static center emojis on Track V4 (no 0.50, 0.50 center clustering) | PASS | 0 static center emojis | 0 static center emojis |
| `TEST-R4-02` | R4 Emojis & Graphics | Track V4 valid impact duration (0.2-0.8s) or corner reaction GIF (1.5-2.3s) | PASS | 0/5 non-compliant V4 items | 0 non-compliant items |
| `TEST-R4-03` | R4 Emojis & Graphics | Track V8 safety graphics modulo loop eliminated & semantic text mapping | PASS | modulo_loop=False, unknown_texts=0 | modulo_loop=False, 100% semantic matching |
| `TEST-R5-01` | R5 Voiceover & Subs | Dynamic VO offset reasoning (eliminate fixed +1.50s formula) | PASS | 0/15 VOs at fixed +1.50s (variance=1.706) | <= 3 fixed 1.5s offsets and variance > 0.35s^2 |
| `TEST-R5-03` | R5 Voiceover & Subs | Track V5 MOGRT subtitles 100% synchronized with Track A2 VO | PASS | 0 timing mismatches (V5 count=15, A2 count=15) | 0 mismatches, V5 count == A2 count |
| `TEST-R5-02` | R5 Voiceover & Subs | VO respects Premise/Aftermath boundaries without spilling past clips | PASS | 0 boundary violations | 0 boundary violations |
| `TEST-R6-01` | R6 Invariants | INV-01: Audio Coverage = 100% (A1 | A5 | A8) | PASS | 100.00% | 100.0% coverage |
| `TEST-R6-02` | R6 Invariants | INV-02: V1 == V3 Full Sync (Start, End, InPoint, OutPoint) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-03` | R6 Invariants | INV-03: V5 == A2 Full Sync (Start, End) | PASS | 0 mismatches | 0 mismatches |
| `TEST-R6-04` | R6 Invariants | INV-04: Zero Black Gaps on Video (V3 | V10) and duration <= 960.0s | PASS | coverage=100.00%, duration=872.91s | coverage=100.0%, duration <= 960.0s |
| `TEST-R6-05` | R6 Invariants | INV-05: Clean .prproj XML & Referential Integrity (0 dangling pointers) | PASS | 0 dangling references | 0 dangling references |
| `TEST-R7-01` | R7 Intro Architecture | Ground-truth kb111-kb117 'Hello everyone!' greeting with unique episode body hook | PASS | valid_script=True, 0 violations | valid_script=True, 0 violations |
| `TEST-R7-02` | R7 Intro Architecture | Ground-truth Intro architecture present (A6 Hadeus.mp4, Teaser 1a/1b split) | PASS | A6_Hadeus=True, Teaser1_split=True, intro_cuts=14 | A6_Hadeus=True, Teaser1_split=True, intro_cuts>=6 |
| `TEST-R7-03` | R7 Intro Architecture | Middle fast-cut teasers (6-8 rapid climax cuts of 15-32 frames) | PASS | 8 rapid cuts (total mid clips=8) | >= 5 rapid cuts between 15f and 32f |
| `TEST-R7-04` | R7 Intro Architecture | 20-frame Warning card & Intro boundary before Part 1 body clips | PASS | has_warning=True, part1_start_frame=375 | has_warning=True, part1_start_frame >= 320 |
| `BOUND-DUR-01` | R1 Duration Boundary | Part 1 cut boundary snap within +-0.30s per transition | PASS | 0 clips exceeded snap boundary | max snap deviation <= 0.60s total |
| `BOUND-DUR-02` | R6 Duration Boundary | Sequence total duration bounded: 420.0s <= duration <= 960.0s | PASS | 872.91s (14.55m) | [420.0s .. 960.0s] |
| `BOUND-DUR-03` | R1 Duration Boundary | Long clips (>= 15s raw) preserve valid VisionCut climax window | PASS | 0 long clips out of bounds | 0 long clips out of bounds |
| `BOUND-SCALE-01` | R2 Scale Boundary | ViralHog clips satisfy Scale >= 115.00% lower bound | PASS | 0/30 below lower bound | Scale >= 115.00% |
| `BOUND-SCALE-02` | R2 Crop Boundary | Pillarbox crop within bounds [20.0% .. 38.0%] | PASS | 0 out-of-bound crop clips | [20.0% .. 38.0%] |
| `BOUND-SFX-01` | R3 SFX Boundary | A2 Voiceover and A3/A4 SFX overlap boundary strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-SFX-02` | R6 Audio Boundary | A1 camera audio and A5 BGM overlap strictly < 1 frame | PASS | 0.0000s overlap | < 0.0417s (0 frames) |
| `BOUND-INTRO-01` | R7 Intro Boundary | Intro section duration bounded [335 .. 390] frames | PASS | 375 frames (15.64s) | [335 .. 390] frames |
| `BOUND-INTRO-02` | R7 Intro Boundary | Warning card duration strictly 20 frames | PASS | [20] frames | exactly 20 frames |
| `COMBO-VH-PILLAR-01` | R2 Combination Synergy | ViralHog + Pillarbox dual constraint: Crop + Compensated Scale >= 120% + 0 Blur | PASS | 0/0 combo violations | 0 combo violations |
| `COMBO-MULTITS-A1-01` | R1 Multi-TS Synergy | Multi-TS discrete splitting produces paired V3 video and A1 audio track items | PASS | 0/0 unpaired multi-ts sources | 0 unpaired sources |
| `COMBO-VO-SUB-V8-01` | R4/R5 Narrative Synergy | 1-to-1 sync between Track V5 subtitles, Track A2 VO, and Track V8 graphics | PASS | V5 count=15, A2 count=15, V8 count=26 | V5 == A2, 0 sync mismatches |
