import os
import time
from urllib.parse import urlparse

import requests
import streamlit as st

from app.config import config
from app.services.mobile_access import enable_mobile_access, get_mobile_access_status
from app.services.customer_readiness import create_backup, restore_backup, run_readiness_checks
from webui.api_help_guides import show_api_help_button


DEFAULT_IMAGE_WORKER_URL = "https://ai-shorts-images.comfreec1.workers.dev"
CUSTOM_WORKER_DEPLOY_URL = (
    "https://deploy.workers.cloudflare.com/"
    "?url=https://github.com/comfreec/youtube-auto/tree/main/image-worker"
)


def _key_count(value) -> int:
    if isinstance(value, list):
        return len([item for item in value if str(item).strip()])
    return 1 if str(value or "").strip() else 0


def _parse_keys(value: str) -> list[str]:
    return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()]


def render_simple_settings(root_dir: str):
    st.markdown("## ⚙️ 설정")
    st.caption("영상 생성에 꼭 필요한 항목만 표시합니다. 나머지는 권장 기본값으로 자동 적용됩니다.")

    with st.popover("❓ API 키·YouTube 설정 도움말", use_container_width=True):
        st.markdown("#### 무엇을 설정해야 하나요?")
        st.markdown(
            "- **Gemini**: 대본 생성에 필요\n"
            "- **Pexels / Pixabay**: 해당 무료 배경 영상을 선택할 때 필요\n"
            "- **YouTube 연결**: 완성된 영상을 자동 업로드할 때만 필요"
        )
        help_type = st.selectbox(
            "도움말 선택",
            options=["gemini", "pexels", "pixabay", "youtube"],
            format_func=lambda value: {
                "gemini": "Gemini API 키 발급",
                "pexels": "Pexels API 키 발급",
                "pixabay": "Pixabay API 키 발급",
                "youtube": "YouTube 계정 연결",
            }[value],
            key="simple_settings_help_type",
        )
        show_api_help_button(help_type)

    source_options = [
        ("🎬 무료 배경 영상 자동 선택", "stock_auto"),
        ("🖼️ 내용맞춤 AI 이미지", "ai_image"),
        ("✨ 간단 애니메이션", "animation"),
    ]
    source_values = [value for _, value in source_options]
    saved_source = str(config.app.get("video_source", "pexels"))
    if saved_source in {"pexels", "pixabay"}:
        saved_source = "stock_auto"
    source_index = source_values.index(saved_source) if saved_source in source_values else 0

    with st.container(border=True):
        st.markdown("### 🎬 기본 배경 방식")
        selected_source = st.selectbox(
            "새 영상에 사용할 기본 배경",
            options=source_values,
            index=source_index,
            format_func=lambda value: dict((v, label) for label, v in source_options)[value],
        )
        if st.button("배경 방식 저장", use_container_width=True, type="primary"):
            config.app["video_source"] = selected_source
            config.save_config()
            st.success("기본 배경 방식을 저장했습니다.")

    voice_options = {
        "ko-KR-SunHiNeural": "👩 선희 · 밝고 친근한 건강·생활정보",
        "ko-KR-InJoonNeural": "👨 인준 · 차분하고 묵직한 인생 조언",
        "ko-KR-HyunsuMultilingualNeural": "👨 현수 · 자연스럽고 중립적인 설명",
    }
    saved_voice = str(config.app.get("korean_voice_name", "ko-KR-SunHiNeural"))
    if saved_voice not in voice_options:
        saved_voice = "ko-KR-SunHiNeural"
    with st.container(border=True):
        st.markdown("### 🎙️ 기본 한국어 성우")
        selected_voice = st.selectbox(
            "새 영상에서 처음 선택될 성우",
            options=list(voice_options),
            index=list(voice_options).index(saved_voice),
            format_func=lambda value: voice_options[value],
            key="simple_default_korean_voice",
        )
        voice_descriptions = {
            "ko-KR-SunHiNeural": "**선희:** 밝고 친근함 — 건강·생활정보 추천",
            "ko-KR-InJoonNeural": "**인준:** 차분하고 묵직함 — 인생 조언 추천",
            "ko-KR-HyunsuMultilingualNeural": "**현수:** 자연스럽고 중립적 — 일반 정보·설명 추천",
        }
        st.info(voice_descriptions[selected_voice])
        st.caption("영상 생성 화면에서 영상마다 다른 성우를 선택할 수도 있습니다. 영어 성우는 바뀌지 않습니다.")
        if st.button("기본 성우 저장", use_container_width=True, key="save_default_korean_voice"):
            config.app["korean_voice_name"] = selected_voice
            config.save_config()
            st.success("기본 한국어 성우를 저장했습니다.")

    with st.expander("🖼️ 내 무료 AI 이미지 서버 연결", expanded=False):
        st.caption("고객마다 자신의 Cloudflare 무료 한도를 사용하므로 다른 고객과 사용량을 나누지 않습니다.")
        st.markdown(
            "**처음 한 번만 따라 하세요.**\n\n"
            "1. 아래 버튼을 눌러 Cloudflare와 GitHub에 로그인합니다.\n"
            "2. 배포 화면에서 기본값을 그대로 두고 **Deploy**를 누릅니다.\n"
            "3. 배포가 끝나면 표시되는 `https://...workers.dev` 주소를 복사합니다.\n"
            "4. 아래 칸에 붙여넣고 **연결 확인 후 저장**을 누릅니다."
        )
        st.link_button(
            "☁️ 내 무료 이미지 서버 만들기",
            CUSTOM_WORKER_DEPLOY_URL,
            use_container_width=True,
            type="primary",
        )

        current_worker = str(config.app.get("ai_image_worker_url", DEFAULT_IMAGE_WORKER_URL)).strip()
        worker_url = st.text_input(
            "내 이미지 서버 주소",
            value=current_worker,
            placeholder="https://내서버이름.내계정.workers.dev",
            key="simple_customer_image_worker_url",
        )
        worker_host = urlparse(current_worker).netloc or "설정되지 않음"
        st.caption(f"현재 연결: {worker_host}")

        worker_col1, worker_col2 = st.columns(2)
        with worker_col1:
            if st.button("연결 확인 후 저장", use_container_width=True, key="save_customer_worker"):
                normalized = worker_url.strip().rstrip("/")
                parsed = urlparse(normalized)
                if parsed.scheme != "https" or not parsed.netloc:
                    st.error("https://로 시작하는 이미지 서버 주소를 입력해주세요.")
                else:
                    try:
                        response = requests.get(f"{normalized}/health", timeout=15)
                        payload = response.json() if response.ok else {}
                        if not response.ok or not payload.get("ok"):
                            raise RuntimeError("이미지 서버 응답이 올바르지 않습니다.")
                        config.app["ai_image_worker_url"] = normalized
                        config.save_config()
                        st.success("내 무료 이미지 서버가 연결되었습니다.")
                    except Exception as exc:
                        st.error(f"연결할 수 없습니다. 배포 완료 후 주소를 다시 확인해주세요. ({exc})")
        with worker_col2:
            if st.button("기본 서버로 되돌리기", use_container_width=True, key="reset_customer_worker"):
                config.app["ai_image_worker_url"] = DEFAULT_IMAGE_WORKER_URL
                config.save_config()
                st.success("기본 이미지 서버로 되돌렸습니다.")
                st.rerun()

    with st.expander("📱 내 모바일 연결 만들기", expanded=False):
        st.caption("고객마다 자기 PC와 휴대폰만 연결되는 무료 전용 주소를 사용합니다.")
        st.markdown(
            "**처음 한 번만 설정하세요.**\n\n"
            "1. PC와 휴대폰에 Tailscale을 설치합니다.\n"
            "2. 두 기기에서 **같은 계정**으로 로그인합니다.\n"
            "3. 아래 **모바일 주소 만들기**를 누릅니다.\n"
            "4. 표시된 주소를 휴대폰 브라우저에서 엽니다."
        )
        st.link_button(
            "Tailscale 무료 설치",
            "https://tailscale.com/download",
            use_container_width=True,
        )
        mobile_status = get_mobile_access_status()
        if mobile_status.get("enabled"):
            mobile_url = mobile_status["mobile_url"]
            st.success("모바일 연결이 준비되었습니다.")
            st.code(mobile_url, language=None)
            st.link_button("📱 모바일 화면 열기", mobile_url, use_container_width=True, type="primary")
            st.caption("주소를 길게 눌러 복사한 뒤 휴대폰으로 보내도 됩니다. PC와 Tailscale은 켜져 있어야 합니다.")
        else:
            if mobile_status.get("connected"):
                st.info(mobile_status.get("message"))
                if st.button("모바일 주소 만들기", use_container_width=True, type="primary", key="enable_mobile_access"):
                    try:
                        enable_mobile_access()
                        st.success("모바일 주소를 만들었습니다.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
            else:
                st.warning(mobile_status.get("message"))
                if st.button("연결 상태 다시 확인", use_container_width=True, key="refresh_mobile_access"):
                    st.rerun()

    with st.expander("✅ 자동 상태점검", expanded=False):
        st.caption("영상 생성 전에 필요한 설정과 PC 상태를 한 번에 확인합니다.")
        if st.button("지금 전체 점검", use_container_width=True, type="primary", key="run_customer_readiness"):
            st.session_state["customer_readiness"] = run_readiness_checks(root_dir)
        readiness = st.session_state.get("customer_readiness")
        if readiness:
            for item in readiness["checks"]:
                if item["ok"]:
                    st.success(f"{item['label']}: {item['message']}")
                elif item["blocking"]:
                    st.error(f"{item['label']}: {item['message']}")
                else:
                    st.warning(f"{item['label']}: {item['message']}")
            if readiness["ready"]:
                st.success("영상 생성에 필요한 필수 항목이 준비되었습니다.")
            else:
                st.error("빨간색 항목을 해결한 뒤 영상 생성을 시작해주세요.")

    with st.expander("💾 전체 설정 백업·복원", expanded=False):
        st.warning("백업에는 API 키와 YouTube 인증이 포함될 수 있습니다. 비밀번호처럼 안전하게 보관하고 다른 사람에게 보내지 마세요.")
        try:
            backup_bytes = create_backup(root_dir)
            st.download_button(
                "전체 설정 백업 다운로드",
                data=backup_bytes,
                file_name=f"youtube_auto_backup_{int(time.time())}.json",
                mime="application/json",
                use_container_width=True,
                key="simple_full_backup_download",
            )
        except Exception as exc:
            st.error(f"백업 파일을 만들 수 없습니다: {exc}")

        uploaded_backup = st.file_uploader(
            "새 PC에서 복원할 백업 파일",
            type=["json"],
            key="simple_full_backup_restore_file",
        )
        if uploaded_backup is not None and st.button(
            "선택한 백업 복원",
            use_container_width=True,
            key="simple_full_backup_restore",
        ):
            try:
                restored = restore_backup(root_dir, uploaded_backup.getvalue())
                st.success("복원 완료: " + ", ".join(restored))
                st.session_state.pop("customer_readiness", None)
                st.rerun()
            except Exception as exc:
                st.error(f"복원할 수 없습니다: {exc}")

    with st.expander("🔑 API 키", expanded=False):
        st.write(f"Gemini: {'✅ 설정됨' if config.app.get('gemini_api_key') else '❌ 미설정'}")
        st.write(f"Pexels: {_key_count(config.app.get('pexels_api_keys'))}개 설정됨")
        st.write(f"Pixabay: {_key_count(config.app.get('pixabay_api_keys'))}개 설정됨")

        api_help_type = st.selectbox(
            "발급 방법을 볼 API",
            options=["gemini", "pexels", "pixabay"],
            format_func=lambda value: {
                "gemini": "Gemini (대본 생성)",
                "pexels": "Pexels (무료 영상)",
                "pixabay": "Pixabay (무료 영상)",
            }[value],
            key="simple_api_inline_help_type",
        )
        with st.popover("❓ 선택한 API 키 발급 방법 보기", use_container_width=True):
            show_api_help_button(api_help_type)

        st.caption("변경할 항목만 입력하세요. 빈칸은 기존 값을 유지합니다.")

        with st.form("simple_api_settings"):
            gemini_key = st.text_input("새 Gemini API 키", type="password")
            pexels_keys = st.text_area("새 Pexels API 키", placeholder="여러 개면 쉼표 또는 줄바꿈으로 구분")
            pixabay_keys = st.text_area("새 Pixabay API 키", placeholder="여러 개면 쉼표 또는 줄바꿈으로 구분")
            if st.form_submit_button("API 키 저장", use_container_width=True):
                if gemini_key.strip():
                    config.app["gemini_api_key"] = gemini_key.strip()
                if pexels_keys.strip():
                    config.app["pexels_api_keys"] = _parse_keys(pexels_keys)
                if pixabay_keys.strip():
                    config.app["pixabay_api_keys"] = _parse_keys(pixabay_keys)
                config.app["llm_provider"] = "gemini"
                config.save_config()
                st.success("API 설정을 저장했습니다.")

    with st.expander("📺 YouTube 연결", expanded=False):
        client_secrets_file = os.path.join(root_dir, "client_secrets.json")
        token_file = os.path.join(root_dir, "token.pickle")
        has_secrets = os.path.exists(client_secrets_file)
        has_token = os.path.exists(token_file)

        st.write(f"인증 파일: {'✅ 있음' if has_secrets else '❌ 없음'}")
        st.write(f"YouTube 계정: {'✅ 연결됨' if has_token else '❌ 연결 안 됨'}")

        with st.popover("❓ YouTube 연결 방법 보기", use_container_width=True):
            show_api_help_button("youtube")

        if not has_secrets:
            uploaded = st.file_uploader("Google OAuth 인증 파일", type=["json"], key="simple_youtube_secrets")
            if uploaded is not None:
                with open(client_secrets_file, "wb") as file:
                    file.write(uploaded.getbuffer())
                st.success("인증 파일을 저장했습니다.")
                st.rerun()

        if has_secrets and not has_token:
            if st.button("YouTube 계정 연결", use_container_width=True):
                try:
                    from app.utils.youtube import get_authenticated_service

                    get_authenticated_service(client_secrets_file, token_file)
                    st.success("YouTube 계정을 연결했습니다.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"YouTube 연결 실패: {exc}")

    st.info("선희 성우, 음성 속도, 자막, 세로 화면, BGM 볼륨은 권장 기본값으로 자동 적용됩니다.")
