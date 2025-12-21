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

def _generate_response(prompt: str) -> str:
    # Force reload config to pick up changes
    config.reload()
    
    content = ""
    llm_provider = config.app.get("llm_provider", "openai")
    logger.info(f"llm provider: {llm_provider}")

    # Enhanced Race Strategy for Free/Unstable Providers
    if llm_provider in ["g4f", "pollinations", "free"]:
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
            start_time = time.time()
            # Increase total timeout to 60s to ensure completion even on slow networks
            for future in concurrent.futures.as_completed(futures, timeout=60):
                result = future.result()
                if result:
                    content = result
                    break
        except concurrent.futures.TimeoutError:
            logger.warning("Race timeout (60s)")
        except Exception as e:
            logger.error(f"Race error: {e}")
        finally:
            # CRITICAL FIX: Do not wait for hanging threads!
            # Shutdown immediately so the UI doesn't freeze waiting for a dead thread
            executor.shutdown(wait=False)

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
                     target_model = config.app.get("gemini_model_name", "gemini-2.5-flash")
                     if not target_model or "3.0" in target_model: target_model = "gemini-2.5-flash"
                     
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
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            # Auto-correct invalid model names or use default
            target_model = model_name
            if not target_model or "3.0" in target_model: # Correct user's 3.0 typo
                target_model = "gemini-2.5-flash"
                
            logger.info(f"Using Gemini model: {target_model}")
            model = genai.GenerativeModel(target_model)
            response = model.generate_content(prompt)
            return response.text

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
    Analyze the following video script and extract {amount} highly visual, concrete English keywords for searching stock footage.
    The keywords MUST be in English, regardless of the script's language.
    Focus on physical objects, locations, actions, and atmosphere described in the script.
    Avoid abstract concepts (e.g., avoid "success", "future"; prefer "skyscraper", "robot", "handshake").
    
    Video Subject: {video_subject}
    Script Snippet: {video_script[:800]}
    
    Return ONLY a comma-separated list of {amount} English keywords. No numbering, no explanations.
    Example: skyscraper, office meeting, shaking hands, blue sky, running crowd
    """
    
    try:
        response = _generate_response(prompt)
        if response:
            # Clean up the response
            cleaned_response = response.replace("Keywords:", "").replace("keywords:", "").strip()
            terms = [t.strip() for t in cleaned_response.split(",") if t.strip()]
            
            # Ensure we have at least some terms
            if len(terms) < 3:
                # Fallback to simple subject-based terms if LLM fails to generate enough
                logger.warning("LLM returned too few terms, adding fallback terms.")
                terms.extend([video_subject] if video_subject else [])
                
            return terms[:amount]
    except Exception as e:
        logger.error(f"failed to generate terms: {e}")
    
    # Absolute fallback if LLM fails completely
    fallback = [video_subject] if video_subject else ["video", "background"]
    # Add some generic terms
    fallback.extend(["scenery", "nature", "business", "technology"])
    return fallback[:amount]

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
