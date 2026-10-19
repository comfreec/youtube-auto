# -*- coding: utf-8 -*-
"""Generate script-related still images and turn them into moving video clips."""

from __future__ import annotations

import base64
import io
import math
import os
import subprocess
import threading
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


class AIImageQuotaError(AIImageServiceError):
    """Raised when the remote image service has no free allocation left."""


_ocr_reader = None
_ocr_lock = threading.Lock()


def _contains_visible_text(image: Image.Image) -> bool:
    """Detect text-like regions so generated gibberish can be rejected."""
    global _ocr_reader
    try:
        import easyocr

        with _ocr_lock:
            if _ocr_reader is None:
                _ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
            preview = image.copy()
            preview.thumbnail((720, 720), Image.Resampling.LANCZOS)
            detections = _ocr_reader.readtext(
                np.asarray(preview),
                detail=1,
                paragraph=False,
                min_size=7,
                text_threshold=0.35,
                low_text=0.20,
                link_threshold=0.25,
            )
        suspicious = [
            (str(text).strip(), float(confidence))
            for _, text, confidence in detections
            if len(str(text).strip()) >= 2 and float(confidence) >= 0.15
        ]
        if suspicious:
            logger.warning(f"AI image rejected because text was detected: {suspicious[:3]}")
            return True
    except Exception as exc:
        # OCR is a quality gate, not a reason to abort the whole video.
        logger.warning(f"AI image text check unavailable: {exc}")
    return False


def _download_text_free_image(prompt: str, attempts: int = 2) -> Image.Image:
    image = None
    for attempt in range(1, attempts + 1):
        retry_rule = ""
        if attempt > 1:
            retry_rule = (
                " Previous candidate contained writing. Use an even simpler scene with only the main subject "
                "against a plain background. Include no text-bearing objects or surface markings whatsoever."
            )
        image = _download_image(prompt + retry_rule)
        if not _contains_visible_text(image):
            return image
        logger.info(f"Regenerating text-free AI image ({attempt}/{attempts})")
    raise AIImageServiceError("글자가 없는 이미지를 생성하지 못했습니다. 다시 시도해주세요.")


def _build_prompt(text: str, keywords: Sequence[str]) -> str:
    topic = text.strip().replace("\n", " ")[:700]
    keyword_text = ", ".join(keywords[:4])
    return (
        f"MAIN VISUAL SUBJECT THAT MUST BE SHOWN CLEARLY: {topic}. "
        f"The central objects must directly represent these concepts: {keyword_text}. "
        "ABSOLUTELY NO TEXT OR WRITING ANYWHERE IN THE IMAGE. "
        "No letters, words, numbers, captions, labels, logos, watermarks, signs, packaging text, "
        "book text, phone text, or screen interface. Do not include books, paper, documents, newspapers, "
        "magazines, phones, computer screens, televisions, signboards, posters, charts, printed clothing, "
        "product packaging, bottles with labels, or any object likely to contain writing. "
        "Use blank unbranded objects and completely blank surfaces only. "
        "Create a vertical 9:16 cinematic macro 3D health-explainer scene for a Korean short video. "
        "Communicate the requested subject literally and immediately without written language. "
        "Use premium product-commercial quality CGI, physically based realistic materials, crisp macro detail, "
        "shallow depth of field, dramatic but soft studio lighting, a clean dark-to-neutral gradient background, "
        "and one strong focal subject filling most of the frame. Use realistic food and everyday objects. "
        "For body or medical concepts, use elegant non-graphic anatomical cutaways, translucent layers, "
        "subtle colored particles, and clean scientific visualization that is understandable at a glance. "
        "The result should feel current, premium, trustworthy, cinematic, and educational. "
        "No cute mascots, no faces on organs or bacteria, no cartoon people, no toy-like plastic look, "
        "no clay animation, no old-fashioned clip art, no cheap stock illustration, no flat vector graphics, "
        "no photorealistic gore, no busy collage, no harsh saturation, no thick outlines, and no visual clutter. "
        "Keep the lower third calm and uncluttered for subtitles. General-audience friendly, "
        "no graphic anatomy and no frightening imagery. Again: the final image must contain zero visible text."
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
        message = detail or f"AI 이미지 생성 실패 ({response.status_code})"
        normalized = message.lower()
        if response.status_code == 429 or any(
            marker in normalized
            for marker in ("무료 이미지 한도", "daily free allocation", "quota", "3036")
        ):
            raise AIImageQuotaError(message)
        raise AIImageServiceError(message)
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


def _cover(
    image: Image.Image,
    width: int,
    height: int,
) -> np.ndarray:
    target_ratio = width / height
    source_ratio = image.width / image.height
    if source_ratio >= target_ratio:
        base_h = height
        base_w = math.ceil(base_h * source_ratio)
    else:
        base_w = width
        base_h = math.ceil(base_w / source_ratio)
    scaled = image.resize((base_w, base_h), Image.Resampling.LANCZOS)
    max_x = max(0, scaled.width - width)
    max_y = max(0, scaled.height - height)
    x = int(max_x * 0.5)
    y = int(max_y * 0.5)
    return np.asarray(scaled.crop((x, y, x + width, y + height)))


def _render_motion_clip(image: Image.Image, output: str, duration: float, aspect: VideoAspect | str) -> None:
    width, height = _target_resolution(aspect)
    fps = 24
    frames = max(1, math.ceil(duration * fps))
    cmd = [get_ffmpeg_exe(), "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264",
           "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart", output]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        assert proc.stdin is not None
        # A truly fixed frame is clearer behind moving subtitles and avoids
        # integer-pixel pan judder on slowly moving portrait images.
        frame = _cover(image, width, height).tobytes()
        for _ in range(frames):
            proc.stdin.write(frame)
        proc.stdin.close()
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        if proc.wait():
            raise AIImageServiceError(stderr[-1000:])
    except Exception:
        if proc.poll() is None:
            proc.kill()
        raise


def generate_videos_by_segments(task_id: str, segment_infos: List[Dict], video_aspect, minimum_clip_duration: float = 3.0) -> List[Dict]:
    from app.services import llm

    output_dir = utils.task_dir(task_id)
    os.makedirs(output_dir, exist_ok=True)
    results = []
    last_successful_image = None
    quota_exhausted = False
    for position, info in enumerate(segment_infos):
        index = int(info.get("index", position))
        text = str(info.get("segment", ""))
        keywords = [str(item) for item in info.get("keywords", [])]
        required = max(1.0, float(info.get("duration", 3.0)))
        duration = max(required, float(minimum_clip_duration))
        logger.info(f"Generating AI scene image {index + 1}/{len(segment_infos)}")
        # The image model follows concrete English scene descriptions much
        # more accurately. This translation is used only for the visual prompt;
        # the video's narration and subtitles remain in the original language.
        visual_text = llm.translate_to_english(text)
        visual_keywords_text = llm.translate_to_english(", ".join(keywords))
        visual_keywords = [
            item.strip()
            for item in visual_keywords_text.split(",")
            if item.strip()
        ] or keywords
        try:
            if quota_exhausted:
                image = last_successful_image.copy()
            else:
                image = _download_text_free_image(_build_prompt(visual_text, visual_keywords))
                last_successful_image = image.copy()
        except AIImageQuotaError as exc:
            # Once Cloudflare reports the daily limit, every additional request
            # would fail and waste time. Stop requesting immediately and reuse
            # the last successful visual for the rest of this video.
            quota_exhausted = True
            if last_successful_image is None:
                raise
            logger.warning(
                f"AI image quota exhausted at scene {index + 1}; "
                "reusing the previous image without further generation requests"
            )
            image = last_successful_image.copy()
        except Exception as exc:
            # A temporary limit or a single rejected image must not discard all
            # AI scenes that were already created and silently switch the whole
            # video back to stock footage. Reuse the latest successful scene for
            # the remaining duration; stock fallback is used only when no AI
            # image could be created at all.
            if last_successful_image is None:
                raise
            logger.warning(
                f"AI scene {index + 1} failed ({exc}); reusing the previous AI image instead of stock footage"
            )
            image = last_successful_image.copy()
        image_path = os.path.join(output_dir, f"ai-scene-{index+1:03d}.jpg")
        image.save(image_path, "JPEG", quality=92)
        clip_path = os.path.join(output_dir, f"ai-scene-{index+1:03d}.mp4")
        _render_motion_clip(image, clip_path, duration, video_aspect)
        results.append({"segment_index": index, "segment_text": text, "keywords": keywords,
                        "video_paths": [clip_path], "image_path": image_path,
                        "required_duration": required, "actual_duration": duration})
    return results
