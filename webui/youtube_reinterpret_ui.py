import streamlit as st

from app.services import llm
from app.services.youtube_analyzer import (
    analyze_and_reinterpret_content,
    extract_key_topics,
    extract_video_id,
    get_video_info,
    get_video_transcript,
)


def _new_title(original_title: str, script: str) -> str:
    prompt = f"""
다음 대본에 어울리는 한국어 유튜브 쇼츠 제목 하나를 작성하세요.
원본 제목과 문구를 복사하지 말고, 과장이나 허위 표현 없이 새 제목으로 작성하세요.
제목만 출력하세요. 45자 이내로 작성하세요.

원본 제목(참고만): {original_title}
새 대본: {script[:1800]}
"""
    title = llm._generate_response(prompt).strip().strip('"').strip("'")
    return title[:60] if title else "새롭게 정리한 생활 정보"


def render_youtube_reinterpret_section():
    st.markdown("#### 🔗 참고할 YouTube 영상")
    st.caption(
        "공개 자막에서 핵심 정보만 참고해 새 제목·새 구성·새 문장으로 대본을 만듭니다. "
        "원본 영상, 음성, 썸네일과 배경은 복사하지 않습니다."
    )

    youtube_url = st.text_input(
        "YouTube 링크",
        placeholder="https://youtube.com/shorts/... 또는 https://youtu.be/...",
        key="reinterpret_youtube_url",
    )
    manual_transcript = st.text_area(
        "자막을 가져오지 못할 때 사용할 원본 내용 (선택)",
        placeholder="자동 자막이 없는 영상이라면 내용을 여기에 붙여 넣으세요.",
        height=130,
        key="reinterpret_manual_transcript",
    )

    if st.button("🎬 분석하고 새 영상 만들기", key="reinterpret_analyze", type="primary", use_container_width=True):
        video_id = extract_video_id(youtube_url) if youtube_url.strip() else None
        if not video_id and not manual_transcript.strip():
            st.error("올바른 YouTube 링크를 입력하거나 원본 내용을 붙여 넣어주세요.")
        else:
            with st.spinner("핵심 내용을 분석하고 독립적인 새 대본을 작성하는 중입니다..."):
                video_info = get_video_info(video_id) if video_id else {
                    "title": "사용자 입력 내용", "author": "", "thumbnail": ""
                }
                transcript = get_video_transcript(video_id) if video_id else None
                if not transcript:
                    transcript = manual_transcript.strip()

                if not transcript:
                    st.error("이 영상에서는 공개 자막을 가져올 수 없습니다. 원본 내용을 직접 붙여 넣어주세요.")
                elif len(transcript) < 80:
                    st.error("분석할 내용이 너무 짧습니다. 내용을 조금 더 입력해주세요.")
                else:
                    script = analyze_and_reinterpret_content(transcript, video_info)
                    if not script or "실패했습니다" in script:
                        st.error("새 대본을 만들지 못했습니다. 잠시 후 다시 시도해주세요.")
                    else:
                        title = _new_title(video_info.get("title", ""), script)
                        topics = extract_key_topics(script)
                        terms = llm.generate_terms(title, script, amount=5) or topics
                        st.session_state.pop("reinterpret_result_title", None)
                        st.session_state.pop("reinterpret_result_script", None)
                        st.session_state["reinterpret_result"] = {
                            "title": title,
                            "script": script,
                            "terms": terms,
                            "source_title": video_info.get("title", ""),
                            "thumbnail": video_info.get("thumbnail", ""),
                        }
                        st.session_state["reinterpret_pending_video"] = st.session_state["reinterpret_result"]
                        st.session_state["reinterpret_start_generation"] = True
                        st.rerun()

    result = st.session_state.get("reinterpret_result")
    if result:
        st.success("새로운 구성의 대본으로 영상 생성을 시작했습니다.")
        if result.get("source_title"):
            st.caption(f"참고한 영상: {result['source_title']}")
        st.text_input("새 제목", value=result["title"], key="reinterpret_result_title")
        st.text_area("새 대본", value=result["script"], height=260, key="reinterpret_result_script")
        st.write("검색 키워드: " + ", ".join(result.get("terms", [])))
