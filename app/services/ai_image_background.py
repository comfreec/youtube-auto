# -*- coding: utf-8 -*-
"""Generate script-related still images and turn them into moving video clips."""

from __future__ import annotations

import base64
import io
import math
import os
import subprocess
from typing import Dict, List, Sequence

import numpy as np
import requests
from imageio_ffmpeg import get_ffmpeg_exe
from loguru import logger
from PIL import Image

from app.config import config
from app.models.schema import VideoAspect
from app.services.license import license_manager
from app.utils import utils


class AIImageServiceError(RuntimeError):
    pass


def _build_prompt(text: str, keywords: Sequence[str]) -> str:
    topic = text.strip().replace("\n", " ")[:700]
    keyword_text = ", ".join(keywords[:4])
    return (
        "Vertical 9:16 editorial illustration for a Korean health and daily-life information short. "
        f"Visually explain this scene: {topic}. Relevant concepts: {keyword_text}. "
        "One clear main subject, friendly trustworthy modern illustration, natural colors, simple background, "
        "accurate everyday objects, suitable for general audiences. Keep the lower third visually quiet for subtitles. "
        "No text, no letters, no numbers, no logo, no watermark, no graphic medical anatomy, no frightening imagery."
    )


def _download_image(prompt: str) -> Image.Image:
    endpoint = str(config.app.get("ai_image_worker_url", "")).rstrip("/")
    if not endpoint:
        raise AIImageServiceError("AI 이미지 서버 주소가 설정되지 않았습니다.")
    credentials = license_manager.get_service_credentials()
    if not credentials:
        raise AIImageServiceError("라이선스 인증정보를 확인할 수 없습니다.")
    try:
        response = requests.post(
            f"{endpoint}/generate",
            json={
                "prompt": prompt,
                "license_key": credentials["license_key"],
                "hardware_id": credentials["hardware_id"],
            },
            timeout=120,
        )
    except requests.RequestException as exc:
        raise AIImageServiceError(f"AI 이미지 서버 연결 실패: {exc}") from exc
    if not response.ok:
        try:
            detail = response.json().get("detail", "")
        except Exception:
            detail = ""
        raise AIImageServiceError(detail or f"AI 이미지 생성 실패 ({response.status_code})")
    try:
        data = response.json()
        raw = base64.b64decode(data["image"])
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise AIImageServiceError("생성된 이미지 형식이 올바르지 않습니다.") from exc


def _target_resolution(video_aspect: VideoAspect | str):
    aspect = VideoAspect(video_aspect)
    if aspect == VideoAspect.landscape:
        return 960, 540
    if aspect == VideoAspect.square:
        return 720, 720
    return 540, 960


def _cover(image: Image.Image, width: int, height: int, zoom: float, drift: float) -> np.ndarray:
    target_ratio = width / height
    source_ratio = image.width / image.height
    if source_ratio >= target_ratio:
        base_h = height
        base_w = math.ceil(base_h * source_ratio)
    else:
        base_w = width
        base_h = math.ceil(base_w / source_ratio)
    scaled = image.resize((math.ceil(base_w * zoom), math.ceil(base_h * zoom)), Image.Resampling.LANCZOS)
    max_x = max(0, scaled.width - width)
    max_y = max(0, scaled.height - height)
    x = int(max_x * (0.5 + 0.18 * drift))
    y = int(max_y * (0.5 - 0.12 * drift))
    return np.asarray(scaled.crop((x, y, x + width, y + height)))


def _render_motion_clip(image: Image.Image, output: str, duration: float, aspect: VideoAspect | str, direction: int) -> None:
    width, height = _target_resolution(aspect)
    fps = 20
    frames = max(1, math.ceil(duration * fps))
    cmd = [get_ffmpeg_exe(), "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264",
           "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart", output]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        assert proc.stdin is not None
        for index in range(frames):
            progress = index / max(1, frames - 1)
            zoom = 1.0 + 0.08 * progress
            drift = direction * (progress - 0.5)
            proc.stdin.write(_cover(image, width, height, zoom, drift).tobytes())
        proc.stdin.close()
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        if proc.wait():
            raise AIImageServiceError(stderr[-1000:])
    except Exception:
        if proc.poll() is None:
            proc.kill()
        raise


def generate_videos_by_segments(task_id: str, segment_infos: List[Dict], video_aspect, minimum_clip_duration: float = 3.0) -> List[Dict]:
    output_dir = utils.task_dir(task_id)
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for position, info in enumerate(segment_infos):
        index = int(info.get("index", position))
        text = str(info.get("segment", ""))
        keywords = [str(item) for item in info.get("keywords", [])]
        required = max(1.0, float(info.get("duration", 3.0)))
        duration = max(required, float(minimum_clip_duration))
        logger.info(f"Generating AI scene image {index + 1}/{len(segment_infos)}")
        image = _download_image(_build_prompt(text, keywords))
        image_path = os.path.join(output_dir, f"ai-scene-{index+1:03d}.jpg")
        image.save(image_path, "JPEG", quality=92)
        clip_path = os.path.join(output_dir, f"ai-scene-{index+1:03d}.mp4")
        _render_motion_clip(image, clip_path, duration, video_aspect, 1 if index % 2 == 0 else -1)
        results.append({"segment_index": index, "segment_text": text, "keywords": keywords,
                        "video_paths": [clip_path], "image_path": image_path,
                        "required_duration": required, "actual_duration": duration})
    return results
