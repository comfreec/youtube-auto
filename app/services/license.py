# -*- coding: utf-8 -*-
"""라이선스 인증 시스템"""

import os
import json
import hmac
import hashlib
import base64
import platform
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
from loguru import logger

# 판매자 전용 비밀 서명 키 (절대 변경/공개 금지)
_SECRET_KEY = b"AI-SHORTS-GENERATOR-SECRET-2024-JADONG-PROD"


def _sign_license(expiry_date: str) -> str:
    """만료일로 HMAC 서명 생성"""
    sig = hmac.new(_SECRET_KEY, expiry_date.encode(), hashlib.sha256).hexdigest()
    return sig


def generate_license_key(days: int, customer_name: str = "") -> str:
    """라이선스 키 생성 (판매자용)
    
    키 구조: 만료일(YYYYMMDD) + HMAC서명앞8자 = 16자 → XXXX-XXXX-XXXX-XXXX
    오프라인 검증 가능, 위조 불가
    """
    expiry_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    sig = _sign_license(expiry_date)

    date_compact = expiry_date.replace("-", "")  # 20251231
    key_raw = (date_compact + sig[:8]).upper()   # 16자
    license_key = f"{key_raw[0:4]}-{key_raw[4:8]}-{key_raw[8:12]}-{key_raw[12:16]}"

    logger.info(f"라이선스 키 생성: {license_key} (만료일: {expiry_date}, 고객: {customer_name})")
    return license_key


def decode_license_key(license_key: str):
    """라이선스 키에서 만료일 추출 및 서명 검증
    
    Returns:
        (유효여부, 만료일 or 오류메시지)
    """
    # 개발자 라이선스
    if license_key.upper() == "DEV-PERM-ANENT-LICN":
        return True, "2099-12-31"

    key_raw = license_key.replace("-", "").upper()
    if len(key_raw) != 16:
        return False, "키 형식 오류"

    date_part = key_raw[:8]   # YYYYMMDD
    sig_part = key_raw[8:16]  # 서명 앞 8자

    # 날짜 파싱
    try:
        expiry_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
        datetime.strptime(expiry_date, "%Y-%m-%d")
    except ValueError:
        return False, "날짜 형식 오류"

    # 서명 검증: 가능한 days 범위(1~3650)로 브루트포스 방지 → 날짜만으로 검증
    # 날짜 기반 서명: days 없이 날짜만으로 서명
    expected_sig = hmac.new(_SECRET_KEY, expiry_date.encode(), hashlib.sha256).hexdigest()[:8].upper()
    if sig_part != expected_sig:
        return False, "유효하지 않은 라이선스 키입니다"

    return True, expiry_date


class LicenseManager:
    """라이선스 관리 클래스"""

    def __init__(self):
        self.license_file = Path("license.dat")
        self.cipher_key = b'6oQwhnTvOZcbsVPf2jFTkaq6LI1ndz_mwZMmJcsZ-aY='
        self.cipher = Fernet(self.cipher_key)

    def get_hardware_id(self) -> str:
        """하드웨어 ID 생성 (컴퓨터 고유 식별자)"""
        try:
            system = platform.system()
            if system == "Windows":
                try:
                    cpu_info = subprocess.check_output("wmic cpu get processorid", shell=True).decode()
                    cpu_id = cpu_info.split('\n')[1].strip()
                except:
                    cpu_id = "unknown"
                try:
                    mb_info = subprocess.check_output("wmic baseboard get serialnumber", shell=True).decode()
                    mb_serial = mb_info.split('\n')[1].strip()
                except:
                    mb_serial = "unknown"
                hardware_string = f"{cpu_id}-{mb_serial}-{platform.node()}"
            elif system == "Darwin":
                try:
                    hw_uuid = subprocess.check_output("system_profiler SPHardwareDataType | grep 'Hardware UUID'", shell=True).decode()
                    hardware_string = hw_uuid.split(':')[1].strip()
                except:
                    hardware_string = platform.node()
            else:
                try:
                    with open('/etc/machine-id', 'r') as f:
                        hardware_string = f.read().strip()
                except:
                    hardware_string = platform.node()

            return hashlib.sha256(hardware_string.encode()).hexdigest()
        except Exception as e:
            logger.error(f"하드웨어 ID 생성 실패: {e}")
            return hashlib.sha256(platform.node().encode()).hexdigest()

    def activate_license(self, license_key: str) -> tuple[bool, str]:
        """라이선스 활성화"""
        try:
            license_key = license_key.strip().upper()

            # 키 자체 검증 (서명 확인 + 만료일 추출)
            valid, result = decode_license_key(license_key)
            if not valid:
                return False, result

            expiry_date = result

            # 이미 만료된 키인지 확인
            if datetime.strptime(expiry_date, "%Y-%m-%d") < datetime.now():
                return False, f"이미 만료된 라이선스 키입니다. (만료일: {expiry_date})"

            # 하드웨어 ID
            hardware_id = self.get_hardware_id()

            # 서버에 하드웨어 ID 등록/검증 (개발자 키 제외)
            if license_key != "DEV-PERM-ANENT-LICN":
                server_result = self._verify_with_server(license_key, hardware_id)
                if not server_result[0]:
                    return False, server_result[1]

            # 로컬 license.dat 저장
            license_data = {
                "license_key": license_key,
                "hardware_id": hardware_id,
                "activated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "expiry_date": expiry_date,
            }

            encrypted_data = self._encrypt_data(license_data)
            with open(self.license_file, 'wb') as f:
                f.write(encrypted_data)

            days_left = (datetime.strptime(expiry_date, "%Y-%m-%d") - datetime.now()).days
            logger.info(f"라이선스 활성화 성공: {license_key} (만료일: {expiry_date}, {days_left}일 남음)")
            return True, f"라이선스가 성공적으로 활성화되었습니다! (만료일: {expiry_date}, {days_left}일 남음)"

        except Exception as e:
            logger.error(f"라이선스 활성화 실패: {e}")
            return False, f"활성화 실패: {str(e)}"

    def _verify_with_server(self, license_key: str, hardware_id: str) -> tuple[bool, str]:
        """서버에 하드웨어 ID 등록/검증"""
        import urllib.request
        import json as _json

        # 서버 주소 설정 파일에서 읽기
        server_url = self._get_license_server_url()
        if not server_url:
            logger.warning("라이선스 서버 주소 미설정 - 로컬 검증만 수행")
            return True, "ok"

        try:
            payload = _json.dumps({
                "license_key": license_key,
                "hardware_id": hardware_id
            }).encode()
            req = urllib.request.Request(
                f"{server_url}/api/license/activate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            res = urllib.request.urlopen(req, timeout=10)
            data = _json.loads(res.read().decode())
            return True, data.get("message", "ok")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                msg = _json.loads(body).get("detail", "서버 오류")
            except:
                msg = body
            return False, msg
        except Exception as e:
            logger.warning(f"서버 연결 실패: {e} - 로컬 검증만 수행")
            return True, "ok"  # 서버 연결 실패 시 로컬 검증으로 폴백

    def _get_license_server_url(self) -> str:
        """라이선스 서버 URL 읽기 (config.toml의 license_server_url)"""
        try:
            import toml
            cfg = toml.load("config.toml")
            return cfg.get("app", {}).get("license_server_url", "").rstrip("/")
        except:
            return ""

    def verify_license(self) -> tuple[bool, str]:
        """라이선스 검증"""
        try:
            if not self.license_file.exists():
                return False, "라이선스가 활성화되지 않았습니다."

            with open(self.license_file, 'rb') as f:
                encrypted_data = f.read()

            license_data = self._decrypt_data(encrypted_data)

            # 하드웨어 ID 확인
            current_hardware_id = self.get_hardware_id()
            if license_data.get("hardware_id") != current_hardware_id:
                return False, "다른 컴퓨터에서 활성화된 라이선스입니다."

            # 키 서명 재검증 (license.dat 위변조 방지)
            license_key = license_data.get("license_key", "")
            valid, result = decode_license_key(license_key)
            if not valid:
                return False, "라이선스 파일이 손상되었습니다."

            # 만료일 확인
            expiry_date = datetime.strptime(license_data.get("expiry_date"), "%Y-%m-%d")
            if datetime.now() > expiry_date:
                return False, f"라이선스가 만료되었습니다. (만료일: {license_data.get('expiry_date')})"

            days_left = (expiry_date - datetime.now()).days
            return True, f"라이선스 유효 (남은 기간: {days_left}일)"

        except Exception as e:
            logger.error(f"라이선스 검증 실패: {e}")
            return False, "라이선스 파일이 손상되었습니다."

    def get_license_info(self) -> dict:
        """라이선스 정보 조회"""
        try:
            if not self.license_file.exists():
                return {}

            with open(self.license_file, 'rb') as f:
                encrypted_data = f.read()

            license_data = self._decrypt_data(encrypted_data)
            expiry_date = datetime.strptime(license_data.get("expiry_date"), "%Y-%m-%d")
            days_left = (expiry_date - datetime.now()).days

            return {
                "license_key": license_data.get("license_key", ""),
                "activated_at": license_data.get("activated_at", ""),
                "expiry_date": license_data.get("expiry_date", ""),
                "days_left": days_left,
                "hardware_id": license_data.get("hardware_id", "")[:16] + "..."
            }
        except Exception as e:
            logger.error(f"라이선스 정보 조회 실패: {e}")
            return {}

    def _encrypt_data(self, data: dict) -> bytes:
        json_data = json.dumps(data).encode()
        return self.cipher.encrypt(json_data)

    def _decrypt_data(self, encrypted_data: bytes) -> dict:
        json_data = self.cipher.decrypt(encrypted_data)
        return json.loads(json_data.decode())


# 전역 인스턴스
license_manager = LicenseManager()
