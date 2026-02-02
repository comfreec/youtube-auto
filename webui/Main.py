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

# Import VideoAspect for timer video generation
from app.models.schema import VideoAspect
from app.config import config

# Import mobile optimization
try:
    from webui.mobile_optimization import (
        add_mobile_styles, add_mobile_connection_monitor, show_mobile_generation_tips,
        show_mobile_progress_tracker, check_mobile_compatibility, add_mobile_error_recovery
    )
    from webui.mobile_session_manager import mobile_session_manager
    MOBILE_OPTIMIZATION_AVAILABLE = True
except ImportError:
    MOBILE_OPTIMIZATION_AVAILABLE = False


st.set_page_config(
    page_title="AI 영상 생성 스튜디오 | MoneyPrinterTurbo",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None  # 완전히 메뉴 제거
)

# PWA 요소 추가
def add_pwa_elements():
    """PWA 요소를 HTML에 추가"""
    pwa_html = """
    <!-- PWA 메타 태그 -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="AI영상">
    <meta name="application-name" content="AI영상">
    <meta name="theme-color" content="#667eea">
    
    <!-- PWA 매니페스트 -->
    <link rel="manifest" href="data:application/json;base64,eyJuYW1lIjoiQUkg7JiB7IOB7IOd7ISxIiwic2hvcnRfbmFtZSI6IkFJ7JiB7IOBIiwiZGVzY3JpcHRpb24iOiJBSeuhnCDsnpDrj5kg7JiB7IOB7J2EIOyDneyEsO2VmOuKlCDrqqjrsJTsnbwg7JWxIiwic3RhcnRfdXJsIjoiLyIsImRpc3BsYXkiOiJzdGFuZGFsb25lIiwiYmFja2dyb3VuZF9jb2xvciI6IiMwZjBmMjMiLCJ0aGVtZV9jb2xvciI6IiM2NjdlZWEifQ==">
    
    <!-- PWA 설치 및 서비스 워커 JavaScript -->
    <script>
    // PWA 설치 프롬프트
    let deferredPrompt;
    
    window.addEventListener('beforeinstallprompt', (e) => {
        console.log('PWA 설치 프롬프트 준비됨');
        e.preventDefault();
        deferredPrompt = e;
        showInstallButton();
    });
    
    function showInstallButton() {
        const installBanner = document.createElement('div');
        installBanner.id = 'install-banner';
        installBanner.innerHTML = `
            <div style="
                position: fixed; 
                bottom: 20px; 
                left: 20px; 
                right: 20px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                padding: 1rem; 
                border-radius: 12px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: space-between;
            ">
                <div>
                    <div style="font-weight: bold; margin-bottom: 0.25rem;">📱 앱으로 설치</div>
                    <div style="font-size: 0.9rem; opacity: 0.9;">홈 화면에 추가하여 앱처럼 사용하세요!</div>
                </div>
                <div>
                    <button onclick="installPWA()" style="
                        background: rgba(255,255,255,0.2); 
                        border: 1px solid rgba(255,255,255,0.3); 
                        color: white; 
                        padding: 0.5rem 1rem; 
                        border-radius: 8px; 
                        margin-right: 0.5rem;
                        cursor: pointer;
                    ">설치</button>
                    <button onclick="closeInstallBanner()" style="
                        background: transparent; 
                        border: none; 
                        color: white; 
                        font-size: 1.2rem;
                        cursor: pointer;
                    ">×</button>
                </div>
            </div>
        `;
        document.body.appendChild(installBanner);
    }
    
    function installPWA() {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            deferredPrompt.userChoice.then((choiceResult) => {
                if (choiceResult.outcome === 'accepted') {
                    console.log('PWA 설치 승인됨');
                } else {
                    console.log('PWA 설치 거부됨');
                }
                deferredPrompt = null;
                closeInstallBanner();
            });
        }
    }
    
    function closeInstallBanner() {
        const banner = document.getElementById('install-banner');
        if (banner) {
            banner.remove();
        }
    }
    
    // 앱 설치 완료 감지
    window.addEventListener('appinstalled', (evt) => {
        console.log('PWA 설치 완료!');
        closeInstallBanner();
    });
    
    // 서비스 워커 등록 (간단 버전)
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            const swCode = `
                const CACHE_NAME = 'ai-video-v1';
                self.addEventListener('install', e => {
                    console.log('SW 설치');
                    self.skipWaiting();
                });
                self.addEventListener('activate', e => {
                    console.log('SW 활성화');
                    e.waitUntil(clients.claim());
                });
                self.addEventListener('fetch', e => {
                    if (e.request.method === 'GET') {
                        e.respondWith(
                            caches.match(e.request).then(response => {
                                return response || fetch(e.request);
                            })
                        );
                    }
                });
            `;
            
            const blob = new Blob([swCode], { type: 'application/javascript' });
            const swUrl = URL.createObjectURL(blob);
            
            navigator.serviceWorker.register(swUrl)
                .then(registration => {
                    console.log('서비스 워커 등록 성공');
                })
                .catch(error => {
                    console.log('서비스 워커 등록 실패:', error);
                });
        });
    }
    </script>
    """
    st.markdown(pwa_html, unsafe_allow_html=True)

# PWA 요소 추가
add_pwa_elements()

# IMMEDIATE MENU HIDING - 페이지 로딩 즉시 적용
immediate_hide_css = """
<style>
    /* IMMEDIATE HIDE - 로딩 시 깜빡임 방지 */
    header[data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        position: absolute !important;
        top: -9999px !important;
        opacity: 0 !important;
    }
    
    #MainMenu {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
    }
    
    .stDeployButton {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
    }
    
    footer {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
    }
    
    /* Hide hamburger menu immediately */
    button[title="View fullscreen"] {
        display: none !important;
        opacity: 0 !important;
    }
    
    /* Hide settings menu immediately */
    button[aria-label="Settings"] {
        display: none !important;
        opacity: 0 !important;
    }
    
    /* Hide "Made with Streamlit" immediately */
    .viewerBadge_container__1QSob,
    .viewerBadge_link__1S137 {
        display: none !important;
        opacity: 0 !important;
    }
    
    /* Hide toolbar immediately */
    .stToolbar,
    [data-testid="stToolbar"] {
        display: none !important;
        opacity: 0 !important;
    }
    
    /* Hide status widget immediately */
    .stStatusWidget,
    [data-testid="stStatusWidget"] {
        display: none !important;
        opacity: 0 !important;
    }
    
    /* Hide decoration immediately */
    [data-testid="stDecoration"] {
        display: none !important;
        opacity: 0 !important;
    }
    
    /* Hide floating container immediately */
    .stFloatingContainer {
        display: none !important;
        opacity: 0 !important;
    }
    
    /* Force hide any menu-related elements immediately */
    .css-1d391kg, .css-1v0mbdj, .css-18e3th9, .css-1dp5vir {
        display: none !important;
        opacity: 0 !important;
    }
    
    /* Remove top padding immediately */
    .main .block-container {
        padding-top: 1rem !important;
    }
    
    /* Hide any remaining top elements immediately */
    .element-container:first-child {
        margin-top: 0 !important;
    }
    
    /* Additional immediate hiding */
    .stApp > header,
    .stApp > div[data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        height: 0 !important;
        position: absolute !important;
        top: -9999px !important;
    }
</style>
"""
st.markdown(immediate_hide_css, unsafe_allow_html=True)

# Apply mobile optimizations
if MOBILE_OPTIMIZATION_AVAILABLE:
    add_mobile_styles()
    add_mobile_connection_monitor()
    add_mobile_error_recovery()


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
    
    /* Base App */
    .stApp { 
        background: var(--surface-dark);
        color: var(--text-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
        font-weight: 400;
        line-height: 1.6;
    }
    
    /* Premium Typography - COMPACT VERSION */
    h1 { 
        font-family: 'Inter', sans-serif;
        font-weight: 900;
        font-size: 2rem !important;  /* Reduced from 2.5rem */
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin: 1rem 0 1.5rem 0 !important;  /* Reduced margins */
        letter-spacing: -0.02em;
        position: relative;
    }
    
    h1::after {
        content: '';
        position: absolute;
        bottom: -8px;  /* Reduced from -10px */
        left: 50%;
        transform: translateX(-50%);
        width: 80px;  /* Reduced from 100px */
        height: 2px;  /* Reduced from 3px */
        background: var(--accent-gradient);
        border-radius: 2px;
    }
    
    h2, h3, h4, h5, h6 { 
        color: var(--text-primary) !important; 
        font-weight: 700; 
        letter-spacing: -0.01em;
        margin-top: 1rem !important;  /* Reduced from 2rem */
        margin-bottom: 0.5rem !important;  /* Added for better spacing */
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
    
    /* Premium Cards & Containers - COMPACT VERSION */
    div[data-testid="stVerticalBlockBorderWrapper"] { 
        background: var(--surface-card);
        border-radius: 12px;
        padding: 1rem;  /* Reduced from 2rem */
        border: 1px solid var(--border-subtle);
        box-shadow: var(--shadow-soft);
        margin-bottom: 1rem;  /* Reduced from 2rem */
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
    
    /* Premium Input Fields - COMPACT VERSION */
    .stTextInput input, .stTextArea textarea { 
        background: rgba(255, 255, 255, 0.95) !important;
        color: #000000 !important;
        border: 2px solid var(--border-subtle) !important;
        border-radius: 8px !important;  /* Reduced from 12px */
        font-weight: 500 !important;
        font-size: 0.9rem !important;  /* Reduced from 1rem */
        padding: 0.75rem !important;  /* Reduced from 1rem */
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
    
    /* Premium Buttons - COMPACT VERSION */
    .stButton > button, .stDownloadButton > button {
        background: var(--surface-elevated) !important;
        border: 2px solid var(--border-subtle) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;  /* Reduced from 0.95rem */
        padding: 0.6rem 1.2rem !important;  /* Reduced from 0.875rem 1.5rem */
        border-radius: 8px !important;  /* Reduced from 12px */
        box-shadow: var(--shadow-soft) !important;
        width: 100% !important;
        margin-bottom: 0.5rem !important;  /* Reduced from 0.75rem */
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(10px);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(102, 126, 234, 0.3) !important;
        border-color: #667eea !important;
    }
    
    /* Primary Buttons (Special Gradient) - COMPACT VERSION */
    .stButton button[kind="primary"] { 
        background: var(--primary-gradient) !important;
        border: none !important;
        color: white !important;
        font-weight: 700 !important;
        font-size: 1rem !important;  /* Reduced from 1.1rem */
        padding: 1rem 1.5rem !important;  /* Reduced from 1.25rem 2rem */
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
    
    /* Premium Layout & Spacing - COMPACT VERSION */
    .block-container {
        padding-top: 1rem !important;  /* Reduced from 2rem */
        padding-bottom: 1rem !important;  /* Reduced from 2rem */
        max-width: 1200px !important;
        padding-left: 1.5rem !important;  /* Reduced from 2rem */
        padding-right: 1.5rem !important;  /* Reduced from 2rem */
    }
    
    div[data-testid="column"] {
        gap: 1rem;  /* Reduced from 1.5rem */
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
    
    /* Hide Streamlit Branding - ENHANCED */
    header[data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        position: absolute !important;
        top: -9999px !important;
    }
    
    footer {
        display: none !important;
        visibility: hidden !important;
    }
    
    #MainMenu {
        visibility: hidden !important;
        display: none !important;
    }
    
    .stDeployButton {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Hide hamburger menu */
    button[title="View fullscreen"] {
        display: none !important;
    }
    
    /* Hide settings menu */
    button[aria-label="Settings"] {
        display: none !important;
    }
    
    /* Hide "Made with Streamlit" */
    .viewerBadge_container__1QSob {
        display: none !important;
    }
    
    .viewerBadge_link__1S137 {
        display: none !important;
    }
    
    /* Hide toolbar */
    .stToolbar {
        display: none !important;
    }
    
    /* Hide status widget */
    .stStatusWidget {
        display: none !important;
    }
    
    /* Hide any remaining Streamlit branding */
    [data-testid="stToolbar"] {
        display: none !important;
    }
    
    [data-testid="stDecoration"] {
        display: none !important;
    }
    
    [data-testid="stStatusWidget"] {
        display: none !important;
    }
    
    /* Hide top padding that might show menu space */
    .main .block-container {
        padding-top: 1rem !important;
    }
    
    /* Force hide any menu-related elements */
    .css-1d391kg, .css-1v0mbdj, .css-18e3th9, .css-1dp5vir {
        display: none !important;
    }
    
    /* Hide any floating elements */
    .stFloatingContainer {
        display: none !important;
    }
    
    /* Additional menu hiding */
    .stApp > header {
        display: none !important;
    }
    
    .stApp > div[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* Hide any remaining top elements */
    .element-container:first-child {
        margin-top: 0 !important;
    }
    
    /* Premium Mobile Responsiveness - COMPACT VERSION */
    @media (max-width: 768px) {
        .block-container {
            padding: 0.5rem !important;  /* Reduced from 1rem */
        }
        
        h1 {
            font-size: 1.5rem !important;  /* Reduced from 2rem */
        }
        
        div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 0.75rem !important;  /* Reduced from 1.5rem */
            margin-bottom: 0.75rem !important;  /* Reduced from 1.5rem */
        }
        
        .stButton > button {
            min-height: 40px !important;  /* Reduced from 50px */
            font-size: 0.85rem !important;  /* Reduced from 1rem */
        }
        
        div[data-testid="column"] {
            gap: 0.5rem !important;  /* Reduced from 1rem */
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
    
    /* File Uploader Styling - BLACK TEXT */
    .stFileUploader > div > div {
        color: #000000 !important;
    }
    
    .stFileUploader label {
        color: #ffffff !important;
    }
    
    /* File uploader drag and drop area */
    .stFileUploader > div > div > div {
        color: #000000 !important;
    }
    
    /* File uploader text elements */
    .stFileUploader span,
    .stFileUploader p,
    .stFileUploader div {
        color: #000000 !important;
    }
    
    /* Specific targeting for file uploader content */
    [data-testid="stFileUploader"] * {
        color: #000000 !important;
    }
    
    /* File uploader drag area styling */
    [data-testid="stFileUploader"] > div > div {
        background: rgba(255, 255, 255, 0.95) !important;
        border: 2px dashed #cccccc !important;
        border-radius: 12px !important;
        color: #000000 !important;
    }
    
    /* File uploader hover state */
    [data-testid="stFileUploader"] > div > div:hover {
        border-color: #667eea !important;
        background: rgba(255, 255, 255, 0.98) !important;
    }
    
    /* Force all text in file uploader to be black */
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] p,
    [data-testid="stFileUploader"] div,
    [data-testid="stFileUploader"] small {
        color: #000000 !important;
    }
    
    /* NUCLEAR OPTION - Force all file uploader text to black */
    .stFileUploader * {
        color: #000000 !important;
    }
    
    /* Target specific file uploader elements */
    .stFileUploader [data-baseweb="file-uploader"] * {
        color: #000000 !important;
    }
    
    /* Override any Streamlit default colors for file uploader */
    section[data-testid="stFileUploader"] * {
        color: #000000 !important;
    }
    
    /* File uploader inner content */
    .stFileUploader > div * {
        color: #000000 !important;
    }
    
    /* Drag and drop text specifically */
    .stFileUploader [role="button"] * {
        color: #000000 !important;
    }
    
    /* File uploader label text - force black */
    .stFileUploader label * {
        color: #000000 !important;
    }
    
    /* Additional targeting for file uploader labels */
    [data-testid="stFileUploader"] label {
        color: #ffffff !important;
    }
    
    [data-testid="stFileUploader"] label * {
        color: #000000 !important;
    }
    
    /* Code elements styling - ensure black text */
    code {
        color: #000000 !important;
        background: #f0f0f0 !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
    }
</style>
"""
st.markdown(streamlit_style, unsafe_allow_html=True)

# JavaScript to hide any remaining menu elements - IMMEDIATE EXECUTION
hide_menu_js = """
<script>
// IMMEDIATE EXECUTION - 페이지 로딩 즉시 실행
(function() {
    'use strict';
    
    function hideMenuElements() {
        const elementsToHide = [
            'header[data-testid="stHeader"]',
            '#MainMenu',
            '.stDeployButton',
            'button[title="View fullscreen"]',
            'button[aria-label="Settings"]',
            '.viewerBadge_container__1QSob',
            '.viewerBadge_link__1S137',
            '.stToolbar',
            '.stStatusWidget',
            '[data-testid="stToolbar"]',
            '[data-testid="stDecoration"]',
            '[data-testid="stStatusWidget"]',
            '.stFloatingContainer',
            '.css-1d391kg',
            '.css-1v0mbdj', 
            '.css-18e3th9',
            '.css-1dp5vir'
        ];
        
        elementsToHide.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                element.style.display = 'none';
                element.style.visibility = 'hidden';
                element.style.opacity = '0';
                element.style.height = '0';
                element.style.position = 'absolute';
                element.style.top = '-9999px';
                element.style.zIndex = '-9999';
            });
        });
        
        // Remove any remaining top padding
        const mainContainer = document.querySelector('.main .block-container');
        if (mainContainer) {
            mainContainer.style.paddingTop = '1rem';
        }
    }
    
    // Execute immediately
    hideMenuElements();
    
    // Execute when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', hideMenuElements);
    } else {
        hideMenuElements();
    }
    
    // Execute when page is fully loaded
    window.addEventListener('load', hideMenuElements);
    
    // Run very frequently to catch any dynamically loaded elements
    const intervalId = setInterval(hideMenuElements, 10); // Every 10ms for first few seconds
    
    // After 5 seconds, reduce frequency to save resources
    setTimeout(() => {
        clearInterval(intervalId);
        setInterval(hideMenuElements, 100); // Every 100ms after that
    }, 5000);
    
    // Also hide on any mutation
    if (typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver(hideMenuElements);
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['style', 'class']
        });
    }
})();
</script>
"""
st.markdown(hide_menu_js, unsafe_allow_html=True)

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

# 모바일 세션 복원 (페이지 로드 시 한 번만 실행) - 완전 자동화 버전
if MOBILE_OPTIMIZATION_AVAILABLE and "session_restored" not in st.session_state:
    try:
        # 이전 세션 복원 시도
        restored_session = mobile_session_manager.restore_session()
        
        if restored_session:
            task_id = restored_session.get("task_id")
            
            if task_id:
                # 작업 상태 확인
                task_status = mobile_session_manager.get_active_task_status(task_id)
                
                if task_status:
                    # 세션 상태 복원
                    st.session_state["current_task_id"] = task_id
                    st.session_state["generation_start_time"] = restored_session.get("start_time", time.time())
                    
                    if task_status["is_active"]:
                        st.session_state["generation_in_progress"] = True
                        st.session_state["auto_restored"] = True
                        
                        # 화면 껐다 켜기 복원 알림 (더 명확하게)
                        elapsed = int(time.time() - restored_session.get("start_time", time.time()))
                        st.success(f"📱 화면 복원: 영상 생성 진행 중 ({task_status['progress']}%, {elapsed//60}분 경과)")
                        
                    elif task_status.get("video_file"):
                        st.session_state["generation_in_progress"] = False
                        st.session_state["completed_video_file"] = task_status["video_file"]
                        st.success("✅ 화면 복원: 완료된 영상을 찾았습니다!")
                    else:
                        st.session_state["generation_in_progress"] = False
                        st.info("ℹ️ 이전 작업 기록을 복원했습니다.")
                else:
                    # 작업 상태를 찾을 수 없어도 세션 정보는 복원
                    st.session_state["current_task_id"] = task_id
                    st.session_state["generation_start_time"] = restored_session.get("start_time", time.time())
                    
                    # 더 자세한 상태 정보 제공
                    elapsed = int(time.time() - restored_session.get("start_time", time.time()))
                    st.info(f"📱 이전 세션을 복원했습니다 ({elapsed//60}분 전 시작). 작업이 완료되었거나 중단되었을 수 있습니다.")
            else:
                st.info("ℹ️ 이전 세션 기록이 있지만 진행 중인 작업은 없습니다.")
        else:
            # 복원할 세션이 없는 경우 (정상적인 첫 방문)
            logger.info("No previous session found - starting fresh")
        
        # 오래된 세션 정리
        mobile_session_manager.cleanup_old_sessions()
        
    except Exception as e:
        logger.error(f"Session restoration failed: {e}")
    
    st.session_state["session_restored"] = True

# 자동 복원된 진행 중인 작업 실시간 모니터링 - 깜빡임 없는 버전
if st.session_state.get("generation_in_progress", False) and st.session_state.get("auto_restored", False):
    task_id = st.session_state.get("current_task_id")
    
    if task_id:
        # 진행률 표시
        task_status = mobile_session_manager.get_active_task_status(task_id)
        if task_status and task_status.get('progress', 0) < 100:
            # 진행 중인 작업 표시
            st.markdown("""
            <div class="mobile-progress">
                <h4>🔄 영상 생성 진행 중</h4>
                <p>백그라운드에서 영상 생성이 계속 진행되고 있습니다.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 실시간 진행률 바 (깜빡임 방지)
            progress = task_status.get('progress', 0)
            message = task_status.get('message', '진행 중...')
            
            # 진행률 표시 (부드러운 애니메이션)
            st.markdown(f"""
            <div style="margin: 1rem 0;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                    <span><strong>진행률: {progress}%</strong></span>
                    <span style="color: #666;">{message}</span>
                </div>
                <div style="background: #f0f0f0; border-radius: 10px; height: 20px; overflow: hidden;">
                    <div style="
                        background: linear-gradient(90deg, #4CAF50, #45a049);
                        height: 100%;
                        width: {progress}%;
                        transition: width 2s ease-in-out;
                        border-radius: 10px;
                    "></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 경과 시간 표시
            start_time = st.session_state.get("generation_start_time", time.time())
            elapsed = int(time.time() - start_time)
            st.write(f"⏱️ 경과 시간: {elapsed//60}분 {elapsed%60}초")
            
            # 수동 새로고침 버튼만 제공 (자동 새로고침 제거)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 진행률 확인", use_container_width=True, key="refresh_progress"):
                    st.rerun()
            with col2:
                if st.button("⏹️ 작업 중단", use_container_width=True, key="stop_task"):
                    st.session_state["generation_in_progress"] = False
                    st.session_state["auto_restored"] = False
                    st.warning("작업이 중단되었습니다.")
                    st.rerun()
            
            # 부드러운 자동 업데이트 (JavaScript 없이)
            st.markdown("""
            <div style="text-align: center; margin-top: 1rem; color: #666; font-size: 0.9rem;">
                💡 진행률을 확인하려면 '🔄 진행률 확인' 버튼을 눌러주세요
            </div>
            """, unsafe_allow_html=True)
            
            # ngrok 환경에서 연결 상태 표시
            if "ngrok" in st.get_option("server.baseUrlPath") or "ngrok" in str(st.session_state.get("server_url", "")):
                st.markdown("""
                <div class="ngrok-status">
                    🌐 ngrok 터널 연결됨
                </div>
                """, unsafe_allow_html=True)
                
                # 연결 안정성 체크
                import requests
                try:
                    # 간단한 연결 테스트 (타임아웃 3초)
                    response = requests.get(f"{st.get_option('server.baseUrlPath')}/health", timeout=3)
                    if response.status_code != 200:
                        st.warning("⚠️ 네트워크 연결이 불안정합니다. 새로고침을 시도해보세요.")
                except:
                    st.error("❌ 네트워크 연결에 문제가 있습니다. ngrok 터널을 확인해주세요.")
            
        elif task_status and task_status.get('progress', 0) >= 100:
            # 완료된 경우 자동으로 완료 상태로 전환
            st.session_state["generation_in_progress"] = False
            st.session_state["auto_restored"] = False
            if task_status.get("video_file"):
                st.session_state["completed_video_file"] = task_status["video_file"]
                st.success("🎉 영상 생성이 완료되었습니다!")
            st.rerun()
        else:
            # 작업을 찾을 수 없는 경우
            st.warning("⚠️ 진행 중인 작업을 찾을 수 없습니다.")
            st.session_state["generation_in_progress"] = False
            st.session_state["auto_restored"] = False

# 영상 생성 시 자동으로 세션 저장
def save_generation_session(task_id: str, subject: str):
    """영상 생성 시작 시 세션 자동 저장"""
    try:
        params = {
            "video_subject": subject,
            "video_type": "shorts",
            "start_time": time.time()
        }
        mobile_session_manager.save_generation_state(task_id, params)
        st.session_state["current_task_id"] = task_id
        st.session_state["generation_in_progress"] = True
        logger.info(f"Auto-saved generation session: {task_id}")
    except Exception as e:
        logger.error(f"Failed to save generation session: {e}")
# 세션복원디버깅 코드 제거됨 - 자동 복원만 사용

if "video_subject" not in st.session_state:
    st.session_state["video_subject"] = ""
if "video_script" not in st.session_state:
    st.session_state["video_script"] = ""
if "video_terms" not in st.session_state:
    st.session_state["video_terms"] = ""
if "ui_language" not in st.session_state:
    st.session_state["ui_language"] = config.ui.get("language", system_locale)

# 쇼츠 최적화 기본 설정 적용 (페이지 첫 로드 시)
if "shorts_optimization_applied" not in st.session_state:
    # 쇼츠 최적화 설정 자동 적용
    if config.app.get("pexels_api_keys"):
        st.session_state["settings_video_source"] = 0
    elif config.app.get("pixabay_api_keys"):
        st.session_state["settings_video_source"] = 1
    else:
        st.session_state["settings_video_source"] = 2
    
    st.session_state["settings_video_aspect"] = 0  # Portrait
    st.session_state["settings_video_concat"] = 0  # Sequential - 자막과 영상 매칭
    st.session_state["settings_video_transition"] = 1  # Shuffle
    st.session_state["settings_clip_duration"] = 3
    st.session_state["settings_video_count"] = 1
    st.session_state["settings_voice_rate"] = 1.2  # 최적화된 템포
    st.session_state["settings_voice_volume"] = 1.0
    st.session_state["settings_korean_speed_boost"] = 1.3  # 한국어 1.3배속
    st.session_state["settings_english_speed_boost"] = 1.1  # 영어 1.1배속
    st.session_state["settings_bgm_type"] = 1
    st.session_state["settings_bgm_volume"] = 0.05
    st.session_state["settings_subtitle_enabled"] = True
    st.session_state["settings_subtitle_position"] = 2
    st.session_state["settings_font_color"] = "#FFFFFF"
    st.session_state["settings_stroke_color"] = "#000000"
    st.session_state["settings_font_size"] = 50
    st.session_state["settings_stroke_width"] = 3.0
    
    config.ui["font_size"] = 50
    config.ui["text_fore_color"] = "#FFFFFF"
    
    # 한 번만 적용되도록 플래그 설정
    st.session_state["shorts_optimization_applied"] = True

# 로케일 로드 (유지)
locales = utils.load_locales(i18n_dir)

# 언어 설정 강제 고정 (한국어)
st.session_state["ui_language"] = "ko-KR"
config.ui["language"] = "ko-KR"

# 타이틀과 상태 표시
col_title, col_status = st.columns([0.7, 0.3])

with col_title:
    st.title("🎬 AI 영상 생성 스튜디오")
    st.markdown("**차세대 AI 기반 자동 영상 생성 플랫폼**")

with col_status:
    st.markdown("### 🚀 시스템 상태")
    
    # 할당량 체크 상태 관리
    if "quota_check_expanded" not in st.session_state:
        st.session_state["quota_check_expanded"] = False
    
    # 할당량 체크 버튼
    col_check_btn, col_close_btn = st.columns([0.7, 0.3])
    
    with col_check_btn:
        if st.button("🔍 API 할당량 체크", use_container_width=True, key="quota_check_btn"):
            st.session_state["quota_check_expanded"] = True
    
    with col_close_btn:
        if st.session_state["quota_check_expanded"]:
            if st.button("❌ 닫기", use_container_width=True, key="quota_close_btn"):
                st.session_state["quota_check_expanded"] = False
                st.rerun()
    
    # 할당량 정보 표시 (펼쳐진 상태일 때만)
    if st.session_state["quota_check_expanded"]:
        with st.spinner("API 할당량 확인 중..."):
            try:
                from app.services import llm
                quota_status = llm.check_api_quota_status()
                
                st.markdown("#### 📊 API 할당량 상태")
                
                # Gemini API 키들 상태
                st.markdown("**🤖 Gemini API 키 상태:**")
                available_gemini = 0
                for key_info in quota_status["gemini_keys"]:
                    if key_info["available"]:
                        available_gemini += 1
                        st.success(f"키 #{key_info['key_num']}: {key_info['status']} ({key_info['key_preview']})")
                    elif "미설정" in key_info["status"]:
                        st.info(f"키 #{key_info['key_num']}: {key_info['status']}")
                    else:
                        st.error(f"키 #{key_info['key_num']}: {key_info['status']} ({key_info['key_preview']})")
                
                # DeepSeek API 키 상태
                st.markdown("**🔧 DeepSeek API 키 상태:**")
                deepseek_info = quota_status["deepseek_status"]
                if deepseek_info["available"]:
                    st.success(f"DeepSeek: {deepseek_info['status']} ({deepseek_info['key_preview']})")
                elif "미설정" in deepseek_info["status"]:
                    st.info(f"DeepSeek: {deepseek_info['status']}")
                else:
                    st.error(f"DeepSeek: {deepseek_info['status']} ({deepseek_info['key_preview']})")
                
                # 전체 요약
                total_available = quota_status["total_available"]
                if total_available > 0:
                    st.success(f"✅ 총 {total_available}개 API 키 사용 가능")
                    if available_gemini > 0:
                        st.info(f"🤖 Gemini: {available_gemini}/10개 키 활성화")
                else:
                    st.error("❌ 사용 가능한 API 키가 없습니다!")
                    st.warning("💡 config.toml에서 API 키를 설정하거나 할당량을 확인하세요")
                
            except Exception as e:
                st.error(f"❌ 할당량 체크 실패: {str(e)}")
    else:
        # 기본 상태 표시 (접혀진 상태일 때)
        st.success("✅ Gemini 2.5 Flash 활성화")
        st.info("🔥 고속 생성 모드 준비완료")

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

# 모바일 진행 중인 작업 알림 (탭 위에 표시) - 개선된 버전
if MOBILE_OPTIMIZATION_AVAILABLE and st.session_state.get("generation_in_progress", False):
    current_task_id = st.session_state.get("current_task_id")
    if current_task_id:
        try:
            task_status = mobile_session_manager.get_active_task_status(current_task_id)
            if task_status and task_status["is_active"]:
                elapsed_time = time.time() - st.session_state.get("generation_start_time", time.time())
                progress = task_status.get('progress', 0)
                message = task_status.get('message', '진행 중...')
                
                # 상세한 진행 상황 표시
                st.markdown(f"""
                <div class="mobile-progress">
                    <h4>🎬 영상 생성 진행 중</h4>
                    <p><strong>진행률:</strong> {progress}%</p>
                    <p><strong>상태:</strong> {message}</p>
                    <p><strong>경과 시간:</strong> {int(elapsed_time//60)}분 {int(elapsed_time%60)}초</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 진행률 바
                st.progress(progress / 100.0)
                
            elif task_status and task_status.get("video_file"):
                st.success("✅ 영상 생성이 완료되었습니다!")
                st.session_state["generation_in_progress"] = False
                
                # 완료된 영상 파일 정보 표시
                video_file = task_status["video_file"]
                if os.path.exists(video_file):
                    file_size = os.path.getsize(video_file) / (1024 * 1024)  # MB
                    st.info(f"📁 생성된 파일: {os.path.basename(video_file)} ({file_size:.1f}MB)")
                    
        except Exception as e:
            logger.error(f"Failed to check mobile task status: {e}")
            st.warning("⚠️ 진행 상황을 확인할 수 없습니다. 새로고침해보세요.")

# Premium Tab Design
tab_main, tab_settings, tab_analytics = st.tabs([
    "🎬 영상 생성", 
    "⚙️ 고급 설정", 
    "📊 분석 & 관리"
])

# --- TAB 1: MAIN (Generate) ---
with tab_main:
    # Hero Section - COMPACT VERSION
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0; margin-bottom: 1rem;">
        <h2 style="color: #667eea; margin-bottom: 0.5rem;">🚀 몇 초 만에 전문가급 영상을 생성하세요</h2>
        <p style="font-size: 1rem; color: #a0a0a0;">주제만 입력하면 AI가 대본, 음성, 영상, 자막을 자동으로 생성합니다</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Mobile optimization tips
    if MOBILE_OPTIMIZATION_AVAILABLE:
        show_mobile_generation_tips()
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
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            llm.generate_terms,
                            video_subject=params.video_subject,
                            video_script=script, 
                            amount=5
                        )
                        
                        for i in range(40):
                            if future.done():
                                break
                            time.sleep(0.1)
                            current_p = min(60 + int(i * 1), 90)
                            progress_bar.progress(current_p)
                            
                        terms = future.result()
                    
                    # Translate terms to English for better search results
                    if terms:
                        logger.info(f"Generated terms: {terms}")
                        # Terms are already in English from the improved generate_terms function
                    
                    if not terms:
                        terms = []

                    status_text.text("✅ 생성 완료!")
                    progress_bar.progress(100)
                    time.sleep(0.5)
                    
                    st.session_state["video_script"] = script
                    st.session_state["video_terms"] = ", ".join(terms) if terms else ""
                    
                    progress_container.empty()
                    st.success("🎉 AI가 완벽한 대본과 키워드를 생성했습니다!")
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
                st.session_state["settings_video_concat"] = 0  # Sequential - 자막과 영상 매칭
                st.session_state["settings_video_transition"] = 1  # Shuffle
                st.session_state["settings_clip_duration"] = 3
                st.session_state["settings_video_count"] = 1
                st.session_state["settings_voice_rate"] = 1.2
                st.session_state["settings_voice_volume"] = 1.0
                st.session_state["settings_korean_speed_boost"] = 1.3  # 한국어 1.3배속
                st.session_state["settings_english_speed_boost"] = 1.1  # 영어 1.1배속
                st.session_state["settings_bgm_type"] = 1
                st.session_state["settings_bgm_volume"] = 0.05
                st.session_state["settings_subtitle_enabled"] = True
                st.session_state["settings_subtitle_position"] = 2
                st.session_state["settings_font_color"] = "#FFFFFF"
                st.session_state["settings_stroke_color"] = "#000000"
                st.session_state["settings_font_size"] = 50
                st.session_state["settings_stroke_width"] = 3.0
                
                config.ui["font_size"] = 50
                config.ui["text_fore_color"] = "#FFFFFF"
                
                st.success("✅ 쇼츠 최적화 설정 완료!")
                st.info("📱 9:16 세로 비율, 최적화된 템포(1.2배속), 큰 자막, 자막-영상 매칭으로 설정되었습니다 (한국어 1.3배속, 영어 1.1배속)")
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
                    value=True, 
                    help="한국어 영상 생성 후, 영어 자막/성우가 적용된 글로벌 버전을 추가로 생성합니다."
                )
            with col_gen_opt2:
                auto_upload = st.checkbox(
                    "📺 자동 업로드", 
                    value=True,
                    key="yt_auto_upload",
                    help="영상 생성 완료 후 자동으로 YouTube에 업로드합니다."
                )
            
            # 쿠팡파트너스 섹션 추가
            st.markdown("---")
            st.markdown("#### 🛒 **쿠팡파트너스 연동**")
            
            col_coupang_enable, col_coupang_links = st.columns([0.3, 0.7])
            
            with col_coupang_enable:
                enable_coupang = st.checkbox(
                    "🛍️ 제품 오버레이 활성화",
                    value=False,
                    key="enable_coupang_overlay",
                    help="영상에 쿠팡 제품 이미지를 오버레이로 추가합니다"
                )
            
            with col_coupang_links:
                if enable_coupang:
                    coupang_links = st.text_area(
                        "쿠팡 제품 링크 (한 줄에 하나씩)",
                        placeholder="https://coupa.ng/xxxxx\nhttps://www.coupang.com/vp/products/xxxxx\n\n최대 3개까지 추가 가능합니다",
                        height=100,
                        key="coupang_links_input",
                        help="쿠팡 제품 링크를 한 줄에 하나씩 입력하세요. 단축링크(coupa.ng)와 일반링크 모두 지원합니다."
                    )
                    
                    # 링크 검증 및 미리보기
                    if coupang_links.strip():
                        links_list = [link.strip() for link in coupang_links.split('\n') if link.strip()]
                        
                        if len(links_list) > 3:
                            st.warning("⚠️ 최대 3개까지만 처리됩니다. 처음 3개 링크만 사용됩니다.")
                            links_list = links_list[:3]
                        
                        # 링크 형식 검증
                        valid_links = []
                        for link in links_list:
                            if 'coupang.com' in link or 'coupa.ng' in link:
                                valid_links.append(link)
                            else:
                                st.error(f"❌ 유효하지 않은 쿠팡 링크: {link}")
                        
                        if valid_links:
                            st.success(f"✅ {len(valid_links)}개의 유효한 쿠팡 링크가 설정되었습니다")
                            
                            # 제품 정보 미리보기 (선택사항)
                            if st.button("🔍 제품 정보 미리보기", key="preview_products"):
                                with st.spinner("제품 정보를 가져오는 중..."):
                                    try:
                                        from app.services.coupang_partners import get_coupang_manager
                                        coupang_manager = get_coupang_manager()
                                        
                                        for i, link in enumerate(valid_links[:2]):  # 최대 2개만 미리보기
                                            product_info = coupang_manager.extract_product_info_from_coupang_url(link)
                                            
                                            col_preview_img, col_preview_info = st.columns([0.3, 0.7])
                                            
                                            with col_preview_img:
                                                if product_info.get('image_url'):
                                                    st.image(product_info['image_url'], width=100)
                                                else:
                                                    st.write("🖼️ 이미지 없음")
                                            
                                            with col_preview_info:
                                                st.write(f"**{product_info.get('name', '제품명 없음')}**")
                                                st.write(f"💰 {product_info.get('price', '가격 정보 없음')}")
                                                st.write(f"⭐ {product_info.get('rating', '평점 정보 없음')}")
                                            
                                            if i < len(valid_links) - 1:
                                                st.markdown("---")
                                    
                                    except Exception as e:
                                        st.error(f"❌ 제품 정보 가져오기 실패: {str(e)}")
                else:
                    st.info("💡 제품 오버레이를 활성화하면 쿠팡 제품 링크를 추가할 수 있습니다")
            
            # Main generation button
            start_button = st.button(
                "🎬 AI 영상 생성 시작", 
                use_container_width=True, 
                type="primary",
                help="모든 설정을 확인한 후 영상 생성을 시작합니다."
            )
            
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
        
        # Timer Channel Authentication
        st.markdown("#### 📺 **타이머 전용 채널 설정**")
        col_auth_timer, col_status_timer = st.columns([0.5, 0.5])
        
        timer_token_file = os.path.join(root_dir, "token_timer.pickle")
        client_secrets_file = os.path.join(root_dir, "client_secrets.json")
        
        with col_auth_timer:
            if st.button("🔐 타이머 채널 인증", key="auth_timer_channel", use_container_width=True):
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
        
        # Timer Configuration
        col_timer_config, col_timer_generate = st.columns([0.6, 0.4])
        
        with col_timer_config:
            st.markdown("#### ⏰ **타이머 설정**")
            
            col_duration, col_style = st.columns(2)
            with col_duration:
                timer_duration = st.number_input(
                    "타이머 시간 (분)", 
                    min_value=1, 
                    max_value=120, 
                    value=5, 
                    step=1, 
                    key="timer_duration_input",
                    help="1분부터 120분까지 설정 가능합니다."
                )
            
            with col_style:
                timer_style = st.selectbox(
                    "타이머 스타일",
                    ["⚫ 미니멀 (검은배경)", "🌅 자연 배경", "🎨 추상 배경"],
                    index=1,  # 자연 배경을 기본값으로 설정
                    key="timer_style_select"
                )
            
            # Advanced timer options
            col_fast, col_music = st.columns(2)
            with col_fast:
                fast_mode = st.checkbox(
                    "⚡ 고속 렌더링", 
                    value=True, 
                    help="720p/24fps로 빠르게 렌더링합니다."
                )
            with col_music:
                music_option = st.selectbox(
                    "🎵 배경음악",
                    ["🚫 없음", "📁 로컬 파일", "🌐 온라인 무료음악"],
                    index=2,  # 온라인 무료음악을 기본값으로
                    help="배경음악 소스를 선택하세요."
                )
        
        with col_timer_generate:
            st.markdown("#### 🚀 **생성 시작**")
            st.markdown(f"**예상 영상 길이:** {timer_duration}분")
            st.markdown(f"**예상 생성 시간:** {timer_duration * 0.3:.1f}분")
            
            # Auto-upload checkbox
            timer_auto_upload_main = st.checkbox(
                "📤 생성 후 YouTube 자동 업로드", 
                value=st.session_state.get("timer_auto_upload", True),
                key="timer_auto_upload_main",
                help="체크하면 타이머 영상 생성 완료 즉시 YouTube에 자동 업로드됩니다"
            )
            
            if st.button("⏱️ 타이머 영상 생성", use_container_width=True, key="timer_generate_btn", type="primary"):
                # Timer generation logic (existing code with improvements)
                timer_seconds = timer_duration * 60
                
                task_id = str(uuid4())
                output_dir = os.path.join(root_dir, "storage", "tasks", task_id)
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, f"timer_video_{int(time.time())}.mp4")
                
                status_container = st.container()
                with status_container:
                    status_text = st.empty()
                    progress_bar = st.progress(0)
                    
                    try:
                        status_text.info(f"🎬 {timer_duration}분 타이머 영상 생성 시작...")
                        logger.info(f"Starting timer generation: {timer_duration} minutes, output: {output_file}")
                        logger.info(f"Timer style selected: {timer_style}")
                        
                        from app.services import video, material
                        
                        bg_video_path = None
                        
                        # Background selection based on style
                        if "자연" in timer_style:
                            status_text.info("🌿 자연 배경 영상 검색 중...")
                            bg_video_path = None
                            max_retries = 3
                            
                            for attempt in range(max_retries):
                                try:
                                    from app.services import material
                                    # Search for nature background videos with more variety
                                    search_terms = [
                                        "nature", "forest", "ocean", "mountain", "landscape", 
                                        "waterfall", "river", "lake", "sunset", "sunrise",
                                        "clouds", "sky", "beach", "trees", "flowers",
                                        "grass", "meadow", "valley", "canyon", "desert",
                                        "snow", "winter", "spring", "autumn", "rain"
                                    ]
                                    search_term = random.choice(search_terms)
                                    status_text.info(f"🌿 '{search_term}' 테마 영상 검색 중... (시도 {attempt + 1}/{max_retries})")
                                    
                                    materials = material.search_videos_pexels(search_term, 3, VideoAspect.portrait)  # 3개 검색
                                    if materials:
                                        # 랜덤하게 하나 선택
                                        selected_material = random.choice(materials)
                                        status_text.info(f"🌿 자연 배경 영상 다운로드 중: '{search_term}' 테마")
                                        bg_video_path = material.save_video(selected_material.url)
                                        if bg_video_path and os.path.exists(bg_video_path):
                                            # Verify video file is valid
                                            try:
                                                from moviepy.video.io.VideoFileClip import VideoFileClip
                                                test_clip = VideoFileClip(bg_video_path)
                                                # Test if we can read the first frame
                                                test_frame = test_clip.get_frame(0)
                                                test_clip.close()
                                                status_text.success(f"✅ 자연 배경 영상 준비 완료: {search_term}")
                                                break
                                            except Exception as video_error:
                                                logger.warning(f"Downloaded video is corrupted: {video_error}")
                                                # Try to delete corrupted file
                                                try:
                                                    os.remove(bg_video_path)
                                                except:
                                                    pass
                                                bg_video_path = None
                                                continue
                                except Exception as e:
                                    logger.warning(f"자연 배경 검색 시도 {attempt + 1} 실패: {e}")
                                    if attempt == max_retries - 1:
                                        status_text.error("❌ 자연 배경 검색 실패, 미니멀 배경으로 대체")
                                    else:
                                        status_text.info(f"🔄 다른 테마로 재시도 중...")
                        elif "추상" in timer_style:
                            status_text.info("🎨 추상 배경 영상 검색 중...")
                            bg_video_path = None
                            max_retries = 3
                            
                            for attempt in range(max_retries):
                                try:
                                    from app.services import material
                                    # Search for abstract background videos with more variety
                                    search_terms = [
                                        "abstract", "geometric", "gradient", "particles", "motion graphics",
                                        "fluid", "liquid", "smoke", "fire", "light", "neon",
                                        "digital", "cyber", "space", "galaxy", "nebula",
                                        "waves", "ripple", "texture", "pattern", "kaleidoscope",
                                        "fractal", "crystal", "glass", "metal", "holographic"
                                    ]
                                    search_term = random.choice(search_terms)
                                    status_text.info(f"🎨 '{search_term}' 테마 영상 검색 중... (시도 {attempt + 1}/{max_retries})")
                                    
                                    materials = material.search_videos_pexels(search_term, 3, VideoAspect.portrait)  # 3개 검색
                                    if materials:
                                        # 랜덤하게 하나 선택
                                        selected_material = random.choice(materials)
                                        status_text.info(f"🎨 추상 배경 영상 다운로드 중: '{search_term}' 테마")
                                        bg_video_path = material.save_video(selected_material.url)
                                        if bg_video_path and os.path.exists(bg_video_path):
                                            # Verify video file is valid
                                            try:
                                                from moviepy.video.io.VideoFileClip import VideoFileClip
                                                test_clip = VideoFileClip(bg_video_path)
                                                # Test if we can read the first frame
                                                test_frame = test_clip.get_frame(0)
                                                test_clip.close()
                                                status_text.success(f"✅ 추상 배경 영상 준비 완료: {search_term}")
                                                break
                                            except Exception as video_error:
                                                logger.warning(f"Downloaded video is corrupted: {video_error}")
                                                # Try to delete corrupted file
                                                try:
                                                    os.remove(bg_video_path)
                                                except:
                                                    pass
                                                bg_video_path = None
                                                continue
                                except Exception as e:
                                    logger.warning(f"추상 배경 검색 시도 {attempt + 1} 실패: {e}")
                                    if attempt == max_retries - 1:
                                        status_text.error("❌ 추상 배경 검색 실패, 미니멀 배경으로 대체")
                                    else:
                                        status_text.info(f"🔄 다른 테마로 재시도 중...")
                        else:
                            status_text.info("⚫ 미니멀 배경으로 설정...")
                        
                        # Background music selection
                        bg_music_path = None
                        if music_option == "📁 로컬 파일":
                            # Use local music files
                            song_dir = os.path.join(root_dir, "resource", "songs")
                            songs = glob.glob(os.path.join(song_dir, "*.mp3"))
                            if songs:
                                bg_music_path = random.choice(songs)
                                status_text.info(f"🎵 로컬 음악 선택됨")
                            else:
                                status_text.warning("⚠️ 로컬 음악 파일이 없어 온라인 음악을 사용합니다")
                                music_option = "🌐 온라인 무료음악"
                        
                        if music_option == "🌐 온라인 무료음악":
                            # Try to download free music from Pixabay
                            status_text.info("🌐 Pixabay에서 무료 배경음악 검색 중...")
                            bg_music_path = None
                            
                            try:
                                from app.services import material
                                
                                # Check if Pixabay API key is configured
                                pixabay_keys = config.app.get("pixabay_api_keys", [])
                                if not pixabay_keys or pixabay_keys == ["YOUR_PIXABAY_API_KEY_HERE"]:
                                    status_text.warning("⚠️ Pixabay API 키가 설정되지 않았습니다. 로컬 음악을 사용합니다.")
                                    raise ValueError("Pixabay API key not configured")
                                
                                # Search terms based on timer style
                                if "자연" in timer_style:
                                    music_terms = ["nature", "ambient", "forest", "peaceful", "meditation", "calm"]
                                elif "추상" in timer_style:
                                    music_terms = ["electronic", "ambient", "synthesizer", "modern", "digital", "abstract"]
                                else:
                                    music_terms = ["minimal", "ambient", "calm", "focus", "concentration", "simple"]
                                
                                search_term = random.choice(music_terms)
                                status_text.info(f"🎵 '{search_term}' 테마 음악 검색 중...")
                                
                                music_list = material.search_free_music(search_term, timer_duration)
                                if music_list:
                                    selected_music = random.choice(music_list)
                                    status_text.info(f"🎵 음악 다운로드 중: {selected_music.get('name', 'Unknown')}")
                                    bg_music_path = material.save_music(selected_music.get('url'))
                                    
                                    if bg_music_path and os.path.exists(bg_music_path):
                                        status_text.success(f"✅ Pixabay 무료 음악 준비 완료")
                                    else:
                                        raise ValueError("Music download failed")
                                else:
                                    raise ValueError("No music found on Pixabay")
                                    
                            except Exception as e:
                                logger.error(f"Failed to get Pixabay music: {e}")
                                status_text.info("🎵 로컬 음악으로 대체합니다...")
                                # Fallback to local music
                                song_dir = os.path.join(root_dir, "resource", "songs")
                                songs = glob.glob(os.path.join(song_dir, "*.mp3"))
                                if songs:
                                    bg_music_path = random.choice(songs)
                                    status_text.success(f"✅ 로컬 배경음악 선택됨")
                                else:
                                    status_text.warning("⚠️ 배경음악 파일이 없어 음악 없이 진행")
                                    bg_music_path = None
                        
                        # Generate timer video
                        logger.info("Calling generate_timer_video function...")
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                video.generate_timer_video, 
                                timer_seconds, 
                                output_file, 
                                None, 
                                250, 
                                bg_video_path, 
                                bg_music_path, 
                                fast_mode, 
                                timer_style,
                                None  # Remove progress_callback to avoid NoSessionContext error
                            )
                            
                            # Enhanced progress tracking with time estimation
                            start_time = time.time()
                            estimated_duration = timer_duration * 0.3 * 60  # Estimated time in seconds (0.3 minutes per timer minute)
                            
                            # Progress messages for different stages
                            progress_messages = [
                                "🎬 타이머 영상 렌더링 시작...",
                                "🎨 배경 영상 처리 중...",
                                "🎵 배경음악 동기화 중...",
                                "⏰ 타이머 오버레이 생성 중...",
                                "🔄 프레임 합성 중...",
                                "💾 최종 영상 저장 중...",
                                "✨ 마무리 작업 중..."
                            ]
                            
                            message_index = 0
                            last_message_time = start_time
                            
                            while not future.done():
                                elapsed_time = time.time() - start_time
                                
                                # Calculate progress with better distribution
                                if elapsed_time < estimated_duration * 0.8:
                                    # First 80% of estimated time -> 0-90% progress
                                    estimated_progress = (elapsed_time / (estimated_duration * 0.8)) * 0.9
                                else:
                                    # Remaining time -> 90-95% progress, then detailed final steps
                                    base_progress = 0.9
                                    remaining_progress = 0.05
                                    overtime_factor = (elapsed_time - estimated_duration * 0.8) / (estimated_duration * 0.2)
                                    estimated_progress = base_progress + (remaining_progress * min(overtime_factor, 1.0))
                                
                                progress_percentage = int(estimated_progress * 100)
                                progress_bar.progress(estimated_progress)
                                
                                # Change message every 10 seconds or when reaching certain progress points
                                if (time.time() - last_message_time > 10) or (progress_percentage >= 90 and message_index < len(progress_messages) - 1):
                                    message_index = min(message_index + 1, len(progress_messages) - 1)
                                    last_message_time = time.time()
                                
                                # Show different messages based on progress
                                if progress_percentage < 95:
                                    status_text.info(f"{progress_messages[min(message_index, 4)]} {progress_percentage}%")
                                else:
                                    # Final stage messages with animation
                                    dots = "." * ((int(elapsed_time) % 3) + 1)
                                    remaining_time = max(0, int(estimated_duration - elapsed_time))
                                    if remaining_time > 0:
                                        status_text.info(f"{progress_messages[min(message_index, len(progress_messages)-1)]}{dots} (예상 완료: {remaining_time}초 후)")
                                    else:
                                        status_text.info(f"{progress_messages[-1]}{dots}")
                                
                                time.sleep(2)  # Update every 2 seconds
                            
                            try:
                                result_file = future.result()
                            except Exception as e:
                                logger.error(f"Timer generation thread failed: {e}")
                                raise e
                        
                        status_text.success(f"✅ {timer_duration}분 타이머 영상 생성 완료!")
                        progress_bar.progress(1.0)
                        
                        # Auto-upload timer video if enabled - FIXED LOGIC
                        if timer_auto_upload_main:
                            status_text.info("📤 YouTube 자동 업로드 중...")
                            timer_token_file = os.path.join(root_dir, "token_timer.pickle")
                            client_secrets_file = os.path.join(root_dir, "client_secrets.json")
                            
                            if os.path.exists(timer_token_file) and os.path.exists(client_secrets_file):
                                try:
                                    from app.utils.youtube import get_authenticated_service, upload_video
                                    
                                    # Clear any previous video session data to prevent tag contamination - ONLY FOR TIMER
                                    # Note: Only clear for timer uploads, not for general video uploads
                                    timer_video_terms = st.session_state.get("video_terms", "")
                                    timer_video_subject = st.session_state.get("video_subject", "")
                                    if timer_video_terms:
                                        logger.info(f"Timer upload: Temporarily clearing video_terms: {timer_video_terms}")
                                    if timer_video_subject:
                                        logger.info(f"Timer upload: Previous video subject was: {timer_video_subject}")
                                    
                                    # Get authenticated YouTube service
                                    youtube = get_authenticated_service(client_secrets_file, timer_token_file)
                                    
                                    # Generate title and tags for timer video - ENHANCED TAGS
                                    title_prefix = st.session_state.get("yt_title_prefix", "#Shorts")
                                    
                                    # Style-based title and tags
                                    if "자연" in timer_style:
                                        style_text = "자연배경"
                                        style_tags = ["자연", "nature", "forest", "peaceful", "힐링", "healing"]
                                    elif "추상" in timer_style:
                                        style_text = "추상배경"
                                        style_tags = ["추상", "abstract", "modern", "digital", "아트", "art"]
                                    else:
                                        style_text = "미니멀"
                                        style_tags = ["미니멀", "minimal", "simple", "clean", "깔끔", "focus"]
                                    
                                    video_title = f"{title_prefix} {timer_duration}분 {style_text} 타이머 - 명상/집중/운동용"
                                    
                                    # Comprehensive tags (Korean + English) - FIXED TAG SYSTEM
                                    base_tags = [
                                        "타이머", "timer", 
                                        f"{timer_duration}분", f"{timer_duration}min",
                                        f"{timer_duration}분타이머", f"{timer_duration}minute timer",
                                        "명상", "meditation", "집중", "focus", "concentration",
                                        "운동", "workout", "exercise", "공부", "study",
                                        "힐링", "healing", "휴식", "rest", "relax",
                                        "pomodoro", "뽀모도로", "productivity", "생산성",
                                        "countdown", "카운트다운", "시간관리", "time management"
                                    ]
                                    
                                    # Add style-specific tags
                                    all_tags = base_tags + style_tags
                                    
                                    # Add more specific time-related tags
                                    time_tags = []
                                    if timer_duration <= 5:
                                        time_tags = ["짧은타이머", "short timer", "quick timer"]
                                    elif timer_duration <= 15:
                                        time_tags = ["중간타이머", "medium timer", "break timer"]
                                    elif timer_duration <= 30:
                                        time_tags = ["긴타이머", "long timer", "work timer"]
                                    else:
                                        time_tags = ["장시간타이머", "extended timer", "marathon timer"]
                                    
                                    all_tags.extend(time_tags)
                                    
                                    # Format tags as comma-separated string for YouTube API
                                    keywords = ", ".join(all_tags[:25])  # Limit to 25 tags
                                    
                                    logger.info(f"TIMER VIDEO - Generated title: {video_title}")
                                    logger.info(f"TIMER VIDEO - Generated tags: {keywords}")
                                    
                                    # Create custom thumbnail for timer video
                                    thumbnail_path = None
                                    try:
                                        from app.utils.youtube import create_timer_thumbnail
                                        thumbnail_path = result_file.replace(".mp4", "_thumbnail.jpg")
                                        create_timer_thumbnail(timer_duration, thumbnail_path, timer_style)
                                        logger.info(f"Timer thumbnail created: {thumbnail_path}")
                                    except Exception as thumb_error:
                                        logger.warning(f"Failed to create timer thumbnail: {thumb_error}")
                                        thumbnail_path = None
                                    
                                    video_id = upload_video(
                                        youtube=youtube,
                                        file_path=result_file,
                                        title=video_title,
                                        description=f"{timer_duration}분 {style_text} 타이머 영상입니다.\n\n🎯 용도: 명상, 집중, 운동, 공부, 휴식\n🎨 스타일: {style_text}\n⏰ 시간: {timer_duration}분\n\nGenerated youtube-auto AI\n\n#타이머 #명상 #집중 #운동 #공부 #힐링 #timer #meditation #focus #study",
                                        keywords=keywords,
                                        privacy_status=st.session_state.get("yt_privacy", "private"),
                                        category=st.session_state.get("yt_category", "22"),
                                        thumbnail_path=thumbnail_path
                                    )
                                    
                                    if video_id:
                                        video_url = f"https://youtube.com/watch?v={video_id}"
                                        status_text.success(f"✅ YouTube 업로드 완료! [영상 보기]({video_url})")
                                        logger.info(f"Timer video uploaded successfully: {video_url}")
                                    else:
                                        status_text.error("❌ YouTube 업로드 실패")
                                        logger.error("Timer video upload failed: no video ID returned")
                                        
                                except Exception as e:
                                    logger.error(f"Timer video upload failed: {e}")
                                    status_text.error(f"❌ 업로드 실패: {str(e)}")
                            else:
                                status_text.error("❌ YouTube 인증이 필요합니다 (타이머 채널 인증 버튼 클릭)")
                                logger.warning("Timer upload failed: missing authentication files")
                        
                        # Add to session state
                        if "generated_video_files" not in st.session_state:
                            st.session_state["generated_video_files"] = []
                        st.session_state["generated_video_files"].insert(0, result_file)
                        
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        import traceback
                        error_details = traceback.format_exc()
                        logger.error(f"Timer generation failed: {e}")
                        logger.error(f"Full traceback: {error_details}")
                        status_text.error(f"❌ 생성 실패: {str(e)}")
                        progress_bar.empty()

    # Premium Long-form Video Section
    with st.expander("📺 **롱폼 영상 생성** - 5-15분 교육/정보 콘텐츠", expanded=False):
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); 
                    padding: 1rem; border-radius: 12px; margin-bottom: 1rem;">
            <p style="margin: 0; color: #a0a0a0;">
                🎓 <strong>교육 콘텐츠</strong> | 📚 <strong>정보 전달</strong> | 🎯 <strong>심화 학습</strong><br>
                5-15분 분량의 전문적인 롱폼 영상을 생성합니다. 쇼츠보다 깊이 있는 내용을 다룹니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Long-form Configuration
        col_longform_config, col_longform_generate = st.columns([0.6, 0.4])
        
        with col_longform_config:
            st.markdown("#### 📝 **롱폼 설정**")
            
            col_duration, col_style = st.columns(2)
            with col_duration:
                longform_duration = st.selectbox(
                    "영상 길이 (분)", 
                    options=[5, 8, 10, 12, 15], 
                    index=2,  # 10분을 기본값으로
                    key="longform_duration_input",
                    help="5분부터 15분까지 설정 가능합니다."
                )
            
            with col_style:
                longform_style = st.selectbox(
                    "콘텐츠 스타일",
                    ["📚 교육형 (상세 설명)", "💡 팁 모음 (실용적)", "🎯 가이드 (단계별)", "📊 분석형 (데이터 기반)"],
                    index=0,  # 교육형을 기본값으로
                    key="longform_style_select"
                )
            
            # Long-form subject input
            st.markdown("#### 🎯 **롱폼 주제**")
            longform_subject = st.text_input(
                "롱폼 영상 주제",
                placeholder="예: 성공하는 사람들의 시간 관리 비법 완전 분석",
                key="longform_subject_input",
                help="쇼츠보다 더 깊이 있고 구체적인 주제를 입력하세요."
            )
            
            # Advanced longform options
            col_chapters, col_segments = st.columns(2)
            with col_chapters:
                chapter_count = st.selectbox(
                    "📖 챕터 수", 
                    options=[5, 6, 7, 8], 
                    index=1,  # 6개를 기본값으로
                    help="롱폼 영상을 나눌 챕터 수입니다."
                )
            with col_segments:
                segment_duration = st.selectbox(
                    "⏱️ 세그먼트 길이 (분)",
                    options=[2, 3, 4],
                    index=1,  # 3분을 기본값으로
                    help="각 세그먼트의 길이입니다. 짧을수록 더 많은 세그먼트가 생성됩니다."
                )
        
        with col_longform_generate:
            st.markdown("#### 🚀 **롱폼 생성**")
            st.markdown(f"**예상 영상 길이:** {longform_duration}분")
            st.markdown(f"**예상 챕터 수:** {chapter_count}개")
            st.markdown(f"**예상 생성 시간:** {longform_duration * 2:.0f}분")
            
            # Auto-upload checkbox for longform
            longform_auto_upload = st.checkbox(
                "📤 생성 후 YouTube 자동 업로드", 
                value=st.session_state.get("longform_auto_upload", True),
                key="longform_auto_upload_main",
                help="체크하면 롱폼 영상 생성 완료 즉시 YouTube에 자동 업로드됩니다"
            )
            
            if st.button("📺 롱폼 영상 생성", use_container_width=True, key="longform_generate_btn", type="primary"):
                if not longform_subject.strip():
                    st.error("❌ 롱폼 영상 주제를 입력해주세요!")
                    st.stop()
                
                # Long-form generation logic
                task_id = str(uuid4())
                
                status_container = st.container()
                with status_container:
                    status_text = st.empty()
                    progress_bar = st.progress(0)
                    
                    try:
                        status_text.info(f"🎬 {longform_duration}분 롱폼 영상 생성 시작...")
                        logger.info(f"Starting longform generation: {longform_duration} minutes, subject: {longform_subject}")
                        
                        # Create longform parameters
                        longform_params = VideoParams(
                            video_subject=longform_subject,
                            video_language="ko-KR",
                            paragraph_number=chapter_count,
                            video_aspect=params.video_aspect,
                            video_source=params.video_source,
                            video_concat_mode=params.video_concat_mode,
                            video_transition_mode=params.video_transition_mode,
                            video_clip_duration=params.video_clip_duration,
                            video_count=1,
                            voice_name=params.voice_name,
                            voice_rate=params.voice_rate,
                            voice_volume=params.voice_volume,
                            bgm_type=params.bgm_type,
                            bgm_volume=params.bgm_volume,
                            subtitle_enabled=params.subtitle_enabled,
                            subtitle_position=params.subtitle_position,
                            text_fore_color=params.text_fore_color,
                            font_size=params.font_size,
                            stroke_color=params.stroke_color,
                            stroke_width=params.stroke_width,
                            n_threads=params.n_threads
                        )
                        
                        # Add longform-specific attributes
                        longform_params.longform_duration = longform_duration
                        longform_params.longform_style = longform_style
                        longform_params.segment_duration = segment_duration
                        
                        # Generate longform video using task manager
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                tm.generate_longform_video,
                                task_id,
                                longform_params
                            )
                            
                            # Enhanced progress tracking
                            start_time = time.time()
                            estimated_duration = longform_duration * 2 * 60  # 2 minutes per video minute
                            
                            progress_messages = [
                                "📝 롱폼 대본 생성 중...",
                                "✂️ 세그먼트 분할 중...", 
                                "🎬 세그먼트 영상 생성 중...",
                                "🎵 오디오 처리 중...",
                                "🎨 배경 영상 수집 중...",
                                "🔄 세그먼트 병합 중...",
                                "💾 최종 영상 저장 중...",
                                "✨ 마무리 작업 중..."
                            ]
                            
                            message_index = 0
                            last_message_time = start_time
                            
                            while not future.done():
                                elapsed_time = time.time() - start_time
                                
                                # Calculate progress
                                if elapsed_time < estimated_duration * 0.8:
                                    estimated_progress = (elapsed_time / (estimated_duration * 0.8)) * 0.9
                                else:
                                    base_progress = 0.9
                                    remaining_progress = 0.1
                                    overtime_factor = (elapsed_time - estimated_duration * 0.8) / (estimated_duration * 0.2)
                                    estimated_progress = base_progress + (remaining_progress * min(overtime_factor, 1.0))
                                
                                progress_percentage = int(estimated_progress * 100)
                                progress_bar.progress(estimated_progress)
                                
                                # Change message periodically
                                if (time.time() - last_message_time > 15) or (progress_percentage >= 90 and message_index < len(progress_messages) - 1):
                                    message_index = min(message_index + 1, len(progress_messages) - 1)
                                    last_message_time = time.time()
                                
                                # Show progress messages
                                if progress_percentage < 95:
                                    status_text.info(f"{progress_messages[min(message_index, 6)]} {progress_percentage}%")
                                else:
                                    dots = "." * ((int(elapsed_time) % 3) + 1)
                                    remaining_time = max(0, int(estimated_duration - elapsed_time))
                                    if remaining_time > 0:
                                        status_text.info(f"{progress_messages[-1]}{dots} (예상 완료: {remaining_time//60}분 {remaining_time%60}초 후)")
                                    else:
                                        status_text.info(f"{progress_messages[-1]}{dots}")
                                
                                time.sleep(3)  # Update every 3 seconds for longform
                            
                            try:
                                result_file = future.result()
                            except Exception as e:
                                logger.error(f"Longform generation thread failed: {e}")
                                raise e
                        
                        if result_file:
                            status_text.success(f"✅ {longform_duration}분 롱폼 영상 생성 완료!")
                            progress_bar.progress(1.0)
                            
                            # Auto-upload longform video if enabled
                            if longform_auto_upload:
                                status_text.info("📤 YouTube 자동 업로드 중...")
                                default_token_file = os.path.join(root_dir, "token.pickle")
                                client_secrets_file = os.path.join(root_dir, "client_secrets.json")
                                
                                if os.path.exists(default_token_file) and os.path.exists(client_secrets_file):
                                    try:
                                        from app.utils.youtube import get_authenticated_service, upload_video
                                        
                                        # Get authenticated YouTube service
                                        youtube = get_authenticated_service(client_secrets_file, default_token_file)
                                        
                                        # Generate title and tags for longform video
                                        title_prefix = st.session_state.get("yt_title_prefix", "")
                                        video_title = f"{title_prefix} {longform_subject} - {longform_duration}분 완전 가이드"
                                        
                                        # Comprehensive tags for longform content
                                        base_tags = [
                                            "롱폼", "longform", "가이드", "guide", "완전분석", "complete analysis",
                                            "교육", "education", "학습", "learning", "정보", "information",
                                            f"{longform_duration}분", f"{longform_duration}minutes", "심화학습", "deep learning",
                                            "전문가", "expert", "상세설명", "detailed explanation"
                                        ]
                                        
                                        # Add style-specific tags
                                        if "교육형" in longform_style:
                                            style_tags = ["교육콘텐츠", "educational content", "강의", "lecture", "설명", "explanation"]
                                        elif "팁 모음" in longform_style:
                                            style_tags = ["팁", "tips", "노하우", "know-how", "실용적", "practical"]
                                        elif "가이드" in longform_style:
                                            style_tags = ["단계별", "step by step", "튜토리얼", "tutorial", "방법", "method"]
                                        else:  # 분석형
                                            style_tags = ["분석", "analysis", "데이터", "data", "통계", "statistics"]
                                        
                                        all_tags = base_tags + style_tags
                                        keywords = ", ".join(all_tags[:30])  # Limit to 30 tags
                                        
                                        logger.info(f"LONGFORM VIDEO - Generated title: {video_title}")
                                        logger.info(f"LONGFORM VIDEO - Generated tags: {keywords}")
                                        
                                        video_id = upload_video(
                                            youtube=youtube,
                                            file_path=result_file,
                                            title=video_title,
                                            description=f"{longform_subject}에 대한 {longform_duration}분 완전 가이드입니다.\n\n🎯 스타일: {longform_style}\n⏰ 길이: {longform_duration}분\n📚 챕터: {chapter_count}개\n\n이 영상에서 다루는 내용을 통해 깊이 있는 학습을 경험하세요.\n\nGenerated by youtube-auto AI\n\n#롱폼 #가이드 #교육 #학습 #정보 #longform #guide #education",
                                            keywords=keywords,
                                            privacy_status=st.session_state.get("yt_privacy", "private"),
                                            category=st.session_state.get("yt_category", "27"),  # Education category
                                            thumbnail_path=None
                                        )
                                        
                                        if video_id:
                                            video_url = f"https://youtube.com/watch?v={video_id}"
                                            status_text.success(f"✅ YouTube 업로드 완료! [영상 보기]({video_url})")
                                            logger.info(f"Longform video uploaded successfully: {video_url}")
                                        else:
                                            status_text.error("❌ YouTube 업로드 실패")
                                            logger.error("Longform video upload failed: no video ID returned")
                                            
                                    except Exception as e:
                                        logger.error(f"Longform video upload failed: {e}")
                                        status_text.error(f"❌ 업로드 실패: {str(e)}")
                                else:
                                    status_text.error("❌ YouTube 인증이 필요합니다 (메인 채널 인증 필요)")
                                    logger.warning("Longform upload failed: missing authentication files")
                            
                            # Add to session state
                            if "generated_video_files" not in st.session_state:
                                st.session_state["generated_video_files"] = []
                            st.session_state["generated_video_files"].insert(0, result_file)
                            
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                        else:
                            status_text.error("❌ 롱폼 영상 생성 실패")
                            progress_bar.empty()
                        
                    except Exception as e:
                        import traceback
                        error_details = traceback.format_exc()
                        logger.error(f"Longform generation failed: {e}")
                        logger.error(f"Full traceback: {error_details}")
                        status_text.error(f"❌ 생성 실패: {str(e)}")
                        progress_bar.empty()

    # YouTube 영상 분석 & 재해석 - 완전히 새로운 독립적 구현
    with st.expander("🎯 **YouTube 영상 분석 & 재해석** - 기존 영상을 새롭게 재창조", expanded=False):
        try:
            from webui.youtube_reinterpret_ui import render_youtube_reinterpret_section
            render_youtube_reinterpret_section()
        except ImportError as e:
            st.error(f"❌ YouTube 재해석 모듈 로드 실패: {e}")
            st.info("💡 youtube_reinterpret_ui.py 파일이 필요합니다.")
        except Exception as e:
            st.error(f"❌ YouTube 재해석 기능 오류: {e}")
            logger.error(f"YouTube reinterpret UI error: {e}")

    # Premium Batch Video Generation Section
    with st.expander("🔄 **배치 영상 생성** - 여러 영상을 한 번에 자동 생성", expanded=False):
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(139, 195, 74, 0.1) 100%); 
                   padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
            <p style="margin: 0; color: #a0a0a0;">
                🚀 <strong>대량 생성</strong> | ⚡ <strong>자동화</strong> | 📋 <strong>리스트 처리</strong><br>
                영상 제목 리스트를 입력하면 자동으로 모든 영상을 연속 생성합니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Batch video list input
        st.markdown("#### 📝 **영상 제목 리스트**")
        batch_video_list = st.text_area(
            "생성할 영상 제목들을 한 줄에 하나씩 입력하세요",
            placeholder="""예시:
1. 건강한 아침 식사 레시피 5가지
2. 집에서 할 수 있는 간단한 운동
3. 스트레스 해소하는 방법
4. 효율적인 시간 관리 팁
5. 좋은 수면을 위한 습관들

- 번호나 기호는 자동으로 제거됩니다
- 빈 줄은 무시됩니다
- 최대 20개까지 입력 가능합니다""",
            height=200,
            key="batch_video_list",
            help="한 줄에 하나씩 영상 제목을 입력하세요. 번호나 기호는 자동으로 제거됩니다."
        )
        
        # Batch settings
        col_batch_type, col_batch_settings = st.columns(2)
        
        with col_batch_type:
            st.markdown("#### ⚙️ **배치 설정**")
            batch_video_type = st.selectbox(
                "영상 타입",
                ["shorts", "longform", "timer"],
                format_func=lambda x: {
                    "shorts": "🎬 쇼츠 (60초)",
                    "longform": "📺 롱폼 (5-15분)",
                    "timer": "⏱️ 타이머"
                }[x],
                key="batch_video_type",
                help="배치로 생성할 영상의 타입을 선택하세요"
            )
            
            batch_language = st.selectbox(
                "언어",
                ["ko-KR", "en-US"],
                format_func=lambda x: "🇰🇷 한국어" if x == "ko-KR" else "🇺🇸 English",
                key="batch_language"
            )
        
        with col_batch_settings:
            st.markdown("#### 🎯 **추가 옵션**")
            
            # 글로벌 버전 옵션 (쇼츠와 롱폼에만 적용)
            if batch_video_type in ["shorts", "longform"]:
                batch_create_global = st.checkbox(
                    "🌍 글로벌 버전 추가 생성",
                    value=True,
                    key="batch_create_global",
                    help="한국어 버전 생성 후, 영어 자막/성우가 적용된 글로벌 버전을 추가로 생성합니다."
                )
            else:
                batch_create_global = False
            
            if batch_video_type == "shorts":
                batch_duration = st.slider("영상 길이 (초)", 30, 90, 60, key="batch_duration")
                batch_style = st.selectbox(
                    "영상 스타일",
                    ["informative", "entertaining", "educational", "motivational"],
                    format_func=lambda x: {
                        "informative": "📊 정보 전달",
                        "entertaining": "🎉 재미있는",
                        "educational": "🎓 교육적",
                        "motivational": "💪 동기부여"
                    }[x],
                    key="batch_style"
                )
            elif batch_video_type == "longform":
                batch_duration = st.slider("영상 길이 (분)", 5, 15, 10, key="batch_longform_duration")
                batch_style = st.selectbox(
                    "영상 스타일",
                    ["educational", "documentary", "tutorial", "discussion"],
                    format_func=lambda x: {
                        "educational": "🎓 교육적",
                        "documentary": "📹 다큐멘터리",
                        "tutorial": "🛠️ 튜토리얼",
                        "discussion": "💬 토론"
                    }[x],
                    key="batch_longform_style"
                )
            else:  # timer
                batch_duration = st.slider("타이머 길이 (분)", 5, 60, 20, key="batch_timer_duration")
                batch_style = st.selectbox(
                    "타이머 스타일",
                    ["modern", "minimal", "nature", "focus"],
                    format_func=lambda x: {
                        "modern": "🎨 모던",
                        "minimal": "⚪ 미니멀",
                        "nature": "🌿 자연",
                        "focus": "🎯 집중"
                    }[x],
                    key="batch_timer_style"
                )
            
            batch_auto_upload = st.checkbox(
                "📤 자동 업로드",
                value=True,
                key="batch_auto_upload",
                help="각 영상 생성 완료 후 자동으로 YouTube에 업로드합니다"
            )
        
        # Preview parsed titles
        if batch_video_list.strip():
            from app.services.batch_processor import batch_processor
            parsed_titles = batch_processor.parse_video_list(batch_video_list)
            
            if parsed_titles:
                st.markdown("#### 📋 **파싱된 제목 목록**")
                if len(parsed_titles) > 20:
                    st.warning(f"⚠️ 입력된 제목이 {len(parsed_titles)}개입니다. 최대 20개까지만 처리됩니다.")
                    parsed_titles = parsed_titles[:20]
                
                with st.container(border=True):
                    for i, title in enumerate(parsed_titles, 1):
                        st.write(f"{i}. {title}")
                
                # 예상 생성 영상 수 계산
                expected_videos = len(parsed_titles)
                if batch_video_type in ["shorts", "longform"] and st.session_state.get('batch_create_global', True):
                    expected_videos *= 2  # 한국어 + 영어 버전
                
                st.info(f"📊 총 {len(parsed_titles)}개 주제, 예상 {expected_videos}개 영상이 생성됩니다.")
                
                if batch_video_type in ["shorts", "longform"] and st.session_state.get('batch_create_global', True):
                    st.success("🌍 각 주제마다 한국어 + 영어 버전이 생성됩니다!")
        
        # Batch generation button
        if st.button("🚀 배치 영상 생성 시작", use_container_width=True, key="batch_generate_btn", type="primary"):
            if not batch_video_list.strip():
                st.error("❌ 영상 제목 리스트를 입력해주세요!")
                st.stop()
            
            from app.services.batch_processor import batch_processor
            parsed_titles = batch_processor.parse_video_list(batch_video_list)
            
            if not parsed_titles:
                st.error("❌ 유효한 영상 제목이 없습니다!")
                st.stop()
            
            if len(parsed_titles) > 20:
                parsed_titles = parsed_titles[:20]
                st.warning("⚠️ 최대 20개까지만 처리합니다.")
            
            # 배치 영상 생성 즉시 시작
            st.markdown("---")
            st.markdown("### 🔄 **배치 영상 생성 진행 중**")
            
            # 진행률 표시 컨테이너
            progress_container = st.container()
            status_container = st.container()
            results_container = st.container()
            
            with progress_container:
                overall_progress = st.progress(0, text="배치 처리 준비 중...")
                current_status = st.empty()
            
            # 배치 처리 시작
            total_videos = len(parsed_titles)
            if batch_create_global and batch_video_type in ["shorts", "longform"]:
                expected_videos = total_videos * 2  # 한국어 + 영어
            else:
                expected_videos = total_videos
            
            completed_videos = []
            failed_videos = []
            
            for i, title in enumerate(parsed_titles):
                current_video_num = i + 1
                
                # Task header (일반 영상 생성과 동일)
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
                    padding: 1rem;
                    border-radius: 12px;
                    margin: 1rem 0;
                    border-left: 4px solid #667eea;
                ">
                    <h4 style="margin: 0; color: #667eea;">🎬 ({current_video_num}/{total_videos}) {title} 생성 중...</h4>
                </div>
                """, unsafe_allow_html=True)
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # 1. 대본 생성 (일반 영상과 정확히 동일한 방식)
                    status_text.text("🤖 AI가 대본을 생성 중입니다...")
                    progress_bar.progress(10)
                    
                    # 일반 영상과 동일한 params 객체 생성
                    from app.models.schema import VideoParams
                    temp_params = VideoParams(
                        video_subject=title,
                        video_script="",  # 임시
                        video_language="ko-KR"
                    )
                    
                    script = ""
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            llm.generate_script,
                            video_subject=temp_params.video_subject,  # 일반 영상과 동일
                            language="ko-KR",
                            paragraph_number=4 if batch_video_type == 'longform' else 1
                        )
                        
                        # Animated progress (일반 영상과 동일)
                        for i in range(50):
                            if future.done():
                                break
                            time.sleep(0.1)
                            current_p = min(10 + int(i * 0.8), 50)
                            progress_bar.progress(current_p)
                            
                        script = future.result()
                    
                    if not script or "실패했습니다" in script or "Error:" in script:
                        st.warning(f"⚠️ 대본 생성 실패 (API 할당량 초과): 기본 대본 사용")
                        # API 할당량 초과 시 기본 대본 사용
                        script = f"{title}에 대한 유용한 정보를 제공하는 영상입니다. 이 주제에 대해 자세히 알아보겠습니다."
                        st.info("💡 API 할당량이 복구되면 더 나은 대본이 생성됩니다.")
                    
                    # 대본 표시 (중첩 expander 제거)
                    st.markdown(f"**📝 사용된 대본 - {title}**")
                    import time
                    unique_key = f"script_display_batch_{i}_{hash(title)}_{int(time.time()*1000)}"
                    st.text_area("대본 내용", value=script, height=100, disabled=True, key=unique_key)
                    
                    # 2. 키워드 생성 (일반 영상과 정확히 동일한 방식)
                    status_text.text("🔍 대본 분석 및 키워드 추출 중...")
                    progress_bar.progress(60)
                    
                    terms = []
                    try:
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                llm.generate_terms,
                                video_subject=temp_params.video_subject,  # 일반 영상과 동일
                                video_script=script, 
                                amount=5
                            )
                            
                            # Animated progress (일반 영상과 동일)
                            for i_term in range(40):
                                if future.done():
                                    break
                                time.sleep(0.1)
                                current_p = min(60 + int(i_term * 1), 90)
                                progress_bar.progress(current_p)
                                
                            terms = future.result()
                    except Exception as e:
                        st.warning(f"⚠️ 키워드 생성 실패 (API 할당량 초과): 기본 키워드 사용")
                        terms = []
                    
                    if not terms:
                        terms = [title]  # 제목을 기본 키워드로 사용
                    
                    # 키워드 표시
                    if terms and terms != [title]:
                        st.info(f"🏷️ 생성된 키워드: {', '.join(terms)}")
                    else:
                        st.info(f"🏷️ 기본 키워드 사용: {', '.join(terms)}")
                    
                    status_text.text("🎬 영상 생성 중...")
                    progress_bar.progress(95)
                    
                    # 한국어 버전 생성 (일반 영상 생성과 동일한 방식)
                    import webui.batch_video_generator as batch_gen
                    from uuid import uuid4
                    from app.services import state as sm, llm
                    from app.models import const
                    import concurrent.futures
                    import time
                    
                    task_id = str(uuid4())
                    status_text.info(f"🎬 작업 시작... (ID: {task_id[:8]})")
                    
                    # 일반 영상 생성과 동일한 ThreadPoolExecutor 사용
                    ko_result = None
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(batch_gen.generate_single_video,
                            title=title,
                            video_type=batch_video_type,
                            language="ko-KR",
                            duration=batch_duration,
                            style=batch_style,
                            auto_upload=batch_auto_upload,
                            task_id=task_id,  # task_id 전달
                            script=script,    # 생성된 대본 전달
                            terms=terms,      # 생성된 키워드 전달
                            ui_params=params  # 일반영상과 동일한 UI 설정 전달
                        )
                        
                        # 일반 영상 생성과 동일한 진행률 모니터링
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
                            time.sleep(2)  # 모바일 깜빡임 방지를 위해 업데이트 간격 증가
                        
                        if future.done():
                            try:
                                ko_result = future.result()
                                logger.info(f"Korean version future completed. Result type: {type(ko_result)}")
                                logger.info(f"Korean version result: {ko_result}")
                                
                                if ko_result:
                                    if ko_result.get('file_path'):
                                        status_text.success(f"🎉 한국어 버전 생성 완료!")
                                        logger.info(f"Korean version file: {ko_result['file_path']}")
                                        
                                        # 파일 존재 확인
                                        if os.path.exists(ko_result['file_path']):
                                            file_size = os.path.getsize(ko_result['file_path'])
                                            logger.info(f"Korean version file exists, size: {file_size} bytes")
                                        else:
                                            logger.warning(f"Korean version file does not exist: {ko_result['file_path']}")
                                        
                                        if ko_result.get('upload_error'):
                                            st.warning(f"⚠️ YouTube 업로드 실패: {ko_result['upload_error']}")
                                    else:
                                        logger.warning(f"Korean version result missing file_path: {ko_result}")
                                        status_text.warning(f"⚠️ 한국어 버전 생성 완료되었지만 파일 정보가 불완전합니다")
                                else:
                                    logger.error("Korean version result is None or empty")
                                    status_text.error(f"❌ 한국어 버전 생성 결과가 없습니다")
                                    raise Exception("영상 파일이 생성되지 않았습니다")
                            except Exception as e:
                                logger.error(f"Korean version generation failed: {e}")
                                status_text.error(f"❌ 한국어 버전 생성 실패: {str(e)}")
                                raise e
                    
                    # 결과 검증을 더 관대하게 처리
                    if ko_result:
                        logger.info(f"Processing Korean result for completed_videos: {ko_result}")
                        
                        video_result = {
                            'title': title,
                            'korean_version': ko_result,
                            'english_version': None,
                            'success': True
                        }
                        
                        # 자동 업로드 처리 (일반 영상과 완전히 동일한 방식)
                        if batch_auto_upload and ko_result.get('auto_upload_requested'):
                            logger.info("Processing auto upload for Korean version...")
                            try:
                                video_path = ko_result.get('file_path')
                                if video_path and os.path.exists(video_path):
                                    status_text.info(f"📺 YouTube 자동 업로드 시작...")
                                    
                                    # 일반 영상과 완전히 동일한 파일 경로 처리
                                    import os
                                    root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
                                    token_file = os.path.join(root_dir, "token.pickle")
                                    client_secrets_file = os.path.join(root_dir, "client_secrets.json")
                                    
                                    logger.info(f"🔍 Token file exists: {os.path.exists(token_file)}")
                                    logger.info(f"🔍 Client secrets file exists: {os.path.exists(client_secrets_file)}")
                                    
                                    if os.path.exists(token_file) and os.path.exists(client_secrets_file):
                                        from app.utils.youtube import get_authenticated_service, upload_video
                                        
                                        youtube = get_authenticated_service(client_secrets_file, token_file)
                                        title_subject = title
                                        upload_title = f"#Shorts {title_subject}"
                                        description = f"Generated youtube-auto AI\n\nSubject: {title_subject}"
                                        
                                        # 태그 생성 (일반 영상과 완전히 동일한 방식)
                                        script = ko_result.get('script', '')
                                        try:
                                            # 1. 먼저 영어 키워드 생성 (일반 영상과 동일)
                                            english_terms = llm.generate_terms(title_subject, script, 10) or []
                                            
                                            # 2. 영어 키워드를 한국어로 번역 (일반 영상과 동일)
                                            if english_terms:
                                                try:
                                                    korean_terms = llm.translate_terms_to_korean(english_terms)
                                                    keywords = ", ".join(korean_terms + [str(title_subject).strip()])
                                                    logger.info(f"🇰🇷 Successfully translated tags: {keywords}")
                                                except Exception as e:
                                                    logger.error(f"Translation failed: {e}, using fallback Korean tags")
                                                    fallback_terms = ["정보", "팁", "노하우", "가이드", "도움"]
                                                    keywords = ", ".join(fallback_terms + [str(title_subject).strip()])
                                            else:
                                                # 영어 키워드 생성 실패 시 fallback
                                                fallback_terms = ["정보", "팁", "노하우", "가이드", "도움"]
                                                keywords = ", ".join(fallback_terms + [str(title_subject).strip()])
                                                
                                            logger.info(f"🏷️ Final Korean tags: {keywords}")
                                        except Exception as e:
                                            logger.warning(f"Tag generation failed: {e}")
                                            # 기본 키워드 사용
                                            keywords = str(title_subject).strip()
                                            logger.info(f"🏷️ Using fallback keywords: {keywords}")
                                        
                                        vid_id = upload_video(
                                            youtube, 
                                            video_path, 
                                            title=upload_title[:100],
                                            description=description,
                                            category="22",
                                            keywords=keywords,
                                            privacy_status="private"
                                        )
                                        
                                        if vid_id:
                                            ko_result['video_id'] = vid_id
                                            video_url = f"https://youtube.com/watch?v={vid_id}"
                                            status_text.success(f"🎉 자동 업로드 성공! [영상 보기]({video_url})")
                                        else:
                                            ko_result['upload_error'] = "YouTube 업로드 실패"
                                            status_text.warning("⚠️ 자동 업로드 실패")
                                    else:
                                        ko_result['upload_error'] = "YouTube 인증 필요"
                                        status_text.warning("⚠️ YouTube 인증이 필요합니다")
                                else:
                                    logger.error("Video file not found for auto upload")
                            except Exception as upload_error:
                                logger.error(f"Auto upload failed: {upload_error}")
                                ko_result['upload_error'] = str(upload_error)
                                status_text.warning(f"⚠️ 자동 업로드 실패: {upload_error}")
                        
                        # 파일 경로가 없어도 결과는 표시하되 경고 표시
                        if not ko_result.get('file_path'):
                            st.warning(f"⚠️ {title}: 영상이 생성되었지만 파일 경로 정보가 없습니다")
                            logger.warning(f"Missing file_path in result: {ko_result}")
                    else:
                        logger.error("No Korean result available for completed_videos")
                        raise Exception("한국어 버전 생성 결과가 없습니다")
                    
                    # 영어 버전 생성 (글로벌 버전이 활성화된 경우)
                    logger.info(f"Checking English version generation: batch_create_global={batch_create_global}, batch_video_type={batch_video_type}")
                    if batch_create_global and batch_video_type in ["shorts", "longform"]:
                        try:
                            st.markdown(f"""
                            <div style="
                                background: linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(139, 195, 74, 0.1) 100%);
                                padding: 1rem;
                                border-radius: 12px;
                                margin: 1rem 0;
                                border-left: 4px solid #4caf50;
                            ">
                                <h4 style="margin: 0; color: #4caf50;">🌍 ({current_video_num}/{total_videos}) {title} 영어 버전 생성 중...</h4>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            eng_progress_bar = st.progress(0)
                            eng_status_text = st.empty()
                            
                            # 영어 버전 대본 생성 (일반 영상과 정확히 동일한 방식)
                            eng_status_text.text("🤖 AI가 영어 대본을 생성 중입니다...")
                            eng_progress_bar.progress(10)
                            
                            # 일반 영상과 동일한 params 객체 생성
                            from app.models.schema import VideoParams
                            temp_eng_params = VideoParams(
                                video_subject=title,
                                video_script="",  # 임시
                                video_language="en-US"
                            )
                            
                            eng_script = ""
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(
                                    llm.generate_script,
                                    video_subject=temp_eng_params.video_subject,  # 일반 영상과 동일
                                    language="en-US",
                                    paragraph_number=4 if batch_video_type == 'longform' else 1
                                )
                                
                                # Animated progress (일반 영상과 동일)
                                for i in range(50):
                                    if future.done():
                                        break
                                    time.sleep(0.1)
                                    current_p = min(10 + int(i * 0.8), 50)
                                    eng_progress_bar.progress(current_p)
                                    
                                eng_script = future.result()
                            
                            if not eng_script or "실패했습니다" in eng_script or "Error:" in eng_script:
                                st.warning(f"⚠️ 영어 대본 생성 실패 (API 할당량 초과): 기본 대본 사용")
                                # API 할당량 초과 시 기본 영어 대본 사용
                                eng_script = f"This video provides useful information about {title}. Let's explore this topic in detail."
                                st.info("💡 API 할당량이 복구되면 더 나은 영어 대본이 생성됩니다.")
                            
                            # 영어 대본 표시 (중첩 expander 제거)
                            st.markdown(f"**📝 사용된 영어 대본 - {title}**")
                            import time
                            unique_eng_key = f"eng_script_display_batch_{i}_{hash(title)}_{int(time.time()*1000)}"
                            st.text_area("영어 대본 내용", value=eng_script, height=100, disabled=True, key=unique_eng_key)
                            
                            # 영어 키워드 생성 (일반 영상과 정확히 동일한 방식)
                            eng_status_text.text("🔍 영어 대본 분석 및 키워드 추출 중...")
                            eng_progress_bar.progress(60)
                            
                            eng_terms = []
                            try:
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(
                                        llm.generate_terms,
                                        video_subject=temp_eng_params.video_subject,  # 일반 영상과 동일
                                        video_script=eng_script, 
                                        amount=5
                                    )
                                    
                                    # Animated progress (일반 영상과 동일)
                                    for i_term in range(40):
                                        if future.done():
                                            break
                                        time.sleep(0.1)
                                        current_p = min(60 + int(i_term * 1), 90)
                                        eng_progress_bar.progress(current_p)
                                        
                                    eng_terms = future.result()
                            except Exception as e:
                                st.warning(f"⚠️ 영어 키워드 생성 실패 (API 할당량 초과): 기본 키워드 사용")
                                eng_terms = []
                            
                            if not eng_terms:
                                eng_terms = [title]  # 제목을 기본 키워드로 사용
                            
                            # 영어 키워드 표시
                            if eng_terms and eng_terms != [title]:
                                st.info(f"🏷️ 생성된 영어 키워드: {', '.join(eng_terms)}")
                            else:
                                st.info(f"🏷️ 기본 영어 키워드 사용: {', '.join(eng_terms)}")
                            
                            eng_status_text.text("🎬 영어 영상 생성 중...")
                            eng_progress_bar.progress(95)
                            
                            # 영어 제목 생성 (일반 영상과 완전히 동일한 방식)
                            eng_title = title  # 기본값
                            try:
                                # 주제를 영어로 번역 시도
                                eng_title = llm.translate_to_english(title)
                                if not eng_title or eng_title == title or re.search(r'[가-힣]', str(eng_title)):
                                    # 번역 실패 시 키워드 기반 영어 제목 생성
                                    if eng_terms and len(eng_terms) > 0:
                                        eng_title = " · ".join([t for t in eng_terms[:3] if t and not re.search(r'[가-힣]', t)])
                                    else:
                                        eng_title = "Motivational Content"
                                logger.info(f"🌍 Generated English title: {eng_title}")
                            except Exception as e:
                                logger.warning(f"English title generation failed: {e}")
                                eng_title = "Motivational Content"
                            
                            eng_task_id = str(uuid4())
                            eng_status_text.info(f"🌍 영어 버전 작업 시작... (ID: {eng_task_id[:8]})")
                            
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                eng_future = executor.submit(batch_gen.generate_single_video,
                                    title=eng_title,  # 영어로 번역된 제목 사용
                                    video_type=batch_video_type,
                                    language="en-US",
                                    duration=batch_duration,
                                    style=batch_style,
                                    auto_upload=batch_auto_upload,
                                    task_id=eng_task_id,  # task_id 전달
                                    script=eng_script,    # 생성된 영어 대본 전달
                                    terms=eng_terms,      # 생성된 영어 키워드 전달
                                    ui_params=params      # 일반영상과 동일한 UI 설정 전달
                                )
                                
                                while not eng_future.done():
                                    eng_task_info = sm.state.get_task(eng_task_id)
                                    if eng_task_info:
                                        eng_progress = eng_task_info.get("progress", 0)
                                        eng_state = eng_task_info.get("state", const.TASK_STATE_PROCESSING)
                                        eng_task_msg = eng_task_info.get("message", "")
                                        
                                        eng_progress_normalized = min(int(eng_progress) / 100, 1.0)
                                        eng_progress_bar.progress(eng_progress_normalized)
                                        
                                        if eng_state == const.TASK_STATE_PROCESSING:
                                            eng_status_text.info(f"🌍 {eng_task_msg} ({int(eng_progress)}%)" if eng_task_msg else f"영어 버전 처리 중... {int(eng_progress)}%")
                                        elif eng_state == const.TASK_STATE_FAILED:
                                            eng_status_text.error(f"❌ 영어 버전 실패: {eng_task_msg}")
                                            break
                                        elif eng_state == const.TASK_STATE_COMPLETE:
                                            eng_status_text.success("✅ 영어 버전 완료!")
                                            break
                                    time.sleep(2)  # 모바일 깜빡임 방지를 위해 업데이트 간격 증가
                                
                                if eng_future.done():
                                    eng_result = eng_future.result()
                                    # 영어 제목 정보 추가
                                    eng_result['english_title'] = eng_title
                                    video_result['english_version'] = eng_result
                                    eng_status_text.success(f"🎉 영어 버전 생성 완료!")
                                    
                                    # 영어 버전 자동 업로드 처리 (일반 영상과 완전히 동일한 방식)
                                    if batch_auto_upload and eng_result and eng_result.get('auto_upload_requested'):
                                        logger.info("Processing auto upload for English version...")
                                        try:
                                            video_path = eng_result.get('file_path')
                                            if video_path and os.path.exists(video_path):
                                                eng_status_text.info(f"📺 YouTube 자동 업로드 시작 (English)...")
                                                
                                                # 일반 영상과 완전히 동일한 파일 경로 처리
                                                import os
                                                root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
                                                token_file = os.path.join(root_dir, "token.pickle")
                                                client_secrets_file = os.path.join(root_dir, "client_secrets.json")
                                                
                                                logger.info(f"🔍 Token file exists: {os.path.exists(token_file)}")
                                                logger.info(f"🔍 Client secrets file exists: {os.path.exists(client_secrets_file)}")
                                                
                                                if os.path.exists(token_file) and os.path.exists(client_secrets_file):
                                                    from app.utils.youtube import get_authenticated_service, upload_video
                                                    
                                                    youtube = get_authenticated_service(client_secrets_file, token_file)
                                                    
                                                    # 일반 영상과 동일한 로직: eng_result에서 영어 제목 가져오기
                                                    title_subject = eng_result.get('english_title') or eng_result.get('title', 'Motivational Content')
                                                    
                                                    logger.info(f"🔍 Auto Upload English - title_subject: {title_subject}")
                                                    
                                                    upload_title = f"#Shorts {title_subject}"
                                                    description = f"Generated youtube-auto AI\n\nSubject: {title_subject}"
                                                    
                                                    logger.info(f"📺 Auto Upload - Title: {upload_title}")
                                                    logger.info(f"📺 Auto Upload - Description: {description}")
                                                    
                                                    # 키워드는 이미 생성된 것 사용 (API 재호출 방지)
                                                    script = eng_result.get('script', '')
                                                    if terms and len(terms) > 0:
                                                        # 이미 생성된 키워드 사용
                                                        keywords = ", ".join(terms + [str(title_subject).strip()])
                                                        logger.info(f"🏷️ Using pre-generated keywords: {keywords}")
                                                    else:
                                                        # 기본 키워드 사용 (API 호출 없음)
                                                        keywords = str(title_subject).strip()
                                                        logger.info(f"🏷️ Using basic keywords: {keywords}")
                                                    
                                                    vid_id = upload_video(
                                                        youtube, 
                                                        video_path, 
                                                        title=upload_title[:100],
                                                        description=description,
                                                        category="22",
                                                        keywords=keywords,
                                                        privacy_status="private"
                                                    )
                                                    
                                                    if vid_id:
                                                        eng_result['video_id'] = vid_id
                                                        video_url = f"https://youtube.com/watch?v={vid_id}"
                                                        eng_status_text.success(f"🎉 영어 버전 자동 업로드 성공! [영상 보기]({video_url})")
                                                    else:
                                                        eng_result['upload_error'] = "YouTube 업로드 실패"
                                                        eng_status_text.warning("⚠️ 영어 버전 자동 업로드 실패")
                                                else:
                                                    eng_result['upload_error'] = "YouTube 인증 필요"
                                                    eng_status_text.warning("⚠️ YouTube 인증이 필요합니다")
                                            else:
                                                logger.error("English video file not found for auto upload")
                                        except Exception as upload_error:
                                            logger.error(f"English auto upload failed: {upload_error}")
                                            eng_result['upload_error'] = str(upload_error)
                                            eng_status_text.warning(f"⚠️ 영어 버전 자동 업로드 실패: {upload_error}")
                            
                        except Exception as e:
                            st.warning(f"⚠️ 영어 버전 생성 실패: {title} - {str(e)}")
                    else:
                        logger.info(f"Skipping English version: batch_create_global={batch_create_global}, batch_video_type={batch_video_type}")
                        if not batch_create_global:
                            st.info("ℹ️ 글로벌 버전 생성이 비활성화되어 있습니다.")
                        elif batch_video_type not in ["shorts", "longform"]:
                            st.info(f"ℹ️ {batch_video_type} 타입은 글로벌 버전을 지원하지 않습니다.")
                    
                    completed_videos.append(video_result)
                    
                except Exception as e:
                    failed_videos.append({
                        'title': title,
                        'error': str(e)
                    })
                    st.error(f"❌ 영상 생성 실패: {title} - {str(e)}")
                
                # 각 영상 완료 후 잠시 대기 (UI 업데이트를 위해)
                import time
                time.sleep(0.5)
            
            # 최종 완료
            overall_progress.progress(1.0, text=f"배치 처리 완료! {len(completed_videos)}개 성공, {len(failed_videos)}개 실패")
            current_status.success("✅ 모든 배치 처리가 완료되었습니다!")
            
            # 결과 표시
            with results_container:
                st.markdown("---")
                st.markdown("### 📊 **배치 처리 결과**")
                
                # 디버깅 정보
                st.write(f"DEBUG: completed_videos 개수: {len(completed_videos)}")
                st.write(f"DEBUG: failed_videos 개수: {len(failed_videos)}")
                
                col_success, col_fail = st.columns(2)
                with col_success:
                    st.metric("성공", len(completed_videos))
                with col_fail:
                    st.metric("실패", len(failed_videos))
                
                # 성공한 영상들
                if completed_videos:
                    st.markdown("#### ✅ **성공한 영상들**")
                    for i, result in enumerate(completed_videos):
                        st.write(f"DEBUG: 결과 {i+1}: {result}")  # 디버깅 정보
                        
                        with st.container(border=True):
                            st.markdown(f"**✅ {result['title']}**")
                            
                            # 한국어 버전
                            if result.get('korean_version'):
                                ko_version = result['korean_version']
                                st.markdown("**🇰🇷 한국어 버전**")
                                
                                # 파일 경로 표시
                                if ko_version.get('file_path'):
                                    video_path = ko_version['file_path']
                                    st.write(f"**파일**: {video_path}")
                                    
                                    # 파일 존재 여부 확인
                                    import os
                                    if os.path.exists(video_path):
                                        file_size = os.path.getsize(video_path)
                                        st.success(f"✅ 파일 존재함 ({file_size:,} bytes)")
                                        
                                        # 영상 표시 및 컨트롤 (일반 영상과 동일)
                                        col_video, col_controls = st.columns([0.6, 0.4])
                                        
                                        with col_video:
                                            st.video(video_path, format="video/mp4")
                                        
                                        with col_controls:
                                            st.markdown("#### 🎬 **영상 작업**")
                                            
                                            # 채널 선택
                                            channels = [("🏠 메인 채널", "default"), ("⏱️ 타이머 채널", "timer")]
                                            selected_channel_index = st.selectbox(
                                                "업로드 채널 선택",
                                                options=range(len(channels)),
                                                format_func=lambda x: channels[x][0],
                                                index=0,
                                                key=f"batch_ko_channel_{i}"
                                            )
                                            
                                            # 액션 버튼들
                                            col_btn1, col_btn2 = st.columns(2)
                                            
                                            with col_btn1:
                                                # 다운로드 버튼
                                                try:
                                                    with open(video_path, "rb") as video_file:
                                                        video_bytes = video_file.read()
                                                    st.download_button(
                                                        label="📥 다운로드",
                                                        data=video_bytes,
                                                        file_name=os.path.basename(video_path),
                                                        mime="video/mp4",
                                                        key=f"batch_ko_dl_{i}",
                                                        use_container_width=True
                                                    )
                                                except Exception:
                                                    st.button("📥 다운로드", disabled=True, use_container_width=True)
                                            
                                            with col_btn2:
                                                # 재생 버튼
                                                if st.button("▶️ 재생", key=f"batch_ko_play_{i}", use_container_width=True):
                                                    try:
                                                        if os.name == 'nt':
                                                            os.startfile(video_path)
                                                        else:
                                                            import subprocess
                                                            subprocess.call(('xdg-open', video_path))
                                                    except Exception:
                                                        st.error("재생할 수 없습니다.")
                                            
                                            # 수동 업로드 버튼
                                            upload_progress_container = st.empty()
                                            
                                            if st.button("📺 YouTube 업로드", key=f"batch_ko_upload_{i}", use_container_width=True, type="primary"):
                                                st.session_state[f"batch_ko_upload_requested_{i}"] = True
                                            
                                            # 업로드 로직 처리 (일반 영상과 동일)
                                            if st.session_state.get(f"batch_ko_upload_requested_{i}"):
                                                with upload_progress_container.container():
                                                    # 토큰 파일 선택
                                                    timer_token_file = "token_timer.pickle"
                                                    default_token_file = "token.pickle"
                                                    ch_idx = st.session_state.get(f"batch_ko_channel_{i}", 0)
                                                    token_file = timer_token_file if ch_idx == 1 else default_token_file
                                                    
                                                    # client_secrets.json 찾기
                                                    client_secrets_file = "client_secrets.json"
                                                    if not os.path.exists(client_secrets_file):
                                                        alt_copy = "client_secrets - 복사본.json"
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
                                                            
                                                            from app.utils.youtube import get_authenticated_service, upload_video
                                                            youtube = get_authenticated_service(client_secrets_file, token_file)
                                                            
                                                            # 메타데이터 생성
                                                            title_subject = result['title']
                                                            title = f"#Shorts {title_subject}"
                                                            description = f"{title}\n\nGenerated youtube-auto AI\nSubject: {title_subject}"
                                                            
                                                            # 한국어 키워드 생성 (일반 영상과 완전히 동일한 방식)
                                                            script = ko_version.get('script', '')
                                                            from app.services import llm
                                                            
                                                            # 1. 먼저 영어 키워드 생성 (일반 영상과 동일)
                                                            english_terms = llm.generate_terms(title_subject, script, 10) or []
                                                            
                                                            # 2. 영어 키워드를 한국어로 번역 (일반 영상과 동일)
                                                            if english_terms:
                                                                try:
                                                                    korean_terms = llm.translate_terms_to_korean(english_terms)
                                                                    keywords = ", ".join(korean_terms + [str(title_subject).strip()])
                                                                    logger.info(f"🇰🇷 Successfully translated tags: {keywords}")
                                                                except Exception as e:
                                                                    logger.error(f"Translation failed: {e}, using fallback Korean tags")
                                                                    fallback_terms = ["정보", "팁", "노하우", "가이드", "도움"]
                                                                    keywords = ", ".join(fallback_terms + [str(title_subject).strip()])
                                                            else:
                                                                # 영어 키워드 생성 실패 시 fallback
                                                                fallback_terms = ["정보", "팁", "노하우", "가이드", "도움"]
                                                                keywords = ", ".join(fallback_terms + [str(title_subject).strip()])
                                                            
                                                            vid_id = upload_video(
                                                                youtube, 
                                                                video_path, 
                                                                title=title[:100],
                                                                description=description,
                                                                category="22",
                                                                keywords=keywords,
                                                                privacy_status="private",
                                                                progress_callback=update_progress
                                                            )
                                                            
                                                            if vid_id:
                                                                upload_progress.progress(1.0)
                                                                upload_status.success("✅ 업로드 성공!")
                                                                st.markdown(f"🎉 [영상 보러가기](https://youtu.be/{vid_id})")
                                                                st.session_state[f"batch_ko_upload_requested_{i}"] = False
                                                            else:
                                                                upload_status.error("❌ 업로드 실패")
                                                                st.session_state[f"batch_ko_upload_requested_{i}"] = False
                                                                
                                                        except Exception as e:
                                                            st.error(f"❌ 업로드 오류: {e}")
                                                            st.session_state[f"batch_ko_upload_requested_{i}"] = False
                                                    else:
                                                        st.error("❌ 인증 필요 (설정에서 YouTube 인증을 완료해주세요)")
                                                        st.session_state[f"batch_ko_upload_requested_{i}"] = False
                                    else:
                                        st.error("❌ 파일 없음")
                                else:
                                    st.warning("파일 경로 정보 없음")
                                
                                # YouTube 링크 표시 (자동 업로드된 경우)
                                if ko_version.get('video_id'):
                                    video_url = f"https://youtube.com/watch?v={ko_version['video_id']}"
                                    st.write(f"**YouTube**: [영상 보기]({video_url})")
                                
                                # 업로드 오류 표시
                                if ko_version.get('upload_error'):
                                    st.warning(f"자동 업로드 오류: {ko_version['upload_error']}")
                                    
                                # 추가 정보 표시 (중첩 expander 제거)
                                if ko_version.get('script'):
                                    st.markdown("**📝 생성된 대본**")
                                    st.text_area("대본 내용", value=ko_version['script'], height=100, disabled=True, key=f"result_script_{result.get('title', 'unknown')}_ko")
                            else:
                                st.warning("한국어 버전 정보 없음")
                            
                            # 영어 버전
                            if result.get('english_version'):
                                eng_version = result['english_version']
                                st.markdown("**🇺🇸 English 버전**")
                                
                                # 파일 경로 표시
                                if eng_version.get('file_path'):
                                    video_path = eng_version['file_path']
                                    st.write(f"**파일**: {video_path}")
                                    
                                    # 파일 존재 여부 확인
                                    import os
                                    if os.path.exists(video_path):
                                        file_size = os.path.getsize(video_path)
                                        st.success(f"✅ 파일 존재함 ({file_size:,} bytes)")
                                        
                                        # 영상 표시 및 컨트롤 (일반 영상과 동일)
                                        col_video, col_controls = st.columns([0.6, 0.4])
                                        
                                        with col_video:
                                            st.video(video_path, format="video/mp4")
                                        
                                        with col_controls:
                                            st.markdown("#### 🎬 **영상 작업**")
                                            
                                            # 채널 선택
                                            channels = [("🏠 메인 채널", "default"), ("⏱️ 타이머 채널", "timer")]
                                            selected_channel_index = st.selectbox(
                                                "업로드 채널 선택",
                                                options=range(len(channels)),
                                                format_func=lambda x: channels[x][0],
                                                index=0,
                                                key=f"batch_en_channel_{i}"
                                            )
                                            
                                            # 액션 버튼들
                                            col_btn1, col_btn2 = st.columns(2)
                                            
                                            with col_btn1:
                                                # 다운로드 버튼
                                                try:
                                                    with open(video_path, "rb") as video_file:
                                                        video_bytes = video_file.read()
                                                    st.download_button(
                                                        label="📥 다운로드",
                                                        data=video_bytes,
                                                        file_name=os.path.basename(video_path),
                                                        mime="video/mp4",
                                                        key=f"batch_en_dl_{i}",
                                                        use_container_width=True
                                                    )
                                                except Exception:
                                                    st.button("📥 다운로드", disabled=True, use_container_width=True)
                                            
                                            with col_btn2:
                                                # 재생 버튼
                                                if st.button("▶️ 재생", key=f"batch_en_play_{i}", use_container_width=True):
                                                    try:
                                                        if os.name == 'nt':
                                                            os.startfile(video_path)
                                                        else:
                                                            import subprocess
                                                            subprocess.call(('xdg-open', video_path))
                                                    except Exception:
                                                        st.error("재생할 수 없습니다.")
                                            
                                            # 수동 업로드 버튼
                                            upload_progress_container = st.empty()
                                            
                                            if st.button("📺 YouTube 업로드", key=f"batch_en_upload_{i}", use_container_width=True, type="primary"):
                                                st.session_state[f"batch_en_upload_requested_{i}"] = True
                                            
                                            # 업로드 로직 처리 (일반 영상과 동일)
                                            if st.session_state.get(f"batch_en_upload_requested_{i}"):
                                                with upload_progress_container.container():
                                                    # 토큰 파일 선택
                                                    timer_token_file = "token_timer.pickle"
                                                    default_token_file = "token.pickle"
                                                    ch_idx = st.session_state.get(f"batch_en_channel_{i}", 0)
                                                    token_file = timer_token_file if ch_idx == 1 else default_token_file
                                                    
                                                    # client_secrets.json 찾기
                                                    client_secrets_file = "client_secrets.json"
                                                    if not os.path.exists(client_secrets_file):
                                                        alt_copy = "client_secrets - 복사본.json"
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
                                                            
                                                            from app.utils.youtube import get_authenticated_service, upload_video
                                                            youtube = get_authenticated_service(client_secrets_file, token_file)
                                                            
                                                            # 일반 영상과 동일한 로직 사용
                                                            # eng_version['english_title']이 이미 영어로 설정되어 있음
                                                            title_subject = eng_version.get('english_title') or eng_version.get('title', 'Motivational Content')
                                                            
                                                            logger.info(f"🔍 Batch English Upload - title_subject: {title_subject}")
                                                            
                                                            # 일반 영상과 동일한 형식
                                                            title = f"#Shorts {title_subject}"
                                                            description = f"Generated youtube-auto AI\n\nSubject: {title_subject}"
                                                            
                                                            logger.info(f"📺 YouTube Upload - Title: {title}")
                                                            logger.info(f"📺 YouTube Upload - Description: {description}")
                                                            
                                                            # 키워드 생성 (영어)
                                                            script = eng_version.get('script', '')
                                                            from app.services import llm
                                                            base_terms = llm.generate_terms(title_subject, script, amount=15) or []
                                                            keywords = ", ".join(base_terms + [str(title_subject).strip()])
                                                            
                                                            vid_id = upload_video(
                                                                youtube, 
                                                                video_path, 
                                                                title=title[:100],
                                                                description=description,
                                                                category="22",
                                                                keywords=keywords,
                                                                privacy_status="private",
                                                                progress_callback=update_progress
                                                            )
                                                            
                                                            if vid_id:
                                                                upload_progress.progress(1.0)
                                                                upload_status.success("✅ 업로드 성공!")
                                                                st.markdown(f"🎉 [영상 보러가기](https://youtu.be/{vid_id})")
                                                                st.session_state[f"batch_en_upload_requested_{i}"] = False
                                                            else:
                                                                upload_status.error("❌ 업로드 실패")
                                                                st.session_state[f"batch_en_upload_requested_{i}"] = False
                                                                
                                                        except Exception as e:
                                                            st.error(f"❌ 업로드 오류: {e}")
                                                            st.session_state[f"batch_en_upload_requested_{i}"] = False
                                                    else:
                                                        st.error("❌ 인증 필요 (설정에서 YouTube 인증을 완료해주세요)")
                                                        st.session_state[f"batch_en_upload_requested_{i}"] = False
                                    else:
                                        st.error("❌ 파일 없음")
                                else:
                                    st.warning("파일 경로 정보 없음")
                                
                                # YouTube 링크 표시 (자동 업로드된 경우)
                                if eng_version.get('video_id'):
                                    video_url = f"https://youtube.com/watch?v={eng_version['video_id']}"
                                    st.write(f"**YouTube**: [영상 보기]({video_url})")
                                
                                # 업로드 오류 표시
                                if eng_version.get('upload_error'):
                                    st.warning(f"자동 업로드 오류: {eng_version['upload_error']}")
                                    
                                # 추가 정보 표시 (중첩 expander 제거)
                                if eng_version.get('script'):
                                    st.markdown("**📝 생성된 대본 (English)**")
                                    st.text_area("대본 내용", value=eng_version['script'], height=100, disabled=True, key=f"result_script_{result.get('title', 'unknown')}_en")
                            else:
                                st.info("영어 버전 없음")
                else:
                    st.warning("성공한 영상이 없습니다.")
                
                # 실패한 영상들
                if failed_videos:
                    st.markdown("#### ❌ **실패한 영상들**")
                    for error in failed_videos:
                        with st.container(border=True):
                            st.markdown(f"**❌ {error['title']}**")
                            st.error(f"오류: {error['error']}")


def generate_single_video(title: str, video_type: str, language: str, duration: int, style: str, auto_upload: bool = False) -> dict:
    """단일 영상 생성 (기존 웹UI 로직 활용)"""
    
    from uuid import uuid4
    from app.models.schema import VideoParams
    from app.services import task, llm
    from app.utils.youtube import get_authenticated_service, upload_video
    import os
    import glob
    from app.utils import utils
    
    # Task ID 생성
    task_id = str(uuid4())
    
    try:
        # 1. 대본 생성
        if video_type == "longform":
            script = llm.generate_longform_script(
                video_subject=title,
                language=language,
                duration_minutes=duration
            )
        else:  # shorts
            script = llm.generate_script(
                video_subject=title,
                language=language,
                paragraph_number=1
            )
        
        if not script:
            raise Exception("대본 생성 실패")
        
        # 2. VideoParams 설정
        params_dict = {
            'video_subject': title,
            'video_script': script,
            'video_language': language,
            'voice_name': 'casual' if video_type == 'shorts' else 'professional',
            'bgm_type': 'random',
            'bgm_volume': 0.2,
            'subtitle_enabled': True,
            'subtitle_position': 'bottom',
            'video_source': 'pexels',
            'video_aspect': '9:16' if video_type == 'shorts' else '16:9',
            'video_concat_mode': 'random',
            'video_clip_duration': 3 if video_type == 'shorts' else 5,
            'video_count': 5 if video_type == 'shorts' else 10,
            'font_size': 60,
            'stroke_width': 1.5,
            'n_threads': 2,
            'paragraph_number': 1 if video_type == 'shorts' else 4
        }
        
        params = VideoParams(**params_dict)
        
        # 3. 영상 생성
        if video_type == "longform":
            task.generate_longform_video(task_id, params)
        else:
            task.start(task_id, params, stop_at="video")
        
        # 4. 생성된 파일 찾기
        task_dir = utils.task_dir(task_id)
        
        video_patterns = [
            os.path.join(task_dir, f"longform_final_{task_id}.mp4"),  # 롱폼
            os.path.join(task_dir, "final-*.mp4"),                    # 쇼츠
            os.path.join(task_dir, "combined-*.mp4"),                 # 결합된 영상
            os.path.join(task_dir, "*.mp4")                           # 모든 mp4
        ]
        
        video_file = None
        for pattern in video_patterns:
            files = glob.glob(pattern)
            if files:
                video_file = files[0]
                break
        
        if not video_file:
            raise Exception("영상 파일을 찾을 수 없습니다")
        
        # 5. YouTube 업로드 (옵션)
        video_id = None
        if auto_upload:
            try:
                client_secrets_file = "client_secrets.json"
                token_file = "token.pickle"
                
                if os.path.exists(client_secrets_file) and os.path.exists(token_file):
                    youtube_service = get_authenticated_service(client_secrets_file, token_file)
                    
                    # 태그 생성
                    tags = llm.generate_terms(title, script, 10)
                    
                    video_id = upload_video(
                        youtube=youtube_service,
                        file_path=video_file,
                        title=title,
                        description=f"AI가 생성한 {video_type} 영상입니다.\n\n주제: {title}",
                        keywords=",".join(tags) if tags else "",
                        privacy_status="private"
                    )
            except Exception as e:
                st.warning(f"YouTube 업로드 실패: {e}")
        
        return {
            'file_path': video_file,
            'script': script,
            'video_id': video_id,
            'type': video_type,
            'language': language
        }
        
    except Exception as e:
        raise Exception(f"영상 생성 실패: {str(e)}")
        
        # Batch processing status
        if st.session_state.get('batch_processing', False):
            st.markdown("---")
            st.markdown("### 🔄 **배치 처리 진행 상황**")
            
            from app.services.batch_processor import batch_processor
            
            # Create progress containers
            batch_status_container = st.container()
            batch_progress_container = st.container()
            batch_results_container = st.container()
            
            with batch_status_container:
                status = batch_processor.get_status()
                
                if status['is_processing']:
                    # Overall progress
                    overall_progress = status['current_progress'] / 100.0
                    st.progress(overall_progress, text=f"전체 진행률: {status['current_progress']:.0f}%")
                    
                    # Current video info
                    if status['current_video_title']:
                        st.info(f"🎬 현재 처리 중: ({status['current_video_index']}/{status['total_videos']}) {status['current_video_title']}")
                    
                    # Auto-refresh every 2 seconds
                    time.sleep(2)
                    st.rerun()
                
                else:
                    # Processing completed
                    st.success("✅ 배치 처리가 완료되었습니다!")
                    
                    # Results summary
                    col_success, col_error = st.columns(2)
                    with col_success:
                        st.metric("성공", status['completed_count'], delta=None)
                    with col_error:
                        st.metric("실패", status['error_count'], delta=None)
                    
                    # Detailed results
                    if status['results']:
                        st.markdown("#### ✅ **성공한 영상들**")
                        for result in status['results']:
                            with st.container(border=True):
                                st.markdown(f"**✅ {result['title']}**")
                                result_data = result['result']
                                
                                # 한국어 버전 정보
                                if result_data.get('korean_version'):
                                    ko_version = result_data['korean_version']
                                    st.markdown("**🇰🇷 한국어 버전**")
                                    st.write(f"**파일**: {ko_version.get('file_path', 'N/A')}")
                                    if ko_version.get('video_id'):
                                        video_url = f"https://youtube.com/watch?v={ko_version['video_id']}"
                                        st.write(f"**YouTube**: [영상 보기]({video_url})")
                                
                                # 영어 버전 정보
                                if result_data.get('english_version'):
                                    eng_version = result_data['english_version']
                                    st.markdown("**🇺🇸 English 버전**")
                                    st.write(f"**파일**: {eng_version.get('file_path', 'N/A')}")
                                    if eng_version.get('video_id'):
                                        video_url = f"https://youtube.com/watch?v={eng_version['video_id']}"
                                        st.write(f"**YouTube**: [영상 보기]({video_url})")
                                
                                # 단일 버전인 경우 (타이머 등)
                                if not result_data.get('korean_version') and not result_data.get('english_version'):
                                    st.write(f"**파일**: {result_data.get('file_path', 'N/A')}")
                                    if result_data.get('video_id'):
                                        video_url = f"https://youtube.com/watch?v={result_data['video_id']}"
                                        st.write(f"**YouTube**: [영상 보기]({video_url})")
                                
                                st.write(f"**완료 시간**: {result['timestamp']}")
                                
                                # 총 생성된 버전 수 표시
                                total_versions = result_data.get('total_versions', 1)
                                if total_versions > 1:
                                    st.info(f"📊 총 {total_versions}개 버전 생성됨")
                    
                    if status['errors']:
                        st.markdown("#### ❌ **실패한 영상들**")
                        for error in status['errors']:
                            with st.container(border=True):
                                st.markdown(f"**❌ {error['title']}**")
                                st.error(f"오류: {error['error']}")
                                st.write(f"**실패 시간**: {error['timestamp']}")
                    
                    # Reset batch processing state
                    if st.button("🔄 새로운 배치 처리 시작", key="reset_batch_btn"):
                        st.session_state['batch_processing'] = False
                        if 'batch_titles' in st.session_state:
                            del st.session_state['batch_titles']
                        if 'batch_params' in st.session_state:
                            del st.session_state['batch_params']
                        st.rerun()
            
            # Start batch processing if not already started
            if not batch_processor.is_processing and 'batch_titles' in st.session_state:
                import asyncio
                
                async def run_batch_processing():
                    titles = st.session_state['batch_titles']
                    params = st.session_state['batch_params']
                    
                    def progress_callback(status):
                        # This will be called by the batch processor
                        pass
                    
                    result = await batch_processor.process_batch_videos(
                        titles, params, progress_callback, params.get('auto_upload', False)
                    )
                    
                    return result
                
                # Run batch processing
                try:
                    asyncio.run(run_batch_processing())
                except Exception as e:
                    st.error(f"배치 처리 중 오류 발생: {e}")
                    st.session_state['batch_processing'] = False

    # Container for progress bar (placed immediately after the button)
    # generation_status_container is already defined above after the main button

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
                    
                    # Video player and controls
                    col_video, col_controls = st.columns([0.6, 0.4])
                    
                    with col_video:
                        st.video(video_path, format="video/mp4")
                    
                    with col_controls:
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
                        
                        # Action buttons
                        col_btn1, col_btn2 = st.columns(2)
                        
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
                        
                        # Upload button
                        upload_progress_container = st.empty()
                        
                        if st.button("📺 YouTube 업로드", key=f"upload_btn_{i}", use_container_width=True, type="primary"):
                            st.session_state[f"upload_requested_{i}"] = True
                        
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
                                        description = f"{title}\n\nGenerated youtube-auto AI\nSubject: {title_subject}"
                                        
                                        # Generate keywords based on script content
                                        base_terms = llm.generate_terms(title_subject, task_script or (params.video_script or ""), amount=15) or []
                                        # Only use script-based keywords, no generic tags
                                        keywords = ", ".join(base_terms + [str(title_subject).strip()])
                                        
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
                                        st.error(f"❌ 업로드 오류: {e}")
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
                    ("📋 순차 연결 (쇼츠 최적화)", "sequential"),
                    ("🎲 무작위 연결", "random"),
                ]
                selected_index = st.selectbox(
                    "영상 연결 방식",
                    index=0,
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
                ("🆓 Google TTS (무료, 고품질)", "gtts"),
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
            elif selected_tts_server == "gtts":
                filtered_voices = voice.get_gtts_voices()
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
                    index=5, 
                    key="settings_voice_rate",
                    help="쇼츠 최적화: 1.2배 속도 (최적화된 템포)"
                )
            
            # 언어별 속도 미세 조정
            st.markdown("##### 🌍 언어별 속도 미세 조정")
            col_ko_speed, col_en_speed = st.columns(2)
            
            with col_ko_speed:
                if "settings_korean_speed_boost" not in st.session_state:
                    st.session_state["settings_korean_speed_boost"] = 1.3
                
                korean_speed = st.selectbox(
                    "🇰🇷 한국어 추가 속도",
                    options=[1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
                    index=3,  # 1.3 기본값
                    key="settings_korean_speed_boost",
                    help="한국어 gTTS는 느려서 1.3배속 추천"
                )
            
            with col_en_speed:
                if "settings_english_speed_boost" not in st.session_state:
                    st.session_state["settings_english_speed_boost"] = 1.1
                
                english_speed = st.selectbox(
                    "🇺🇸 영어 추가 속도",
                    options=[1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
                    index=1,  # 1.1 기본값
                    key="settings_english_speed_boost",
                    help="영어도 1.1배속으로 쇼츠 최적화"
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
                    index=2,
                    options=range(len(subtitle_positions)),
                    format_func=lambda x: subtitle_positions[x][0],
                    key="settings_subtitle_position",
                    help="쇼츠용은 하단이 가장 적합합니다"
                )
                params.subtitle_position = subtitle_positions[selected_index][1]
            
            if params.subtitle_position == "custom":
                params.custom_position = st.slider(
                    "사용자 지정 위치 (%)", 
                    0.0, 
                    100.0, 
                    70.0, 
                    key="settings_custom_position",
                    help="0%는 최상단, 100%는 최하단"
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
        
        # Font preview removed - no longer needed
        
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
        
        # API Key input
        llm_api_key = config.app.get(f"{llm_provider}_api_key", "")
        st_llm_api_key = st.text_input(
            f"🔑 {llm_provider.upper()} API 키", 
            value=llm_api_key, 
            type="password",
            help="API 키는 안전하게 암호화되어 저장됩니다"
        )
        if st_llm_api_key: 
            config.app[f"{llm_provider}_api_key"] = st_llm_api_key
        
        # Additional API keys for quota management (Gemini only)
        if llm_provider == "gemini":
            st.markdown("---")
            st.markdown("**🔄 추가 Gemini API 키 (할당량 관리)**")
            st.info("💡 여러 API 키를 설정하면 할당량 초과 시 자동으로 다른 키로 전환됩니다")
            
            # Show current additional keys
            gemini_keys = []
            for i in range(2, 11):  # Support up to 10 total keys (key_2 to key_10)
                key_name = f"gemini_api_key_{i}"
                current_key = config.app.get(key_name, "")
                if current_key:
                    gemini_keys.append((i, current_key))
            
            if gemini_keys:
                st.markdown("**📋 저장된 추가 API 키:**")
                keys_to_remove = []
                for i, (key_num, key_value) in enumerate(gemini_keys):
                    col_key, col_del = st.columns([0.8, 0.2])
                    with col_key:
                        masked_key = f"{key_value[:8]}...{key_value[-4:]}" if len(key_value) > 12 else key_value
                        st.text(f"🔑 API 키 #{key_num}: {masked_key}")
                    with col_del:
                        if st.button("🗑️", key=f"del_gemini_{key_num}", help="삭제"):
                            keys_to_remove.append(f"gemini_api_key_{key_num}")
                
                if keys_to_remove:
                    for key_name in keys_to_remove:
                        if key_name in config.app:
                            del config.app[key_name]
                    config.save_config()
                    st.success("✅ API 키가 삭제되었습니다!")
                    time.sleep(1)
                    st.rerun()
            
            # Add new API key
            st.markdown("**➕ 새 API 키 추가:**")
            col_new_key, col_add_btn = st.columns([0.7, 0.3])
            
            with col_new_key:
                new_gemini_key = st.text_input(
                    "새 Gemini API 키", 
                    key="new_gemini_key", 
                    type="password",
                    placeholder="AIza...",
                    help="추가할 Gemini API 키를 입력하세요"
                )
            
            with col_add_btn:
                st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
                if st.button("➕ 키 추가", key="add_gemini", use_container_width=True, type="primary"):
                    if new_gemini_key:
                        # Find next available slot
                        next_slot = None
                        for i in range(2, 11):  # Support up to 10 total keys
                            key_name = f"gemini_api_key_{i}"
                            if not config.app.get(key_name):
                                next_slot = i
                                break
                        
                        if next_slot:
                            config.app[f"gemini_api_key_{next_slot}"] = new_gemini_key
                            config.save_config()
                            st.success(f"✅ API 키 #{next_slot}이 추가되었습니다!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ 최대 10개의 API 키만 저장할 수 있습니다")
                    else:
                        st.error("API 키를 입력해주세요")
            
            # Show total count
            total_keys = 1 if st_llm_api_key else 0
            total_keys += len(gemini_keys)
            if total_keys > 1:
                st.success(f"🎯 총 {total_keys}개의 Gemini API 키가 설정되어 있습니다")
            elif total_keys == 1:
                st.info("💡 추가 API 키를 등록하면 할당량 초과 시 자동으로 전환됩니다")
        
        
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
                <code style="color: #000000; background: #f0f0f0; padding: 2px 6px; border-radius: 4px;">client_secrets.json</code> 파일이 필요합니다.
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
            
            # 중복 제거: 타이머 자동 업로드는 메인 타이머 생성 섹션에서만 관리
            
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
    # Mobile optimization: Set generation state and add keep-alive
    st.session_state["generation_in_progress"] = True
    st.session_state["generation_start_time"] = time.time()
    
    task_id = str(uuid4())
    
    # 모바일 세션 저장 - 안전한 방식으로 재활성화
    if MOBILE_OPTIMIZATION_AVAILABLE:
        try:
            mobile_session_manager.save_generation_state(task_id, {
                "video_subject": params.video_subject,
                "video_type": "shorts" if params.video_aspect == "9:16" else "longform",
                "video_language": params.video_language,
                "voice_name": params.voice_name,
            })
        except Exception as e:
            logger.error(f"Failed to save mobile session: {e}")
    
    # Mobile optimization: Add connection keep-alive and progress tracking
    if MOBILE_OPTIMIZATION_AVAILABLE:
        st.markdown("""
        <script>
        // Enhanced mobile optimization for background operation
        let keepAliveInterval;
        let progressCheckInterval;
        let backgroundMode = false;
        
        function startMobileOptimization() {
            // Aggressive keep connection alive (every 15 seconds)
            keepAliveInterval = setInterval(() => {
                fetch(window.location.href, {method: 'HEAD'}).catch(() => {
                    console.log('Keep-alive request failed, retrying...');
                });
            }, 15000); // Every 15 seconds for better reliability
            
            // Prevent screen sleep on mobile
            if ('wakeLock' in navigator) {
                navigator.wakeLock.request('screen').catch(() => {
                    console.log('Wake lock not available, using alternative methods');
                });
            }
            
            // Enhanced page visibility monitoring
            document.addEventListener('visibilitychange', function() {
                if (document.hidden) {
                    backgroundMode = true;
                    console.log('Page went to background - enabling background mode');
                    
                    // More aggressive keep-alive in background
                    if (keepAliveInterval) {
                        clearInterval(keepAliveInterval);
                    }
                    keepAliveInterval = setInterval(() => {
                        fetch(window.location.href, {method: 'HEAD'}).catch(() => {});
                        // Also ping a simple endpoint to keep session alive
                        fetch(window.location.origin + '/health', {method: 'HEAD'}).catch(() => {});
                    }, 10000); // Every 10 seconds in background
                    
                } else {
                    backgroundMode = false;
                    console.log('Page came to foreground - resuming normal mode');
                    
                    // Resume normal keep-alive interval
                    if (keepAliveInterval) {
                        clearInterval(keepAliveInterval);
                    }
                    keepAliveInterval = setInterval(() => {
                        fetch(window.location.href, {method: 'HEAD'}).catch(() => {});
                    }, 15000);
                    
                    // Refresh page to get latest status
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                }
            });
            
            // Service Worker for background processing (if supported)
            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.register('/sw.js').then(function(registration) {
                    console.log('Service Worker registered for background processing');
                }).catch(function(error) {
                    console.log('Service Worker registration failed:', error);
                });
            }
            
            // Beforeunload warning for mobile users
            window.addEventListener('beforeunload', function(e) {
                if (!backgroundMode) {
                    e.preventDefault();
                    e.returnValue = '영상 생성이 진행 중입니다. 페이지를 닫으시겠습니까?';
                    return e.returnValue;
                }
            });
        }
        
        function stopMobileOptimization() {
            if (keepAliveInterval) {
                clearInterval(keepAliveInterval);
            }
            if (progressCheckInterval) {
                clearInterval(progressCheckInterval);
            }
            backgroundMode = false;
        }
        
        // Start optimization
        startMobileOptimization();
        
        // Auto cleanup after 45 minutes (extended for longer videos)
        setTimeout(stopMobileOptimization, 45 * 60 * 1000);
        
        // Global functions for cleanup
        window.stopMobileOptimization = stopMobileOptimization;
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
    
    # 쿠팡파트너스 오버레이 데이터 준비
    coupang_overlay_data = None
    if st.session_state.get("enable_coupang_overlay", False):
        coupang_links_input = st.session_state.get("coupang_links_input", "")
        if coupang_links_input.strip():
            try:
                from app.services.coupang_partners import get_coupang_manager
                
                # 링크 파싱
                links_list = [link.strip() for link in coupang_links_input.split('\n') if link.strip()]
                valid_links = [link for link in links_list if 'coupang.com' in link or 'coupa.ng' in link][:3]
                
                if valid_links:
                    st.info(f"🛒 {len(valid_links)}개 쿠팡 제품 정보 수집 중...")
                    coupang_manager = get_coupang_manager()
                    coupang_overlay_data = coupang_manager.create_product_overlay_data(valid_links)
                    st.success(f"✅ 쿠팡 제품 오버레이 준비 완료!")
                    
            except Exception as e:
                st.warning(f"⚠️ 쿠팡 제품 정보 수집 실패: {str(e)}")
                st.info("💡 제품 오버레이 없이 영상을 생성합니다")
                coupang_overlay_data = None
    
    # Task 1: Korean (Original)
    korean_params = params.copy()
    korean_params.coupang_overlay_data = coupang_overlay_data  # 쿠팡 오버레이 데이터 추가
    tasks_to_run.append({
        "label": "🇰🇷 한국어 버전",
        "params": korean_params,
        "icon": "🎬"
    })
    
    # Task 2: English (Optional)
    if generate_english_version:
        st.write(f"🔍 DEBUG: 영어 버전 생성 시작 - generate_english_version = {generate_english_version}")
        with st.spinner("🌍 글로벌 버전 준비 중... (대본 번역)"):
            try:
                # 1단계: 대본 번역 시도
                st.write(f"🔍 DEBUG: 번역 시도 - 원본 대본: {params.video_script[:50]}...")
                english_script = llm.translate_to_english(params.video_script)
                st.write(f"🔍 DEBUG: 번역 결과: {english_script[:50] if english_script else 'None'}...")
                
                # 번역 성공 여부 확인 (한글이 없고, 원본과 다르면 성공)
                import re
                translation_success = (
                    english_script and 
                    english_script != params.video_script and 
                    "Error" not in english_script and
                    not re.search(r'[가-힣]', english_script)
                )
                st.write(f"🔍 DEBUG: 번역 성공 여부: {translation_success}")
                
                if not translation_success:
                    st.warning("⚠️ 대본 번역에 실패했습니다. 영어 키워드로 새 대본을 생성합니다...")
                    
                    # 백업 방법 1: 영어 키워드로 새 대본 생성
                    try:
                        # 주제를 영어로 번역 시도
                        eng_subject = llm.translate_to_english(params.video_subject)
                        if not eng_subject or eng_subject == params.video_subject or re.search(r'[가-힣]', str(eng_subject)):
                            # 번역 실패 시 키워드 기반 영어 주제 생성
                            terms_en = llm.generate_terms(video_subject=params.video_subject, video_script=params.video_script, amount=5) or []
                            if terms_en:
                                eng_subject = " · ".join([t for t in terms_en[:3] if t and not re.search(r'[가-힣]', t)])
                            else:
                                # 최후 백업: 기본 영어 주제들
                                fallback_subjects = [
                                    "Success Tips and Life Hacks",
                                    "Motivation and Personal Growth", 
                                    "Lifestyle and Wellness Guide",
                                    "Productivity and Time Management",
                                    "Health and Fitness Tips"
                                ]
                                import random
                                eng_subject = random.choice(fallback_subjects)
                        
                        # 영어 주제로 새 대본 생성
                        st.info(f"🔄 영어 주제로 새 대본 생성 중: {eng_subject}")
                        english_script = llm.generate_english_script(
                            video_subject=eng_subject,
                            paragraph_number=4
                        )
                        
                        if english_script and "Error" not in english_script:
                            translation_success = True
                            st.success("✅ 영어 대본 생성 완료!")
                        else:
                            st.warning("⚠️ 영어 대본 생성도 실패했습니다.")
                            
                    except Exception as e:
                        st.warning(f"⚠️ 영어 대본 생성 실패: {e}")
                
                # 번역/생성이 성공했으면 영어 버전 태스크 추가
                if translation_success:
                    eng_params = params.copy()
                    eng_params.video_script = english_script
                    
                    # 영어 주제 설정
                    if 'eng_subject' in locals() and eng_subject:
                        eng_params.video_subject = eng_subject
                    else:
                        eng_subject = llm.translate_to_english(params.video_subject)
                        if not eng_subject or eng_subject == params.video_subject or re.search(r'[가-힣]', str(eng_subject)):
                            # 키워드 기반 영어 주제 생성
                            try:
                                terms_en = llm.generate_terms(video_subject=params.video_subject, video_script=english_script, amount=5) or []
                                if terms_en:
                                    eng_subject = " · ".join([t for t in terms_en[:3] if t and not re.search(r'[가-힣]', t)])
                                else:
                                    eng_subject = "Motivational Content"
                            except Exception:
                                eng_subject = "Motivational Content"
                        eng_params.video_subject = eng_subject
                    
                    # 영어 음성 설정 - gTTS 우선, Azure TTS 폴백
                    english_voices = [
                        "gtts:en-English",             # 무료 Google TTS (영어)
                        "en-US-AndrewNeural",          # 남성, 자연스러운 목소리
                        "en-US-BrianNeural",           # 남성, 깊은 목소리  
                        "en-US-ChristopherNeural",     # 남성, 전문적인 목소리
                        "en-US-AriaNeural",            # 여성, 친근한 목소리
                        "en-US-JennyNeural",           # 여성, 명확한 목소리
                        "en-US-MichelleNeural"         # 여성, 따뜻한 목소리
                    ]
                    
                    # gTTS 영어 음성을 우선 사용 (할당량 절약)
                    selected_voice = "gtts:en-English"  # 기본적으로 무료 gTTS 사용
                    eng_params.voice_name = selected_voice
                    eng_params.video_language = "en-US"
                    
                    # 영어 버전 자막 설정 명시적 활성화
                    eng_params.subtitle_enabled = True
                    
                    # 영어 키워드 생성 (영상 소재 검색용)
                    try:
                        eng_terms = llm.generate_terms(video_subject=eng_subject, video_script=english_script, amount=8) or []
                        if eng_terms:
                            # 영어 키워드만 필터링
                            filtered_terms = [t for t in eng_terms if t and not re.search(r'[가-힣]', t)]
                            if filtered_terms:
                                eng_params.video_terms = ", ".join(filtered_terms)
                            else:
                                # 기본 영어 키워드
                                eng_params.video_terms = "motivation, success, lifestyle, tips, guide, inspiration"
                        else:
                            eng_params.video_terms = "motivation, success, lifestyle, tips, guide, inspiration"
                    except Exception:
                        eng_params.video_terms = "motivation, success, lifestyle, tips, guide, inspiration"
                    
                    # 영어 버전에도 쿠팡 오버레이 데이터 추가
                    eng_params.coupang_overlay_data = coupang_overlay_data
                    
                    # 영어 버전임을 표시하고 한국어 자막 경로 전달
                    eng_params.is_english_version = True
                    eng_params.korean_task_id = None  # 한국어 버전 완료 후 설정됨
                    
                    tasks_to_run.append({
                        "label": "🌍 글로벌 버전",
                        "params": eng_params,
                        "icon": "🌎"
                    })
                    
                    st.write(f"🔍 DEBUG: 영어 버전 태스크 추가됨 - 총 태스크 수: {len(tasks_to_run)}")
                    
                    st.success(f"✅ 글로벌 버전 준비 완료!")
                    st.info(f"📝 영어 주제: {eng_subject}")
                    st.info(f"🎵 영어 음성: Google TTS (무료)")
                    st.info(f"🏷️ 영어 키워드: {eng_params.video_terms[:50]}{'...' if len(eng_params.video_terms) > 50 else ''}")
                else:
                    st.write(f"🔍 DEBUG: 번역 실패로 영어 버전 건너뜀")
                    st.warning("⚠️ 모든 영어 버전 생성 방법이 실패하여 글로벌 버전 생성을 건너뜁니다")
                    
            except Exception as e:
                st.error(f"❌ 글로벌 버전 준비 실패: {e}")
                logger.error(f"English version preparation failed: {e}")

    final_video_files = []

    # Premium Generation UI
    with generation_status_container:
        st.markdown("### 🚀 **AI 영상 생성 진행중**")
        
        st.write(f"🔍 DEBUG: 실행할 태스크 수: {len(tasks_to_run)}")
        for i, task in enumerate(tasks_to_run):
            st.write(f"🔍 DEBUG: 태스크 {i+1} 시작 - {task['label']}")
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
                        time.sleep(2)
                    
                    if future.done():
                        result = future.result()
                        if result and "videos" in result:
                            generated_videos = result["videos"]
                            final_video_files.extend(generated_videos)
                            status_text.success(f"🎉 {task_label} 생성 완료!")
                            
                            # 모바일 세션 완료 처리 - 안전한 방식으로 재활성화
                            if MOBILE_OPTIMIZATION_AVAILABLE and generated_videos:
                                try:
                                    video_file = generated_videos[0] if generated_videos else None
                                    mobile_session_manager.complete_generation(task_id, video_file)
                                except Exception as e:
                                    logger.error(f"Failed to update mobile session completion: {e}")
                            
                            # 한국어 버전 완료 시 영어 버전에 task_id 전달
                            if i == 0 and len(tasks_to_run) > 1:  # 첫 번째 태스크(한국어)이고 영어 버전이 있는 경우
                                tasks_to_run[1]["params"].korean_task_id = task_id
                                logger.info(f"Korean task completed, passing task_id to English version: {task_id}")
                            
                            # Auto-upload if enabled
                            auto_upload_enabled = st.session_state.get("yt_auto_upload", False)
                            logger.info(f"🔍 DEBUG: Auto-upload checkbox state: {auto_upload_enabled}")
                            logger.info(f"🔍 DEBUG: Session state yt_auto_upload: {st.session_state.get('yt_auto_upload')}")
                            logger.info(f"🔍 DEBUG: All session keys with 'upload': {[k for k in st.session_state.keys() if 'upload' in k.lower()]}")
                            
                            if auto_upload_enabled:
                                logger.info("✅ 자동 업로드가 활성화되어 있습니다.")
                                st.info("🔍 자동 업로드가 활성화되어 있습니다.")
                                token_file = os.path.join(root_dir, "token.pickle")
                                client_secrets_file = os.path.join(root_dir, "client_secrets.json")
                                
                                logger.info(f"🔍 Token file exists: {os.path.exists(token_file)}")
                                logger.info(f"🔍 Client secrets file exists: {os.path.exists(client_secrets_file)}")
                                
                                # Debug: Check task_params content
                                logger.info(f"DEBUG: task_params keys: {list(task_params.__dict__.keys()) if hasattr(task_params, '__dict__') else 'No __dict__'}")
                                logger.info(f"DEBUG: task_params type: {type(task_params)}")
                                
                                if os.path.exists(token_file) and os.path.exists(client_secrets_file):
                                    for video_path in generated_videos:
                                        if os.path.exists(video_path):
                                            status_text.info(f"📺 YouTube 업로드 시작: {os.path.basename(video_path)}")
                                            try:
                                                youtube = get_authenticated_service(client_secrets_file, token_file)
                                                title_subject = task_params.video_subject
                                                title = f"{st.session_state.get('yt_title_prefix', '#Shorts')} {title_subject}"
                                                description = f"Generated youtube-auto AI\n\nSubject: {title_subject}"
                                                
                                                # Use existing video_terms (search keywords) as YouTube tags
                                                video_terms_value = getattr(task_params, 'video_terms', None)
                                                video_language = getattr(task_params, 'video_language', 'ko-KR')
                                                logger.info(f"DEBUG: video_terms from task_params: {video_terms_value}")
                                                logger.info(f"DEBUG: video_language: {video_language}")
                                                
                                                if video_terms_value:
                                                    # Check if this is Korean version and terms are in English
                                                    if video_language != "en-US":
                                                        # Korean version - check if terms need translation
                                                        if isinstance(video_terms_value, list):
                                                            terms_list = video_terms_value
                                                        else:
                                                            terms_list = [term.strip() for term in str(video_terms_value).split(",")]
                                                        
                                                        # Check if terms contain Korean characters
                                                        import re
                                                        has_korean = any(re.search(r'[가-힣]', str(term)) for term in terms_list)
                                                        
                                                        if not has_korean:
                                                            # English terms detected in Korean version - translate them
                                                            logger.info(f"🇰🇷 Translating English terms to Korean: {terms_list}")
                                                            try:
                                                                korean_terms = llm.translate_terms_to_korean(terms_list)
                                                                keywords = ", ".join(korean_terms + [str(title_subject).strip()])
                                                                logger.info(f"🇰🇷 Successfully translated tags: {keywords}")
                                                            except Exception as e:
                                                                logger.error(f"Translation failed: {e}, using fallback Korean tags")
                                                                fallback_terms = ["정보", "팁", "노하우", "가이드", "도움"]
                                                                keywords = ", ".join(fallback_terms + [str(title_subject).strip()])
                                                        else:
                                                            # Already Korean terms
                                                            keywords = ", ".join(terms_list + [str(title_subject).strip()])
                                                            logger.info(f"🇰🇷 Using existing Korean tags: {keywords}")
                                                    else:
                                                        # English version - use as is
                                                        if isinstance(video_terms_value, list):
                                                            keywords = ", ".join(video_terms_value + [str(title_subject).strip()])
                                                        else:
                                                            keywords = f"{video_terms_value}, {str(title_subject).strip()}"
                                                        logger.info(f"🇺🇸 Using English tags: {keywords}")
                                                else:
                                                    # Fallback: generate new tags only if no search keywords exist
                                                    logger.warning(f"No existing video_terms found, generating new tags for language: {video_language}")
                                                    
                                                    if video_language == "en-US":
                                                        terms = llm.generate_terms(task_params.video_subject, getattr(task_params, 'video_script', '') or "", amount=15) or []
                                                        keywords = ", ".join(terms + [str(title_subject).strip()])
                                                        logger.info(f"Generated new English terms: {keywords}")
                                                    else:
                                                        korean_terms = llm.generate_korean_terms(task_params.video_subject, getattr(task_params, 'video_script', '') or "", amount=15) or []
                                                        keywords = ", ".join(korean_terms + [str(title_subject).strip()])
                                                        logger.info(f"Generated new Korean terms: {keywords}")
                                                
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
                                                status_text.error(f"❌ 업로드 오류: {e}")
                                            else:
                                                status_text.warning("⚠️ 자동 업로드가 활성화되어 있지만 YouTube 인증이 필요합니다")
                                                st.info("💡 '고급 설정' → 'YouTube 업로드 설정'에서 '🔐 메인 채널 인증' 버튼을 클릭하세요")
                            else:
                                logger.warning("❌ 자동 업로드가 비활성화되어 있습니다.")
                                st.warning("⚠️ 자동 업로드가 비활성화되어 있습니다.")
                        else:
                            status_text.error(f"❌ {task_label} 생성 실패")
                            
            except Exception as e:
                logger.error(f"Error during video generation: {e}")
                status_text.error(f"❌ 생성 오류: {e}")

    # Success handling
    if final_video_files:
        # Add new videos to existing list instead of replacing
        if "generated_video_files" not in st.session_state:
            st.session_state["generated_video_files"] = []
        
        # Add new videos to the beginning of the list
        for video_file in reversed(final_video_files):
            if video_file not in st.session_state["generated_video_files"]:
                st.session_state["generated_video_files"].insert(0, video_file)
        
        logger.info(f"Updated video list with {len(final_video_files)} new videos. Total: {len(st.session_state['generated_video_files'])}")
        
        # Mobile optimization: Reset generation state
        st.session_state["generation_in_progress"] = False
        if MOBILE_OPTIMIZATION_AVAILABLE:
            st.markdown("""
            <script>
            // Mobile optimization: Stop keep-alive and cleanup
            if (typeof stopMobileOptimization === 'function') {
                stopMobileOptimization();
            }
            
            // Re-enable screen sleep
            if ('wakeLock' in navigator && navigator.wakeLock.release) {
                navigator.wakeLock.release();
            }
            
            console.log('Mobile optimization cleanup completed');
            </script>
            """, unsafe_allow_html=True)
        
        # Success celebration
        st.markdown(f"""
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
        # Mobile optimization: Reset generation state on failure
        st.session_state["generation_in_progress"] = False
        if MOBILE_OPTIMIZATION_AVAILABLE:
            st.markdown("""
            <script>
            // Mobile optimization: Stop keep-alive and cleanup on failure
            if (typeof stopMobileOptimization === 'function') {
                stopMobileOptimization();
            }
            console.log('Mobile optimization cleanup completed (failure)');
            </script>
            """, unsafe_allow_html=True)
        
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
