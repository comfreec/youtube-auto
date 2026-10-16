# -*- coding: utf-8 -*-
"""First-run setup wizard for non-technical users."""

import json
import os
import sys
from pathlib import Path

import streamlit as st

from app.config import config
from app.utils.youtube import get_authenticated_service
from webui.api_help_guides import (
    show_gemini_api_guide,
    show_pexels_api_guide,
    show_pixabay_api_guide,
    show_youtube_oauth_guide,
)
from webui.setup_helpers import (
    get_setup_progress,
    validate_gemini_api_key,
    validate_pexels_api_key,
    validate_pixabay_api_key,
    validate_youtube_secrets,
)


ROOT_DIR = Path(__file__).resolve().parent.parent


def setup_required() -> bool:
    """Keep configured upgrades working while forcing wizard for fresh installs."""
    completed = config.ui.get("setup_completed")
    if completed is True:
        return False
    if completed is False:
        return True
    progress = get_setup_progress()
    return not (progress["llm_configured"] and progress["video_source_configured"])


def _next(step: int) -> None:
    st.session_state.setup_wizard_step = step
    st.rerun()


def show_setup_wizard() -> None:
    step = int(st.session_state.get("setup_wizard_step", 1))
    progress = get_setup_progress()

    st.markdown("## 👋 처음 사용 설정")
    st.caption("필수 항목 두 가지만 연결하면 첫 영상을 만들 수 있습니다. YouTube 업로드는 나중에 설정해도 됩니다.")
    st.progress(step / 5, text=f"설정 {step}/5")

    if step == 1:
        st.markdown("### 1. 설치 상태 확인")
        checks = {
            "Python 3.10 이상": sys.version_info >= (3, 10),
            "설정 파일 저장 가능": os.access(ROOT_DIR, os.W_OK),
        }
        for label, ok in checks.items():
            st.write(f"{'✅' if ok else '❌'} {label}")
        st.info("API 키는 이 PC의 config.toml에 저장되며, 영상 생성 시 선택한 서비스에만 전달됩니다.")
        if all(checks.values()) and st.button("설정 시작", type="primary", use_container_width=True):
            _next(2)

    elif step == 2:
        st.markdown("### 2. 대본 생성 AI 연결 (필수)")
        st.markdown("[Google AI Studio에서 Gemini API 키 만들기](https://aistudio.google.com/app/apikey)")
        with st.expander("처음이라면: Gemini API 키 만드는 방법", expanded=True):
            show_gemini_api_guide()
        if progress["llm_configured"]:
            st.success("이미 AI API 키가 설정되어 있습니다.")
        api_key = st.text_input("Gemini API 키", type="password", placeholder="AIza로 시작하는 키")
        if st.button("키 확인 후 저장", type="primary", disabled=not api_key):
            with st.spinner("Google에 연결해 키를 확인하는 중입니다..."):
                ok, message = validate_gemini_api_key(api_key.strip())
            if ok:
                config.app["llm_provider"] = "gemini"
                config.app["gemini_api_key"] = api_key.strip()
                config.save_config()
                st.success(message)
                st.session_state.setup_llm_validated = True
            else:
                st.error(message)
        if progress["llm_configured"] or st.session_state.get("setup_llm_validated"):
            if st.button("다음", use_container_width=True):
                _next(3)

    elif step == 3:
        st.markdown("### 3. 배경 영상 방식 선택 (필수)")
        source = st.radio("사용할 방식", ["Pexels", "Pixabay", "내용맞춤 AI 이미지", "간단 애니메이션"], horizontal=True)
        if source == "내용맞춤 AI 이미지":
            st.info("대본 장면마다 관련 이미지를 만들고 움직임을 적용합니다. 무료 한도 소진 시 무료 영상으로 자동 전환됩니다.")
            if st.button("내용맞춤 AI 이미지 사용", type="primary", use_container_width=True):
                config.app["video_source"] = "ai_image"
                config.save_config()
                st.session_state.setup_video_validated = True
                st.success("내용맞춤 AI 이미지 배경이 선택되었습니다.")
        elif source == "간단 애니메이션":
            st.info("대본 내용에 맞는 간단한 모션 그래픽을 이 PC에서 만듭니다. API 키와 외부 영상 다운로드가 필요 없습니다.")
            if st.button("간단 애니메이션 사용", type="primary", use_container_width=True):
                config.app["video_source"] = "animation"
                config.save_config()
                st.session_state.setup_video_validated = True
                st.success("간단 애니메이션 배경이 선택되었습니다.")
        else:
            link = "https://www.pexels.com/api/" if source == "Pexels" else "https://pixabay.com/api/docs/"
            st.markdown(f"[{source} 무료 API 키 발급 페이지]({link})")
            with st.expander(f"처음이라면: {source} API 키 만드는 방법", expanded=True):
                if source == "Pexels":
                    show_pexels_api_guide()
                else:
                    show_pixabay_api_guide()
            if progress["video_source_configured"]:
                st.success("이미 영상 소스가 설정되어 있습니다.")
            source_key = st.text_input(f"{source} API 키", type="password")
            if st.button("키 확인 후 저장", type="primary", disabled=not source_key):
                with st.spinner(f"{source}에 연결해 키를 확인하는 중입니다..."):
                    validator = validate_pexels_api_key if source == "Pexels" else validate_pixabay_api_key
                    ok, message = validator(source_key.strip())
                if ok:
                    setting = "pexels_api_keys" if source == "Pexels" else "pixabay_api_keys"
                    config.app[setting] = [source_key.strip()]
                    config.app["video_source"] = source.lower()
                    config.save_config()
                    st.success(message)
                    st.session_state.setup_video_validated = True
                else:
                    st.error(message)
        if progress["video_source_configured"] or st.session_state.get("setup_video_validated"):
            if st.button("다음", use_container_width=True):
                _next(4)

    elif step == 4:
        st.markdown("### 4. 기본 음성 확인")
        st.success("한국어: 선희 · 영어: 기존 영어 음성 유지")
        st.write("음성 길이를 기준으로 자막과 영상 길이가 자동으로 맞춰집니다.")
        if st.button("이 설정 사용", type="primary", use_container_width=True):
            config.ui["voice_name"] = "ko-KR-SunHiNeural-Female"
            config.ui["tts_server"] = "azure-tts-v1"
            config.save_config()
            _next(5)

    elif step == 5:
        st.markdown("### 5. YouTube 자동 업로드 (선택)")
        st.write("영상 파일만 만들 예정이면 건너뛰어도 됩니다. 업로드 기능이 필요할 때 언제든 고급 설정에서 추가할 수 있습니다.")
        st.markdown("[YouTube 열기](https://www.youtube.com/) · [Google Cloud Console 열기](https://console.cloud.google.com/)")
        with st.expander("처음이라면: Google 계정부터 YouTube 인증까지", expanded=True):
            st.markdown("""
1. Google 계정으로 YouTube에 로그인하고, 영상 업로드에 사용할 채널을 만듭니다.
2. Google Cloud Console에서 새 프로젝트를 만듭니다.
3. **API 및 서비스 → 라이브러리**에서 **YouTube Data API v3**를 검색해 사용 설정합니다.
4. **Google Auth Platform/OAuth 동의 화면**에서 외부 사용자를 선택하고 본인 이메일을 테스트 사용자로 추가합니다.
5. **사용자 인증 정보 → OAuth 클라이언트 만들기**에서 애플리케이션 유형을 **데스크톱 앱**으로 선택합니다.
6. JSON 파일을 내려받아 아래에 업로드합니다. 파일명은 달라도 괜찮습니다.
7. 업로드 후 **YouTube 로그인 및 권한 승인**을 누르고, 영상을 올릴 채널의 계정을 선택합니다.

주의: JSON과 생성되는 `token.pickle`은 유튜브 계정 인증정보이므로 다른 사람에게 보내지 마세요.
            """)
            show_youtube_oauth_guide()
        uploaded = st.file_uploader("Google OAuth client_secrets.json", type=["json"])
        if uploaded is not None:
            try:
                secrets = json.loads(uploaded.getvalue().decode("utf-8-sig"))
                ok, message = validate_youtube_secrets(secrets)
                if ok:
                    (ROOT_DIR / "client_secrets.json").write_text(
                        json.dumps(secrets, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    st.success(message)
                else:
                    st.error(message)
            except (UnicodeDecodeError, json.JSONDecodeError):
                st.error("JSON 형식의 OAuth 파일이 아닙니다.")

        client_file = ROOT_DIR / "client_secrets.json"
        token_file = ROOT_DIR / "token.pickle"
        if client_file.exists():
            st.success("YouTube OAuth JSON이 준비되었습니다.")
            if token_file.exists():
                st.success("YouTube 로그인 인증도 완료되어 있습니다.")
            if st.button("YouTube 로그인 및 권한 승인", use_container_width=True):
                try:
                    with st.spinner("Google 로그인 창에서 사용할 YouTube 채널을 선택하고 권한을 승인하세요..."):
                        get_authenticated_service(str(client_file), str(token_file))
                    st.success("YouTube 인증이 완료되었습니다.")
                except Exception as exc:
                    st.error(f"YouTube 인증 실패: {exc}")

        if st.button("설정 완료하고 시작", type="primary", use_container_width=True):
            current = get_setup_progress()
            if not current["llm_configured"] or not current["video_source_configured"]:
                st.error("Gemini와 배경 영상 방식을 먼저 설정해주세요.")
            else:
                config.ui["setup_completed"] = True
                config.save_config()
                st.session_state.setup_wizard_step = 1
                st.success("설정이 완료되었습니다.")
                st.rerun()
