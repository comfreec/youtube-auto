import json
import logging
import re
from collections import Counter
from typing import List, Optional

from loguru import logger
from openai import AzureOpenAI, OpenAI

from app.config import config

_max_retries = 3

def check_api_quota_status():
    """API 할당량 상태 실제 확인 (테스트 호출 포함)"""
    try:
        config.reload()
        
        # Gemini API 키들 실제 상태 확인
        gemini_keys = []
        for i in range(1, 11):  # gemini_api_key, gemini_api_key_2, ..., gemini_api_key_10
            if i == 1:
                key = config.app.get("gemini_api_key")
            else:
                key = config.app.get(f"gemini_api_key_{i}")
            
            if key:
                # 실제 API 호출로 상태 확인
                status = _test_gemini_api_key(key, i)
                gemini_keys.append({
                    "key_num": i,
                    "key_preview": f"{key[:8]}...{key[-4:]}",
                    "available": status["available"],
                    "status": status["message"]
                })
            else:
                gemini_keys.append({
                    "key_num": i,
                    "key_preview": "미설정",
                    "available": False,
                    "status": "미설정"
                })
        
        # OpenAI API 키 실제 상태 확인
        openai_keys = []
        openai_key = config.app.get("openai_api_key")
        if openai_key:
            status = _test_openai_api_key(openai_key)
            openai_keys.append({
                "key_num": 1,
                "key_preview": f"{openai_key[:8]}...{openai_key[-4:]}",
                "available": status["available"],
                "status": status["message"]
            })
        else:
            openai_keys.append({
                "key_num": 1,
                "key_preview": "미설정",
                "available": False,
                "status": "미설정"
            })
        
        return {
            "gemini_keys": gemini_keys,
            "openai_keys": openai_keys
        }
        
    except Exception as e:
        logger.error(f"API quota status check failed: {e}")
        return {
            "gemini_keys": [],
            "openai_keys": []
        }

def _test_gemini_api_key(api_key: str, key_num: int):
    """Gemini API 키 실제 테스트"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # 간단한 테스트 요청
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Hello", 
                                        generation_config=genai.types.GenerationConfig(
                                            max_output_tokens=10,
                                            temperature=0.1
                                        ))
        
        if response and response.text:
            return {
                "available": True,
                "message": "✅ 정상 작동 (할당량 사용 가능)"
            }
        else:
            return {
                "available": False,
                "message": "❌ 응답 없음 (할당량 소진 가능)"
            }
            
    except Exception as e:
        error_msg = str(e).lower()
        if "quota" in error_msg or "limit" in error_msg:
            return {
                "available": False,
                "message": "❌ 할당량 초과"
            }
        elif "invalid" in error_msg or "unauthorized" in error_msg:
            return {
                "available": False,
                "message": "❌ 유효하지 않은 키"
            }
        elif "blocked" in error_msg:
            return {
                "available": False,
                "message": "❌ 차단된 키"
            }
        else:
            return {
                "available": False,
                "message": f"❌ 오류: {str(e)[:50]}..."
            }

def _test_openai_api_key(api_key: str):
    """OpenAI API 키 실제 테스트"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # 간단한 테스트 요청
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
            temperature=0.1
        )
        
        if response and response.choices:
            return {
                "available": True,
                "message": "✅ 정상 작동 (할당량 사용 가능)"
            }
        else:
            return {
                "available": False,
                "message": "❌ 응답 없음"
            }
            
    except Exception as e:
        error_msg = str(e).lower()
        if "quota" in error_msg or "limit" in error_msg:
            return {
                "available": False,
                "message": "❌ 할당량 초과"
            }
        elif "invalid" in error_msg or "unauthorized" in error_msg:
            return {
                "available": False,
                "message": "❌ 유효하지 않은 키"
            }
        else:
            return {
                "available": False,
                "message": f"❌ 오류: {str(e)[:50]}..."
            }

def _generate_response(prompt: str) -> str:
    config.reload()
    
    content = ""
    llm_provider = config.app.get("llm_provider", "gemini")
    logger.info(f"llm provider: {llm_provider}")
    
    # Multi-API key rotation for better quota management
    if llm_provider == "gemini":
        # Collect all available Gemini API keys (up to 10 keys)
        gemini_keys = []
        for i in range(1, 11):  # gemini_api_key, gemini_api_key_2, ..., gemini_api_key_10
            if i == 1:
                key = config.app.get("gemini_api_key")
            else:
                key = config.app.get(f"gemini_api_key_{i}")
            if key:
                gemini_keys.append((i, key))
        
        if not gemini_keys:
            logger.error("No Gemini API keys configured")
            raise Exception("No Gemini API keys available")
        
        logger.info(f"Found {len(gemini_keys)} Gemini API keys for rotation")
        
        # Try each key until one works
        for key_num, api_key in gemini_keys:
            try:
                logger.info(f"Trying Gemini API key #{key_num} ({len(gemini_keys)} total)")
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
                        logger.info(f"Using Gemini model: {m} with API key #{key_num}")
                        model = genai.GenerativeModel(m)
                        response = model.generate_content(prompt)
                        if response and getattr(response, "text", None):
                            logger.success(f"✅ Success with API key #{key_num} and model {m}")
                            return response.text
                    except Exception as e_try:
                        logger.warning(f"Gemini model {m} failed with key #{key_num}: {e_try}")
                        if "429" in str(e_try) or "Quota exceeded" in str(e_try) or "Resource has been exhausted" in str(e_try) or "RESOURCE_EXHAUSTED" in str(e_try):
                            logger.warning(f"🚫 API key #{key_num} quota exceeded, trying next key...")
                            break
                        continue
                        
            except Exception as e:
                logger.warning(f"❌ Gemini API key #{key_num} failed: {e}")
                if "429" in str(e) or "Quota exceeded" in str(e) or "Resource has been exhausted" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    logger.warning(f"🚫 API key #{key_num} quota exceeded")
                continue
        
        # If all Gemini keys fail, fall back to DeepSeek
        logger.error("❌ All Gemini API keys failed or quota exceeded, falling back to DeepSeek")
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
        # paragraph_number에 따른 대본 길이 동적 설정
        if paragraph_number >= 3:
            length_description = "총 길이는 90-120초 분량 (약 300-400자)"
            detail_instruction = "각 문단은 3-4문장으로 구성하여 충분히 상세하게 작성"
        elif paragraph_number >= 2:
            length_description = "총 길이는 60-90초 분량 (약 200-280자)"
            detail_instruction = "각 문단은 3문장으로 구성하여 상세하게 작성"
        else:
            length_description = "총 길이는 30-60초 분량 (약 150-200자)"
            detail_instruction = "각 문단은 2-3문장으로 작성"
        
        prompt = f"""
        주제 '{video_subject}'에 대한 유튜브 쇼츠용 대본을 작성해주세요.

        ⚠️ 중요: 반드시 아래 길이 요구사항을 준수해주세요!

        요구사항:
        1. {paragraph_number}개의 문단으로 구성
        2. {detail_instruction}
        3. {length_description}
        4. 인사말(안녕하세요, 여러분, 시청자 여러분 등) 사용 금지
        5. 바로 본론으로 시작
        6. 구체적이고 실용적인 내용을 풍부하게 포함
        7. 감정적이고 매력적인 표현 사용
        8. 시청자의 관심을 끌 수 있는 내용
        9. 마크다운 형식(**, ##, - 등) 사용 금지
        10. 장면 설명([장면 1] 등) 사용 금지
        11. 순수한 텍스트만 작성
        12. ⚠️ 너무 짧게 작성하지 말고 충분한 길이로 작성할 것

        스타일: 직접적이고 임팩트 있게, 인사말 없이 바로 핵심 내용으로 시작

        주제: {video_subject}

        ⚠️ 다시 한번 강조: {length_description}에 맞게 충분히 길게 작성해주세요!

        대본을 작성해주세요:
        """
    else:
        # paragraph_number에 따른 영어 대본 길이 동적 설정
        if paragraph_number >= 3:
            length_description = "Total length: 90-120 seconds (about 250-350 words)"
            detail_instruction = "Each paragraph: 3-4 sentences with detailed content"
        elif paragraph_number >= 2:
            length_description = "Total length: 60-90 seconds (about 180-250 words)"
            detail_instruction = "Each paragraph: 3 sentences with detailed content"
        else:
            length_description = "Total length: 30-60 seconds (about 120-180 words)"
            detail_instruction = "Each paragraph: 2-3 sentences"
        
        prompt = f"""
        Write a YouTube Shorts script about '{video_subject}'.

        ⚠️ IMPORTANT: Please strictly follow the length requirements below!

        Requirements:
        1. {paragraph_number} paragraphs
        2. {detail_instruction}
        3. {length_description}
        4. NO greetings (Hello, Hi everyone, Welcome, etc.)
        5. Start directly with the main content
        6. Include specific and practical information with rich details
        7. Engaging and emotional language
        8. Content that captures viewer attention
        9. NO markdown formatting (**, ##, - etc.)
        10. NO scene descriptions ([Scene 1] etc.)
        11. Plain text only
        12. ⚠️ Do NOT write too short - write with sufficient length

        Style: Direct and impactful, start immediately with core content

        Subject: {video_subject}

        ⚠️ REMINDER: Please write according to {length_description} with sufficient length!

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
    logger.info(f"Starting enhanced script-content matching keyword generation for subject: {video_subject}")
    
    # 대본 내용을 문장별로 분석하여 더 정확한 키워드 생성
    prompt = f"""
    You are a professional video editor specializing in matching script content with perfect background footage.

    TASK: Analyze the script sentence by sentence and generate English keywords that will find EXACTLY matching stock footage.

    ANALYSIS REQUIREMENTS:
    1. Read each sentence and identify SPECIFIC visual elements mentioned
    2. Convert Korean concepts to English keywords that stock footage sites use
    3. Focus on CONCRETE, FILMABLE elements (not abstract concepts)
    4. Each keyword should be 1-2 words maximum
    5. Prioritize keywords that will find footage matching the script's narrative flow
    6. Avoid generic terms - be SPECIFIC to what's actually mentioned

    SCRIPT CONTENT ANALYSIS:
    Subject: {video_subject}
    Full Script: {video_script}

    DETAILED ANALYSIS PROCESS:
    1. Break down the script into key visual concepts
    2. Identify specific actions, objects, settings, emotions that can be filmed
    3. Convert to English terms commonly used in stock footage
    4. Ensure keywords match the script's tone and message

    EXAMPLES OF GOOD KEYWORD MATCHING:
    - Script mentions "아침 루틴" → keywords: "morning routine", "wake up", "coffee"
    - Script mentions "성공한 사람들" → keywords: "business success", "professional", "achievement"
    - Script mentions "운동하는 방법" → keywords: "workout", "exercise", "fitness training"
    - Script mentions "돈 관리" → keywords: "money management", "finance", "savings"

    Based on the script analysis above, generate {amount} HIGHLY SPECIFIC English keywords that will find footage perfectly matching the script content.
    
    Return ONLY the keywords separated by commas, no explanations:
    """
    
    try:
        logger.info("Generating script-content-matched keywords using advanced LLM analysis...")
        response = _generate_response(prompt)
        logger.info(f"LLM keyword response: {response}")
        
        if response:
            # Clean up the response more aggressively
            cleaned = response.strip()
            
            # Remove common prefixes and formatting
            prefixes = ["keywords:", "Keywords:", "Sure", "The keywords", "Based on", "For this", "Here are", "Analysis:", "Result:"]
            for p in prefixes:
                if cleaned.lower().startswith(p.lower()):
                    cleaned = cleaned[len(p):].strip()
                    if cleaned.startswith(":"):
                        cleaned = cleaned[1:].strip()
            
            # Clean formatting and extract terms
            cleaned = cleaned.replace("\n", ",").replace("- ", "").replace("* ", "").replace('"', '').replace("'", "").strip()
            terms = [t.strip() for t in cleaned.split(",") if t.strip()]
            
            # Enhanced validation for script-content matching
            valid_terms = []
            for term in terms:
                term = term.strip().lower()
                # More strict validation for content matching
                if (len(term.split()) <= 2 and  # Max 2 words for better search results
                    term.isascii() and 
                    len(term) > 2 and
                    # Exclude generic/meta terms
                    not any(generic in term for generic in [
                        "ai generated", "viral", "content", "shorts", "video", "youtube",
                        "script", "keyword", "analysis", "example", "concept"
                    ]) and
                    # Exclude common stop words
                    not any(stop_word in term for stop_word in [
                        "the", "and", "or", "but", "with", "for", "this", "that", "these", "those"
                    ]) and
                    # Ensure it's a concrete, searchable term
                    not term.startswith(("how to", "what is", "why", "when"))):
                    valid_terms.append(term)
            
            logger.info(f"Script-matched valid terms: {valid_terms}")
            
            if len(valid_terms) >= 3:
                # Return the most relevant terms
                final_terms = valid_terms[:amount]
                logger.info(f"Final script-content-matched keywords: {final_terms}")
                return final_terms
                
    except Exception as e:
        logger.error(f"Failed to generate script-content-matched terms: {e}")
    
    # Enhanced fallback with deeper script analysis
    logger.warning("LLM failed. Using enhanced script content analysis fallback...")
    return _generate_enhanced_script_keywords(video_subject, video_script, amount)


def _generate_enhanced_script_keywords(video_subject: str, video_script: str, amount: int = 5) -> List[str]:
    """Enhanced fallback that analyzes script content more deeply"""
    logger.info(f"Performing enhanced script content analysis for: '{video_subject}'")
    
    script_lower = video_script.lower()
    subject_lower = video_subject.lower()
    
    # Comprehensive Korean-to-English mapping with script context analysis
    content_mapping = {
        # Actions and behaviors
        "루틴": ["routine", "daily habits"],
        "습관": ["habits", "lifestyle"],
        "방법": ["method", "technique"],
        "비법": ["secret", "strategy"],
        "팁": ["tips", "advice"],
        "가이드": ["guide", "tutorial"],
        "운동": ["workout", "exercise"],
        "명상": ["meditation", "mindfulness"],
        "집중": ["focus", "concentration"],
        "공부": ["study", "learning"],
        "독서": ["reading", "books"],
        "요리": ["cooking", "kitchen"],
        "청소": ["cleaning", "organization"],
        
        # Emotions and states
        "성공": ["success", "achievement"],
        "행복": ["happiness", "joy"],
        "스트레스": ["stress", "pressure"],
        "피로": ["tired", "exhausted"],
        "에너지": ["energy", "vitality"],
        "자신감": ["confidence", "self-esteem"],
        "동기": ["motivation", "inspiration"],
        
        # Objects and tools
        "돈": ["money", "cash"],
        "투자": ["investment", "finance"],
        "부동산": ["real estate", "property"],
        "자동차": ["car", "vehicle"],
        "핸드폰": ["smartphone", "phone"],
        "컴퓨터": ["computer", "laptop"],
        "책": ["book", "reading"],
        "음식": ["food", "meal"],
        "커피": ["coffee", "cafe"],
        
        # Places and environments
        "집": ["home", "house"],
        "사무실": ["office", "workplace"],
        "카페": ["cafe", "coffee shop"],
        "헬스장": ["gym", "fitness"],
        "도서관": ["library", "study"],
        "공원": ["park", "outdoor"],
        "바다": ["ocean", "beach"],
        "산": ["mountain", "hiking"],
        
        # Time and scheduling
        "아침": ["morning", "sunrise"],
        "저녁": ["evening", "sunset"],
        "밤": ["night", "dark"],
        "주말": ["weekend", "leisure"],
        "휴가": ["vacation", "holiday"],
        "시간": ["time", "clock"],
        
        # Health and wellness
        "건강": ["health", "wellness"],
        "다이어트": ["diet", "weight loss"],
        "영양": ["nutrition", "healthy food"],
        "수면": ["sleep", "rest"],
        "휴식": ["rest", "relaxation"],
        
        # Relationships and social
        "가족": ["family", "together"],
        "친구": ["friends", "social"],
        "연인": ["couple", "romance"],
        "결혼": ["wedding", "marriage"],
        "아이": ["children", "kids"],
        "부모": ["parents", "family"],
        
        # Work and career
        "일": ["work", "business"],
        "회사": ["company", "corporate"],
        "창업": ["startup", "entrepreneur"],
        "면접": ["interview", "job"],
        "승진": ["promotion", "career"],
        "퇴사": ["resignation", "quit job"],
        
        # Technology and modern life
        "AI": ["artificial intelligence", "technology"],
        "디지털": ["digital", "tech"],
        "온라인": ["online", "internet"],
        "소셜미디어": ["social media", "smartphone"],
        "유튜브": ["content creation", "video"],
        "인스타그램": ["social media", "photography"]
    }
    
    # Analyze script content for matching keywords
    matched_keywords = []
    
    # First, look for direct matches in script content
    for korean_term, english_terms in content_mapping.items():
        if korean_term in script_lower:
            matched_keywords.extend(english_terms[:2])  # Take first 2 from each match
            logger.info(f"Found script content match: '{korean_term}' -> {english_terms[:2]}")
    
    # Then, look for subject-based matches
    for korean_term, english_terms in content_mapping.items():
        if korean_term in subject_lower and korean_term not in script_lower:
            matched_keywords.extend(english_terms[:1])  # Take 1 from subject matches
            logger.info(f"Found subject match: '{korean_term}' -> {english_terms[:1]}")
    
    # Remove duplicates while preserving order
    unique_keywords = []
    seen = set()
    for keyword in matched_keywords:
        if keyword.lower() not in seen:
            unique_keywords.append(keyword.lower())
            seen.add(keyword.lower())
    
    # If we don't have enough keywords, add contextual ones
    if len(unique_keywords) < amount:
        contextual_keywords = []
        
        # Add context-based keywords based on script tone and content
        if any(word in script_lower for word in ["성공", "달성", "목표", "이루"]):
            contextual_keywords.extend(["success", "achievement", "goal"])
        if any(word in script_lower for word in ["건강", "운동", "다이어트", "몸"]):
            contextual_keywords.extend(["health", "fitness", "wellness"])
        if any(word in script_lower for word in ["돈", "투자", "부자", "경제"]):
            contextual_keywords.extend(["money", "finance", "wealth"])
        if any(word in script_lower for word in ["시간", "효율", "생산성", "관리"]):
            contextual_keywords.extend(["time", "productivity", "efficiency"])
        if any(word in script_lower for word in ["행복", "만족", "기쁨", "즐거"]):
            contextual_keywords.extend(["happiness", "joy", "satisfaction"])
        
        # Add unique contextual keywords
        for keyword in contextual_keywords:
            if keyword not in seen and len(unique_keywords) < amount:
                unique_keywords.append(keyword)
                seen.add(keyword)
    
    # Final fallback with universal keywords if still not enough
    if len(unique_keywords) < amount:
        universal_keywords = ["lifestyle", "people", "modern", "daily life", "professional"]
        for keyword in universal_keywords:
            if keyword not in seen and len(unique_keywords) < amount:
                unique_keywords.append(keyword)
                seen.add(keyword)
    
    result = unique_keywords[:amount]
    logger.info(f"Enhanced script analysis final keywords: {result}")
    return result

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
    
    # 더 명확한 번역 프롬프트
    prompt = f"""다음 영어 키워드들을 자연스러운 한국어로 번역하세요. 각 키워드는 YouTube 태그로 사용될 예정입니다.

영어 키워드: {joined}

요구사항:
1. 각 키워드를 정확한 한국어로 번역
2. 쉼표로 구분하여 나열
3. 추가 설명이나 번호 없이 키워드만 작성
4. 한국어 검색에 적합한 자연스러운 용어 사용

번역된 한국어 키워드:"""
    
    try:
        response = _generate_response(prompt)
        if response:
            cleaned = response.replace("\n", ",").strip()
            # 불필요한 텍스트 제거
            prefixes = ["번역된 한국어 키워드:", "키워드:", "태그:", "결과:"]
            for prefix in prefixes:
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):].strip()
                    if cleaned.startswith(":"):
                        cleaned = cleaned[1:].strip()
            
            out = [t.strip() for t in cleaned.split(",") if t.strip()]
            
            # 번역 결과 검증 - 한국어가 포함되어 있는지 확인
            import re
            korean_terms = [term for term in out if re.search(r'[가-힣]', term)]
            
            if korean_terms and len(korean_terms) >= len(terms) * 0.5:  # 최소 50% 이상이 한국어여야 함
                logger.info(f"Successfully translated to Korean: {korean_terms}")
                return korean_terms
            else:
                logger.warning(f"Translation quality insufficient, Korean terms: {korean_terms}")
                return []
                
    except Exception as e:
        logger.error(f"Translation failed: {e}")
    
    return []

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
    # Korean keyword generation for YouTube tags based on script content
    prompt = f"""
    당신은 전문 유튜브 크리에이터입니다.
    
    작업: 다음 영상 대본을 분석하여 {amount}개의 한국어 YouTube 태그를 생성하세요.
    
    요구사항:
    1. 대본에서 실제로 언급된 내용만 키워드로 사용
    2. 구체적이고 검색 가능한 한국어 용어
    3. 각 태그는 1-3단어로 구성
    4. 대본의 핵심 메시지와 직접 관련된 키워드
    5. "AI생성", "바이럴", "콘텐츠", "쇼츠" 같은 일반적 태그 사용 금지
    6. 대본에서 언급된 행동, 방법, 결과, 감정에 집중
    
    분석할 내용:
    주제: {video_subject}
    대본: {video_script[:1000]}
    
    대본에서 추출 가능한 키워드 예시:
    - 언급된 구체적인 행동이나 방법
    - 제시된 결과나 효과
    - 나타나는 감정이나 상태
    - 설명된 상황이나 문제
    - 제안된 해결책이나 팁
    
    대본 내용을 바탕으로 한 {amount}개의 한국어 키워드만 쉼표로 구분하여 나열하세요:
    """
    
    try:
        response = _generate_response(prompt)
        if response:
            # Clean up the response
            cleaned = response.strip()
            
            # Remove common prefixes
            prefixes = ["태그:", "키워드:", "다음과 같습니다", "생성된 태그", "분석 결과"]
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
                if (len(term.split()) <= 3 and len(term) > 1 and 
                    re.search("[가-힣]", term) and 
                    # Exclude generic terms
                    not any(generic in term for generic in ["AI생성", "바이럴", "콘텐츠", "쇼츠", "영상", "유튜브"])):
                    valid_terms.append(term)
            
            if len(valid_terms) >= 3:
                logger.info(f"Generated script-based Korean tags: {valid_terms[:amount]}")
                return valid_terms[:amount]
                
    except Exception as e:
        logger.error(f"failed to generate Korean terms: {e}")
    
    # Enhanced fallback with script content analysis
    logger.warning("LLM failed to generate Korean terms. Using script analysis fallback.")
    return _generate_script_based_korean_keywords(video_subject, video_script, amount)

def _generate_script_based_korean_keywords(video_subject: str, video_script: str, amount: int = 5) -> List[str]:
    """대본 내용 분석 기반 한국어 키워드 생성"""
    logger.info(f"Analyzing Korean script content for keyword generation: '{video_subject}'")
    
    import re
    
    # 대본에서 키워드 추출을 위한 패턴 분석
    script_lower = video_script.lower()
    subject_lower = video_subject.lower()
    
    # 대본 내용 기반 한국어 키워드 매핑 (구체적이고 실용적)
    content_keywords = {
        # 행동/방법 관련
        "물마시기": ["물마시기", "수분섭취", "건강습관"],
        "스트레칭": ["스트레칭", "몸풀기", "유연성"],
        "명상": ["명상", "마음챙김", "정신건강"],
        "호흡": ["호흡법", "심호흡", "마음안정"],
        "걷기": ["걷기운동", "산책", "유산소"],
        "운동": ["운동법", "헬스", "체력관리"],
        "요리": ["요리법", "음식만들기", "건강식"],
        "독서": ["독서법", "책읽기", "지식습득"],
        "기록": ["기록하기", "일기쓰기", "계획세우기"],
        
        # 결과/효과 관련
        "집중력": ["집중력향상", "몰입", "생산성"],
        "효율": ["효율성", "시간관리", "생산성"],
        "변화": ["변화", "개선", "성장"],
        "성과": ["성과", "결과", "달성"],
        "건강": ["건강관리", "웰빙", "체력"],
        
        # 감정/상태 관련
        "스트레스": ["스트레스관리", "스트레스해소", "마음관리"],
        "행복": ["행복", "긍정", "만족"],
        "자신감": ["자신감", "자존감", "마인드"],
        "평온": ["평온", "안정", "휴식"],
        
        # 시간/루틴 관련
        "아침": ["아침루틴", "모닝", "하루시작"],
        "저녁": ["저녁루틴", "하루마무리", "휴식"],
        "하루": ["일상", "루틴", "생활패턴"],
        "습관": ["좋은습관", "습관만들기", "라이프스타일"],
        
        # 구체적 방법/팁
        "방법": ["방법", "노하우", "팁"],
        "비법": ["비법", "꿀팁", "노하우"],
        "단계": ["단계별", "순서", "과정"],
        "원칙": ["원칙", "법칙", "기준"]
    }
    
    # 대본에서 언급된 키워드 찾기
    found_keywords = []
    
    # 1. 직접 매칭
    for korean_word, korean_keywords_list in content_keywords.items():
        if korean_word in script_lower or korean_word in subject_lower:
            found_keywords.extend(korean_keywords_list[:2])  # 각 카테고리에서 2개씩
            logger.info(f"Found Korean keyword '{korean_word}' -> {korean_keywords_list[:2]}")
    
    # 2. 문맥 기반 키워드 추가
    context_keywords = []
    
    # 건강 관련 문맥
    if any(word in script_lower for word in ["건강", "몸", "체력", "운동", "다이어트"]):
        context_keywords.extend(["건강관리", "웰빙", "체력향상"])
    
    # 성공/자기계발 문맥
    if any(word in script_lower for word in ["성공", "목표", "달성", "습관", "계발"]):
        context_keywords.extend(["자기계발", "성공법", "목표달성"])
    
    # 일상/라이프스타일 문맥
    if any(word in script_lower for word in ["일상", "하루", "루틴", "생활", "시간"]):
        context_keywords.extend(["일상루틴", "라이프스타일", "시간관리"])
    
    # 마음/정신 건강 문맥
    if any(word in script_lower for word in ["마음", "정신", "감정", "스트레스", "행복"]):
        context_keywords.extend(["마음관리", "정신건강", "감정조절"])
    
    # 3. 키워드 조합 및 정리
    all_keywords = found_keywords + context_keywords
    
    # 중복 제거 및 정리
    unique_keywords = []
    seen = set()
    
    for keyword in all_keywords:
        keyword_clean = keyword.strip()
        if (keyword_clean not in seen and len(keyword_clean) > 1 and
            # 일반적인 태그 제외
            not any(generic in keyword_clean for generic in ["AI생성", "바이럴", "콘텐츠", "쇼츠", "영상"])):
            unique_keywords.append(keyword_clean)
            seen.add(keyword_clean)
    
    # 4. 부족한 경우 주제 기반 키워드 추가
    if len(unique_keywords) < amount:
        subject_based = _get_korean_subject_keywords(video_subject)
        for keyword in subject_based:
            if keyword not in seen and len(unique_keywords) < amount:
                unique_keywords.append(keyword)
                seen.add(keyword)
    
    result = unique_keywords[:amount]
    logger.info(f"Final script-based Korean keywords: {result}")
    return result

def _get_korean_subject_keywords(video_subject: str) -> List[str]:
    """주제 기반 한국어 키워드 생성"""
    subject_lower = video_subject.lower()
    
    subject_mapping = {
        "아침": ["아침루틴", "모닝", "하루시작", "기상"],
        "루틴": ["일상루틴", "생활패턴", "습관", "라이프스타일"],
        "습관": ["좋은습관", "습관만들기", "자기관리", "라이프스타일"],
        "건강": ["건강관리", "웰빙", "체력", "건강법"],
        "운동": ["운동법", "헬스", "체력관리", "피트니스"],
        "다이어트": ["다이어트", "체중관리", "건강식", "운동법"],
        "돈": ["재테크", "돈관리", "경제", "투자"],
        "투자": ["투자법", "재테크", "경제", "자산관리"],
        "성공": ["성공법", "자기계발", "목표달성", "성장"],
        "스트레스": ["스트레스관리", "마음관리", "힐링", "휴식"],
        "시간": ["시간관리", "효율성", "생산성", "계획"],
        "관리": ["자기관리", "생활관리", "효율성", "조절"],
        "방법": ["노하우", "팁", "비법", "해결책"],
        "마음": ["마음관리", "정신건강", "감정", "심리"]
    }
    
    keywords = []
    for korean, korean_list in subject_mapping.items():
        if korean in subject_lower:
            keywords.extend(korean_list)
    
    return keywords[:8] if keywords else ["정보", "팁", "노하우", "일상"]


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
def _generate_enhanced_script_keywords(video_subject: str, video_script: str, amount: int = 5) -> List[str]:
    """Enhanced fallback that analyzes script content more deeply"""
    logger.info(f"Performing enhanced script content analysis for: '{video_subject}'")
    
    script_lower = video_script.lower()
    subject_lower = video_subject.lower()
    
    # Comprehensive Korean-to-English mapping with script context analysis
    content_mapping = {
        # Actions and behaviors
        "루틴": ["routine", "daily habits"],
        "습관": ["habits", "lifestyle"],
        "방법": ["method", "technique"],
        "비법": ["secret", "strategy"],
        "팁": ["tips", "advice"],
        "가이드": ["guide", "tutorial"],
        "운동": ["workout", "exercise"],
        "명상": ["meditation", "mindfulness"],
        "집중": ["focus", "concentration"],
        "공부": ["study", "learning"],
        "독서": ["reading", "books"],
        "요리": ["cooking", "kitchen"],
        "청소": ["cleaning", "organization"],
        
        # Emotions and states
        "성공": ["success", "achievement"],
        "행복": ["happiness", "joy"],
        "스트레스": ["stress", "pressure"],
        "피로": ["tired", "exhausted"],
        "에너지": ["energy", "vitality"],
        "자신감": ["confidence", "self-esteem"],
        "동기": ["motivation", "inspiration"],
        
        # Objects and tools
        "돈": ["money", "cash"],
        "투자": ["investment", "finance"],
        "부동산": ["real estate", "property"],
        "자동차": ["car", "vehicle"],
        "핸드폰": ["smartphone", "phone"],
        "컴퓨터": ["computer", "laptop"],
        "책": ["book", "reading"],
        "음식": ["food", "meal"],
        "커피": ["coffee", "cafe"],
        
        # Places and environments
        "집": ["home", "house"],
        "사무실": ["office", "workplace"],
        "카페": ["cafe", "coffee shop"],
        "헬스장": ["gym", "fitness"],
        "도서관": ["library", "study"],
        "공원": ["park", "outdoor"],
        "바다": ["ocean", "beach"],
        "산": ["mountain", "hiking"],
        
        # Time and scheduling
        "아침": ["morning", "sunrise"],
        "저녁": ["evening", "sunset"],
        "밤": ["night", "dark"],
        "주말": ["weekend", "leisure"],
        "휴가": ["vacation", "holiday"],
        "시간": ["time", "clock"],
        
        # Health and wellness
        "건강": ["health", "wellness"],
        "다이어트": ["diet", "weight loss"],
        "영양": ["nutrition", "healthy food"],
        "수면": ["sleep", "rest"],
        "휴식": ["rest", "relaxation"],
        
        # Relationships and social
        "가족": ["family", "together"],
        "친구": ["friends", "social"],
        "연인": ["couple", "romance"],
        "결혼": ["wedding", "marriage"],
        "아이": ["children", "kids"],
        "부모": ["parents", "family"],
        
        # Work and career
        "일": ["work", "business"],
        "회사": ["company", "corporate"],
        "창업": ["startup", "entrepreneur"],
        "면접": ["interview", "job"],
        "승진": ["promotion", "career"],
        "퇴사": ["resignation", "quit job"],
        
        # Technology and modern life
        "AI": ["artificial intelligence", "technology"],
        "디지털": ["digital", "tech"],
        "온라인": ["online", "internet"],
        "소셜미디어": ["social media", "smartphone"],
        "유튜브": ["content creation", "video"],
        "인스타그램": ["social media", "photography"]
    }
    
    # Analyze script content for matching keywords
    matched_keywords = []
    
    # First, look for direct matches in script content
    for korean_term, english_terms in content_mapping.items():
        if korean_term in script_lower:
            matched_keywords.extend(english_terms[:2])  # Take first 2 from each match
            logger.info(f"Found script content match: '{korean_term}' -> {english_terms[:2]}")
    
    # Then, look for subject-based matches
    for korean_term, english_terms in content_mapping.items():
        if korean_term in subject_lower and korean_term not in script_lower:
            matched_keywords.extend(english_terms[:1])  # Take 1 from subject matches
            logger.info(f"Found subject match: '{korean_term}' -> {english_terms[:1]}")
    
    # Remove duplicates while preserving order
    unique_keywords = []
    seen = set()
    for keyword in matched_keywords:
        if keyword.lower() not in seen:
            unique_keywords.append(keyword.lower())
            seen.add(keyword.lower())
    
    # If we don't have enough keywords, add contextual ones
    if len(unique_keywords) < amount:
        contextual_keywords = []
        
        # Add context-based keywords based on script tone and content
        if any(word in script_lower for word in ["성공", "달성", "목표", "이루"]):
            contextual_keywords.extend(["success", "achievement", "goal"])
        if any(word in script_lower for word in ["건강", "운동", "다이어트", "몸"]):
            contextual_keywords.extend(["health", "fitness", "wellness"])
        if any(word in script_lower for word in ["돈", "투자", "부자", "경제"]):
            contextual_keywords.extend(["money", "finance", "wealth"])
        if any(word in script_lower for word in ["시간", "효율", "생산성", "관리"]):
            contextual_keywords.extend(["time", "productivity", "efficiency"])
        if any(word in script_lower for word in ["행복", "만족", "기쁨", "즐거"]):
            contextual_keywords.extend(["happiness", "joy", "satisfaction"])
        
        # Add unique contextual keywords
        for keyword in contextual_keywords:
            if keyword not in seen and len(unique_keywords) < amount:
                unique_keywords.append(keyword)
                seen.add(keyword)
    
    # Final fallback with universal keywords if still not enough
    if len(unique_keywords) < amount:
        universal_keywords = ["lifestyle", "people", "modern", "daily life", "professional"]
        for keyword in universal_keywords:
            if keyword not in seen and len(unique_keywords) < amount:
                unique_keywords.append(keyword)
                seen.add(keyword)
    
    result = unique_keywords[:amount]
    logger.info(f"Enhanced script analysis final keywords: {result}")
    return result


def generate_longform_script(video_subject: str, language: str = "ko-KR", duration_minutes: int = 10) -> str:
    """롱폼 영상용 긴 대본 생성 (5-15분 분량)"""
    logger.info(f"Generating long-form script for subject: {video_subject}, duration: {duration_minutes} minutes")
    
    # 언어별 프롬프트 설정
    if language == "ko-KR" or language == "auto":
        prompt = f"""
        주제 '{video_subject}'에 대한 {duration_minutes}분 분량의 롱폼 YouTube 영상 대본을 작성해주세요.

        요구사항:
        1. 총 {duration_minutes}분 분량 (약 {duration_minutes * 150}자)
        2. 인트로 - 본론 - 아웃트로 구조
        3. 5-7개의 주요 챕터로 구성
        4. 각 챕터는 명확한 소제목과 2-3분 분량
        5. 시청자 참여 유도 요소 포함 (질문, 댓글 유도 등)
        6. 구체적이고 실용적인 정보 제공
        7. 자연스러운 말투와 흐름
        8. 마크다운 형식 사용 금지
        9. 장면 설명 사용 금지
        10. 순수한 텍스트만 작성

        구조:
        - 인트로: 주제 소개 및 시청자 관심 끌기
        - 본론: 5-7개 챕터로 나누어 상세 설명
        - 아웃트로: 요약 및 구독/좋아요 유도

        스타일: 교육적이면서도 흥미롭게, 전문적이지만 이해하기 쉽게

        주제: {video_subject}

        {duration_minutes}분 분량의 롱폼 대본을 작성해주세요:
        """
    else:
        prompt = f"""
        Write a {duration_minutes}-minute long-form YouTube video script about '{video_subject}'.

        Requirements:
        1. Total duration: {duration_minutes} minutes (approximately {duration_minutes * 120} words)
        2. Structure: Intro - Main Content - Outro
        3. 5-7 main chapters
        4. Each chapter: clear subtitle and 2-3 minutes content
        5. Include viewer engagement elements (questions, comment prompts)
        6. Provide specific and practical information
        7. Natural speaking tone and flow
        8. NO markdown formatting
        9. NO scene descriptions
        10. Plain text only

        Structure:
        - Intro: Topic introduction and hook
        - Main: 5-7 chapters with detailed explanations
        - Outro: Summary and subscribe/like call-to-action

        Style: Educational yet engaging, professional but accessible

        Subject: {video_subject}

        Write the {duration_minutes}-minute long-form script:
        """
    
    try:
        response = _generate_response(prompt)
        if response:
            script = response.strip()
            
            # 인사말 제거 로직
            script = _remove_greetings(script, language)
            
            # 마크다운 형식 제거
            script = _clean_markdown_formatting(script)
            
            logger.info(f"Generated long-form script: {len(script)} characters")
            return script
    except Exception as e:
        logger.error(f"Failed to generate long-form script: {e}")
    
    return "롱폼 대본 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."


def split_longform_script(script: str, segment_duration: int = 3) -> list:
    """롱폼 대본을 세그먼트로 분할"""
    logger.info(f"Splitting long-form script into {segment_duration}-minute segments")
    
    # 대본을 문장 단위로 분할
    sentences = script.replace('\n\n', '\n').split('\n')
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # 각 세그먼트당 예상 문자 수 (3분 = 약 450자)
    chars_per_segment = segment_duration * 150
    
    segments = []
    current_segment = ""
    
    for sentence in sentences:
        # 현재 세그먼트에 문장을 추가했을 때의 길이 확인
        test_segment = current_segment + "\n" + sentence if current_segment else sentence
        
        if len(test_segment) <= chars_per_segment:
            current_segment = test_segment
        else:
            # 현재 세그먼트가 너무 짧으면 더 추가
            if len(current_segment) < chars_per_segment * 0.7:
                current_segment = test_segment
            else:
                # 세그먼트 완성
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = sentence
    
    # 마지막 세그먼트 추가
    if current_segment:
        segments.append(current_segment.strip())
    
    logger.info(f"Split script into {len(segments)} segments")
    return segments


def generate_longform_background_keywords(video_subject: str, script_segment: str, segment_index: int) -> list:
    """롱폼 영상 세그먼트별 배경 영상 키워드 생성 - 향상된 대본 분석 기반"""
    logger.info(f"Generating enhanced background keywords for longform segment {segment_index}")
    
    # 향상된 세그먼트 분석 프롬프트
    prompt = f"""
    You are a professional video editor specializing in matching longform content with perfect background footage.

    TASK: Analyze this specific segment of a longform video and generate HIGHLY SPECIFIC English keywords for background video search.

    LONGFORM CONTEXT:
    - Overall Subject: {video_subject}
    - Segment Number: {segment_index}
    - Segment Content: {script_segment}

    ENHANCED ANALYSIS REQUIREMENTS:
    1. Read the segment content sentence by sentence
    2. Identify SPECIFIC visual elements, actions, and concepts mentioned
    3. Convert to English keywords that will find EXACTLY matching stock footage
    4. Focus on CONCRETE, FILMABLE elements (not abstract concepts)
    5. Each keyword should be 1-2 words maximum for better search results
    6. Ensure variety - different segments should have different visual styles
    7. Consider the educational/informational nature of longform content

    LONGFORM-SPECIFIC CONSIDERATIONS:
    - Longer content needs more visual variety
    - Educational content benefits from professional, clean visuals
    - Each segment should have distinct visual identity
    - Mix of close-ups, wide shots, and different environments

    EXAMPLES OF EXCELLENT LONGFORM KEYWORD MATCHING:
    - Segment about "시간 관리" → "time management", "clock", "schedule", "planning"
    - Segment about "성공 습관" → "business success", "professional", "achievement", "goal"
    - Segment about "건강한 식습관" → "healthy food", "nutrition", "cooking", "fresh vegetables"
    - Segment about "운동 루틴" → "workout", "gym", "exercise", "fitness training"

    Based on the segment analysis above, generate 8 HIGHLY SPECIFIC English keywords that will find footage perfectly matching this segment's content.
    
    Return ONLY the keywords separated by commas, no explanations:
    """
    
    try:
        logger.info(f"Generating segment-specific keywords using enhanced LLM analysis for segment {segment_index}...")
        response = _generate_response(prompt)
        logger.info(f"LLM response for segment {segment_index}: {response}")
        
        if response:
            # Clean up the response
            cleaned = response.strip()
            
            # Remove common prefixes
            prefixes = ["keywords:", "Keywords:", "Sure", "The keywords", "Based on", "For this", "Here are", "Analysis:", "Result:"]
            for p in prefixes:
                if cleaned.lower().startswith(p.lower()):
                    cleaned = cleaned[len(p):].strip()
                    if cleaned.startswith(":"):
                        cleaned = cleaned[1:].strip()
            
            # Clean formatting and extract terms
            cleaned = cleaned.replace("\n", ",").replace("- ", "").replace("* ", "").replace('"', '').replace("'", "").strip()
            keywords = [k.strip() for k in cleaned.split(",") if k.strip()]
            
            # Enhanced validation for longform content
            valid_keywords = []
            for keyword in keywords:
                keyword = keyword.strip().lower()
                # Strict validation for longform content matching
                if (len(keyword.split()) <= 2 and  # Max 2 words
                    keyword.isascii() and 
                    len(keyword) > 2 and
                    # Exclude generic/meta terms
                    not any(generic in keyword for generic in [
                        "ai", "video", "content", "longform", "segment", "analysis", 
                        "keyword", "example", "concept", "youtube", "education"
                    ]) and
                    # Exclude common stop words
                    not any(stop_word in keyword for stop_word in [
                        "the", "and", "or", "but", "with", "for", "this", "that"
                    ]) and
                    # Ensure it's a concrete, searchable term
                    not keyword.startswith(("how to", "what is", "why", "when"))):
                    valid_keywords.append(keyword)
            
            logger.info(f"Segment {segment_index} valid keywords: {valid_keywords}")
            
            if len(valid_keywords) >= 5:
                final_keywords = valid_keywords[:8]
                logger.info(f"Final longform segment {segment_index} keywords: {final_keywords}")
                return final_keywords
                
    except Exception as e:
        logger.error(f"Failed to generate longform segment keywords: {e}")
    
    # Enhanced fallback with segment-specific analysis
    logger.warning(f"LLM failed for segment {segment_index}. Using enhanced segment analysis fallback...")
    return _generate_longform_segment_keywords(video_subject, script_segment, segment_index)


def _generate_longform_segment_keywords(video_subject: str, script_segment: str, segment_index: int) -> list:
    """Enhanced fallback for longform segment keyword generation"""
    logger.info(f"Performing enhanced longform segment analysis for segment {segment_index}")
    
    script_lower = script_segment.lower()
    subject_lower = video_subject.lower()
    
    # Longform-specific keyword mapping with more professional/educational focus
    longform_mapping = {
        # Professional and business
        "성공": ["business success", "achievement", "professional", "goal"],
        "비즈니스": ["business", "corporate", "office", "meeting"],
        "전략": ["strategy", "planning", "business plan", "analysis"],
        "목표": ["goal", "target", "achievement", "success"],
        "계획": ["planning", "strategy", "organization", "schedule"],
        
        # Learning and education
        "학습": ["learning", "education", "study", "knowledge"],
        "교육": ["education", "teaching", "classroom", "training"],
        "지식": ["knowledge", "information", "learning", "education"],
        "연구": ["research", "analysis", "study", "investigation"],
        "분석": ["analysis", "data", "research", "statistics"],
        
        # Health and wellness (professional focus)
        "건강": ["health", "wellness", "medical", "healthcare"],
        "운동": ["exercise", "fitness", "gym", "training"],
        "영양": ["nutrition", "healthy food", "diet", "wellness"],
        "의료": ["medical", "healthcare", "doctor", "hospital"],
        
        # Technology and innovation
        "기술": ["technology", "innovation", "digital", "tech"],
        "혁신": ["innovation", "technology", "modern", "future"],
        "디지털": ["digital", "technology", "computer", "online"],
        "AI": ["artificial intelligence", "technology", "computer", "digital"],
        
        # Finance and economics
        "경제": ["economy", "finance", "business", "market"],
        "투자": ["investment", "finance", "money", "business"],
        "금융": ["finance", "banking", "investment", "money"],
        "시장": ["market", "business", "economy", "trading"],
        
        # Time and productivity
        "시간": ["time", "clock", "productivity", "schedule"],
        "효율": ["efficiency", "productivity", "optimization", "performance"],
        "생산성": ["productivity", "efficiency", "work", "performance"],
        "관리": ["management", "organization", "control", "system"],
        
        # Communication and social
        "소통": ["communication", "meeting", "discussion", "teamwork"],
        "협업": ["teamwork", "collaboration", "meeting", "group"],
        "리더십": ["leadership", "management", "team", "professional"],
        "네트워킹": ["networking", "business", "professional", "meeting"],
        
        # Environment and sustainability
        "환경": ["environment", "nature", "sustainability", "green"],
        "지속가능": ["sustainability", "environment", "green", "eco"],
        "자연": ["nature", "environment", "outdoor", "landscape"],
        
        # Psychology and mindset
        "심리": ["psychology", "mindset", "mental", "brain"],
        "마음": ["mindset", "psychology", "mental", "emotion"],
        "감정": ["emotion", "psychology", "mental", "feeling"],
        "스트레스": ["stress", "pressure", "mental health", "wellness"]
    }
    
    # Analyze segment content for matching keywords
    matched_keywords = []
    
    # Look for direct matches in segment content (prioritized)
    for korean_term, english_terms in longform_mapping.items():
        if korean_term in script_lower:
            matched_keywords.extend(english_terms[:2])  # Take 2 from each match
            logger.info(f"Segment {segment_index} content match: '{korean_term}' -> {english_terms[:2]}")
    
    # Look for subject-based matches (secondary)
    for korean_term, english_terms in longform_mapping.items():
        if korean_term in subject_lower and korean_term not in script_lower:
            matched_keywords.extend(english_terms[:1])  # Take 1 from subject matches
            logger.info(f"Segment {segment_index} subject match: '{korean_term}' -> {english_terms[:1]}")
    
    # Remove duplicates while preserving order
    unique_keywords = []
    seen = set()
    for keyword in matched_keywords:
        if keyword.lower() not in seen:
            unique_keywords.append(keyword.lower())
            seen.add(keyword.lower())
    
    # Add segment-specific variety based on index
    if len(unique_keywords) < 8:
        # Different visual styles for different segments
        segment_variety = {
            1: ["professional", "business", "modern"],
            2: ["technology", "innovation", "digital"],
            3: ["analysis", "data", "research"],
            4: ["teamwork", "collaboration", "meeting"],
            5: ["growth", "development", "progress"],
            6: ["strategy", "planning", "organization"],
            7: ["success", "achievement", "goal"],
            8: ["future", "vision", "innovation"]
        }
        
        variety_keywords = segment_variety.get(segment_index % 8 + 1, ["professional", "modern", "business"])
        for keyword in variety_keywords:
            if keyword not in seen and len(unique_keywords) < 8:
                unique_keywords.append(keyword)
                seen.add(keyword)
    
    # Final fallback with longform-appropriate keywords
    if len(unique_keywords) < 8:
        longform_fallback = [
            "professional", "business", "modern", "technology", 
            "education", "analysis", "strategy", "innovation"
        ]
        for keyword in longform_fallback:
            if keyword not in seen and len(unique_keywords) < 8:
                unique_keywords.append(keyword)
                seen.add(keyword)
    
    result = unique_keywords[:8]
    logger.info(f"Enhanced longform segment {segment_index} final keywords: {result}")
    return result