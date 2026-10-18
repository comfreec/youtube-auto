"""Customer-facing readiness checks, backups, and friendly error messages."""

from __future__ import annotations

import base64
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from app.config import config


BACKUP_FORMAT = "youtube-auto-customer-backup-v1"
AUTH_FILES = {
    "client_secrets": "client_secrets.json",
    "token": "token.pickle",
}


def _has_value(value: Any) -> bool:
    if isinstance(value, (list, tuple)):
        return any(str(item).strip() for item in value)
    return bool(str(value or "").strip())


def friendly_error(error: Any) -> str:
    raw = str(error or "").strip()
    lowered = raw.lower()
    mappings = [
        (("quota", "resource_exhausted", "429"), "무료 API 사용량이 끝났습니다. 잠시 후 다시 시도하거나 다른 API 키를 등록해주세요."),
        (("api key", "api_key", "unauthorized", "401"), "API 키가 올바르지 않거나 만료되었습니다. PC 설정에서 API 키를 확인해주세요."),
        (("youtube", "oauth", "token"), "YouTube 연결이 만료되었거나 인증이 필요합니다. PC 설정에서 YouTube 계정을 다시 연결해주세요."),
        (("timed out", "timeout"), "외부 서비스 응답이 늦습니다. 인터넷 연결을 확인한 뒤 잠시 후 다시 시도해주세요."),
        (("connection", "network", "name resolution"), "인터넷 또는 외부 서비스에 연결할 수 없습니다. 네트워크 연결을 확인해주세요."),
        (("no space", "disk full"), "저장 공간이 부족합니다. PC의 여유 공간을 확보한 뒤 다시 시도해주세요."),
        (("ffmpeg",), "영상 처리 도구를 실행할 수 없습니다. 프로그램을 다시 설치하거나 판매자에게 문의해주세요."),
    ]
    for needles, message in mappings:
        if any(needle in lowered for needle in needles):
            return message
    if not raw:
        return "알 수 없는 문제가 발생했습니다. 다시 시도하고 계속되면 판매자에게 문의해주세요."
    return raw if len(raw) <= 180 else "영상 생성 중 문제가 발생했습니다. PC 설정의 자동 점검을 실행해주세요."


def run_readiness_checks(root_dir: str | Path, video_source: str | None = None, auto_upload: bool = False) -> dict:
    root = Path(root_dir)
    source = str(video_source or config.app.get("video_source", "stock_auto"))
    if source in {"pexels", "pixabay"}:
        source = "stock_auto"
    checks: list[dict] = []

    def add(key: str, label: str, ok: bool, message: str, blocking: bool = False) -> None:
        checks.append({"key": key, "label": label, "ok": ok, "message": message, "blocking": blocking and not ok})

    gemini_keys = [config.app.get("gemini_api_key")]
    gemini_keys.extend(config.app.get(f"gemini_api_key_{index}") for index in range(2, 11))
    has_gemini = any(_has_value(key) for key in gemini_keys)
    add("gemini", "대본 생성 API", has_gemini, "Gemini API 키가 설정되어 있습니다." if has_gemini else "PC 설정에서 Gemini API 키를 입력해주세요.", True)

    if source == "stock_auto":
        has_stock = _has_value(config.app.get("pexels_api_keys")) or _has_value(config.app.get("pixabay_api_keys"))
        add("stock", "무료 배경 영상", has_stock, "무료 영상 API가 준비되었습니다." if has_stock else "Pexels 또는 Pixabay API 키가 하나 이상 필요합니다.", True)
    elif source == "ai_image":
        worker_url = str(config.app.get("ai_image_worker_url", "")).strip()
        add("image", "AI 이미지 서버", worker_url.startswith("https://"), "AI 이미지 서버 주소가 설정되어 있습니다." if worker_url else "AI 이미지 서버가 없어 실패 시 무료 영상으로 전환됩니다.", False)
    else:
        add("background", "배경 생성", True, "오프라인 애니메이션을 사용합니다.")

    youtube_ready = (root / "client_secrets.json").is_file() and (root / "token.pickle").is_file()
    youtube_message = (
        "YouTube 계정이 연결되어 있습니다."
        if youtube_ready
        else "자동 업로드를 사용하지 않아 계정 연결 없이도 영상 파일을 만들 수 있습니다."
        if not auto_upload
        else "자동 업로드를 사용하려면 PC 설정에서 YouTube 계정을 연결해주세요. 영상 파일 생성은 가능합니다."
    )
    add("youtube", "YouTube 자동 업로드", youtube_ready or not auto_upload, youtube_message, False)

    try:
        free_gb = shutil.disk_usage(root).free / (1024 ** 3)
        enough_space = free_gb >= 2
        add("disk", "저장 공간", enough_space, f"사용 가능한 공간: {free_gb:.1f}GB" if enough_space else f"여유 공간이 {free_gb:.1f}GB뿐입니다. 2GB 이상 확보해주세요.", True)
    except OSError:
        add("disk", "저장 공간", False, "저장 공간을 확인할 수 없습니다.", True)

    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_ok = bool(ffmpeg_path and Path(ffmpeg_path).is_file())
    except Exception:
        ffmpeg_ok = bool(shutil.which("ffmpeg"))
    add("ffmpeg", "영상 처리 도구", ffmpeg_ok, "영상 처리 도구가 준비되었습니다." if ffmpeg_ok else "FFmpeg를 찾을 수 없습니다. 프로그램을 다시 설치해주세요.", True)

    blocking = [item for item in checks if item["blocking"]]
    warnings = [item for item in checks if not item["ok"] and not item["blocking"]]
    return {"ready": not blocking, "checks": checks, "blocking": blocking, "warnings": warnings}


def create_backup(root_dir: str | Path) -> bytes:
    root = Path(root_dir)
    auth: dict[str, str] = {}
    for key, filename in AUTH_FILES.items():
        path = root / filename
        if path.is_file():
            auth[key] = base64.b64encode(path.read_bytes()).decode("ascii")
    payload = {
        "format": BACKUP_FORMAT,
        "created_at": int(time.time()),
        "config": dict(config.app),
        "ui_settings": dict(config.ui),
        "youtube_auth": auth,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def restore_backup(root_dir: str | Path, raw: bytes) -> list[str]:
    if len(raw) > 20 * 1024 * 1024:
        raise ValueError("백업 파일이 너무 큽니다.")
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except Exception as exc:
        raise ValueError("올바른 백업 JSON 파일이 아닙니다.") from exc
    if payload.get("format") != BACKUP_FORMAT or not isinstance(payload.get("config"), dict):
        raise ValueError("이 프로그램에서 만든 새 형식의 백업 파일이 아닙니다.")

    config.app.update(payload["config"])
    if isinstance(payload.get("ui_settings"), dict):
        config.ui.update(payload["ui_settings"])
    config.save_config()

    restored = ["프로그램 설정"]
    auth = payload.get("youtube_auth") or {}
    root = Path(root_dir)
    for key, filename in AUTH_FILES.items():
        encoded = auth.get(key)
        if not encoded:
            continue
        try:
            content = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise ValueError(f"{filename} 백업 내용이 손상되었습니다.") from exc
        if len(content) > 10 * 1024 * 1024:
            raise ValueError(f"{filename} 파일이 너무 큽니다.")
        if filename.endswith(".json"):
            json.loads(content.decode("utf-8"))
        (root / filename).write_bytes(content)
        restored.append(filename)
    return restored
