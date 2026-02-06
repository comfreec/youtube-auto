import ast
import time
from abc import ABC, abstractmethod

from app.config import config
from app.models import const


# Base class for state management
class BaseState(ABC):
    @abstractmethod
    def update_task(self, task_id: str, state: int, progress: int = 0, **kwargs):
        pass

    @abstractmethod
    def get_task(self, task_id: str):
        pass

    @abstractmethod
    def get_all_tasks(self, page: int, page_size: int):
        pass


# Memory state management
class MemoryState(BaseState):
    def __init__(self):
        self._tasks = {}

    def get_all_tasks(self, page: int, page_size: int):
        start = (page - 1) * page_size
        end = start + page_size
        tasks = list(self._tasks.values())
        total = len(tasks)
        return tasks[start:end], total

    def update_task(
        self,
        task_id: str,
        state: int = const.TASK_STATE_PROCESSING,
        progress: int = 0,
        **kwargs,
    ):
        progress = int(progress)
        if progress > 100:
            progress = 100

        self._tasks[task_id] = {
            "task_id": task_id,
            "state": state,
            "progress": progress,
            **kwargs,
        }
        
        # 🔄 모바일 세션 진행률 업데이트 (자동) - 안정성 강화
        try:
            # 모바일 최적화가 활성화된 경우에만
            import streamlit as st
            if hasattr(st, 'session_state') and st.session_state.get("generation_in_progress", False):
                current_task_id = st.session_state.get("current_task_id")
                if current_task_id == task_id:
                    # 세션 상태에 진행률 저장 (UI 반영용)
                    st.session_state["current_progress"] = progress
                    st.session_state["current_status"] = kwargs.get("message", f"진행률 {progress}%")
                    st.session_state["last_progress_update"] = time.time()
                    
                    # 모바일 세션 매니저 import
                    try:
                        from webui.mobile_session_manager import mobile_session_manager
                        message = kwargs.get("message", f"진행률 {progress}%")
                        mobile_session_manager.update_generation_progress(task_id, progress, message)
                    except ImportError:
                        pass  # 모바일 최적화가 비활성화된 경우
        except Exception as e:
            # 오류가 발생해도 메인 작업에는 영향 없도록
            pass

    def get_task(self, task_id: str):
        return self._tasks.get(task_id, None)
    
    def get_all_tasks(self):
        """모든 작업 반환 (모바일 세션 복원용)"""
        return self._tasks

    def delete_task(self, task_id: str):
        if task_id in self._tasks:
            del self._tasks[task_id]


# Redis state management
class RedisState(BaseState):
    def __init__(self, host="localhost", port=6379, db=0, password=None):
        import redis

        self._redis = redis.StrictRedis(host=host, port=port, db=db, password=password)

    def get_all_tasks(self, page: int, page_size: int):
        start = (page - 1) * page_size
        end = start + page_size
        tasks = []
        cursor = 0
        total = 0
        while True:
            cursor, keys = self._redis.scan(cursor, count=page_size)
            total += len(keys)
            if total > start:
                for key in keys[max(0, start - total):end - total]:
                    task_data = self._redis.hgetall(key)
                    task = {
                        k.decode("utf-8"): self._convert_to_original_type(v) for k, v in task_data.items()
                    }
                    tasks.append(task)
                    if len(tasks) >= page_size:
                        break
            if cursor == 0 or len(tasks) >= page_size:
                break
        return tasks, total

    def update_task(
        self,
        task_id: str,
        state: int = const.TASK_STATE_PROCESSING,
        progress: int = 0,
        **kwargs,
    ):
        progress = int(progress)
        if progress > 100:
            progress = 100

        fields = {
            "task_id": task_id,
            "state": state,
            "progress": progress,
            **kwargs,
        }

        for field, value in fields.items():
            self._redis.hset(task_id, field, str(value))

    def get_task(self, task_id: str):
        task_data = self._redis.hgetall(task_id)
        if not task_data:
            return None

        task = {
            key.decode("utf-8"): self._convert_to_original_type(value)
            for key, value in task_data.items()
        }
        return task

    def delete_task(self, task_id: str):
        self._redis.delete(task_id)

    @staticmethod
    def _convert_to_original_type(value):
        """
        Convert the value from byte string to its original data type.
        You can extend this method to handle other data types as needed.
        """
        value_str = value.decode("utf-8")

        try:
            # try to convert byte string array to list
            return ast.literal_eval(value_str)
        except (ValueError, SyntaxError):
            pass

        if value_str.isdigit():
            return int(value_str)
        # Add more conversions here if needed
        return value_str


# Global state
_enable_redis = config.app.get("enable_redis", False)
_redis_host = config.app.get("redis_host", "localhost")
_redis_port = config.app.get("redis_port", 6379)
_redis_db = config.app.get("redis_db", 0)
_redis_password = config.app.get("redis_password", None)

state = (
    RedisState(
        host=_redis_host, port=_redis_port, db=_redis_db, password=_redis_password
    )
    if _enable_redis
    else MemoryState()
)
