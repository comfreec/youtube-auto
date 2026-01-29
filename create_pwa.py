"""
PWA (Progressive Web App) 생성기
기존 웹 버전을 모바일 앱으로 변환
"""
import os
import json
import base64
from PIL import Image, ImageDraw

def create_app_icons():
    """앱 아이콘 생성"""
    print("🎨 앱 아이콘 생성 중...")
    
    # 기본 아이콘 생성 (간단한 그라데이션)
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    for size in sizes:
        # 그라데이션 아이콘 생성
        img = Image.new('RGB', (size, size), color='#0f0f23')
        draw = ImageDraw.Draw(img)
        
        # 원형 그라데이션 효과
        center = size // 2
        for i in range(center):
            color_intensity = int(255 * (1 - i / center))
            color = (
                min(255, 102 + color_intensity // 4),  # R
                min(255, 126 + color_intensity // 4),  # G  
                min(255, 234 + color_intensity // 8)   # B
            )
            draw.ellipse([center-i, center-i, center+i, center+i], fill=color)
        
        # 중앙에 "AI" 텍스트 (간단하게)
        if size >= 128:
            # 큰 아이콘에만 텍스트 추가
            try:
                from PIL import ImageFont
                font_size = size // 4
                font = ImageFont.load_default()
                text = "🎬"
                
                # 텍스트 중앙 정렬
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (size - text_width) // 2
                y = (size - text_height) // 2
                
                draw.text((x, y), text, fill='white', font=font)
            except:
                pass
        
        # 아이콘 저장
        icon_path = f"webui/static/icons/icon-{size}x{size}.png"
        os.makedirs(os.path.dirname(icon_path), exist_ok=True)
        img.save(icon_path, 'PNG')
    
    print("✅ 앱 아이콘 생성 완료!")
    return sizes

def create_manifest():
    """PWA 매니페스트 생성"""
    print("📄 PWA 매니페스트 생성 중...")
    
    manifest = {
        "name": "AI 영상 생성기",
        "short_name": "AI영상",
        "description": "AI로 자동 영상을 생성하는 모바일 앱",
        "start_url": "/",
        "display": "standalone",
        "orientation": "portrait-primary",
        "background_color": "#0f0f23",
        "theme_color": "#667eea",
        "categories": ["productivity", "multimedia"],
        "lang": "ko",
        "icons": [
            {
                "src": "/static/icons/icon-72x72.png",
                "sizes": "72x72",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-96x96.png",
                "sizes": "96x96",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-128x128.png",
                "sizes": "128x128",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-144x144.png",
                "sizes": "144x144",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-152x152.png",
                "sizes": "152x152",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-384x384.png",
                "sizes": "384x384",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ],
        "screenshots": [
            {
                "src": "/static/screenshots/mobile-1.png",
                "sizes": "390x844",
                "type": "image/png",
                "form_factor": "narrow"
            }
        ],
        "shortcuts": [
            {
                "name": "새 영상 생성",
                "short_name": "새 영상",
                "description": "새로운 AI 영상을 생성합니다",
                "url": "/?action=new",
                "icons": [
                    {
                        "src": "/static/icons/icon-192x192.png",
                        "sizes": "192x192"
                    }
                ]
            },
            {
                "name": "배치 생성",
                "short_name": "배치",
                "description": "여러 영상을 한번에 생성합니다",
                "url": "/?action=batch",
                "icons": [
                    {
                        "src": "/static/icons/icon-192x192.png",
                        "sizes": "192x192"
                    }
                ]
            }
        ]
    }
    
    # 매니페스트 파일 저장
    manifest_path = "webui/static/manifest.json"
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print("✅ PWA 매니페스트 생성 완료!")

def create_service_worker():
    """서비스 워커 생성"""
    print("⚙️ 서비스 워커 생성 중...")
    
    service_worker_js = '''
// AI 영상 생성기 서비스 워커
const CACHE_NAME = 'ai-video-generator-v1';
const urlsToCache = [
    '/',
    '/static/manifest.json',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png'
];

// 설치 이벤트
self.addEventListener('install', event => {
    console.log('서비스 워커 설치 중...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('캐시 열기 성공');
                return cache.addAll(urlsToCache);
            })
    );
});

// 활성화 이벤트
self.addEventListener('activate', event => {
    console.log('서비스 워커 활성화');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('오래된 캐시 삭제:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// 네트워크 요청 가로채기
self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // 캐시에 있으면 캐시에서 반환
                if (response) {
                    return response;
                }
                
                // 없으면 네트워크에서 가져오기
                return fetch(event.request).then(response => {
                    // 유효한 응답인지 확인
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }
                    
                    // 응답 복사 (스트림은 한 번만 사용 가능)
                    const responseToCache = response.clone();
                    
                    caches.open(CACHE_NAME)
                        .then(cache => {
                            cache.put(event.request, responseToCache);
                        });
                    
                    return response;
                });
            })
    );
});

// 백그라운드 동기화
self.addEventListener('sync', event => {
    if (event.tag === 'video-generation') {
        console.log('백그라운드 영상 생성 동기화');
        event.waitUntil(processVideoQueue());
    }
});

// 푸시 알림
self.addEventListener('push', event => {
    console.log('푸시 알림 수신:', event);
    
    const options = {
        body: event.data ? event.data.text() : '영상 생성이 완료되었습니다!',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-72x72.png',
        vibrate: [200, 100, 200],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'view',
                title: '영상 보기',
                icon: '/static/icons/icon-192x192.png'
            },
            {
                action: 'close',
                title: '닫기'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('AI 영상 생성기', options)
    );
});

// 알림 클릭 처리
self.addEventListener('notificationclick', event => {
    console.log('알림 클릭:', event);
    event.notification.close();
    
    if (event.action === 'view') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// 영상 생성 대기열 처리 (오프라인 지원)
async function processVideoQueue() {
    try {
        // IndexedDB에서 대기 중인 작업 가져오기
        const pendingTasks = await getPendingTasks();
        
        for (const task of pendingTasks) {
            try {
                // API 요청 시도
                const response = await fetch('/api/video/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(task.data)
                });
                
                if (response.ok) {
                    // 성공 시 대기열에서 제거
                    await removePendingTask(task.id);
                    console.log('백그라운드 영상 생성 성공:', task.id);
                }
            } catch (error) {
                console.log('백그라운드 영상 생성 실패:', error);
            }
        }
    } catch (error) {
        console.log('대기열 처리 오류:', error);
    }
}

// IndexedDB 헬퍼 함수들
async function getPendingTasks() {
    // 실제 구현에서는 IndexedDB 사용
    return [];
}

async function removePendingTask(taskId) {
    // 실제 구현에서는 IndexedDB에서 제거
    console.log('작업 제거:', taskId);
}
'''
    
    # 서비스 워커 파일 저장
    sw_path = "webui/static/sw.js"
    with open(sw_path, 'w', encoding='utf-8') as f:
        f.write(service_worker_js)
    
    print("✅ 서비스 워커 생성 완료!")

def create_pwa_html_additions():
    """PWA용 HTML 추가 요소 생성"""
    print("📝 PWA HTML 요소 생성 중...")
    
    pwa_html = '''
<!-- PWA 메타 태그 -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="AI영상">
<meta name="application-name" content="AI영상">
<meta name="theme-color" content="#667eea">
<meta name="msapplication-TileColor" content="#667eea">
<meta name="msapplication-navbutton-color" content="#667eea">

<!-- PWA 매니페스트 -->
<link rel="manifest" href="/static/manifest.json">

<!-- 앱 아이콘들 -->
<link rel="icon" type="image/png" sizes="32x32" href="/static/icons/icon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/static/icons/icon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/static/icons/icon-192x192.png">
<link rel="apple-touch-icon" sizes="152x152" href="/static/icons/icon-152x152.png">
<link rel="apple-touch-icon" sizes="144x144" href="/static/icons/icon-144x144.png">
<link rel="apple-touch-icon" sizes="120x120" href="/static/icons/icon-128x128.png">
<link rel="apple-touch-icon" sizes="114x114" href="/static/icons/icon-128x128.png">
<link rel="apple-touch-icon" sizes="76x76" href="/static/icons/icon-72x72.png">
<link rel="apple-touch-icon" sizes="72x72" href="/static/icons/icon-72x72.png">
<link rel="apple-touch-icon" sizes="60x60" href="/static/icons/icon-72x72.png">
<link rel="apple-touch-icon" sizes="57x57" href="/static/icons/icon-72x72.png">

<!-- PWA 설치 JavaScript -->
<script>
// PWA 설치 프롬프트
let deferredPrompt;
let installButton;

window.addEventListener('beforeinstallprompt', (e) => {
    console.log('PWA 설치 프롬프트 준비됨');
    e.preventDefault();
    deferredPrompt = e;
    showInstallButton();
});

function showInstallButton() {
    // 설치 버튼 표시
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

// 서비스 워커 등록
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then((registration) => {
                console.log('서비스 워커 등록 성공:', registration.scope);
            })
            .catch((error) => {
                console.log('서비스 워커 등록 실패:', error);
            });
    });
}

// 앱 설치 완료 감지
window.addEventListener('appinstalled', (evt) => {
    console.log('PWA 설치 완료!');
    closeInstallBanner();
});

// 온라인/오프라인 상태 감지
window.addEventListener('online', () => {
    console.log('온라인 상태');
    showNetworkStatus('🟢 온라인', '#28a745');
});

window.addEventListener('offline', () => {
    console.log('오프라인 상태');
    showNetworkStatus('🔴 오프라인', '#dc3545');
});

function showNetworkStatus(message, color) {
    const statusDiv = document.createElement('div');
    statusDiv.innerHTML = `
        <div style="
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${color};
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.8rem;
            z-index: 10001;
            animation: fadeInOut 3s ease-in-out;
        ">${message}</div>
    `;
    document.body.appendChild(statusDiv);
    
    setTimeout(() => {
        statusDiv.remove();
    }, 3000);
}

// CSS 애니메이션 추가
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeInOut {
        0% { opacity: 0; transform: translateY(-20px); }
        20% { opacity: 1; transform: translateY(0); }
        80% { opacity: 1; transform: translateY(0); }
        100% { opacity: 0; transform: translateY(-20px); }
    }
`;
document.head.appendChild(style);
</script>
'''
    
    # PWA HTML 요소 파일 저장
    pwa_html_path = "webui/static/pwa_additions.html"
    with open(pwa_html_path, 'w', encoding='utf-8') as f:
        f.write(pwa_html)
    
    print("✅ PWA HTML 요소 생성 완료!")

def main():
    """PWA 생성 메인 함수"""
    print("🚀 PWA (Progressive Web App) 생성 시작!")
    print("=" * 50)
    
    try:
        # 1. 앱 아이콘 생성
        create_app_icons()
        
        # 2. PWA 매니페스트 생성
        create_manifest()
        
        # 3. 서비스 워커 생성
        create_service_worker()
        
        # 4. PWA HTML 요소 생성
        create_pwa_html_additions()
        
        print("\n" + "=" * 50)
        print("🎉 PWA 생성 완료!")
        print("=" * 50)
        
        print("\n📱 사용 방법:")
        print("1. 웹 서버 실행: python 외부접속.py")
        print("2. 모바일에서 접속")
        print("3. '홈 화면에 추가' 버튼 클릭")
        print("4. 앱처럼 사용!")
        
        print("\n✨ PWA 기능:")
        print("- 홈 화면 아이콘")
        print("- 전체화면 실행")
        print("- 오프라인 캐싱")
        print("- 푸시 알림")
        print("- 백그라운드 동기화")
        
        print("\n💡 다음 단계:")
        print("- webui/Main.py에 PWA HTML 요소 추가")
        print("- 정적 파일 서빙 설정")
        print("- 푸시 알림 서버 구성")
        
    except Exception as e:
        print(f"\n❌ PWA 생성 실패: {e}")

if __name__ == "__main__":
    main()