"""
YouTube 영상 분석 & 재해석 전용 UI 컴포넌트
기존 영상생성 UI와 완전히 분리된 독립적인 모듈
"""

import streamlit as st
import time
import os
import sys
import importlib
from typing import Dict, Any, Optional
from loguru import logger

# 모듈 강제 재로드 (개발 중에만 사용)
def force_reload_youtube_modules():
    """YouTube 관련 모듈들을 강제로 재로드"""
    modules_to_reload = [
        'app.services.youtube_reinterpret',
        'app.services.youtube_analyzer'
    ]
    
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])

# 개발 중에는 항상 최신 코드 사용
try:
    force_reload_youtube_modules()
except:
    pass

from app.services.youtube_reinterpret import youtube_reinterpret_service
from app.models.schema import VideoParams, VideoAspect


def render_youtube_reinterpret_section():
    """YouTube 영상 분석 & 재해석 섹션 렌더링"""
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(255, 193, 7, 0.1) 0%, rgba(255, 152, 0, 0.1) 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border-left: 4px solid #ffc107;
    ">
        <h3 style="color: #ff8f00; margin: 0 0 0.5rem 0;">🎯 YouTube 영상 분석 & 재해석</h3>
        <p style="margin: 0; color: #666;">
            기존 YouTube 영상을 AI로 분석하고 새로운 관점으로 재해석하여 완전히 새로운 콘텐츠를 만들어보세요.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 단계별 탭 구성
    tab_analyze, tab_reinterpret, tab_generate = st.tabs([
        "📊 1단계: 영상 분석",
        "🎨 2단계: 콘텐츠 재해석", 
        "🎬 3단계: 새 영상 생성"
    ])
    
    with tab_analyze:
        render_analysis_tab()
    
    with tab_reinterpret:
        render_reinterpret_tab()
    
    with tab_generate:
        render_generation_tab()


def render_analysis_tab():
    """영상 분석 탭"""
    
    st.markdown("### 📊 YouTube 영상 분석")
    st.markdown("분석하고 싶은 YouTube 영상의 URL을 입력하세요.")
    
    # YouTube URL 입력
    col_url, col_analyze = st.columns([0.7, 0.3])
    
    with col_url:
        youtube_url = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            key="reinterpret_youtube_url",
            help="분석할 YouTube 영상의 URL을 입력하세요. 자막이 있는 공개 영상이어야 합니다."
        )
        
        # URL 형식 안내
        if youtube_url and not any(domain in youtube_url.lower() for domain in ['youtube.com', 'youtu.be']):
            st.warning("⚠️ 올바른 YouTube URL 형식을 입력해주세요")
            st.info("💡 지원되는 형식:\n- https://www.youtube.com/watch?v=VIDEO_ID\n- https://youtu.be/VIDEO_ID\n- https://m.youtube.com/watch?v=VIDEO_ID")
    
    with col_analyze:
        st.markdown("<br>", unsafe_allow_html=True)  # 높이 맞춤
        analyze_button = st.button(
            "🔍 영상 분석",
            use_container_width=True,
            type="primary",
            key="analyze_youtube_btn",
            disabled=not youtube_url or not any(domain in youtube_url.lower() for domain in ['youtube.com', 'youtu.be'])
        )
    
    # 분석 실행
    if analyze_button and youtube_url:
        # 디버그 정보 표시
        st.info(f"🔍 입력된 URL: `{youtube_url}`")
        
        # URL 추출 테스트
        try:
            from app.services.youtube_reinterpret import youtube_reinterpret_service
            video_id = youtube_reinterpret_service._extract_video_id(youtube_url)
            if video_id:
                st.success(f"✅ 비디오 ID 추출 성공: `{video_id}`")
            else:
                st.error("❌ 비디오 ID 추출 실패")
                st.stop()
        except Exception as e:
            st.error(f"❌ URL 추출 오류: {e}")
            st.stop()
        
        with st.spinner("🔍 YouTube 영상을 분석하고 있습니다..."):
            analysis_result = youtube_reinterpret_service.analyze_youtube_video(youtube_url)
            
            if analysis_result["success"]:
                st.session_state["youtube_analysis"] = analysis_result
                st.success("✅ 영상 분석이 완료되었습니다!")
                
                # 분석 결과 표시
                display_analysis_result(analysis_result)
                
            else:
                st.error(f"❌ 분석 실패: {analysis_result['error']}")
                # 추가 디버그 정보
                st.json(analysis_result)
    
    elif analyze_button and not youtube_url:
        st.warning("⚠️ YouTube URL을 입력해주세요.")
    
    # 기존 분석 결과가 있으면 표시
    if "youtube_analysis" in st.session_state and st.session_state["youtube_analysis"]["success"]:
        st.markdown("---")
        st.markdown("### 📋 이전 분석 결과")
        display_analysis_result(st.session_state["youtube_analysis"])


def display_analysis_result(analysis_result: Dict[str, Any]):
    """분석 결과 표시"""
    
    metadata = analysis_result.get("metadata", {})
    content_analysis = analysis_result.get("content_analysis", {})
    
    # 기본 정보
    st.markdown("#### 📹 영상 정보")
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.info(f"**제목:** {metadata.get('title', 'N/A')}")
        st.info(f"**채널:** {metadata.get('channel', 'N/A')}")
    
    with col_info2:
        view_count = metadata.get('view_count', 'N/A')
        if isinstance(view_count, (int, float)):
            st.info(f"**조회수:** {view_count:,}")
        else:
            st.info(f"**조회수:** {view_count}")
        st.info(f"**길이:** {metadata.get('duration', 'N/A')}")
    
    # 콘텐츠 분석 결과
    if content_analysis:
        st.markdown("#### 🧠 AI 분석 결과")
        
        col_analysis1, col_analysis2 = st.columns(2)
        
        with col_analysis1:
            if "main_topics" in content_analysis:
                st.markdown("**주요 주제:**")
                for topic in content_analysis["main_topics"][:5]:
                    st.write(f"• {topic}")
            
            if "target_audience" in content_analysis:
                st.markdown(f"**타겟 오디언스:** {content_analysis['target_audience']}")
            
            if "content_style" in content_analysis:
                st.markdown(f"**콘텐츠 스타일:** {content_analysis['content_style']}")
        
        with col_analysis2:
            if "keywords" in content_analysis:
                st.markdown("**핵심 키워드:**")
                keywords = content_analysis["keywords"][:8]
                st.write(", ".join(keywords))
            
            if "emotional_tone" in content_analysis:
                st.markdown(f"**감정적 톤:** {content_analysis['emotional_tone']}")
            
            if "credibility" in content_analysis:
                st.markdown(f"**신뢰성:** {content_analysis['credibility']}")
        
        # 재해석 포인트
        if "reinterpret_points" in content_analysis:
            st.markdown("**재해석 가능 포인트:**")
            for point in content_analysis["reinterpret_points"][:3]:
                st.write(f"💡 {point}")


def render_reinterpret_tab():
    """콘텐츠 재해석 탭"""
    
    st.markdown("### 🎨 콘텐츠 재해석")
    
    # 분석 결과 확인
    if "youtube_analysis" not in st.session_state or not st.session_state["youtube_analysis"]["success"]:
        st.warning("⚠️ 먼저 1단계에서 YouTube 영상을 분석해주세요.")
        return
    
    st.markdown("분석된 콘텐츠를 어떤 방식으로 재해석할지 설정하세요.")
    
    # 재해석 옵션 설정
    col_style, col_audience, col_focus = st.columns(3)
    
    with col_style:
        reinterpret_style = st.selectbox(
            "재해석 스타일",
            options=["creative", "educational", "entertaining", "professional", "casual"],
            format_func=lambda x: {
                "creative": "🎨 창의적",
                "educational": "📚 교육적", 
                "entertaining": "🎭 재미있게",
                "professional": "💼 전문적",
                "casual": "😊 친근하게"
            }[x],
            key="reinterpret_style"
        )
    
    with col_audience:
        target_audience = st.selectbox(
            "타겟 오디언스",
            options=["general", "young", "professional", "students", "seniors"],
            format_func=lambda x: {
                "general": "👥 일반 대중",
                "young": "🧑‍💼 젊은 세대",
                "professional": "👔 전문가",
                "students": "🎓 학습자",
                "seniors": "👴 중장년층"
            }[x],
            key="target_audience"
        )
    
    with col_focus:
        content_focus = st.selectbox(
            "콘텐츠 초점",
            options=["main_points", "details", "practical", "theoretical", "examples"],
            format_func=lambda x: {
                "main_points": "🎯 핵심 포인트",
                "details": "🔍 세부 내용",
                "practical": "🛠️ 실용적 측면",
                "theoretical": "📖 이론적 배경",
                "examples": "💡 구체적 예시"
            }[x],
            key="content_focus"
        )
    
    # 재해석 실행
    col_preview, col_reinterpret = st.columns([0.6, 0.4])
    
    with col_preview:
        st.markdown("#### 📋 재해석 미리보기")
        original_title = st.session_state["youtube_analysis"]["metadata"].get("title", "")
        st.write(f"**원본 제목:** {original_title}")
        st.write(f"**재해석 스타일:** {reinterpret_style}")
        st.write(f"**타겟 오디언스:** {target_audience}")
        st.write(f"**콘텐츠 초점:** {content_focus}")
    
    with col_reinterpret:
        st.markdown("<br>", unsafe_allow_html=True)
        reinterpret_button = st.button(
            "🎨 재해석 시작",
            use_container_width=True,
            type="primary",
            key="reinterpret_content_btn"
        )
    
    # 재해석 실행
    if reinterpret_button:
        with st.spinner("🎨 AI가 콘텐츠를 재해석하고 있습니다..."):
            try:
                reinterpret_result = youtube_reinterpret_service.reinterpret_content(
                    analysis_result=st.session_state["youtube_analysis"],
                    reinterpret_style=reinterpret_style,
                    target_audience=target_audience,
                    content_focus=content_focus
                )
                
                if reinterpret_result["success"]:
                    st.session_state["reinterpret_result"] = reinterpret_result
                    st.success("✅ 콘텐츠 재해석이 완료되었습니다!")
                    
                    # 재해석 결과는 아래 기존 결과 표시 부분에서 자동으로 표시됨
                    
                else:
                    st.error(f"❌ 재해석 실패: {reinterpret_result['error']}")
                    st.json(reinterpret_result)
                    
            except Exception as e:
                st.error(f"❌ 재해석 처리 중 예외 발생: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    # 기존 재해석 결과가 있으면 표시
    if "reinterpret_result" in st.session_state and st.session_state["reinterpret_result"]["success"]:
        st.markdown("---")
        st.markdown("### 📋 재해석 결과")
        display_reinterpret_result(st.session_state["reinterpret_result"])


def display_reinterpret_result(reinterpret_result: Dict[str, Any]):
    """재해석 결과 표시"""
    
    reinterpreted_content = reinterpret_result.get("reinterpreted_content", {})
    
    # 새로운 제목
    if "new_title" in reinterpreted_content:
        st.markdown("#### 🎯 새로운 제목")
        st.success(reinterpreted_content["new_title"])
    
    # 새로운 대본
    if "new_script" in reinterpreted_content:
        st.markdown("#### 📝 새로운 대본")
        st.text_area(
            "재해석된 대본",
            value=reinterpreted_content["new_script"],
            height=200,
            disabled=True,
            key="unique_reinterpreted_script_display"
        )
    
    # 키워드와 추가 정보
    col_keywords, col_points = st.columns(2)
    
    with col_keywords:
        if "keywords" in reinterpreted_content:
            st.markdown("#### 🏷️ 핵심 키워드")
            st.info(reinterpreted_content["keywords"])
    
    with col_points:
        if "reinterpret_points" in reinterpreted_content:
            st.markdown("#### 💡 재해석 포인트")
            st.info(reinterpreted_content["reinterpret_points"])
    
    # 예상 반응
    if "expected_reaction" in reinterpreted_content:
        st.markdown("#### 📊 예상 시청자 반응")
        st.write(reinterpreted_content["expected_reaction"])


def render_generation_tab():
    """새 영상 생성 탭"""
    
    st.markdown("### 🎬 새 영상 생성")
    
    # 재해석 결과 확인
    if "reinterpret_result" not in st.session_state or not st.session_state["reinterpret_result"]["success"]:
        st.warning("⚠️ 먼저 2단계에서 콘텐츠를 재해석해주세요.")
        return
    
    st.markdown("재해석된 콘텐츠로 새로운 영상을 생성합니다.")
    
    # 영상 생성 옵션
    col_options1, col_options2 = st.columns(2)
    
    with col_options1:
        video_aspect = st.selectbox(
            "영상 비율",
            options=["portrait", "landscape", "square"],
            format_func=lambda x: {
                "portrait": "📱 세로형 (9:16) - 쇼츠",
                "landscape": "🖥️ 가로형 (16:9) - 일반",
                "square": "⬜ 정사각형 (1:1)"
            }[x],
            index=0,  # 기본값: 세로형
            key="reinterpret_video_aspect"
        )
        
        voice_name = st.selectbox(
            "음성 선택",
            options=[
                "ko-KR-SunHiNeural",
                "ko-KR-InJoonNeural", 
                "ko-KR-BongJinNeural",
                "ko-KR-GookMinNeural"
            ],
            format_func=lambda x: {
                "ko-KR-SunHiNeural": "👩 선희 (여성, 친근함)",
                "ko-KR-InJoonNeural": "👨 인준 (남성, 차분함)",
                "ko-KR-BongJinNeural": "👨 봉진 (남성, 활기참)",
                "ko-KR-GookMinNeural": "👨 국민 (남성, 안정감)"
            }[x],
            key="reinterpret_voice_name"
        )
    
    with col_options2:
        subtitle_enabled = st.checkbox(
            "자막 활성화",
            value=True,
            key="reinterpret_subtitle_enabled"
        )
        
        auto_upload = st.checkbox(
            "생성 후 자동 업로드",
            value=False,
            key="reinterpret_auto_upload"
        )
    
    # 생성 미리보기
    st.markdown("#### 📋 생성 미리보기")
    reinterpreted_content = st.session_state["reinterpret_result"]["reinterpreted_content"]
    
    col_preview1, col_preview2 = st.columns(2)
    
    with col_preview1:
        st.write(f"**제목:** {reinterpreted_content.get('new_title', 'N/A')}")
        st.write(f"**영상 비율:** {video_aspect}")
        st.write(f"**음성:** {voice_name}")
    
    with col_preview2:
        st.write(f"**자막:** {'활성화' if subtitle_enabled else '비활성화'}")
        st.write(f"**자동 업로드:** {'예' if auto_upload else '아니오'}")
        st.write(f"**키워드:** {reinterpreted_content.get('keywords', 'N/A')[:50]}...")
    
    # 영상 생성 버튼
    st.markdown("---")
    col_generate_btn = st.columns([0.3, 0.4, 0.3])[1]  # 중앙 정렬
    
    with col_generate_btn:
        generate_button = st.button(
            "🎬 재해석 영상 생성",
            use_container_width=True,
            type="primary",
            key="generate_reinterpreted_video_btn"
        )
    
    # 영상 생성 실행
    if generate_button:
        # VideoParams 설정
        video_params = VideoParams()
        video_params.video_aspect = getattr(VideoAspect, video_aspect)
        video_params.voice_name = voice_name
        video_params.subtitle_enabled = subtitle_enabled
        video_params.video_language = "ko-KR"
        
        # 영상 생성 진행 상황 표시
        progress_container = st.empty()
        status_container = st.empty()
        
        with st.spinner("🎬 재해석된 콘텐츠로 새로운 영상을 생성하고 있습니다..."):
            generation_result = youtube_reinterpret_service.generate_reinterpreted_video(
                reinterpret_result=st.session_state["reinterpret_result"],
                video_params=video_params
            )
            
            if generation_result["success"]:
                st.success("🎉 재해석 영상 생성이 완료되었습니다!")
                
                # 생성된 영상 정보 표시
                display_generation_result(generation_result)
                
                # 자동 업로드 처리
                if auto_upload:
                    handle_auto_upload(generation_result)
                
            else:
                st.error(f"❌ 영상 생성 실패: {generation_result['error']}")


def display_generation_result(generation_result: Dict[str, Any]):
    """영상 생성 결과 표시"""
    
    st.markdown("#### 🎉 생성 완료!")
    
    video_files = generation_result.get("video_files", [])
    reinterpret_info = generation_result.get("reinterpret_info", {})
    
    # 생성된 영상 정보
    col_result1, col_result2 = st.columns(2)
    
    with col_result1:
        st.info(f"**생성된 영상 수:** {len(video_files)}개")
        st.info(f"**원본 영상 ID:** {reinterpret_info.get('original_video_id', 'N/A')}")
    
    with col_result2:
        st.info(f"**재해석 스타일:** {reinterpret_info.get('reinterpret_style', 'N/A')}")
        st.info(f"**타겟 오디언스:** {reinterpret_info.get('target_audience', 'N/A')}")
    
    # 다운로드 버튼
    for i, video_file in enumerate(video_files):
        if os.path.exists(video_file):
            with open(video_file, "rb") as f:
                st.download_button(
                    label=f"📥 영상 다운로드 {i+1}",
                    data=f.read(),
                    file_name=os.path.basename(video_file),
                    mime="video/mp4",
                    use_container_width=True,
                    key=f"download_reinterpreted_video_{i}"
                )


def handle_auto_upload(generation_result: Dict[str, Any]):
    """자동 업로드 처리"""
    
    try:
        from app.utils.youtube import get_authenticated_service, upload_video
        import os
        
        # YouTube 인증 확인
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        token_file = os.path.join(root_dir, "token.pickle")
        client_secrets_file = os.path.join(root_dir, "client_secrets.json")
        
        if not os.path.exists(token_file) or not os.path.exists(client_secrets_file):
            st.warning("⚠️ YouTube 인증이 필요합니다. '고급 설정'에서 인증을 완료해주세요.")
            return
        
        video_files = generation_result.get("video_files", [])
        reinterpret_info = generation_result.get("reinterpret_info", {})
        
        for video_file in video_files:
            if os.path.exists(video_file):
                with st.spinner(f"📺 YouTube 업로드 중: {os.path.basename(video_file)}"):
                    try:
                        youtube = get_authenticated_service(client_secrets_file, token_file)
                        
                        # 업로드 정보 설정
                        title = f"[재해석] {os.path.basename(video_file).replace('.mp4', '')}"
                        description = f"AI로 재해석된 콘텐츠\n\n재해석 스타일: {reinterpret_info.get('reinterpret_style', 'N/A')}\n타겟 오디언스: {reinterpret_info.get('target_audience', 'N/A')}"
                        
                        video_id = upload_video(
                            youtube=youtube,
                            video_path=video_file,
                            title=title[:100],
                            description=description,
                            category="22",  # People & Blogs
                            keywords="재해석,AI,콘텐츠",
                            privacy_status="private"
                        )
                        
                        if video_id:
                            video_url = f"https://youtube.com/watch?v={video_id}"
                            st.success(f"🎉 업로드 성공! [영상 보기]({video_url})")
                        else:
                            st.error("❌ 업로드 실패")
                            
                    except Exception as e:
                        st.error(f"❌ 업로드 오류: {e}")
        
    except Exception as e:
        logger.error(f"Auto upload error: {e}")
        st.error(f"❌ 자동 업로드 처리 중 오류: {e}")