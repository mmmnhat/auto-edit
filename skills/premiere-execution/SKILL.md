---
name: premiere-execution
description: Adobe Premiere Pro MCP execution engine. Translates edit and patch plans into verified ExtendScript/UXP mutations. Manages checkpoints, timebases, and tracks.
---

# Premiere Execution (`premiere-execution`)

Translates abstract editorial plans (`edit-plan.json` and `patch-plan.json`) into concrete Adobe Premiere Pro MCP tool calls.

## 🎯 Directives
- **Conforming Timebase:**
  - Sequences must strictly conform to Full HD 1080p (1920x1080) at 23.976 fps constant frame rate.
- **Dedicated Project Bins:**
  - Import pre-trimmed source clips into `_Clips` bin and SFX assets into `_SFX` bin.
- **Track Layout Mapping:**
  - `V1`: Primary Video Clips
  - `V2`: Adjustment Layers / Visual Shields
  - `A1`: Original Ambient Sound (Gain boosted if authentic transient)
  - `A2`: **RESERVED 100% EMPTY FOR VOICEOVER**
  - `A3`: Transition Whoosh SFX
  - `A4`: Action Climax Impacts
  - `A5`: Ducked Background Music
- **Atomic Operations & Checkpoints:**
  - Always create a sequence checkpoint (`create_sequence_checkpoint`) before major mutations.
  - Apply mutations using batch tools (`add_to_timeline_batch`, `set_clip_properties_batch`) or direct HTTP POST to `http://127.0.0.1:47823/command` (`premiere-cli` bridge) so 100+ clip edits complete in < 15 seconds.
  - Always specify `sequenceName` explicitly to prevent editing the wrong sequence when multiple `.prproj` files are open.
  - **Zero-Drift V1+A1 Sync:** Never use `seq.overwriteClip` alone for subclips (it ignores `inPoint`/`outPoint` on Premiere 2026 and places untrimmed audio on `A1`). Always set `inPoint`, `outPoint`, `start`, and `end` atomically on both `V1` and `A1` paired clips, and verify with `check-sequence-sync`.
  - **Direct `.prproj` XML Mutation & BFS Canonicalization:** When cloning subgraphs across `.prproj` files (10-track ITV finishing), always run BFS ObjectID renumbering starting from `<Project ObjectID="1">`, deduplicate `<Node><ID>` and `<ClipID>` UUIDs, preserve first-occurrence `BinaryHash` payloads, and patch gzip header bytes `[8:10] = \x00\x0a`.
  - **7-Point `.prproj` Clone Hygiene & Stream Conformity Protocol:**
    1. *Open Sequence & Project Path:* Set `MZ.PrefixKey.OpenSequenceGuidList.1` strictly to the target sequence `ObjectUID` (preserving `ProjectViewState.List`) and update `project.settings.lastknowngoodprojectpath`.
    2. *Stale `.pek` Waveform Purge & MOGRT Relink:* Strip all cloned `<PeakFilePath>` and `<ConformedAudioPath>` elements referencing donor filenames across the entire XML tree so Premiere renders authentic waveforms, and relink `.aegraphic` files to the target episode folder.
    3. *MasterClip Consolidation, `ClipLoggingInfo` Sync & Complete Binning:* Consolidate duplicate file-backed `MasterClip`s onto 1 canonical `MasterClip` per `(normcase(FilePath), Name)`, sync `<ClipName>` across `Media`, `VideoMediaSource`/`AudioMediaSource`, `SubClip -> Clip`, and top-level `MasterClip -> LoggingInfo -> ClipLoggingInfo` (plus relink any transition-cloned `.mp4` so **`0` foreign donor strings** like `kb121`/`kb122`/`script-82` remain anywhere in the `.prproj`), auto-mint `ClipProjectItem`s for newly cloned `MasterClip`s, and place every active item into `source`, `ITV-Moments-script-XX`, `RootProjectItem`, or `Recovered Clips` (`0` unbinned active `MasterClip`s).
    4. *Audio Stream Guarantee:* Probe all `.mp4` files with `ffprobe`; mux a `48000 Hz` stereo silent AAC stream (`-c:v copy -c:a aac -ar 48000 -ac 2 -shortest`) into any video-only `.mp4` and regenerate `<FileKey>` / `<ImplementationID>` UUIDs on its `<Media>`.
    5. *Exact `ffprobe` Stream Sync:* Sync `<VideoStream>` (`FrameRect = 0,0,W,H`, `FrameRate`, `Duration`), `<AudioStream>` (`FrameRate = 254016000000 // sample_rate`, `Duration`), and `<VideoMediaSource>`/`<AudioMediaSource>` `OriginalDuration` to real disk values.
    6. *Non-1080p Framing Protection:* Enable `<ScaleToFramePolicy>1</ScaleToFramePolicy>` on every `<VideoClip>` whose media dimensions differ from `1920x1080` and attach an explicit centered `AE.ADBE Motion` (`Position = 0.5:0.5`).
    7. *Track A3 OutPoint Clamping & Continuous Track A5 BGM:* Clamp every `Track A3` SFX `TrackItem` duration to `<= real_ffprobe_dur - 1 frame` (preventing zebra stripes) and unify contiguous `Track A5` tail BGM segments into a single continuous track item whenever the BGM file duration permits.
  - **CEP Bridge Reliability (`premiere-cli`):** Keep `com.stefanwebb.premierecli/.debug` on port `8089` (avoiding `8088` conflict with `MCPBridgeCEP`), include `JSON.stringify` polyfill in `host/index.jsx`, and never put `<StartOn>` events on visible UI panels so Premiere Pro's Home/Workspace layout loads cleanly.
  - **Live Open Premiere Session Guard & Zero-Disruption Hot-Swap Protocol:**
    - Always check running `Adobe Premiere Pro.exe` processes and `<kb>.prproj` `st_mtime` before and after any project operation; **never** run a full `rebuild` over a `.prproj` containing manual user edits.
    - *Zero-Dialog MCP Project Switching & Sequential Frame Export:* When switching projects via Premiere MCP, **always call `premiere-pro:save_project` on the currently open project FIRST** before calling `open_project(path=...)` so user edits are saved without triggering Premiere's modal *"Save changes?"* dialog. When verifying frames via `premiere-pro:export_frame`, issue calls **strictly sequentially (`1` per turn)** to prevent playhead seek race conditions.
    - *If Premiere Pro is actively open (and CEP bridge port `47823` is closed):* Do NOT overwrite `<kb>.prproj` on disk (Premiere holds the live project in RAM and overwrites disk on `Ctrl+S`). Instead, back up the original media file, hot-swap the re-cut `.mp4` in-place at the exact same file path preserving original audio `sample_rate` (`44100 Hz` / `48000 Hz`) so Premiere auto-reloads the new stream duration in RAM, and report the exact `HH:MM:SS:FF` clip-end timecode for a 1-drag `B` (Ripple Edit Tool) extension.
    - *If Premiere Pro is closed:* Back up `<kb>.prproj` first, then apply a surgical XML patch on top of the user's latest save (updating `<Media>` `FileKey`/`ImplementationID`, `<VideoStream>`/`<AudioStream>` `Duration`, `<VideoMediaSource>`/`<AudioMediaSource>` `OriginalDuration`, `<MasterClip>` `OutPoint`, extending spanning utility overlays, and ripple-shifting downstream `TrackItems` + `TransitionItems` in lockstep).
  - Read back timeline state via `get_sequence_structure` / `get-full-sequence-info` and `premiere-cli export-frame` + `view_file` for closed-loop evaluation.
