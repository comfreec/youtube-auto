import os
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

st.set_page_config(
    page_title="유튜브 영상 자동생성기",
    page_icon="📹",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Report a bug": "https://github.com/harry0703/MoneyPrinterTurbo/issues",
        "About": "# 유튜브 영상 자동생성기\n\nAI 기반 자동 영상 생성 도구입니다.",
    },
)


streamlit_style = """
<style>
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
    
    /* Base App Settings - Light Mode */
    :root { color-scheme: light; }
    .stApp { 
        background-color: #ffffff; 
        color: #31333F; 
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif; 
    }
    
    /* Headings */
    h1 { 
        font-family: 'Pretendard'; 
        font-weight: 900; 
        background: linear-gradient(90deg, #FF3CAC 0%, #784BA0 50%, #2B86C5 100%); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        letter-spacing: -1px; 
        padding-bottom: 20px; 
        text-align: left; 
    }
    h2, h3, h4, h5, h6 { color: #31333F !important; font-weight: 700; }
    
    /* Text Color Overrides to ensure visibility on white */
    body, .stApp, .stMarkdown, p, label, span, div { color: #31333F !important; }
    .stTextInput label, .stTextArea label, .stSelectbox label, .stSlider label, .stCheckbox label, .stRadio label { color: #31333F !important; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; 
        white-space: pre-wrap; 
        background-color: transparent; 
        border-radius: 4px 4px 0 0; 
        gap: 1px; 
        padding-top: 10px; 
        padding-bottom: 10px; 
        color: #888888; 
        font-weight: 600; 
    }
    .stTabs [aria-selected="true"] { 
        background-color: transparent; 
        color: #31333F !important; 
        border-bottom: 2px solid #FF3CAC; 
    }
    
    /* Containers */
    div[data-testid="stVerticalBlockBorderWrapper"] { 
        background-color: #f8f9fa; 
        border-radius: 12px; 
        padding: 20px; 
        border: 1px solid #dee2e6; 
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); 
    }
    
    /* Inputs, TextAreas, SelectBoxes */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] { 
        background-color: #ffffff !important; 
        color: #31333F !important; 
        border: 1px solid #ced4da !important; 
        border-radius: 8px !important; 
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #adb5bd !important; }
    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox div[data-baseweb="select"]:focus-within { 
        border-color: #FF3CAC !important; 
        box-shadow: 0 0 0 1px #FF3CAC !important; 
    }
    
    /* Dropdowns & Options - Clean White Theme */
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[data-baseweb="menu"] {
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
    }
    li[data-baseweb="option"], div[data-baseweb="option"] {
        background-color: #ffffff !important;
        color: #31333F !important;
    }
    li[data-baseweb="option"] *, div[data-baseweb="option"] * {
        color: #31333F !important;
    }
    li[data-baseweb="option"]:hover, li[data-baseweb="option"][aria-selected="true"],
    div[data-baseweb="option"]:hover, div[data-baseweb="option"][aria-selected="true"] {
        background-color: #FF3CAC !important;
        color: #ffffff !important;
    }
    li[data-baseweb="option"]:hover *, li[data-baseweb="option"][aria-selected="true"] *,
    div[data-baseweb="option"]:hover *, div[data-baseweb="option"][aria-selected="true"] * {
        color: #ffffff !important;
    }

    /* Buttons */
    .stButton > button {
        background-color: #ffffff !important;
        color: #31333F !important;
        border: 1px solid #ced4da !important;
    }
    .stButton > button:hover {
        border-color: #FF3CAC !important;
        color: #FF3CAC !important;
    }
    .stButton button[kind="primary"] { 
        background: linear-gradient(90deg, #FF3CAC 0%, #784BA0 100%) !important; 
        border: none !important; 
        color: white !important; 
        font-weight: bold; 
        padding: 0.75rem 2rem; 
        border-radius: 30px; 
        transition: transform 0.2s, box-shadow 0.2s; 
    }
    .stButton button[kind="primary"]:hover { 
        transform: scale(1.05); 
        box-shadow: 0 0 20px rgba(255, 60, 172, 0.5); 
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { 
        background-color: #f0f2f6; 
        border-right: 1px solid #dee2e6; 
    }
    .streamlit-expanderHeader { 
        background-color: #f8f9fa !important; 
        color: #31333F !important; 
        border-radius: 8px; 
    }
    
    /* Input caret color */
    input, textarea { caret-color: #FF3CAC !important; }
</style>
"""
st.markdown(streamlit_style, unsafe_allow_html=True)

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
st.title("유튜브 영상 자동생성기")

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

# --- REFACTORED LAYOUT: TABS ---
params = VideoParams(video_subject="")
uploaded_files = []

# Create Tabs
tab1, tab2, tab3, tab4 = st.tabs(["대본 및 기획", "영상 및 오디오 설정", "자막 및 스타일", "시스템 및 API 설정"])

# --- TAB 1: SCRIPT ---
with tab1:
    with st.container(border=True):
        st.write("**영상 대본 설정**")
        params.video_subject = st.text_input(
            "영상 주제 (키워드를 입력하면 :red[AI가 자동으로] 대본을 생성합니다)",
            value=st.session_state["video_subject"],
            key="video_subject_input",
        ).strip()

        # Script Language UI Removed - Forced to Korean
        params.video_language = "ko-KR"
        auto_script_enabled = st.checkbox(
            "제목 기반 실시간 대본 자동 생성", value=config.ui.get("auto_script_enabled", True)
        )
        config.ui["auto_script_enabled"] = auto_script_enabled
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

        if st.button(
            "클릭하여 **주제**를 기반으로 [영상 대본] 및 [영상 키워드] 생성", key="auto_generate_script"
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
        params.video_script = st.text_area(
            "영상 대본 (:blue[① 선택 사항, AI 생성  ② 올바른 구두점은 자막 생성에 도움이 됩니다])", value=st.session_state["video_script"], height=280
        )
        # Removed "Generate Video Keywords" button as per user request to simplify UI
        # if st.button(tr("Generate Video Keywords"), key="auto_generate_terms"):
        #     if not params.video_script:
        #         st.error(tr("Please Enter the Video Subject"))
        #         st.stop()
        #
        #     with st.spinner(tr("Generating Video Keywords")):
        #         terms = llm.generate_terms(params.video_subject, params.video_script)
        #         if "Error: " in terms:
        #             st.error(tr(terms))
        #         else:
        #             st.session_state["video_terms"] = ", ".join(terms)

        params.video_terms = st.text_area(
            "영상 키워드 (:blue[① 선택 사항, AI 생성 ② **영문 쉼표**로 구분, 영어만 가능])", value=st.session_state["video_terms"]
        )

# --- TAB 2: VIDEO & AUDIO ---
with tab2:
    col_video, col_audio = st.columns(2)
    
    # Left Column: Video Settings
    with col_video:
        with st.container(border=True):
            st.write("**영상 설정**")
            video_concat_modes = [
                ("순차 연결", "sequential"),
                ("무작위 연결 (권장)", "random"),
            ]
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
            saved_video_source_index = [v[1] for v in video_sources].index(
                saved_video_source_name
            )

            selected_index = st.selectbox(
                "영상 소스",
                options=range(len(video_sources)),
                format_func=lambda x: video_sources[x][0],
                index=saved_video_source_index,
            )
            params.video_source = video_sources[selected_index][1]
            config.app["video_source"] = params.video_source

            if params.video_source == "local":
                st.info("로컬 파일 모드: 파일을 업로드하지 않아도 기본 배경으로 생성됩니다. 업로드하면 해당 파일을 사용합니다.")
                uploaded_files = st.file_uploader(
                    "로컬 파일 업로드",
                    type=["mp4", "mov", "avi", "flv", "mkv", "jpg", "jpeg", "png"],
                    accept_multiple_files=True,
                )

            selected_index = st.selectbox(
                "영상 연결 모드",
                index=1,
                options=range(
                    len(video_concat_modes)
                ),  # Use the index as the internal option value
                format_func=lambda x: video_concat_modes[x][
                    0
                ],  # The label is displayed to the user
            )
            params.video_concat_mode = VideoConcatMode(
                video_concat_modes[selected_index][1]
            )

            # Video Transition Mode
            video_transition_modes = [
                ("없음", VideoTransitionMode.none.value),
                ("무작위", VideoTransitionMode.shuffle.value),
                ("페이드 인", VideoTransitionMode.fade_in.value),
                ("페이드 아웃", VideoTransitionMode.fade_out.value),
                ("슬라이드 인", VideoTransitionMode.slide_in.value),
                ("슬라이드 아웃", VideoTransitionMode.slide_out.value),
            ]
            selected_index = st.selectbox(
                "영상 전환 모드",
                options=range(len(video_transition_modes)),
                format_func=lambda x: video_transition_modes[x][0],
                index=0,
            )
            params.video_transition_mode = VideoTransitionMode(
                video_transition_modes[selected_index][1]
            )

            video_aspect_ratios = [
                ("세로 9:16", VideoAspect.portrait.value),
                ("가로 16:9", VideoAspect.landscape.value),
            ]
            selected_index = st.selectbox(
                "영상 비율",
                options=range(
                    len(video_aspect_ratios)
                ),  # Use the index as the internal option value
                format_func=lambda x: video_aspect_ratios[x][
                    0
                ],  # The label is displayed to the user
            )
            params.video_aspect = VideoAspect(video_aspect_ratios[selected_index][1])

            params.video_clip_duration = st.selectbox(
                "영상 클립 최대 지속 시간 (초)", options=[2, 3, 4, 5, 6, 7, 8, 9, 10], index=1
            )
            params.video_count = st.selectbox(
                "동시 생성 영상 수",
                options=[1, 2, 3, 4, 5],
                index=0,
            )

    # Right Column: Audio Settings
    with col_audio:
        with st.container(border=True):
            st.write("**오디오 설정**")

            # TTS Server Selection
            tts_servers = [
                ("azure-tts-v1", "Azure TTS V1"),
                ("azure-tts-v2", "Azure TTS V2"),
                ("siliconflow", "SiliconFlow TTS"),
                ("gemini-tts", "Google Gemini TTS"),
            ]

            # Get saved TTS server
            saved_tts_server = config.ui.get("tts_server", "azure-tts-v1")
            saved_tts_server_index = 0
            for i, (server_value, _) in enumerate(tts_servers):
                if server_value == saved_tts_server:
                    saved_tts_server_index = i
                    break

            selected_tts_server_index = st.selectbox(
                "TTS 서버",
                options=range(len(tts_servers)),
                format_func=lambda x: tts_servers[x][1],
                index=saved_tts_server_index,
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
                        if "V2" in v:
                            filtered_voices.append(v)
                    else:
                        if "V2" not in v:
                            filtered_voices.append(v)

            friendly_names = {
                v: v.replace("Female", tr("Female"))
                .replace("Male", tr("Male"))
                .replace("Neural", "")
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

            if friendly_names:
                selected_friendly_name = st.selectbox(
                    tr("Speech Synthesis"),
                    options=list(friendly_names.values()),
                    index=min(saved_voice_name_index, len(friendly_names) - 1)
                    if friendly_names
                    else 0,
                )

                voice_name = list(friendly_names.keys())[
                    list(friendly_names.values()).index(selected_friendly_name)
                ]
                params.voice_name = voice_name
                config.ui["voice_name"] = voice_name
            else:
                st.warning(
                    tr(
                        "No voices available for the selected TTS server. Please select another server."
                    )
                )
                params.voice_name = ""
                config.ui["voice_name"] = ""

            if friendly_names and st.button(tr("Play Voice")):
                play_content = params.video_subject
                if not play_content:
                    play_content = params.video_script
                if not play_content:
                    play_content = tr("Voice Example")
                with st.spinner(tr("Synthesizing Voice")):
                    temp_dir = utils.storage_dir("temp", create=True)
                    audio_file = os.path.join(temp_dir, f"tmp-voice-{str(uuid4())}.mp3")
                    sub_maker = voice.tts(
                        text=play_content,
                        voice_name=voice_name,
                        voice_rate=params.voice_rate,
                        voice_file=audio_file,
                        voice_volume=params.voice_volume,
                    )
                    if not sub_maker:
                        play_content = "This is a example voice. if you hear this, the voice synthesis failed with the original content."
                        sub_maker = voice.tts(
                            text=play_content,
                            voice_name=voice_name,
                            voice_rate=params.voice_rate,
                            voice_file=audio_file,
                            voice_volume=params.voice_volume,
                        )

                    if sub_maker and os.path.exists(audio_file):
                        st.audio(audio_file, format="audio/mp3")
                        if os.path.exists(audio_file):
                            os.remove(audio_file)

            if selected_tts_server == "azure-tts-v2" or (
                voice_name and voice.is_azure_v2_voice(voice_name)
            ):
                saved_azure_speech_region = config.azure.get("speech_region", "")
                saved_azure_speech_key = config.azure.get("speech_key", "")
                azure_speech_region = st.text_input(
                    tr("Speech Region"),
                    value=saved_azure_speech_region,
                    key="azure_speech_region_input",
                )
                azure_speech_key = st.text_input(
                    tr("Speech Key"),
                    value=saved_azure_speech_key,
                    type="password",
                    key="azure_speech_key_input",
                )
                config.azure["speech_region"] = azure_speech_region
                config.azure["speech_key"] = azure_speech_key

            if selected_tts_server == "siliconflow" or (
                voice_name and voice.is_siliconflow_voice(voice_name)
            ):
                saved_siliconflow_api_key = config.siliconflow.get("api_key", "")

                siliconflow_api_key = st.text_input(
                    tr("SiliconFlow API Key"),
                    value=saved_siliconflow_api_key,
                    type="password",
                    key="siliconflow_api_key_input",
                )

                st.info(
                    tr("SiliconFlow TTS Settings")
                    + ":\n"
                    + "- "
                    + tr("Speed: Range [0.25, 4.0], default is 1.0")
                    + "\n"
                    + "- "
                    + tr("Volume: Uses Speech Volume setting, default 1.0 maps to gain 0")
                )

                config.siliconflow["api_key"] = siliconflow_api_key

            params.voice_volume = st.selectbox(
                tr("Speech Volume"),
                options=[0.6, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0, 4.0, 5.0],
                index=2,
            )

            params.voice_rate = st.selectbox(
                tr("Speech Rate"),
                options=[0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.0],
                index=2,
            )

            bgm_options = [
                (tr("No Background Music"), ""),
                (tr("Random Background Music"), "random"),
                (tr("Custom Background Music"), "custom"),
            ]
            selected_index = st.selectbox(
                tr("Background Music"),
                index=1,
                options=range(
                    len(bgm_options)
                ),  # Use the index as the internal option value
                format_func=lambda x: bgm_options[x][
                    0
                ],  # The label is displayed to the user
            )
            params.bgm_type = bgm_options[selected_index][1]

            if params.bgm_type == "custom":
                custom_bgm_file = st.text_input(
                    tr("Custom Background Music File"), key="custom_bgm_file_input"
                )
                if custom_bgm_file and os.path.exists(custom_bgm_file):
                    params.bgm_file = custom_bgm_file
            params.bgm_volume = st.selectbox(
                tr("Background Music Volume"),
                options=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
                index=2,
            )

# --- TAB 3: SUBTITLES & STYLE ---
with tab3:
    with st.container(border=True):
        st.write(tr("Subtitle Settings"))
        params.subtitle_enabled = st.checkbox(tr("Enable Subtitles"), value=True)
        font_names = get_all_fonts()
        saved_font_name = config.ui.get("font_name", "MicrosoftYaHeiBold.ttc")
        saved_font_name_index = 0
        if saved_font_name in font_names:
            saved_font_name_index = font_names.index(saved_font_name)
        params.font_name = st.selectbox(
            tr("Font"), font_names, index=saved_font_name_index
        )
        config.ui["font_name"] = params.font_name

        subtitle_positions = [
            (tr("Top"), "top"),
            (tr("Center"), "center"),
            (tr("Bottom"), "bottom"),
            (tr("Custom"), "custom"),
        ]
        selected_index = st.selectbox(
            tr("Position"),
            index=2,
            options=range(len(subtitle_positions)),
            format_func=lambda x: subtitle_positions[x][0],
        )
        params.subtitle_position = subtitle_positions[selected_index][1]

        if params.subtitle_position == "custom":
            custom_position = st.text_input(
                tr("Custom Position (% from top)"),
                value="70.0",
                key="custom_position_input",
            )
            try:
                params.custom_position = float(custom_position)
                if params.custom_position < 0 or params.custom_position > 100:
                    st.error(tr("Please enter a value between 0 and 100"))
            except ValueError:
                st.error(tr("Please enter a valid number"))

        font_cols = st.columns([0.3, 0.7])
        with font_cols[0]:
            saved_text_fore_color = config.ui.get("text_fore_color", "#FFFFFF")
            params.text_fore_color = st.color_picker(
                tr("Font Color"), saved_text_fore_color
            )
            config.ui["text_fore_color"] = params.text_fore_color

        with font_cols[1]:
            saved_font_size = config.ui.get("font_size", 60)
            params.font_size = st.slider(tr("Font Size"), 30, 100, saved_font_size)
            config.ui["font_size"] = params.font_size

        stroke_cols = st.columns([0.3, 0.7])
        with stroke_cols[0]:
            params.stroke_color = st.color_picker(tr("Stroke Color"), "#000000")
        with stroke_cols[1]:
            params.stroke_width = st.slider(tr("Stroke Width"), 0.0, 10.0, 1.5)

# --- TAB 4: SYSTEM & API ---
with tab4:
    col_llm, col_keys = st.columns(2)
    
    with col_llm:
        with st.container(border=True):
            st.write("LLM 설정")
            llm_providers = [
                "OpenAI", "Moonshot", "Azure", "Qwen", "DeepSeek", "ModelScope",
                "Gemini", "Ollama", "G4f", "OneAPI", "Cloudflare", "ERNIE", "Pollinations"
            ]
            saved_llm_provider = config.app.get("llm_provider", "pollinations").lower()
            saved_llm_provider_index = 0
            for i, provider in enumerate(llm_providers):
                if provider.lower() == saved_llm_provider:
                    saved_llm_provider_index = i
                    break

            llm_provider = st.selectbox("LLM 제공자", options=llm_providers, index=saved_llm_provider_index)
            llm_provider = llm_provider.lower()
            config.app["llm_provider"] = llm_provider

            llm_api_key = config.app.get(f"{llm_provider}_api_key", "")
            llm_secret_key = config.app.get(f"{llm_provider}_secret_key", "")
            llm_base_url = config.app.get(f"{llm_provider}_base_url", "")
            llm_model_name = config.app.get(f"{llm_provider}_model_name", "")
            llm_account_id = config.app.get(f"{llm_provider}_account_id", "")

            st_llm_api_key = st.text_input("API 키", value=llm_api_key, type="password")
            st_llm_base_url = st.text_input("기본 URL", value=llm_base_url)
            
            if llm_provider == "ernie":
                st_llm_secret_key = st.text_input("비밀 키", value=llm_secret_key, type="password")
                config.app[f"{llm_provider}_secret_key"] = st_llm_secret_key

            if llm_provider == "cloudflare":
                st_llm_account_id = st.text_input("계정 ID", value=llm_account_id)
                config.app[f"{llm_provider}_account_id"] = st_llm_account_id

            st_llm_model_name = st.text_input("모델 이름", value=llm_model_name, key=f"{llm_provider}_model_name_input")
            
            if st_llm_api_key: config.app[f"{llm_provider}_api_key"] = st_llm_api_key
            if st_llm_base_url: config.app[f"{llm_provider}_base_url"] = st_llm_base_url
            if st_llm_model_name: config.app[f"{llm_provider}_model_name"] = st_llm_model_name

            # Log Settings
            st.divider()
            hide_log = st.checkbox("로그 숨기기", value=config.ui.get("hide_log", False))
            config.ui["hide_log"] = hide_log

            st.divider()
            st.write("대체 사용 설정")
            script_fallback_enabled = st.checkbox(
                "LLM 실패 시 대체 대본 사용", value=config.ui.get("script_fallback_enabled", False)
            )
            terms_fallback_enabled = st.checkbox(
                "LLM 실패 시 키워드 대체 사용", value=config.ui.get("terms_fallback_enabled", True)
            )
            config.ui["script_fallback_enabled"] = script_fallback_enabled
            config.ui["terms_fallback_enabled"] = terms_fallback_enabled

    with col_keys:
        with st.container(border=True):
            st.write("Pexels 및 Pixabay API 키 관리")
            
            key_tabs_1, key_tabs_2 = st.tabs(["Pexels", "Pixabay"])

            with key_tabs_1:
                st.subheader("Pexels API Keys")
                if config.app["pexels_api_keys"]:
                    st.write("현재 키:")
                    for key in config.app["pexels_api_keys"]:
                        st.code(key)
                else:
                    st.info("현재 Pexels API 키가 없습니다")

                new_key = st.text_input("Pexels API 키 추가", key="pexels_new_key")
                if st.button("Pexels API 키 추가"):
                    if new_key and new_key not in config.app["pexels_api_keys"]:
                        config.app["pexels_api_keys"].append(new_key)
                        config.save_config()
                        st.success("Pexels API 키가 성공적으로 추가되었습니다")
                    elif new_key in config.app["pexels_api_keys"]:
                        st.warning("이 API 키는 이미 존재합니다")
                    else:
                        st.error("유효한 API 키를 입력하세요")

                if config.app["pexels_api_keys"]:
                    delete_key = st.selectbox(
                        "삭제할 Pexels API 키 선택", config.app["pexels_api_keys"], key="pexels_delete_key"
                    )
                    if st.button("선택한 Pexels API 키 삭제"):
                        config.app["pexels_api_keys"].remove(delete_key)
                        config.save_config()
                        st.success("Pexels API 키가 성공적으로 삭제되었습니다")

            with key_tabs_2:
                st.subheader("Pixabay API Keys")
                if config.app["pixabay_api_keys"]:
                    st.write("현재 키:")
                    for key in config.app["pixabay_api_keys"]:
                        st.code(key)
                else:
                    st.info("현재 Pixabay API 키가 없습니다")

                new_key = st.text_input("Pixabay API 키 추가", key="pixabay_new_key")
                if st.button("Pixabay API 키 추가"):
                    if new_key and new_key not in config.app["pixabay_api_keys"]:
                        config.app["pixabay_api_keys"].append(new_key)
                        config.save_config()
                        st.success("Pixabay API 키가 성공적으로 추가되었습니다")
                    elif new_key in config.app["pixabay_api_keys"]:
                        st.warning("이 API 키는 이미 존재합니다")
                    else:
                        st.error("유효한 API 키를 입력하세요")

                if config.app["pixabay_api_keys"]:
                    delete_key = st.selectbox(
                        "삭제할 Pixabay API 키 선택", config.app["pixabay_api_keys"], key="pixabay_delete_key"
                    )
                    if st.button("선택한 Pixabay API 키 삭제"):
                        config.app["pixabay_api_keys"].remove(delete_key)
                        config.save_config()
                        st.success("Pixabay API 키가 성공적으로 삭제되었습니다")


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

start_button = st.button("영상 생성", use_container_width=True, type="primary")

if start_button:
    task_id = str(uuid4())
    if not params.video_subject and not params.video_script:
        st.error("영상 대본과 주제는 둘 다 비워둘 수 없습니다")
        st.stop()

    if params.video_source == "local":
        if not uploaded_files:
            st.error("로컬 파일을 업로드하거나 다른 영상 소스(Pexels/Pixabay)를 선택하세요")
            st.stop()
    elif params.video_source == "pexels":
        if not config.app["pexels_api_keys"]:
            st.error("Pexels API 키를 입력하세요")
            st.stop()
    elif params.video_source == "pixabay":
        if not config.app["pixabay_api_keys"]:
            st.error("Pixabay API 키를 입력하세요")
            st.stop()
    else:
        st.error("유효한 영상 소스를 선택하세요")
        st.stop()

    if uploaded_files:
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
    from app.services import state as sm
    progress_container = st.container()
    with progress_container:
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
    
    # Display logic handled below outside the button scope if needed, 
    # but for now we keep it here and also ensure it persists
    try:
        if video_files:
            # Use full width for better visibility
            for i, video_path in enumerate(video_files):
                if os.path.exists(video_path):
                    st.write(f"**영상 파일:** `{video_path}`")
                    
                    # Main video player
                    col_v_1, col_v_2, col_v_3 = st.columns([3, 2, 3])
                    with col_v_2:
                        st.video(video_path, format="video/mp4")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        # Add a download button for safety
                        try:
                            with open(video_path, "rb") as video_file:
                                video_bytes = video_file.read()
                            file_name = os.path.basename(video_path)
                            st.download_button(
                                label=f"📥 영상 다운로드 ({file_name})",
                                data=video_bytes,
                                file_name=file_name,
                                mime="video/mp4",
                                key=f"dl_btn_{i}",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"다운로드 준비 중 오류 발생: {e}")
                        
                        # Add Copy to Desktop button
                        if st.button(f"📂 바탕화면으로 복사", key=f"copy_desk_{i}", use_container_width=True):
                            try:
                                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                                dest_file = os.path.join(desktop_path, file_name)
                                import shutil
                                shutil.copy2(video_path, dest_file)
                                st.success(f"바탕화면에 복사되었습니다: {dest_file}")
                            except Exception as e:
                                st.error(f"복사 실패: {e}")

                    with col2:
                        # Add Open in System Player button
                        if st.button("💻 시스템 플레이어에서 재생", key=f"play_sys_{i}", use_container_width=True):
                            try:
                                if os.name == 'nt':
                                    os.startfile(video_path)
                                else:
                                    import subprocess
                                    subprocess.call(('xdg-open', video_path))
                            except Exception as e:
                                st.error(f"플레이어 실행 실패: {e}. (다른 플레이어로 파일을 열어보세요)")

                else:
                    st.error(f"Video file not found: {video_path}")
    except Exception as e:
        logger.error(f"Error displaying video: {e}")
        st.error(f"Error displaying video: {e}")

    open_task_folder(task_id)
    logger.info(tr("Video Generation Completed"))
    scroll_to_bottom()

# Always check if there are generated videos in session state to display (persistence)
if "generated_video_files" in st.session_state and st.session_state["generated_video_files"]:
    st.divider()
    st.subheader(tr("Last Generated Videos"))
    video_files = st.session_state["generated_video_files"]
    
    for i, video_path in enumerate(video_files):
        if os.path.exists(video_path):
            try:
                st.write(f"**Video File:** `{video_path}`")
                
                # Persistent video player
                col_v_p_1, col_v_p_2, col_v_p_3 = st.columns([3, 2, 3])
                with col_v_p_2:
                    st.video(video_path, format="video/mp4")
                
                col1, col2 = st.columns(2)
                with col1:
                    # Add Download button (Persistent view)
                    try:
                        with open(video_path, "rb") as video_file:
                            video_bytes = video_file.read()
                        file_name = os.path.basename(video_path)
                        st.download_button(
                            label=f"📥 영상 다운로드 ({file_name})",
                            data=video_bytes,
                            file_name=file_name,
                            mime="video/mp4",
                            key=f"dl_btn_pers_{i}",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"다운로드 준비 중 오류 발생: {e}")
                    
                    # Add Copy to Desktop button (Persistent view)
                    if st.button(f"📂 바탕화면으로 복사", key=f"copy_desk_pers_{i}", use_container_width=True):
                        try:
                            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                            dest_file = os.path.join(desktop_path, file_name)
                            import shutil
                            shutil.copy2(video_path, dest_file)
                            st.success(f"바탕화면에 복사되었습니다: {dest_file}")
                        except Exception as e:
                            st.error(f"복사 실패: {e}")

                with col2:
                    # Add Open in System Player button (Persistent view)
                    if st.button("💻 시스템 플레이어에서 재생", key=f"play_sys_pers_{i}", use_container_width=True):
                        try:
                            if os.name == 'nt':
                                os.startfile(video_path)
                            else:
                                import subprocess
                                subprocess.call(('xdg-open', video_path))
                        except Exception as e:
                            st.error(f"플레이어 실행 실패: {e}. (다른 플레이어로 파일을 열어보세요)")
                
            except Exception:
                pass # Already handled or transient error


config.save_config()
