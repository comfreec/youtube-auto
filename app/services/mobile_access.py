"""Tailscale-based private mobile access helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


MOBILE_SERVER_PORT = 8000
TAILSCALE_HTTPS_PORT = 8446
PC_SERVER_PORT = 8501
PC_SETTINGS_HTTPS_PORT = 8447


def _tailscale_executable() -> str | None:
    found = shutil.which("tailscale")
    if found:
        return found
    windows_path = Path(r"C:\Program Files\Tailscale\tailscale.exe")
    return str(windows_path) if windows_path.exists() else None


def _run(*arguments: str, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    executable = _tailscale_executable()
    if not executable:
        raise FileNotFoundError("Tailscale이 설치되어 있지 않습니다.")
    startupinfo = None
    if hasattr(subprocess, "STARTUPINFO"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return subprocess.run(
        [executable, *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        startupinfo=startupinfo,
        check=False,
    )


def _friendly_error(output: str) -> str:
    lowered = output.lower()
    if "access is denied" in lowered or "permission denied" in lowered:
        return "권한이 부족합니다. 프로그램을 관리자 권한으로 한 번 실행해주세요."
    if "not logged in" in lowered or "needslogin" in lowered:
        return "Tailscale 로그인이 필요합니다. PC에서 Tailscale을 열고 로그인해주세요."
    return output.strip() or "Tailscale 상태를 확인할 수 없습니다."


def get_mobile_access_status() -> dict:
    executable = _tailscale_executable()
    if not executable:
        return {
            "installed": False,
            "connected": False,
            "enabled": False,
            "message": "Tailscale을 PC에 먼저 설치해주세요.",
        }

    result = _run("status", "--json")
    if result.returncode != 0:
        return {
            "installed": True,
            "connected": False,
            "enabled": False,
            "message": _friendly_error(result.stderr or result.stdout),
        }

    try:
        status = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "installed": True,
            "connected": False,
            "enabled": False,
            "message": "Tailscale 연결 정보를 읽을 수 없습니다.",
        }

    self_info = status.get("Self") or {}
    dns_name = str(self_info.get("DNSName") or "").rstrip(".")
    connected = status.get("BackendState") == "Running" and bool(self_info.get("Online", True))
    mobile_url = f"https://{dns_name}:{TAILSCALE_HTTPS_PORT}" if dns_name else ""
    settings_url = f"https://{dns_name}:{PC_SETTINGS_HTTPS_PORT}/?view=settings" if dns_name else ""
    enabled = False
    settings_enabled = False

    if connected and dns_name:
        serve_result = _run("serve", "status", "--json")
        if serve_result.returncode == 0:
            try:
                serve_status = json.loads(serve_result.stdout or "{}")
                web = serve_status.get("Web") or {}
                host = f"{dns_name}:{TAILSCALE_HTTPS_PORT}"
                handlers = (web.get(host) or {}).get("Handlers") or {}
                proxy = str((handlers.get("/") or {}).get("Proxy") or "")
                enabled = proxy.rstrip("/") in {
                    f"http://127.0.0.1:{MOBILE_SERVER_PORT}",
                    f"http://localhost:{MOBILE_SERVER_PORT}",
                }
                settings_host = f"{dns_name}:{PC_SETTINGS_HTTPS_PORT}"
                settings_handlers = (web.get(settings_host) or {}).get("Handlers") or {}
                settings_proxy = str((settings_handlers.get("/") or {}).get("Proxy") or "")
                settings_enabled = settings_proxy.rstrip("/") in {
                    f"http://127.0.0.1:{PC_SERVER_PORT}",
                    f"http://localhost:{PC_SERVER_PORT}",
                }
            except (json.JSONDecodeError, AttributeError):
                pass

    return {
        "installed": True,
        "connected": connected,
        "enabled": enabled,
        "settings_enabled": settings_enabled,
        "dns_name": dns_name,
        "mobile_url": mobile_url,
        "settings_url": settings_url,
        "message": (
            "모바일 연결 주소가 준비되었습니다."
            if enabled
            else "Tailscale은 연결됐습니다. 아래 버튼으로 모바일 주소를 만들어주세요."
            if connected
            else "PC에서 Tailscale을 열고 로그인해주세요."
        ),
    }


def enable_mobile_access() -> dict:
    status = get_mobile_access_status()
    if not status.get("installed") or not status.get("connected"):
        raise RuntimeError(status.get("message") or "Tailscale 연결이 필요합니다.")
    if not status.get("enabled"):
        result = _run(
            "serve",
            "--bg",
            f"--https={TAILSCALE_HTTPS_PORT}",
            f"http://127.0.0.1:{MOBILE_SERVER_PORT}",
        )
        if result.returncode != 0:
            raise RuntimeError(_friendly_error(result.stderr or result.stdout))
    if not status.get("settings_enabled"):
        result = _run(
            "serve",
            "--bg",
            f"--https={PC_SETTINGS_HTTPS_PORT}",
            f"http://127.0.0.1:{PC_SERVER_PORT}",
        )
        if result.returncode != 0:
            raise RuntimeError(_friendly_error(result.stderr or result.stdout))
    refreshed = get_mobile_access_status()
    if not refreshed.get("enabled") or not refreshed.get("settings_enabled"):
        raise RuntimeError("주소 생성 결과를 확인하지 못했습니다. 잠시 후 다시 시도해주세요.")
    return refreshed
