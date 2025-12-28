import os
import re
import glob
import random
import platform
import sys
import time
import json
import concurrent.futures
from uuid import uuid4

import streamlit as st
from loguru import logger

# Add the root directory of the project to the system path to allow importing modules from the project
root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Import config module
from app.config import config
from webui.setup_helpers import (
    validate_gemini_api_key, validate_pexels_api_key, validate_pixabay_api_key,
    validate_youtube_secrets, get_setup_progress, get_quick_start_tips,
    get_troubleshooting_guide
)
from webui.mobile_optimization import (
    add_mobile_styles, add_mobile_connection_monitor, show_mobile_generation_tips,
    show_mobile_progress_tracker, check_mobile_compatibility, add_mobile_error_recovery
)

st.set_page_config(
    page_title="AI 영상 생성 스튜디오 | MoneyPrinterTurbo",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": "https://github.com/FujiwaraChoki/MoneyPrinterTurbo",
        "Report a bug": "https://github.com/FujiwaraChoki/MoneyPrinterTurbo/issues",
        "About": "# AI 영상 생성 스튜디오\n\n차세대 AI 기반 자동 영상 생성 플랫폼입니다.",
    },
)

# 모바일 최적화 적용
add_mobile_styles()
add_mobile_connection_monitor()
add_mobile_error_recovery()

# 상단 헤더 및 초기설정 버튼
col_title, col_setup_btn = st.columns([3, 1])

with col_title:
    st.title("🎬 AI 영상 생성 스튜디오")
    st.markdown("**차세대 AI 기반 자동 영상 생성 플랫폼**")

with col_setup_btn:
    st.markdown("<br>", unsafe_allow_html=True)  # 버튼 위치 조정
    if st.button("⚙️ 초기설정", use_container_width=True, help="API 키 및 기본 설정을 구성합니다"):
        st.session_state["show_setup"] = True
    
    # 설정 상태 표시
    has_llm = bool(config.app.get('gemini_api_key') or config.app.get('qwen_api_key') or config.app.get('deepseek_api_key'))
    has_video_source = bool(config.app.get('pexels_api_keys') or config.app.get('pixabay_api_keys'))
    is_setup_complete = has_llm and has_video_source
    
    if is_setup_complete:
        st.success("✅ 설정완료")
    else:
        st.warning("⚠️ 설정필요")

# 초기설정 상태 관리
if "show_setup" not in st.session_state:
    st.session_state["show_setup"] = not is_setup_complete  # 설정 미완료시 자동 표시

# 초기설정 화면 표시
if st.session_state.get("show_setup", False):
    # 초기설정 화면
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0; margin-bottom: 2rem;">
        <h2 style="color: #667eea; margin-bottom: 1rem;">🚀 AI 영상 생성 스튜디오 초기설정</h2>
        <p style="font-size: 1.2rem; color: #a0a0a0; margin-bottom: 0.5rem;">프로그램을 처음 사용하시나요?</p>
        <p style="font-size: 1rem; color: #888;">아래 단계를 따라 설정하시면 바로 영상 생성을 시작할 수 있습니다!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 설정 완료 버튼
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✅ 설정 완료 - 영상 생성하기", use_container_width=True, type="primary"):
            st.session_state["show_setup"] = False
            st.rerun()
    
    st.markdown("---")
    
    # === 1단계: AI 언어 모델 설정 ===
    with st.container(border=True):
        st.markdown("### 🤖 **1단계: AI 언어 모델 설정** (필수)")
        
        if has_llm:
            current_provider = config.app.get('llm_provider', 'gemini')
            st.success(f"✅ **설정 완료**: {current_provider.upper()} 모델이 설정되어 있습니다.")
        else:
            st.warning("⚠️ **설정 필요**: AI 대본 생성을 위해 언어 모델 API 키가 필요합니다.")
        
        # Gemini 설정 (간단 버전)
        gemini_api_key = st.text_input(
            "🤖 Gemini API 키 (추천)",
            value=config.app.get('gemini_api_key', ''),
            type="password",
            placeholder="AIza...",
            help="Google AI Studio에서 발급: https://aistudio.google.com/app/apikey"
        )
        
        if st.button("💾 Gemini 설정 저장", use_container_width=True, type="primary"):
            if gemini_api_key:
                config.app['llm_provider'] = 'gemini'
                config.app['gemini_api_key'] = gemini_api_key
                config.app['gemini_model_name'] = 'gemini-2.5-flash-exp'
                config.save_config()
                st.success("✅ Gemini 설정이 저장되었습니다!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ API 키를 입력해주세요!")
    
    # === 2단계: 영상 소스 설정 ===
    with st.container(border=True):
        st.markdown("### 📹 **2단계: 영상 소스 설정** (필수)")
        
        if has_video_source:
            current_source = config.app.get('video_source', 'pexels')
            st.success(f"✅ **설정 완료**: {current_source.upper()} 영상 소스가 설정되어 있습니다.")
        else:
            st.warning("⚠️ **설정 필요**: 배경 영상을 가져올 소스 설정이 필요합니다.")
        
        # Pexels 설정 (간단 버전)
        pexels_api_key = st.text_input(
            "📹 Pexels API 키 (추천)",
            value=config.app.get('pexels_api_keys', [''])[0] if config.app.get('pexels_api_keys') else '',
            type="password",
            placeholder="563492ad6f91700001000001...",
            help="Pexels에서 발급: https://www.pexels.com/api/"
        )
        
        if st.button("💾 Pexels 설정 저장", use_container_width=True, type="primary"):
            if pexels_api_key:
                config.app['video_source'] = 'pexels'
                config.app['pexels_api_keys'] = [pexels_api_key]
                config.save_config()
                st.success("✅ Pexels 설정이 저장되었습니다!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ API 키를 입력해주세요!")
    
    # === 설정 완료 ===
    if is_setup_complete:
        st.markdown("---")
        st.markdown("""
        ### 🎉 **축하합니다! 모든 설정이 완료되었습니다!**
        
        이제 영상 생성을 시작할 수 있습니다!
        """)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 **영상 생성 시작하기**", use_container_width=True, type="primary"):
                st.session_state["show_setup"] = False
                st.success("🎉 영상 생성 화면으로 이동합니다!")
                st.rerun()

else:
    # 메인 화면 - 탭 구조
    tab_main, tab_settings, tab_analytics = st.tabs([
        "🎬 영상 생성", 
        "⚙️ 고급 설정", 
        "📊 분석 & 관리"
    ])

    # --- TAB 1: MAIN (Generate) ---
    with tab_main:
        # Hero Section
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0; margin-bottom: 1rem;">
            <h2 style="color: #667eea; margin-bottom: 0.5rem;">🚀 몇 초 만에 전문가급 영상을 생성하세요</h2>
            <p style="font-size: 1.1rem; color: #a0a0a0;">주제만 입력하면 AI가 대본, 음성, 영상, 자막을 자동으로 생성합니다</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 모바일 사용자 안내
        show_mobile_generation_tips()
        
        # 영상 주제 입력
        with st.container(border=True):
            st.markdown("### 📝 **콘텐츠 기획**")
            st.markdown("*AI가 당신의 아이디어를 완성된 영상으로 만들어드립니다*")
            
            # Subject Input with Premium Design
            st.markdown("#### 🎯 영상 주제")
            video_subject = st.text_input(
                "영상 주제",
                placeholder="예: 성공하는 사람들의 7가지 습관",
                key="video_subject_input",
                label_visibility="collapsed",
                help="구체적이고 흥미로운 주제를 입력하세요. AI가 더 좋은 콘텐츠를 생성합니다."
            ).strip()
            
            # Quick Action Buttons
            col_quick1, col_quick2, col_quick3 = st.columns(3)
            with col_quick1:
                if st.button("💡 영감 얻기", use_container_width=True):
                    inspiration_topics = [
                        "성공하는 사람들의 아침 루틴",
                        "돈을 부르는 5가지 습관",
                        "스트레스 해소하는 간단한 방법",
                        "인생을 바꾸는 독서법",
                        "건강한 다이어트 비법",
                        "시간 관리의 황금 법칙",
                        "자신감을 높이는 방법",
                        "행복한 인간관계 만들기"
                    ]
                    random_topic = random.choice(inspiration_topics)
                    st.session_state["video_subject_input"] = random_topic
                    st.rerun()
            
            with col_quick2:
                if st.button("🔥 트렌드 주제", use_container_width=True):
                    trend_topics = [
                        "2025년 꼭 해야 할 것들",
                        "AI 시대 생존법",
                        "MZ세대가 열광하는 것들",
                        "부자들만 아는 투자 비밀",
                        "미니멀 라이프의 진실",
                        "디지털 디톡스 방법",
                        "새해 목표 달성법",
                        "감정 조절의 기술"
                    ]
                    random_topic = random.choice(trend_topics)
                    st.session_state["video_subject_input"] = random_topic
                    st.rerun()
            
            with col_quick3:
                if st.button("✨ 자동 생성", use_container_width=True, type="primary"):
                    if not video_subject:
                        st.error("먼저 영상 주제를 입력해주세요!")
                    else:
                        st.success("🎬 영상 생성을 시작합니다!")
                        st.info("실제 영상 생성 기능은 원본 파일에서 확인하세요.")

    # --- TAB 2: SETTINGS ---
    with tab_settings:
        st.markdown("### ⚙️ 고급 설정")
        st.info("고급 설정 기능은 원본 파일에서 확인하세요.")

    # --- TAB 3: ANALYTICS ---
    with tab_analytics:
        st.markdown("### 📊 분석 & 관리")
        st.info("분석 및 관리 기능은 원본 파일에서 확인하세요.")