# -*- coding: utf-8 -*-
"""Customer-side license validation.

License creation and private signing keys intentionally live outside this module.
"""

import base64
import hashlib
import json
import platform
import subprocess
import requests
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from loguru import logger


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PUBLIC_KEY_FILE = ROOT_DIR / "resource" / "license_public_key.pem"
ONLINE_CHECK_INTERVAL_HOURS = 24
OFFLINE_GRACE_HOURS = 72


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class LicenseManager:
    """Activates and verifies server-issued, machine-bound licenses."""

    def __init__(self):
        self.license_file = ROOT_DIR / "license.dat"
        self.cipher = Fernet(b"6oQwhnTvOZcbsVPf2jFTkaq6LI1ndz_mwZMmJcsZ-aY=")

    def get_hardware_id(self) -> str:
        try:
            system = platform.system()
            if system == "Windows":
                try:
                    cpu_info = subprocess.check_output(
                        "wmic cpu get processorid", shell=True, stderr=subprocess.DEVNULL
                    ).decode(errors="ignore")
                    cpu_id = cpu_info.splitlines()[1].strip()
                except Exception:
                    cpu_id = "unknown"
                try:
                    board_info = subprocess.check_output(
                        "wmic baseboard get serialnumber", shell=True, stderr=subprocess.DEVNULL
                    ).decode(errors="ignore")
                    board_id = board_info.splitlines()[1].strip()
                except Exception:
                    board_id = "unknown"
                raw = f"{cpu_id}-{board_id}-{platform.node()}"
            elif system == "Darwin":
                raw = platform.node()
            else:
                machine_id = Path("/etc/machine-id")
                raw = machine_id.read_text(encoding="utf-8").strip() if machine_id.exists() else platform.node()
            return hashlib.sha256(raw.encode()).hexdigest()
        except Exception as exc:
            logger.warning(f"하드웨어 ID 생성 실패: {exc}")
            return hashlib.sha256(platform.node().encode()).hexdigest()

    def _server_url(self) -> str:
        try:
            import toml

            cfg = toml.load(ROOT_DIR / "config.toml")
            return cfg.get("app", {}).get("license_server_url", "").rstrip("/")
        except Exception:
            return ""

    def _request(self, path: str, payload: dict) -> dict:
        server_url = self._server_url()
        if not server_url:
            raise RuntimeError("라이선스 서버 주소가 설정되지 않았습니다.")
        try:
            response = requests.post(
                f"{server_url}{path}",
                json=payload,
                headers={"User-Agent": "AI-Shorts-Generator/1.0"},
                timeout=10,
            )
            if response.ok:
                return response.json()
            try:
                message = response.json().get("detail", "라이선스 서버 오류")
            except Exception:
                message = "라이선스 서버 오류"
            raise RuntimeError(message)
        except requests.RequestException as exc:
            raise RuntimeError(f"라이선스 서버 연결 실패: {exc}") from exc

    def _verify_certificate(self, certificate: dict, hardware_id: str) -> dict:
        if not PUBLIC_KEY_FILE.exists():
            raise RuntimeError("라이선스 공개키 파일이 없습니다.")
        payload_b64 = certificate.get("payload", "")
        signature_b64 = certificate.get("signature", "")
        try:
            payload_bytes = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
            signature = base64.urlsafe_b64decode(signature_b64.encode("ascii"))
            public_key = serialization.load_pem_public_key(PUBLIC_KEY_FILE.read_bytes())
            if not isinstance(public_key, Ed25519PublicKey):
                raise ValueError("잘못된 공개키 형식")
            public_key.verify(signature, payload_bytes)
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError("라이선스 인증서가 올바르지 않습니다.") from exc

        if payload.get("hardware_id") != hardware_id:
            raise RuntimeError("다른 컴퓨터에서 활성화된 라이선스입니다.")
        if payload.get("status") != "active":
            raise RuntimeError("사용이 중지된 라이선스입니다.")
        if _utc_now() > _parse_time(payload["expires_at"]):
            raise RuntimeError(f"라이선스가 만료되었습니다. (만료일: {payload['expires_at'][:10]})")
        return payload

    def activate_license(self, license_key: str) -> tuple[bool, str]:
        license_key = license_key.strip().upper()
        if not license_key:
            return False, "라이선스 키를 입력해주세요."
        hardware_id = self.get_hardware_id()
        try:
            response = self._request(
                "/api/v1/licenses/activate",
                {"license_key": license_key, "hardware_id": hardware_id},
            )
            certificate = response["certificate"]
            payload = self._verify_certificate(certificate, hardware_id)
            data = {
                "license_key": license_key,
                "hardware_id": hardware_id,
                "certificate": certificate,
                "last_verified_at": _utc_now().isoformat(),
                "activated_at": _utc_now().isoformat(),
            }
            self.license_file.write_bytes(self._encrypt_data(data))
            if payload["expires_at"].startswith("9999-12-31"):
                return True, "영구 라이선스가 활성화되었습니다."
            return True, f"라이선스가 활성화되었습니다. (만료일: {payload['expires_at'][:10]})"
        except Exception as exc:
            logger.warning(f"라이선스 활성화 실패: {exc}")
            return False, str(exc)

    def verify_license(self) -> tuple[bool, str]:
        if not self.license_file.exists():
            return False, "라이선스가 활성화되지 않았습니다."
        try:
            data = self._decrypt_data(self.license_file.read_bytes())
            hardware_id = self.get_hardware_id()
            # One-time migration for licenses issued by versions before v1.5.
            if "certificate" not in data and data.get("license_key"):
                response = self._request(
                    "/api/v1/licenses/activate",
                    {"license_key": data["license_key"], "hardware_id": hardware_id},
                )
                data = {
                    "license_key": data["license_key"],
                    "hardware_id": hardware_id,
                    "certificate": response["certificate"],
                    "last_verified_at": _utc_now().isoformat(),
                    "activated_at": data.get("activated_at", _utc_now().isoformat()),
                }
                self.license_file.write_bytes(self._encrypt_data(data))
            payload = self._verify_certificate(data["certificate"], hardware_id)
            last_verified = _parse_time(data["last_verified_at"])
            elapsed_hours = (_utc_now() - last_verified).total_seconds() / 3600

            if elapsed_hours >= ONLINE_CHECK_INTERVAL_HOURS:
                try:
                    response = self._request(
                        "/api/v1/licenses/verify",
                        {"license_key": data["license_key"], "hardware_id": hardware_id},
                    )
                    certificate = response["certificate"]
                    payload = self._verify_certificate(certificate, hardware_id)
                    data["certificate"] = certificate
                    data["last_verified_at"] = _utc_now().isoformat()
                    self.license_file.write_bytes(self._encrypt_data(data))
                except Exception as exc:
                    if elapsed_hours > OFFLINE_GRACE_HOURS:
                        return False, f"라이선스 서버 확인이 필요합니다. 인터넷 연결 후 다시 실행해주세요. ({exc})"
                    logger.warning(f"라이선스 서버 일시 연결 실패, 오프라인 유예 적용: {exc}")

            if payload["expires_at"].startswith("9999-12-31"):
                return True, "영구 라이선스 유효"
            days_left = max(0, (_parse_time(payload["expires_at"]) - _utc_now()).days)
            return True, f"라이선스 유효 (남은 기간: {days_left}일)"
        except Exception as exc:
            logger.warning(f"라이선스 검증 실패: {exc}")
            return False, str(exc)

    def get_license_info(self) -> dict:
        try:
            data = self._decrypt_data(self.license_file.read_bytes())
            payload = self._verify_certificate(data["certificate"], self.get_hardware_id())
            expiry = _parse_time(payload["expires_at"])
            return {
                "license_key": data.get("license_key", ""),
                "activated_at": data.get("activated_at", ""),
                "expiry_date": "영구" if payload["expires_at"].startswith("9999-12-31") else payload["expires_at"][:10],
                "days_left": None if payload["expires_at"].startswith("9999-12-31") else max(0, (expiry - _utc_now()).days),
                "hardware_id": data.get("hardware_id", "")[:16] + "...",
            }
        except Exception:
            return {}

    def get_service_credentials(self) -> dict:
        """Return full credentials only for authenticated first-party services."""
        try:
            data = self._decrypt_data(self.license_file.read_bytes())
            self._verify_certificate(data["certificate"], self.get_hardware_id())
            return {
                "license_key": data.get("license_key", ""),
                "hardware_id": self.get_hardware_id(),
            }
        except Exception:
            return {}

    def _encrypt_data(self, data: dict) -> bytes:
        return self.cipher.encrypt(json.dumps(data).encode("utf-8"))

    def _decrypt_data(self, encrypted_data: bytes) -> dict:
        return json.loads(self.cipher.decrypt(encrypted_data).decode("utf-8"))


license_manager = LicenseManager()
