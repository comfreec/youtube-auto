import os
import glob
import platform
import sys
import time
import concurrent.futures
from uuid import uuid4

import streamlit as st
from loguru import logger

# Add the root directory of the project to the system path to allow importing modules from the project
root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)
    print("******** sys.path ********")
    print(sys.path)
    print("")


st.set_page_config(
    page_title="유튜브 쇼츠영상 자동생성기",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/FujiwaraChoki/MoneyPrinterTurbo",
        "Report a bug": "https://github.com/FujiwaraChoki/MoneyPrinterTurbo/issues",
        "About": "# 유튜브 쇼츠영상 자동생성기\n\nAI 기반 자동 영상 생성 도구입니다.",
    },
)


streamlit_style = """
<style>
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
    
    /* Base App Settings - Dark Luxury Theme */
    :root { color-scheme: dark; }
    .stApp { 
        background-color: #121212; 
        color: #E0E0E0; 
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif; 
    }
    
    /* Headings */
    h1 { 
        font-family: 'Pretendard'; 
        font-weight: 800; 
        font-size: 1.5rem !important; /* Reduced size */
        background: linear-gradient(90deg, #D4AF37 0%, #F0E68C 50%, #D4AF37 100%); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        letter-spacing: -0.5px; 
        padding-bottom: 10px; 
        text-align: center;
        text-shadow: 0px 2px 10px rgba(212, 175, 55, 0.2);
    }
    h2, h3, h4, h5, h6 { color: #F5F5F5 !important; font-weight: 600; letter-spacing: -0.5px; }
    
    /* Text Color Overrides */
    body, .stApp, .stMarkdown, p, label, span, div { color: #E0E0E0 !important; }
    .stTextInput label, .stTextArea label, .stSelectbox label, .stSlider label, .stCheckbox label, .stRadio label { 
        color: #B0B0B0 !important; 
        font-size: 0.9rem !important;
        font-weight: 500 !important;
    }
    
    /* Containers & Cards */
    div[data-testid="stVerticalBlockBorderWrapper"] { 
        background-color: #1E1E1E; 
        border-radius: 16px; 
        padding: 24px; 
        border: 1px solid #333333; 
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3); 
        margin-bottom: 16px;
    }
    
    /* Inputs & TextAreas (White High Contrast) */
    .stTextInput input, .stTextArea textarea { 
        background-color: #FFFFFF !important; 
        color: #000000 !important; 
        border: 1px solid #D4AF37 !important; 
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    /* Center align the Video Subject input (first text input usually) */
    .stTextInput input {
        text-align: center !important;
        font-size: 1.1rem !important;
    }
    
    /* Placeholders need to be visible on white */
    .stTextInput input::placeholder, .stTextArea textarea::placeholder { 
        color: #666666 !important; 
    }
    
    /* Focus states */
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #D4AF37 !important; 
        box-shadow: 0 0 0 1px #D4AF37 !important;
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Selectbox focus */
    .stSelectbox div[data-baseweb="select"]:focus-within { 
        border-color: #D4AF37 !important; 
        box-shadow: 0 0 0 1px #D4AF37 !important; 
    }
    
    /* SelectBox (Dropdown) - High Contrast (White Bg + Black Text) */
    .stSelectbox div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #D4AF37 !important;
        border-radius: 8px !important;
    }

    /* Explicitly target text inside selectbox */
    .stSelectbox div[data-baseweb="select"] div {
        color: #000000 !important;
    }
    
    /* Dropdowns & Options - High Contrast Mode (White Background + Black Text) */
    div[data-baseweb="popover"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D4AF37 !important;
    }
    
    div[data-baseweb="menu"] {
        background-color: #FFFFFF !important;
    }
    
    ul[data-baseweb="menu"] {
        background-color: #FFFFFF !important;
    }

    /* Option Styling - deeply targeted */
    li[data-baseweb="option"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* UNIVERSAL FORCE BLACK TEXT INSIDE POPOVER */
    div[data-baseweb="popover"] * {
        color: #000000 !important;
    }
    
    /* Hover & Selected States for Options */
    li[data-baseweb="option"]:hover, 
    li[data-baseweb="option"][aria-selected="true"] {
        background-color: #D4AF37 !important;
        color: #000000 !important;
        font-weight: bold !important;
    }
    
    /* Force text color on hover/selection */
    li[data-baseweb="option"]:hover *, 
    li[data-baseweb="option"][aria-selected="true"] * {
        color: #000000 !important;
        background-color: transparent !important;
    }
    
    /* Chevron Icon Color */
    .stSelectbox svg {
        fill: #D4AF37 !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #2D2D2D !important;
        color: #D4AF37 !important;
        border: 1px solid #D4AF37 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #D4AF37 !important;
        color: #121212 !important;
        box-shadow: 0 0 15px rgba(212, 175, 55, 0.3) !important;
    }
    
    /* Download Button Specific Styling - Dark Background, White Text */
    .stDownloadButton > button {
        background-color: #1a1a1a !important; /* Very dark background */
        color: #FFFFFF !important; /* White text for max visibility */
        border: 1px solid #555555 !important;
        font-weight: 700 !important;
    }
    .stDownloadButton > button:hover {
        background-color: #333333 !important;
        color: #FFFFFF !important;
        border-color: #FFFFFF !important;
        box-shadow: 0 0 10px rgba(255, 255, 255, 0.2) !important;
    }
    
    /* Primary Buttons (Gradient) */
    .stButton button[kind="primary"] { 
        background: linear-gradient(135deg, #D4AF37 0%, #C5A028 100%) !important; 
        border: none !important; 
        color: #000000 !important; 
        font-weight: 900 !important; 
        font-size: 1.2rem !important;
        padding: 1rem 3rem; 
        border-radius: 12px; 
        box-shadow: 0 4px 15px rgba(212, 175, 55, 0.4);
    }
    .stButton button[kind="primary"]:hover { 
        transform: translateY(-2px); 
        box-shadow: 0 6px 20px rgba(212, 175, 55, 0.6); 
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { 
        background-color: #0F0F0F; 
        border-right: 1px solid #333333; 
    }
    
    /* Input caret color */
    input, textarea { caret-color: #D4AF37 !important; }
    
    /* Progress Bar */
    .stProgress > div > div > div > div {
        background-color: #D4AF37 !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #2D2D2D !important;
        border-radius: 8px !important;
        color: #E0E0E0 !important;
    }
    
    /* Compact spacing */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    div[data-testid="column"] {
        gap: 1rem;
    }
    
    /* HIDE STREAMLIT HEADER (Deploy button, Menu, etc.) */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    /* Hide Footer */
    footer {
        display: none !important;
    }
    /* Hide Main Menu just in case */
    #MainMenu {
        visibility: hidden;
    }
    /* Hide Deploy Button specifically if header isn't enough */
    .stDeployButton {
        display: none;
    }
    
    /* AGGRESSIVE HEADER HIDE */
    header, [data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
        z-index: -1 !important;
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

# 타이틀만 표시 (언어 선택 컬럼 제거)
st.title("유튜브 쇼츠영상 자동생성기")

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


init_log()

locales = utils.load_locales(i18n_dir)


def tr(key):
    loc = locales.get(st.session_state["ui_language"], {})
    return loc.get("Translation", {}).get(key, key)


# Legacy settings removed - migrated to Tabs


llm_provider = config.app.get("llm_provider", "").lower()

# --- REFACTORED LAYOUT: TABBED INTERFACE ---
params = VideoParams(video_subject="")
uploaded_files = None

tab_main, tab_settings = st.tabs(["🎬 영상 생성 (Main)", "⚙️ 고급 설정 (Settings)"])

# --- TAB 1: MAIN (Generate) ---
with tab_main:
    # --- SECTION 1: CONTENT PLANNING ---
    with st.container(border=True):
        st.write("📝 **대본 및 기획**")
        
        # Subject Input & Auto-Generate Controls
        col_subject, col_auto = st.columns([0.7, 0.3])
        with col_subject:
            params.video_subject = st.text_input(
                "영상 주제",
                placeholder="예: 예수님의 명언 10가지",
                value=st.session_state["video_subject"],
                key="video_subject_input",
                label_visibility="collapsed"
            ).strip()
        
        with col_auto:
            # Script Language UI Removed - Forced to Korean
            params.video_language = "ko-KR"
            auto_script_enabled = st.checkbox(
                "실시간 자동 생성", value=config.ui.get("auto_script_enabled", True)
            )
            config.ui["auto_script_enabled"] = auto_script_enabled

        # Auto-generation Logic (Keep existing)
        if auto_script_enabled:
            subject_changed = (
                params.video_subject
                and params.video_subject != st.session_state.get("last_auto_subject", "")
            )
            now_ts = time.time()
            last_ts = st.session_state.get("last_auto_ts", 0.0)
            can_trigger = now_ts - last_ts > 1.0 and len(params.video_subject) >= 4
            if subject_changed and can_trigger:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("AI가 제목을 기반으로 대본을 생성 중입니다... (10%)")
                progress_bar.progress(10)
                
                script = llm.generate_script(
                    video_subject=params.video_subject,
                    language=params.video_language,
                    paragraph_number=4,
                )
                
                status_text.text("대본 생성 완료. 키워드를 생성 중입니다... (50%)")
                progress_bar.progress(50)
                
                terms = llm.generate_terms(params.video_subject, script)
                
                status_text.text("생성 완료! (100%)")
                progress_bar.progress(100)
                time.sleep(0.5)
                status_text.empty()
                progress_bar.empty()

                if isinstance(script, str) and "Error: " not in script:
                    st.session_state["video_script"] = script
                    if isinstance(terms, list):
                        st.session_state["video_terms"] = ", ".join(terms)
                    st.session_state["last_auto_subject"] = params.video_subject
                    st.session_state["last_auto_ts"] = now_ts

        # Manual Generate Button
        if st.button(
            "✨ 주제 기반 대본 및 키워드 생성", key="auto_generate_script", use_container_width=True, type="primary"
        ):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("AI가 영상 대본을 생성 중입니다... (10%)")
            progress_bar.progress(10)
            
            script = llm.generate_script(
                video_subject=params.video_subject,
                language=params.video_language,
                paragraph_number=4,
            )
            
            status_text.text("영상 대본 생성 완료. 키워드를 생성 중입니다... (50%)")
            progress_bar.progress(50)
            
            terms = llm.generate_terms(params.video_subject, script)
            
            status_text.text("생성 완료! (100%)")
            progress_bar.progress(100)
            time.sleep(0.5)
            status_text.empty()
            progress_bar.empty()

            if "Error: " in script:
                st.error(tr(script))
            elif "Error: " in terms:
                st.error(tr(terms))
            else:
                st.session_state["video_script"] = script
                st.session_state["video_terms"] = ", ".join(terms)

        # Script & Keywords (Side-by-side)
        col_script, col_terms = st.columns(2)
        with col_script:
            params.video_script = st.text_area(
                "영상 대본", 
                value=st.session_state["video_script"], 
                height=200,
                placeholder="AI가 생성한 대본이 여기에 표시됩니다. 직접 수정할 수도 있습니다."
            )
        with col_terms:
            params.video_terms = st.text_area(
                "영상 키워드 (영어, 쉼표 구분)", 
                value=st.session_state["video_terms"],
                height=200,
                placeholder="video, keywords, tags"
            )

    # OPTIMAL SETTINGS BUTTON (Moved to Main Tab)
    st.write("")
    if st.button("✨ 쇼츠 최적 세팅 자동 적용 (클릭)", use_container_width=True, type="primary"):
        # 1. Video Source (Pexels usually best for visuals)
        # Check if Pexels key exists
        if config.app.get("pexels_api_keys"):
            st.session_state["settings_video_source"] = 0 # Pexels
        elif config.app.get("pixabay_api_keys"):
            st.session_state["settings_video_source"] = 1 # Pixabay
        else:
            st.session_state["settings_video_source"] = 2 # Local (fallback)

        # 2. Aspect Ratio (Portrait 9:16 is crucial for Shorts)
        st.session_state["settings_video_aspect"] = 0 # 0 is Portrait

        # 3. Concat Mode (Random is usually better for variety)
        st.session_state["settings_video_concat"] = 1 # Random

        # 4. Transition (Shuffle)
        st.session_state["settings_video_transition"] = 1 # Shuffle

        # 5. Clip Duration (Fast paced for Shorts)
        st.session_state["settings_clip_duration"] = 3 # 3-5 seconds is good. Let's go with 3 for fast pace.

        # 6. Video Count
        st.session_state["settings_video_count"] = 1

        # 7. Voice Settings (Fast pace)
        st.session_state["settings_voice_rate"] = 1.2 # Slightly faster
        st.session_state["settings_voice_volume"] = 1.0

        # 8. BGM (Random)
        st.session_state["settings_bgm_type"] = 1 # Random
        st.session_state["settings_bgm_volume"] = 0.2

        # 9. Subtitle Settings (High visibility)
        st.session_state["settings_subtitle_enabled"] = True
        st.session_state["settings_subtitle_position"] = 2 # Bottom (standard for Shorts)
        st.session_state["settings_font_color"] = "#FFFFFF" # White
        st.session_state["settings_stroke_color"] = "#000000" # Black outline
        st.session_state["settings_font_size"] = 50 # Adjusted for better visibility
        st.session_state["settings_stroke_width"] = 3.0

        # Update Config objects too just in case
        config.ui["font_size"] = 50
        config.ui["text_fore_color"] = "#FFFFFF"

        st.toast("✅ 쇼츠 최적화 세팅이 적용되었습니다! (9:16, 빠른 템포, 큰 자막)")
        time.sleep(1)
        st.rerun()

    # START GENERATION BUTTON (Moved Up)
    st.write("")
    start_button = st.button("🚀 영상 생성 시작", use_container_width=True, type="primary")
    
    # Container for progress bar (placed immediately after the button)
    generation_status_container = st.empty()

    # --- Video Result ---
    if "generated_video_files" in st.session_state and st.session_state["generated_video_files"]:
        st.write("---")
        st.subheader("🎥 완성된 영상")
        video_files = st.session_state["generated_video_files"]
        
        for i, video_path in enumerate(video_files):
            if os.path.exists(video_path):
                # Video Player and Buttons Side-by-Side
                # Left: Video (approx 40% width), Right: Buttons (approx 60% width)
                # But since we want the video to be "halved" in size relative to full width, 
                # we can use a layout like [0.2, 0.3, 0.5] or similar.
                # Let's try [0.4, 0.2] relative to a centered container?
                # User said: "Video playing, space on right, align buttons there".
                
                # Create two columns: Video and Actions
                # The video is portrait (9:16), so it doesn't need much width.
                col_video, col_actions = st.columns([0.35, 0.65])
                
                with col_video:
                    st.video(video_path, format="video/mp4")
                
                with col_actions:
                    st.write("### 영상 작업")
                    # Stack buttons vertically
                    
                    try:
                        with open(video_path, "rb") as video_file:
                            video_bytes = video_file.read()
                        file_name = os.path.basename(video_path)
                        st.download_button(
                            label=f"📥 저장",
                            data=video_bytes,
                            file_name=file_name,
                            mime="video/mp4",
                            key=f"dl_btn_right_{i}",
                            use_container_width=True,
                            type="primary" 
                        )
                    except Exception:
                        pass
                        
                    st.write("") # Spacer
                    
                    if st.button("💻 재생", key=f"play_sys_right_{i}", use_container_width=True, type="primary"):
                        try:
                            if os.name == 'nt':
                                os.startfile(video_path)
                            else:
                                import subprocess
                                subprocess.call(('xdg-open', video_path))
                        except Exception:
                            pass

                    st.write("") # Spacer

                    # Upload Button
                    if st.button("📺 업로드", key=f"up_yt_right_{i}", use_container_width=True, type="primary"):
                            # Logic will be handled below (state check)
                            st.session_state[f"upload_requested_{i}"] = True

                # Handle Upload Logic (Full Width below if needed or inside container)
                if st.session_state.get(f"upload_requested_{i}"):
                    token_file = os.path.join(root_dir, "token.pickle")
                    client_secrets_file = os.path.join(root_dir, "client_secrets.json")
                    
                    if os.path.exists(token_file) and os.path.exists(client_secrets_file):
                        try:
                            # Progress Bar
                            upload_progress = st.progress(0)
                            upload_status = st.empty()
                            upload_status.info("업로드 준비 중...")
                            
                            def update_progress(p):
                                upload_progress.progress(p / 100)
                                upload_status.info(f"업로드 중... {p}%")

                            youtube = get_authenticated_service(client_secrets_file, token_file)
                            
                            title = f"{st.session_state.get('yt_title_prefix', '')} {params.video_subject}"
                            description = f"Generated by MoneyPrinterTurbo\nSubject: {params.video_subject}"
                            keywords = "shorts,ai"
                            
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
                                upload_status.success(f"업로드 성공!")
                                st.markdown(f"👉 [영상 보러가기](https://youtu.be/{vid_id})")
                                st.session_state[f"upload_requested_{i}"] = False # Reset
                            else:
                                upload_status.error("업로드 실패")
                                st.session_state[f"upload_requested_{i}"] = False # Reset
                        except Exception as e:
                            st.error(f"오류: {e}")
                            st.session_state[f"upload_requested_{i}"] = False # Reset
                    else:
                        st.error("인증 필요 (위 설정에서 인증해주세요)")
                        st.session_state[f"upload_requested_{i}"] = False # Reset

# --- TAB 2: SETTINGS (Moved everything else here) ---
with tab_settings:
    col_video_audio, col_style_sys = st.columns([1, 1])
    
    # Left Column: Video & Audio
    with col_video_audio:
        with st.container(border=True):
            st.write("🎬 **영상 설정**")
            
            video_sources = [
                ("Pexels", "pexels"),
                ("Pixabay", "pixabay"),
                ("로컬 파일", "local"),
                ("TikTok", "douyin"),
                ("Bilibili", "bilibili"),
                ("Xiaohongshu", "xiaohongshu"),
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

            col_src, col_ratio = st.columns(2)
            with col_src:
                selected_index = st.selectbox(
                    "영상 소스",
                    options=range(len(video_sources)),
                    format_func=lambda x: video_sources[x][0],
                    index=saved_video_source_index,
                    key="settings_video_source"
                )
                params.video_source = video_sources[selected_index][1]
                config.app["video_source"] = params.video_source

            with col_ratio:
                video_aspect_ratios = [
                    ("세로 9:16", VideoAspect.portrait.value),
                    ("가로 16:9", VideoAspect.landscape.value),
                ]
                selected_index = st.selectbox(
                    "영상 비율",
                    options=range(len(video_aspect_ratios)),
                    format_func=lambda x: video_aspect_ratios[x][0],
                    key="settings_video_aspect"
                )
                params.video_aspect = VideoAspect(video_aspect_ratios[selected_index][1])

            if params.video_source == "local":
                st.info("로컬 파일 모드: 파일을 업로드하지 않아도 기본 배경으로 생성됩니다. 업로드하면 해당 파일을 사용합니다.")
                uploaded_files = st.file_uploader(
                    "로컬 파일 업로드",
                    type=["mp4", "mov", "avi", "flv", "mkv", "jpg", "jpeg", "png"],
                    accept_multiple_files=True,
                    key="settings_local_upload"
                )
                
            col_concat, col_trans = st.columns(2)
            with col_concat:
                video_concat_modes = [
                    ("순차 연결", "sequential"),
                    ("무작위 연결 (권장)", "random"),
                ]
                selected_index = st.selectbox(
                    "영상 연결",
                    index=1,
                    options=range(len(video_concat_modes)),
                    format_func=lambda x: video_concat_modes[x][0],
                    key="settings_video_concat"
                )
                params.video_concat_mode = VideoConcatMode(video_concat_modes[selected_index][1])
                
            with col_trans:
                video_transition_modes = [
                    ("없음", VideoTransitionMode.none.value),
                    ("무작위", VideoTransitionMode.shuffle.value),
                    ("페이드 인", VideoTransitionMode.fade_in.value),
                    ("페이드 아웃", VideoTransitionMode.fade_out.value),
                    ("슬라이드 인", VideoTransitionMode.slide_in.value),
                    ("슬라이드 아웃", VideoTransitionMode.slide_out.value),
                ]
                selected_index = st.selectbox(
                    "영상 전환",
                    options=range(len(video_transition_modes)),
                    format_func=lambda x: video_transition_modes[x][0],
                    index=0,
                    key="settings_video_transition"
                )
                params.video_transition_mode = VideoTransitionMode(video_transition_modes[selected_index][1])

            col_dur, col_count = st.columns(2)
            with col_dur:
                params.video_clip_duration = st.selectbox(
                    "클립 길이 (초)", options=[2, 3, 4, 5, 6, 7, 8, 9, 10], index=1,
                    key="settings_clip_duration"
                )
            with col_count:
                params.video_count = st.selectbox(
                    "생성 수량", options=[1, 2, 3, 4, 5], index=0,
                    key="settings_video_count"
                )

    with col_style_sys:
        with st.container(border=True):
            st.write("🎵 **오디오 설정**")
            
            # TTS Server Selection
            tts_servers = [
                ("azure-tts-v1", "Azure TTS V1"),
                ("azure-tts-v2", "Azure TTS V2"),
                ("siliconflow", "SiliconFlow TTS"),
                ("gemini-tts", "Google Gemini TTS"),
            ]

            saved_tts_server = config.ui.get("tts_server", "azure-tts-v1")
            saved_tts_server_index = 0
            for i, (server_value, _) in enumerate(tts_servers):
                if server_value == saved_tts_server:
                    saved_tts_server_index = i
                    break

            col_tts, col_voice = st.columns(2)
            with col_tts:
                selected_tts_server_index = st.selectbox(
                    "TTS 서버",
                    options=range(len(tts_servers)),
                    format_func=lambda x: tts_servers[x][1],
                    index=saved_tts_server_index,
                    key="settings_tts_server"
                )
                selected_tts_server = tts_servers[selected_tts_server_index][0]
                config.ui["tts_server"] = selected_tts_server

            # Get voice list based on selected TTS server
            filtered_voices = []
            if selected_tts_server == "siliconflow":
                filtered_voices = voice.get_siliconflow_voices()
            elif selected_tts_server == "gemini-tts":
                filtered_voices = voice.get_gemini_voices()
            else:
                all_voices = voice.get_all_azure_voices(filter_locals=None)
                for v in all_voices:
                    if selected_tts_server == "azure-tts-v2":
                        if "V2" in v: filtered_voices.append(v)
                    else:
                        if "V2" not in v: filtered_voices.append(v)

            friendly_names = {
                v: v.replace("Female", tr("Female")).replace("Male", tr("Male")).replace("Neural", "")
                for v in filtered_voices
            }

            saved_voice_name = config.ui.get("voice_name", "")
            saved_voice_name_index = 0
            if saved_voice_name in friendly_names:
                saved_voice_name_index = list(friendly_names.keys()).index(saved_voice_name)
            else:
                for i, v in enumerate(filtered_voices):
                    if v.lower().startswith(st.session_state["ui_language"].lower()):
                        saved_voice_name_index = i
                        break
            if saved_voice_name_index >= len(friendly_names) and friendly_names:
                saved_voice_name_index = 0

            with col_voice:
                if friendly_names:
                    selected_friendly_name = st.selectbox(
                        "목소리 선택",
                        options=list(friendly_names.values()),
                        index=min(saved_voice_name_index, len(friendly_names) - 1) if friendly_names else 0,
                        key="settings_voice_name"
                    )
                    voice_name = list(friendly_names.keys())[list(friendly_names.values()).index(selected_friendly_name)]
                    params.voice_name = voice_name
                    config.ui["voice_name"] = voice_name
                else:
                    st.warning("사용 가능한 목소리가 없습니다.")
                    params.voice_name = ""
                    config.ui["voice_name"] = ""
            
            if friendly_names and st.button("🔊 목소리 미리듣기", use_container_width=True):
                 # (Keep existing logic, simplified for brevity in replacement if needed, but keeping logic is safer)
                 play_content = params.video_subject if params.video_subject else "안녕하세요, 목소리 테스트입니다."
                 with st.spinner("목소리 생성 중..."):
                    temp_dir = utils.storage_dir("temp", create=True)
                    audio_file = os.path.join(temp_dir, f"tmp-voice-{str(uuid4())}.mp3")
                    sub_maker = voice.tts(text=play_content, voice_name=voice_name, voice_rate=params.voice_rate, voice_file=audio_file, voice_volume=params.voice_volume)
                    if sub_maker and os.path.exists(audio_file):
                        st.audio(audio_file, format="audio/mp3")
                        os.remove(audio_file)

            col_vol, col_rate = st.columns(2)
            with col_vol:
                params.voice_volume = st.selectbox("음성 볼륨", options=[0.6, 0.8, 1.0, 1.2, 1.5, 2.0], index=2, key="settings_voice_volume")
            with col_rate:
                params.voice_rate = st.selectbox("음성 속도", options=[0.8, 0.9, 1.0, 1.1, 1.2, 1.3], index=2, key="settings_voice_rate")

            bgm_options = [
                ("없음", ""),
                ("무작위 (권장)", "random"),
                ("사용자 지정", "custom"),
            ]
            col_bgm, col_bgm_vol = st.columns(2)
            with col_bgm:
                selected_index = st.selectbox(
                    "배경 음악",
                    index=1,
                    options=range(len(bgm_options)),
                    format_func=lambda x: bgm_options[x][0],
                    key="settings_bgm_type"
                )
                params.bgm_type = bgm_options[selected_index][1]
            with col_bgm_vol:
                 params.bgm_volume = st.selectbox("BGM 볼륨", options=[0.1, 0.2, 0.3, 0.4, 0.5], index=1, key="settings_bgm_volume")

            # --- BGM Manager for Copyright Issues ---
            with st.expander("🎵 배경음악 관리 (저작권 해결)", expanded=False):
                st.info("💡 유튜브 업로드 시 저작권 문제가 발생한다면, 기본 음악을 삭제하고 **유튜브 오디오 보관함**에서 받은 안전한 음악을 업로드하세요.")
                
                song_dir = utils.song_dir()
                existing_songs = glob.glob(os.path.join(song_dir, "*.mp3"))
                
                # File Uploader
                uploaded_bgm = st.file_uploader("새로운 배경음악 업로드 (MP3)", type=["mp3"], accept_multiple_files=True, key="bgm_uploader")
                if uploaded_bgm:
                    for music_file in uploaded_bgm:
                        save_path = os.path.join(song_dir, music_file.name)
                        with open(save_path, "wb") as f:
                            f.write(music_file.getbuffer())
                    st.success(f"{len(uploaded_bgm)}개의 음악이 추가되었습니다!")
                    time.sleep(1)
                    st.rerun()

                # List & Delete
                if existing_songs:
                    st.write(f"현재 저장된 음악: {len(existing_songs)}개")
                    # Use a scrollable container if too many songs
                    bgm_container = st.container(height=300)
                    with bgm_container:
                        for i, song_path in enumerate(existing_songs):
                            col_name, col_del = st.columns([0.8, 0.2])
                            song_name = os.path.basename(song_path)
                            with col_name:
                                st.text(f"🎵 {song_name}")
                                # st.audio(song_path) # Too slow to load all
                            with col_del:
                                if st.button("삭제", key=f"del_song_{i}", use_container_width=True):
                                    try:
                                        os.remove(song_path)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"삭제 실패: {e}")
                else:
                    st.warning("저장된 배경음악이 없습니다. 음악을 업로드하거나 '배경 음악' 설정을 '없음'으로 변경하세요.")

    # Settings Tab Content
    with tab_settings:
        with st.expander("🎨 자막 및 스타일 설정", expanded=True):
            params.subtitle_enabled = st.checkbox("자막 활성화", value=True, key="settings_subtitle_enabled")
            
            col_font, col_pos = st.columns(2)
            with col_font:
                font_names = get_all_fonts()
                saved_font_name = config.ui.get("font_name", "MicrosoftYaHeiBold.ttc")
                try:
                    saved_font_name_index = font_names.index(saved_font_name)
                except ValueError:
                    saved_font_name_index = 0
                params.font_name = st.selectbox("폰트", font_names, index=saved_font_name_index, key="settings_font_name")
                config.ui["font_name"] = params.font_name
                
            with col_pos:
                subtitle_positions = [
                    ("상단", "top"),
                    ("중앙", "center"),
                    ("하단", "bottom"),
                    ("사용자 지정", "custom"),
                ]
                selected_index = st.selectbox(
                    "자막 위치",
                    index=2,
                    options=range(len(subtitle_positions)),
                    format_func=lambda x: subtitle_positions[x][0],
                    key="settings_subtitle_position"
                )
                params.subtitle_position = subtitle_positions[selected_index][1]

            col_color, col_size = st.columns(2)
            with col_color:
                saved_text_fore_color = config.ui.get("text_fore_color", "#FFFFFF")
                params.text_fore_color = st.color_picker("폰트 색상", saved_text_fore_color, key="settings_font_color")
                config.ui["text_fore_color"] = params.text_fore_color
            with col_size:
                saved_font_size = config.ui.get("font_size", 50)
                params.font_size = st.slider("폰트 크기", 30, 100, saved_font_size, key="settings_font_size")
                config.ui["font_size"] = params.font_size

            col_stroke_color, col_stroke_width = st.columns(2)
            with col_stroke_color:
                params.stroke_color = st.color_picker("테두리 색상", "#000000", key="settings_stroke_color")
            with col_stroke_width:
                params.stroke_width = st.slider("테두리 두께", 0.0, 10.0, 1.5, key="settings_stroke_width")

        with st.expander("⚙️ 시스템 및 API 설정", expanded=False):
            llm_providers = [
                "OpenAI", "Moonshot", "Azure", "Qwen", "DeepSeek", "ModelScope",
                "Gemini", "Ollama", "G4f", "OneAPI", "Cloudflare", "ERNIE", "Pollinations"
            ]
            saved_llm_provider = config.app.get("llm_provider", "pollinations").lower()
            try:
                saved_llm_provider_index = [p.lower() for p in llm_providers].index(saved_llm_provider)
            except ValueError:
                saved_llm_provider_index = 0

            llm_provider = st.selectbox("LLM 제공자", options=llm_providers, index=saved_llm_provider_index)
            llm_provider = llm_provider.lower()
            config.app["llm_provider"] = llm_provider
            
            # Simple API Key Input
            llm_api_key = config.app.get(f"{llm_provider}_api_key", "")
            st_llm_api_key = st.text_input("LLM API 키", value=llm_api_key, type="password")
            if st_llm_api_key: config.app[f"{llm_provider}_api_key"] = st_llm_api_key
            
            st.write("---")
            st.write("**Pexels/Pixabay API 키**")
            col_pex, col_pix = st.columns(2)
            with col_pex:
                new_key = st.text_input("Pexels 키 추가", key="new_pexels_key")
                if st.button("추가", key="add_pexels", use_container_width=True):
                    if new_key:
                        config.app["pexels_api_keys"].append(new_key)
                        config.save_config()
                        st.success("추가됨")
                        st.rerun()
                
                # Show existing keys
                if config.app.get("pexels_api_keys"):
                    st.caption("저장된 Pexels 키 (클릭하여 삭제):")
                    keys_to_remove = []
                    for i, key in enumerate(config.app["pexels_api_keys"]):
                        masked_key = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else key
                        if st.button(f"🗑️ {masked_key}", key=f"del_pex_{i}", use_container_width=True):
                            keys_to_remove.append(i)
                    
                    if keys_to_remove:
                        for i in sorted(keys_to_remove, reverse=True):
                            config.app["pexels_api_keys"].pop(i)
                        config.save_config()
                        st.rerun()

            with col_pix:
                new_key = st.text_input("Pixabay 키 추가", key="new_pixabay_key")
                if st.button("추가", key="add_pixabay", use_container_width=True):
                    if new_key:
                        config.app["pixabay_api_keys"].append(new_key)
                        config.save_config()
                        st.success("추가됨")
                        st.rerun()

                # Show existing keys
                if config.app.get("pixabay_api_keys"):
                    st.caption("저장된 Pixabay 키 (클릭하여 삭제):")
                    keys_to_remove = []
                    for i, key in enumerate(config.app["pixabay_api_keys"]):
                        masked_key = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else key
                        if st.button(f"🗑️ {masked_key}", key=f"del_pix_{i}", use_container_width=True):
                            keys_to_remove.append(i)
                    
                    if keys_to_remove:
                        for i in sorted(keys_to_remove, reverse=True):
                            config.app["pixabay_api_keys"].pop(i)
                        config.save_config()
                        st.rerun()

        with st.expander("📺 유튜브 업로드 설정", expanded=False):
            st.write("Google Cloud Platform에서 발급받은 `client_secrets.json` 파일이 필요합니다.")
            
            # 1. Credentials File Upload
            client_secrets_file = os.path.join(root_dir, "client_secrets.json")
            uploaded_secrets = st.file_uploader("client_secrets.json 업로드", type=["json"], key="youtube_secrets")
            if uploaded_secrets:
                with open(client_secrets_file, "wb") as f:
                    f.write(uploaded_secrets.getbuffer())
                st.success("인증 파일 업로드 완료!")
                
            # 2. Authentication
            token_file = os.path.join(root_dir, "token.pickle")
            is_authenticated = os.path.exists(token_file)
            
            if st.button("YouTube 계정 인증 (브라우저 열림)", key="auth_youtube", use_container_width=True):
                if os.path.exists(client_secrets_file):
                    try:
                        get_authenticated_service(client_secrets_file, token_file)
                        st.success("인증 성공!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"인증 실패: {e}")
                else:
                    st.error("client_secrets.json 파일이 없습니다. 먼저 업로드해주세요.")
                    
            if is_authenticated:
                st.success("✅ 인증됨")
                
                # 3. Upload Settings
                st.write("---")
                auto_upload = st.checkbox("영상 생성 후 자동 업로드", value=False, key="yt_auto_upload")
                
                yt_title_prefix = st.text_input("제목 접두사 (예: #Shorts)", value="#Shorts", key="yt_title_prefix")
                yt_privacy = st.selectbox("공개 설정", ["private", "unlisted", "public"], index=0, key="yt_privacy")
                yt_category = st.text_input("카테고리 ID (22: 인물/블로그)", value="22", key="yt_category")
            else:
                st.warning("⚠️ 유튜브 업로드 기능을 사용하려면 먼저 계정 인증이 필요합니다.")
                auto_upload = False



# Space before generate button
st.write("") 



import glob

# ... (existing imports)

# Load existing video if session state is empty (Persistence Recovery)
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

# Centered Generate Button (Removed - Moved to Top)
# _, col_gen_center, _ = st.columns([0.4, 0.2, 0.4])
# with col_gen_center:
#    # start_button = st.button("영상 생성", use_container_width=True, type="primary")
#    pass

if start_button:
    task_id = str(uuid4())
    if not params.video_subject and not params.video_script:
        st.error("❌ 영상 대본과 주제는 둘 다 비워둘 수 없습니다")
        st.stop()

    # BGM Validation
    if params.bgm_type == "random":
        song_dir = utils.song_dir()
        if not glob.glob(os.path.join(song_dir, "*.mp3")):
            st.error("❌ '배경 음악'이 '무작위'로 설정되었으나, 저장된 MP3 파일이 없습니다. 음악을 업로드하거나 설정을 '없음'으로 변경하세요.")
            st.stop()

    # Video Source Validation & Auto-Correction
    if params.video_source == "local":
        if not uploaded_files:
            # Try to fallback to Pexels/Pixabay if keys exist
            if config.app.get("pexels_api_keys"):
                st.warning("⚠️ 로컬 파일이 없어 'Pexels'로 자동 전환합니다.")
                params.video_source = "pexels"
            elif config.app.get("pixabay_api_keys"):
                st.warning("⚠️ 로컬 파일이 없어 'Pixabay'로 자동 전환합니다.")
                params.video_source = "pixabay"
            else:
                st.error("❌ 로컬 영상을 생성하려면 파일을 업로드해야 합니다. (또는 Pexels/Pixabay 키를 입력하세요)")
                st.stop()
                
    if params.video_source == "pexels":
        if not config.app.get("pexels_api_keys"):
             # Try fallback to Pixabay
            if config.app.get("pixabay_api_keys"):
                 st.warning("⚠️ Pexels 키가 없어 'Pixabay'로 자동 전환합니다.")
                 params.video_source = "pixabay"
            else:
                st.error("❌ Pexels API 키가 없습니다. 설정에서 키를 추가하거나 영상 소스를 변경하세요.")
                st.stop()
                
    if params.video_source == "pixabay":
        if not config.app.get("pixabay_api_keys"):
             # Try fallback to Pexels
            if config.app.get("pexels_api_keys"):
                 st.warning("⚠️ Pixabay 키가 없어 'Pexels'로 자동 전환합니다.")
                 params.video_source = "pexels"
            else:
                st.error("❌ Pixabay API 키가 없습니다. 설정에서 키를 추가하거나 영상 소스를 변경하세요.")
                st.stop()

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

    # Progress bar and status container
    # Use the container created above (generation_status_container)
    with generation_status_container:
        st.info("작업 초기화 중...")
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    result = None
    
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(tm.start, task_id=task_id, params=params)
            
            while not future.done():
                task_info = sm.state.get_task(task_id)
                if task_info:
                    progress = task_info.get("progress", 0)
                    state = task_info.get("state", const.TASK_STATE_PROCESSING)
                    task_msg = task_info.get("message", "")
                    
                    # Update progress bar
                    progress_bar.progress(min(int(progress) / 100, 1.0))
                    
                    # Update status text
                    if state == const.TASK_STATE_PROCESSING:
                        if task_msg:
                            status_text.info(f"{task_msg} ({int(progress)}%)")
                        else:
                            status_text.info(f"처리 중... {int(progress)}%")
                    elif state == const.TASK_STATE_FAILED:
                        if task_msg:
                            status_text.error(f"영상 생성 실패: {task_msg}")
                        else:
                            status_text.error("영상 생성 실패")
                        break # Exit loop if failed
                    elif state == const.TASK_STATE_COMPLETE:
                        if task_msg:
                            status_text.success(f"{task_msg}")
                        else:
                            status_text.success("영상 생성 완료")
                else:
                    # Retry getting task info or just show starting
                    status_text.info(f"작업 시작 중... ({task_id})")
                
                time.sleep(0.5)
            
            result = future.result()
            
    except Exception as e:
        logger.error(f"Error during video generation: {e}")
        status_text.error(f"오류: {e}")
        st.stop()

    if not result or "videos" not in result:
        progress_bar.progress(0)
        status_text.error(tr("Video Generation Failed"))
        logger.error(tr("Video Generation Failed"))
        # scroll_to_bottom()
        st.stop()

    # Final success state
    progress_bar.progress(1.0)
    status_text.success(tr("Video Generation Completed"))
    
    if "generated_video_files" not in st.session_state:
        st.session_state["generated_video_files"] = []

    video_files = result.get("videos", [])
    st.session_state["generated_video_files"] = video_files
    
    # Auto Upload Logic
    if st.session_state.get("yt_auto_upload"):
        token_file = os.path.join(root_dir, "token.pickle")
        client_secrets_file = os.path.join(root_dir, "client_secrets.json")
        
        if os.path.exists(token_file) and os.path.exists(client_secrets_file):
            for video_path in video_files:
                if os.path.exists(video_path):
                    st.info(f"유튜브 업로드 시작: {os.path.basename(video_path)}")
                    try:
                        youtube = get_authenticated_service(client_secrets_file, token_file)
                        
                        # Generate Title/Desc
                        title = f"{st.session_state.get('yt_title_prefix', '')} {params.video_subject}"
                        description = f"Generated by MoneyPrinterTurbo\nSubject: {params.video_subject}\n\n{params.video_script[:200] if params.video_script else ''}..."
                        keywords = params.video_terms if isinstance(params.video_terms, str) else ",".join(params.video_terms) if params.video_terms else "shorts,ai"
                        
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
                            st.success(f"업로드 성공! Video ID: {vid_id}")
                            st.markdown(f"[영상 보러가기](https://youtu.be/{vid_id})")
                        else:
                            st.error("업로드 실패")
                    except Exception as e:
                        st.error(f"업로드 중 오류 발생: {e}")
        else:
            st.warning("자동 업로드가 켜져있지만 인증 정보가 없습니다.")

    open_task_folder(task_id)
    logger.info(tr("Video Generation Completed"))
    
    # Rerun to show the result in the right column
    st.rerun()

# Always check if there are generated videos in session state to display (persistence)
# (Moved to Right Column - see above)

config.save_config()
