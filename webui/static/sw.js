
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
