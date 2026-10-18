# -*- coding: utf-8 -*-
"""API 발급 도움말 가이드"""

import streamlit as st


def show_gemini_api_guide():
    """Gemini API 키 발급 가이드"""
    st.info("""
**🔑 Gemini API 키 발급 방법**

Gemini는 **영상 대본을 만드는 데 꼭 필요**합니다.

**1단계:** [Google AI Studio](https://aistudio.google.com/app/apikey)에 접속하고 Google 계정으로 로그인합니다.

**2단계:** 화면의 **Get API key** 또는 **Create API key**를 누릅니다.

**3단계:** 프로젝트를 묻는다면 **새 프로젝트에서 API 키 만들기**를 선택합니다.

**4단계:** 생성된 긴 영문·숫자 키 오른쪽의 **복사 아이콘**을 누릅니다. 보통 `AIza`로 시작합니다.

**5단계:** 이 안내를 닫고 **새 Gemini API 키** 칸에 붙여넣은 뒤 **API 키 저장**을 누릅니다.

**6단계:** 화면 위의 Gemini 상태가 `✅ 설정됨`으로 표시되면 완료입니다.

💡 무료 사용 가능 여부와 할당량은 Google AI Studio의 현재 정책을 확인하세요.

🔒 발급한 키는 다른 사람에게 전달하거나 공개 저장소에 올리지 마세요.
    """)
    st.markdown("[🔗 Google AI Studio 바로가기](https://aistudio.google.com/app/apikey)")



def show_pexels_api_guide():
    """Pexels API 키 발급 가이드"""
    st.info("""
**🌟 Pexels API 키 발급 방법**

Pexels 키는 배경 방식을 **Pexels 무료 영상**으로 사용할 때 필요합니다.

**1단계:** [Pexels 홈페이지](https://www.pexels.com)에 접속해 회원가입하고 로그인합니다.

**2단계:** [Pexels API 페이지](https://www.pexels.com/api/)로 이동합니다.

**3단계:** **Get Started** 또는 API 키 요청 버튼을 누릅니다.

**4단계:** 사용 목적을 묻는다면 `YouTube shorts video creation`처럼 입력하고 신청을 완료합니다.

**5단계:** 발급된 긴 API 키를 빠짐없이 복사합니다.

**6단계:** 이 안내를 닫고 **새 Pexels API 키** 칸에 붙여넣은 뒤 **API 키 저장**을 누릅니다.

**7단계:** Pexels 상태가 `1개 설정됨` 이상이면 완료입니다.

💡 요청 한도와 콘텐츠 사용 조건은 Pexels API 페이지의 현재 정책을 확인하세요.
    """)
    st.markdown("[🔗 Pexels API 바로가기](https://www.pexels.com/api/)")



def show_pixabay_api_guide():
    """Pixabay API 키 발급 가이드"""
    st.info("""
**🎨 Pixabay API 키 발급 방법**

Pixabay 키는 배경 방식을 **Pixabay 무료 영상**으로 사용할 때 필요합니다.

**1단계:** [Pixabay 홈페이지](https://pixabay.com)에 접속해 회원가입하고 로그인합니다.

**2단계:** 가입 이메일로 온 인증 메일을 열어 이메일 인증을 완료합니다.

**3단계:** 로그인한 상태에서 [Pixabay API 문서](https://pixabay.com/api/docs/)로 이동합니다.

**4단계:** 페이지의 **Your API key** 부분에 표시된 키를 복사합니다.

**5단계:** 이 안내를 닫고 **새 Pixabay API 키** 칸에 붙여넣은 뒤 **API 키 저장**을 누릅니다.

**6단계:** Pixabay 상태가 `1개 설정됨` 이상이면 완료입니다.

💡 요청 한도와 콘텐츠 사용 조건은 Pixabay API 페이지의 현재 정책을 확인하세요.
    """)
    st.markdown("[🔗 Pixabay API 바로가기](https://pixabay.com/api/docs/)")



def show_youtube_oauth_guide():
    """YouTube OAuth 인증 설정 가이드"""
    st.info("""
**📺 처음 하는 분을 위한 YouTube 연결 방법**

준비물은 **영상을 올릴 YouTube 채널이 있는 Google 계정**입니다. 아래 순서를 한 단계씩 진행하세요.

**1. Google Cloud에 작업 공간 만들기**

1) 아래의 **Google Cloud Console 바로가기**를 누르고 YouTube 채널의 Google 계정으로 로그인합니다.  
2) 화면 위쪽의 프로젝트 이름을 누릅니다. 처음이면 `프로젝트 선택`으로 표시될 수 있습니다.  
3) 오른쪽 위의 **새 프로젝트**를 누릅니다.  
4) 프로젝트 이름에 `쇼츠 자동 업로드`처럼 알아보기 쉬운 이름을 쓰고 **만들기**를 누릅니다.  
5) 만든 프로젝트가 화면 위쪽에 선택되어 있는지 확인합니다.

**2. YouTube 업로드 기능 켜기**

1) 왼쪽 메뉴에서 **API 및 서비스 → 라이브러리**로 들어갑니다.  
2) 검색창에 `YouTube Data API v3`를 입력합니다.  
3) 검색 결과의 **YouTube Data API v3**를 누릅니다.  
4) **사용** 버튼을 누릅니다. 이미 `관리`라고 나오면 켜져 있는 상태입니다.

**3. 앱 정보 등록하기**

1) 왼쪽 메뉴의 **Google Auth Platform** 또는 **API 및 서비스 → OAuth 동의 화면**으로 들어갑니다.  
2) 처음 설정하는 경우 **시작하기**를 누릅니다.  
3) 앱 이름은 `쇼츠 자동 업로드`, 사용자 지원 이메일은 **본인 이메일**을 선택합니다.  
4) 대상 또는 사용자 유형을 묻는다면 개인 Gmail 계정은 **외부(External)**를 선택합니다.  
5) 연락처 이메일에도 본인 이메일을 넣고 생성 또는 저장합니다.  
6) **대상(Audience) → 테스트 사용자(Test users)**에서 **사용자 추가**를 누르고, 실제 YouTube 채널 계정의 이메일을 추가합니다.

**4. 데스크톱용 인증 파일 만들기**

1) **Google Auth Platform → 클라이언트(Clients)**로 들어갑니다. 이전 화면에서는 **API 및 서비스 → 사용자 인증 정보**일 수 있습니다.  
2) **클라이언트 만들기** 또는 **사용자 인증 정보 만들기 → OAuth 클라이언트 ID**를 누릅니다.  
3) 애플리케이션 유형은 반드시 **데스크톱 앱(Desktop app)**을 선택합니다.  
4) 이름은 `쇼츠 프로그램`처럼 입력하고 **만들기**를 누릅니다.  
5) 만들어진 항목의 **JSON 다운로드**를 누릅니다. 내려받은 파일 이름은 길어도 정상입니다.

**5. 이 프로그램에 인증 파일 넣기**

1) 이 도움말을 닫고 **📺 YouTube 연결** 칸으로 돌아갑니다.  
2) `Google OAuth 인증 파일`의 **Browse files**를 누릅니다.  
3) 방금 내려받은 `.json` 파일을 선택합니다. 프로그램이 알맞은 이름으로 저장하므로 직접 파일명을 바꿀 필요가 없습니다.  
4) `인증 파일: ✅ 있음`으로 바뀌는지 확인합니다.

**6. 내 YouTube 계정 승인하기**

1) **YouTube 계정 연결** 버튼을 누릅니다.  
2) Google 로그인 창이 열리면 반드시 **영상을 올릴 채널의 계정**을 선택합니다.  
3) `Google에서 이 앱을 확인하지 않았습니다`가 나오면 **고급 → 쇼츠 자동 업로드(으)로 이동**을 누릅니다. 본인이 직접 만든 앱일 때만 진행하세요.  
4) YouTube 동영상 관리 또는 업로드 권한 화면에서 **계속/허용**을 누릅니다.  
5) 프로그램으로 돌아와 `YouTube 계정: ✅ 연결됨`이라고 나오면 완료입니다.

💡 Google 화면의 메뉴 이름은 계정에 따라 조금 다를 수 있지만, **YouTube Data API v3 사용 → OAuth 데스크톱 앱 생성 → JSON 업로드** 순서는 같습니다.
    """)
    st.markdown("[🔗 Google Cloud Console 바로가기](https://console.cloud.google.com/)")
    st.markdown("[🔗 Google 공식 YouTube 데스크톱 인증 설명](https://developers.google.com/youtube/data/guides/auth/installed-apps)")
    
    st.warning("""
**❓ 막힐 때 확인하세요**

**`access_denied` 또는 앱이 차단됨:** 테스트 사용자에 현재 로그인한 Google 이메일이 들어 있는지 확인하세요.

**`redirect_uri_mismatch`:** OAuth 클라이언트 유형을 웹 앱이 아닌 **데스크톱 앱**으로 다시 만드세요.

**엉뚱한 채널이 연결됨:** 브라우저의 Google 계정을 확인한 뒤 다시 연결해야 합니다.

**인증 파일이 선택되지 않음:** 압축파일이 아니라 Google에서 내려받은 `.json` 파일 하나를 선택하세요.

**보안 주의:** 내려받은 JSON 인증 파일과 `token.pickle`은 비밀번호처럼 보관하고 다른 사람에게 보내거나 공개 저장소에 올리지 마세요.
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
