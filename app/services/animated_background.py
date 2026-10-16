# -*- coding: utf-8 -*-
"""Offline, procedural background clips for script-matched videos.

This module is deliberately independent from the stock-video providers.  It
creates small MP4 clips with Pillow/numpy and the ffmpeg binary already bundled
with MoviePy, so it needs neither an API key nor an internet connection.
"""

from __future__ import annotations

import hashlib
import math
import os
import subprocess
from typing import Dict, List, Sequence, Tuple

import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe
from loguru import logger
from PIL import Image, ImageDraw

from app.models.schema import VideoAspect
from app.utils import utils


Color = Tuple[int, int, int]

_THEMES = {
    "health": ((13, 54, 65), (31, 163, 148), (153, 246, 228)),
    "food": ((72, 34, 20), (239, 108, 75), (255, 220, 120)),
    "exercise": ((35, 24, 75), (124, 75, 210), (255, 118, 117)),
    "sleep": ((12, 18, 55), (54, 72, 150), (244, 226, 140)),
    "home": ((38, 48, 62), (66, 135, 160), (255, 196, 112)),
    "technology": ((10, 35, 58), (24, 118, 176), (91, 224, 255)),
    "nature": ((20, 57, 38), (48, 139, 87), (180, 232, 150)),
    "money": ((36, 52, 39), (76, 139, 81), (255, 214, 91)),
    "general": ((28, 30, 56), (78, 86, 170), (137, 220, 235)),
}

_THEME_WORDS = {
    "health": ("건강", "혈압", "혈당", "심장", "병원", "의사", "약", "health", "heart", "medical"),
    "food": ("음식", "식사", "요리", "과일", "채소", "야채", "영양", "food", "fruit", "meal", "diet"),
    "exercise": ("운동", "걷기", "달리기", "스트레칭", "근육", "체조", "exercise", "fitness", "walk", "running"),
    "sleep": ("수면", "잠", "밤", "피로", "휴식", "sleep", "night", "rest"),
    "home": ("생활", "집", "청소", "세탁", "주방", "욕실", "home", "house", "daily", "lifestyle"),
    "technology": ("스마트폰", "컴퓨터", "인터넷", "앱", "기술", "phone", "computer", "technology", "digital"),
    "nature": ("자연", "숲", "나무", "꽃", "바다", "하늘", "nature", "forest", "ocean", "flower"),
    "money": ("돈", "금액", "절약", "가격", "재테크", "money", "saving", "price", "finance"),
}


def _pick_theme(text: str, keywords: Sequence[str]) -> str:
    haystack = f"{text} {' '.join(keywords)}".lower()
    scores = {name: sum(haystack.count(word) for word in words) for name, words in _THEME_WORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "general"


def _resolution(video_aspect: VideoAspect | str) -> Tuple[int, int]:
    aspect = VideoAspect(video_aspect)
    # Half-resolution source keeps offline rendering practical. The existing
    # compositor performs the final high-quality scale to the output size.
    if aspect == VideoAspect.landscape:
        return 960, 540
    if aspect == VideoAspect.square:
        return 720, 720
    return 540, 960


def _blend(a: Color, b: Color, amount: float) -> Color:
    return tuple(int(a[i] * (1.0 - amount) + b[i] * amount) for i in range(3))


def _draw_symbol(draw: ImageDraw.ImageDraw, theme: str, cx: int, cy: int, size: int, color: Color, phase: float) -> None:
    s = size
    width = max(4, s // 15)
    if theme == "health":
        points = [(cx-s, cy), (cx-s//2, cy), (cx-s//3, cy-s//2), (cx, cy+s//2),
                  (cx+s//3, cy-s//3), (cx+s//2, cy), (cx+s, cy)]
        draw.line(points, fill=color, width=width, joint="curve")
    elif theme == "food":
        draw.ellipse((cx-s, cy-s//3, cx+s, cy+s//2), outline=color, width=width)
        draw.arc((cx-s, cy-s, cx+s, cy+s//3), 10, 170, fill=color, width=width)
        for dx in (-s//2, 0, s//2):
            draw.ellipse((cx+dx-s//8, cy-s//5, cx+dx+s//8, cy+s//20), fill=color)
    elif theme == "exercise":
        bob = int(math.sin(phase) * s * 0.12)
        draw.ellipse((cx-s//5, cy-s+bob, cx+s//5, cy-3*s//5+bob), outline=color, width=width)
        draw.line((cx, cy-3*s//5+bob, cx, cy+s//5), fill=color, width=width)
        draw.line((cx, cy-s//3, cx-s*3//4, cy), fill=color, width=width)
        draw.line((cx, cy-s//3, cx+s*3//4, cy-s//2), fill=color, width=width)
        draw.line((cx, cy+s//5, cx-s//2, cy+s), fill=color, width=width)
        draw.line((cx, cy+s//5, cx+s*3//4, cy+s*3//4), fill=color, width=width)
    elif theme == "sleep":
        draw.ellipse((cx-s, cy-s, cx+s, cy+s), fill=color)
        draw.ellipse((cx-s//2, cy-s*6//5, cx+s*6//5, cy+s*3//5), fill=_THEMES[theme][1])
        for i in range(3):
            x = cx + s + i*s//3
            y = cy - s + (i % 2)*s//3
            draw.ellipse((x, y, x+width, y+width), fill=color)
    elif theme == "home":
        draw.polygon([(cx-s, cy), (cx, cy-s), (cx+s, cy), (cx+s*4//5, cy),
                      (cx+s*4//5, cy+s), (cx-s*4//5, cy+s), (cx-s*4//5, cy)], outline=color)
        draw.rectangle((cx-s//5, cy+s//3, cx+s//5, cy+s), outline=color, width=width)
    elif theme == "technology":
        draw.rounded_rectangle((cx-s, cy-s, cx+s, cy+s), radius=s//8, outline=color, width=width)
        draw.rectangle((cx-s*4//5, cy-s*3//4, cx+s*4//5, cy+s//2), outline=color, width=width)
        draw.ellipse((cx-width, cy+s*2//3-width, cx+width, cy+s*2//3+width), fill=color)
    elif theme == "nature":
        draw.ellipse((cx-s, cy-s//2, cx+s//5, cy+s), outline=color, width=width)
        draw.ellipse((cx-s//5, cy-s, cx+s, cy+s//2), outline=color, width=width)
        draw.line((cx-s//2, cy+s//2, cx+s//2, cy-s//2), fill=color, width=width)
    elif theme == "money":
        draw.ellipse((cx-s, cy-s, cx+s, cy+s), outline=color, width=width)
        draw.line((cx-s//2, cy-s//3, cx+s//2, cy-s//3), fill=color, width=width)
        draw.line((cx-s//2, cy+s//3, cx+s//2, cy+s//3), fill=color, width=width)
        draw.line((cx-s//3, cy-s*2//3, cx-s//3, cy+s*2//3), fill=color, width=width)
        draw.line((cx+s//3, cy-s*2//3, cx+s//3, cy+s*2//3), fill=color, width=width)
    else:
        for i in range(3):
            radius = int(s * (0.3 + i * 0.25) + math.sin(phase+i) * s * 0.05)
            draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), outline=color, width=width)


def _make_frame(width: int, height: int, theme: str, seed: int, t: float, duration: float) -> np.ndarray:
    dark, mid, accent = _THEMES[theme]
    phase = 2 * math.pi * (t / max(duration, 0.1))
    top = np.array(_blend(dark, mid, 0.22 + 0.08 * math.sin(phase)), dtype=np.float32)
    bottom = np.array(_blend(mid, dark, 0.48), dtype=np.float32)
    gradient = np.linspace(0, 1, height, dtype=np.float32)[:, None, None]
    frame = np.broadcast_to(top, (height, width, 3)) * (1-gradient) + np.broadcast_to(bottom, (height, width, 3)) * gradient
    image = Image.fromarray(np.uint8(np.clip(frame, 0, 255)), "RGB")
    draw = ImageDraw.Draw(image, "RGBA")

    rng = np.random.default_rng(seed)
    for i in range(12):
        radius = int(rng.uniform(width * 0.025, width * 0.11))
        speed = rng.uniform(0.03, 0.11)
        x = int((rng.uniform(0, width) + math.sin(phase * speed * 8 + i) * width * 0.08) % width)
        y = int((rng.uniform(0, height) - t * height * speed) % (height + 2*radius) - radius)
        alpha = int(rng.uniform(18, 48))
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(*accent, alpha))

    pulse = 1.0 + 0.06 * math.sin(phase * 2)
    symbol_size = int(min(width, height) * 0.20 * pulse)
    _draw_symbol(draw, theme, width//2, int(height*0.45), symbol_size, (*accent,), phase * 2)

    # Soft moving foreground waves give the clip depth without competing with subtitles.
    for band in range(2):
        points = []
        base = int(height * (0.78 + band * 0.08))
        amp = int(height * (0.018 + band * 0.01))
        for x in range(-20, width+21, 20):
            y = base + int(math.sin(x/width*math.pi*2 + phase + band) * amp)
            points.append((x, y))
        points += [(width+20, height), (-20, height)]
        draw.polygon(points, fill=(*accent, 28 + band*18))
    return np.asarray(image)


def _render_clip(path: str, duration: float, video_aspect: VideoAspect | str, theme: str, seed: int) -> str:
    width, height = _resolution(video_aspect)
    fps = 20
    duration = max(1.0, float(duration))
    frame_count = max(1, math.ceil(duration * fps))
    cmd = [
        get_ffmpeg_exe(), "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart", path,
    ]
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        assert process.stdin is not None
        for index in range(frame_count):
            process.stdin.write(_make_frame(width, height, theme, seed, index/fps, duration).tobytes())
        process.stdin.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        return_code = process.wait()
        if return_code:
            raise RuntimeError(stderr[-1200:])
    except Exception:
        if process.poll() is None:
            process.kill()
        raise
    return path


def generate_videos_by_segments(
    task_id: str,
    segment_infos: List[Dict],
    video_aspect: VideoAspect | str = VideoAspect.portrait,
    minimum_clip_duration: float = 3.0,
) -> List[Dict]:
    """Create one content-themed animation clip for every script segment."""
    output_dir = utils.task_dir(task_id)
    os.makedirs(output_dir, exist_ok=True)
    results = []
    logger.info(f"Generating {len(segment_infos)} offline animation background clips")
    for position, info in enumerate(segment_infos):
        index = int(info.get("index", position))
        text = str(info.get("segment", ""))
        keywords = [str(v) for v in info.get("keywords", [])]
        required_duration = max(1.0, float(info.get("duration", 3.0)))
        # The legacy compositor intentionally ignores source clips shorter than
        # its configured clip size. Pad only the generated source duration so
        # even a very short script remains compatible with that unchanged path.
        duration = max(required_duration, float(minimum_clip_duration))
        theme = _pick_theme(text, keywords)
        digest = hashlib.sha256(f"{task_id}:{index}:{text}".encode("utf-8")).hexdigest()
        seed = int(digest[:8], 16)
        clip_path = os.path.join(output_dir, f"anim-{index+1:03d}-{theme}.mp4")
        _render_clip(clip_path, duration, video_aspect, theme, seed)
        results.append({
            "segment_index": index, "segment_text": text, "keywords": keywords,
            "video_paths": [clip_path], "required_duration": required_duration,
            "actual_duration": duration, "theme": theme,
        })
        logger.info(f"Animation segment {index+1}: theme={theme}, duration={duration:.1f}s")
    return results
