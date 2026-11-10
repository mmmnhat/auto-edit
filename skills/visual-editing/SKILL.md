---
name: visual-editing
description: Visual treatments, punch-in zooms, speed ramping, ViralHog zoom-only watermark removal, channel-specific blur masks, Track V4 keyframed impact emojis / corner reaction GIFs, and Track V8 semantic safety disclaimers. Manages Track V1/V3 clips, Track V2 adjustment layers, Track V4 emojis, and Track V8 graphics.
---

# Visual Editing (`visual-editing`)

Applies optical enhancements and shielding treatments to maintain visual engagement and content compliance.

## 🎯 Directives
- **Action Peak Punch-In:**
  - Keyframes subtle zooms (1.10x–1.20x scale) around the action climax (`mapped_climax_frame - 0.5s` to `mapped_climax_frame + 0.3s`).
  - Anchor point focused on the point of impact or subject face.
- **Content Shielding (Watermarks, Logos, Sensitive Content) & `R2` Channel Rules:**
  - Uses OpenCV KCF/CSRT tracking to track moving ROIs.
  - Headless mode: Renders via FFmpeg `delogo` or `boxblur`.
  - Premiere Pro mode: Places an Adjustment Layer or cropped shield clip on Track `V2` (or Masked `AE.Impact_Blur_FX` on `V3`) with Gaussian Blur and keyframed motion.
  - **ViralHog Asymmetric Zoom-Only Reframing (`R2`, `0` Blur):** Every `ViralHog` clip MUST push both the top `ViralHog` logo AND any secondary bottom timestamp/caption (`0 KM/H`, `ring.com`, `2017/03/26`) outside the `1920x1080` frame using **`Scale` $\ge 115.0\% .. 155.0\%$** (standard `120.0%`; if combined with Pillarbox `AECrop`, compensated `Scale` MUST stay $\ge 120.0\%$ per `COMBO-VH-PILLAR-01`) with **STRICT ZERO (`0`) Blur Masks**. Use the exact vertical projection $Y(u) = p_y + S(u - 0.5)$ (visible source span `[0.5 - p_y/S .. 0.5 + (1 - p_y)/S]`, keeping $1 - 0.5S \le p_y \le 0.5S$ so zero black bars appear).
  - **Anti-Erosion Custom Rectangular Masks, `HEAD/MID/TAIL` Caption Check & Sub-Pixel Pillarbox `AECrop` (`R2`):**
    - Never blindly apply template `8000` blur across all Part 1 `itv.kb*` clips. Measure exact sidebar boundaries (`[20.0% .. 38.0%]`, e.g., `22.2%` wide FailArmy/VH pillarboxes up to `34.7%` narrow `9:16`) for `AE.ADBE AECrop` (`Left`/`Right`), and **never** apply pillarbox `AECrop` to mixed-aspect compilation clips that cut mid-clip to full `16:9` action.
    - Inspect **`HEAD`, `MID`, `76% Post-Impact`, and `TAIL`** frames of every clip via `locate_anything_engine.py --task scan-all-sources --kb <kb>` + `read_file` so temporary mid-clip disclaimers (`3.7s..4.2s`), post-impact laugh captions (`"HAHAHAHA"`, `"HOHOHO!!!"`), opposite-corner `LA` logos, and multi-word bottom watermarks (`"Funny Animals Pets"`) are never missed, while simultaneously stripping **False Positive** masks (such as blurring indoor objects inside `AECrop` columns or empty corners).
    - Build tight custom `[(x1, y1, x2, y2), ...]` `AE.Impact_Blur_FX` `Mask2` rectangles calibrated by `LocateAnything-3B` OCR bounds with anti-erosion strength (**`Amount = 15, Thickness = 15, Feather = 22.0, Expansion = 12.0`**) so feathered edges stay opaque over white/neon glyphs, while keeping `[x1 .. x2]` strictly inside `[crop_pct .. 1 - crop_pct]` so blur never spills onto subjects' faces. For 2-line `ViralHog + ring.com` watermarks extending to `y = 0.115`, use `(128.0, 0.500, 0.485)` (`u_top = 0.121 > 0.115`, `u_bot = 0.902 < 0.95`).
- **Animated Emoji Impact Shields (`Track V4` in ITV 10-Track Template, `R4`):**
  - Covers strong physical impacts (`🙈` `512 (1).gif` for groin/crotch hits or explicit `"che"` censor notes, `😵‍💫` `mnhat_emoji_37.gif` for direct head/face hits, `💥` `512 (4).gif` for heavy slams/explosions, `💨⭐` `512 (7).gif` for chaotic tumbles, `😹` `512 (6).gif` / `🐱` `512 (5).gif` for slapstick slips).
  - **Human-Proportioned Scale (`17%–24%`) & Lead-In Window (`kb123` Standard):** Native `512x512` GIFs at `34%–42%` overwhelm medium/wide subjects. Size impact emojis proportionally to the hit body part at **`Scale = 17.0% – 24.0%`** (`25%–30%` max only for close-up foreground censor shields), starting `1–2 frames` (`~0.04s–0.08s`) before contact and lasting **`6–10 frames` (`0.25s–0.42s`**, safely within `TEST-R4-02` `[0.18s..0.85s]`).
  - **Zero Static Center `(0.50, 0.50)` Rule (`R4`):** Never leave Track V4 items with `<DefaultMotion>true</DefaultMotion>` or clustered inside `(0.50 ± 0.05, 0.50 ± 0.05)`. Every V4 item must either be a keyframed impact/censor shield (`0.20s–0.80s`) with an explicit `AE.ADBE Motion` component or a corner reaction GIF (`1.50s–2.30s` at bottom-left/bottom-right `x <= 0.30` or `x >= 0.70`, `y >= 0.65`).
  - **Dense Frame-by-Frame Keyframing (`10 Keyframes / 9-Frame Clip`) & Premiere Decoder Ground-Truth Grid Calibration:**
    - OpenCV `CAP_PROP_POS_MSEC` on VFR/CCTV clips can drift by `1–3 frames` (`0.04s–0.12s`) relative to Premiere Pro's media decoder, and 4 sparse keyframes lag behind fast nonlinear falls.
    - Always set Emoji `InPoint = 0`, write **dense 1-keyframe-per-frame trajectories** (`N + 1` keyframes at `k * 10594584000` ticks on `AE.ADBE Motion -> Position`, e.g., `10` keyframes for a `9`-frame `0.375s` clip), calibrate normalized `(x, y)` coordinates directly on **Premiere Pro exported frames (`premiere-pro:export_frame`) overlaid with a `0.02`-step coordinate grid**, and verify via strictly sequential (`1` call/turn) `export_frame` + `read_file`.
- **Semantic Safety Context Graphics (`Track V8` in ITV 10-Track Template, `R4`):**
  - Eliminate the hardcoded `index % 4 == 1` modulo loop (`safety_context_graphics_policy`). Place safety disclaimers at bottom-left `[0.015625, 0.972222]` only on genuine accident/stunt clips and match the subject semantically (`*HE'S FINE` -> single male, `*SHE'S FINE` -> single female, `*EVERYONE IS SAFE` / `*ALL SAFE` -> 2+ people, `*DON'T TRY THIS` -> dangerous stunt/tool, `*ALL GOOD` -> general tumble).
- **Subject Preservation:**
  - Never crop out the primary subject or essential reaction during reframing.
