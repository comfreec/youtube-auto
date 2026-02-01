import os
import time
import requests
import urllib.parse
import random
from loguru import logger
from PIL import Image
from io import BytesIO
from typing import Optional

def generate_ai_image(prompt, style="realistic"):
    """AI 이미지 생성 (Gemini + Pollinations, 폴백 없음)"""
    logger.info("🎨 AI 이미지 생성 시작 (Gemini + Pollinations)")
    
    try:
        logger.info(f"🤖 이미지 생성 요청: {prompt[:50]}...")
        
        # Gemini로 프롬프트 향상 (필수)
        enhanced_prompt = _enhance_prompt_with_gemini(prompt, style)
        logger.success("✅ Gemini 프롬프트 향상 성공")
        
        # Pollinations API로 이미지 생성
        logger.info("🎯 Pollinations API로 이미지 생성...")
        result = _generate_with_pollinations(enhanced_prompt, style)
        if result:
            logger.success("✅ AI 이미지 생성 성공!")
            return result
        else:
            logger.error("❌ Pollinations API 이미지 생성 실패")
            raise Exception("POLLINATIONS_API_FAILED: Pollinations API에서 이미지 생성에 실패했습니다. API 키를 확인하거나 잠시 후 다시 시도해주세요.")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ AI 이미지 생성 실패: {e}")
        raise e


def _enhance_prompt_with_gemini(prompt: str, style: str) -> str:
    """Gemini로 프롬프트 향상"""
    try:
        from app.config import config
        import google.generativeai as genai
        
        # API 키 설정 (첫 번째 유효한 키 사용)
        api_keys = [
            config.app.get("gemini_api_key"),
            config.app.get("gemini_api_key_2"),
            config.app.get("gemini_api_key_3"),
            config.app.get("gemini_api_key_4"),
            config.app.get("gemini_api_key_5")
        ]
        valid_keys = [key for key in api_keys if key and key.strip()]
        
        if not valid_keys:
            raise Exception("No valid Gemini API keys")
        
        # 첫 번째 키로 시도
        genai.configure(api_key=valid_keys[0])
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        enhancement_prompt = f"""
다음 한국어 프롬프트를 {style} 스타일의 고품질 AI 이미지 생성을 위한 영어 프롬프트로 향상시켜주세요.

원본 프롬프트: {prompt}
스타일: {style}

요구사항:
1. 영어로 번역
2. {style} 스타일에 맞는 키워드 추가
3. 고품질 이미지를 위한 기술적 키워드 포함
4. 1080x1920 세로형 비율에 적합하게
5. 간결하고 명확하게 (200자 이내)

향상된 프롬프트만 출력하세요:
"""
        
        response = model.generate_content(
            enhancement_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=100,
                temperature=0.3
            )
        )
        
        if response and response.text:
            enhanced = response.text.strip()
            logger.info(f"🤖 Gemini 향상 프롬프트: {enhanced[:100]}...")
            return enhanced
        else:
            raise Exception("Empty Gemini response")
            
    except Exception as e:
        logger.warning(f"⚠️ Gemini 프롬프트 향상 실패: {e}")
        raise e



def _generate_with_pollinations(enhanced_prompt: str, style: str) -> Optional[str]:
    """정상적인 Pollinations API 이미지 생성"""
    try:
        from app.config import config
        
        # API 키 확인
        api_keys = [
            config.app.get("pollinations_api_key"),
            config.app.get("pollinations_api_key_2"),
            config.app.get("pollinations_api_key_3")
        ]
        
        # 유효한 API 키 필터링
        valid_keys = [key for key in api_keys if key and key.strip()]
        
        if not valid_keys:
            logger.error("❌ Pollinations API 키가 없습니다")
            return None
        
        # 키 로테이션으로 시도 (더 관대한 재시도)
        for i, api_key in enumerate(valid_keys):
            logger.info(f"🔑 API 키 #{i+1} 시도: {api_key[:8]}...{api_key[-4:]}")
            
            # 각 키당 최대 3번 재시도
            for retry in range(3):
                try:
                    unique_seed = int(time.time() * 1000) % 1000000 + random.randint(1000, 9999) + retry * 100
                    encoded_prompt = urllib.parse.quote(f"{enhanced_prompt.strip()}, unique_{unique_seed}")
                    
                    # URL 길이 제한
                    if len(encoded_prompt) > 1500:
                        words = enhanced_prompt.strip().split()
                        truncated_prompt = " ".join(words[:40])
                        encoded_prompt = urllib.parse.quote(f"{truncated_prompt}, unique_{unique_seed}")
                    
                    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                    params = {
                        "width": 1080,
                        "height": 1920,
                        "seed": unique_seed,
                        "model": "flux",
                        "enhance": "true",
                        "nologo": "true",
                        "private": "true",
                        "apikey": api_key.strip()
                    }
                    
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                    
                    # 더 긴 타임아웃 (45초)
                    response = requests.get(url, params=params, headers=headers, timeout=45)
                    
                    if response.status_code == 200 and len(response.content) > 10000:
                        # 할당량 초과 이미지 체크
                        if _is_rate_limit_image(response.content):
                            logger.warning(f"⚠️ API 키 #{i+1} 할당량 초과 (재시도 {retry+1}/3)")
                            if retry < 2:  # 마지막 재시도가 아니면 잠시 대기
                                time.sleep(2)
                                continue
                            else:
                                break  # 다음 키로
                        
                        # 정상 이미지 저장
                        from app.utils import utils
                        img = Image.open(BytesIO(response.content))
                        image_dir = utils.storage_dir("ai_images", create=True)
                        timestamp = int(time.time())
                        filepath = os.path.join(image_dir, f"pollinations_{unique_seed}_{timestamp}.png")
                        img.save(filepath, "PNG")
                        
                        logger.success(f"✅ Pollinations API 성공 (키 #{i+1}, 재시도 {retry+1}): {filepath}")
                        return filepath
                    else:
                        logger.warning(f"⚠️ API 키 #{i+1} 실패 (재시도 {retry+1}/3): {response.status_code}")
                        if retry < 2:
                            time.sleep(1)  # 재시도 전 잠시 대기
                            continue
                        
                except requests.exceptions.Timeout:
                    logger.warning(f"⏰ API 키 #{i+1} 타임아웃 (재시도 {retry+1}/3, 45초)")
                    if retry < 2:
                        time.sleep(2)
                        continue
                except Exception as e:
                    logger.warning(f"⚠️ API 키 #{i+1} 오류 (재시도 {retry+1}/3): {e}")
                    if retry < 2:
                        time.sleep(1)
                        continue
        
        logger.error("❌ 모든 Pollinations API 키 실패")
        return None
            
    except Exception as e:
        logger.error(f"❌ Pollinations API 전체 실패: {e}")
        return None


def _is_rate_limit_image(image_data: bytes) -> bool:
    """할당량 초과 이미지 감지 (더 정확한 감지)"""
    try:
        file_size = len(image_data)
        
        # 할당량 초과 이미지 크기 체크 (더 많은 패턴)
        known_rate_limit_sizes = [
            1396239, 1396240, 1396238, 1396237, 1396241,  # 기존 패턴
            1395000, 1397000, 1400000, 1390000,  # 유사 크기 범위
            512000, 1024000, 2048000  # 다른 할당량 초과 패턴
        ]
        
        # 정확한 크기 매칭
        if file_size in known_rate_limit_sizes:
            logger.error(f"❌ 할당량 초과 이미지 감지 (정확한 크기): {file_size:,} bytes")
            return True
        
        # 크기 범위 체크 (1.39MB ~ 1.40MB 범위)
        if 1390000 <= file_size <= 1400000:
            logger.warning(f"⚠️ 의심스러운 크기 범위: {file_size:,} bytes")
            
            # 이미지 내용 분석으로 2차 확인
            try:
                img = Image.open(BytesIO(image_data))
                width, height = img.size
                
                # 할당량 초과 이미지는 보통 1024x1024 크기
                if width == 1024 and height == 1024:
                    logger.error(f"❌ 할당량 초과 이미지 확인: {width}x{height}, {file_size:,} bytes")
                    return True
                    
                # 너무 작은 이미지도 의심
                if width < 500 or height < 500:
                    logger.error(f"❌ 너무 작은 이미지 (할당량 초과 의심): {width}x{height}")
                    return True
                    
            except Exception as img_error:
                logger.warning(f"⚠️ 이미지 분석 실패: {img_error}")
                # 이미지를 열 수 없으면 할당량 초과로 간주
                return True
        
        # 너무 작은 파일 크기 (10KB 미만)
        if file_size < 10000:
            logger.error(f"❌ 파일 크기가 너무 작음 (할당량 초과 의심): {file_size:,} bytes")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ 할당량 초과 이미지 감지 실패: {e}")
        return True  # 오류 시 안전하게 할당량 초과로 간주


# 호환성 함수들
def check_ai_services_status():
    """AI 서비스 상태 체크 (Gemini 활성화)"""
    logger.info("🔍 Gemini API 상태 체크 활성화")
    
    try:
        from app.config import config
        import google.generativeai as genai
        
        # API 키 확인
        api_keys = [
            config.app.get("gemini_api_key"),
            config.app.get("gemini_api_key_2"),
            config.app.get("gemini_api_key_3"),
            config.app.get("gemini_api_key_4"),
            config.app.get("gemini_api_key_5")
        ]
        valid_keys = [key for key in api_keys if key and key.strip()]
        
        if not valid_keys:
            return {
                "gemini": {
                    "quota_available": False, 
                    "status": "no_keys", 
                    "message": "API keys not configured"
                }
            }
        
        # 첫 번째 키로 간단한 테스트
        try:
            genai.configure(api_key=valid_keys[0])
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            response = model.generate_content(
                "Hi", 
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=5,
                    temperature=0.1
                )
            )
            
            if response and response.text:
                return {
                    "gemini": {
                        "quota_available": True, 
                        "status": "available", 
                        "message": f"{len(valid_keys)} keys available"
                    }
                }
            else:
                return {
                    "gemini": {
                        "quota_available": False, 
                        "status": "error", 
                        "message": "Empty response"
                    }
                }
                
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "limit" in error_msg or "exceeded" in error_msg:
                return {
                    "gemini": {
                        "quota_available": False, 
                        "status": "quota_exceeded", 
                        "message": "Quota exceeded"
                    }
                }
            else:
                return {
                    "gemini": {
                        "quota_available": False, 
                        "status": "error", 
                        "message": f"API error: {str(e)[:50]}..."
                    }
                }
                
    except Exception as e:
        return {
            "gemini": {
                "quota_available": False, 
                "status": "error", 
                "message": f"Check failed: {str(e)[:50]}..."
            }
        }

def get_ai_generator():
    """AI 이미지 생성기 반환 (정상적인 생성만)"""
    class NormalAIGenerator:
        def generate_image(self, prompt, style="realistic"):
            return generate_ai_image(prompt, style)
    
    return NormalAIGenerator()

def generate_image_pollinations(prompt, **kwargs):
    return generate_ai_image(prompt, kwargs.get("style", "realistic"))

def generate_images_batch(prompts, **kwargs):
    return [generate_ai_image(prompt, kwargs.get("style", "realistic")) for prompt in prompts]

def enhance_prompt_for_animation(prompt, style="cinematic"):
    return f"{prompt}, {style}, high quality, detailed, 1080x1920 portrait"