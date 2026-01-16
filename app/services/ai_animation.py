"""
AI 애니메이션 생성 서비스
이미지를 애니메이션 영상으로 변환
"""

import os
import time
from typing import Optional, Literal
from loguru import logger
import numpy as np
from PIL import Image


AnimationEffect = Literal["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down", "static"]


def create_ken_burns_effect(
    image_path: str,
    duration: float = 5.0,
    effect: AnimationEffect = "zoom_in",
    output_path: Optional[str] = None
) -> Optional[str]:
    """
    Ken Burns 효과 (줌, 팬 등)를 적용하여 이미지를 애니메이션으로 변환
    
    Args:
        image_path: 입력 이미지 경로
        duration: 애니메이션 지속 시간 (초)
        effect: 애니메이션 효과 종류
        output_path: 출력 비디오 경로 (None이면 자동 생성)
        
    Returns:
        생성된 비디오 파일 경로 또는 None
    """
    try:
        logger.info(f"🎬 Creating animation from image: {effect} effect")
        
        from moviepy.video.VideoClip import VideoClip
        
        # 이미지 로드
        img = Image.open(image_path)
        img_array = np.array(img)
        h, w = img_array.shape[:2]
        
        fps = 30
        total_frames = int(duration * fps)
        
        def make_frame(t):
            """각 프레임 생성 함수"""
            progress = t / duration  # 0.0 ~ 1.0
            frame = img_array.copy()
            
            if effect == "zoom_in":
                # 줌인 효과 (1.0 -> 1.3배)
                zoom_factor = 1.0 + progress * 0.3
                new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
                y1, x1 = (h - new_h) // 2, (w - new_w) // 2
                cropped = frame[y1:y1+new_h, x1:x1+new_w]
                img_pil = Image.fromarray(cropped)
                img_pil = img_pil.resize((w, h), Image.Resampling.LANCZOS)
                return np.array(img_pil)
                
            elif effect == "zoom_out":
                # 줌아웃 효과 (1.3 -> 1.0배)
                zoom_factor = 1.3 - progress * 0.3
                new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
                y1, x1 = max(0, (h - new_h) // 2), max(0, (w - new_w) // 2)
                y2, x2 = min(h, y1 + new_h), min(w, x1 + new_w)
                cropped = frame[y1:y2, x1:x2]
                img_pil = Image.fromarray(cropped)
                img_pil = img_pil.resize((w, h), Image.Resampling.LANCZOS)
                return np.array(img_pil)
                
            elif effect == "pan_right":
                # 오른쪽으로 팬
                shift = int(progress * w * 0.15)  # 15% 이동
                result = np.zeros_like(frame)
                if shift < w:
                    result[:, :w-shift] = frame[:, shift:]
                    result[:, w-shift:] = frame[:, -1:]  # 마지막 픽셀로 채우기
                return result
                
            elif effect == "pan_left":
                # 왼쪽으로 팬
                shift = int(progress * w * 0.15)
                result = np.zeros_like(frame)
                if shift < w:
                    result[:, shift:] = frame[:, :w-shift]
                    result[:, :shift] = frame[:, :1]  # 첫 픽셀로 채우기
                return result
                
            elif effect == "pan_up":
                # 위로 팬
                shift = int(progress * h * 0.15)
                result = np.zeros_like(frame)
                if shift < h:
                    result[shift:, :] = frame[:h-shift, :]
                    result[:shift, :] = frame[:1, :]
                return result
                
            elif effect == "pan_down":
                # 아래로 팬
                shift = int(progress * h * 0.15)
                result = np.zeros_like(frame)
                if shift < h:
                    result[:h-shift, :] = frame[shift:, :]
                    result[h-shift:, :] = frame[-1:, :]
                return result
            
            else:  # static
                return frame
        
        # VideoClip 생성
        clip = VideoClip(make_frame, duration=duration)
        
        # 출력 경로 설정
        if output_path is None:
            from app.utils import utils
            video_dir = utils.storage_dir("ai_animations", create=True)
            timestamp = int(time.time())
            output_path = os.path.join(video_dir, f"animation_{timestamp}.mp4")
        
        # 비디오 저장
        clip.write_videofile(
            output_path,
            fps=fps,
            codec='libx264',
            audio=False,
            preset='medium',
            logger=None
        )
        
        clip.close()
        
        logger.success(f"✅ Animation created: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"❌ Failed to create animation: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_animation_from_images(
    image_paths: list[str],
    durations: list[float],
    effects: list[AnimationEffect],
    output_path: Optional[str] = None
) -> Optional[str]:
    """
    여러 이미지를 애니메이션으로 변환하여 하나의 비디오로 결합
    
    Args:
        image_paths: 이미지 경로 리스트
        durations: 각 이미지의 지속 시간 리스트
        effects: 각 이미지에 적용할 효과 리스트
        output_path: 출력 비디오 경로
        
    Returns:
        생성된 비디오 파일 경로 또는 None
    """
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.video.compositing.concatenate import concatenate_videoclips
        
        logger.info(f"🎬 Creating animation from {len(image_paths)} images")
        
        clips = []
        for i, (image_path, duration, effect) in enumerate(zip(image_paths, durations, effects)):
            logger.info(f"Processing image {i+1}/{len(image_paths)}: {effect}")
            
            # 임시 애니메이션 생성
            temp_path = create_ken_burns_effect(image_path, duration, effect)
            if temp_path:
                clip = VideoFileClip(temp_path)
                clips.append(clip)
        
        if not clips:
            logger.error("No clips created")
            return None
        
        # 클립 결합
        final_clip = concatenate_videoclips(clips, method="compose")
        
        # 출력 경로 설정
        if output_path is None:
            from app.utils import utils
            video_dir = utils.storage_dir("ai_animations", create=True)
            timestamp = int(time.time())
            output_path = os.path.join(video_dir, f"animation_combined_{timestamp}.mp4")
        
        # 비디오 저장
        final_clip.write_videofile(
            output_path,
            fps=30,
            codec='libx264',
            audio=False,
            preset='medium',
            logger=None
        )
        
        # 정리
        for clip in clips:
            clip.close()
        final_clip.close()
        
        logger.success(f"✅ Combined animation created: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"❌ Failed to create combined animation: {e}")
        return None


def get_random_effect() -> AnimationEffect:
    """랜덤 애니메이션 효과 반환"""
    import random
    effects: list[AnimationEffect] = ["zoom_in", "zoom_out", "pan_left", "pan_right"]
    return random.choice(effects)

