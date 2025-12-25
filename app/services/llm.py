import json
import logging
import re
from collections import Counter
from typing import List, Optional

from loguru import logger
from openai import AzureOpenAI, OpenAI

from app.config import config

_max_retries = 3

def _generate_response(prompt: str) -> str:
    config.reload()
    
    content = ""
    llm_provider = config.app.get("llm_provider", "gemini")
    logger.info(f"llm provider: {llm_provider}")
    # Remove the redirect to gemini for g4f
    if llm_provider in ["pollinations", "free"]:
        llm_provider = "gemini"

    # Standard Providers
    try:
        api_key = config.app.get(f"{llm_provider}_api_key")
        base_url = config.app.get(f"{llm_provider}_base_url")
        model_name = config.app.get(f"{llm_provider}_model_name")
        
        if llm_provider == "openai":
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=model_name or "gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
            
        elif llm_provider == "moonshot":
            client = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")
            response = client.chat.completions.create(
                model=model_name or "moonshot-v1-8k",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
            
        elif llm_provider == "azure":
            client = AzureOpenAI(
                api_key=api_key,
                api_version="2024-02-15-preview",
                azure_endpoint=base_url
            )
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
            
        elif llm_provider == "gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                
                target_model = (model_name or "gemini-2.5-flash").strip()
                models_to_try = [
                    target_model,
                    "gemini-2.5-flash",
                    "gemini-flash-latest",
                    "gemini-2.0-flash",
                    "gemini-2.0-flash-exp",
                ]
                
                last_error = None
                for m in models_to_try:
                    try:
                        logger.info(f"Using Gemini model: {m}")
                        model = genai.GenerativeModel(m)
                        response = model.generate_content(prompt)
                        if response and getattr(response, "text", None):
                            return response.text
                    except Exception as e_try:
                        last_error = e_try
                        logger.warning(f"Gemini model {m} failed: {e_try}")
                        if "429" in str(e_try) or "Quota exceeded" in str(e_try):
                            logger.warning("Gemini Quota Exceeded. Skipping other models.")
                            break
                        continue
                
                try:
                    logger.info("Listing available Gemini models to auto-correct...")
                    available = []
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            available.append(m.name)
                    logger.info(f"Available models: {', '.join(available[:10])}...")
                except Exception as e_list:
                    logger.warning(f"Failed to list Gemini models: {e_list}")
                
                if last_error:
                    raise last_error
            except Exception as e:
                logger.warning(f"Gemini failed ({e})")
                raise e

        # Add other providers as needed (DeepSeek, Qwen, etc usually generic OpenAI)
        elif llm_provider in ["deepseek", "qwen", "ollama", "oneapi", "cloudflare", "ernie", "modelscope"]:
             # Generic OpenAI client
             if not base_url and llm_provider == "ollama":
                 base_url = "http://localhost:11434/v1"
             
             client = OpenAI(api_key=api_key or "dummy", base_url=base_url)
             response = client.chat.completions.create(
                model=model_name or "gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
             return response.choices[0].message.content
             
        elif llm_provider == "g4f":
            try:
                import g4f
                logger.info("Using G4F provider")
                
                # Try multiple providers in order of reliability
                providers_to_try = [
                    g4f.Provider.DuckDuckGo,
                    g4f.Provider.Blackbox,
                    g4f.Provider.Airforce,
                    g4f.Provider.DarkAI,
                ]
                
                for provider in providers_to_try:
                    try:
                        logger.info(f"Trying G4F provider: {provider.__name__}")
                        response = g4f.ChatCompletion.create(
                            model="gpt-3.5-turbo",
                            provider=provider,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        if response and response.strip():
                            logger.info(f"G4F success with {provider.__name__}")
                            return response.strip()
                    except Exception as e:
                        logger.warning(f"G4F provider {provider.__name__} failed: {e}")
                        continue
                
                # If all providers fail, raise the last error
                raise Exception("All G4F providers failed")
                
            except ImportError:
                logger.error("G4F not installed. Install with: pip install g4f")
                raise Exception("G4F not installed")
            except Exception as e:
                logger.error(f"G4F error: {e}")
                raise e

    except Exception as e:
        logger.error(f"LLM {llm_provider} error: {e}")
        raise e
        
    return ""

def generate_script(video_subject: str, language: str = "auto", paragraph_number: int = 1) -> str:
    prompt = f"""
    Write a video script about '{video_subject}'.
    Language: {language}
    Format: Plain text, {paragraph_number} paragraphs.
    Do not include title, scene descriptions, or camera instructions. Just the narration text.
    """
    
    # Check if subject is empty
    if not video_subject:
        return ""

    final_script = ""
    for i in range(_max_retries):
        try:
            response = _generate_response(prompt)
            if response:
                final_script = response.strip()
                break
        except Exception as e:
            logger.error(f"failed to generate script: {e}")
            
    if not final_script:
        return "AI 대본 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."
        
    return final_script

def generate_terms(video_subject: str, video_script: str, amount: int = 5) -> List[str]:
    # Enhanced prompt for better English keyword generation
    prompt = f"""
    You are a professional video editor creating stock footage search keywords.
    
    TASK: Extract {amount} highly relevant ENGLISH keywords for stock video search.
    
    REQUIREMENTS:
    1. Keywords MUST be in English only
    2. Use concrete, visual terms (not abstract concepts)
    3. Focus on scenes, objects, actions that can be filmed
    4. Each keyword should be 1-3 words maximum
    5. Think about what stock footage would match this script
    
    EXAMPLES:
    - If script mentions "성공" → use "business success", "achievement", "celebration"
    - If script mentions "건강" → use "healthy lifestyle", "exercise", "nutrition"
    - If script mentions "돈" → use "money", "finance", "investment"
    
    VIDEO SUBJECT: {video_subject}
    SCRIPT: {video_script[:800]}
    
    Return ONLY a comma-separated list of English keywords:
    """
    
    try:
        response = _generate_response(prompt)
        if response:
            # Clean up the response more aggressively
            cleaned = response.strip()
            
            # Remove common prefixes
            prefixes = ["Here are", "Keywords:", "keywords:", "Sure", "The keywords", "Based on", "For this"]
            for p in prefixes:
                if cleaned.lower().startswith(p.lower()):
                    cleaned = cleaned[len(p):].strip()
                    if cleaned.startswith(":"):
                        cleaned = cleaned[1:].strip()
            
            # Clean formatting
            cleaned = cleaned.replace("\n", ",").replace("- ", "").replace("* ", "").replace('"', '').strip()
            
            # Extract terms
            terms = [t.strip() for t in cleaned.split(",") if t.strip()]
            
            # Filter and validate terms
            valid_terms = []
            for term in terms:
                term = term.strip().lower()
                # Skip if too long or contains non-English characters
                if len(term.split()) <= 3 and term.isascii() and len(term) > 2:
                    # Skip common stop words
                    if not any(stop_word in term for stop_word in ["the", "and", "or", "but", "with", "for"]):
                        valid_terms.append(term)
            
            if len(valid_terms) >= 2:
                logger.info(f"Generated English keywords: {valid_terms[:amount]}")
                return valid_terms[:amount]
                
    except Exception as e:
        logger.error(f"failed to generate terms: {e}")
    
    # Enhanced fallback with better English keyword extraction
    logger.warning("LLM failed to generate terms. Using enhanced fallback.")
    
    # Try to extract meaningful English keywords from subject and script
    fallback_keywords = []
    
    # Subject-based keywords
    subject_lower = video_subject.lower()
    subject_keywords = {
        "성공": ["success", "achievement", "business"],
        "건강": ["health", "fitness", "wellness"],
        "돈": ["money", "finance", "wealth"],
        "투자": ["investment", "trading", "finance"],
        "다이어트": ["diet", "weight loss", "fitness"],
        "운동": ["exercise", "workout", "fitness"],
        "독서": ["reading", "books", "education"],
        "공부": ["study", "learning", "education"],
        "음식": ["food", "cooking", "nutrition"],
        "여행": ["travel", "vacation", "adventure"],
        "사랑": ["love", "relationship", "romance"],
        "가족": ["family", "home", "togetherness"],
        "일": ["work", "office", "career"],
        "스트레스": ["stress", "relaxation", "meditation"],
        "행복": ["happiness", "joy", "celebration"],
        "시간": ["time", "clock", "schedule"],
        "자연": ["nature", "landscape", "outdoor"],
        "기술": ["technology", "innovation", "digital"]
    }
    
    # Find matching keywords
    for korean, english_list in subject_keywords.items():
        if korean in subject_lower:
            fallback_keywords.extend(english_list)
    
    # Add generic visual keywords
    if not fallback_keywords:
        fallback_keywords = ["lifestyle", "people", "modern", "business", "success"]
    
    # Remove duplicates and limit
    unique_keywords = list(dict.fromkeys(fallback_keywords))[:amount]
    logger.info(f"Using fallback English keywords: {unique_keywords}")
    
def translate_to_english(text: str) -> str:
    if not text:
        return ""
    prompt = f"Translate the following Korean text into natural English. Return ONLY the translated text without any quotes, notes, or explanations:\n\n{text}"
    
    try:
        response = _generate_response(prompt)
        if response:
            return response.strip()
    except Exception as e:
        logger.error(f"Translation failed: {e}")
    
    logger.warning("Translation failed, returning original text.")
    return text

def translate_to_korean(text: str) -> str:
    if not text:
        return ""
    prompt = f"Translate the following English text into natural Korean. Return ONLY the translated text without any quotes, notes, or explanations:\n\n{text}"
    try:
        response = _generate_response(prompt)
        if response:
            return response.strip()
    except Exception as e:
        logger.error(f"Translation failed: {e}")
    return text

def translate_terms_to_korean(terms: List[str]) -> List[str]:
    if not terms:
        return []
    joined = ", ".join([t.strip() for t in terms if t])
    if not joined:
        return []
    prompt = f"Translate the following English keywords into Korean. Return ONLY a comma-separated list with no extra words:\n\n{joined}"
    try:
        response = _generate_response(prompt)
        if response:
            cleaned = response.replace("\n", ",").strip()
            out = [t.strip() for t in cleaned.split(",") if t.strip()]
            return out
    except Exception as e:
        logger.error(f"Translation failed: {e}")
    return terms

def translate_terms_to_english(terms: List[str]) -> List[str]:
    if not terms:
        return []
    joined = ", ".join([t.strip() for t in terms if t])
    if not joined:
        return []
    prompt = f"Translate the following keywords into natural English. Return ONLY a comma-separated list with no extra words:\n\n{joined}"
    try:
        response = _generate_response(prompt)
        if response:
            cleaned = response.replace("\n", ",").strip()
            out = [t.strip() for t in cleaned.split(",") if t.strip()]
            return out
    except Exception as e:
        logger.error(f"Translation failed: {e}")
    return terms
def generate_korean_terms(video_subject: str, video_script: str, amount: int = 5) -> List[str]:
    # Korean keyword generation for YouTube tags
    prompt = f"""
    당신은 전문 유튜브 크리에이터입니다.
    
    작업: 다음 영상에 대한 {amount}개의 한국어 YouTube 태그를 생성하세요.
    
    요구사항:
    1. 태그는 한국어로만 작성
    2. YouTube 검색에 효과적인 키워드 사용
    3. 각 태그는 1-3단어로 구성
    4. 구체적이고 검색 가능한 용어 사용
    5. 영상 내용과 직접 관련된 키워드
    
    예시:
    - 주제가 "성공 습관"이면 → "성공법", "좋은습관", "자기계발", "성공마인드"
    - 주제가 "건강 다이어트"이면 → "다이어트", "건강관리", "체중감량", "운동법"
    
    영상 주제: {video_subject}
    영상 대본: {video_script[:800]}
    
    쉼표로 구분된 한국어 태그만 반환하세요:
    """
    
    try:
        response = _generate_response(prompt)
        if response:
            # Clean up the response
            cleaned = response.strip()
            
            # Remove common prefixes
            prefixes = ["태그:", "키워드:", "다음과 같습니다", "생성된 태그"]
            for p in prefixes:
                if cleaned.startswith(p):
                    cleaned = cleaned[len(p):].strip()
                    if cleaned.startswith(":"):
                        cleaned = cleaned[1:].strip()
            
            # Clean formatting
            cleaned = cleaned.replace("\n", ",").replace("- ", "").replace("* ", "").replace('"', '').strip()
            
            # Extract terms
            terms = [t.strip() for t in cleaned.split(",") if t.strip()]
            
            # Filter and validate Korean terms
            valid_terms = []
            for term in terms:
                term = term.strip()
                # Check if contains Korean characters and is reasonable length
                if len(term.split()) <= 3 and len(term) > 1 and re.search("[가-힣]", term):
                    valid_terms.append(term)
            
            if len(valid_terms) >= 2:
                logger.info(f"Generated Korean tags: {valid_terms[:amount]}")
                return valid_terms[:amount]
                
    except Exception as e:
        logger.error(f"failed to generate Korean terms: {e}")
    
    # Enhanced fallback with Korean keywords
    logger.warning("LLM failed to generate Korean terms. Using enhanced fallback.")
    
    # Subject-based Korean keywords
    subject_lower = video_subject.lower()
    korean_keywords = {
        "성공": ["성공법", "성공마인드", "자기계발", "성공습관"],
        "건강": ["건강관리", "건강법", "웰빙", "건강정보"],
        "돈": ["돈버는법", "재테크", "투자", "부자되기"],
        "투자": ["투자법", "재테크", "투자정보", "주식"],
        "다이어트": ["다이어트", "체중감량", "살빼기", "운동법"],
        "운동": ["운동법", "헬스", "피트니스", "건강운동"],
        "독서": ["독서법", "책추천", "독서습관", "책읽기"],
        "공부": ["공부법", "학습법", "공부습관", "효율적공부"],
        "음식": ["요리", "레시피", "맛집", "음식정보"],
        "여행": ["여행정보", "여행팁", "관광", "여행지"],
        "사랑": ["연애", "사랑", "관계", "연애팁"],
        "가족": ["가족", "육아", "부모", "가정"],
        "일": ["직장", "업무", "커리어", "취업"],
        "스트레스": ["스트레스해소", "힐링", "명상", "휴식"],
        "행복": ["행복", "긍정", "마음", "감정"],
        "시간": ["시간관리", "효율성", "생산성", "일정관리"],
        "자연": ["자연", "힐링", "풍경", "환경"],
        "기술": ["기술", "IT", "디지털", "혁신"]
    }
    
    fallback_keywords = []
    for korean, keyword_list in korean_keywords.items():
        if korean in subject_lower:
            fallback_keywords.extend(keyword_list)
    
    # Add generic Korean tags
    if not fallback_keywords:
        fallback_keywords = ["정보", "팁", "노하우", "라이프스타일", "일상"]
    
    # Remove duplicates and limit
    unique_keywords = list(dict.fromkeys(fallback_keywords))[:amount]
    logger.info(f"Using fallback Korean tags: {unique_keywords}")
    
    return unique_keywords