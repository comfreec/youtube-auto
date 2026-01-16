"""
AI 이미지 생성 서비스
무료 AI API를 사용하여 텍스트 프롬프트로부터 이미지 생성
"""

import requests
import urllib.parse
import os
import time
from typing import Optional
from loguru import logger
from app.utils import utils


def generate_image_pollinations(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    model: str = "flux",
    seed: Optional[int] = None,
    enhance: bool = True
) -> Optional[str]:
    """
    Pollinations.ai를 사용하여 이미지 생성
    
    Args:
        prompt: 이미지 생성 프롬프트
        width: 이미지 너비 (기본: 1024)
        height: 이미지 높이 (기본: 1024)
        model: 사용할 모델 (flux, turbo 등)
        seed: 랜덤 시드 (재현성을 위해)
        enhance: 프롬프트 자동 개선 여부
        
    Returns:
        생성된 이미지 파일 경로 또는 None
    """
    try:
        logger.info(f"🎨 Generating image with Pollinations.ai: {prompt[:50]}...")
        
        # 시드가 없으면 랜덤 생성
        if seed is None:
            import random
            seed = random.randint(1, 999999)
        
        # URL 인코딩
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Pollinations.ai 이미지 생성 URL
        # https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&seed={seed}&model={model}&enhance={enhance}
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        params = {
            "width": width,
            "height": height,
            "seed": seed,
            "model": model,
            "enhance": "true" if enhance else "false",
            "nologo": "true"  # 로고 제거
        }
        
        # 이미지 다운로드
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        
        # 이미지 저장
        image_dir = utils.storage_dir("ai_images", create=True)
        timestamp = int(time.time())
        image_path = os.path.join(image_dir, f"ai_image_{timestamp}_{seed}.png")
        
        with open(image_path, "wb") as f:
            f.write(response.content)
        
        logger.success(f"✅ Image generated: {image_path}")
        return image_path
        
    except Exception as e:
        logger.error(f"❌ Failed to generate image: {e}")
        return None


def generate_image_batch(
    prompts: list[str],
    width: int = 1024,
    height: int = 1024,
    model: str = "flux"
) -> list[str]:
    """
    여러 프롬프트로 배치 이미지 생성
    
    Args:
        prompts: 이미지 생성 프롬프트 리스트
        width: 이미지 너비
        height: 이미지 높이
        model: 사용할 모델
        
    Returns:
        생성된 이미지 파일 경로 리스트
    """
    image_paths = []
    
    for i, prompt in enumerate(prompts):
        logger.info(f"🎨 Generating image {i+1}/{len(prompts)}")
        image_path = generate_image_pollinations(
            prompt=prompt,
            width=width,
            height=height,
            model=model
        )
        
        if image_path:
            image_paths.append(image_path)
        
        # API 레이트 리밋 방지
        if i < len(prompts) - 1:
            time.sleep(2)
    
    return image_paths


def enhance_prompt_for_animation(prompt: str, style: str = "cinematic") -> str:
    """
    애니메이션에 적합하도록 프롬프트 개선
    
    Args:
        prompt: 원본 프롬프트
        style: 스타일 (cinematic, anime, cartoon, realistic 등)
        
    Returns:
        개선된 프롬프트
    """
    style_prefixes = {
        "cinematic": "cinematic, dramatic lighting, high quality, detailed, professional",
        "anime": "anime style, vibrant colors, detailed, high quality, studio ghibli inspired",
        "cartoon": "cartoon style, colorful, fun, expressive, high quality",
        "realistic": "photorealistic, highly detailed, 8k, professional photography",
        "fantasy": "fantasy art, magical, ethereal, detailed, high quality",
        "scifi": "sci-fi, futuristic, high-tech, detailed, cinematic"
    }
    
    prefix = style_prefixes.get(style, style_prefixes["cinematic"])
    enhanced = f"{prefix}, {prompt}"
    
    return enhanced
