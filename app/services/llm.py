import json
import logging
import re
import requests
import time
import random
import concurrent.futures
from typing import List, Optional

import g4f
from loguru import logger
from openai import AzureOpenAI, OpenAI

from app.config import config

_max_retries = 3

def _generate_free_response(prompt: str) -> str:
    def try_pollinations_openai():
        try:
            import urllib.parse
            encoded_prompt = urllib.parse.quote(prompt)
            # Try openai model
            url = f"https://text.pollinations.ai/{encoded_prompt}?seed={random.randint(100, 999999)}&model=openai"
            response = requests.get(url, timeout=30) 
            if response.status_code == 200 and response.text.strip():
                logger.info("Race win: Pollinations OpenAI")
                return response.text
        except Exception:
            pass
        return None

    def try_pollinations_mistral():
        try:
            import urllib.parse
            encoded_prompt = urllib.parse.quote(prompt)
            # Try mistral model
            url = f"https://text.pollinations.ai/{encoded_prompt}?seed={random.randint(100, 999999)}&model=mistral"
            response = requests.get(url, timeout=30) 
            if response.status_code == 200 and response.text.strip():
                logger.info("Race win: Pollinations Mistral")
                return response.text
        except Exception:
            pass
        return None
        
    def try_pollinations_llama():
        try:
            import urllib.parse
            encoded_prompt = urllib.parse.quote(prompt)
            # Try llama model
            url = f"https://text.pollinations.ai/{encoded_prompt}?seed={random.randint(100, 999999)}&model=llama"
            response = requests.get(url, timeout=30) 
            if response.status_code == 200 and response.text.strip():
                logger.info("Race win: Pollinations Llama")
                return response.text
        except Exception:
            pass
        return None
        
    def try_pollinations_searchgpt():
        try:
            import urllib.parse
            encoded_prompt = urllib.parse.quote(prompt)
            # Try searchgpt model
            url = f"https://text.pollinations.ai/{encoded_prompt}?seed={random.randint(100, 999999)}&model=searchgpt"
            response = requests.get(url, timeout=30) 
            if response.status_code == 200 and response.text.strip():
                logger.info("Race win: Pollinations SearchGPT")
                return response.text
        except Exception:
            pass
        return None

    def try_g4f_duckduckgo():
        try:
            # DuckDuckGo is often stable
            resp = g4f.ChatCompletion.create(
                model="gpt-3.5-turbo",
                provider=g4f.Provider.DuckDuckGo,
                messages=[{"role": "user", "content": prompt}]
            )
            if resp:
                logger.info("Race win: G4F DuckDuckGo")
                return resp
        except Exception:
            pass
        return None

    def try_g4f_blackbox():
        try:
            # Blackbox is another good free option
            resp = g4f.ChatCompletion.create(
                model="gpt-4",
                provider=g4f.Provider.Blackbox,
                messages=[{"role": "user", "content": prompt}]
            )
            if resp:
                logger.info("Race win: G4F Blackbox")
                return resp
        except Exception:
            pass
        return None
        
    def try_g4f_auto():
        try:
            # Auto selection as last resort
            resp = g4f.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            if resp:
                logger.info("Race win: G4F Auto")
                return resp
        except Exception:
            pass
        return None

    def try_g4f_darkai():
        try:
            # DarkAI
            resp = g4f.ChatCompletion.create(
                model="gpt-3.5-turbo",
                provider=g4f.Provider.DarkAI,
                messages=[{"role": "user", "content": prompt}]
            )
            if resp:
                logger.info("Race win: G4F DarkAI")
                return resp
        except Exception:
            pass
        return None

    def try_g4f_airforce():
        try:
            # Airforce
            resp = g4f.ChatCompletion.create(
                model="gpt-3.5-turbo",
                provider=g4f.Provider.Airforce,
                messages=[{"role": "user", "content": prompt}]
            )
            if resp:
                logger.info("Race win: G4F Airforce")
                return resp
        except Exception:
            pass
        return None

    content = ""
    # Increase workers to cover new providers
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
    futures = [
        executor.submit(try_pollinations_openai),
        executor.submit(try_pollinations_mistral),
        executor.submit(try_pollinations_llama),
        executor.submit(try_pollinations_searchgpt),
        executor.submit(try_g4f_duckduckgo),
        executor.submit(try_g4f_blackbox),
        executor.submit(try_g4f_darkai),
        executor.submit(try_g4f_airforce),
        executor.submit(try_g4f_auto)
    ]
    
    try:
        # Reduce timeout to 30s to keep UI responsive
        for future in concurrent.futures.as_completed(futures, timeout=30):
            result = future.result()
            if result:
                content = result
                break
    except concurrent.futures.TimeoutError:
        logger.warning("Race timeout (30s)")
    except Exception as e:
        logger.error(f"Race error: {e}")
    finally:
        # CRITICAL FIX: Do not wait for hanging threads!
        executor.shutdown(wait=False)

    return content

def _generate_response(prompt: str) -> str:
    # Force reload config to pick up changes
    config.reload()
    
    content = ""
    llm_provider = config.app.get("llm_provider", "openai")
    logger.info(f"llm provider: {llm_provider}")

    # Enhanced Race Strategy for Free/Unstable Providers
    if llm_provider in ["g4f", "pollinations", "free"]:
        content = _generate_free_response(prompt)

        if not content:
             logger.warning("All providers failed or timed out in race.")
             
             # Smart Fallback to Gemini if key exists
             gemini_key = config.app.get("gemini_api_key")
             if gemini_key:
                 logger.info("Falling back to Gemini...")
                 try:
                     import google.generativeai as genai
                     genai.configure(api_key=gemini_key)
                     # Fallback model
                     target_model = config.app.get("gemini_model_name", "gemini-1.5-flash")
                     if not target_model or "3.0" in target_model: target_model = "gemini-1.5-flash"
                     
                     model = genai.GenerativeModel(target_model)
                     response = model.generate_content(prompt)
                     if response.text:
                         return response.text
                 except Exception as e_gemini:
                     logger.error(f"Gemini fallback failed: {e_gemini}")
             
             raise Exception("All free providers failed (Race Timeout) and Fallback failed")
        
        return content

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
                logger.warning(f"Gemini failed ({e}), falling back to free providers...")
                return _generate_free_response(prompt)

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
    
    # IMPROVED FALLBACK: Use Subject and Script words (Translated to English)
    logger.warning("LLM failed to generate relevant terms. Using translated fallback.")
    
    # 1. Start with the subject
    subject_eng = translate_to_english(video_subject) if video_subject else ""
    fallback = [subject_eng] if subject_eng else []
    
    # 2. Extract some potential keywords from the script
    words = re.findall(r'\w+', video_script)
    # Filter Korean words and translate them
    ko_words = [w for w in words if re.search('[가-힣]', w)][:3]
    for w in ko_words:
        eng_w = translate_to_english(w)
        if eng_w and eng_w != w:
            fallback.append(eng_w)
    
    # 3. Add quality terms
    fallback.extend(["cinematic", "realistic", "4k background"])
    
    # Clean up fallback (unique and English only)
    unique_fallback = []
    for f in fallback:
        # Simple check for English characters
        if f and not re.search('[가-힣]', f) and f not in unique_fallback:
            unique_fallback.append(f)
            
    return unique_fallback[:amount]

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
