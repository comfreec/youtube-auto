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
    
    # Multi-API key rotation for better quota management
    if llm_provider == "gemini":
        gemini_keys = [
            config.app.get("gemini_api_key"),
            config.app.get("gemini_api_key_2"),
            config.app.get("gemini_api_key_3"),
        ]
        gemini_keys = [k for k in gemini_keys if k]  # Remove None values
        
        if not gemini_keys:
            logger.error("No Gemini API keys configured")
            raise Exception("No Gemini API keys available")
        
        # Try each key until one works
        for i, api_key in enumerate(gemini_keys):
            try:
                logger.info(f"Trying Gemini API key {i+1}/{len(gemini_keys)}")
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                
                model_name = config.app.get("gemini_model_name", "gemini-2.5-flash")
                target_model = model_name.strip()
                models_to_try = [
                    target_model,
                    "gemini-2.5-flash",
                    "gemini-flash-latest",
                    "gemini-2.0-flash",
                    "gemini-2.0-flash-exp",
                ]
                
                for m in models_to_try:
                    try:
                        logger.info(f"Using Gemini model: {m}")
                        model = genai.GenerativeModel(m)
                        response = model.generate_content(prompt)
                        if response and getattr(response, "text", None):
                            logger.info(f"Success with API key {i+1} and model {m}")
                            return response.text
                    except Exception as e_try:
                        logger.warning(f"Gemini model {m} failed: {e_try}")
                        if "429" in str(e_try) or "Quota exceeded" in str(e_try):
                            logger.warning(f"API key {i+1} quota exceeded, trying next key...")
                            break
                        continue
                        
            except Exception as e:
                logger.warning(f"Gemini API key {i+1} failed: {e}")
                continue
        
        # If all Gemini keys fail, fall back to DeepSeek
        logger.warning("All Gemini keys failed, falling back to DeepSeek")
        llm_provider = "deepseek"
    
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
    # 언어별 프롬프트 설정
    if language == "ko-KR" or language == "auto":
        prompt = f"""
        주제 '{video_subject}'에 대한 유튜브 쇼츠용 대본을 작성해주세요.

        요구사항:
        1. {paragraph_number}개의 문단으로 구성
        2. 각 문단은 2-3문장으로 작성
        3. 총 길이는 60-90초 분량 (약 150-200자)
        4. 인사말(안녕하세요, 여러분, 시청자 여러분 등) 사용 금지
        5. 바로 본론으로 시작
        6. 구체적이고 실용적인 내용
        7. 감정적이고 매력적인 표현 사용
        8. 시청자의 관심을 끌 수 있는 내용
        9. 마크다운 형식(**, ##, - 등) 사용 금지
        10. 장면 설명([장면 1] 등) 사용 금지
        11. 순수한 텍스트만 작성

        스타일: 직접적이고 임팩트 있게, 인사말 없이 바로 핵심 내용으로 시작

        주제: {video_subject}

        대본을 작성해주세요:
        """
    else:
        prompt = f"""
        Write a YouTube Shorts script about '{video_subject}'.

        Requirements:
        1. {paragraph_number} paragraphs
        2. Each paragraph: 2-3 sentences
        3. Total length: 60-90 seconds (about 150-200 words)
        4. NO greetings (Hello, Hi everyone, Welcome, etc.)
        5. Start directly with the main content
        6. Specific and practical information
        7. Engaging and emotional language
        8. Content that captures viewer attention
        9. NO markdown formatting (**, ##, - etc.)
        10. NO scene descriptions ([Scene 1] etc.)
        11. Plain text only

        Style: Direct and impactful, start immediately with core content

        Subject: {video_subject}

        Write the script:
        """
    
    # Check if subject is empty
    if not video_subject:
        return ""

    final_script = ""
    for i in range(_max_retries):
        try:
            response = _generate_response(prompt)
            if response:
                script = response.strip()
                
                # 인사말 제거 로직
                script = _remove_greetings(script, language)
                
                # 마크다운 형식 제거
                script = _clean_markdown_formatting(script)
                
                final_script = script
                break
        except Exception as e:
            logger.error(f"failed to generate script: {e}")
            
    if not final_script:
        return "AI 대본 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."
        
    return final_script

def generate_terms(video_subject: str, video_script: str, amount: int = 5) -> List[str]:
    logger.info(f"Starting keyword generation for subject: {video_subject}")
    
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
        logger.info("Attempting to generate keywords using LLM...")
        response = _generate_response(prompt)
        logger.info(f"LLM response: {response}")
        
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
            logger.info(f"Cleaned response: {cleaned}")
            
            # Extract terms
            terms = [t.strip() for t in cleaned.split(",") if t.strip()]
            logger.info(f"Extracted terms: {terms}")
            
            # Filter and validate terms
            valid_terms = []
            for term in terms:
                term = term.strip().lower()
                # Skip if too long or contains non-English characters
                if len(term.split()) <= 3 and term.isascii() and len(term) > 2:
                    # Skip common stop words
                    if not any(stop_word in term for stop_word in ["the", "and", "or", "but", "with", "for"]):
                        valid_terms.append(term)
            
            logger.info(f"Valid terms after filtering: {valid_terms}")
            
            if len(valid_terms) >= 2:
                logger.info(f"Generated English keywords: {valid_terms[:amount]}")
                return valid_terms[:amount]
                
    except Exception as e:
        logger.error(f"failed to generate terms: {e}")
    
    # Enhanced fallback with better English keyword extraction
    logger.warning("LLM failed to generate terms. Using enhanced fallback.")
    return _generate_fallback_keywords(video_subject, video_script, amount)

def _generate_fallback_keywords(video_subject: str, video_script: str, amount: int = 5) -> List[str]:
    """Generate fallback keywords when LLM fails"""
    logger.info(f"Generating fallback keywords for subject: '{video_subject}' and script length: {len(video_script)}")
    
    fallback_keywords = []
    
    # Subject-based keywords
    subject_lower = video_subject.lower()
    script_lower = video_script.lower()
    
    # Enhanced Korean to English keyword mapping
    subject_keywords = {
        "성공": ["success", "achievement", "business", "winner", "celebration"],
        "건강": ["health", "fitness", "wellness", "exercise", "nutrition"],
        "돈": ["money", "finance", "wealth", "investment", "cash"],
        "투자": ["investment", "trading", "finance", "stock market", "business"],
        "다이어트": ["diet", "weight loss", "fitness", "healthy eating", "workout"],
        "운동": ["exercise", "workout", "fitness", "gym", "sports"],
        "독서": ["reading", "books", "education", "learning", "study"],
        "공부": ["study", "learning", "education", "school", "knowledge"],
        "음식": ["food", "cooking", "nutrition", "kitchen", "meal"],
        "여행": ["travel", "vacation", "adventure", "tourism", "journey"],
        "사랑": ["love", "relationship", "romance", "couple", "heart"],
        "가족": ["family", "home", "togetherness", "children", "parents"],
        "일": ["work", "office", "career", "job", "business"],
        "스트레스": ["stress", "relaxation", "meditation", "calm", "peace"],
        "행복": ["happiness", "joy", "celebration", "smile", "positive"],
        "시간": ["time", "clock", "schedule", "planning", "productivity"],
        "자연": ["nature", "landscape", "outdoor", "forest", "mountains"],
        "기술": ["technology", "innovation", "digital", "computer", "modern"],
        "음악": ["music", "sound", "audio", "instruments", "melody"],
        "영화": ["movie", "cinema", "entertainment", "film", "video"],
        "게임": ["gaming", "play", "entertainment", "fun", "competition"],
        "요리": ["cooking", "kitchen", "food", "chef", "recipe"],
        "패션": ["fashion", "style", "clothing", "design", "trendy"],
        "뷰티": ["beauty", "skincare", "cosmetics", "makeup", "care"],
        "교육": ["education", "learning", "teaching", "school", "knowledge"],
        "창업": ["startup", "business", "entrepreneur", "innovation", "success"],
        "부동산": ["real estate", "property", "investment", "house", "building"],
        "자동차": ["car", "automotive", "driving", "vehicle", "transportation"],
        "반려동물": ["pet", "animal", "dog", "cat", "care"],
        "육아": ["parenting", "children", "family", "baby", "care"],
        "결혼": ["wedding", "marriage", "couple", "love", "ceremony"],
        "취업": ["job", "career", "employment", "work", "interview"]
    }
    
    # Find matching keywords from subject
    for korean, english_list in subject_keywords.items():
        if korean in subject_lower:
            fallback_keywords.extend(english_list[:3])  # Take first 3 from each match
            logger.info(f"Found subject keyword '{korean}' -> {english_list[:3]}")
    
    # Find matching keywords from script
    for korean, english_list in subject_keywords.items():
        if korean in script_lower and korean not in subject_lower:  # Avoid duplicates
            fallback_keywords.extend(english_list[:2])  # Take fewer from script
            logger.info(f"Found script keyword '{korean}' -> {english_list[:2]}")
    
    # Add generic visual keywords based on common themes
    if not fallback_keywords:
        logger.info("No specific keywords found, using generic keywords")
        fallback_keywords = ["lifestyle", "people", "modern", "business", "success"]
    
    # Add some universal keywords that work well for stock footage
    universal_keywords = ["lifestyle", "modern", "people", "business", "professional"]
    for keyword in universal_keywords:
        if keyword not in fallback_keywords:
            fallback_keywords.append(keyword)
    
    # Remove duplicates and limit
    unique_keywords = []
    seen = set()
    for keyword in fallback_keywords:
        if keyword.lower() not in seen:
            unique_keywords.append(keyword.lower())
            seen.add(keyword.lower())
    
    # Ensure we have enough keywords
    if len(unique_keywords) < amount:
        additional_keywords = ["creative", "inspiration", "motivation", "growth", "innovation"]
        for keyword in additional_keywords:
            if keyword not in seen and len(unique_keywords) < amount:
                unique_keywords.append(keyword)
                seen.add(keyword)
    
    result = unique_keywords[:amount]
    logger.info(f"Final fallback keywords: {result}")
    return result

def generate_english_script(video_subject: str, paragraph_number: int = 4) -> str:
    """Generate English script directly (for when translation fails)"""
    logger.info(f"Generating English script for subject: {video_subject}")
    
    prompt = f"""
    Create an engaging English script for a short video (60-90 seconds) about: {video_subject}

    REQUIREMENTS:
    1. Write {paragraph_number} paragraphs
    2. Each paragraph should be 2-3 sentences
    3. Use simple, clear English suitable for global audience
    4. Make it engaging and motivational
    5. Focus on practical tips or insights
    6. Use active voice and conversational tone
    7. No special formatting, just plain text

    STYLE: Motivational, educational, accessible to international viewers
    
    Subject: {video_subject}
    
    Write the script now:
    """
    
    try:
        response = _generate_response(prompt)
        if response and len(response.strip()) > 50:
            # Clean up the response
            script = response.strip()
            
            # Remove common prefixes
            prefixes = ["Here's", "Here is", "Script:", "The script", "Sure", "Certainly"]
            for prefix in prefixes:
                if script.startswith(prefix):
                    script = script[len(prefix):].strip()
                    if script.startswith(":"):
                        script = script[1:].strip()
            
            logger.info(f"Generated English script: {script[:100]}...")
            return script
            
    except Exception as e:
        logger.error(f"Failed to generate English script: {e}")
    
    # Fallback English script template
    logger.warning("Using fallback English script template")
    fallback_script = f"""
    Today we're exploring {video_subject}. This topic can transform your daily life in meaningful ways.

    Many successful people have discovered the power of focusing on what truly matters. Small changes in your routine can lead to remarkable results over time.

    The key is to start with simple, actionable steps. Don't try to change everything at once. Instead, pick one area and commit to consistent improvement.

    Remember, every expert was once a beginner. Your journey toward {video_subject} starts with a single decision to take action today.
    """
    
    return fallback_script.strip()
    
def translate_to_english(text: str) -> str:
    if not text:
        return ""
    
    # 이미 영어인지 확인 (한글이 없으면 영어로 간주)
    import re
    if not re.search(r'[가-힣]', text):
        return text
    
    prompt = f"Translate the following Korean text into natural English. Return ONLY the translated text without any quotes, notes, or explanations:\n\n{text}"
    
    try:
        # 1차 시도: 메인 LLM 사용
        response = _generate_response(prompt)
        if response and response.strip() != text and not re.search(r'[가-힣]', response):
            logger.info(f"Successfully translated using main LLM: '{text}' -> '{response.strip()}'")
            return response.strip()
    except Exception as e:
        logger.warning(f"Main LLM failed for translation: {e}")
    
    logger.info("Main LLM failed for translation, trying free provider fallback...")
    
    try:
        # 2차 시도: 무료 제공자 사용
        response = _generate_free_response(prompt)
        if response and response.strip() != text and not re.search(r'[가-힣]', response):
            logger.info(f"Successfully translated using free provider: '{text}' -> '{response.strip()}'")
            return response.strip()
    except Exception as e:
        logger.warning(f"Free provider also failed: {e}")
    
    # 3차 시도: 간단한 키워드 매핑 (백업용)
    try:
        simple_translations = {
            "성공": "success",
            "습관": "habits", 
            "방법": "methods",
            "비법": "secrets",
            "팁": "tips",
            "가이드": "guide",
            "라이프": "life",
            "스타일": "style",
            "건강": "health",
            "다이어트": "diet",
            "운동": "exercise",
            "명상": "meditation",
            "집중": "focus",
            "시간": "time",
            "관리": "management",
            "돈": "money",
            "투자": "investment",
            "부자": "rich",
            "행복": "happiness",
            "사랑": "love",
            "인간관계": "relationships",
            "자신감": "confidence",
            "동기부여": "motivation",
            "영감": "inspiration",
            "창업": "startup",
            "비즈니스": "business",
            "마케팅": "marketing",
            "브랜딩": "branding",
            "소셜미디어": "social media",
            "유튜브": "youtube",
            "콘텐츠": "content",
            "크리에이터": "creator"
        }
        
        # 키워드 기반 번역 시도
        words = text.split()
        translated_words = []
        for word in words:
            # 특수문자 제거하고 매핑 확인
            clean_word = re.sub(r'[^\w가-힣]', '', word)
            if clean_word in simple_translations:
                translated_words.append(simple_translations[clean_word])
            else:
                # 부분 매칭 시도
                found = False
                for ko, en in simple_translations.items():
                    if ko in clean_word:
                        translated_words.append(en)
                        found = True
                        break
                if not found:
                    translated_words.append(word)
        
        if translated_words and len(translated_words) > 0:
            fallback_result = " ".join(translated_words)
            if fallback_result != text:
                logger.info(f"Using fallback translation: '{text}' -> '{fallback_result}'")
                return fallback_result
    except Exception as e:
        logger.warning(f"Fallback translation failed: {e}")
    
    logger.warning("Translation failed or API error, returning original text.")
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

def _remove_greetings(script: str, language: str = "auto") -> str:
    """대본에서 인사말 제거"""
    if not script:
        return script
    
    lines = script.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 한국어 인사말 패턴
        korean_greetings = [
            "안녕하세요", "안녕", "여러분", "시청자 여러분", "구독자 여러분",
            "오늘은", "오늘 영상에서는", "이번 영상에서는", "반갑습니다",
            "환영합니다", "다시 만나뵙습니다", "채널에 오신 것을 환영합니다",
            "오늘도", "다시 한번"
        ]
        
        # 영어 인사말 패턴
        english_greetings = [
            "hello", "hi everyone", "hi there", "welcome", "welcome back",
            "good morning", "good afternoon", "good evening", "hey guys",
            "what's up", "greetings", "welcome to", "hey there", "hi folks",
            "today we", "in today's video", "today i", "today's topic"
        ]
        
        # 인사말로 시작하는 문장 제거
        should_skip = False
        line_lower = line.lower()
        
        if language == "ko-KR" or language == "auto":
            for greeting in korean_greetings:
                if line.startswith(greeting) or greeting in line[:30]:
                    should_skip = True
                    break
        
        if language == "en-US" or not should_skip:
            for greeting in english_greetings:
                if (line_lower.startswith(greeting + " ") or 
                    line_lower.startswith(greeting + ",") or
                    line_lower.startswith(greeting + ".") or
                    line_lower == greeting):
                    should_skip = True
                    break
        
        # 인사말이 아닌 문장만 추가
        if not should_skip:
            cleaned_lines.append(line)
    
    # 결과 조합
    result = '\n'.join(cleaned_lines).strip()
    
    # 빈 결과인 경우 원본 반환 (모든 문장이 인사말인 경우 방지)
    if not result or len(result) < 20:
        # 첫 번째 문장만 제거하고 나머지 반환
        original_lines = script.split('\n')
        if len(original_lines) > 1:
            return '\n'.join(original_lines[1:]).strip()
        else:
            return script
    
    return result
def _clean_markdown_formatting(script: str) -> str:
    """마크다운 형식 제거"""
    if not script:
        return script
    
    import re
    
    # 마크다운 형식 제거
    # ** 볼드 제거
    script = re.sub(r'\*\*(.*?)\*\*', r'\1', script)
    
    # * 이탤릭 제거
    script = re.sub(r'\*(.*?)\*', r'\1', script)
    
    # ## 헤더 제거
    script = re.sub(r'^#{1,6}\s*', '', script, flags=re.MULTILINE)
    
    # - 리스트 제거
    script = re.sub(r'^-\s*', '', script, flags=re.MULTILINE)
    
    # 1. 숫자 리스트 제거
    script = re.sub(r'^\d+\.\s*', '', script, flags=re.MULTILINE)
    
    # [링크](url) 형식 제거
    script = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', script)
    
    # ``` 코드 블록 제거
    script = re.sub(r'```.*?```', '', script, flags=re.DOTALL)
    
    # ` 인라인 코드 제거
    script = re.sub(r'`([^`]+)`', r'\1', script)
    
    # > 인용문 제거
    script = re.sub(r'^>\s*', '', script, flags=re.MULTILINE)
    
    # [장면 1], [장면 2] 등 장면 설명 제거
    script = re.sub(r'\[장면\s*\d+\]', '', script)
    script = re.sub(r'\[Scene\s*\d+\]', '', script)
    
    # 연속된 공백 정리
    script = re.sub(r'\s+', ' ', script)
    
    # 연속된 줄바꿈 정리
    script = re.sub(r'\n\s*\n', '\n\n', script)
    
    return script.strip()