# -*- coding: utf-8 -*-
"""라이선스 인증 시스템"""

import os
import json
import hashlib
import platform
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
from loguru import logger


class LicenseManager:
    """라이선스 관리 클래스"""
    
    def __init__(self):
        self.license_file = Path("license.dat")
        # 고정 암호화 키 (변경하지 마세요!)
        self.cipher_key = b'6oQwhnTvOZcbsVPf2jFTkaq6LI1ndz_mwZMmJcsZ-aY='
        self.cipher = Fernet(self.cipher_key)
        
    def get_hardware_id(self) -> str:
        """하드웨어 ID 생성 (컴퓨터 고유 식별자)"""
        try:
            system = platform.system()
            
            if system == "Windows":
                # Windows: CPU ID + 메인보드 시리얼
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
                
            elif system == "Darwin":  # macOS
                # macOS: 하드웨어 UUID
                try:
                    hw_uuid = subprocess.check_output("system_profiler SPHardwareDataType | grep 'Hardware UUID'", shell=True).decode()
                    hardware_string = hw_uuid.split(':')[1].strip()
                except:
                    hardware_string = platform.node()
                    
            else:  # Linux
                # Linux: 머신 ID
                try:
                    with open('/etc/machine-id', 'r') as f:
                        hardware_string = f.read().strip()
                except:
                    hardware_string = platform.node()
            
            # SHA256 해시로 변환
            hardware_id = hashlib.sha256(hardware_string.encode()).hexdigest()
            return hardware_id
            
        except Exception as e:
            logger.error(f"하드웨어 ID 생성 실패: {e}")
            return hashlib.sha256(platform.node().encode()).hexdigest()
    
    def generate_license_key(self, days: int = 365, customer_name: str = "") -> str:
        """라이선스 키 생성 (판매자용)
        
        Args:
            days: 유효 기간 (일)
            customer_name: 고객 이름 (선택)
        
        Returns:
            라이선스 키
        """
        expiry_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        
        # 라이선스 데이터
        license_data = {
            "customer": customer_name,
            "expiry": expiry_date,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # JSON으로 변환 후 해시
        data_string = json.dumps(license_data, sort_keys=True)
        license_hash = hashlib.sha256(data_string.encode()).hexdigest()
        
        # 라이선스 키 형식: XXXX-XXXX-XXXX-XXXX
        license_key = f"{license_hash[:4]}-{license_hash[4:8]}-{license_hash[8:12]}-{license_hash[12:16]}".upper()
        
        logger.info(f"라이선스 키 생성: {license_key} (만료일: {expiry_date})")
        
        return license_key
    
    def activate_license(self, license_key: str) -> tuple[bool, str]:
        """라이선스 활성화
        
        Args:
            license_key: 라이선스 키
        
        Returns:
            (성공 여부, 메시지)
        """
        try:
            # 라이선스 키 검증 (실제로는 서버나 데이터베이스에서 확인)
            # 여기서는 간단히 형식만 확인
            if not self._validate_license_format(license_key):
                return False, "잘못된 라이선스 키 형식입니다."
            
            # 하드웨어 ID 가져오기
            hardware_id = self.get_hardware_id()
            
            # 라이선스 데이터 생성
            license_data = {
                "license_key": license_key,
                "hardware_id": hardware_id,
                "activated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "expiry_date": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")  # 1년
            }
            
            # 암호화하여 저장
            encrypted_data = self._encrypt_data(license_data)
            with open(self.license_file, 'wb') as f:
                f.write(encrypted_data)
            
            logger.info(f"라이선스 활성화 성공: {license_key}")
            return True, "라이선스가 성공적으로 활성화되었습니다!"
            
        except Exception as e:
            logger.error(f"라이선스 활성화 실패: {e}")
            return False, f"활성화 실패: {str(e)}"
    
    def verify_license(self) -> tuple[bool, str]:
        """라이선스 검증
        
        Returns:
            (유효 여부, 메시지)
        """
        try:
            # 라이선스 파일 존재 확인
            if not self.license_file.exists():
                return False, "라이선스가 활성화되지 않았습니다."
            
            # 라이선스 데이터 읽기
            with open(self.license_file, 'rb') as f:
                encrypted_data = f.read()
            
            license_data = self._decrypt_data(encrypted_data)
            
            # 하드웨어 ID 확인
            current_hardware_id = self.get_hardware_id()
            if license_data.get("hardware_id") != current_hardware_id:
                return False, "다른 컴퓨터에서 활성화된 라이선스입니다."
            
            # 만료일 확인
            expiry_date = datetime.strptime(license_data.get("expiry_date"), "%Y-%m-%d")
            if datetime.now() > expiry_date:
                return False, f"라이선스가 만료되었습니다. (만료일: {license_data.get('expiry_date')})"
            
            # 남은 일수 계산
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
            
            # 만료일까지 남은 일수
            expiry_date = datetime.strptime(license_data.get("expiry_date"), "%Y-%m-%d")
            days_left = (expiry_date - datetime.now()).days
            
            return {
                "license_key": license_data.get("license_key", ""),
                "activated_at": license_data.get("activated_at", ""),
                "expiry_date": license_data.get("expiry_date", ""),
                "days_left": days_left,
                "hardware_id": license_data.get("hardware_id", "")[:16] + "..."  # 일부만 표시
            }
            
        except Exception as e:
            logger.error(f"라이선스 정보 조회 실패: {e}")
            return {}
    
    def _validate_license_format(self, license_key: str) -> bool:
        """라이선스 키 형식 검증"""
        # 개발자 라이선스 허용
        if license_key == "DEV-PERM-ANENT-LICN":
            return True
        
        # XXXX-XXXX-XXXX-XXXX 형식
        parts = license_key.split('-')
        if len(parts) != 4:
            return False
        
        for part in parts:
            if len(part) != 4:
                return False
            # 영문자와 숫자만 허용
            if not all(c.isalnum() for c in part.upper()):
                return False
        
        return True
    
    def _encrypt_data(self, data: dict) -> bytes:
        """데이터 암호화"""
        json_data = json.dumps(data).encode()
        return self.cipher.encrypt(json_data)
    
    def _decrypt_data(self, encrypted_data: bytes) -> dict:
        """데이터 복호화"""
        json_data = self.cipher.decrypt(encrypted_data)
        return json.loads(json_data.decode())


# 전역 라이선스 매니저 인스턴스
license_manager = LicenseManager()
