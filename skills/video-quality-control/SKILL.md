---
name: video-quality-control
description: Closed-loop QA and evaluation harness runner. Audits the 5 Timeline Invariants and the 40-assertion ITV E2E test suite (R1-R7), generates atomic micro-patch plans, and enforces the 3-cycle circuit breaker.
---

# Video Quality Control (`video-quality-control`)

Audits the assembled sequence using `HarnessEvaluator` and `e:\ITV\tests\run_e2e_tests.py`, and orchestrates self-healing repairs.

## 🎯 Directives
- **Audit Against the 5 Invariants:**
  1. `INV-01 (Zero Gaps on V1 / V3 | V10 & 100% Audio Coverage)`: Ripple-deletes black gaps and ensures `Coverage(A1 | A5 | A8) = 100.00%` with `0.000s` overlap between `A1` and `A5`.
  2. `INV-02 (SFX Sync <= 1 frame & V1 == V3 Full Sync)`: Moves misaligned SFX clips on A4 and ensures 100% sync (`Start`, `End`, `InPoint`, `OutPoint`) between `V1` and `V3`.
  3. `INV-03 (Headroom <= -1.0 dBFS & V5 == A2 Full Sync)`: Attenuates master audio to prevent clipping and verifies 100% sync (`Start`, `End`) between `Track V5` MOGRT subtitles and `Track A2` Voiceover.
  4. `INV-04 (Voiceover Track A2 Protection)`: Ensures `0.000s` overlap between `Track A3`/`A4` SFX and `Track A2` Voiceover.
  5. `INV-05 (Payoff Window >= 0.8s & Clean .prproj Referential Integrity)`: Preserves reaction tails and verifies `0` dangling `ObjectRef`/`ObjectURef` pointers in `.prproj` XML.
- **ITV E2E Automated Test Suite (`40 Assertions / Project` in `< 0.9s`):**
  - Run `python "e:\ITV\tests\run_e2e_tests.py" --mode strict` to validate `R1` (100% Sheet/note/raw durations & discrete splitting for $\ge 2$ timestamps), `R2` (ViralHog `Scale >= 115%` + `0` blur masks & channel presets), `R3` (ban on `interjection` SFX & 100% silent-clip SFX coverage), `R4` (keyframed `V4` emojis & semantic `V8` safety disclaimers), `R5` (ElevenLabs `ITV 5` `eleven_v3` & dynamic `Premise`/`Aftermath` VO offsets), `R6` (5 Timeline Invariants), and `R7` (3-tier Intro `0..350f` & ban on `"HELLOOOO, EVERYONE!"`).
- **Micro-Patch Generation:**
  - Emits `state/patch-plan.json` containing atomic corrective actions.
  - Passes patch plan to `premiere-execution` for single-batch application.
- **Circuit Breaker Policy:**
  - Maximum repair cycles: 3.
  - If invariants fail on cycle 3:
    1. Soft rollback to pre-fix sequence checkpoint.
    2. Plant Red sequence markers (`[QA_FAIL]`) at problem frame positions.
    3. Capture review frame (`capture_frame`) and present in chat for editor intervention.
- **Final Visual Verification:**
  - Export sequence review frames (`export_sequence_review_frames`) and verify visual integrity with AI Vision (`view_file`).
