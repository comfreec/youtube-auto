"""
애니메이션 영상 생성 서비스
대본을 기반으로 AI 이미지를 생성하고 애니메이션으로 변환하여 영상 제작
"""

import os
from typing import Optional, List
from loguru import logger
from app.services import ai_image, ai_animation, llm
from app.models.schema import MaterialInfo


def generate_image_prompts_from_script(
    script: str,
    segment_count: int = 5,
    style: str = "cinematic"
) -> List[str]:
    """
    대본으로부터 이미지 생성 프롬프트 추출
    
    Args:
        script: 영상 대본
        segment_count: 생성할 이미지 개수
        style: 이미지 스타일
        
    Returns:
        이미지 생성 프롬프트 리스트
    """
    try:
        logger.info(f"📝 Generating {segment_count} image prompts from script")
        
        # LLM을 사용하여 대본에서 시각적 장면 추출
        prompt = f"""
다음 대본을 {segment_count}개의 시각적 장면으로 나누고, 각 장면을 표현하는 이미지 생성 프롬프트를 영어로 작성해주세요.

대본:
{script}

스타일: {style}

각 프롬프트는 다음 형식으로 작성:
1. [장면 설명을 영어로, 구체적이고 시각적으로]
2. [장면 설명을 영어로, 구체적이고 시각적으로]
...

프롬프트는 반드시 영어로 작성하고, 구체적인 시각적 요소(색상, 조명, 구도 등)를 포함해주세요.
"""
        
        response = llm.generate_script(
            video_subject=prompt,
            language="en-US",
            paragraph_number=1
        )
        
        if not response:
            logger.warning("Failed to generate prompts from LLM, using fallback")
            return generate_fallback_prompts(script, segment_count, style)
        
        # 프롬프트 파싱
        prompts = []
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            # 번호 제거 (1., 2., - 등)
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # 번호와 점, 대시 등 제거
                cleaned = line.lstrip('0123456789.-•) ').strip()
                if cleaned:
                    # 스타일 프리픽스 추가
                    enhanced = ai_image.enhance_prompt_for_animation(cleaned, style)
                    prompts.append(enhanced)
        
        # 목표 개수만큼 조정
        if len(prompts) < segment_count:
            logger.warning(f"Only {len(prompts)} prompts generated, duplicating to reach {segment_count}")
            while len(prompts) < segment_count:
                prompts.append(prompts[len(prompts) % len(prompts)])
        elif len(prompts) > segment_count:
            prompts = prompts[:segment_count]
        
        logger.success(f"✅ Generated {len(prompts)} image prompts")
        return prompts
        
    except Exception as e:
        logger.error(f"❌ Failed to generate prompts: {e}")
        return generate_fallback_prompts(script, segment_count, style)


def generate_fallback_prompts(script: str, count: int, style: str) -> List[str]:
    """폴백 프롬프트 생성"""
    base_prompts = [
        "beautiful landscape with mountains and sky",
        "abstract colorful background with flowing shapes",
        "peaceful nature scene with trees and water",
        "inspiring sunrise over the horizon",
        "modern minimalist design with geometric patterns"
    ]
    
    prompts = []
    for i in range(count):
        base = base_prompts[i % len(base_prompts)]
        enhanced = ai_image.enhance_prompt_for_animation(base, style)
        prompts.append(enhanced)
    
    return prompts


def generate_animation_materials(
    script: str,
    segment_count: int = 5,
    style: str = "cinematic",
    duration_per_segment: float = 5.0,
    aspect_ratio: str = "9:16"
) -> List[MaterialInfo]:
    """
    대본으로부터 애니메이션 영상 소재 생성
    
    Args:
        script: 영상 대본
        segment_count: 생성할 세그먼트 개수
        style: 이미지 스타일
        duration_per_segment: 각 세그먼트 지속 시간
        aspect_ratio: 영상 비율 (9:16, 16:9 등)
        
    Returns:
        생성된 애니메이션 영상 MaterialInfo 리스트
    """
    try:
        logger.info(f"🎨 Generating {segment_count} animation materials")
        
        # 1. 이미지 프롬프트 생성
        prompts = generate_image_prompts_from_script(script, segment_count, style)
        
        # 2. 이미지 크기 설정 (비율에 따라)
        if aspect_ratio == "9:16":
            width, height = 1080, 1920
        elif aspect_ratio == "16:9":
            width, height = 1920, 1080
        else:
            width, height = 1080, 1920
        
        # 3. 이미지 생성
        logger.info(f"🎨 Generating {len(prompts)} images...")
        image_paths = []
        for i, prompt in enumerate(prompts):
            logger.info(f"Generating image {i+1}/{len(prompts)}: {prompt[:50]}...")
            image_path = ai_image.generate_image_pollinations(
                prompt=prompt,
                width=width,
                height=height,
                model="flux"
            )
            if image_path:
                image_paths.append(image_path)
            else:
                logger.warning(f"Failed to generate image {i+1}, skipping")
        
        if not image_paths:
            logger.error("No images generated")
            return []
        
        # 4. 이미지를 애니메이션으로 변환
        logger.info(f"🎬 Converting {len(image_paths)} images to animations...")
        materials = []
        for i, image_path in enumerate(image_paths):
            effect = ai_animation.get_random_effect()
            logger.info(f"Creating animation {i+1}/{len(image_paths)}: {effect}")
            
            video_path = ai_animation.create_ken_burns_effect(
                image_path=image_path,
                duration=duration_per_segment,
                effect=effect
            )
            
            if video_path:
                material = MaterialInfo()
                material.provider = "ai_animation"
                material.url = video_path
                material.duration = duration_per_segment
                materials.append(material)
            else:
                logger.warning(f"Failed to create animation {i+1}")
        
        logger.success(f"✅ Generated {len(materials)} animation materials")
        return materials
        
    except Exception as e:
        logger.error(f"❌ Failed to generate animation materials: {e}")
        return []


def test_animation_generation():
    """애니메이션 생성 테스트"""
    script = """
    성공하는 사람들은 아침에 일찍 일어납니다.
    그들은 명확한 목표를 가지고 있습니다.
    매일 조금씩 발전하는 것이 중요합니다.
    긍정적인 마인드로 하루를 시작하세요.
    """
    
    materials = generate_animation_materials(
        script=script,
        segment_count=4,
        style="cinematic",
        duration_per_segment=5.0,
        aspect_ratio="9:16"
    )
    
    print(f"\n✅ Generated {len(materials)} animation materials:")
    for i, material in enumerate(materials):
        print(f"{i+1}. {material.url}")


if __name__ == "__main__":
    test_animation_generation()
