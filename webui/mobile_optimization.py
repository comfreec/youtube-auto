"""
모바일 최적화 관련 함수들
"""
import streamlit as st
import time
import os
from typing import Dict, Any

def add_mobile_styles():
    """모바일 친화적 CSS 스타일 추가"""
    st.markdown("""
    <style>
    /* 모바일 최적화 스타일 */
    @media (max-width: 768px) {
        /* 버튼 크기 증가 */
        .stButton > button {
            padding: 1rem 1.5rem !important;
            font-size: 1.1rem !important;
            min-height: 3rem !important;
        }
        
        /* 입력 필드 크기 증가 */
        .stTextInput input, .stTextArea textarea {
            font-size: 1rem !important;
            padding: 1rem !important;
            min-height: 3rem !important;
        }
        
        /* 진행률 바 크기 증가 */
        .stProgress > div {
            height: 1rem !important;
        }
        
        /* 컨테이너 패딩 조정 */
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        
        /* 탭 크기 증가 */
        .stTabs [data-baseweb="tab"] {
            padding: 1rem 1.5rem !important;
            font-size: 1rem !important;
            min-height: 3rem !important;
        }
        
        /* 알림 메시지 크기 조정 */
        .stAlert {
            font-size: 0.9rem !important;
            padding: 1rem !important;
        }
    }
    
    /* 모바일 전용 클래스 */
    .mobile-warning {
        background: linear-gradient(135deg, rgba(255, 193, 7, 0.1) 0%, rgba(255, 152, 0, 0.1) 100%);
        border: 1px solid rgba(255, 193, 7, 0.3);
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .mobile-progress {
        background: rgba(0, 123, 255, 0.1);
        border: 1px solid rgba(0, 123, 255, 0.3);
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* 연결 상태 표시 */
    .connection-status {
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 1000;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.8rem;
    }
    
    .connection-online {
        background: rgba(40, 167, 69, 0.9) !important;
    }
    
    .connection-offline {
        background: rgba(220, 53, 69, 0.9) !important;
    }
    </style>
    """, unsafe_allow_html=True)

def add_mobile_connection_monitor():
    """모바일 연결 상태 모니터링 - 강화된 버전"""
    st.markdown("""
    <div id="connectionStatus" class="connection-status connection-online">
        🟢 연결됨
    </div>
    
    <script>
    // 연결 상태 모니터링 - 강화된 버전
    let connectionRetryCount = 0;
    let lastSuccessfulConnection = Date.now();
    
    function updateConnectionStatus() {
        const statusDiv = document.getElementById('connectionStatus');
        if (navigator.onLine) {
            statusDiv.className = 'connection-status connection-online';
            statusDiv.innerHTML = '🟢 연결됨';
            connectionRetryCount = 0;
            lastSuccessfulConnection = Date.now();
        } else {
            statusDiv.className = 'connection-status connection-offline';
            statusDiv.innerHTML = '🔴 연결 끊김';
        }
    }
    
    // 연결 상태 이벤트 리스너
    window.addEventListener('online', updateConnectionStatus);
    window.addEventListener('offline', updateConnectionStatus);
    
    // 초기 상태 설정
    updateConnectionStatus();
    
    // 강화된 연결 확인 - 재시도 로직 포함
    function checkConnection() {
        const now = Date.now();
        const timeSinceLastSuccess = now - lastSuccessfulConnection;
        
        // 30초 이상 연결이 안되면 더 자주 확인
        const checkInterval = timeSinceLastSuccess > 30000 ? 5000 : 10000;
        
        fetch(window.location.href, {
            method: 'HEAD',
            cache: 'no-cache',
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        })
        .then(response => {
            if (response.ok) {
                if (!navigator.onLine) {
                    navigator.onLine = true;
                    updateConnectionStatus();
                }
                connectionRetryCount = 0;
                lastSuccessfulConnection = Date.now();
            } else {
                throw new Error('Server response not OK');
            }
        })
        .catch(() => {
            connectionRetryCount++;
            if (navigator.onLine && connectionRetryCount > 3) {
                navigator.onLine = false;
                updateConnectionStatus();
            }
            
            // 연결 실패가 계속되면 페이지 새로고침 제안
            if (connectionRetryCount > 10) {
                const shouldReload = confirm('연결이 불안정합니다. 페이지를 새로고침하시겠습니까?');
                if (shouldReload) {
                    window.location.reload();
                }
                connectionRetryCount = 0; // 리셋
            }
        });
        
        setTimeout(checkConnection, checkInterval);
    }
    
    // 연결 확인 시작
    setTimeout(checkConnection, 5000); // 5초 후 시작
    
    // 네트워크 변경 감지 (모바일에서 WiFi <-> 셀룰러 전환)
    if ('connection' in navigator) {
        navigator.connection.addEventListener('change', () => {
            console.log('네트워크 연결 변경 감지:', navigator.connection.effectiveType);
            setTimeout(updateConnectionStatus, 1000);
        });
    }
    </script>
    """, unsafe_allow_html=True)

def show_mobile_generation_tips():
    """모바일 영상 생성 팁 표시"""
    st.markdown("""
    <div class="mobile-warning">
        <h4 style="color: #ff6b35; margin: 0 0 0.5rem 0;">📱 모바일 사용자 필독!</h4>
        <div style="color: #666; font-size: 0.9rem;">
            <strong>🔋 배터리:</strong> 충전 상태를 확인하세요 (생성 시간: 3-10분)<br>
            <strong>📶 네트워크:</strong> 안정적인 Wi-Fi 연결을 사용하세요<br>
            <strong>🔒 화면:</strong> 화면 자동 잠금을 해제하거나 시간을 늘려주세요<br>
            <strong>🚫 멀티태스킹:</strong> 다른 앱 사용을 최소화해주세요<br>
            <strong>💾 저장공간:</strong> 최소 1GB 이상의 여유 공간이 필요합니다
        </div>
    </div>
    """, unsafe_allow_html=True)

def show_mobile_progress_tracker(progress: float, status: str, elapsed_time: float = 0):
    """모바일 친화적 진행 상태 표시 - 강화된 버전"""
    estimated_total = 300  # 5분 예상
    remaining_time = max(0, estimated_total - elapsed_time)
    
    # 진행률에 따른 동적 메시지
    if progress < 0.1:
        phase_msg = "🚀 영상 생성 준비 중"
    elif progress < 0.3:
        phase_msg = "🤖 AI가 대본을 분석하고 있습니다"
    elif progress < 0.5:
        phase_msg = "🎬 영상 소재를 수집하고 있습니다"
    elif progress < 0.7:
        phase_msg = "🎵 음성과 자막을 생성하고 있습니다"
    elif progress < 0.9:
        phase_msg = "✂️ 영상을 편집하고 있습니다"
    else:
        phase_msg = "🎉 마무리 작업 중입니다"
    
    st.markdown(f"""
    <div class="mobile-progress">
        <h4 style="color: #007bff; margin: 0 0 0.5rem 0;">{phase_msg}</h4>
        <div style="margin-bottom: 1rem;">
            <div style="background: rgba(0,0,0,0.1); border-radius: 10px; height: 25px; overflow: hidden; position: relative;">
                <div style="background: linear-gradient(90deg, #007bff, #0056b3); height: 100%; width: {progress*100}%; transition: width 0.5s ease; border-radius: 10px;"></div>
                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: white; font-weight: bold; font-size: 0.9rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.7);">
                    {progress*100:.1f}%
                </div>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
            <div style="text-align: center; padding: 0.5rem; background: rgba(0,123,255,0.1); border-radius: 8px;">
                <div style="font-size: 0.8rem; color: #666;">경과 시간</div>
                <div style="font-weight: bold; color: #007bff;">{int(elapsed_time//60)}분 {int(elapsed_time%60)}초</div>
            </div>
            <div style="text-align: center; padding: 0.5rem; background: rgba(40,167,69,0.1); border-radius: 8px;">
                <div style="font-size: 0.8rem; color: #666;">예상 남은 시간</div>
                <div style="font-weight: bold; color: #28a745;">{int(remaining_time//60)}분 {int(remaining_time%60)}초</div>
            </div>
        </div>
        <div style="color: #666; font-size: 0.9rem; text-align: center; margin-bottom: 1rem;">
            <strong>현재 상태:</strong> {status}
        </div>
        <div style="padding: 1rem; background: rgba(255,193,7,0.1); border-radius: 8px; font-size: 0.85rem; color: #856404;">
            <div style="margin-bottom: 0.5rem;"><strong>📱 모바일 사용자 안내:</strong></div>
            <div>• 화면을 켜둔 상태로 유지해주세요</div>
            <div>• 다른 앱으로 전환해도 백그라운드에서 계속 진행됩니다</div>
            <div>• 네트워크 연결이 끊어지면 자동으로 재연결을 시도합니다</div>
            <div>• 완료되면 알림으로 알려드립니다</div>
        </div>
    </div>
    
    <script>
    // 진행률 업데이트 시 로컬 스토리지에 저장
    localStorage.setItem('video_generation_progress', JSON.stringify({{
        progress: {progress},
        status: '{status}',
        elapsed_time: {elapsed_time},
        timestamp: Date.now()
    }}));
    
    // 진동 피드백 (지원되는 경우)
    if ('vibrate' in navigator && {progress} > 0.95) {{
        navigator.vibrate([200, 100, 200]); // 완료 시 진동
    }}
    </script>
    """, unsafe_allow_html=True)

def check_mobile_compatibility() -> Dict[str, Any]:
    """모바일 호환성 확인"""
    # 기본적인 호환성 체크 (실제로는 JavaScript로 더 정확한 정보를 얻을 수 있음)
    return {
        "is_mobile": True,  # 실제로는 user agent 확인 필요
        "has_sufficient_storage": True,  # 실제로는 storage API 확인 필요
        "has_stable_connection": True,  # 실제로는 connection API 확인 필요
        "battery_level": "unknown"  # 실제로는 battery API 확인 필요
    }

def add_mobile_error_recovery():
    """모바일 오류 복구 기능 - 강화된 버전"""
    st.markdown("""
    <script>
    // 모바일 오류 복구 - 강화된 버전
    let errorCount = 0;
    let lastErrorTime = 0;
    
    window.addEventListener('error', function(e) {
        console.error('Mobile error detected:', e);
        errorCount++;
        lastErrorTime = Date.now();
        
        // 연속 오류 발생 시 즉시 새로고침 제안
        if (errorCount > 3) {
            if (confirm('연속으로 오류가 발생했습니다. 페이지를 새로고침하시겠습니까?')) {
                window.location.reload();
            }
            errorCount = 0;
        } else {
            // 단일 오류는 5초 후 새로고침 제안
            setTimeout(() => {
                if (Date.now() - lastErrorTime > 4000) { // 4초 이상 지났으면
                    if (confirm('오류가 발생했습니다. 페이지를 새로고침하시겠습니까?')) {
                        window.location.reload();
                    }
                }
            }, 5000);
        }
    });
    
    // 메모리 부족 감지 및 관리
    if ('memory' in performance) {
        setInterval(() => {
            const memInfo = performance.memory;
            const usedPercent = (memInfo.usedJSHeapSize / memInfo.jsHeapSizeLimit) * 100;
            
            if (usedPercent > 85) {
                console.warn('High memory usage detected:', usedPercent + '%');
                
                // 메모리 정리 시도
                if (window.gc) {
                    window.gc();
                }
                
                // 90% 초과 시 경고
                if (usedPercent > 90) {
                    console.error('Critical memory usage:', usedPercent + '%');
                    // 사용자에게 알림 (너무 자주 뜨지 않도록 제한)
                    if (!sessionStorage.getItem('memory_warning_shown')) {
                        alert('메모리 사용량이 높습니다. 다른 앱을 종료하거나 페이지를 새로고침해주세요.');
                        sessionStorage.setItem('memory_warning_shown', 'true');
                    }
                }
            }
        }, 30000); // 30초마다 확인
    }
    
    // 페이지 가시성 API로 백그라운드 감지 - 개선된 버전
    let backgroundStartTime = 0;
    let wasInBackground = false;
    
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            console.log('Page went to background');
            backgroundStartTime = Date.now();
            wasInBackground = true;
            
            // 백그라운드 상태를 로컬 스토리지에 저장
            localStorage.setItem('app_in_background', 'true');
            localStorage.setItem('background_start_time', backgroundStartTime.toString());
            
        } else {
            console.log('Page came to foreground');
            const backgroundDuration = Date.now() - backgroundStartTime;
            
            localStorage.removeItem('app_in_background');
            localStorage.removeItem('background_start_time');
            
            if (wasInBackground) {
                console.log('Was in background for:', backgroundDuration, 'ms');
                
                // 5분 이상 백그라운드에 있었으면 상태 동기화
                if (backgroundDuration > 300000) { // 5분
                    console.log('Long background duration, refreshing...');
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else if (backgroundDuration > 60000) { // 1분 이상
                    // 진행 상태 확인
                    const savedProgress = localStorage.getItem('video_generation_progress');
                    if (savedProgress) {
                        const progressData = JSON.parse(savedProgress);
                        const timeSinceUpdate = Date.now() - progressData.timestamp;
                        
                        // 진행 상태가 5분 이상 업데이트되지 않았으면 새로고침
                        if (timeSinceUpdate > 300000) {
                            console.log('Progress stale, refreshing...');
                            window.location.reload();
                        }
                    }
                }
                
                wasInBackground = false;
            }
        }
    });
    
    // 네트워크 연결 복구 시 자동 재시도
    window.addEventListener('online', function() {
        console.log('Network connection restored');
        
        // 백그라운드에서 연결이 복구되었으면 상태 확인
        if (document.hidden) {
            setTimeout(() => {
                fetch(window.location.href, {method: 'HEAD'})
                    .then(() => {
                        console.log('Connection verified after network restore');
                    })
                    .catch(() => {
                        console.log('Connection still unstable');
                    });
            }, 2000);
        }
    });
    
    // 앱 시작 시 이전 세션 복구 확인
    window.addEventListener('load', function() {
        const wasInBackground = localStorage.getItem('app_in_background');
        const backgroundStartTime = localStorage.getItem('background_start_time');
        
        if (wasInBackground && backgroundStartTime) {
            const backgroundDuration = Date.now() - parseInt(backgroundStartTime);
            console.log('Recovered from background session, duration:', backgroundDuration, 'ms');
            
            // 정리
            localStorage.removeItem('app_in_background');
            localStorage.removeItem('background_start_time');
            
            // 긴 백그라운드 세션이었다면 사용자에게 알림
            if (backgroundDuration > 600000) { // 10분 이상
                console.log('Long background session detected, may need refresh');
            }
        }
    });
    
    // 배터리 상태 모니터링 (지원되는 경우)
    if ('getBattery' in navigator) {
        navigator.getBattery().then(function(battery) {
            function updateBatteryStatus() {
                if (battery.level < 0.15 && !battery.charging) {
                    console.warn('Low battery detected:', (battery.level * 100).toFixed(0) + '%');
                    
                    if (!sessionStorage.getItem('battery_warning_shown')) {
                        alert('배터리가 부족합니다 (' + (battery.level * 100).toFixed(0) + '%). 충전기를 연결하거나 영상 생성을 나중에 시도해주세요.');
                        sessionStorage.setItem('battery_warning_shown', 'true');
                    }
                }
            }
            
            battery.addEventListener('levelchange', updateBatteryStatus);
            battery.addEventListener('chargingchange', updateBatteryStatus);
            
            // 초기 배터리 상태 확인
            updateBatteryStatus();
        }).catch(function(error) {
            console.log('Battery API not supported:', error);
        });
    }
    </script>
    """, unsafe_allow_html=True)