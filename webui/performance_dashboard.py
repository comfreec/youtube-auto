#!/usr/bin/env python3
"""
성능 모니터링 대시보드 - Phase 2
실시간 시스템 성능 모니터링 및 최적화 제어
"""

import os
import sys
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, Any, List, Optional
import time

# Add the root directory to the path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    from app.services.advanced_memory_manager import get_memory_manager
    from app.services.intelligent_cache import get_cache
    from app.services.advanced_error_recovery import get_error_recovery
    from app.services.async_task_manager import get_task_manager
except ImportError as e:
    st.error(f"모듈 import 오류: {e}")
    st.stop()

class PerformanceDashboard:
    """성능 모니터링 대시보드"""
    
    def __init__(self):
        try:
            self.memory_manager = get_memory_manager()
            self.cache_system = get_cache()
            self.error_recovery = get_error_recovery()
            self.task_manager = get_task_manager()
        except Exception as e:
            st.error(f"시스템 초기화 오류: {e}")
            return
        
        # 성능 데이터 히스토리
        if 'performance_history' not in st.session_state:
            st.session_state.performance_history = []
        
        # 자동 새로고침 설정
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = False
        
        # 알림 설정
        if 'alert_thresholds' not in st.session_state:
            st.session_state.alert_thresholds = {
                'memory_usage': 85,
                'cache_hit_rate': 70,
                'error_rate': 5,
                'task_queue_size': 10
            }
    
    def show_dashboard(self):
        """대시보드 메인 화면"""
        st.title("📊 성능 모니터링 대시보드")
        st.markdown("실시간 시스템 성능 모니터링 및 최적화 제어")
        
        # 자동 새로고침 설정
        self._show_refresh_controls()
        
        # 실시간 메트릭 수집
        current_metrics = self._collect_current_metrics()
        
        # 히스토리에 추가
        self._update_performance_history(current_metrics)
        
        # 대시보드 섹션들
        self._show_system_overview(current_metrics)
        self._show_memory_monitoring()
        self._show_cache_monitoring()
        self._show_task_monitoring()
        self._show_error_monitoring()
        self._show_performance_trends()
        self._show_optimization_controls()
        self._show_alerts_and_notifications(current_metrics)
    
    def _show_refresh_controls(self):
        """새로고침 제어"""
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            st.markdown("### 🔄 실시간 모니터링")
        
        with col2:
            auto_refresh = st.checkbox("자동 새로고침", value=st.session_state.auto_refresh)
            st.session_state.auto_refresh = auto_refresh
        
        with col3:
            if st.button("🔄 수동 새로고침"):
                st.rerun()
        
        with col4:
            if st.button("🗑️ 히스토리 초기화"):
                st.session_state.performance_history = []
                st.success("히스토리가 초기화되었습니다!")
        
        # 자동 새로고침 (JavaScript 사용)
        if auto_refresh:
            st.markdown("""
            <script>
            setTimeout(function(){
                window.location.reload();
            }, 5000);
            </script>
            """, unsafe_allow_html=True)
    
    def _collect_current_metrics(self) -> Dict[str, Any]:
        """현재 메트릭 수집"""
        try:
            # 메모리 관리자 메트릭
            memory_info = self.memory_manager.get_memory_info()
            
            # 캐시 시스템 메트릭
            cache_stats = self.cache_system.get_stats()
            
            # 오류 복구 시스템 메트릭
            error_stats = self.error_recovery.get_stats()
            
            # 작업 관리자 메트릭
            task_stats = self.task_manager.get_stats()
            
            return {
                'timestamp': datetime.now(),
                'memory': memory_info,
                'cache': cache_stats,
                'errors': error_stats,
                'tasks': task_stats
            }
        
        except Exception as e:
            st.error(f"메트릭 수집 오류: {e}")
            return {
                'timestamp': datetime.now(),
                'memory': {},
                'cache': {},
                'errors': {},
                'tasks': {}
            }
    
    def _update_performance_history(self, metrics: Dict[str, Any]):
        """성능 히스토리 업데이트"""
        st.session_state.performance_history.append(metrics)
        
        # 최근 100개 데이터만 유지
        if len(st.session_state.performance_history) > 100:
            st.session_state.performance_history = st.session_state.performance_history[-100:]
    
    def _show_system_overview(self, metrics: Dict[str, Any]):
        """시스템 개요"""
        st.markdown("### 🖥️ 시스템 개요")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # 메모리 사용률
        with col1:
            memory_usage = metrics['memory'].get('internal_usage_percent', 0)
            
            st.metric(
                label="🧠 메모리 사용률",
                value=f"{memory_usage:.1f}%",
                delta=f"최대: {metrics['memory'].get('max_memory_mb', 0):.0f}MB"
            )
            
            # 메모리 사용률 프로그레스 바
            if memory_usage > 85:
                st.error(f"⚠️ 높은 메모리 사용률: {memory_usage:.1f}%")
            elif memory_usage > 70:
                st.warning(f"⚠️ 보통 메모리 사용률: {memory_usage:.1f}%")
            else:
                st.success(f"✅ 정상 메모리 사용률: {memory_usage:.1f}%")
        
        # 캐시 적중률
        with col2:
            hit_rate = metrics['cache'].get('hit_rate', 0) * 100
            
            st.metric(
                label="💾 캐시 적중률",
                value=f"{hit_rate:.1f}%",
                delta=f"메모리: {metrics['cache'].get('memory_hit_rate', 0) * 100:.1f}%"
            )
            
            if hit_rate >= 80:
                st.success(f"✅ 우수한 캐시 성능: {hit_rate:.1f}%")
            elif hit_rate >= 60:
                st.warning(f"⚠️ 보통 캐시 성능: {hit_rate:.1f}%")
            else:
                st.error(f"❌ 낮은 캐시 성능: {hit_rate:.1f}%")
        
        # 활성 작업 수
        with col3:
            active_tasks = metrics['tasks'].get('active_tasks', 0)
            pending_tasks = metrics['tasks'].get('pending_tasks', 0)
            
            st.metric(
                label="⚡ 활성 작업",
                value=f"{active_tasks}개",
                delta=f"대기: {pending_tasks}개"
            )
            
            if active_tasks == 0 and pending_tasks == 0:
                st.info("💤 작업 없음")
            elif pending_tasks > 10:
                st.warning(f"⚠️ 많은 대기 작업: {pending_tasks}개")
            else:
                st.success(f"✅ 정상 작업 상태")
        
        # 오류 복구율
        with col4:
            recovery_rate = metrics['errors'].get('recovery_rate', 0) * 100
            total_errors = metrics['errors'].get('total_errors', 0)
            
            st.metric(
                label="🛡️ 오류 복구율",
                value=f"{recovery_rate:.1f}%",
                delta=f"총 오류: {total_errors}개"
            )
            
            if recovery_rate >= 90:
                st.success(f"✅ 우수한 복구율: {recovery_rate:.1f}%")
            elif recovery_rate >= 70:
                st.warning(f"⚠️ 보통 복구율: {recovery_rate:.1f}%")
            else:
                st.error(f"❌ 낮은 복구율: {recovery_rate:.1f}%")
    
    def _show_memory_monitoring(self):
        """메모리 모니터링"""
        st.markdown("### 🧠 메모리 모니터링")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 메모리 사용량 상세
            memory_info = self.memory_manager.get_memory_info()
            
            st.markdown("**📊 메모리 사용량 상세**")
            
            # 메모리 통계 표시
            internal_usage = memory_info.get('internal_usage_mb', 0)
            max_memory = memory_info.get('max_memory_mb', 1)
            active_blocks = memory_info.get('active_blocks', 0)
            
            st.write(f"• 내부 사용량: {internal_usage:.1f}MB / {max_memory:.1f}MB")
            st.write(f"• 활성 블록: {active_blocks}개")
            
            # 시스템 메모리 정보
            system_memory = memory_info.get('system_memory_percent', 0)
            process_memory = memory_info.get('process_memory_mb', 0)
            
            st.write(f"• 시스템 메모리: {system_memory:.1f}%")
            st.write(f"• 프로세스 메모리: {process_memory:.1f}MB")
        
        with col2:
            # 메모리 통계
            st.markdown("**📈 메모리 통계**")
            
            stats = memory_info.get('stats', {})
            
            col2_1, col2_2 = st.columns(2)
            
            with col2_1:
                st.metric("총 할당", f"{stats.get('total_allocations', 0)}회")
                st.metric("총 해제", f"{stats.get('total_deallocations', 0)}회")
            
            with col2_2:
                st.metric("캐시 히트", f"{stats.get('cache_hits', 0)}회")
                st.metric("캐시 미스", f"{stats.get('cache_misses', 0)}회")
            
            # 메모리 정리 작업
            st.markdown("**🧹 메모리 관리**")
            
            col3_1, col3_2 = st.columns(2)
            
            with col3_1:
                if st.button("🧹 스마트 정리", use_container_width=True):
                    try:
                        self.memory_manager._smart_cleanup()
                        st.success("스마트 정리 완료!")
                    except Exception as e:
                        st.error(f"정리 실패: {e}")
            
            with col3_2:
                if st.button("🚨 긴급 정리", use_container_width=True):
                    try:
                        self.memory_manager._emergency_cleanup()
                        st.success("긴급 정리 완료!")
                    except Exception as e:
                        st.error(f"정리 실패: {e}")
    
    def _show_cache_monitoring(self):
        """캐시 모니터링"""
        st.markdown("### 💾 캐시 모니터링")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 캐시 통계
            cache_stats = self.cache_system.get_stats()
            
            st.markdown("**📊 캐시 성능**")
            
            # 캐시 히트/미스 통계
            memory_hits = cache_stats.get('memory_hits', 0)
            disk_hits = cache_stats.get('disk_hits', 0)
            misses = cache_stats.get('misses', 0)
            
            st.write(f"• 메모리 히트: {memory_hits}회")
            st.write(f"• 디스크 히트: {disk_hits}회")
            st.write(f"• 미스: {misses}회")
            
            # 적중률 계산
            total_requests = memory_hits + disk_hits + misses
            if total_requests > 0:
                hit_rate = ((memory_hits + disk_hits) / total_requests) * 100
                st.write(f"• 전체 적중률: {hit_rate:.1f}%")
        
        with col2:
            # 캐시 사용량
            st.markdown("**💽 캐시 사용량**")
            
            memory_usage = cache_stats.get('memory_usage_mb', 0)
            memory_limit = cache_stats.get('memory_limit_mb', 1)
            disk_usage = cache_stats.get('disk_usage_mb', 0)
            disk_limit = cache_stats.get('disk_limit_mb', 1)
            
            # 메모리 캐시 사용률
            memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0
            st.progress(memory_percent / 100)
            st.write(f"메모리 캐시: {memory_usage:.1f}MB / {memory_limit:.1f}MB ({memory_percent:.1f}%)")
            
            # 디스크 캐시 사용률
            disk_percent = (disk_usage / disk_limit) * 100 if disk_limit > 0 else 0
            st.progress(disk_percent / 100)
            st.write(f"디스크 캐시: {disk_usage:.1f}MB / {disk_limit:.1f}MB ({disk_percent:.1f}%)")
            
            # 캐시 관리
            st.markdown("**🔧 캐시 관리**")
            
            col2_1, col2_2 = st.columns(2)
            
            with col2_1:
                if st.button("🧹 메모리 캐시 정리", use_container_width=True):
                    try:
                        from app.services.intelligent_cache import CacheLevel
                        self.cache_system.clear(CacheLevel.MEMORY)
                        st.success("메모리 캐시 정리 완료!")
                    except Exception as e:
                        st.error(f"정리 실패: {e}")
            
            with col2_2:
                if st.button("🗑️ 전체 캐시 정리", use_container_width=True):
                    try:
                        self.cache_system.clear()
                        st.success("전체 캐시 정리 완료!")
                    except Exception as e:
                        st.error(f"정리 실패: {e}")
    
    def _show_task_monitoring(self):
        """작업 모니터링"""
        st.markdown("### ⚡ 작업 모니터링")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 작업 통계
            task_stats = self.task_manager.get_stats()
            
            st.markdown("**📊 작업 통계**")
            
            col1_1, col1_2, col1_3 = st.columns(3)
            
            with col1_1:
                st.metric("활성 작업", f"{task_stats.get('active_tasks', 0)}개")
                st.metric("대기 작업", f"{task_stats.get('pending_tasks', 0)}개")
            
            with col1_2:
                st.metric("완료 작업", f"{task_stats.get('completed_tasks', 0)}개")
                st.metric("실패 작업", f"{task_stats.get('failed_tasks', 0)}개")
            
            with col1_3:
                avg_time = task_stats.get('average_execution_time', 0)
                st.metric("평균 실행시간", f"{avg_time:.1f}초")
                
                utilization = task_stats.get('worker_utilization', 0) * 100
                st.metric("워커 사용률", f"{utilization:.1f}%")
        
        with col2:
            # 실행 중인 작업 목록
            st.markdown("**🔄 실행 중인 작업**")
            
            try:
                running_tasks = self.task_manager.get_running_tasks()
                
                if running_tasks:
                    for i, task in enumerate(running_tasks[:3]):  # 최대 3개만 표시
                        progress = task.progress.percentage if task.progress else 0
                        
                        st.write(f"**{task.name}**")
                        st.progress(progress / 100)
                        st.write(f"진행률: {progress:.1f}%")
                        
                        if task.progress and task.progress.current_operation:
                            st.write(f"현재 작업: {task.progress.current_operation}")
                        
                        if st.button(f"취소", key=f"cancel_{task.id}_{i}"):
                            if self.task_manager.cancel_task(task.id):
                                st.success(f"작업 '{task.name}'이 취소되었습니다!")
                                st.rerun()
                        
                        st.markdown("---")
                else:
                    st.info("현재 실행 중인 작업이 없습니다.")
            
            except Exception as e:
                st.error(f"작업 목록 조회 실패: {e}")
    
    def _show_error_monitoring(self):
        """오류 모니터링"""
        st.markdown("### 🛡️ 오류 모니터링")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 오류 통계
            error_stats = self.error_recovery.get_stats()
            
            st.markdown("**📊 오류 통계**")
            
            col1_1, col1_2 = st.columns(2)
            
            with col1_1:
                st.metric("총 오류", f"{error_stats.get('total_errors', 0)}개")
                st.metric("복구 성공", f"{error_stats.get('recovered_errors', 0)}개")
                st.metric("자동 복구", f"{error_stats.get('auto_recoveries', 0)}개")
            
            with col1_2:
                st.metric("복구 실패", f"{error_stats.get('failed_recoveries', 0)}개")
                st.metric("수동 개입", f"{error_stats.get('manual_interventions', 0)}개")
                st.metric("예방된 오류", f"{error_stats.get('prevented_errors', 0)}개")
            
            # 복구율 계산
            recovery_rate = error_stats.get('recovery_rate', 0) * 100
            
            if recovery_rate >= 90:
                st.success(f"🎉 우수한 복구율: {recovery_rate:.1f}%")
            elif recovery_rate >= 70:
                st.warning(f"⚠️ 보통 복구율: {recovery_rate:.1f}%")
            else:
                st.error(f"🚨 낮은 복구율: {recovery_rate:.1f}%")
        
        with col2:
            # 등록된 패턴 및 액션
            st.markdown("**🔧 등록된 복구 패턴**")
            
            pattern_count = error_stats.get('registered_patterns', 0)
            action_count = error_stats.get('registered_actions', 0)
            
            st.write(f"• 오류 패턴: {pattern_count}개")
            st.write(f"• 복구 액션: {action_count}개")
            
            # 시스템 상태
            system_health = error_stats.get('system_health', {})
            
            st.markdown("**💊 시스템 상태**")
            
            memory_usage = system_health.get('memory_usage', 0) * 100
            cpu_usage = system_health.get('cpu_usage', 0) * 100
            
            st.write(f"• 메모리 사용률: {memory_usage:.1f}%")
            st.write(f"• CPU 사용률: {cpu_usage:.1f}%")
            st.write(f"• 네트워크 상태: {'정상' if system_health.get('network_status', True) else '오류'}")
    
    def _show_performance_trends(self):
        """성능 트렌드"""
        st.markdown("### 📈 성능 트렌드")
        
        if len(st.session_state.performance_history) < 2:
            st.info("트렌드 분석을 위해 더 많은 데이터가 필요합니다.")
            return
        
        try:
            # 히스토리 데이터를 DataFrame으로 변환
            history_data = []
            for h in st.session_state.performance_history[-20:]:  # 최근 20개
                history_data.append({
                    'timestamp': h['timestamp'],
                    'memory_usage': h['memory'].get('internal_usage_percent', 0),
                    'cache_hit_rate': h['cache'].get('hit_rate', 0) * 100,
                    'active_tasks': h['tasks'].get('active_tasks', 0),
                })
            
            df = pd.DataFrame(history_data)
            
            if len(df) > 1:
                # 메모리 사용률 트렌드
                fig = px.line(
                    df,
                    x='timestamp',
                    y='memory_usage',
                    title='메모리 사용률 트렌드',
                    labels={'memory_usage': '사용률 (%)', 'timestamp': '시간'}
                )
                fig.add_hline(y=85, line_dash="dash", line_color="red", 
                             annotation_text="위험 임계값 (85%)")
                st.plotly_chart(fig, use_container_width=True)
        
        except Exception as e:
            st.error(f"트렌드 차트 생성 실패: {e}")
    
    def _show_optimization_controls(self):
        """최적화 제어"""
        st.markdown("### ⚙️ 최적화 제어")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**🧠 메모리 최적화**")
            
            if st.button("🎯 영상 처리 최적화", use_container_width=True):
                try:
                    self.memory_manager.optimize_for_video_processing()
                    st.success("영상 처리 최적화 완료!")
                except Exception as e:
                    st.error(f"최적화 실패: {e}")
            
            if st.button("🔄 메모리 최적화 해제", use_container_width=True):
                try:
                    self.memory_manager.release_video_processing_memory()
                    st.success("메모리 최적화 해제 완료!")
                except Exception as e:
                    st.error(f"해제 실패: {e}")
        
        with col2:
            st.markdown("**💾 캐시 최적화**")
            
            if st.button("🔄 캐시 분산 최적화", use_container_width=True):
                try:
                    self.cache_system._optimize_cache_distribution()
                    st.success("캐시 분산 최적화 완료!")
                except Exception as e:
                    st.error(f"최적화 실패: {e}")
            
            if st.button("🧹 만료된 캐시 정리", use_container_width=True):
                try:
                    self.cache_system._cleanup_expired_entries()
                    st.success("만료된 캐시 정리 완료!")
                except Exception as e:
                    st.error(f"정리 실패: {e}")
        
        with col3:
            st.markdown("**⚡ 작업 최적화**")
            
            if st.button("🧹 완료된 작업 정리", use_container_width=True):
                try:
                    self.task_manager.clear_completed_tasks()
                    st.success("완료된 작업 정리 완료!")
                except Exception as e:
                    st.error(f"정리 실패: {e}")
    
    def _show_alerts_and_notifications(self, metrics: Dict[str, Any]):
        """알림 및 경고"""
        st.markdown("### 🚨 알림 및 경고")
        
        alerts = []
        
        # 메모리 사용률 체크
        memory_usage = metrics['memory'].get('internal_usage_percent', 0)
        if memory_usage > st.session_state.alert_thresholds['memory_usage']:
            alerts.append({
                'level': 'error' if memory_usage > 95 else 'warning',
                'message': f"메모리 사용률이 높습니다: {memory_usage:.1f}%",
                'action': "메모리 정리를 실행하세요."
            })
        
        # 캐시 적중률 체크
        hit_rate = metrics['cache'].get('hit_rate', 0) * 100
        if hit_rate < st.session_state.alert_thresholds['cache_hit_rate']:
            alerts.append({
                'level': 'warning',
                'message': f"캐시 적중률이 낮습니다: {hit_rate:.1f}%",
                'action': "캐시 설정을 확인하세요."
            })
        
        # 작업 대기열 체크
        queue_size = metrics['tasks'].get('queue_size', 0)
        if queue_size > st.session_state.alert_thresholds['task_queue_size']:
            alerts.append({
                'level': 'warning',
                'message': f"작업 대기열이 길어졌습니다: {queue_size}개",
                'action': "워커 수를 늘리거나 작업을 분산하세요."
            })
        
        # 알림 표시
        if alerts:
            for alert in alerts:
                if alert['level'] == 'error':
                    st.error(f"🚨 {alert['message']} - {alert['action']}")
                else:
                    st.warning(f"⚠️ {alert['message']} - {alert['action']}")
        else:
            st.success("✅ 모든 시스템이 정상 작동 중입니다!")


def show_performance_dashboard():
    """성능 대시보드 표시"""
    try:
        dashboard = PerformanceDashboard()
        dashboard.show_dashboard()
    except Exception as e:
        st.error(f"대시보드 초기화 실패: {e}")
        st.info("시스템이 아직 완전히 초기화되지 않았을 수 있습니다.")


def main():
    """메인 함수"""
    st.set_page_config(
        page_title="📊 성능 모니터링 대시보드",
        page_icon="📊",
        layout="wide"
    )
    
    show_performance_dashboard()


if __name__ == "__main__":
    main()