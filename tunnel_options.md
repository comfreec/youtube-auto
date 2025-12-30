# 🌐 터널 고정 주소 옵션

## 1️⃣ Cloudflare Tunnel (무료, 계정 필요)
```bash
# 1. 계정 생성: https://dash.cloudflare.com
# 2. 로그인
cloudflared tunnel login

# 3. 터널 생성
cloudflared tunnel create youtube-shorts

# 4. 터널 실행
cloudflared tunnel --config config.yml run youtube-shorts
```

**장점**: 완전 무료, 빠름, 안정적
**단점**: 계정 생성 필요, 설정 복잡

## 2️⃣ ngrok (무료 플랜 제한적)
```bash
# 1. 다운로드: https://ngrok.com/download
# 2. 인증
ngrok authtoken [YOUR_TOKEN]

# 3. 터널 시작
ngrok http 8501
```

**장점**: 설정 간단, 고정 도메인 가능
**단점**: 무료는 임시 주소, 유료 필요

## 3️⃣ 현재 방법 (임시 터널)
```bash
cloudflared tunnel --url http://localhost:8501
```

**장점**: 설정 없음, 즉시 사용
**단점**: 재시작 시 주소 변경

## 🎯 추천 방법

### 개발/테스트용
- 현재 방법 (임시 터널) 사용

### 실제 사용/공유용
1. **Cloudflare 계정 생성** (무료)
2. **고정 터널 설정**
3. **고정 주소 획득**

## 📱 모바일 접속 우선순위
1. **로컬 네트워크**: http://192.168.25.14:8501 (가장 빠름)
2. **고정 터널**: https://your-domain.trycloudflare.com
3. **임시 터널**: https://random-name.trycloudflare.com (매번 변경)