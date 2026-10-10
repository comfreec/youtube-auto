# -*- coding: utf-8 -*-
"""First-run setup wizard for non-technical users."""

import json
import os
import sys
from pathlib import Path

import streamlit as st

from app.config import config
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
        st.markdown("### 3. 무료 영상 소스 연결 (필수)")
        source = st.radio("사용할 서비스", ["Pexels", "Pixabay"], horizontal=True)
        link = "https://www.pexels.com/api/" if source == "Pexels" else "https://pixabay.com/api/docs/"
        st.markdown(f"[{source} 무료 API 키 발급 페이지]({link})")
        if progress["video_source_configured"]:
            st.success("이미 영상 소스 API 키가 설정되어 있습니다.")
        source_key = st.text_input(f"{source} API 키", type="password")
        if st.button("키 확인 후 저장", type="primary", disabled=not source_key):
            with st.spinner(f"{source}에 연결해 키를 확인하는 중입니다..."):
                validator = validate_pexels_api_key if source == "Pexels" else validate_pixabay_api_key
                ok, message = validator(source_key.strip())
            if ok:
                setting = "pexels_api_keys" if source == "Pexels" else "pixabay_api_keys"
                config.app[setting] = [source_key.strip()]
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

        if st.button("설정 완료하고 시작", type="primary", use_container_width=True):
            current = get_setup_progress()
            if not current["llm_configured"] or not current["video_source_configured"]:
                st.error("Gemini와 영상 소스 API 키 설정을 먼저 완료해주세요.")
            else:
                config.ui["setup_completed"] = True
                config.save_config()
                st.session_state.setup_wizard_step = 1
                st.success("설정이 완료되었습니다.")
                st.rerun()
