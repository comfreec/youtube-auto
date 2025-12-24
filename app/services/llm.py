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
    prompt = f"""
    You are a professional video editor. Extract {amount} highly relevant English keywords for stock footage search.
    The keywords MUST directly represent the specific scenes and actions described in the script below.
    
    CRITICAL: 
    - NO abstract words. 
    - Use concrete visual terms (e.g., if script is about 'Jesus', use 'ancient Israel', 'man preaching', 'desert', 'cross').
    - Keywords must be in English.
    
    Script: {video_script[:1000]}
    
    Return ONLY a comma-separated list.
    """
    
    try:
        response = _generate_response(prompt)
        if response:
            # Clean up the response aggressively
            cleaned = response
            prefixes = ["Here are", "Keywords:", "keywords:", "Sure", "The keywords"]
            for p in prefixes:
                if p in cleaned:
                    cleaned = cleaned.split(p)[-1]
            
            cleaned = cleaned.replace("\n", ",").replace("- ", "").replace("* ", "").strip()
            terms = [t.strip() for t in cleaned.split(",") if t.strip()]
            terms = [t for t in terms if len(t.split()) <= 5]
            
            if len(terms) >= 2:
                return terms[:amount]
    except Exception as e:
        logger.error(f"failed to generate terms: {e}")
    
    logger.warning("LLM failed to generate relevant terms. Using script-based fallback.")
    script_text = video_script or ""
    has_korean = bool(re.search("[가-힣]", script_text))
    tokens_en = []
    if has_korean:
        try:
            translated = translate_to_english(script_text) or script_text
            if translated and not re.search("[가-힣]", translated):
                script_text = translated
        except Exception:
            pass
    tokens_en = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", script_text)
    stop = {
        "the","a","an","and","to","of","in","on","with","for","as","by","is","are","was","were","be","being","been",
        "have","has","had","do","does","did","from","that","this","it","they","them","he","she","we","you","i","not",
        "but","or","so","if","then","at","into","out","over","under","up","down","about","than","too","very","can",
        "may","might","should","would","could","will","shall"
    }
    if tokens_en:
        filtered = [t.lower() for t in tokens_en if t.lower() not in stop]
        bigrams = [" ".join([filtered[i], filtered[i+1]]) for i in range(len(filtered)-1)]
        tri = [" ".join([filtered[i], filtered[i+1], filtered[i+2]]) for i in range(len(filtered)-2)]
        counts_big = Counter(bigrams)
        counts_tri = Counter(tri)
        counts_uni = Counter(filtered)
        ordered = []
        for phrase, _ in counts_tri.most_common():
            ordered.append(phrase)
        for phrase, _ in counts_big.most_common():
            ordered.append(phrase)
        for word, _ in counts_uni.most_common():
            ordered.append(word)
        dedup = []
        for t in ordered:
            if t and t not in dedup and len(t.split()) <= 5:
                dedup.append(t)
            if len(dedup) >= amount:
                break
        if len(dedup) < amount:
            subj = translate_to_english(video_subject) if video_subject else ""
            if subj and subj not in dedup:
                dedup.append(subj)
        return dedup[:amount]
    tokens_ko = re.findall(r"[가-힣]{2,}", video_script or "")
    if tokens_ko:
        phrases_ko = []
        for i in range(len(tokens_ko)-2):
            phrases_ko.append(" ".join([tokens_ko[i], tokens_ko[i+1], tokens_ko[i+2]]))
        for i in range(len(tokens_ko)-1):
            phrases_ko.append(" ".join([tokens_ko[i], tokens_ko[i+1]]))
        phrases_ko.extend(tokens_ko)
        seen = set()
        dedup_ko = []
        for t in phrases_ko:
            if t and t not in seen:
                seen.add(t)
                dedup_ko.append(t)
            if len(dedup_ko) >= amount:
                break
        try:
            translated_terms = translate_terms_to_english(dedup_ko)
            if translated_terms:
                return translated_terms[:amount]
        except Exception:
            pass
    subj = translate_to_english(video_subject) if video_subject else ""
    return [subj][:amount] if subj else []

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
