"""
초기설정 도우미 함수들
"""
import requests
import json
import os
from typing import Dict, Tuple, Optional

def validate_gemini_api_key(api_key: str) -> Tuple[bool, str]:
    """Gemini API 키 유효성 검증"""
    if not api_key or not api_key.startswith('AIza'):
        return False, "올바른 Gemini API 키 형식이 아닙니다. 'AIza'로 시작해야 합니다."
    
    try:
        # 간단한 API 호출로 키 유효성 검증
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # 먼저 사용 가능한 모델 목록을 확인
        try:
            models = genai.list_models()
            available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
            
            if not available_models:
                return False, "사용 가능한 모델이 없습니다. API 키를 확인해주세요."
            
            # 첫 번째 사용 가능한 모델로 테스트
            model_name = available_models[0].replace('models/', '')
            model = genai.GenerativeModel(model_name)
            
        except Exception:
            # 모델 목록 조회 실패 시 기본 모델들로 시도 (최신 모델 우선)
            test_models = ['gemini-2.5-flash-exp', 'gemini-1.5-flash-latest', 'gemini-1.5-pro-latest', 'gemini-pro']
            model = None
            
            for test_model in test_models:
                try:
                    model = genai.GenerativeModel(test_model)
                    break
                except Exception:
                    continue
            
            if model is None:
                return False, "사용 가능한 모델을 찾을 수 없습니다."
        
        # 실제 생성 테스트
        response = model.generate_content(
            "Hello", 
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=10,
                temperature=0.1
            )
        )
        
        if response.text:
            return True, "API 키가 유효합니다!"
        else:
            return False, "API 응답이 비어있습니다."
            
    except Exception as e:
        error_msg = str(e).lower()
        
        if "quota" in error_msg or "limit" in error_msg:
            return False, "API 할당량이 초과되었습니다. 잠시 후 다시 시도해주세요."
        elif "permission" in error_msg or "forbidden" in error_msg or "401" in error_msg:
            return False, "API 키가 유효하지 않거나 권한이 없습니다. Google AI Studio에서 키를 다시 확인해주세요."
        elif "404" in error_msg:
            return False, "모델을 찾을 수 없습니다. API 키가 올바른지 확인해주세요."
        else:
            return False, f"API 키 검증 실패: {str(e)}"

def validate_pexels_api_key(api_key: str) -> Tuple[bool, str]:
    """Pexels API 키 유효성 검증"""
    if not api_key:
        return False, "API 키를 입력해주세요."
    
    try:
        headers = {'Authorization': api_key}
        response = requests.get(
            'https://api.pexels.com/videos/search?query=nature&per_page=1',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "API 키가 유효합니다!"
        elif response.status_code == 401:
            return False, "API 키가 유효하지 않습니다."
        else:
            return False, f"API 응답 오류: {response.status_code}"
    except Exception as e:
        return False, f"API 키 검증 실패: {str(e)}"

def validate_pixabay_api_key(api_key: str) -> Tuple[bool, str]:
    """Pixabay API 키 유효성 검증"""
    if not api_key:
        return False, "API 키를 입력해주세요."
    
    try:
        response = requests.get(
            f'https://pixabay.com/api/videos/?key={api_key}&q=nature&per_page=3',
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'error' in data:
                return False, f"API 오류: {data['error']}"
            return True, "API 키가 유효합니다!"
        else:
            return False, f"API 응답 오류: {response.status_code}"
    except Exception as e:
        return False, f"API 키 검증 실패: {str(e)}"

def validate_youtube_secrets(secrets_content: dict) -> Tuple[bool, str]:
    """YouTube client_secrets.json 파일 유효성 검증"""
    try:
        # OAuth 클라이언트 구조 확인
        if 'installed' in secrets_content:
            client_info = secrets_content['installed']
        elif 'web' in secrets_content:
            client_info = secrets_content['web']
        else:
            return False, "올바른 OAuth 클라이언트 파일이 아닙니다."
        
        # 필수 필드 확인
        required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
        for field in required_fields:
            if field not in client_info:
                return False, f"필수 필드 '{field}'가 없습니다."
        
        return True, "YouTube 설정 파일이 유효합니다!"
    
    except Exception as e:
        return False, f"파일 검증 실패: {str(e)}"

def get_setup_progress() -> Dict[str, bool]:
    """현재 설정 진행률 확인"""
    from app.config import config
    
    return {
        'llm_configured': bool(
            config.app.get('gemini_api_key') or 
            config.app.get('qwen_api_key') or 
            config.app.get('deepseek_api_key')
        ),
        'video_source_configured': bool(
            config.app.get('pexels_api_keys') or 
            config.app.get('pixabay_api_keys')
        ),
        'tts_configured': True,  # Edge TTS는 기본 제공
        'youtube_configured': os.path.exists('client_secrets.json')
    }

def get_quick_start_tips() -> list:
    """빠른 시작을 위한 팁들"""
    return [
        "💡 **팁 1**: Gemini API는 무료 할당량이 있어 처음 사용자에게 추천합니다.",
        "💡 **팁 2**: Pexels는 완전 무료이며 상업적 이용이 가능합니다.",
        "💡 **팁 3**: YouTube 설정은 선택사항이므로 나중에 해도 됩니다.",
        "💡 **팁 4**: 모든 설정은 언제든지 '고급 설정' 탭에서 변경할 수 있습니다.",
        "💡 **팁 5**: API 키는 안전하게 보관되며 외부로 전송되지 않습니다."
    ]

def get_troubleshooting_guide() -> dict:
    """문제 해결 가이드"""
    return {
        "api_key_invalid": {
            "title": "API 키가 작동하지 않아요",
            "solutions": [
                "1. API 키를 다시 복사해서 붙여넣기 해보세요",
                "2. API 키에 공백이 없는지 확인하세요", 
                "3. API 서비스가 활성화되어 있는지 확인하세요",
                "4. 할당량이 남아있는지 확인하세요"
            ]
        },
        "youtube_setup": {
            "title": "YouTube 설정이 어려워요",
            "solutions": [
                "1. Google Cloud Console에서 프로젝트를 먼저 생성하세요",
                "2. YouTube Data API v3를 활성화하세요",
                "3. OAuth 동의 화면을 설정하세요",
                "4. 데스크톱 애플리케이션으로 OAuth 클라이언트를 생성하세요"
            ]
        },
        "slow_generation": {
            "title": "영상 생성이 너무 느려요",
            "solutions": [
                "1. 더 빠른 AI 모델을 선택하세요 (Gemini Flash 등)",
                "2. 영상 길이를 줄여보세요",
                "3. 인터넷 연결 상태를 확인하세요",
                "4. 다른 프로그램을 종료해보세요"
            ]
        }
    }