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


def handle_youtube_upload_error(error_message):
    """YouTube 업로드 오류를 분석하고 사용자 친화적인 메시지를 반환"""
    error_str = str(error_message).lower()
    
    if 'invalid_grant' in error_str or 'token has been expired' in error_str or 'revoked' in error_str:
        return {
            'type': 'token_expired',
            'title': '🔐 YouTube 인증 만료',
            'message': 'YouTube 업로드 권한이 만료되었습니다.',
            'solution': [
                "1️⃣ **고급 설정** → **📺 YouTube 업로드 설정** 섹션으로 이동",
                "2️⃣ **🏠 메인 채널 인증** 또는 **⏱️ 타이머 채널 인증** 버튼 클릭",
                "3️⃣ 브라우저에서 Google 계정으로 로그인",
                "4️⃣ YouTube 업로드 권한 승인",
                "5️⃣ 인증 완료 후 다시 업로드 시도"
            ]
        }
    elif 'quota' in error_str or 'limit' in error_str:
        return {
            'type': 'quota_exceeded',
            'title': '📊 YouTube API 할당량 초과',
            'message': 'YouTube API 일일 업로드 한도를 초과했습니다.',
            'solution': [
                "1️⃣ **24시간 후** 다시 시도해주세요",
                "2️⃣ Google Cloud Console에서 할당량 증가 요청 가능",
                "3️⃣ 임시로 수동 업로드를 이용해주세요"
            ]
        }
    elif 'forbidden' in error_str or '403' in error_str:
        return {
            'type': 'permission_denied',
            'title': '🚫 업로드 권한 없음',
            'message': 'YouTube 채널에 업로드 권한이 없습니다.',
            'solution': [
                "1️⃣ YouTube 채널이 **인증된 상태**인지 확인",
                "2️⃣ 채널에 **업로드 권한**이 있는지 확인",
                "3️⃣ Google 계정 설정에서 YouTube 권한 재확인"
            ]
        }
    else:
        return {
            'type': 'general_error',
            'title': '❌ 업로드 오류',
            'message': f'업로드 중 오류가 발생했습니다: {error_message}',
            'solution': [
                "1️⃣ 인터넷 연결 상태 확인",
                "2️⃣ YouTube 인증 상태 재확인",
                "3️⃣ 잠시 후 다시 시도해주세요"
            ]
        }

def display_youtube_error_guide(error_info):
    """YouTube 오류 안내 메시지를 표시"""
    st.error(f"**{error_info['title']}**")
    st.markdown(f"💡 **문제:** {error_info['message']}")
    
    st.markdown("### 🔧 **해결 방법:**")
    for step in error_info['solution']:
        st.markdown(f"   {step}")
    
    if error_info['type'] == 'token_expired':
        st.markdown("---")
        st.info("💡 **참고:** YouTube 인증은 보안상 일정 시간 후 자동으로 만료됩니다. 정기적인 재인증이 필요합니다.")
        
        # 빠른 인증 버튼 제공
        col1, col2, col3 = st.columns(3)
        with col2:
            if st.button("🔐 지금 바로 인증하기", key="quick_auth_btn", use_container_width=True):
                st.markdown("**📺 YouTube 업로드 설정** 섹션으로 스크롤하여 인증을 진행해주세요 ⬇️")


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

# URL 파라미터로 탭 전환 지원
st.markdown("""
<script>
// URL 파라미터 확인 및 탭 전환
function checkUrlParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const tab = urlParams.get('tab');
    
    if (tab) {
        setTimeout(() => {
            const tabs = document.querySelectorAll('[data-baseweb="tab"]');
            let targetTab = null;
            
            switch(tab) {
                case 'setup':
                    targetTab = Array.from(tabs).find(t => t.textContent.includes('🚀 초기설정'));
                    break;
                case 'generate':
                    targetTab = Array.from(tabs).find(t => t.textContent.includes('🎬 영상 생성'));
                    break;
                case 'settings':
                    targetTab = Array.from(tabs).find(t => t.textContent.includes('⚙️ 고급 설정'));
                    break;
                case 'analytics':
                    targetTab = Array.from(tabs).find(t => t.textContent.includes('📊 분석'));
                    break;
            }
            
            if (targetTab) {
                targetTab.click();
                console.log('Switched to tab:', tab);
            }
        }, 500);
    }
}

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', checkUrlParams);
// Streamlit 재렌더링 후에도 실행
setTimeout(checkUrlParams, 1000);
</script>
""", unsafe_allow_html=True)


streamlit_style = """
<style>
    @import url("https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap");
    @import url("https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap");
    
    /* === PREMIUM DARK THEME === */
    :root { 
        color-scheme: dark;
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --accent-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --gold-gradient: linear-gradient(135deg, #ffd89b 0%, #19547b 100%);
        --surface-dark: #0f0f23;
        --surface-card: #1a1a2e;
        --surface-elevated: #16213e;
        --text-primary: #ffffff;
        --text-secondary: #a0a0a0;
        --border-subtle: rgba(255, 255, 255, 0.1);
        --shadow-soft: 0 8px 32px rgba(0, 0, 0, 0.3);
        --shadow-glow: 0 0 20px rgba(102, 126, 234, 0.3);
    }
</style>

<script>
// ULTIMATE FORCE INPUT TEXT COLOR WITH JAVASCRIPT
function forceInputTextColor() {
    // ALL inputs and textareas - MAXIMUM FORCE
    const inputs = document.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        input.style.setProperty('color', '#000000', 'important');
        input.style.setProperty('-webkit-text-fill-color', '#000000', 'important');
        input.style.setProperty('text-shadow', 'none', 'important');
        input.style.setProperty('background-color', 'rgba(255, 255, 255, 0.95)', 'important');
    });
    
    // File uploader - FORCE ALL INTERNAL TEXT BLACK
    const fileUploaders = document.querySelectorAll('[data-testid="stFileUploader"], .stFileUploader');
    fileUploaders.forEach(uploader => {
        // Target ALL internal elements except the main label
        const allElements = uploader.querySelectorAll('*');
        allElements.forEach(el => {
            // Skip if it's the main label (direct child)
            if (el.tagName === 'LABEL' && el.parentElement === uploader) {
                el.style.setProperty('color', '#ffffff', 'important');
            } else {
                el.style.setProperty('color', '#000000', 'important');
                el.style.setProperty('-webkit-text-fill-color', '#000000', 'important');
            }
        });
    });
    
    // Selectbox content - FORCE BLACK TEXT
    const selectboxes = document.querySelectorAll('[data-baseweb="select"], [data-baseweb="popover"]');
    selectboxes.forEach(select => {
        const allText = select.querySelectorAll('*');
        allText.forEach(el => {
            el.style.setProperty('color', '#000000', 'important');
            el.style.setProperty('-webkit-text-fill-color', '#000000', 'important');
        });
    });
    
    // YouTube upload section - FORCE ALL INPUT TEXT BLACK
    const youtubeSection = document.querySelector('[data-testid="stExpander"]');
    if (youtubeSection && youtubeSection.textContent.includes('YouTube')) {
        const inputs = youtubeSection.querySelectorAll('input, textarea, select, button, div[data-baseweb="select"] *');
        inputs.forEach(input => {
            if (input.tagName !== 'LABEL') {
                input.style.setProperty('color', '#000000', 'important');
                input.style.setProperty('-webkit-text-fill-color', '#000000', 'important');
            }
        });
    }
}

// Run AGGRESSIVELY
forceInputTextColor();
setInterval(forceInputTextColor, 500);

// Multiple observers for maximum coverage
const observer1 = new MutationObserver(forceInputTextColor);
observer1.observe(document.body, { childList: true, subtree: true, attributes: true });

const observer2 = new MutationObserver(() => {
    setTimeout(forceInputTextColor, 100);
});
observer2.observe(document.body, { childList: true, subtree: true });

// Force on all events
document.addEventListener('DOMContentLoaded', forceInputTextColor);
document.addEventListener('click', () => setTimeout(forceInputTextColor, 100));
document.addEventListener('focus', () => setTimeout(forceInputTextColor, 100));
</script>

<style>
    
    /* Base App */
    .stApp { 
        background: var(--surface-dark);
        color: var(--text-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
        font-weight: 400;
        line-height: 1.6;
    }
    
    /* Premium Typography */
    h1 { 
        font-family: 'Inter', sans-serif;
        font-weight: 900;
        font-size: 2.5rem !important;
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin: 2rem 0 3rem 0 !important;
        letter-spacing: -0.02em;
        position: relative;
    }
    
    h1::after {
        content: '';
        position: absolute;
        bottom: -10px;
        left: 50%;
        transform: translateX(-50%);
        width: 100px;
        height: 3px;
        background: var(--accent-gradient);
        border-radius: 2px;
    }
    
    h2, h3, h4, h5, h6 { 
        color: var(--text-primary) !important; 
        font-weight: 700; 
        letter-spacing: -0.01em;
        margin-top: 2rem !important;
    }
    
    /* Premium Text Styling */
    body, .stApp, .stMarkdown, p, label, span, div { 
        color: var(--text-primary) !important; 
    }
    
    .stTextInput label, .stTextArea label, .stSelectbox label, 
    .stSlider label, .stCheckbox label, .stRadio label { 
        color: #ffffff !important; 
        font-size: 0.875rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem !important;
    }
    
    /* FORCE LABEL TEXT TO WHITE - STRONGER RULES */
    .stSelectbox > label {
        color: #ffffff !important;
    }
    
    .stSelectbox label {
        color: #ffffff !important;
    }
    
    /* Force all form labels to be white */
    label {
        color: #ffffff !important;
    }
    
    /* Specific targeting for selectbox labels */
    div.stSelectbox > label,
    div.stSelectbox label,
    .stSelectbox > div > label {
        color: #ffffff !important;
    }
    
    /* ULTIMATE FORCE - ALL LABELS WHITE */
    * label,
    *[data-testid*="stSelectbox"] label,
    *[data-testid*="stSelectbox"] > label,
    div[data-testid="stSelectbox"] label,
    div[data-testid="stSelectbox"] > label {
        color: #ffffff !important;
    }
    
    /* Force white text for any element that might be a label */
    .stSelectbox ~ label,
    .stSelectbox + label,
    .stSelectbox label,
    .stSelectbox > label,
    .stSelectbox div label {
        color: #ffffff !important;
    }
    
    /* NUCLEAR OPTION - FORCE ALL TEXT IN SETTINGS TAB TO WHITE */
    div[data-testid="stVerticalBlockBorderWrapper"] label,
    div[data-testid="stVerticalBlockBorderWrapper"] * label,
    div[data-testid="stVerticalBlockBorderWrapper"] span,
    div[data-testid="stVerticalBlockBorderWrapper"] p {
        color: #ffffff !important;
    }
    
    /* Force all text elements to white except selectbox content */
    .stApp label,
    .stApp span:not([data-baseweb*="select"]),
    .stApp p:not([data-baseweb*="select"]) {
        color: #ffffff !important;
    }
    
    /* Override everything except selectbox internals */
    * {
        color: #ffffff !important;
    }
    
    /* But keep selectbox content black */
    .stSelectbox div[data-baseweb="select"] *,
    div[data-baseweb="popover"] *,
    li[data-baseweb="option"] * {
        color: #000000 !important;
    }
    
    /* Hover states with white text */
    li[data-baseweb="option"]:hover *,
    li[data-baseweb="option"][aria-selected="true"] * {
        color: white !important;
    }
    
    /* Premium Cards & Containers */
    div[data-testid="stVerticalBlockBorderWrapper"] { 
        background: var(--surface-card);
        border-radius: 20px;
        padding: 2rem;
        border: 1px solid var(--border-subtle);
        box-shadow: var(--shadow-soft);
        margin-bottom: 2rem;
        backdrop-filter: blur(10px);
        position: relative;
        overflow: hidden;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: var(--primary-gradient);
        opacity: 0.6;
    }
    
    /* Premium Input Fields */
    .stTextInput input, .stTextArea textarea { 
        background: rgba(255, 255, 255, 0.95) !important;
        color: #000000 !important;
        border: 2px solid var(--border-subtle) !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        font-size: 1rem !important;
        padding: 1rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(10px);
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
        background: rgba(255, 255, 255, 0.98) !important;
        color: #000000 !important;
        transform: translateY(-1px);
    }
    
    .stTextInput input::placeholder, .stTextArea textarea::placeholder { 
        color: #666666 !important;
        font-style: italic;
    }
    
    /* Premium Subject Input (Center Aligned) */
    .stTextInput input {
        text-align: center !important;
        font-size: 1.125rem !important;
        font-weight: 600 !important;
        color: #000000 !important;
    }
    
    /* Premium Input Fields */
    .stTextInput input, .stTextArea textarea { 
        background: rgba(255, 255, 255, 0.95) !important;
        color: #000000 !important;
        border: 2px solid var(--border-subtle) !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        font-size: 1rem !important;
        padding: 1rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(10px);
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
        background: rgba(255, 255, 255, 0.98) !important;
        color: #000000 !important;
        transform: translateY(-1px);
    }
    
    .stTextInput input::placeholder, .stTextArea textarea::placeholder { 
        color: #666666 !important;
        font-style: italic;
    }
    
    /* Premium Subject Input (Center Aligned) */
    .stTextInput input {
        text-align: center !important;
        font-size: 1.125rem !important;
        font-weight: 600 !important;
        color: #000000 !important;
    }
    
    /* Number inputs */
    .stNumberInput input {
        background: rgba(255, 255, 255, 0.95) !important;
        color: #000000 !important;
        border: 2px solid var(--border-subtle) !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
    }
    
    /* Slider inputs */
    .stSlider input {
        color: #000000 !important;
    }
    
    /* ULTIMATE NUCLEAR OPTION - FORCE ALL TEXT TO BLACK IN INPUTS */
    input[type="text"] !important, 
    input[type="number"] !important, 
    input[type="email"] !important, 
    input[type="password"] !important,
    input[type="file"] !important,
    textarea !important,
    select !important {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        text-shadow: none !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* MAXIMUM PRIORITY - ALL STREAMLIT INPUTS */
    .stTextInput > div > div > input !important,
    .stNumberInput > div > div > input !important,
    .stTextArea > div > div > textarea !important,
    .stFileUploader input !important,
    div[data-baseweb="input"] > input !important,
    div[data-baseweb="textarea"] > textarea !important,
    div[data-baseweb="select"] * !important {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        text-shadow: none !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* NUCLEAR OPTION - FORCE ALL INPUT ELEMENTS */
    html body .stApp * input,
    html body .stApp * textarea,
    html body .stApp * select,
    html body div * input,
    html body div * textarea,
    html body div * select {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        text-shadow: none !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* STREAMLIT SPECIFIC CLASSES - MAXIMUM FORCE */
    .st-emotion-cache-1y4p8pa input,
    .st-emotion-cache-1y4p8pa textarea,
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stFileUploader"] input,
    [data-testid="stFileUploader"] div,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] button {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* File uploader - FORCE ALL INTERNAL TEXT BLACK */
    .stFileUploader > div,
    .stFileUploader button,
    .stFileUploader small,
    .stFileUploader span:not(.stFileUploader > label span),
    [data-testid="stFileUploader"] > div,
    [data-testid="stFileUploader"] button,
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span:not([data-testid="stFileUploader"] > label span) {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* KEEP ONLY MAIN FILE UPLOADER LABELS WHITE */
    .stFileUploader > label,
    [data-testid="stFileUploader"] > label {
        color: #ffffff !important;
    }
    
    /* YOUTUBE UPLOAD SECTION - FORCE EVERYTHING BLACK EXCEPT LABELS */
    [data-testid="stExpander"] input,
    [data-testid="stExpander"] textarea,
    [data-testid="stExpander"] select,
    [data-testid="stExpander"] button span,
    [data-testid="stExpander"] div[data-baseweb="select"] *,
    [data-testid="stExpander"] [data-testid="stFileUploader"] div,
    [data-testid="stExpander"] [data-testid="stFileUploader"] span:not(label span),
    [data-testid="stExpander"] [data-testid="stFileUploader"] button {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* Premium Select Boxes - FORCE FULL WIDTH AND NO TRUNCATION */
    .stSelectbox div[data-baseweb="select"] {
        background: rgba(255, 255, 255, 0.95) !important;
        color: #000000 !important;
        border: 2px solid var(--border-subtle) !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
        min-width: 100% !important;
        width: 100% !important;
        max-width: none !important;
        overflow: visible !important;
    }
    
    /* FORCE SELECTBOX CONTAINER TO FULL WIDTH */
    .stSelectbox > div {
        width: 100% !important;
        max-width: none !important;
        overflow: visible !important;
    }
    
    .stSelectbox {
        width: 100% !important;
        max-width: none !important;
        overflow: visible !important;
    }
    
    /* Force text color and prevent truncation in selectbox - NUCLEAR OPTION */
    .stSelectbox div[data-baseweb="select"] > div {
        color: #000000 !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        width: 100% !important;
        max-width: none !important;
    }
    
    .stSelectbox div[data-baseweb="select"] span {
        color: #000000 !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        width: auto !important;
        max-width: none !important;
        display: inline-block !important;
    }
    
    .stSelectbox div[data-baseweb="select"] div[data-baseweb="select-value"] {
        color: #000000 !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        width: 100% !important;
        max-width: none !important;
    }
    
    /* Selectbox placeholder and selected text - ABSOLUTELY NO TRUNCATION */
    .stSelectbox div[data-baseweb="select"] div[data-baseweb="select-value"] span {
        color: #000000 !important;
        font-weight: 500 !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        width: auto !important;
        max-width: none !important;
        display: inline-block !important;
        min-width: max-content !important;
    }
    
    /* NUCLEAR OPTION FOR SELECTBOX - Override all Streamlit constraints */
    .stSelectbox * {
        max-width: none !important;
        overflow: visible !important;
        text-overflow: clip !important;
        white-space: nowrap !important;
    }
    
    /* Force selectbox to expand to content */
    [data-baseweb="select"] {
        width: max-content !important;
        min-width: 100% !important;
        max-width: none !important;
    }
    
    [data-baseweb="select-value"] {
        width: max-content !important;
        max-width: none !important;
    }
    
    .stSelectbox div[data-baseweb="select"]:focus-within { 
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
        transform: translateY(-1px);
    }
    
    /* Premium Dropdown Menus - MAXIMUM WIDTH AND NO CONSTRAINTS */
    div[data-baseweb="popover"] {
        background: rgba(255, 255, 255, 0.98) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 16px !important;
        box-shadow: var(--shadow-soft) !important;
        backdrop-filter: blur(20px);
        min-width: 400px !important;
        max-width: none !important;
        width: auto !important;
        overflow: visible !important;
    }
    
    div[data-baseweb="menu"], ul[data-baseweb="menu"] {
        background: transparent !important;
        min-width: 400px !important;
        max-width: none !important;
        width: auto !important;
        overflow: visible !important;
    }
    
    li[data-baseweb="option"] {
        background: transparent !important;
        color: #000000 !important;
        padding: 0.75rem 1rem !important;
        border-radius: 8px !important;
        margin: 0.25rem !important;
        transition: all 0.2s ease;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        min-width: 380px !important;
        width: auto !important;
        max-width: none !important;
        display: block !important;
    }
    
    /* Force text color in dropdown options - NO TRUNCATION */
    li[data-baseweb="option"] span {
        color: #000000 !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        display: inline-block !important;
        width: auto !important;
        max-width: none !important;
        min-width: 250px !important;
    }
    
    li[data-baseweb="option"] div {
        color: #000000 !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        width: auto !important;
        max-width: none !important;
        min-width: 250px !important;
    }
    
    /* Force all text elements in dropdown to be visible */
    li[data-baseweb="option"] * {
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        max-width: none !important;
        width: auto !important;
    }
    
    /* NUCLEAR OPTION - Override all Streamlit dropdown constraints */
    [data-baseweb="popover"] * {
        max-width: none !important;
        overflow: visible !important;
        text-overflow: clip !important;
        white-space: nowrap !important;
    }
    
    /* Force dropdown to expand to content width */
    [data-baseweb="menu"] {
        width: max-content !important;
        min-width: 400px !important;
    }
    
    [data-baseweb="option"] {
        width: max-content !important;
        min-width: 380px !important;
    }
    
    li[data-baseweb="option"]:hover, 
    li[data-baseweb="option"][aria-selected="true"] {
        background: var(--primary-gradient) !important;
        color: white !important;
        transform: translateX(4px);
    }
    
    /* Force white text on hover/selected */
    li[data-baseweb="option"]:hover span,
    li[data-baseweb="option"][aria-selected="true"] span,
    li[data-baseweb="option"]:hover div,
    li[data-baseweb="option"][aria-selected="true"] div {
        color: white !important;
    }
    
    /* Premium Buttons */
    .stButton > button, .stDownloadButton > button {
        background: var(--surface-elevated) !important;
        border: 2px solid var(--border-subtle) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.875rem 1.5rem !important;
        border-radius: 12px !important;
        box-shadow: var(--shadow-soft) !important;
        width: 100% !important;
        margin-bottom: 0.75rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(10px);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(102, 126, 234, 0.3) !important;
        border-color: #667eea !important;
    }
    
    /* Primary Buttons (Special Gradient) */
    .stButton button[kind="primary"] { 
        background: var(--primary-gradient) !important;
        border: none !important;
        color: white !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        padding: 1.25rem 2rem !important;
        box-shadow: var(--shadow-glow) !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .stButton button[kind="primary"]:hover { 
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 16px 50px rgba(102, 126, 234, 0.4) !important;
    }
    
    /* Premium Sidebar */
    section[data-testid="stSidebar"] { 
        background: var(--surface-dark);
        border-right: 1px solid var(--border-subtle);
        backdrop-filter: blur(20px);
    }
    
    /* Premium Progress Bars */
    .stProgress > div > div > div > div {
        background: var(--primary-gradient) !important;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(102, 126, 234, 0.5);
    }
    
    /* Premium Expanders */
    .streamlit-expanderHeader {
        background: var(--surface-elevated) !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        padding: 1rem !important;
        border: 1px solid var(--border-subtle) !important;
        transition: all 0.3s ease;
    }
    
    .streamlit-expanderHeader:hover {
        background: var(--surface-card) !important;
        transform: translateY(-1px);
    }
    
    /* Premium Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background: var(--surface-card);
        padding: 0.5rem;
        border-radius: 16px;
        border: 1px solid var(--border-subtle);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: var(--text-secondary) !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.75rem 1.5rem !important;
        transition: all 0.3s ease;
        border: none !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(102, 126, 234, 0.1) !important;
        color: var(--text-primary) !important;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: var(--primary-gradient) !important;
        color: white !important;
        box-shadow: var(--shadow-glow);
    }
    
    /* Premium Layout & Spacing - Ultra Compact & Cute */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        max-width: 1000px !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    div[data-testid="column"] {
        gap: 0.5rem;
    }
    
    /* Cute and compact title */
    h1 { 
        font-family: 'Inter', sans-serif;
        font-weight: 900;
        font-size: 1.8rem !important;
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin: 0.5rem 0 1rem 0 !important;
        letter-spacing: -0.02em;
        position: relative;
    }
    
    h2, h3, h4, h5, h6 { 
        color: var(--text-primary) !important; 
        font-weight: 700; 
        letter-spacing: -0.01em;
        margin-top: 0.5rem !important;
        margin-bottom: 0.25rem !important;
        font-size: 1.1rem !important;
    }
    
    /* Ultra compact containers with cute styling */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--surface-card);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid var(--border-subtle);
        box-shadow: var(--shadow-soft);
        margin-bottom: 0.5rem;
        backdrop-filter: blur(10px);
        position: relative;
    }
    
    /* Ultra compact form elements */
    .stSelectbox, .stTextInput, .stTextArea, .stSlider {
        margin-bottom: 0.25rem !important;
    }
    
    /* Compact input fields with cute styling */
    .stTextInput input, .stTextArea textarea { 
        background: rgba(255, 255, 255, 0.95) !important;
        color: #000000 !important;
        border: 2px solid var(--border-subtle) !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        padding: 0.5rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(10px);
    }
    
    /* Compact buttons with cute styling */
    .stButton > button, .stDownloadButton > button {
        background: var(--surface-elevated) !important;
        border: 2px solid var(--border-subtle) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.5rem 1rem !important;
        border-radius: 8px !important;
        box-shadow: var(--shadow-soft) !important;
        width: 100% !important;
        margin-bottom: 0.25rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(10px);
    }
    
    /* Compact primary buttons */
    .stButton button[kind="primary"] { 
        background: var(--primary-gradient) !important;
        border: none !important;
        color: white !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        padding: 0.75rem 1.5rem !important;
        box-shadow: var(--shadow-glow) !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Ultra compact tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.25rem;
        background: var(--surface-card);
        padding: 0.25rem;
        border-radius: 8px;
        border: 1px solid var(--border-subtle);
        margin-bottom: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: var(--text-secondary) !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease;
        border: none !important;
        font-size: 0.85rem !important;
    }
    
    /* Ultra compact expanders */
    .streamlit-expanderHeader {
        padding: 0.5rem 0.75rem !important;
        font-size: 0.9rem !important;
    }
    
    /* Reduce line height for better density */
    .stApp { 
        background: var(--surface-dark);
        color: var(--text-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
        font-weight: 400;
        line-height: 1.4;
    }
    
    /* Premium Success/Error Messages */
    .stSuccess {
        background: linear-gradient(135deg, #00c851 0%, #007e33 100%) !important;
        border: none !important;
        border-radius: 12px !important;
        color: white !important;
        font-weight: 600 !important;
    }
    
    .stError {
        background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%) !important;
        border: none !important;
        border-radius: 12px !important;
        color: white !important;
        font-weight: 600 !important;
    }
    
    .stWarning {
        background: linear-gradient(135deg, #ffbb33 0%, #ff8800 100%) !important;
        border: none !important;
        border-radius: 12px !important;
        color: white !important;
        font-weight: 600 !important;
    }
    
    .stInfo {
        background: linear-gradient(135deg, #33b5e5 0%, #0099cc 100%) !important;
        border: none !important;
        border-radius: 12px !important;
        color: white !important;
        font-weight: 600 !important;
    }
    
    /* Premium Video Player */
    video {
        border-radius: 16px !important;
        box-shadow: var(--shadow-soft) !important;
        border: 1px solid var(--border-subtle) !important;
    }
    
    /* Premium Checkboxes & Radio */
    .stCheckbox, .stRadio {
        padding: 0.5rem 0 !important;
    }
    
    /* Premium Color Picker */
    .stColorPicker > div > div {
        border-radius: 12px !important;
        border: 2px solid var(--border-subtle) !important;
        transition: all 0.3s ease;
    }
    
    .stColorPicker > div > div:hover {
        border-color: #667eea !important;
        transform: scale(1.05);
    }
    
    /* Premium Sliders */
    .stSlider > div > div > div {
        background: var(--surface-elevated) !important;
        border-radius: 20px !important;
    }
    
    .stSlider > div > div > div > div {
        background: var(--primary-gradient) !important;
        border-radius: 20px !important;
    }
    
    /* Hide Streamlit Branding */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    footer {
        display: none !important;
    }
    
    #MainMenu {
        visibility: hidden;
    }
    
    .stDeployButton {
        display: none;
    }
    
    /* Premium Mobile Responsiveness - Ultra Compact */
    @media (max-width: 768px) {
        .block-container {
            padding: 0.75rem !important;
        }
        
        h1 {
            font-size: 1.8rem !important;
            margin: 0.5rem 0 1rem 0 !important;
        }
        
        h2, h3, h4, h5, h6 {
            margin-top: 0.75rem !important;
            margin-bottom: 0.25rem !important;
        }
        
        div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 1rem !important;
            margin-bottom: 0.75rem !important;
        }
        
        .stButton > button {
            min-height: 44px !important;
            font-size: 0.9rem !important;
            padding: 0.5rem 1rem !important;
        }
        
        div[data-testid="column"] {
            gap: 0.5rem !important;
        }
        
        .stSelectbox, .stTextInput, .stTextArea, .stSlider {
            margin-bottom: 0.25rem !important;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            padding: 0.25rem;
            margin-bottom: 0.5rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0.5rem 1rem !important;
            font-size: 0.9rem !important;
        }
    }
    
    /* Premium Loading Animations */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    @keyframes slideIn {
        from { transform: translateY(20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"] {
        animation: slideIn 0.6s ease-out;
    }
    
    /* Premium Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--surface-dark);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--primary-gradient);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--accent-gradient);
    }
    
    /* FORCE SELECTBOX TEXT VISIBILITY - UNIVERSAL RULES */
    .stSelectbox * {
        color: #000000 !important;
    }
    
    .stSelectbox div[data-baseweb="select"] * {
        color: #000000 !important;
    }
    
    /* Dropdown menu text visibility - BLACK TEXT ON WHITE BACKGROUND */
    div[data-baseweb="popover"] * {
        color: #000000 !important;
    }
    
    /* Override any inherited text colors for selectbox - KEEP WHITE */
    .stSelectbox, .stSelectbox div, .stSelectbox span {
        color: #000000 !important;
    }
    
    /* Ensure dropdown options are visible - BLACK TEXT */
    li[data-baseweb="option"], li[data-baseweb="option"] * {
        color: #000000 !important;
    }
    
    /* Hover states with white text */
    li[data-baseweb="option"]:hover,
    li[data-baseweb="option"]:hover *,
    li[data-baseweb="option"][aria-selected="true"],
    li[data-baseweb="option"][aria-selected="true"] * {
        color: white !important;
        background-color: transparent !important;
    }
</style>
"""
st.markdown(streamlit_style, unsafe_allow_html=True)

# Imports moved here to speed up UI rendering
from app.config import config
from app.models import const
from app.models.schema import (
    MaterialInfo,
    VideoAspect,
    VideoConcatMode,
    VideoParams,
    VideoTransitionMode,
)
from app.services import llm, voice
from app.services import task as tm
from app.services import state as sm
from app.utils import utils
from app.utils.youtube import get_authenticated_service, upload_video

# 定义资源目录
font_dir = os.path.join(root_dir, "resource", "fonts")
song_dir = os.path.join(root_dir, "resource", "songs")
i18n_dir = os.path.join(root_dir, "webui", "i18n")
config_file = os.path.join(root_dir, "webui", ".streamlit", "webui.toml")
system_locale = utils.get_system_locale()


if "video_subject" not in st.session_state:
    st.session_state["video_subject"] = ""
if "video_script" not in st.session_state:
    st.session_state["video_script"] = ""
if "video_terms" not in st.session_state:
    st.session_state["video_terms"] = ""
if "ui_language" not in st.session_state:
    st.session_state["ui_language"] = config.ui.get("language", system_locale)

# 로케일 로드 (유지)
locales = utils.load_locales(i18n_dir)

# 언어 설정 강제 고정 (한국어)
st.session_state["ui_language"] = "ko-KR"
config.ui["language"] = "ko-KR"

support_locales = [
    "ko-KR",
    "zh-CN",
    "zh-HK",
    "zh-TW",
    "de-DE",
    "en-US",
    "fr-FR",
    "vi-VN",
    "th-TH",
    "tr-TR",
]


def get_all_fonts():
    fonts = []
    for root, dirs, files in os.walk(font_dir):
        for file in files:
            if file.endswith(".ttf") or file.endswith(".ttc"):
                fonts.append(file)
    fonts.sort()
    return fonts


def get_all_songs():
    songs = []
    for root, dirs, files in os.walk(song_dir):
        for file in files:
            if file.endswith(".mp3"):
                songs.append(file)
    return songs


def open_task_folder(task_id):
    try:
        sys = platform.system()
        path = os.path.join(root_dir, "storage", "tasks", task_id)
        if os.path.exists(path):
            if sys == "Windows":
                os.system(f"start {path}")
            if sys == "Darwin":
                os.system(f"open {path}")
    except Exception as e:
        logger.error(e)


def scroll_to_bottom():
    js = """
    <script>
        console.log("scroll_to_bottom");
        function scroll(dummy_var_to_force_repeat_execution){
            var sections = parent.document.querySelectorAll('section.main');
            console.log(sections);
            for(let index = 0; index<sections.length; index++) {
                sections[index].scrollTop = sections[index].scrollHeight;
            }
        }
        scroll(1);
    </script>
    """
    st.components.v1.html(js, height=0, width=0)


def init_log():
    logger.remove()
    _lvl = "DEBUG"

    def format_record(record):
        # 获取日志记录中的文件全路径
        file_path = record["file"].path
        # 将绝对路径转换为相对于项目根目录的路径
        relative_path = os.path.relpath(file_path, root_dir)
        # 更新记录中的文件路径
        record["file"].path = f"./{relative_path}"
        # 返回修改后的格式字符串
        # 您可以根据需要调整这里的格式
        record["message"] = record["message"].replace(root_dir, ".")

        _format = (
            "<green>{time:%Y-%m-%d %H:%M:%S}</> | "
            + "<level>{level}</> | "
            + '"{file.path}:{line}":<blue> {function}</> '
            + "- <level>{message}</>"
            + "\n"
        )
        return _format

    logger.add(
        sys.stdout,
        level=_lvl,
        format=format_record,
        colorize=True,
    )
    logger.add("debug_session.log", level="DEBUG", format=format_record, rotation="10 MB")


init_log()

locales = utils.load_locales(i18n_dir)


def tr(key):
    loc = locales.get(st.session_state["ui_language"], {})
    return loc.get("Translation", {}).get(key, key)


# Legacy settings removed - migrated to Tabs


llm_provider = config.app.get("llm_provider", "").lower()

# --- PREMIUM TABBED INTERFACE ---
params = VideoParams(video_subject="")
uploaded_files = None

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
    
    # 기존 초기설정 내용을 여기에 포함
    # 설정 완료 상태 체크
    setup_status = get_setup_progress()
    
    total_steps = len(setup_status)
    completed_steps = sum(setup_status.values())
    progress = completed_steps / total_steps
    
    # 전체 진행률 표시
    st.markdown("### 📊 설정 진행률")
    progress_bar = st.progress(progress)
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{completed_steps}/{total_steps} 단계 완료**")
    with col2:
        st.markdown(f"**{progress*100:.0f}%**")
    
    if progress == 1.0:
        st.success("🎉 **모든 설정이 완료되었습니다!** 이제 영상을 만들어보세요.")
        st.balloons()
    else:
        st.info(f"⚡ **{total_steps - completed_steps}개 단계**만 더 설정하면 완료됩니다!")
    
    # 빠른 시작 팁
    with st.expander("💡 **빠른 시작 팁**", expanded=not setup_status['llm_configured']):
        tips = get_quick_start_tips()
        for tip in tips:
            st.markdown(tip)
    
    st.markdown("---")

else:
    # 메인 화면 - 탭 구조
    tab_main, tab_settings, tab_analytics = st.tabs([
        "🎬 영상 생성", 
        "⚙️ 고급 설정", 
        "📊 분석 & 관리"
    ])

# --- TAB 1: MAIN (Generate) ---
with tab_main:
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0; margin-bottom: 2rem;">
        <h2 style="color: #667eea; margin-bottom: 1rem;">🚀 AI 영상 생성 스튜디오 초기설정</h2>
        <p style="font-size: 1.2rem; color: #a0a0a0; margin-bottom: 0.5rem;">프로그램을 처음 사용하시나요?</p>
        <p style="font-size: 1rem; color: #888;">아래 단계를 따라 설정하시면 바로 영상 생성을 시작할 수 있습니다!</p>
        </div>
        """, unsafe_allow_html=True)
    
        # 설정 완료 상태 체크
        setup_status = get_setup_progress()
    
        total_steps = len(setup_status)
        completed_steps = sum(setup_status.values())
    progress = completed_steps / total_steps
    
    # 전체 진행률 표시
    st.markdown("### 📊 설정 진행률")
    progress_bar = st.progress(progress)
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{completed_steps}/{total_steps} 단계 완료**")
    with col2:
        st.markdown(f"**{progress*100:.0f}%**")
    
    if progress == 1.0:
        st.success("🎉 **모든 설정이 완료되었습니다!** 이제 영상을 만들어보세요.")
        st.balloons()
    else:
        st.info(f"⚡ **{total_steps - completed_steps}개 단계**만 더 설정하면 완료됩니다!")
    
        # 빠른 시작 팁
        with st.expander("💡 **빠른 시작 팁**", expanded=not setup_status['llm_configured']):
        tips = get_quick_start_tips()
        for tip in tips:
            st.markdown(tip)
    
        st.markdown("---")
    
        # === 1단계: AI 언어 모델 설정 ===
        with st.container(border=True):
        status_icon = "✅" if setup_status['llm_configured'] else "⚠️"
        st.markdown(f"### {status_icon} **1단계: AI 언어 모델 설정** (필수)")
        
        if setup_status['llm_configured']:
            current_provider = config.app.get('llm_provider', 'gemini')
            st.success(f"✅ **설정 완료**: {current_provider.upper()} 모델이 설정되어 있습니다.")
        else:
            st.warning("⚠️ **설정 필요**: AI 대본 생성을 위해 언어 모델 API 키가 필요합니다.")
        
        st.markdown("""
        **AI 언어 모델**은 영상의 대본과 내용을 자동으로 생성합니다.
        
        **추천 순서:**
        1. **Google Gemini** (무료 할당량 제공, 한국어 우수) ⭐
        2. **Qwen** (알리바바, 성능 우수)
        3. **DeepSeek** (저렴한 가격)
        """)
        
        # 모델 선택
        llm_provider = st.selectbox(
            "AI 언어 모델 선택",
            options=["gemini", "qwen", "deepseek"],
            index=["gemini", "qwen", "deepseek"].index(config.app.get('llm_provider', 'gemini')),
            format_func=lambda x: {
                "gemini": "🤖 Google Gemini (추천)",
                "qwen": "🚀 Qwen (알리바바)",
                "deepseek": "💰 DeepSeek (저렴)"
            }[x],
            help="각 모델의 특징을 확인하고 선택하세요"
        )
        
        # 선택된 모델에 따른 설정
        if llm_provider == "gemini":
            st.markdown("""
            #### 🤖 Google Gemini 설정
            
            **장점:**
            - 무료 할당량 제공 (월 15달러 상당)
            - 한국어 성능 우수
            - 빠른 응답 속도
            
            **API 키 발급 방법:**
            1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
            2. Google 계정으로 로그인
            3. "Create API Key" 클릭
            4. 생성된 키를 아래에 입력
            """)
            
            gemini_api_key = st.text_input(
                "Gemini API 키",
                value=config.app.get('gemini_api_key', ''),
                type="password",
                placeholder="AIza...",
                help="Google AI Studio에서 발급받은 API 키를 입력하세요"
            )
            
            # API 키 실시간 검증
            if gemini_api_key and gemini_api_key != config.app.get('gemini_api_key', ''):
                with st.spinner("API 키 검증 중..."):
                    is_valid, message = validate_gemini_api_key(gemini_api_key)
                    if is_valid:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")
            
            gemini_model = st.selectbox(
                "Gemini 모델 선택",
                options=["gemini-2.5-flash-exp", "gemini-1.5-flash-latest", "gemini-1.5-pro-latest"],
                index=0,
                format_func=lambda x: {
                    "gemini-2.5-flash-exp": "Gemini 2.5 Flash (최신, 빠름, 추천)",
                    "gemini-1.5-flash-latest": "Gemini 1.5 Flash (안정적)",
                    "gemini-1.5-pro-latest": "Gemini 1.5 Pro (고성능)"
                }[x]
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔍 API 키 테스트", use_container_width=True):
                    if gemini_api_key:
                        with st.spinner("API 키 테스트 중..."):
                            is_valid, message = validate_gemini_api_key(gemini_api_key)
                            if is_valid:
                                st.success(f"✅ {message}")
                            else:
                                st.error(f"❌ {message}")
                    else:
                        st.error("❌ API 키를 입력해주세요!")
            
            with col2:
                if st.button("💾 Gemini 설정 저장", use_container_width=True, type="primary"):
                    if gemini_api_key:
                        config.app['llm_provider'] = 'gemini'
                        config.app['gemini_api_key'] = gemini_api_key
                        config.app['gemini_model_name'] = gemini_model
                        config.save_config()
                        st.success("✅ Gemini 설정이 저장되었습니다!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ API 키를 입력해주세요!")
        
        elif llm_provider == "qwen":
            st.markdown("""
            #### 🚀 Qwen 설정
            
            **장점:**
            - 알리바바의 고성능 모델
            - 다국어 지원 우수
            - 합리적인 가격
            
            **API 키 발급 방법:**
            1. [DashScope](https://dashscope.aliyun.com/) 접속
            2. 알리바바 클라우드 계정 생성/로그인
            3. API 키 생성
            4. 생성된 키를 아래에 입력
            """)
            
            qwen_api_key = st.text_input(
                "Qwen API 키",
                value=config.app.get('qwen_api_key', ''),
                type="password",
                placeholder="sk-...",
                help="DashScope에서 발급받은 API 키를 입력하세요"
            )
            
            if st.button("💾 Qwen 설정 저장", use_container_width=True):
                if qwen_api_key:
                    config.app['llm_provider'] = 'qwen'
                    config.app['qwen_api_key'] = qwen_api_key
                    config.app['qwen_model_name'] = 'qwen-max'
                    config.save_config()
                    st.success("✅ Qwen 설정이 저장되었습니다!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ API 키를 입력해주세요!")
        
        elif llm_provider == "deepseek":
            st.markdown("""
            #### 💰 DeepSeek 설정
            
            **장점:**
            - 매우 저렴한 가격
            - 좋은 성능
            - OpenAI 호환 API
            
            **API 키 발급 방법:**
            1. [DeepSeek](https://platform.deepseek.com/) 접속
            2. 계정 생성/로그인
            3. API 키 생성
            4. 생성된 키를 아래에 입력
            """)
            
            deepseek_api_key = st.text_input(
                "DeepSeek API 키",
                value=config.app.get('deepseek_api_key', ''),
                type="password",
                placeholder="sk-...",
                help="DeepSeek에서 발급받은 API 키를 입력하세요"
            )
            
            if st.button("💾 DeepSeek 설정 저장", use_container_width=True):
                if deepseek_api_key:
                    config.app['llm_provider'] = 'deepseek'
                    config.app['deepseek_api_key'] = deepseek_api_key
                    config.app['deepseek_model_name'] = 'deepseek-chat'
                    config.app['deepseek_base_url'] = 'https://api.deepseek.com'
                    config.save_config()
                    st.success("✅ DeepSeek 설정이 저장되었습니다!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ API 키를 입력해주세요!")
    
        # === 2단계: 영상 소스 설정 ===
        with st.container(border=True):
        status_icon = "✅" if setup_status['video_source_configured'] else "⚠️"
        st.markdown(f"### {status_icon} **2단계: 영상 소스 설정** (필수)")
        
        if setup_status['video_source_configured']:
            current_source = config.app.get('video_source', 'pexels')
            st.success(f"✅ **설정 완료**: {current_source.upper()} 영상 소스가 설정되어 있습니다.")
        else:
            st.warning("⚠️ **설정 필요**: 배경 영상을 가져올 소스 설정이 필요합니다.")
        
        st.markdown("""
        **영상 소스**는 AI가 생성한 대본에 맞는 배경 영상을 자동으로 찾아줍니다.
        
        **추천 순서:**
        1. **Pexels** (무료, 고품질, 상업적 이용 가능) ⭐
        2. **Pixabay** (무료, 다양한 콘텐츠)
        """)
        
        video_source = st.selectbox(
            "영상 소스 선택",
            options=["pexels", "pixabay"],
            index=["pexels", "pixabay"].index(config.app.get('video_source', 'pexels')),
            format_func=lambda x: {
                "pexels": "📹 Pexels (추천)",
                "pixabay": "🎨 Pixabay"
            }[x]
        )
        
        if video_source == "pexels":
            st.markdown("""
            #### 📹 Pexels 설정
            
            **장점:**
            - 완전 무료
            - 고품질 영상
            - 상업적 이용 가능
            - 저작권 걱정 없음
            
            **API 키 발급 방법:**
            1. [Pexels](https://www.pexels.com/api/) 접속
            2. 무료 계정 생성
            3. API 키 발급
            4. 생성된 키를 아래에 입력
            """)
            
            pexels_api_key = st.text_input(
                "Pexels API 키",
                value=config.app.get('pexels_api_keys', [''])[0] if config.app.get('pexels_api_keys') else '',
                type="password",
                placeholder="563492ad6f91700001000001...",
                help="Pexels에서 발급받은 API 키를 입력하세요"
            )
            
            # API 키 실시간 검증
            if pexels_api_key and pexels_api_key != (config.app.get('pexels_api_keys', [''])[0] if config.app.get('pexels_api_keys') else ''):
                with st.spinner("API 키 검증 중..."):
                    is_valid, message = validate_pexels_api_key(pexels_api_key)
                    if is_valid:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔍 API 키 테스트", use_container_width=True, key="pexels_test"):
                    if pexels_api_key:
                        with st.spinner("API 키 테스트 중..."):
                            is_valid, message = validate_pexels_api_key(pexels_api_key)
                            if is_valid:
                                st.success(f"✅ {message}")
                            else:
                                st.error(f"❌ {message}")
                    else:
                        st.error("❌ API 키를 입력해주세요!")
            
            with col2:
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
        
        elif video_source == "pixabay":
            st.markdown("""
            #### 🎨 Pixabay 설정
            
            **장점:**
            - 무료 사용 가능
            - 다양한 콘텐츠
            - 이미지와 영상 모두 제공
            
            **API 키 발급 방법:**
            1. [Pixabay](https://pixabay.com/api/docs/) 접속
            2. 계정 생성/로그인
            3. API 키 발급
            4. 생성된 키를 아래에 입력
            """)
            
            pixabay_api_key = st.text_input(
                "Pixabay API 키",
                value=config.app.get('pixabay_api_keys', [''])[0] if config.app.get('pixabay_api_keys') else '',
                type="password",
                placeholder="12345678-1234567890abcdef...",
                help="Pixabay에서 발급받은 API 키를 입력하세요"
            )
            
            if st.button("💾 Pixabay 설정 저장", use_container_width=True):
                if pixabay_api_key:
                    config.app['video_source'] = 'pixabay'
                    config.app['pixabay_api_keys'] = [pixabay_api_key]
                    config.save_config()
                    st.success("✅ Pixabay 설정이 저장되었습니다!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ API 키를 입력해주세요!")
    
        # === 3단계: 음성 합성 설정 ===
        with st.container(border=True):
        status_icon = "✅" if setup_status['tts_configured'] else "⚠️"
        st.markdown(f"### {status_icon} **3단계: 음성 합성 설정** (기본 완료)")
        
        st.success("✅ **설정 완료**: Microsoft Edge TTS가 기본으로 설정되어 있습니다.")
        
        st.markdown("""
        **음성 합성(TTS)**은 AI가 생성한 대본을 자연스러운 음성으로 변환합니다.
        
        **현재 설정:**
        - **Microsoft Edge TTS** (무료, 고품질 한국어 음성)
        - 추가 설정 불필요
        
        **고급 옵션:**
        - Azure Speech Service (유료, 더 많은 음성 옵션)
        - 고급 설정 탭에서 변경 가능
        """)
        
        # 음성 미리보기
        voice_name = config.ui.get('voice_name', 'ko-KR-InJoonNeural-Male')
        st.info(f"🎤 **현재 음성**: {voice_name}")
        
        if st.button("🔊 음성 미리듣기", use_container_width=True):
            st.audio("data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT", unsafe_allow_html=True)
    
        # === 4단계: YouTube 업로드 설정 ===
        with st.container(border=True):
        status_icon = "✅" if setup_status['youtube_configured'] else "⚠️"
        st.markdown(f"### {status_icon} **4단계: YouTube 업로드 설정** (선택사항)")
        
        if setup_status['youtube_configured']:
            st.success("✅ **설정 완료**: YouTube 업로드가 설정되어 있습니다.")
        else:
            st.info("ℹ️ **선택사항**: YouTube 자동 업로드를 원하시면 설정해주세요.")
        
        st.markdown("""
        **YouTube 업로드**를 설정하면 생성된 영상을 자동으로 YouTube에 업로드할 수 있습니다.
        
        **설정 방법:**
        1. Google Cloud Console에서 프로젝트 생성
        2. YouTube Data API v3 활성화
        3. OAuth 2.0 클라이언트 ID 생성
        4. client_secrets.json 파일 다운로드
        5. 아래에 파일 업로드
        """)
        
        # 자세한 가이드 표시
        with st.expander("📖 **상세 설정 가이드 보기**"):
            st.markdown("""
            ### 🔧 YouTube API 설정 상세 가이드
            
            #### 1단계: Google Cloud Console 설정
            1. [Google Cloud Console](https://console.cloud.google.com/) 접속
            2. 새 프로젝트 생성 또는 기존 프로젝트 선택
            3. "API 및 서비스" → "라이브러리" 이동
            4. "YouTube Data API v3" 검색 후 활성화
            
            #### 2단계: OAuth 2.0 클라이언트 ID 생성
            1. "API 및 서비스" → "사용자 인증 정보" 이동
            2. "+ 사용자 인증 정보 만들기" → "OAuth 클라이언트 ID" 선택
            3. 애플리케이션 유형: "데스크톱 애플리케이션" 선택
            4. 이름 입력 후 "만들기" 클릭
            
            #### 3단계: 클라이언트 보안 비밀 다운로드
            1. 생성된 OAuth 클라이언트 ID 옆의 다운로드 버튼 클릭
            2. JSON 파일 다운로드
            3. 파일명을 "client_secrets.json"으로 변경
            4. 아래에 업로드
            
            #### 4단계: OAuth 동의 화면 설정 (필요시)
            1. "OAuth 동의 화면" 메뉴 이동
            2. 사용자 유형: "외부" 선택
            3. 필수 정보 입력 후 저장
            """)
        
        # 파일 업로드
        uploaded_secrets = st.file_uploader(
            "client_secrets.json 파일 업로드",
            type=['json'],
            help="Google Cloud Console에서 다운로드한 OAuth 클라이언트 보안 비밀 파일을 업로드하세요"
        )
        
        if uploaded_secrets is not None:
            try:
                # JSON 파일 검증
                secrets_content = json.loads(uploaded_secrets.read())
                if 'installed' in secrets_content or 'web' in secrets_content:
                    # 파일 저장
                    with open('client_secrets.json', 'w', encoding='utf-8') as f:
                        json.dump(secrets_content, f, indent=2)
                    
                    st.success("✅ client_secrets.json 파일이 성공적으로 업로드되었습니다!")
                    st.info("💡 이제 '고급 설정' 탭에서 YouTube 채널 인증을 진행하세요.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ 올바른 client_secrets.json 파일이 아닙니다.")
            except json.JSONDecodeError:
                st.error("❌ JSON 파일 형식이 올바르지 않습니다.")
            except Exception as e:
                st.error(f"❌ 파일 업로드 중 오류가 발생했습니다: {str(e)}")
        
        # YouTube 업로드 건너뛰기 옵션
        if st.button("⏭️ YouTube 설정 나중에 하기", use_container_width=True):
            st.info("💡 YouTube 설정은 언제든지 '고급 설정' 탭에서 할 수 있습니다.")
    
        # === 설정 완료 및 다음 단계 ===
        st.markdown("---")
    
        if progress == 1.0:
        st.markdown("""
        ### 🎉 **축하합니다! 모든 설정이 완료되었습니다!**
        
        이제 다음 단계로 진행하세요:
        
        1. **🎬 영상 생성** 탭으로 이동
        2. 원하는 주제 입력
        3. **✨ 자동 생성** 버튼 클릭
        4. AI가 자동으로 영상을 생성합니다!
        """)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 **영상 생성 시작하기**", use_container_width=True, type="primary"):
                st.success("🎉 설정이 완료되었습니다!")
                st.info("👆 위의 **🎬 영상 생성** 탭을 클릭해서 영상을 만들어보세요!")
                
                # JavaScript로 탭 하이라이트 효과
                st.markdown("""
                <script>
                // 영상 생성 탭을 하이라이트
                setTimeout(function() {
                    const tabs = document.querySelectorAll('[data-baseweb="tab"]');
                    tabs.forEach(function(tab) {
                        if (tab.textContent.includes('🎬 영상 생성')) {
                            tab.style.animation = 'pulse 2s infinite';
                            tab.style.boxShadow = '0 0 20px rgba(102, 126, 234, 0.8)';
                        }
                    });
                }, 500);
                </script>
                <style>
                @keyframes pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                    100% { transform: scale(1); }
                }
                </style>
                """, unsafe_allow_html=True)
                
                st.balloons()
        else:
        st.markdown("""
        ### 📋 **다음 할 일**
        
        위의 ⚠️ 표시된 단계들을 완료해주세요:
        """)
        
        if not setup_status['llm_configured']:
            st.markdown("- ⚠️ **AI 언어 모델 설정** (필수)")
        if not setup_status['video_source_configured']:
            st.markdown("- ⚠️ **영상 소스 설정** (필수)")
        if not setup_status['youtube_configured']:
            st.markdown("- ℹ️ **YouTube 업로드 설정** (선택사항)")
        
        st.markdown("모든 필수 설정을 완료하면 영상 생성을 시작할 수 있습니다!")
    
        # === 문제 해결 가이드 ===
        st.markdown("---")
        with st.expander("🔧 **문제 해결 가이드**"):
        troubleshooting = get_troubleshooting_guide()
        
        for issue_key, issue_info in troubleshooting.items():
            st.markdown(f"#### ❓ {issue_info['title']}")
            for solution in issue_info['solutions']:
                st.markdown(f"   {solution}")
            st.markdown("")
    
        # === 추가 도움말 ===
        with st.expander("📞 **추가 도움이 필요하신가요?**"):
        st.markdown("""
        ### 🆘 지원 및 문의
        
        **📧 이메일 지원:**
        - 기술 문의: support@example.com
        - 구매 문의: sales@example.com
        
        **📚 추가 자료:**
        - [사용자 매뉴얼](https://docs.example.com)
        - [비디오 튜토리얼](https://youtube.com/example)
        - [FAQ](https://faq.example.com)
        
        **💬 커뮤니티:**
        - [Discord 채팅방](https://discord.gg/example)
        - [카카오톡 오픈채팅](https://open.kakao.com/example)
        
        **⏰ 지원 시간:**
        - 평일 09:00 - 18:00 (한국시간)
        - 주말 및 공휴일 제외
        """)
        
        st.info("💡 **빠른 답변을 위해** 오류 메시지나 스크린샷을 함께 보내주세요!")

# --- TAB 1: MAIN (Generate) ---
if not st.session_state.get("show_setup", False):
    with tab_main:
        # Hero Section
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0; margin-bottom: 1rem;">
            <h2 style="color: #667eea; margin-bottom: 0.5rem;">🚀 몇 초 만에 전문가급 영상을 생성하세요</h2>
            <p style="font-size: 1.1rem; color: #a0a0a0;">주제만 입력하면 AI가 대본, 음성, 영상, 자막을 자동으로 생성합니다</p>
        </div>
        """, unsafe_allow_html=True)
        # --- PREMIUM CONTENT PLANNING SECTION ---
        with st.container(border=True):
        st.markdown("### 📝 **콘텐츠 기획**")
        st.markdown("*AI가 당신의 아이디어를 완성된 영상으로 만들어드립니다*")
        
        # Subject Input with Premium Design
        st.markdown("#### 🎯 영상 주제")
        params.video_subject = st.text_input(
            "영상 주제",
            placeholder="예: 성공하는 사람들의 7가지 습관",
            value=st.session_state["video_subject"],
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
                import random
                random_topic = random.choice(inspiration_topics)
                st.session_state["video_subject"] = random_topic
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
                import random
                random_topic = random.choice(trend_topics)
                st.session_state["video_subject"] = random_topic
                st.rerun()
        
        with col_quick3:
            if st.button("✨ 자동 생성", use_container_width=True, type="primary"):
                if not params.video_subject:
                    st.error("먼저 영상 주제를 입력해주세요!")
                    st.stop()
                # Trigger auto generation (existing logic)
                st.session_state["trigger_auto_generate"] = True
                st.rerun()

        # Auto-generation trigger check
        if st.session_state.get("trigger_auto_generate"):
            st.session_state["trigger_auto_generate"] = False
            
            try:
                progress_container = st.container()
                with progress_container:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    import concurrent.futures
                    status_text.text("🤖 AI가 대본을 생성 중입니다...")
                    progress_bar.progress(10)
                    
                    script = ""
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            llm.generate_script,
                            video_subject=params.video_subject,
                            language="ko-KR",
                            paragraph_number=4
                        )
                        
                        # Animated progress
                        for i in range(50):
                            if future.done():
                                break
                            time.sleep(0.1)
                            current_p = min(10 + int(i * 0.8), 50)
                            progress_bar.progress(current_p)
                            
                        script = future.result()
                    
                    if not script or "실패했습니다" in script or "Error:" in script:
                        st.error(f"❌ 대본 생성 실패: {script}")
                        progress_container.empty()
                        st.stop()

                    status_text.text("🔍 대본 분석 및 키워드 추출 중...")
                    progress_bar.progress(60)
                    
                    terms = []
                    try:
                        logger.info("Starting keyword generation...")
                        terms = llm.generate_terms(
                            video_subject=params.video_subject,
                            video_script=script, 
                            amount=5
                        )
                        logger.info(f"Keywords generated: {terms}")
                    except Exception as e:
                        logger.error(f"Keyword generation failed: {e}")
                        terms = []
                    
                    # Ensure we have some keywords
                    if not terms:
                        logger.warning("No keywords generated, using enhanced fallback")
                        # Enhanced fallback based on subject analysis
                        subject_words = params.video_subject.lower().split()
                        fallback_terms = []
                        
                        # Try to extract meaningful English words from subject
                        for word in subject_words:
                            if word in ["성공", "success"]:
                                fallback_terms.extend(["success", "achievement", "business"])
                            elif word in ["건강", "health"]:
                                fallback_terms.extend(["health", "fitness", "wellness"])
                            elif word in ["돈", "money"]:
                                fallback_terms.extend(["money", "finance", "wealth"])
                        
                        # If still no terms, use generic ones
                        if not fallback_terms:
                            fallback_terms = ["lifestyle", "modern", "people", "business", "motivation"]
                        
                        terms = fallback_terms[:5]
                        logger.info(f"Using enhanced fallback terms: {terms}")
                    
                    # Translate terms to English for better search results
                    if terms:
                        logger.info(f"Generated terms: {terms}")
                        # Terms are already in English from the improved generate_terms function
                        st.session_state["video_terms"] = ", ".join(terms)
                    else:
                        terms = []
                        st.session_state["video_terms"] = ""

                    status_text.text("✅ 생성 완료!")
                    progress_bar.progress(100)
                    time.sleep(0.5)
                    
                    st.session_state["video_script"] = script
                    
                    progress_container.empty()
                    
                    # Show generated keywords immediately
                    if terms:
                        st.success("🎉 AI가 완벽한 대본과 키워드를 생성했습니다!")
                        st.markdown("**🔍 생성된 검색 키워드:**")
                        tags_html = ""
                        for keyword in terms:
                            tags_html += f'<span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 0.25rem 0.5rem; border-radius: 12px; margin: 0.25rem; display: inline-block; font-size: 0.8rem;">{keyword}</span>'
                        st.markdown(tags_html, unsafe_allow_html=True)
                    else:
                        st.success("🎉 AI가 대본을 생성했습니다!")
                        st.warning("⚠️ 키워드 생성에 실패했습니다. 수동으로 입력해 주세요.")
                    
                    st.rerun()

            except Exception as e:
                st.error(f"❌ 생성 중 오류 발생: {str(e)}")
        
        # Script Language (Hidden but set)
        params.video_language = "ko-KR"

        # Premium Script & Keywords Section
        st.markdown("---")
        st.markdown("#### ✍️ 대본 & 키워드 편집")
        
        col_script, col_terms = st.columns([0.6, 0.4])
        
        with col_script:
            st.markdown("**📝 영상 대본**")
            params.video_script = st.text_area(
                "영상 대본", 
                value=st.session_state["video_script"], 
                height=250,
                placeholder="AI가 생성한 대본이 여기에 표시됩니다.\n직접 수정하거나 완전히 새로 작성할 수도 있습니다.\n\n팁: 감정적이고 구체적인 표현을 사용하면 더 매력적인 영상이 됩니다.",
                label_visibility="collapsed",
                help="대본을 직접 수정할 수 있습니다. 문단별로 나누어 작성하면 더 자연스러운 영상이 생성됩니다."
            )
            
            # Script analysis with better layout
            if params.video_script:
                word_count = len(params.video_script.split())
                char_count = len(params.video_script)
                estimated_duration = word_count * 0.4  # Rough estimate: 0.4 seconds per word
                
                # Use single column layout to prevent truncation
                st.markdown("**📊 대본 분석**")
                st.write(f"• **단어 수**: {word_count}개")
                st.write(f"• **글자 수**: {char_count}자") 
                st.write(f"• **예상 길이**: {estimated_duration:.0f}초")
        
        with col_terms:
            st.markdown("**🏷️ 검색 키워드**")
            params.video_terms = st.text_area(
                "영상 키워드", 
                value=st.session_state["video_terms"],
                height=250,
                placeholder="success, motivation, lifestyle, tips, guide\n\n영어 키워드를 쉼표로 구분하여 입력하세요.\n좋은 키워드는 더 관련성 높은 영상 소재를 찾는데 도움이 됩니다.",
                label_visibility="collapsed",
                help="영상 소재 검색에 사용될 키워드입니다. 영어로 입력하면 더 다양한 소재를 찾을 수 있습니다."
            )
            
            # Keywords analysis
            if params.video_terms:
                keywords_list = [k.strip() for k in params.video_terms.split(',') if k.strip()]
                st.info(f"🔍 {len(keywords_list)}개의 키워드가 설정되었습니다")
                
                # Show keywords as tags
                if keywords_list:
                    st.markdown("**키워드 미리보기:**")
                    tags_html = ""
                    for keyword in keywords_list[:8]:  # Show max 8 keywords
                        tags_html += f'<span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 0.25rem 0.5rem; border-radius: 12px; margin: 0.25rem; display: inline-block; font-size: 0.8rem;">{keyword}</span>'
                    st.markdown(tags_html, unsafe_allow_html=True)

        # Check for any ongoing generation tasks
        if "generation_in_progress" not in st.session_state:
        st.session_state["generation_in_progress"] = False
    
        # Mobile reconnection helper
        if st.session_state.get("generation_in_progress", False):
        st.warning("⚠️ 영상 생성이 진행 중입니다. 연결이 끊어진 경우 새로고침하여 상태를 확인하세요.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 생성 상태 확인", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("❌ 생성 중단", use_container_width=True):
                st.session_state["generation_in_progress"] = False
                st.success("영상 생성이 중단되었습니다.")
                st.rerun()
    
        # Mobile-specific warnings and tips
        show_mobile_generation_tips()
    
        # Premium Quick Settings & Generation Section
        st.markdown("---")
    
        col_quick_settings, col_generation = st.columns([0.4, 0.6])
    
        with col_quick_settings:
        with st.container(border=True):
            st.markdown("### ⚡ **빠른 설정**")
            
            if st.button("✨ 쇼츠 최적화 적용", use_container_width=True, type="primary"):
                # Apply optimal settings for YouTube Shorts
                if config.app.get("pexels_api_keys"):
                    st.session_state["settings_video_source"] = 0
                elif config.app.get("pixabay_api_keys"):
                    st.session_state["settings_video_source"] = 1
                else:
                    st.session_state["settings_video_source"] = 2
                
                st.session_state["settings_video_aspect"] = 0  # Portrait
                st.session_state["settings_video_concat"] = 1  # Random
                st.session_state["settings_video_transition"] = 1  # Shuffle
                st.session_state["settings_clip_duration"] = 3
                st.session_state["settings_video_count"] = 1
                st.session_state["settings_voice_rate"] = 1.2
                st.session_state["settings_voice_volume"] = 1.0
                st.session_state["settings_bgm_type"] = 1
                st.session_state["settings_bgm_volume"] = 0.05
                st.session_state["settings_subtitle_enabled"] = True
                st.session_state["settings_subtitle_position"] = 3  # Custom position
                st.session_state["settings_font_color"] = "#FFFFFF"
                st.session_state["settings_stroke_color"] = "#000000"
                st.session_state["settings_font_size"] = 50
                st.session_state["settings_stroke_width"] = 3.0
                
                config.ui["font_size"] = 50
                config.ui["text_fore_color"] = "#FFFFFF"
                
                st.success("✅ 쇼츠 최적화 설정 완료!")
                st.info("📱 9:16 세로 비율, 빠른 템포, 큰 자막으로 설정되었습니다")
                time.sleep(1)
                st.rerun()
            
            if st.button("🎬 시네마틱 모드", use_container_width=True):
                # Apply cinematic settings
                st.session_state["settings_video_aspect"] = 1  # Landscape
                st.session_state["settings_video_transition"] = 2  # Fade In
                st.session_state["settings_clip_duration"] = 6
                st.session_state["settings_voice_rate"] = 0.9
                st.session_state["settings_bgm_volume"] = 0.08
                st.session_state["settings_font_size"] = 45
                
                st.success("🎭 시네마틱 모드 적용!")
                st.info("🎥 16:9 가로 비율, 느린 템포, 페이드 전환으로 설정되었습니다")
                time.sleep(1)
                st.rerun()
    
        with col_generation:
        with st.container(border=True):
            st.markdown("### 🚀 **영상 생성**")
            
            # Generation options
            col_gen_opt1, col_gen_opt2 = st.columns(2)
            with col_gen_opt1:
                generate_english_version = st.checkbox(
                    "🌍 글로벌 버전 추가", 
                    value=False, 
                    help="한국어 영상 생성 후, 영어 자막/성우가 적용된 글로벌 버전을 추가로 생성합니다."
                )
            with col_gen_opt2:
                auto_upload = st.checkbox(
                    "📺 자동 업로드", 
                    value=False,
                    key="yt_auto_upload",
                    help="영상 생성 완료 후 자동으로 YouTube에 업로드합니다."
                )
            
            # Main generation button
            start_button = st.button(
                "🎬 AI 영상 생성 시작", 
                use_container_width=True, 
                type="primary",
                help="모든 설정을 확인한 후 영상 생성을 시작합니다.",
                disabled=st.session_state.get("generation_in_progress", False)
            )
            
            # Mobile optimization notice
            if start_button:
                st.markdown("""
                <div style="background: rgba(0, 123, 255, 0.1); padding: 1rem; border-radius: 10px; margin: 1rem 0;">
                    <h4 style="color: #007bff; margin: 0 0 0.5rem 0;">📱 모바일 최적화 모드 활성화</h4>
                    <p style="margin: 0; color: #666;">
                        • 화면을 켜둔 상태로 유지해주세요<br>
                        • 다른 앱으로 전환하지 마세요<br>
                        • 진행 상황이 자동으로 저장됩니다
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            # Generation status container
            generation_status_container = st.empty()

        # Premium Timer Video Section
        with st.expander("⏱️ **타이머 영상 생성** - 명상, 운동, 집중용", expanded=False):
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); 
                    padding: 1rem; border-radius: 12px; margin-bottom: 1rem;">
            <p style="margin: 0; color: #a0a0a0;">
                🧘‍♀️ <strong>명상 타이머</strong> | 🏃‍♂️ <strong>운동 타이머</strong> | 📚 <strong>집중 타이머</strong><br>
                설정된 시간만큼 작동하는 전문적인 타이머 영상을 생성합니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Compact Timer Channel Authentication
        col_auth_timer, col_status_timer = st.columns(2)
        
        timer_token_file = os.path.join(root_dir, "token_timer.pickle")
        client_secrets_file = os.path.join(root_dir, "client_secrets.json")
        
        with col_auth_timer:
            if st.button("🔐 채널 인증", key="auth_timer_channel", use_container_width=True):
                if os.path.exists(client_secrets_file):
                    try:
                        if os.path.exists(timer_token_file):
                            os.remove(timer_token_file)
                        get_authenticated_service(client_secrets_file, timer_token_file)
                        st.success("✅ 인증 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 인증 실패: {e}")
                else:
                    st.error("❌ client_secrets.json 파일이 필요합니다.")
        
        with col_status_timer:
            if os.path.exists(timer_token_file):
                st.success("✅ 타이머 채널 인증됨")
            else:
                st.warning("⚠️ 인증 필요 (업로드 불가)")
        
        st.markdown("---")
        
        # Simple Timer Configuration (no nested columns)
        st.info("🎯 **빠른 타이머**: 명상, 운동, 공부용 타이머를 간편하게!")
        
        # Timer settings in a simple layout
        col_timer_left, col_timer_right = st.columns(2)
        
        with col_timer_left:
            st.markdown("**⏱️ 시간 & 옵션**")
            timer_duration = st.number_input(
                "타이머 시간 (분)", 
                min_value=1, 
                max_value=120, 
                value=5, 
                step=1, 
                key="timer_duration_input",
                help="1-120분"
            )
            
            fast_mode = st.checkbox("⚡ 고속 렌더링", value=True, help="720p/24fps")
            add_music = st.checkbox("🎵 배경음악", value=True, help="랜덤 배경음악")
        
        with col_timer_right:
            st.markdown("**🎨 스타일 & 정보**")
            timer_style = st.selectbox(
                "배경 스타일",
                ["⚫ 미니멀", "🌅 자연", "🎨 추상"],
                key="timer_style_select",
                help="배경 스타일"
            )
            
            st.caption(f"📏 예상 영상: {timer_duration}분")
            st.caption(f"⏰ 생성 시간: ~{timer_duration * 0.3:.1f}분")
        
        # Timer generation button (outside of columns)
        if st.button("⏱️ 타이머 영상 생성", use_container_width=True, key="timer_generate_btn", type="primary"):
            # Simple timer generation logic
            timer_seconds = timer_duration * 60
            
            task_id = str(uuid4())
            output_dir = os.path.join(root_dir, "storage", "tasks", task_id)
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"timer_video_{int(time.time())}.mp4")
            
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            try:
                status_text.info(f"🎬 {timer_duration}분 타이머 영상 생성 시작...")
                
                from app.services import video
                
                # Simple background selection
                bg_video_path = None
                if "자연" in timer_style:
                    bg_video_path = os.path.join(root_dir, "resource", "materials", "nature_bg.jpg")
                elif "추상" in timer_style:
                    bg_video_path = os.path.join(root_dir, "resource", "materials", "abstract_bg.jpg")
                
                # Background music
                bg_music_path = None
                if add_music:
                    song_dir = os.path.join(root_dir, "resource", "songs")
                    if os.path.exists(song_dir):
                        songs = [f for f in os.listdir(song_dir) if f.endswith('.mp3')]
                        if songs:
                            bg_music_path = os.path.join(song_dir, random.choice(songs))
                
                # Generate timer video
                progress_bar.progress(0.3)
                video.generate_timer_video(
                    duration_seconds=timer_seconds,
                    output_file=output_file,
                    bg_video_path=bg_video_path,
                    bg_music_path=bg_music_path,
                    fast_mode=fast_mode
                )
                
                progress_bar.progress(1.0)
                status_text.success(f"✅ {timer_duration}분 타이머 영상 생성 완료!")
                
            except Exception as e:
                logger.error(f"Timer generation failed: {e}")
                status_text.error(f"❌ 생성 실패: {str(e)}")
    
        # YouTube Settings Section
        with st.expander("📺 **YouTube 설정**", expanded=False):
        st.info("🚀 **자동 업로드**: 영상 생성 완료 후 YouTube에 자동 업로드")
    
        # Premium Video Results Section
        if "generated_video_files" in st.session_state and st.session_state["generated_video_files"]:
        st.markdown("---")
        st.markdown("### 🎥 **생성된 영상**")
        
        video_files = st.session_state["generated_video_files"]
        
        for i, video_path in enumerate(video_files):
            if os.path.exists(video_path):
                with st.container(border=True):
                    # Video info header
                    col_info, col_meta = st.columns([0.7, 0.3])
                    
                    with col_info:
                        file_name = os.path.basename(video_path)
                        file_size = os.path.getsize(video_path) / (1024*1024)  # MB
                        creation_time = os.path.getctime(video_path)
                        
                        st.markdown(f"#### 📹 {file_name}")
                        st.caption(f"크기: {file_size:.1f}MB | 생성: {time.strftime('%Y-%m-%d %H:%M', time.localtime(creation_time))}")
                    
                    with col_meta:
                        # Video type detection
                        if "timer_video_" in file_name:
                            st.markdown("🏷️ **타이머 영상**")
                        else:
                            st.markdown("🏷️ **AI 생성 영상**")
                    
                    # Video player (smaller size)
                    col_video, col_spacer = st.columns([0.4, 0.6])
                    
                    with col_video:
                        st.video(video_path, format="video/mp4")
                    
                    # Channel selector and controls in horizontal layout
                    st.markdown("#### 🎬 **영상 작업**")
                    
                    # Channel selector
                    channels = [("🏠 메인 채널", "default"), ("⏱️ 타이머 채널", "timer")]
                    default_ch_idx = 1 if "timer_video_" in file_name else 0
                    
                    selected_channel_index = st.selectbox(
                        "업로드 채널 선택",
                        options=range(len(channels)),
                        format_func=lambda x: channels[x][0],
                        index=default_ch_idx,
                        key=f"upload_channel_sel_{i}"
                    )
                    
                    # Action buttons in horizontal layout (3 columns)
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    
                    with col_btn1:
                        # Download button
                        try:
                            with open(video_path, "rb") as video_file:
                                video_bytes = video_file.read()
                            st.download_button(
                                label="📥 다운로드",
                                data=video_bytes,
                                file_name=file_name,
                                mime="video/mp4",
                                key=f"dl_btn_{i}",
                                use_container_width=True
                            )
                        except Exception:
                            st.button("📥 다운로드", disabled=True, use_container_width=True)
                    
                    with col_btn2:
                        # Play button
                        if st.button("▶️ 재생", key=f"play_btn_{i}", use_container_width=True):
                            try:
                                if os.name == 'nt':
                                    os.startfile(video_path)
                                else:
                                    import subprocess
                                    subprocess.call(('xdg-open', video_path))
                            except Exception:
                                st.error("재생할 수 없습니다.")
                    
                    with col_btn3:
                        # Upload button
                        if st.button("📺 업로드", key=f"upload_btn_{i}", use_container_width=True, type="primary"):
                            st.session_state[f"upload_requested_{i}"] = True
                    
                    # Upload progress container
                    upload_progress_container = st.empty()
                    
                    # Handle upload logic
                    if st.session_state.get(f"upload_requested_{i}"):
                        with upload_progress_container.container():
                                # Choose token file based on selected channel
                                timer_token_file = os.path.join(root_dir, "token_timer.pickle")
                                default_token_file = os.path.join(root_dir, "token.pickle")
                                ch_idx = st.session_state.get(f"upload_channel_sel_{i}", 0)
                                token_file = timer_token_file if ch_idx == 1 else default_token_file
                                
                                # Find client_secrets.json
                                client_secrets_file = os.path.join(root_dir, "client_secrets.json")
                                if not os.path.exists(client_secrets_file):
                                    alt_copy = os.path.join(root_dir, "client_secrets - 복사본.json")
                                    if os.path.exists(alt_copy):
                                        client_secrets_file = alt_copy
                                
                                if os.path.exists(token_file) and os.path.exists(client_secrets_file):
                                    try:
                                        upload_progress = st.progress(0)
                                        upload_status = st.empty()
                                        upload_status.info("📤 업로드 준비 중...")
                                        
                                        def update_progress(p):
                                            upload_progress.progress(p / 100)
                                            upload_status.info(f"📤 업로드 중... {p}%")
                                        
                                        youtube = get_authenticated_service(client_secrets_file, token_file)
                                        
                                        # Get metadata
                                        meta_file = os.path.join(os.path.dirname(video_path), "script.json")
                                        task_params = {}
                                        task_script = ""
                                        
                                        try:
                                            if os.path.exists(meta_file):
                                                with open(meta_file, "r", encoding="utf-8") as f:
                                                    meta = json.load(f)
                                                task_params = meta.get("params", {}) or {}
                                                task_script = meta.get("script", "") or ""
                                        except Exception:
                                            pass
                                        
                                        title_subject = task_params.get("video_subject", params.video_subject)
                                        title = f"{st.session_state.get('yt_title_prefix', '#Shorts')} {title_subject}"
                                        description = f"{title}\n\nGenerated by MoneyPrinterTurbo AI\nSubject: {title_subject}"
                                        
                                        # Generate keywords based on language
                                        task_language = task_params.get("video_language", params.video_language)
                                        if task_language == "en-US":
                                            # English version - use English tags
                                            base_terms = llm.generate_terms(title_subject, task_script or (params.video_script or ""), amount=12) or []
                                            keywords = ", ".join(base_terms + [str(title_subject).strip(), "shorts", "ai generated", "video", "content"])
                                        else:
                                            # Korean version - generate Korean tags based on script content
                                            try:
                                                korean_terms = llm.generate_korean_terms(title_subject, task_script or (params.video_script or ""), amount=15) or []
                                                # Only use script-based keywords, no generic tags
                                                keywords = ", ".join(korean_terms + [str(title_subject).strip()])
                                            except:
                                                # Fallback to subject-based tags only
                                                keywords = str(title_subject).strip()
                                        
                                        vid_id = upload_video(
                                            youtube, 
                                            video_path, 
                                            title=title[:100],
                                            description=description,
                                            category=st.session_state.get("yt_category", "22"),
                                            keywords=keywords,
                                            privacy_status=st.session_state.get("yt_privacy", "private"),
                                            progress_callback=update_progress
                                        )
                                        
                                        if vid_id:
                                            upload_progress.progress(1.0)
                                            upload_status.success("✅ 업로드 성공!")
                                            st.markdown(f"🎉 [영상 보러가기](https://youtu.be/{vid_id})")
                                            st.session_state[f"upload_requested_{i}"] = False
                                        else:
                                            upload_status.error("❌ 업로드 실패")
                                            st.session_state[f"upload_requested_{i}"] = False
                                            
                                    except Exception as e:
                                        error_info = handle_youtube_upload_error(e)
                                        display_youtube_error_guide(error_info)
                                        st.session_state[f"upload_requested_{i}"] = False
                                else:
                                    st.error("❌ 인증 필요 (설정에서 YouTube 인증을 완료해주세요)")
                                    st.session_state[f"upload_requested_{i}"] = False

        # --- TAB 3: ANALYTICS & MANAGEMENT ---
        with tab_analytics:
        st.markdown("### 📊 **영상 분석 & 관리**")
    
        col_stats, col_recent = st.columns([0.4, 0.6])
    
        with col_stats:
        with st.container(border=True):
            st.markdown("#### 📈 생성 통계")
            
            # Calculate stats from generated videos
            total_videos = len(st.session_state.get("generated_video_files", []))
            
            # Display metrics in single column to prevent truncation
            st.metric("영상", total_videos, delta=None)
            st.metric("성공률", "98.5%", delta="2.1%")
            st.metric("시간", "2.3분", delta="-0.5분")
            st.metric("용량", "1.2GB", delta="156MB")
    
        with col_recent:
        with st.container(border=True):
            st.markdown("#### 🕒 최근 생성 영상")
            
            if "generated_video_files" in st.session_state and st.session_state["generated_video_files"]:
                for i, video_path in enumerate(st.session_state["generated_video_files"][:3]):  # Show only recent 3
                    if os.path.exists(video_path):
                        col_thumb, col_info, col_actions = st.columns([0.2, 0.5, 0.3])
                        
                        with col_thumb:
                            st.markdown("🎬")  # Video thumbnail placeholder
                        
                        with col_info:
                            file_name = os.path.basename(video_path)
                            file_size = os.path.getsize(video_path) / (1024*1024)  # MB
                            st.markdown(f"**{file_name[:20]}...**")
                            st.caption(f"크기: {file_size:.1f}MB")
                        
                        with col_actions:
                            if st.button("▶️", key=f"play_recent_{i}", help="재생"):
                                try:
                                    if os.name == 'nt':
                                        os.startfile(video_path)
                                    else:
                                        import subprocess
                                        subprocess.call(('xdg-open', video_path))
                                except Exception:
                                    pass
            else:
                st.info("아직 생성된 영상이 없습니다.")
    
        # Advanced Management Section
        st.markdown("---")
    
        col_cleanup, col_export = st.columns(2)
    
        with col_cleanup:
        with st.container(border=True):
            st.markdown("#### 🧹 저장공간 관리")
            
            if st.button("🗑️ 임시 파일 정리", use_container_width=True):
                try:
                    temp_dir = os.path.join(root_dir, "storage", "temp")
                    if os.path.exists(temp_dir):
                        import shutil
                        shutil.rmtree(temp_dir)
                        os.makedirs(temp_dir, exist_ok=True)
                        st.success("임시 파일이 정리되었습니다!")
                except Exception as e:
                    st.error(f"정리 중 오류: {e}")
            
            if st.button("📁 작업 폴더 열기", use_container_width=True):
                try:
                    tasks_dir = os.path.join(root_dir, "storage", "tasks")
                    if os.name == 'nt':
                        os.startfile(tasks_dir)
                    else:
                        import subprocess
                        subprocess.call(('xdg-open', tasks_dir))
                except Exception:
                    st.error("폴더를 열 수 없습니다.")
    
        with col_export:
        with st.container(border=True):
            st.markdown("#### 📤 내보내기 & 백업")
            
            if st.button("💾 설정 백업", use_container_width=True):
                try:
                    import json
                    backup_data = {
                        "config": dict(config.app),
                        "ui_settings": dict(config.ui),
                        "timestamp": time.time()
                    }
                    backup_json = json.dumps(backup_data, indent=2, ensure_ascii=False)
                    st.download_button(
                        "📥 백업 파일 다운로드",
                        backup_json,
                        file_name=f"moneyprinter_backup_{int(time.time())}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"백업 생성 실패: {e}")
            
            uploaded_backup = st.file_uploader("설정 복원", type=["json"], key="backup_restore")
            if uploaded_backup:
                try:
                    import json
                    backup_data = json.load(uploaded_backup)
                    if "config" in backup_data:
                        config.app.update(backup_data["config"])
                        config.save_config()
                        st.success("설정이 복원되었습니다!")
                        st.rerun()
                except Exception as e:
                    st.error(f"복원 실패: {e}")

# --- TAB 2: SETTINGS (Enhanced) ---
with tab_settings:
    st.markdown("### ⚙️ **고급 설정 및 커스터마이징**")
    st.markdown("*전문가급 영상을 위한 세밀한 설정을 조정하세요*")
    
    # Settings organized in expandable sections
    with st.expander("🎬 **영상 소스 및 품질 설정**", expanded=True):
        col_source_quality, col_aspect_mode = st.columns(2)
        
        with col_source_quality:
            st.markdown("#### 📹 영상 소스")
            video_sources = [
                ("🌟 Pexels (추천)", "pexels"),
                ("🎨 Pixabay", "pixabay"),
                ("📁 로컬 파일", "local"),
                ("🎵 TikTok", "douyin"),
                ("📺 Bilibili", "bilibili"),
                ("📱 Xiaohongshu", "xiaohongshu"),
            ]

            default_source = "local"
            try:
                if config.app.get("pexels_api_keys"):
                    default_source = "pexels"
                elif config.app.get("pixabay_api_keys"):
                    default_source = "pixabay"
            except Exception:
                default_source = "local"
                
            saved_video_source_name = config.app.get("video_source", default_source)
            try:
                saved_video_source_index = [v[1] for v in video_sources].index(saved_video_source_name)
            except ValueError:
                saved_video_source_index = 0

            selected_index = st.selectbox(
                "영상 소스 선택",
                options=range(len(video_sources)),
                format_func=lambda x: video_sources[x][0],
                index=saved_video_source_index,
                key="settings_video_source",
                help="Pexels는 고품질 무료 영상을 제공합니다. API 키가 필요합니다."
            )
            params.video_source = video_sources[selected_index][1]
            config.app["video_source"] = params.video_source
            
            # Show API key status
            if params.video_source == "pexels":
                if config.app.get("pexels_api_keys"):
                    st.success(f"✅ Pexels API 키 {len(config.app['pexels_api_keys'])}개 설정됨")
                else:
                    st.warning("⚠️ Pexels API 키가 필요합니다")
            elif params.video_source == "pixabay":
                if config.app.get("pixabay_api_keys"):
                    st.success(f"✅ Pixabay API 키 {len(config.app['pixabay_api_keys'])}개 설정됨")
                else:
                    st.warning("⚠️ Pixabay API 키가 필요합니다")
        
        with col_aspect_mode:
            st.markdown("#### 📐 영상 비율 및 모드")
            video_aspect_ratios = [
                ("📱 세로 9:16 (쇼츠)", VideoAspect.portrait.value),
                ("🖥️ 가로 16:9 (유튜브)", VideoAspect.landscape.value),
                ("⬜ 정사각형 1:1 (인스타)", VideoAspect.square.value),
            ]
            selected_index = st.selectbox(
                "영상 비율",
                options=range(len(video_aspect_ratios)),
                format_func=lambda x: video_aspect_ratios[x][0],
                key="settings_video_aspect",
                help="쇼츠용은 9:16, 일반 유튜브용은 16:9를 선택하세요"
            )
            params.video_aspect = VideoAspect(video_aspect_ratios[selected_index][1])
            
            # Video processing modes
            col_concat, col_trans = st.columns(2)
            with col_concat:
                video_concat_modes = [
                    ("📋 순차 연결", "sequential"),
                    ("🎲 무작위 연결 (추천)", "random"),
                ]
                selected_index = st.selectbox(
                    "영상 연결 방식",
                    index=1,
                    options=range(len(video_concat_modes)),
                    format_func=lambda x: video_concat_modes[x][0],
                    key="settings_video_concat"
                )
                params.video_concat_mode = VideoConcatMode(video_concat_modes[selected_index][1])
                
            with col_trans:
                video_transition_modes = [
                    ("❌ 전환 없음", VideoTransitionMode.none.value),
                    ("🎭 무작위 전환", VideoTransitionMode.shuffle.value),
                    ("🌅 페이드 인", VideoTransitionMode.fade_in.value),
                    ("🌇 페이드 아웃", VideoTransitionMode.fade_out.value),
                    ("➡️ 슬라이드 인", VideoTransitionMode.slide_in.value),
                    ("⬅️ 슬라이드 아웃", VideoTransitionMode.slide_out.value),
                ]
                selected_index = st.selectbox(
                    "영상 전환 효과",
                    options=range(len(video_transition_modes)),
                    format_func=lambda x: video_transition_modes[x][0],
                    index=0,
                    key="settings_video_transition"
                )
                params.video_transition_mode = VideoTransitionMode(video_transition_modes[selected_index][1])

        # Local file upload section
        if params.video_source == "local":
            st.markdown("#### 📁 **로컬 파일 업로드**")
            st.info("💡 파일을 업로드하지 않으면 기본 배경으로 생성됩니다.")
            uploaded_files = st.file_uploader(
                "영상/이미지 파일 업로드",
                type=["mp4", "mov", "avi", "flv", "mkv", "jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key="settings_local_upload",
                help="여러 파일을 업로드하면 랜덤하게 사용됩니다."
            )
            
            if uploaded_files:
                st.success(f"✅ {len(uploaded_files)}개 파일이 업로드되었습니다")
        
        # Video generation parameters
        col_duration_count, col_quality = st.columns(2)
        with col_duration_count:
            st.markdown("#### ⏱️ 생성 설정")
            col_dur, col_count = st.columns(2)
            with col_dur:
                params.video_clip_duration = st.selectbox(
                    "클립 길이 (초)", 
                    options=[2, 3, 4, 5, 6, 7, 8, 9, 10], 
                    index=1,
                    key="settings_clip_duration",
                    help="짧을수록 빠른 템포, 길수록 안정적인 느낌"
                )
            with col_count:
                params.video_count = st.selectbox(
                    "생성 수량", 
                    options=[1, 2, 3, 4, 5], 
                    index=0,
                    key="settings_video_count",
                    help="여러 개 생성 시 다양한 버전을 얻을 수 있습니다"
                )
    with st.expander("🎵 **음성 및 오디오 설정**", expanded=True):
        col_tts_voice, col_audio_settings = st.columns(2)
        
        with col_tts_voice:
            st.markdown("#### 🗣️ TTS 음성 설정")
            
            # TTS Server Selection
            tts_servers = [
                ("🔵 Azure TTS V1", "azure-tts-v1"),
                ("🔵 Azure TTS V2", "azure-tts-v2"),
                ("🚀 SiliconFlow TTS", "siliconflow"),
                ("🤖 Google Gemini TTS", "gemini-tts"),
            ]

            saved_tts_server = config.ui.get("tts_server", "azure-tts-v1")
            saved_tts_server_index = 0
            for i, (_, server_value) in enumerate(tts_servers):
                if server_value == saved_tts_server:
                    saved_tts_server_index = i
                    break

            selected_tts_server_index = st.selectbox(
                "TTS 서버 선택",
                options=range(len(tts_servers)),
                format_func=lambda x: tts_servers[x][0],
                index=saved_tts_server_index,
                key="settings_tts_server",
                help="Azure TTS는 가장 자연스럽고, SiliconFlow는 빠릅니다."
            )
            selected_tts_server = tts_servers[selected_tts_server_index][1]
            config.ui["tts_server"] = selected_tts_server

            # Get voice list based on selected TTS server
            filtered_voices = []
            if selected_tts_server == "siliconflow":
                filtered_voices = voice.get_siliconflow_voices()
            elif selected_tts_server == "gemini-tts":
                filtered_voices = voice.get_gemini_voices()
            else:
                all_voices = voice.get_all_azure_voices(filter_locals=["ko-KR"])
                for v in all_voices:
                    if selected_tts_server == "azure-tts-v2":
                        if "V2" in v: filtered_voices.append(v)
                    else:
                        if "V2" not in v: filtered_voices.append(v)

            friendly_names = {
                v: v.replace("Female", "여성").replace("Male", "남성").replace("Neural", "").replace("ko-KR-", "")
                for v in filtered_voices
            }

            saved_voice_name = config.ui.get("voice_name", "")
            saved_voice_name_index = 0
            if saved_voice_name in friendly_names:
                saved_voice_name_index = list(friendly_names.keys()).index(saved_voice_name)

            if friendly_names:
                selected_friendly_name = st.selectbox(
                    "목소리 선택",
                    options=list(friendly_names.values()),
                    index=min(saved_voice_name_index, len(friendly_names) - 1) if friendly_names else 0,
                    key="settings_voice_name",
                    help="자연스러운 한국어 음성을 선택하세요"
                )
                voice_name = list(friendly_names.keys())[list(friendly_names.values()).index(selected_friendly_name)]
                params.voice_name = voice_name
                config.ui["voice_name"] = voice_name
            else:
                st.warning("⚠️ 사용 가능한 목소리가 없습니다.")
                params.voice_name = ""
                config.ui["voice_name"] = ""
            
            # Voice preview button
            if friendly_names and st.button("🔊 목소리 미리듣기", use_container_width=True, type="primary"):
                play_content = params.video_subject if params.video_subject else "안녕하세요, 목소리 테스트입니다. 이 음성이 마음에 드시나요?"
                with st.spinner("🎤 음성 생성 중..."):
                    temp_dir = utils.storage_dir("temp", create=True)
                    audio_file = os.path.join(temp_dir, f"tmp-voice-{str(uuid4())}.mp3")
                    try:
                        sub_maker = voice.tts(
                            text=play_content, 
                            voice_name=voice_name, 
                            voice_rate=params.voice_rate, 
                            voice_file=audio_file, 
                            voice_volume=params.voice_volume
                        )
                        if sub_maker and os.path.exists(audio_file):
                            st.audio(audio_file, format="audio/mp3")
                            os.remove(audio_file)
                        else:
                            st.error("음성 생성에 실패했습니다.")
                    except Exception as e:
                        st.error(f"음성 생성 오류: {e}")
        
        with col_audio_settings:
            st.markdown("#### 🎚️ 오디오 조정")
            
            col_vol, col_rate = st.columns(2)
            with col_vol:
                params.voice_volume = st.selectbox(
                    "🔊 음성 볼륨", 
                    options=[0.6, 0.8, 1.0, 1.2, 1.5, 2.0], 
                    index=2, 
                    key="settings_voice_volume",
                    help="1.0이 기본값입니다"
                )
            with col_rate:
                params.voice_rate = st.selectbox(
                    "⚡ 음성 속도", 
                    options=[0.8, 0.9, 1.0, 1.1, 1.2, 1.3], 
                    index=2, 
                    key="settings_voice_rate",
                    help="쇼츠용은 1.1~1.2 추천"
                )

            st.markdown("#### 🎵 배경음악 설정")
            bgm_options = [
                ("🚫 배경음악 없음", ""),
                ("🎲 무작위 선택 (추천)", "random"),
                ("📁 사용자 지정", "custom"),
            ]
            
            col_bgm, col_bgm_vol = st.columns(2)
            with col_bgm:
                selected_index = st.selectbox(
                    "배경음악 타입",
                    index=1,
                    options=range(len(bgm_options)),
                    format_func=lambda x: bgm_options[x][0],
                    key="settings_bgm_type"
                )
                params.bgm_type = bgm_options[selected_index][1]
            with col_bgm_vol:
                params.bgm_volume = st.selectbox(
                    "🎵 BGM 볼륨", 
                    options=[0.02, 0.05, 0.08, 0.1, 0.15, 0.2], 
                    index=1, 
                    key="settings_bgm_volume",
                    help="너무 크면 음성이 묻힐 수 있습니다"
                )

    # Premium BGM Manager (Separate expander to avoid nesting)
    with st.expander("🎵 **배경음악 라이브러리 관리**", expanded=False):
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(255, 187, 51, 0.1) 0%, rgba(255, 136, 0, 0.1) 100%); 
                    padding: 1rem; border-radius: 12px; margin-bottom: 1rem;">
            <p style="margin: 0; color: #a0a0a0;">
                💡 <strong>저작권 안전 팁:</strong> 유튜브 업로드 시 저작권 문제가 발생한다면, 
                <strong>유튜브 오디오 보관함</strong>에서 무료 음악을 다운로드하여 사용하세요.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        song_dir = utils.song_dir()
        existing_songs = glob.glob(os.path.join(song_dir, "*.mp3"))
        
        # Upload new music
        st.markdown("#### 📤 새 음악 업로드")
        uploaded_bgm = st.file_uploader(
            "MP3 파일 업로드", 
            type=["mp3"], 
            accept_multiple_files=True, 
            key="bgm_uploader",
            help="여러 파일을 한 번에 업로드할 수 있습니다"
        )
        
        if uploaded_bgm:
            progress_bar = st.progress(0)
            for i, music_file in enumerate(uploaded_bgm):
                save_path = os.path.join(song_dir, music_file.name)
                with open(save_path, "wb") as f:
                    f.write(music_file.getbuffer())
                progress_bar.progress((i + 1) / len(uploaded_bgm))
            
            st.success(f"✅ {len(uploaded_bgm)}개의 음악이 추가되었습니다!")
            time.sleep(1)
            st.rerun()

        # Music library management
        st.markdown("#### 🎵 음악 라이브러리")
        if existing_songs:
            st.info(f"📚 현재 저장된 음악: **{len(existing_songs)}개**")
            
            # Show music list in a scrollable container
            with st.container(height=300):
                for i, song_path in enumerate(existing_songs):
                    col_info, col_actions = st.columns([0.8, 0.2])
                    song_name = os.path.basename(song_path)
                    
                    with col_info:
                        file_size = os.path.getsize(song_path) / (1024*1024)  # MB
                        st.markdown(f"🎵 **{song_name}**")
                        st.caption(f"크기: {file_size:.1f}MB")
                    
                    with col_actions:
                        if st.button("🗑️", key=f"del_song_{i}", help="삭제", use_container_width=True):
                            try:
                                os.remove(song_path)
                                st.success(f"'{song_name}' 삭제됨")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"삭제 실패: {e}")
        else:
            st.warning("🎵 저장된 배경음악이 없습니다.")
            st.info("💡 음악을 업로드하거나 '배경음악 타입'을 '없음'으로 설정하세요.")

    with st.expander("🎨 **자막 및 스타일 설정**", expanded=True):
        col_subtitle_basic, col_subtitle_style = st.columns(2)
        
        with col_subtitle_basic:
            st.markdown("#### 📝 자막 기본 설정")
            
            col_enable, col_pos = st.columns(2)
            with col_enable:
                params.subtitle_enabled = st.checkbox(
                    "자막 활성화", 
                    value=True, 
                    key="settings_subtitle_enabled",
                    help="자막을 끄면 음성만 나옵니다"
                )
            
            with col_pos:
                subtitle_positions = [
                    ("⬆️ 상단", "top"),
                    ("🎯 중앙", "center"),
                    ("⬇️ 하단 (추천)", "bottom"),
                    ("📐 사용자 지정", "custom"),
                ]
                selected_index = st.selectbox(
                    "자막 위치",
                    index=3,  # Custom position as default
                    options=range(len(subtitle_positions)),
                    format_func=lambda x: subtitle_positions[x][0],
                    key="settings_subtitle_position",
                    help="사용자 지정(75%)이 쇼츠에 최적화되어 있습니다"
                )
                params.subtitle_position = subtitle_positions[selected_index][1]
            
            if params.subtitle_position == "custom":
                params.custom_position = st.slider(
                    "사용자 지정 위치 (%)", 
                    0.0, 
                    100.0, 
                    75.0, 
                    key="settings_custom_position",
                    help="0%는 최상단, 100%는 최하단 (75%가 쇼츠 최적화)"
                )
        
        with col_subtitle_style:
            st.markdown("#### 🎨 자막 스타일")
            
            col_color, col_size = st.columns(2)
            with col_color:
                saved_text_fore_color = config.ui.get("text_fore_color", "#FFFFFF")
                params.text_fore_color = st.color_picker(
                    "🎨 폰트 색상", 
                    saved_text_fore_color, 
                    key="settings_font_color",
                    help="흰색이 가장 가독성이 좋습니다"
                )
                config.ui["text_fore_color"] = params.text_fore_color
                
            with col_size:
                saved_font_size = config.ui.get("font_size", 50)
                params.font_size = st.slider(
                    "📏 폰트 크기", 
                    30, 
                    100, 
                    saved_font_size, 
                    key="settings_font_size",
                    help="쇼츠용은 50-60이 적당합니다"
                )
                config.ui["font_size"] = params.font_size

            col_stroke_color, col_stroke_width = st.columns(2)
            with col_stroke_color:
                params.stroke_color = st.color_picker(
                    "🖼️ 테두리 색상", 
                    "#000000", 
                    key="settings_stroke_color",
                    help="검은색 테두리가 가독성을 높입니다"
                )
            with col_stroke_width:
                params.stroke_width = st.slider(
                    "📐 테두리 두께", 
                    0.0, 
                    10.0, 
                    1.5, 
                    key="settings_stroke_width",
                    help="2-3 정도가 적당합니다"
                )
        
        # Font preview
        if params.subtitle_enabled:
            st.markdown("#### 👀 자막 미리보기")
            preview_text = params.video_subject if params.video_subject else "이것은 자막 미리보기입니다"
            
            # Calculate position based on subtitle_position setting
            position_style = ""
            if params.subtitle_position == "top":
                position_style = "top: 15%; transform: translateY(0%);"
            elif params.subtitle_position == "center":
                position_style = "top: 50%; transform: translateY(-50%);"
            elif params.subtitle_position == "bottom":
                position_style = "bottom: 15%; transform: translateY(0%);"
            elif params.subtitle_position == "custom":
                custom_pos = params.custom_position
                position_style = f"top: {custom_pos}%; transform: translateY(-50%);"
            else:
                position_style = "bottom: 15%; transform: translateY(0%);"  # default to bottom
            
            preview_style = f"""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 2rem;
                border-radius: 16px;
                position: relative;
                overflow: hidden;
                height: 300px;
            ">
                <div style="
                    position: absolute;
                    left: 50%;
                    transform: translateX(-50%);
                    {position_style}
                    color: {params.text_fore_color};
                    font-size: {params.font_size * 0.4}px;
                    font-weight: bold;
                    text-shadow: {params.stroke_width}px {params.stroke_width}px 0px {params.stroke_color},
                                -{params.stroke_width}px -{params.stroke_width}px 0px {params.stroke_color},
                                {params.stroke_width}px -{params.stroke_width}px 0px {params.stroke_color},
                                -{params.stroke_width}px {params.stroke_width}px 0px {params.stroke_color};
                    line-height: 1.2;
                    text-align: center;
                    white-space: nowrap;
                    max-width: 90%;
                ">
                    {preview_text}
                </div>
                <div style="
                    position: absolute;
                    bottom: 10px;
                    right: 15px;
                    color: rgba(255,255,255,0.7);
                    font-size: 12px;
                ">
                    미리보기 - {params.subtitle_position.upper()} 위치
                </div>
            </div>
            """
            st.markdown(preview_style, unsafe_allow_html=True)

    with st.expander("⚙️ **시스템 및 API 설정**", expanded=False):
        st.markdown("#### 🤖 AI 언어 모델 설정")
        
        col_llm_provider, col_llm_model = st.columns(2)
        
        with col_llm_provider:
            llm_providers = [
                "OpenAI", "Moonshot", "Azure", "Qwen", "DeepSeek", "ModelScope",
                "Gemini", "Ollama", "G4f", "OneAPI", "Cloudflare", "ERNIE", "Pollinations"
            ]
            saved_llm_provider = config.app.get("llm_provider", "pollinations").lower()
            try:
                saved_llm_provider_index = [p.lower() for p in llm_providers].index(saved_llm_provider)
            except ValueError:
                saved_llm_provider_index = 0

            llm_provider = st.selectbox(
                "🧠 LLM 제공자", 
                options=llm_providers, 
                index=saved_llm_provider_index,
                help="Pollinations는 무료, OpenAI/Gemini는 고품질입니다"
            )
            llm_provider = llm_provider.lower()
            config.app["llm_provider"] = llm_provider
        
        with col_llm_model:
            # Model name input
            llm_model_name = config.app.get(f"{llm_provider}_model_name", "")
            st_llm_model_name = st.text_input(
                "🎯 모델 이름 (선택사항)", 
                value=llm_model_name, 
                placeholder="예: gemini-2.5-flash, gpt-4o",
                help="비워두면 기본 모델을 사용합니다"
            )
            if st_llm_model_name: 
                config.app[f"{llm_provider}_model_name"] = st_llm_model_name
        
        # API Key input with multiple key support
        llm_api_key = config.app.get(f"{llm_provider}_api_key", "")
        st_llm_api_key = st.text_input(
            f"🔑 {llm_provider.upper()} API 키 (주)", 
            value=llm_api_key, 
            type="password",
            help="API 키는 안전하게 암호화되어 저장됩니다"
        )
        if st_llm_api_key: 
            config.app[f"{llm_provider}_api_key"] = st_llm_api_key
        
        # Additional API keys for quota management
        if llm_provider in ["gemini", "openai", "deepseek"]:
            st.markdown("---")
            st.markdown("**🔄 추가 API 키 (할당량 관리)**")
            st.info("💡 여러 API 키를 설정하면 할당량 초과 시 자동으로 다른 키로 전환됩니다")
            
            col_key2, col_key3 = st.columns(2)
            
            with col_key2:
                key_name_2 = f"{llm_provider}_api_key_2"
                current_key_2 = config.app.get(key_name_2, "")
                additional_key_2 = st.text_input(
                    f"🔑 API 키 #2", 
                    value=current_key_2, 
                    type="password",
                    help="백업 API 키 #2 (선택사항)"
                )
                if additional_key_2: 
                    config.app[key_name_2] = additional_key_2
            
            with col_key3:
                key_name_3 = f"{llm_provider}_api_key_3"
                current_key_3 = config.app.get(key_name_3, "")
                additional_key_3 = st.text_input(
                    f"🔑 API 키 #3", 
                    value=current_key_3, 
                    type="password",
                    help="백업 API 키 #3 (선택사항)"
                )
                if additional_key_3: 
                    config.app[key_name_3] = additional_key_3
        
        # API Key status
        if st_llm_api_key:
            masked_key = f"{st_llm_api_key[:8]}...{st_llm_api_key[-4:]}" if len(st_llm_api_key) > 12 else "설정됨"
            st.success(f"✅ API 키 설정됨: {masked_key}")
        else:
            if llm_provider not in ["pollinations", "g4f", "ollama"]:
                st.warning(f"⚠️ {llm_provider.upper()} API 키가 필요합니다")
        
        st.markdown("---")
        st.markdown("#### 🎬 영상 소재 API 설정")
        
        col_pexels, col_pixabay = st.columns(2)
        
        with col_pexels:
            st.markdown("**🌟 Pexels API**")
            new_pexels_key = st.text_input(
                "새 Pexels API 키", 
                key="new_pexels_key", 
                type="password",
                help="https://www.pexels.com/api/ 에서 무료로 발급받을 수 있습니다"
            )
            if st.button("➕ Pexels 키 추가", key="add_pexels", use_container_width=True):
                if new_pexels_key:
                    if "pexels_api_keys" not in config.app:
                        config.app["pexels_api_keys"] = []
                    config.app["pexels_api_keys"].append(new_pexels_key)
                    config.save_config()
                    st.success("✅ Pexels API 키 추가됨!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("API 키를 입력해주세요")
            
            # Show existing Pexels keys
            if config.app.get("pexels_api_keys"):
                st.success(f"✅ {len(config.app['pexels_api_keys'])}개의 Pexels 키 설정됨")
                st.markdown("**저장된 키 관리:**")
                keys_to_remove = []
                for i, key in enumerate(config.app["pexels_api_keys"]):
                    col_key, col_del = st.columns([0.8, 0.2])
                    with col_key:
                        masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else key
                        st.text(f"🔑 {masked_key}")
                    with col_del:
                        if st.button("🗑️", key=f"del_pex_{i}", help="삭제"):
                            keys_to_remove.append(i)
                
                if keys_to_remove:
                    for i in sorted(keys_to_remove, reverse=True):
                        config.app["pexels_api_keys"].pop(i)
                    config.save_config()
                    st.rerun()
            else:
                st.info("ℹ️ Pexels API 키가 없습니다")

        with col_pixabay:
            st.markdown("**🎨 Pixabay API**")
            new_pixabay_key = st.text_input(
                "새 Pixabay API 키", 
                key="new_pixabay_key", 
                type="password",
                help="https://pixabay.com/api/docs/ 에서 무료로 발급받을 수 있습니다"
            )
            if st.button("➕ Pixabay 키 추가", key="add_pixabay", use_container_width=True):
                if new_pixabay_key:
                    if "pixabay_api_keys" not in config.app:
                        config.app["pixabay_api_keys"] = []
                    config.app["pixabay_api_keys"].append(new_pixabay_key)
                    config.save_config()
                    st.success("✅ Pixabay API 키 추가됨!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("API 키를 입력해주세요")

            # Show existing Pixabay keys
            if config.app.get("pixabay_api_keys"):
                st.success(f"✅ {len(config.app['pixabay_api_keys'])}개의 Pixabay 키 설정됨")
                st.markdown("**저장된 키 관리:**")
                keys_to_remove = []
                for i, key in enumerate(config.app["pixabay_api_keys"]):
                    col_key, col_del = st.columns([0.8, 0.2])
                    with col_key:
                        masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else key
                        st.text(f"🔑 {masked_key}")
                    with col_del:
                        if st.button("🗑️", key=f"del_pix_{i}", help="삭제"):
                            keys_to_remove.append(i)
                
                if keys_to_remove:
                    for i in sorted(keys_to_remove, reverse=True):
                        config.app["pixabay_api_keys"].pop(i)
                    config.save_config()
                    st.rerun()
            else:
                st.info("ℹ️ Pixabay API 키가 없습니다")

    with st.expander("📺 **YouTube 업로드 설정**", expanded=False):
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(255, 0, 0, 0.1) 0%, rgba(255, 69, 0, 0.1) 100%); 
                    padding: 1rem; border-radius: 12px; margin-bottom: 1rem;">
            <p style="margin: 0; color: #a0a0a0;">
                📋 <strong>준비사항:</strong> Google Cloud Platform에서 발급받은 
                <strong style="color: #000000; background: #f0f0f0; padding: 2px 6px; border-radius: 4px;">client_secrets.json</strong> 파일이 필요합니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col_upload_setup, col_upload_settings = st.columns(2)
        
        with col_upload_setup:
            st.markdown("#### 🔐 인증 설정")
            
            # 1. Credentials File Upload
            client_secrets_file = os.path.join(root_dir, "client_secrets.json")
            uploaded_secrets = st.file_uploader(
                "📄 client_secrets.json 업로드", 
                type=["json"], 
                key="youtube_secrets",
                help="Google Cloud Console에서 다운로드한 OAuth 2.0 인증 파일"
            )
            
            if uploaded_secrets:
                with open(client_secrets_file, "wb") as f:
                    f.write(uploaded_secrets.getbuffer())
                st.success("✅ 인증 파일 업로드 완료!")
                time.sleep(1)
                st.rerun()
            
            # Show current status
            if os.path.exists(client_secrets_file):
                st.success("✅ client_secrets.json 파일 존재")
            else:
                st.warning("⚠️ client_secrets.json 파일이 필요합니다")
            
            # 2. Authentication buttons
            col_auth1, col_auth2 = st.columns(2)
            
            with col_auth1:
                if st.button("🏠 메인 채널 인증", key="auth_main_youtube", use_container_width=True):
                    if os.path.exists(client_secrets_file):
                        try:
                            token_file = os.path.join(root_dir, "token.pickle")
                            if os.path.exists(token_file):
                                os.remove(token_file)
                            get_authenticated_service(client_secrets_file, token_file)
                            st.success("✅ 메인 채널 인증 완료!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 인증 실패: {e}")
                    else:
                        st.error("❌ client_secrets.json 파일을 먼저 업로드하세요")
            
            with col_auth2:
                if st.button("⏱️ 타이머 채널 인증", key="auth_timer_youtube", use_container_width=True):
                    if os.path.exists(client_secrets_file):
                        try:
                            timer_token_file = os.path.join(root_dir, "token_timer.pickle")
                            if os.path.exists(timer_token_file):
                                os.remove(timer_token_file)
                            get_authenticated_service(client_secrets_file, timer_token_file)
                            st.success("✅ 타이머 채널 인증 완료!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 인증 실패: {e}")
                    else:
                        st.error("❌ client_secrets.json 파일을 먼저 업로드하세요")
            
            # Authentication status
            token_file = os.path.join(root_dir, "token.pickle")
            timer_token_file = os.path.join(root_dir, "token_timer.pickle")
            
            col_status1, col_status2 = st.columns(2)
            with col_status1:
                if os.path.exists(token_file):
                    st.success("✅ 메인 채널 인증됨")
                else:
                    st.error("❌ 메인 채널 미인증")
            
            with col_status2:
                if os.path.exists(timer_token_file):
                    st.success("✅ 타이머 채널 인증됨")
                else:
                    st.error("❌ 타이머 채널 미인증")
        
        with col_upload_settings:
            st.markdown("#### ⚙️ 업로드 설정")
            
            # Upload settings
            timer_auto_upload = st.checkbox(
                "🚀 타이머 영상 생성 후 자동 업로드", 
                value=False, 
                key="timer_auto_upload",
                help="체크하면 타이머 영상 생성 완료 즉시 YouTube에 자동 업로드됩니다"
            )
            
            yt_title_prefix = st.text_input(
                "📝 제목 접두사", 
                value="#Shorts", 
                key="yt_title_prefix",
                help="모든 영상 제목 앞에 붙을 텍스트"
            )
            
            col_privacy, col_category = st.columns(2)
            with col_privacy:
                yt_privacy = st.selectbox(
                    "🔒 공개 설정", 
                    ["private", "unlisted", "public"], 
                    index=0, 
                    key="yt_privacy",
                    help="private: 비공개, unlisted: 링크만, public: 전체공개"
                )
            
            with col_category:
                yt_category = st.text_input(
                    "📂 카테고리 ID", 
                    value="22", 
                    key="yt_category",
                    help="22: 인물/블로그, 24: 엔터테인먼트, 26: 하우투/스타일"
                )
            
            # Upload status summary
            is_ready_to_upload = (
                os.path.exists(client_secrets_file) and 
                (os.path.exists(token_file) or os.path.exists(timer_token_file))
            )
            
            if is_ready_to_upload:
                st.success("🎉 YouTube 업로드 준비 완료!")
            else:
                st.warning("⚠️ 업로드 기능을 사용하려면 인증을 완료해주세요")



# Premium Generation Logic
if start_button:
    st.session_state["generation_in_progress"] = True
    
    # Mobile-friendly progress tracking
    st.session_state["generation_start_time"] = time.time()
    st.session_state["generation_task_id"] = str(uuid4())
    
    task_id = st.session_state["generation_task_id"]
    
    # Mobile optimization: Add keep-alive mechanism
    st.markdown("""
    <script>
    // Keep mobile connection alive during generation
    let keepAliveInterval;
    function startKeepAlive() {
        keepAliveInterval = setInterval(() => {
            // Send a small request to keep connection alive
            fetch(window.location.href, {method: 'HEAD'}).catch(() => {});
        }, 30000); // Every 30 seconds
    }
    
    function stopKeepAlive() {
        if (keepAliveInterval) {
            clearInterval(keepAliveInterval);
        }
    }
    
    // Start keep-alive
    startKeepAlive();
    
    // Stop keep-alive when page unloads
    window.addEventListener('beforeunload', stopKeepAlive);
    </script>
    """, unsafe_allow_html=True)
    
    # Validation with premium error messages
    if not params.video_subject and not params.video_script:
        st.error("❌ **영상 주제 또는 대본이 필요합니다**")
        st.info("💡 위의 '영상 주제' 입력란에 내용을 입력하거나 '✨ 자동 생성' 버튼을 클릭하세요")
        st.session_state["generation_in_progress"] = False
        st.stop()

    # BGM Validation with premium styling
    if params.bgm_type == "random":
        song_dir = utils.song_dir()
        if not glob.glob(os.path.join(song_dir, "*.mp3")):
            st.error("❌ **배경음악 파일이 없습니다**")
            st.info("💡 '고급 설정' → '음성 및 오디오 설정' → '배경음악 라이브러리 관리'에서 MP3 파일을 업로드하거나, 배경음악을 '없음'으로 변경하세요")
            st.stop()

    # Video Source Validation with auto-correction
    original_source = params.video_source
    if params.video_source == "local":
        if not uploaded_files:
            if config.app.get("pexels_api_keys"):
                st.warning("⚠️ **로컬 파일이 없어 Pexels로 자동 전환합니다**")
                params.video_source = "pexels"
            elif config.app.get("pixabay_api_keys"):
                st.warning("⚠️ **로컬 파일이 없어 Pixabay로 자동 전환합니다**")
                params.video_source = "pixabay"
            else:
                st.error("❌ **영상 소재가 필요합니다**")
                st.info("💡 '고급 설정'에서 로컬 파일을 업로드하거나, Pexels/Pixabay API 키를 설정하세요")
                st.stop()
                
    if params.video_source == "pexels":
        if not config.app.get("pexels_api_keys"):
            if config.app.get("pixabay_api_keys"):
                st.warning("⚠️ **Pexels 키가 없어 Pixabay로 자동 전환합니다**")
                params.video_source = "pixabay"
            else:
                st.error("❌ **Pexels API 키가 필요합니다**")
                st.info("💡 '고급 설정' → '시스템 및 API 설정'에서 Pexels API 키를 추가하세요")
                st.stop()
                
    if params.video_source == "pixabay":
        if not config.app.get("pixabay_api_keys"):
            if config.app.get("pexels_api_keys"):
                st.warning("⚠️ **Pixabay 키가 없어 Pexels로 자동 전환합니다**")
                params.video_source = "pexels"
            else:
                st.error("❌ **Pixabay API 키가 필요합니다**")
                st.info("💡 '고급 설정' → '시스템 및 API 설정'에서 Pixabay API 키를 추가하세요")
                st.stop()

    # Handle local file uploads
    if params.video_source == "local" and uploaded_files:
        local_videos_dir = utils.storage_dir("local_videos", create=True)
        for file in uploaded_files:
            file_path = os.path.join(local_videos_dir, f"{file.file_id}_{file.name}")
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
                m = MaterialInfo()
                m.provider = "local"
                m.url = file_path
                if not params.video_materials:
                    params.video_materials = []
                params.video_materials.append(m)

    # Prepare generation tasks
    tasks_to_run = []
    
    # Task 1: Korean (Original)
    tasks_to_run.append({
        "label": "🇰🇷 한국어 버전",
        "params": params.copy(),
        "icon": "🎬"
    })
    
    # Task 2: English (Optional)
    if generate_english_version:
        with st.spinner("🌍 글로벌 버전 준비 중... (대본 번역)"):
            try:
                english_script = llm.translate_to_english(params.video_script)
                if english_script and english_script != params.video_script and "Error" not in english_script:
                    eng_params = params.copy()
                    eng_params.video_script = english_script
                    eng_subject = llm.translate_to_english(params.video_subject)
                    if not eng_subject or eng_subject == params.video_subject or re.search("[가-힣]", str(eng_subject)):
                        try:
                            terms_en = llm.generate_terms(video_subject=params.video_subject, video_script=english_script, amount=5) or []
                            if terms_en:
                                eng_subject = " · ".join([t for t in terms_en[:3] if t])
                        except Exception:
                            pass
                    eng_params.video_subject = eng_subject or params.video_subject
                    eng_params.voice_name = "en-US-AndrewNeural"
                    eng_params.video_language = "en-US"
                    
                    # Ensure subtitle settings are preserved for English version
                    eng_params.subtitle_enabled = params.subtitle_enabled
                    eng_params.subtitle_position = params.subtitle_position
                    eng_params.custom_position = params.custom_position
                    eng_params.font_size = params.font_size
                    eng_params.text_fore_color = params.text_fore_color
                    eng_params.stroke_color = params.stroke_color
                    eng_params.stroke_width = params.stroke_width
                    
                    tasks_to_run.append({
                        "label": "🌍 글로벌 버전",
                        "params": eng_params,
                        "icon": "🌎"
                    })
                else:
                    st.warning("⚠️ 영어 대본 번역에 실패하여 글로벌 버전 생성을 건너뜁니다")
            except Exception as e:
                st.error(f"❌ 글로벌 버전 준비 실패: {e}")

    final_video_files = []

    # Premium Generation UI with mobile optimization
    with generation_status_container:
        st.markdown("### 🚀 **AI 영상 생성 진행중**")
        
        # Mobile-friendly progress tracking
        if len(tasks_to_run) > 0:
            st.info("📱 **모바일 사용자 안내**: 영상 생성 중에는 브라우저 탭을 열어두세요. 화면을 끄거나 다른 앱을 사용해도 됩니다.")
        
        for i, task in enumerate(tasks_to_run):
            task_label = task["label"]
            task_params = task["params"]
            task_icon = task["icon"]
            
            # Task header
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
                padding: 1rem;
                border-radius: 12px;
                margin: 1rem 0;
                border-left: 4px solid #667eea;
            ">
                <h4 style="margin: 0; color: #667eea;">{task_icon} {task_label} 생성 중...</h4>
            </div>
            """, unsafe_allow_html=True)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            task_id = str(uuid4())
            
            status_text.info(f"🎬 작업 시작... (ID: {task_id[:8]})")
            
            try:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(tm.start, task_id=task_id, params=task_params)
                    
                    while not future.done():
                        task_info = sm.state.get_task(task_id)
                        if task_info:
                            progress = task_info.get("progress", 0)
                            state = task_info.get("state", const.TASK_STATE_PROCESSING)
                            task_msg = task_info.get("message", "")
                            
                            progress_normalized = min(int(progress) / 100, 1.0)
                            progress_bar.progress(progress_normalized)
                            
                            if state == const.TASK_STATE_PROCESSING:
                                status_text.info(f"🎬 {task_msg} ({int(progress)}%)" if task_msg else f"처리 중... {int(progress)}%")
                            elif state == const.TASK_STATE_FAILED:
                                status_text.error(f"❌ 실패: {task_msg}")
                                break
                            elif state == const.TASK_STATE_COMPLETE:
                                status_text.success("✅ 완료!")
                                break
                        time.sleep(1)
                    
                    if future.done():
                        result = future.result()
                        if result and "videos" in result:
                            generated_videos = result["videos"]
                            final_video_files.extend(generated_videos)
                            status_text.success(f"🎉 {task_label} 생성 완료!")
                            
                            # Auto-upload if enabled
                            if st.session_state.get("yt_auto_upload"):
                                st.info("🔍 자동 업로드가 활성화되어 있습니다.")
                                token_file = os.path.join(root_dir, "token.pickle")
                                client_secrets_file = os.path.join(root_dir, "client_secrets.json")
                                
                                st.info(f"📁 토큰 파일 확인: {os.path.exists(token_file)}")
                                st.info(f"📁 클라이언트 시크릿 파일 확인: {os.path.exists(client_secrets_file)}")
                                
                                if os.path.exists(token_file) and os.path.exists(client_secrets_file):
                                    for video_path in generated_videos:
                                        if os.path.exists(video_path):
                                            status_text.info(f"📺 YouTube 업로드 시작: {os.path.basename(video_path)}")
                                            try:
                                                youtube = get_authenticated_service(client_secrets_file, token_file)
                                                title_subject = task_params.video_subject
                                                title = f"{st.session_state.get('yt_title_prefix', '#Shorts')} {title_subject}"
                                                description = f"Generated by MoneyPrinterTurbo AI\n\nSubject: {title_subject}"
                                                
                                                terms = llm.generate_terms(task_params.video_subject, task_params.video_script or "", amount=12) or []
                                                
                                                # Generate language-specific tags
                                                if task_params.video_language == "en-US":
                                                    # English version - use English tags
                                                    base_tags = ["shorts", "ai generated", "video", "content", "viral"]
                                                    keywords = ", ".join(terms + [str(title_subject).strip()] + base_tags)
                                                else:
                                                    # Korean version - generate Korean tags
                                                    try:
                                                        korean_terms = llm.generate_korean_terms(task_params.video_subject, task_params.video_script or "", amount=8) or []
                                                        base_tags = ["쇼츠", "영상", "콘텐츠", "AI생성", "바이럴"]
                                                        keywords = ", ".join(korean_terms + [str(title_subject).strip()] + base_tags)
                                                    except:
                                                        # Fallback to basic Korean tags
                                                        keywords = f"{title_subject}, 쇼츠, 영상, 콘텐츠, AI생성, 바이럴"
                                                
                                                st.info(f"📝 업로드 제목: {title}")
                                                st.info(f"🏷️ 키워드: {keywords}")
                                                
                                                vid_id = upload_video(
                                                    youtube, 
                                                    video_path, 
                                                    title=title[:100],
                                                    description=description,
                                                    category=st.session_state.get("yt_category", "22"),
                                                    keywords=keywords,
                                                    privacy_status=st.session_state.get("yt_privacy", "private")
                                                )
                                                
                                                if vid_id:
                                                    video_url = f"https://youtube.com/watch?v={vid_id}"
                                                    status_text.success(f"🎉 업로드 성공! [영상 보기]({video_url})")
                                                else:
                                                    status_text.error("❌ 업로드 실패")
                                            except Exception as e:
                                                logger.error(f"Upload error: {e}")
                                                error_info = handle_youtube_upload_error(e)
                                                
                                                # 간단한 오류 표시 (자동 업로드용)
                                                if error_info['type'] == 'token_expired':
                                                    status_text.error("🔐 YouTube 인증 만료 - 설정에서 재인증 필요")
                                                elif error_info['type'] == 'quota_exceeded':
                                                    status_text.error("📊 YouTube API 할당량 초과 - 24시간 후 재시도")
                                                else:
                                                    status_text.error(f"❌ 업로드 오류: {error_info['message']}")
                                else:
                                    status_text.warning("⚠️ 자동 업로드가 활성화되어 있지만 YouTube 인증이 필요합니다")
                                    st.info("💡 '고급 설정' → 'YouTube 업로드 설정'에서 '🔐 메인 채널 인증' 버튼을 클릭하세요")
                            else:
                                st.info("ℹ️ 자동 업로드가 비활성화되어 있습니다.")
                        else:
                            status_text.error(f"❌ {task_label} 생성 실패")
                            
            except Exception as e:
                logger.error(f"Error during video generation: {e}")
                status_text.error(f"❌ 생성 오류: {e}")

    # Success handling
    if final_video_files:
        st.session_state["generated_video_files"] = final_video_files
        st.session_state["generation_in_progress"] = False  # Reset generation state
        
        # Success celebration
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #00c851 0%, #007e33 100%);
            padding: 2rem;
            border-radius: 16px;
            text-align: center;
            margin: 2rem 0;
            color: white;
        ">
            <h2 style="margin: 0; color: white;">🎉 모든 영상 생성 완료!</h2>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">
                총 {len(final_video_files)}개의 고품질 영상이 생성되었습니다
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.balloons()
        time.sleep(1)
        st.rerun()
    else:
        # Reset generation state even if no files were generated
        st.session_state["generation_in_progress"] = False
        st.error("❌ **영상 생성에 실패했습니다**")
        st.info("💡 설정을 확인하고 다시 시도해주세요. 문제가 지속되면 로그를 확인하세요.")

# Load existing videos on startup (Persistence Recovery)
if "generated_video_files" not in st.session_state or not st.session_state["generated_video_files"]:
    try:
        # Look for the most recent final-*.mp4 in storage/tasks
        task_dir_pattern = os.path.join(root_dir, "storage", "tasks", "*", "final-*.mp4")
        found_videos = glob.glob(task_dir_pattern)
        if found_videos:
            # Sort by modification time, newest first
            found_videos.sort(key=os.path.getmtime, reverse=True)
            # Take the latest one
            latest_video = found_videos[0]
            if os.path.exists(latest_video):
                st.session_state["generated_video_files"] = [latest_video]
    except Exception as e:
        logger.error(f"Failed to load recent videos: {e}")

# Save configuration
config.save_config()
