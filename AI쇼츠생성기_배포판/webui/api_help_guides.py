# -*- coding: utf-8 -*-
"""API 발급 도움말 가이드"""

import streamlit as st


def show_gemini_api_guide():
    """Gemini API 키 발급 가이드"""
    st.info("""
**🔑 Gemini API 키 발급 방법**

**1단계:** [Google AI Studio](https://aistudio.google.com/app/apikey) 접속 → Google 계정 로그인

**2단계:** "Get API key" 또는 "Create API key" 버튼 클릭

**3단계:** "Create API key in new project" 선택

**4단계:** 생성된 API 키 복사 (AIza로 시작)

**5단계:** 위의 입력란에 붙여넣기

💡 **무료 할당량:** Gemini 2.5 Flash 분당 15회, 일일 1,500회

💡 **여러 키 사용:** 할당량 초과 시 자동으로 다른 키로 전환 (최대 10개)
    """)
    st.markdown("[🔗 Google AI Studio 바로가기](https://aistudio.google.com/app/apikey)")



def show_pexels_api_guide():
    """Pexels API 키 발급 가이드"""
    st.info("""
**🌟 Pexels API 키 발급 방법**

**1단계:** [Pexels 홈페이지](https://www.pexels.com) 접속 → 회원가입

**2단계:** [Pexels API 페이지](https://www.pexels.com/api/) 접속

**3단계:** "Get Started" 클릭 → 사용 목적 작성 (예: "Video creation")

**4단계:** 즉시 발급된 API 키 복사

**5단계:** 위의 입력란에 붙여넣기 → "➕ Pexels 키 추가" 클릭

💡 **무료 플랜:** 시간당 200회, 월간 제한 없음, 상업적 이용 가능

💡 **콘텐츠:** 고품질 4K 비디오, 크레딧 표시 불필요
    """)
    st.markdown("[🔗 Pexels API 바로가기](https://www.pexels.com/api/)")



def show_pixabay_api_guide():
    """Pixabay API 키 발급 가이드"""
    st.info("""
**🎨 Pixabay API 키 발급 방법**

**1단계:** [Pixabay 홈페이지](https://pixabay.com) 접속 → 회원가입

**2단계:** 이메일 인증 완료

**3단계:** [Pixabay API 문서](https://pixabay.com/api/docs/) 접속 (로그인 상태)

**4단계:** 페이지 상단 "Your API key:" 섹션에서 API 키 확인 (숫자로 구성)

**5단계:** 위의 입력란에 붙여넣기 → "➕ Pixabay 키 추가" 클릭

💡 **무료 플랜:** 분당 100회, 시간당 5,000회, 상업적 이용 가능

💡 **콘텐츠:** 280만+ 이미지/비디오, HD/4K 지원, 크레딧 표시 불필요
    """)
    st.markdown("[🔗 Pixabay API 바로가기](https://pixabay.com/api/docs/)")



def show_youtube_oauth_guide():
    """YouTube OAuth 인증 설정 가이드"""
    st.info("""
**📺 YouTube OAuth 인증 설정 방법**

**1단계:** [Google Cloud Console](https://console.cloud.google.com/) 접속 → 새 프로젝트 생성

**2단계:** "API 및 서비스" > "라이브러리" → "YouTube Data API v3" 검색 → "사용" 클릭

**3단계:** "OAuth 동의 화면" 구성
- User Type: "외부" 선택
- 앱 이름, 이메일 입력
- 테스트 사용자에 본인 이메일 추가

**4단계:** "사용자 인증 정보" → "+ 사용자 인증 정보 만들기" → "OAuth 클라이언트 ID"
- 애플리케이션 유형: "데스크톱 앱" 선택
- 이름 입력 후 "만들기"

**5단계:** "JSON 다운로드" 클릭 → 파일명을 `client_secrets.json`으로 변경

**6단계:** 위의 업로드 버튼으로 파일 업로드

**7단계:** "🔐 YouTube 인증 시작" 버튼 클릭 → 브라우저에서 권한 승인

💡 **할당량:** 일일 10,000 유닛 (하루 약 6개 영상 업로드 가능)

⚠️ **주의:** client_secrets.json은 절대 공개하지 마세요!
    """)
    st.markdown("[🔗 Google Cloud Console 바로가기](https://console.cloud.google.com/)")
    
    st.warning("""
**❓ 문제 해결**

**"앱이 차단됨" 오류:** OAuth 동의 화면에서 본인 이메일을 테스트 사용자로 추가

**"redirect_uri_mismatch" 오류:** 데스크톱 앱 유형으로 생성했는지 확인

**인증 토큰 만료:** token.pickle 파일 삭제 후 재인증
    """)


def show_api_help_button(api_type: str):
    """API 발급 도움말 표시
    
    Args:
        api_type: "gemini", "pexels", "pixabay", "youtube"
    """
    guide_functions = {
        "gemini": show_gemini_api_guide,
        "pexels": show_pexels_api_guide,
        "pixabay": show_pixabay_api_guide,
        "youtube": show_youtube_oauth_guide,
    }
    
    if api_type not in guide_functions:
        return
    
    # 가이드 직접 표시 (expander 중첩 방지)
    guide_functions[api_type]()
