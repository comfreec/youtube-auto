import json
import logging
import re
import requests
from typing import List

import g4f
from loguru import logger
from openai import AzureOpenAI, OpenAI
from openai.types.chat import ChatCompletion

from app.config import config

_max_retries = 3


import concurrent.futures
import random

def _generate_response(prompt: str) -> str:
    try:
        content = ""
        llm_provider = config.app.get("llm_provider", "openai")
        logger.info(f"llm provider: {llm_provider}")
        if llm_provider == "g4f":
            try:
                model_name = config.app.get("g4f_model_name", "")
                if not model_name:
                    model_name = "gpt-4o-mini"
                
                content = g4f.ChatCompletion.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                )
            except Exception as e:
                logger.warning(f"g4f failed: {e}, falling back to pollinations")
                # Fallback to Pollinations
            try:
                import urllib.parse
                encoded_prompt = urllib.parse.quote(prompt)
                url = f"https://text.pollinations.ai/{encoded_prompt}?seed={random.randint(100, 999999)}"
                response = requests.get(url, timeout=60)
                response.raise_for_status()
                content = response.text
            except Exception as e2:
                     raise Exception(f"g4f and pollinations fallback failed: {str(e2)}")

        else:
            api_version = ""  # for azure
            if llm_provider == "moonshot":
                api_key = config.app.get("moonshot_api_key")
                model_name = config.app.get("moonshot_model_name")
                base_url = "https://api.moonshot.cn/v1"
            elif llm_provider == "ollama":
                # api_key = config.app.get("openai_api_key")
                api_key = "ollama"  # any string works but you are required to have one
                model_name = config.app.get("ollama_model_name")
                base_url = config.app.get("ollama_base_url", "")
                if not base_url:
                    base_url = "http://localhost:11434/v1"
            elif llm_provider == "openai":
                api_key = config.app.get("openai_api_key")
                model_name = config.app.get("openai_model_name")
                base_url = config.app.get("openai_base_url", "")
                if not base_url:
                    base_url = "https://api.openai.com/v1"
            elif llm_provider == "oneapi":
                api_key = config.app.get("oneapi_api_key")
                model_name = config.app.get("oneapi_model_name")
                base_url = config.app.get("oneapi_base_url", "")
            elif llm_provider == "azure":
                api_key = config.app.get("azure_api_key")
                model_name = config.app.get("azure_model_name")
                base_url = config.app.get("azure_base_url", "")
                api_version = config.app.get("azure_api_version", "2024-02-15-preview")
            elif llm_provider == "gemini":
                api_key = config.app.get("gemini_api_key")
                model_name = config.app.get("gemini_model_name")
                base_url = config.app.get("gemini_base_url", "")
            elif llm_provider == "qwen":
                api_key = config.app.get("qwen_api_key")
                model_name = config.app.get("qwen_model_name")
                base_url = "***"
            elif llm_provider == "cloudflare":
                api_key = config.app.get("cloudflare_api_key")
                model_name = config.app.get("cloudflare_model_name")
                account_id = config.app.get("cloudflare_account_id")
                base_url = "***"
            elif llm_provider == "deepseek":
                api_key = config.app.get("deepseek_api_key")
                model_name = config.app.get("deepseek_model_name")
                base_url = config.app.get("deepseek_base_url")
                if not base_url:
                    base_url = "https://api.deepseek.com"
            elif llm_provider == "modelscope":
                api_key = config.app.get("modelscope_api_key")
                model_name = config.app.get("modelscope_model_name")
                base_url = config.app.get("modelscope_base_url")
                if not base_url:
                    base_url = "https://api-inference.modelscope.cn/v1/"
            elif llm_provider == "ernie":
                api_key = config.app.get("ernie_api_key")
                secret_key = config.app.get("ernie_secret_key")
                base_url = config.app.get("ernie_base_url")
                model_name = "***"
                if not secret_key:
                    raise ValueError(
                        f"{llm_provider}: secret_key is not set, please set it in the config.toml file."
                    )
            elif llm_provider == "pollinations":
                try:
                    model_name = config.app.get("pollinations_model_name", "openai-fast")
                    sanitized_prompt = re.sub(r"[\r\n]+", " ", prompt).replace("#", " ")
                    import urllib.parse
                    encoded_prompt = urllib.parse.quote(sanitized_prompt)
                    url = f"https://text.pollinations.ai/{encoded_prompt}?model={model_name}&seed={random.randint(100, 999999)}"
                    response = requests.get(url, timeout=60)
                    response.raise_for_status()
                    content = response.text
                    return content
                except Exception as e:
                    raise Exception(f"[{llm_provider}] error: {str(e)}")

            if llm_provider not in ["pollinations", "ollama"]:
                if not api_key or not model_name or not base_url:
                    try:
                        model_name_ = config.app.get("pollinations_model_name", "openai-fast")
                        sanitized_prompt = re.sub(r"[\r\n]+", " ", prompt).replace("#", " ")
                        import urllib.parse
                        encoded_prompt = urllib.parse.quote(sanitized_prompt)
                        url = f"https://text.pollinations.ai/{encoded_prompt}?model={model_name_}"
                        response = requests.get(url, timeout=60)
                        response.raise_for_status()
                        content = response.text
                        return content
                    except Exception as e:
                        raise ValueError(f"{llm_provider}: missing credentials and pollinations failed: {str(e)}")

            if llm_provider == "qwen":
                import dashscope
                from dashscope.api_entities.dashscope_response import GenerationResponse

                dashscope.api_key = api_key
                response = dashscope.Generation.call(
                    model=model_name, messages=[{"role": "user", "content": prompt}]
                )
                if response:
                    if isinstance(response, GenerationResponse):
                        status_code = response.status_code
                        if status_code != 200:
                            raise Exception(
                                f'[{llm_provider}] returned an error response: "{response}"'
                            )

                        content = response["output"]["text"]
                        return content
                    else:
                        raise Exception(
                            f'[{llm_provider}] returned an invalid response: "{response}"'
                        )
                else:
                    raise Exception(f"[{llm_provider}] returned an empty response")

            if llm_provider == "gemini":
                import google.generativeai as genai

                if not base_url:
                    genai.configure(api_key=api_key, transport="rest")
                else:
                    genai.configure(api_key=api_key, transport="rest", client_options={'api_endpoint': base_url})

                generation_config = {
                    "temperature": 0.5,
                    "top_p": 1,
                    "top_k": 1,
                    "max_output_tokens": 2048,
                }

                safety_settings = [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_ONLY_HIGH",
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_ONLY_HIGH",
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_ONLY_HIGH",
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_ONLY_HIGH",
                    },
                ]

                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                )

                try:
                    response = model.generate_content(prompt)
                    candidates = response.candidates
                    generated_text = candidates[0].content.parts[0].text
                except (AttributeError, IndexError) as e:
                    print("Gemini Error:", e)

                return generated_text

            if llm_provider == "cloudflare":
                response = requests.post(
                    f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_name}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a friendly assistant",
                            },
                            {"role": "user", "content": prompt},
                        ]
                    },
                )
                result = response.json()
                logger.info(result)
                return result["result"]["response"]

            if llm_provider == "ernie":
                response = requests.post(
                    "https://aip.baidubce.com/oauth/2.0/token", 
                    params={
                        "grant_type": "client_credentials",
                        "client_id": api_key,
                        "client_secret": secret_key,
                    }
                )
                access_token = response.json().get("access_token")
                url = f"{base_url}?access_token={access_token}"

                payload = json.dumps(
                    {
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.5,
                        "top_p": 0.8,
                        "penalty_score": 1,
                        "disable_search": False,
                        "enable_citation": False,
                        "response_format": "text",
                    }
                )
                headers = {"Content-Type": "application/json"}

                response = requests.request(
                    "POST", url, headers=headers, data=payload
                ).json()
                return response.get("result")

            if llm_provider == "azure":
                client = AzureOpenAI(
                    api_key=api_key,
                    api_version=api_version,
                    azure_endpoint=base_url,
                )

            if llm_provider == "modelscope":
                content = ''
                client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                )
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    extra_body={"enable_thinking": False},
                    stream=True
                )
                if response:
                    for chunk in response:
                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            content += delta.content
                    
                    if not content.strip():
                        raise ValueError("Empty content in stream response")
                    
                    return content
                else:
                    raise Exception(f"[{llm_provider}] returned an empty response")

            else:
                client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                )

            response = client.chat.completions.create(
                model=model_name, messages=[{"role": "user", "content": prompt}]
            )
            if response:
                if isinstance(response, ChatCompletion):
                    content = response.choices[0].message.content
                else:
                    raise Exception(
                        f'[{llm_provider}] returned an invalid response: "{response}", please check your network '
                        f"connection and try again."
                    )
            else:
                raise Exception(
                    f"[{llm_provider}] returned an empty response, please check your network connection and try again."
                )

        return content
    except Exception as e:
        return f"Error: {str(e)}"


def generate_script(
    video_subject: str, language: str = "", paragraph_number: int = 1
) -> str:
    prompt = f"""
# Role: Video Script Generator

# Goals:
Generate a script for a video, depending on the subject of the video.

# Constraints:
1. the script should be helpful and informative.
2. the script should be directly related to the subject.
3. the script should not include any title.
4. the script should be spoken by a narrator.
5. the script should be clear and easy to understand.
6. the script should be engaging and interesting.
7. the script should not include any markdown.
8. the script should not include any other characters.
9. the script should not include any other information.

# Initialization:
- video subject: {video_subject}
- number of paragraphs: {paragraph_number}
""".strip()
    if language:
        prompt += f"\n- language: {language}"

    # Generate a random seed for the prompt to prevent caching
    import uuid
    random_seed_str = f"Request ID: {str(uuid.uuid4())[:8]}"
    prompt += f"\n[{random_seed_str}]"

    final_script = ""
    logger.info(f"subject: {video_subject}")

    def format_response(response):
        # Clean the script
        # Remove asterisks, hashes
        response = response.replace("*", "")
        response = response.replace("#", "")

        # Remove markdown syntax
        response = re.sub(r"\[.*\]", "", response)
        response = re.sub(r"\(.*\)", "", response)

        # Split the script into paragraphs
        paragraphs = response.split("\n\n")

        # Select the specified number of paragraphs
        selected_paragraphs = paragraphs[:paragraph_number]

        # Join the selected paragraphs into a single string
        return "\n\n".join(selected_paragraphs)

    for i in range(_max_retries):
        try:
            response = _generate_response(prompt=prompt)
            if response:
                final_script = format_response(response)
            else:
                logging.error("gpt returned an empty response")

            # g4f may return an error message
            if final_script and "当日额度已消耗完" in final_script:
                raise ValueError(final_script)

            if final_script:
                break
        except Exception as e:
            logger.error(f"failed to generate script: {e}")

        if i < _max_retries:
            logger.warning(f"failed to generate video script, trying again... {i + 1}")
    if not final_script:
        logger.error("failed to generate video script")
        # return fallback script
        if language and ("korea" in language.lower() or "한국" in language):
             final_script = f"{video_subject}에 대해 이야기해 봅시다. 이것은 많은 사람들이 더 알고 싶어하는 흥미로운 주제입니다. {video_subject}에는 탐구할 만한 많은 측면이 있습니다. 이 영상에서는 {video_subject}의 기초에 대해 다룰 것입니다. {video_subject}에 대한 모든 것을 배우기 위해 계속 시청해 주세요."
        else:
             final_script = f"Let's talk about {video_subject}. This is an interesting topic that many people want to know more about. {video_subject} has many aspects worth exploring. In this video, we will cover the basics of {video_subject}. Stay tuned to learn all about {video_subject}."

    logger.success(f"completed: \n{final_script}")
    return final_script.strip()



def _fallback_visual_terms(video_subject: str, video_script: str, amount: int = 5) -> List[str]:
    s = (video_subject or "") + " " + (video_script or "")
    s = s.lower()
    categories = [
        ("finance", ["가격", "비트코인", "주식", "투자", "돈", "금리", "경제", "환율", "부자", "수익"]),
        ("health", ["운동", "건강", "헬스", "피트니스", "다이어트", "의학", "병원", "영양"]),
        ("travel", ["여행", "풍경", "관광", "도시", "바다", "산", "호텔"]),
        ("tech", ["기술", "ai", "인공지능", "컴퓨터", "데이터", "로봇", "코딩"]),
        ("education", ["교육", "공부", "학교", "학생", "강의", "시험"]),
        ("nature", ["자연", "숲", "동물", "하늘", "해변", "바다", "산책"]),
        ("business", ["사업", "회사", "비즈니스", "회의", "사무실", "스타트업"]),
    ]
    cat = "generic"
    for name, tokens in categories:
        if any(t in s for t in tokens):
            cat = name
            break
    base = {
        "finance": [
            "stock market ticker",
            "candlestick chart animation",
            "city skyline at night",
            "hands counting cash",
            "businessman typing laptop",
            "digital coin spinning",
            "trading desk monitors",
        ],
        "health": [
            "gym workout routine",
            "runner on track",
            "healthy meal preparation",
            "yoga meditation pose",
            "fitness trainer coaching",
            "heart rate monitor",
            "stretching exercise mat",
        ],
        "travel": [
            "sunset beach waves",
            "city street timelapse",
            "mountain hiking trail",
            "aerial skyline view",
            "tourist taking photos",
            "cozy hotel lobby",
            "busy airport terminal",
        ],
        "tech": [
            "coding on laptop",
            "data center servers",
            "robotic arm moving",
            "neon circuit board",
            "smartphone close up",
            "developer typing keyboard",
            "ai hologram interface",
        ],
        "education": [
            "student writing notes",
            "teacher in classroom",
            "books on desk",
            "online learning setup",
            "library reading scene",
            "whiteboard lecture",
            "exam preparation study",
        ],
        "nature": [
            "forest sunlight rays",
            "river flowing stones",
            "birds flying sky",
            "green meadow wind",
            "macro leaf dew",
            "ocean wave splash",
            "mountain clouds rolling",
        ],
        "business": [
            "team meeting table",
            "office handshake deal",
            "presentation on screen",
            "coworking space laptops",
            "startup brainstorming notes",
            "modern glass office",
            "businesswoman phone call",
        ],
        "generic": [
            "city street crowd",
            "typing hands closeup",
            "modern office interior",
            "night skyline lights",
            "abstract motion background",
            "people walking corridor",
            "tablet screen scrolling",
        ],
    }
    terms = base.get(cat, base["generic"]).copy()
    random.shuffle(terms)
    return terms[:max(1, amount)]


def _postprocess_terms(video_subject: str, terms: List[str], amount: int) -> List[str]:
    cleaned = []
    seen = set()
    # Prepare normalized subject for comparison
    subj = re.sub(r"[^A-Za-z\s]", " ", (video_subject or "")).strip().lower()
    subj = re.sub(r"\s+", " ", subj)
    for t in terms:
        if not isinstance(t, str):
            continue
        x = t.strip()
        if not x:
            continue
        x = x.replace("_", " ").replace("-", " ").strip()
        x = re.sub(r"[^A-Za-z\\s]", " ", x)
        x = re.sub(r"\\s+", " ", x).strip()
        if not x:
            continue
        words = x.split(" ")
        if len(words) > 5:
            x = " ".join(words[:5])
        if len(x) < 3:
            continue
        key = x.lower()
        # Exclude terms equal to normalized subject
        if subj and key == subj:
            continue
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(x)
        if len(cleaned) >= amount:
            break
    if len(cleaned) < amount:
        fallback = _fallback_visual_terms(video_subject, "", amount - len(cleaned))
        for f in fallback:
            k = f.lower().strip()
            if k and k not in seen:
                cleaned.append(f)
                seen.add(k)
                if len(cleaned) >= amount:
                    break
    return cleaned[:amount]


def generate_terms(video_subject: str, video_script: str, amount: int = 5) -> List[str]:
    prompt = f"""
# Role: Video Search Terms Generator

## Goals:
Generate {amount} search terms for stock videos, based on the subject and script of a video.

## Constraints:
1. Return a JSON-array of strings. Example: ["term1", "term2", "term3"]
2. Each search term must be a concrete VISUAL description (3-5 words) in English.
3. Do NOT use abstract concepts. Describe what can be SEEN.
4. The search terms MUST be directly related to the video subject: "{video_subject}". PRIORITIZE the subject over the script.
5. Do NOT generate generic terms. Use specific nouns and actions related to "{video_subject}".
6. Return ONLY the JSON-array. No other text.

## Context:
### Video Subject
{video_subject}

### Video Script
{video_script}
""".strip()

    logger.info(f"subject: {video_subject}")

    search_terms = []
    response = ""
    for i in range(_max_retries):
        try:
            response = _generate_response(prompt)
            if "Error: " in response:
                logger.warning(f"failed to generate video terms: {response}")
                continue
            
            try:
                search_terms = json.loads(response)
            except:
                # Try to find JSON-like array in the text
                match = re.search(r"\[.*\]", response)
                if match:
                    search_terms = json.loads(match.group())
                else:
                    logger.warning(f"Could not parse JSON from response: {response}")
                    continue

            if not isinstance(search_terms, list) or not all(
                isinstance(term, str) for term in search_terms
            ):
                logger.error("response is not a list of strings.")
                continue
            
            return _postprocess_terms(video_subject, search_terms, amount)

        except Exception as e:
            logger.warning(f"failed to generate video terms: {str(e)}")
            continue
    
    use_fallback = config.ui.get("terms_fallback_enabled", True)
    if use_fallback:
        logger.warning("Generating fallback terms due to LLM failure")
        return _fallback_visual_terms(video_subject, video_script, amount)
    return []


if __name__ == "__main__":
    video_subject = "生命的意义是什么"
    script = generate_script(
        video_subject=video_subject, language="zh-CN", paragraph_number=1
    )
    print("######################")
    print(script)
    search_terms = generate_terms(
        video_subject=video_subject, video_script=script, amount=5
    )
    print("######################")
    print(search_terms)
    
