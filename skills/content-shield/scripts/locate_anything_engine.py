#!/usr/bin/env python3
r"""
LocateAnything-3B Local ONNX INT4 Engine for VisionCut Suite (e:\ITV)
Runs 100% locally via onnxruntime + tokenizers + numpy + OpenCV (Zero PyTorch dependency!).
Model weights (~2.1 GB INT4 with KV-Cache) are cached at E:\.cache\locateanything_onnx_int4.

Supported ITV 10-Track Tasks:
  - audit-project: Batch-audits a full ITV episode (e.g. --kb kb124) in a single model load:
      1) Track V3 Watermark / Burned-in Caption OCR -> generates Anti-Erosion Mask2 specs & comparison sheet.
      2) Track V4 Impact Emojis -> grounds the impacted person/object & generates 4-keyframe trajectories & comparison sheet.
  - watermark-scan: Scans HEAD/MID/TAIL frames via OCR + Grounding to emit Track V3 Anti-Erosion Mask2 & ViralHog Zoom-Only params.
  - emoji-keyframes: Scans 4 frames around impact_sec via Referring Expression / Pointing to emit Track V4 Emoji 4-keyframe coordinates.
  - detect / ground / ocr / point: Single-image visual grounding with annotated image output for AI Vision (read_file) inspection.
"""
import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ONNX_REPO_ID = "Reza2kn/LocateAnything-3B-ONNX-WebGPU-INT4"
DEFAULT_CACHE_DIR = r"E:\.cache\locateanything_onnx_int4"

IMG_CONTEXT_TOKEN_ID = 151665
IM_END_TOKEN_ID = 151645
N_LAYERS = 36
KV_HEADS = 2
HEAD_DIM = 128
PATCH_SIZE = 14
MERGE_SIZE = 2


def parse_locate_anything_output(raw_text: str, width: int, height: int, default_label: str = "target") -> list[dict]:
    """
    Parses LocateAnything-3B structured tokens (<ref>...</ref><box><x1><y1><x2><y2></box> or <box>x1 y1 x2 y2</box>)
    into normalized [0..1] and pixel coordinates.
    """
    detections = []
    if not raw_text:
        return detections

    pattern = r"(<ref>.*?</ref>)|(<box>.*?</box>)"
    current_label = default_label

    for m in re.finditer(pattern, raw_text, flags=re.IGNORECASE | re.DOTALL):
        token = m.group(0)
        if token.lower().startswith("<ref>"):
            lbl = re.sub(r"</?ref>", "", token, flags=re.IGNORECASE).strip()
            if lbl:
                current_label = lbl
        else:
            content = re.sub(r"</?box>", "", token, flags=re.IGNORECASE)
            nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", content)]
            if len(nums) == 4:
                nx1, ny1, nx2, ny2 = [max(0.0, min(1.0, v / 1000.0)) for v in nums]
                nx1, nx2 = min(nx1, nx2), max(nx1, nx2)
                ny1, ny2 = min(ny1, ny2), max(ny1, ny2)
                detections.append({
                    "type": "box",
                    "label": current_label,
                    "norm_box": [round(nx1, 4), round(ny1, 4), round(nx2, 4), round(ny2, 4)],
                    "norm_center": [round((nx1 + nx2) / 2.0, 4), round((ny1 + ny2) / 2.0, 4)],
                    "pixel_box": [int(nx1 * width), int(ny1 * height), int(nx2 * width), int(ny2 * height)],
                })
            elif len(nums) == 2:
                nx, ny = [max(0.0, min(1.0, v / 1000.0)) for v in nums]
                detections.append({
                    "type": "point",
                    "label": current_label,
                    "norm_point": [round(nx, 4), round(ny, 4)],
                    "pixel_point": [int(nx * width), int(ny * height)],
                })
    return detections


class LocateAnythingOnnxEngine:
    """Pure ONNX Runtime INT4 KV-Cache Engine for LocateAnything-3B."""

    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR, in_token_limit: int = 256):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.in_token_limit = in_token_limit

        required_files = [
            "tokenizer.json",
            "onnx/embed_tokens_int4_meta.json",
            "onnx/embed_tokens_int4_scales.bin",
            "onnx/embed_tokens_int4_packed.bin",
            "onnx/vision_mlp_int4.onnx",
            "onnx/vision_mlp_int4.onnx.data",
            "onnx/language_tail_kv_int4.onnx",
            "onnx/language_tail_kv_int4.onnx.data",
        ]
        paths = {}
        for rel in required_files:
            local_target = self.cache_dir / rel
            if not local_target.exists():
                print(f"[LocateAnything-ONNX] Downloading {rel} ...", file=sys.stderr, flush=True)
                hf_hub_download(
                    repo_id=ONNX_REPO_ID,
                    filename=rel,
                    local_dir=str(self.cache_dir),
                )
            paths[rel] = str(local_target)

        t0 = time.time()
        self.tokenizer = Tokenizer.from_file(paths["tokenizer.json"])
        with open(paths["onnx/embed_tokens_int4_meta.json"], "r", encoding="utf-8") as f:
            self.emb_meta = json.load(f)

        self.vocab_size = int(self.emb_meta["vocab"])
        self.hidden_size = int(self.emb_meta["hidden"])
        self.block_size = int(self.emb_meta["block_size"])
        self.n_groups = int(self.emb_meta["n_groups"])
        self.zero_point = float(self.emb_meta["zero_point"])

        self.emb_packed = np.fromfile(paths["onnx/embed_tokens_int4_packed.bin"], dtype=np.uint8).reshape(
            self.vocab_size, self.hidden_size // 2
        )
        self.emb_scales = (
            np.fromfile(paths["onnx/embed_tokens_int4_scales.bin"], dtype=np.float16)
            .astype(np.float32)
            .reshape(self.vocab_size, self.n_groups)
        )

        sess_opts = ort.SessionOptions()
        sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_opts.intra_op_num_threads = max(4, (os.cpu_count() or 8) // 2)

        providers = ort.get_available_providers()
        active_providers = [p for p in ["CUDAExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider"] if p in providers]

        self.vision_sess = ort.InferenceSession(paths["onnx/vision_mlp_int4.onnx"], sess_options=sess_opts, providers=active_providers)
        self.lang_sess = ort.InferenceSession(paths["onnx/language_tail_kv_int4.onnx"], sess_options=sess_opts, providers=active_providers)
        self.vision_out_name = self.vision_sess.get_outputs()[0].name
        self.lang_out_names = [o.name for o in self.lang_sess.get_outputs()]
        print(
            f"[LocateAnything-ONNX] Loaded INT4 sessions in {time.time() - t0:.2f}s (Providers: {active_providers})",
            file=sys.stderr,
            flush=True,
        )

    def gather_embeds(self, token_ids: np.ndarray) -> np.ndarray:
        """Vectorized INT4 embedding dequantization -> float32 [L, hidden_size]."""
        rows = self.emb_packed[token_ids]
        lo = rows & 0x0F
        hi = (rows >> 4) & 0x0F
        q = np.empty((len(token_ids), self.hidden_size), dtype=np.float32)
        q[:, 0::2] = lo
        q[:, 1::2] = hi
        scales = np.repeat(self.emb_scales[token_ids], self.block_size, axis=1)
        return (q - self.zero_point) * scales

    def preprocess_image(self, img_bgr: np.ndarray) -> tuple[np.ndarray, int, int]:
        """Rescales and slices BGR image into MoonViT patch tensor [280, 3, 14, 14]."""
        h, w = img_bgr.shape[:2]
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        if w >= h:
            gh, gw = 14, 20
        else:
            gh, gw = 20, 14

        tw = gw * PATCH_SIZE
        th = gh * PATCH_SIZE

        resized = cv2.resize(img_rgb, (tw, th), interpolation=cv2.INTER_AREA)
        norm = (resized.astype(np.float32) / 255.0 - 0.5) / 0.5

        pv = (
            norm.reshape(gh, PATCH_SIZE, gw, PATCH_SIZE, 3)
            .transpose(0, 2, 4, 1, 3)
            .reshape(gh * gw, 3, PATCH_SIZE, PATCH_SIZE)
        )
        return np.ascontiguousarray(pv, dtype=np.float32), gh, gw

    def build_prompt_ids(self, task_type: str, category: str, gh: int, gw: int, question_override: str | None = None) -> list[int]:
        n_img_tokens = (gh * gw) // (MERGE_SIZE * MERGE_SIZE)
        if question_override:
            user_prompt = question_override
        else:
            cats = "</c>".join(c.strip() for c in category.split(",") if c.strip()) or "objects"
            if task_type == "OCR":
                user_prompt = "Detect all the text in box format."
            elif task_type == "GroundingSingle":
                user_prompt = f"Locate a single instance that matches the following description: {category}."
            elif task_type == "Grounding":
                user_prompt = f"Locate all the instances that match the following description: {cats}."
            elif task_type == "Pointing":
                user_prompt = f"Point to: {category}."
            elif task_type == "GUI":
                user_prompt = f"Locate the region that matches the following description: {category}."
            else:
                user_prompt = f"Locate all the instances that matches the following description: {cats}."

        full_str = (
            "<|im_start|>system\nYou are a helpful assistant.\n<|im_end|>\n"
            f"<|im_start|>user\n<image 1><img>{'<IMG_CONTEXT>' * n_img_tokens}</img>{user_prompt}<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
        enc = self.tokenizer.encode(full_str, add_special_tokens=False)
        return enc.ids

    def infer_bgr(
        self,
        img_bgr: np.ndarray,
        task_type: str = "Detection",
        category: str = "objects",
        question_override: str | None = None,
        max_new_tokens: int = 128,
    ) -> dict:
        orig_h, orig_w = img_bgr.shape[:2]

        t0 = time.time()
        pv, gh, gw = self.preprocess_image(img_bgr)
        grid_hws = np.array([[gh, gw]], dtype=np.int64)
        visual_features = self.vision_sess.run([self.vision_out_name], {"pixel_values": pv, "image_grid_hws": grid_hws})[0]
        t_vis = time.time() - t0

        ids = self.build_prompt_ids(task_type, category, gh, gw, question_override=question_override)
        ids_arr = np.array(ids, dtype=np.int64)
        seq_len = len(ids_arr)

        embeds = self.gather_embeds(ids_arr)
        img_mask = ids_arr == IMG_CONTEXT_TOKEN_ID
        n_vis = min(int(np.sum(img_mask)), len(visual_features))
        embeds[np.where(img_mask)[0][:n_vis]] = visual_features[:n_vis]

        feeds = {
            "input_ids": ids_arr.reshape(1, seq_len),
            "inputs_embeds": embeds.reshape(1, seq_len, self.hidden_size),
            "attention_mask": np.ones((1, seq_len), dtype=np.int64),
            "position_ids": np.arange(seq_len, dtype=np.int64).reshape(1, seq_len),
        }
        empty_kv = np.zeros((1, KV_HEADS, 0, HEAD_DIM), dtype=np.float32)
        for i in range(N_LAYERS):
            feeds[f"past_key_{i}"] = empty_kv
            feeds[f"past_value_{i}"] = empty_kv

        res_list = self.lang_sess.run(self.lang_out_names, feeds)
        res = dict(zip(self.lang_out_names, res_list))

        logits = res["logits"]
        next_token = int(np.argmax(logits[0, -1]))
        gen_tokens = [next_token]
        past_len = seq_len

        for _ in range(max_new_tokens - 1):
            if next_token == IM_END_TOKEN_ID:
                break
            if len(gen_tokens) >= 11 and max_new_tokens <= 20:
                partial_txt = self.tokenizer.decode(gen_tokens, skip_special_tokens=False)
                if "</box>" in partial_txt:
                    break
            emb1 = self.gather_embeds(np.array([next_token], dtype=np.int64)).reshape(1, 1, self.hidden_size)
            step_feeds = {
                "input_ids": np.array([[next_token]], dtype=np.int64),
                "inputs_embeds": emb1,
                "attention_mask": np.ones((1, past_len + 1), dtype=np.int64),
                "position_ids": np.array([[past_len]], dtype=np.int64),
            }
            for i in range(N_LAYERS):
                step_feeds[f"past_key_{i}"] = res[f"present_key_{i}"]
                step_feeds[f"past_value_{i}"] = res[f"present_value_{i}"]

            res_list = self.lang_sess.run(self.lang_out_names, step_feeds)
            res = dict(zip(self.lang_out_names, res_list))
            next_token = int(np.argmax(res["logits"][0, -1]))
            gen_tokens.append(next_token)
            past_len += 1

        raw_text = self.tokenizer.decode(gen_tokens, skip_special_tokens=False)
        detections = parse_locate_anything_output(raw_text, orig_w, orig_h, default_label=category)
        total_time = round(time.time() - t0, 2)

        return {
            "success": True,
            "width": orig_w,
            "height": orig_h,
            "grid": [gh, gw],
            "vision_sec": round(t_vis, 2),
            "total_sec": total_time,
            "tokens_generated": len(gen_tokens),
            "raw_text": raw_text,
            "detections": detections,
        }

    def infer_image(
        self,
        image_path: str,
        task_type: str = "Detection",
        category: str = "objects",
        question_override: str | None = None,
        max_new_tokens: int = 128,
    ) -> dict:
        img_bgr = cv2.imread(str(image_path))
        if img_bgr is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")
        return self.infer_bgr(
            img_bgr,
            task_type=task_type,
            category=category,
            question_override=question_override,
            max_new_tokens=max_new_tokens,
        )


def draw_detections(image_path: str, detections: list[dict], out_path: str, title: str = "") -> str:
    img = cv2.imread(str(image_path))
    if img is None:
        return out_path
    h, w = img.shape[:2]

    for det in detections:
        lbl = det.get("label", "target")
        if det["type"] == "box":
            x1, y1, x2, y2 = det["pixel_box"]
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 128), 3)
            cv2.putText(
                img,
                f"{lbl} [{det['norm_box'][0]:.2f},{det['norm_box'][1]:.2f}..{det['norm_box'][2]:.2f},{det['norm_box'][3]:.2f}]",
                (max(5, x1), max(24, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 128),
                2,
            )
        elif det["type"] == "point":
            px, py = det["pixel_point"]
            cv2.circle(img, (px, py), 12, (0, 64, 255), -1)
            cv2.circle(img, (px, py), 16, (255, 255, 255), 2)
            cv2.putText(
                img,
                f"{lbl} ({det['norm_point'][0]:.3f}, {det['norm_point'][1]:.3f})",
                (min(w - 220, px + 18), max(25, py)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 200, 255),
                2,
            )

    if title:
        cv2.rectangle(img, (0, 0), (w, 36), (0, 0, 0), -1)
        cv2.putText(img, title, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    cv2.imwrite(str(out_path), img)
    return out_path


def extract_video_frame(video_path: str, time_sec: float, out_jpg: str | None = None) -> tuple[np.ndarray, int, int]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    target_idx = max(0, min(total_frames - 1, int(round(time_sec * fps))))
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_idx)
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        raise RuntimeError(f"Failed to read frame at {time_sec:.2f}s from {video_path}")
    if out_jpg:
        os.makedirs(os.path.dirname(os.path.abspath(out_jpg)), exist_ok=True)
        cv2.imwrite(out_jpg, frame)
    return frame, w, h


def run_watermark_scan(engine: LocateAnythingOnnxEngine, video_path: str, out_dir: str) -> dict:
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    dur = total_frames / fps
    cap.release()

    sample_times = [("HEAD", max(0.15, dur * 0.12)), ("MID", dur * 0.50), ("TAIL", max(0.2, dur - 0.25))]
    os.makedirs(out_dir, exist_ok=True)
    stem = Path(video_path).stem

    all_text_boxes = []
    frame_reports = []

    for tag, t_sec in sample_times:
        raw_jpg = os.path.join(out_dir, f"{stem}_{tag}_raw.jpg")
        extract_video_frame(video_path, t_sec, raw_jpg)
        res = engine.infer_image(raw_jpg, task_type="OCR", category="text")

        vis_jpg = os.path.join(out_dir, f"{stem}_{tag}_ocr.jpg")
        draw_detections(
            raw_jpg,
            res["detections"],
            vis_jpg,
            title=f"{stem} [{tag} @ {t_sec:.2f}s] - LocateAnything-3B OCR ({len(res['detections'])} boxes, {res['total_sec']}s)",
        )
        for d in res["detections"]:
            if d["type"] == "box":
                all_text_boxes.append({"tag": tag, "time_sec": round(t_sec, 2), **d})
        frame_reports.append({
            "tag": tag,
            "time_sec": round(t_sec, 2),
            "elapsed_sec": res["total_sec"],
            "raw_text": res["raw_text"],
            "visual_path": vis_jpg,
            "detections": res["detections"],
        })

    recommendations = []
    for b in all_text_boxes:
        nx1, ny1, nx2, ny2 = b["norm_box"]
        mx1 = round(max(0.0, nx1 - 0.015), 4)
        my1 = round(max(0.0, ny1 - 0.015), 4)
        mx2 = round(min(1.0, nx2 + 0.015), 4)
        my2 = round(min(1.0, ny2 + 0.015), 4)
        recommendations.append({
            "found_at": b["tag"],
            "label": b["label"],
            "raw_norm_box": b["norm_box"],
            "track_v3_anti_erosion_mask2": {
                "vertices_normalized": [[mx1, my1], [mx2, my1], [mx2, my2], [mx1, my2]],
                "amount": 15,
                "thickness": 15,
                "feather": 22,
                "expansion": 12,
            },
        })

    return {
        "video_path": str(video_path),
        "duration_sec": round(dur, 3),
        "frames_scanned": frame_reports,
        "track_v3_recommendations": recommendations,
    }


def run_emoji_keyframes(
    engine: LocateAnythingOnnxEngine,
    video_path: str,
    impact_sec: float,
    target_phrase: str,
    emoji_type: str,
    out_dir: str,
) -> dict:
    offsets = [-0.08, 0.0, 0.08, 0.16]
    os.makedirs(out_dir, exist_ok=True)
    stem = Path(video_path).stem
    keyframes = []

    for idx, dt in enumerate(offsets):
        t_sec = max(0.04, impact_sec + dt)
        raw_jpg = os.path.join(out_dir, f"{stem}_kf{idx}_{t_sec:.2f}s_raw.jpg")
        extract_video_frame(video_path, t_sec, raw_jpg)

        res = engine.infer_image(
            raw_jpg,
            task_type="GroundingSingle",
            category=target_phrase,
        )

        cx, cy = 0.5, 0.5
        det_used = None
        if res["detections"]:
            det_used = res["detections"][0]
            if det_used["type"] == "box":
                cx, cy = det_used["norm_center"]
            elif det_used["type"] == "point":
                cx, cy = det_used["norm_point"]

        vis_jpg = os.path.join(out_dir, f"{stem}_kf{idx}_{t_sec:.2f}s_grounded.jpg")
        draw_detections(
            raw_jpg,
            res["detections"],
            vis_jpg,
            title=f"KF#{idx+1} @ {t_sec:.2f}s | '{target_phrase}' -> ({cx:.3f}, {cy:.3f}) [{res['total_sec']}s]",
        )
        keyframes.append({
            "keyframe_index": idx + 1,
            "time_sec": round(t_sec, 3),
            "norm_position": [round(cx, 4), round(cy, 4)],
            "elapsed_sec": res["total_sec"],
            "raw_text": res["raw_text"],
            "detection": det_used,
            "visual_path": vis_jpg,
        })

    return {
        "video_path": str(video_path),
        "impact_sec": impact_sec,
        "target_phrase": target_phrase,
        "recommended_emoji": emoji_type,
        "recommended_scale_pct": 20.0,
        "track_v4_keyframes": keyframes,
    }


def run_project_audit(engine: LocateAnythingOnnxEngine, kb: str, out_dir: str) -> dict:
    """
    Single-load batch test of LocateAnything-3B on an ITV episode (e.g. kb124):
      1) Audits all 5 Track V4 Emoji clips in kb124 (comparing LocateAnything-3B grounding vs existing keyframes).
      2) Audits representative Track V3 Watermark/Burned-in text clips (comparing LocateAnything-3B OCR vs existing Mask2).
      3) Generates 2 visual comparison contact sheets for AI Vision (read_file) inspection.
    """
    sys.path.insert(0, r"E:\.agents\skills\visioncut\scripts")
    from rebuild_all_prproj import EPISODE_PILLARBOX_CROP_PCT, EPISODE_V4_EMOJI_SPEC, WATERMARK_PRESET_MAP

    manifest_path = rf"E:\ITV\Project\{kb}\{kb}_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    clip_by_name = {c["clip_name"]: c for c in manifest["clips"]}
    crop_map = EPISODE_PILLARBOX_CROP_PCT.get(kb, {})

    os.makedirs(out_dir, exist_ok=True)

    # ---- PART A: Track V4 Emoji Grounding across all 5 Emoji clips ----
    emoji_specs = EPISODE_V4_EMOJI_SPEC.get(kb, [])
    emoji_phrases = {
        "itv.kb124.7.mp4": "the person near the exploding tire",
        "08.mp4": "the falling person",
        "24.mp4": "the person falling",
        "33.mp4": "the person falling",
        "62.mp4": "the person falling",
    }
    emoji_results = []
    emoji_tiles = []

    for espec in emoji_specs:
        cname = espec["clip_name"]
        cmeta = clip_by_name.get(cname)
        if not cmeta:
            continue
        vpath = cmeta["source_path"]
        in_sec = float(cmeta.get("in_point_sec") or 0.0)
        off_sec = float(espec["offset_sec"])
        src_impact_sec = in_sec + off_sec
        phrase = emoji_phrases.get(cname, "the falling person")
        crop_pct = crop_map.get(cname, 0.0)

        frame_bgr, w, h = extract_video_frame(vpath, src_impact_sec)
        # If pillarbox cropped on V3, black out sidebars so LocateAnything only grounds inside active column
        work_bgr = frame_bgr.copy()
        if crop_pct > 0:
            px_crop = int(round(w * (crop_pct / 100.0)))
            work_bgr[:, :px_crop] = 0
            work_bgr[:, w - px_crop :] = 0

        res = engine.infer_bgr(work_bgr, task_type="GroundingSingle", category=phrase)
        la_center = None
        la_box = None
        if res["detections"]:
            d0 = res["detections"][0]
            la_box = d0.get("norm_box")
            la_center = d0.get("norm_center") or d0.get("norm_point")

        existing_pt = espec["points"][0]
        vis = work_bgr.copy()
        # Draw existing V4 emoji keyframe #1 in YELLOW
        ex_x, ex_y = int(existing_pt[0] * w), int(existing_pt[1] * h)
        cv2.circle(vis, (ex_x, ex_y), 16, (0, 255, 255), 3)
        cv2.putText(vis, f"PRPROJ KF1 ({existing_pt[0]:.2f},{existing_pt[1]:.2f})", (max(10, ex_x - 90), max(30, ex_y - 22)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Draw LocateAnything-3B box + center in GREEN
        if la_box:
            bx1, by1, bx2, by2 = [int(la_box[0] * w), int(la_box[1] * h), int(la_box[2] * w), int(la_box[3] * h)]
            cv2.rectangle(vis, (bx1, by1), (bx2, by2), (0, 255, 0), 3)
        if la_center:
            lx, ly = int(la_center[0] * w), int(la_center[1] * h)
            cv2.circle(vis, (lx, ly), 12, (0, 255, 0), -1)
            cv2.putText(vis, f"LocateAnything ({la_center[0]:.2f},{la_center[1]:.2f})", (max(10, lx - 90), min(h - 15, ly + 30)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.rectangle(vis, (0, 0), (w, 42), (0, 0, 0), -1)
        cv2.putText(
            vis,
            f"[V4 Emoji] {cname} @ {src_impact_sec:.2f}s ({espec['gif_name']}) | Green=LocateAnything ({res['total_sec']}s) vs Yellow=Current",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )
        tile_path = os.path.join(out_dir, f"{kb}_v4_{Path(cname).stem}_compare.jpg")
        cv2.imwrite(tile_path, vis)
        emoji_tiles.append(cv2.resize(vis, (960, 540)))

        emoji_results.append({
            "clip_name": cname,
            "gif_name": espec["gif_name"],
            "src_impact_sec": round(src_impact_sec, 3),
            "phrase": phrase,
            "elapsed_sec": res["total_sec"],
            "existing_first_point": list(existing_pt),
            "locate_anything_box": la_box,
            "locate_anything_center": la_center,
            "visual_path": tile_path,
        })

    if emoji_tiles:
        while len(emoji_tiles) % 2 != 0:
            emoji_tiles.append(np.zeros_like(emoji_tiles[0]))
        rows = [np.hstack(emoji_tiles[i : i + 2]) for i in range(0, len(emoji_tiles), 2)]
        sheet_v4 = np.vstack(rows)
        v4_sheet_path = os.path.join(out_dir, f"{kb}_v4_emoji_comparison_sheet.jpg")
        cv2.imwrite(v4_sheet_path, sheet_v4)
    else:
        v4_sheet_path = None

    # ---- PART B: Track V3 Watermark / Burned-in Text OCR Scan ----
    wm_map = WATERMARK_PRESET_MAP.get(kb, {})
    sample_wm_clips = ["itv.kb124.2.mp4", "itv.kb124.4.mp4", "itv.kb124.7.mp4", "itv.kb124.14.mp4", "03.mp4", "12.mp4"]
    wm_results = []
    wm_tiles = []

    for cname in sample_wm_clips:
        cmeta = clip_by_name.get(cname)
        if not cmeta or cname not in wm_map:
            continue
        vpath = cmeta["source_path"]
        in_sec = float(cmeta.get("in_point_sec") or 0.0)
        dur_sec = float(cmeta.get("duration_sec") or 3.0)
        mid_sec = in_sec + dur_sec * 0.5
        crop_pct = crop_map.get(cname, 0.0)

        frame_bgr, w, h = extract_video_frame(vpath, mid_sec)
        work_bgr = frame_bgr.copy()
        if crop_pct > 0:
            px_crop = int(round(w * (crop_pct / 100.0)))
            work_bgr[:, :px_crop] = 0
            work_bgr[:, w - px_crop :] = 0

        res = engine.infer_bgr(work_bgr, task_type="OCR", category="text")
        existing_rects = wm_map[cname][0] if isinstance(wm_map[cname][0], list) else []

        vis = work_bgr.copy()
        # Draw existing WATERMARK_PRESET_MAP Mask2 in CYAN/YELLOW
        for rx1, ry1, rx2, ry2 in existing_rects:
            px1, py1 = int(max(0.0, rx1) * w), int(max(0.0, ry1) * h)
            px2, py2 = int(min(1.0, rx2) * w), int(min(1.0, ry2) * h)
            cv2.rectangle(vis, (px1, py1), (px2, py2), (255, 200, 0), 2)

        # Draw LocateAnything-3B OCR detections in GREEN
        for det in res["detections"]:
            if det["type"] == "box":
                bx1, by1, bx2, by2 = det["pixel_box"]
                cv2.rectangle(vis, (bx1, by1), (bx2, by2), (0, 255, 0), 3)
                cv2.putText(vis, f"LA:'{det['label']}'", (max(5, bx1), max(28, by1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

        cv2.rectangle(vis, (0, 0), (w, 42), (0, 0, 0), -1)
        cv2.putText(
            vis,
            f"[V3 Mask2] {cname} @ {mid_sec:.2f}s | Green=LocateAnything OCR ({len(res['detections'])} boxes, {res['total_sec']}s) | Cyan=Current Mask2",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            (255, 255, 255),
            2,
        )
        tile_path = os.path.join(out_dir, f"{kb}_v3_{Path(cname).stem}_compare.jpg")
        cv2.imwrite(tile_path, vis)
        wm_tiles.append(cv2.resize(vis, (960, 540)))

        wm_results.append({
            "clip_name": cname,
            "mid_sec": round(mid_sec, 2),
            "elapsed_sec": res["total_sec"],
            "raw_text": res["raw_text"],
            "existing_masks": existing_rects,
            "locate_anything_detections": res["detections"],
            "visual_path": tile_path,
        })

    if wm_tiles:
        while len(wm_tiles) % 2 != 0:
            wm_tiles.append(np.zeros_like(wm_tiles[0]))
        rows = [np.hstack(wm_tiles[i : i + 2]) for i in range(0, len(wm_tiles), 2)]
        sheet_v3 = np.vstack(rows)
        v3_sheet_path = os.path.join(out_dir, f"{kb}_v3_watermark_comparison_sheet.jpg")
        cv2.imwrite(v3_sheet_path, sheet_v3)
    else:
        v3_sheet_path = None

    return {
        "project": kb,
        "v4_emoji_comparison_sheet": v4_sheet_path,
        "v3_watermark_comparison_sheet": v3_sheet_path,
        "v4_emoji_audit": emoji_results,
        "v3_watermark_audit": wm_results,
    }


def _has_overlay_diff(img_a: np.ndarray, img_b: np.ndarray) -> bool:
    """Checks if top/bottom watermark or caption zones have sharp high-contrast changes between two frames."""
    h, w = img_a.shape[:2]
    ga = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gb = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)
    # Check top 22% and bottom 28% where watermarks/captions live
    top_diff = np.mean(np.abs(ga[: int(h * 0.22), :].astype(np.float32) - gb[: int(h * 0.22), :].astype(np.float32)))
    bot_diff = np.mean(np.abs(ga[int(h * 0.72) :, :].astype(np.float32) - gb[int(h * 0.72) :, :].astype(np.float32)))
    return bool(top_diff > 18.0 or bot_diff > 18.0)


def _has_corner_or_band_stroke(work_bgr: np.ndarray) -> bool:
    """Fast 2ms check whether top 19% or bottom 25% of active viewport contains localized character/logo strokes."""
    h, w = work_bgr.shape[:2]
    gray = cv2.cvtColor(work_bgr, cv2.COLOR_BGR2GRAY)
    bands = [gray[: int(h * 0.19), :], gray[int(h * 0.75) :, :]]
    for b in bands:
        bh, bw = b.shape[:2]
        if bh < 16 or bw < 32:
            continue
        gx = np.abs(cv2.Sobel(b, cv2.CV_16S, 1, 0, ksize=3))
        gy = np.abs(cv2.Sobel(b, cv2.CV_16S, 0, 1, ksize=3))
        grad = gx + gy
        hits = 0
        total_blocks = 0
        for y0 in range(0, bh - 20, 20):
            for x0 in range(0, bw - 56, 56):
                patch_i = b[y0 : y0 + 24, x0 : x0 + 64]
                if int(np.max(patch_i)) < 15:
                    continue
                total_blocks += 1
                patch_g = grad[y0 : y0 + 24, x0 : x0 + 64]
                if np.percentile(patch_g, 92) > 290 and float(np.std(patch_i)) > 48.0 and (int(np.max(patch_i)) - int(np.min(patch_i))) > 155:
                    hits += 1
        # Localized watermark/caption has 1..6 high-contrast stroke blocks (not full-width tree foliage)
        if 1 <= hits <= max(5, int(total_blocks * 0.22)):
            return True
    return False


def run_full_source_scan(engine: LocateAnythingOnnxEngine, kb: str, out_dir: str) -> dict:
    """
    Scans 100% of all source clips in an episode (e.g. kb124: all 89 clips across Part 1 + Part 2)
    at HEAD / MID / TAIL within their active [in_point_sec, out_point_sec] timeline window.
    Identifies:
      - False Positives (clips currently masked in WATERMARK_PRESET_MAP that have NO watermark/text in active window)
      - False Negatives (clips NOT in WATERMARK_PRESET_MAP that DO have watermarks/text/logos)
      - Box Refinements (clips in WATERMARK_PRESET_MAP where mask coordinates need tightening or extra boxes)
    Generates 12 high-resolution [HEAD | MID | TAIL] contact sheets for 100% AI Vision verification.
    """
    from concurrent.futures import ThreadPoolExecutor
    sys.path.insert(0, r"E:\.agents\skills\visioncut\scripts")
    from rebuild_all_prproj import (
        EPISODE_PILLARBOX_CROP_PCT,
        EPISODE_VH_MOTION_OVERRIDE,
        WATERMARK_PRESET_MAP,
    )

    manifest_path = rf"E:\ITV\Project\{kb}\{kb}_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    clips = manifest["clips"]
    wm_map = WATERMARK_PRESET_MAP.get(kb, {})
    crop_map = EPISODE_PILLARBOX_CROP_PCT.get(kb, {})
    vh_map = EPISODE_VH_MOTION_OVERRIDE.get(kb, {})

    sheets_dir = os.path.join(out_dir, f"{kb}_full_scan_sheets")
    os.makedirs(sheets_dir, exist_ok=True)

    all_clip_reports = []
    row_images = []
    t_start_all = time.time()

    # Pre-extract all (HEAD, MID, TAIL) frames in parallel across 12 worker threads
    def _extract_clip_triplet(cmeta):
        vpath = cmeta["source_path"]
        in_sec = float(cmeta.get("in_point_sec") or 0.0)
        dur_sec = float(cmeta.get("duration_sec") or 3.0)
        stimes = [
            ("HEAD", in_sec + min(0.20, dur_sec * 0.12)),
            ("MID", in_sec + dur_sec * 0.50),
            ("TAIL", in_sec + max(0.15, dur_sec - 0.20)),
        ]
        fb_dict = {}
        for tag, ts in stimes:
            try:
                fbgr, _, _ = extract_video_frame(vpath, ts)
            except Exception:
                fbgr = np.zeros((1080, 1920, 3), dtype=np.uint8)
            fb_dict[tag] = fbgr
        return stimes, fb_dict

    with ThreadPoolExecutor(max_workers=12) as pool:
        extracted_triplets = list(pool.map(_extract_clip_triplet, clips))

    for idx, (cmeta, (sample_times, frames_bgr)) in enumerate(zip(clips, extracted_triplets)):
        cname = cmeta["clip_name"]
        vpath = cmeta["source_path"]
        in_sec = float(cmeta.get("in_point_sec") or 0.0)
        dur_sec = float(cmeta.get("duration_sec") or 3.0)
        out_sec = in_sec + dur_sec

        crop_pct = float(crop_map.get(cname, 0.0))
        vh_override = vh_map.get(cname)  # (scale_pct, pos_x, pos_y) or None
        existing_entry = wm_map.get(cname)
        existing_rects = existing_entry[0] if (existing_entry and isinstance(existing_entry[0], list)) else []

        # Prepare active-viewport masked frames for LocateAnything-3B so it doesn't waste tokens on cropped-out sidebars
        def mask_inactive_viewport(img_in: np.ndarray) -> np.ndarray:
            work = img_in.copy()
            h_i, w_i = work.shape[:2]
            if crop_pct > 0:
                px_c = int(round(w_i * (crop_pct / 100.0)))
                work[:, :px_c] = 0
                work[:, w_i - px_c :] = 0
            if vh_override:
                sc_pct, px_norm, py_norm = vh_override
                s = sc_pct / 100.0
                if s > 1.0:
                    # Canvas u in [0,1] maps from source u_src = 0.5 + (u - px_norm)/s
                    u1 = max(0.0, 0.5 + (0.0 - px_norm) / s)
                    u2 = min(1.0, 0.5 + (1.0 - px_norm) / s)
                    v1 = max(0.0, 0.5 + (0.0 - py_norm) / s)
                    v2 = min(1.0, 0.5 + (1.0 - py_norm) / s)
                    ix1, ix2 = int(round(u1 * w_i)), int(round(u2 * w_i))
                    iy1, iy2 = int(round(v1 * h_i)), int(round(v2 * h_i))
                    if ix1 > 0:
                        work[:, :ix1] = 0
                    if ix2 < w_i:
                        work[:, ix2:] = 0
                    if iy1 > 0:
                        work[:iy1, :] = 0
                    if iy2 < h_i:
                        work[iy2:, :] = 0
            # Mask interior scene [0.19 .. 0.75] unless existing_rects has a mid-screen box, so OCR focuses on top/bottom watermark & caption bands
            has_mid_existing = any(0.19 < ((ry1 + ry2) * 0.5) < 0.75 for _, ry1, _, ry2 in existing_rects)
            if not has_mid_existing:
                work[int(h_i * 0.19) : int(h_i * 0.75), :] = 0
            return work

        # Run LocateAnything-3B OCR when existing_rects is present or top/bottom bands contain high-contrast character/logo strokes
        work_mid = mask_inactive_viewport(frames_bgr["MID"])
        if existing_rects:
            tags_to_infer = ["HEAD", "MID", "TAIL"]
        elif (not vh_override) and _has_corner_or_band_stroke(work_mid):
            tags_to_infer = ["MID"]
        else:
            tags_to_infer = []

        detections_by_tag = {"HEAD": [], "MID": [], "TAIL": []}
        raw_text_by_tag = {}
        infer_sec_total = 0.0

        for tag in tags_to_infer:
            work_img = work_mid if tag == "MID" else mask_inactive_viewport(frames_bgr[tag])
            res = engine.infer_bgr(work_img, task_type="OCR", category="text", max_new_tokens=18)
            detections_by_tag[tag] = [d for d in res["detections"] if d["type"] == "box"]
            raw_text_by_tag[tag] = res["raw_text"]
            infer_sec_total += res["total_sec"]

        # Merge unique detected boxes across scanned tags
        all_la_boxes = []
        for tag in ("HEAD", "MID", "TAIL"):
            for d in detections_by_tag[tag]:
                all_la_boxes.append({"tag": tag, "label": d["label"], "norm_box": d["norm_box"]})

        # Build 3-panel visualization row [HEAD | MID | TAIL] (each panel 640x360 -> row 1920x388)
        panels = []
        pw, ph = 640, 360
        for tag, t_sec in sample_times:
            p_img = cv2.resize(frames_bgr[tag], (pw, ph))
            # Draw subtle 0.2 grid
            for gx in (0.2, 0.4, 0.6, 0.8):
                cv2.line(p_img, (int(gx * pw), 0), (int(gx * pw), ph), (55, 55, 55), 1)
            for gy in (0.2, 0.4, 0.6, 0.8):
                cv2.line(p_img, (0, int(gy * ph)), (pw, int(gy * ph)), (55, 55, 55), 1)

            # Draw crop_pct boundaries in MAGENTA
            if crop_pct > 0:
                cx_l = int(round((crop_pct / 100.0) * pw))
                cx_r = int(round((1.0 - crop_pct / 100.0) * pw))
                cv2.line(p_img, (cx_l, 0), (cx_l, ph), (255, 0, 255), 2)
                cv2.line(p_img, (cx_r, 0), (cx_r, ph), (255, 0, 255), 2)
                # Darken cropped-out sidebars slightly so AI Vision sees what's cropped
                p_img[:, :cx_l] = (p_img[:, :cx_l] * 0.35).astype(np.uint8)
                p_img[:, cx_r:] = (p_img[:, cx_r:] * 0.35).astype(np.uint8)

            # Draw VH_MOTION_OVERRIDE active viewport in MAGENTA
            if vh_override:
                sc_pct, px_norm, py_norm = vh_override
                s = sc_pct / 100.0
                if s > 1.0:
                    u1 = max(0.0, 0.5 + (0.0 - px_norm) / s)
                    u2 = min(1.0, 0.5 + (1.0 - px_norm) / s)
                    v1 = max(0.0, 0.5 + (0.0 - py_norm) / s)
                    v2 = min(1.0, 0.5 + (1.0 - py_norm) / s)
                    cv2.rectangle(p_img, (int(u1 * pw), int(v1 * ph)), (int(u2 * pw), int(v2 * ph)), (255, 0, 255), 2)

            # Draw existing WATERMARK_PRESET_MAP Mask2 in YELLOW/CYAN
            for rx1, ry1, rx2, ry2 in existing_rects:
                x1, y1 = int(max(0.0, rx1) * pw), int(max(0.0, ry1) * ph)
                x2, y2 = int(min(1.0, rx2) * pw), int(min(1.0, ry2) * ph)
                cv2.rectangle(p_img, (x1, y1), (x2, y2), (0, 230, 255), 2)
                cv2.putText(p_img, "CUR", (max(2, x1 + 2), max(14, y1 + 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 230, 255), 1)

            # Draw LocateAnything-3B detections in GREEN
            for d in detections_by_tag[tag]:
                nx1, ny1, nx2, ny2 = d["norm_box"]
                gx1, gy1 = int(nx1 * pw), int(ny1 * ph)
                gx2, gy2 = int(nx2 * pw), int(ny2 * ph)
                cv2.rectangle(p_img, (gx1, gy1), (gx2, gy2), (0, 255, 0), 2)
                lbl_short = (d["label"] or "")[:14]
                cv2.putText(p_img, f"LA:{lbl_short}", (max(2, gx1), max(14, gy1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

            sc_flag = "*" if tag in tags_to_infer else ""
            cv2.putText(p_img, f"{tag}{sc_flag} {t_sec:.2f}s", (8, ph - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)
            panels.append(p_img)

        row_body = np.hstack(panels)
        header = np.zeros((32, pw * 3, 3), dtype=np.uint8)
        status_tag = "MASKED" if existing_rects else ("VH_ZOOM" if vh_override else "UNMASKED")
        la_summary = f"LA={len(all_la_boxes)} boxes {[b['label'] for b in all_la_boxes[:3]]}" if all_la_boxes else "LA=0 (clean)"
        hdr_color = (0, 255, 255) if (bool(existing_rects) != bool(all_la_boxes)) else (200, 255, 200)
        hdr_text = (
            f"#{idx+1:02d} {cname} [{in_sec:.2f}..{out_sec:.2f}s] | {status_tag} (CUR={len(existing_rects)} rects, crop={crop_pct}%, vh={vh_override}) | {la_summary}"
        )
        cv2.putText(header, hdr_text, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.54, hdr_color, 1)
        row_full = np.vstack([header, row_body])
        row_images.append(row_full)

        # Classify preliminary discrepancy
        if existing_rects and not all_la_boxes:
            category_flag = "CHECK_FALSE_POSITIVE_OR_FAINT_WM"
        elif (not existing_rects) and (not vh_override) and all_la_boxes:
            category_flag = "CANDIDATE_MISSING_MASK"
        elif existing_rects and all_la_boxes:
            category_flag = "BOTH_HAVE_BOXES_CHECK_ALIGNMENT"
        else:
            category_flag = "CLEAN_OR_VH_ZOOMED"

        rep = {
            "index": idx + 1,
            "clip_name": cname,
            "source_path": vpath,
            "in_sec": round(in_sec, 2),
            "out_sec": round(out_sec, 2),
            "crop_pct": crop_pct,
            "vh_override": list(vh_override) if vh_override else None,
            "existing_masks": [list(r) for r in existing_rects],
            "tags_inferred": tags_to_infer,
            "infer_sec": round(infer_sec_total, 2),
            "la_detections": all_la_boxes,
            "category_flag": category_flag,
        }
        all_clip_reports.append(rep)
        print(
            f"[{idx+1:02d}/{len(clips):02d}] {cname:18s} | {status_tag:8s} | CUR={len(existing_rects)} | LA={len(all_la_boxes)} | {category_flag} ({infer_sec_total:.1f}s)",
            flush=True,
        )

    # Save contact sheets (8 clips per sheet)
    sheet_paths = []
    rows_per_sheet = 8
    for s_idx in range(0, len(row_images), rows_per_sheet):
        chunk = row_images[s_idx : s_idx + rows_per_sheet]
        sheet_img = np.vstack(chunk)
        sp = os.path.join(sheets_dir, f"sheet_{(s_idx // rows_per_sheet) + 1:02d}.jpg")
        cv2.imwrite(sp, sheet_img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        sheet_paths.append(sp)

    summary = {
        "project": kb,
        "total_clips": len(clips),
        "total_elapsed_sec": round(time.time() - t_start_all, 1),
        "contact_sheets": sheet_paths,
        "counts": {
            "currently_masked": sum(1 for r in all_clip_reports if r["existing_masks"]),
            "la_detected_any": sum(1 for r in all_clip_reports if r["la_detections"]),
            "check_false_positive_or_faint": sum(1 for r in all_clip_reports if r["category_flag"] == "CHECK_FALSE_POSITIVE_OR_FAINT_WM"),
            "candidate_missing_mask": sum(1 for r in all_clip_reports if r["category_flag"] == "CANDIDATE_MISSING_MASK"),
            "both_have_boxes": sum(1 for r in all_clip_reports if r["category_flag"] == "BOTH_HAVE_BOXES_CHECK_ALIGNMENT"),
        },
        "clips": all_clip_reports,
    }
    return summary


def main():
    ap = argparse.ArgumentParser(description="LocateAnything-3B Local ONNX INT4 Engine for VisionCut Suite")
    ap.add_argument("--task", required=True, choices=["audit-project", "scan-all-sources", "watermark-scan", "emoji-keyframes", "ocr", "ground", "point"])
    ap.add_argument("--kb", default="kb124", help="Episode ID for audit-project (default kb124)")
    ap.add_argument("--video", help="Path to input video clip")
    ap.add_argument("--image", help="Path to input image")
    ap.add_argument("--impact-sec", type=float, default=1.5, help="Impact timestamp in seconds for emoji-keyframes")
    ap.add_argument("--phrase", default="the head of the falling person", help="Referring expression to locate")
    ap.add_argument("--emoji", default="mnhat_emoji_37.gif", help="Emoji asset name for Track V4")
    ap.add_argument("--token-limit", type=int, default=256, help="Max vision patch tokens (default 256)")
    ap.add_argument("--out-dir", default=r"E:\ITV\_scene\locate_anything_test", help="Output directory")
    args = ap.parse_args()

    engine = LocateAnythingOnnxEngine(in_token_limit=args.token_limit)

    if args.task == "audit-project":
        report = run_project_audit(engine, args.kb, args.out_dir)
        out_json = os.path.join(args.out_dir, f"{args.kb}_locate_anything_audit.json")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(json.dumps(report, indent=2, ensure_ascii=False))

    elif args.task == "scan-all-sources":
        report = run_full_source_scan(engine, args.kb, args.out_dir)
        out_json = os.path.join(args.out_dir, f"{args.kb}_full_source_scan.json")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n[LocateAnything-ONNX] Saved full scan JSON to: {out_json}", flush=True)
        print(json.dumps(report["counts"], indent=2, ensure_ascii=False), flush=True)

    elif args.task == "watermark-scan":
        if not args.video:
            raise ValueError("--video is required for watermark-scan")
        report = run_watermark_scan(engine, args.video, args.out_dir)
        out_json = os.path.join(args.out_dir, f"{Path(args.video).stem}_watermark_report.json")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(json.dumps(report, indent=2, ensure_ascii=False))

    elif args.task == "emoji-keyframes":
        if not args.video:
            raise ValueError("--video is required for emoji-keyframes")
        report = run_emoji_keyframes(engine, args.video, args.impact_sec, args.phrase, args.emoji, args.out_dir)
        out_json = os.path.join(args.out_dir, f"{Path(args.video).stem}_emoji_keyframes.json")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(json.dumps(report, indent=2, ensure_ascii=False))

    elif args.task in ("ocr", "ground", "point"):
        if not args.image:
            raise ValueError("--image is required for single-image tasks")
        t_map = {"ocr": "OCR", "ground": "Grounding", "point": "Pointing"}
        res = engine.infer_image(args.image, task_type=t_map[args.task], category=args.phrase)
        vis_jpg = os.path.join(args.out_dir, f"{Path(args.image).stem}_{args.task}_vis.jpg")
        draw_detections(args.image, res["detections"], vis_jpg, title=f"{args.task.upper()}: '{args.phrase}' ({res['total_sec']}s)")
        res["visual_path"] = vis_jpg
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
