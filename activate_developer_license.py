#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""개발자용 영구 라이선스 활성화"""

from app.services.license import LicenseManager
from datetime import datetime, timedelta

def activate_developer_license():
    """개발자용 영구 라이선스 활성화 (9999년 만료)"""
    manager = LicenseManager()
    
    # 하드웨어 ID 가져오기
    hardware_id = manager.get_hardware_id()
    
    print("=" * 60)
    print("개발자용 영구 라이선스 활성화")
    print("=" * 60)
    print(f"\n하드웨어 ID: {hardware_id[:16]}...")
    
    # 영구 라이선스 데이터 생성 (9999년 만료)
    import json
    license_data = {
        "license_key": "DEV-PERM-ANENT-LICN",
        "hardware_id": hardware_id,
        "activated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "expiry_date": "9999-12-31"  # 영구 라이선스
    }
    
    # 암호화하여 저장
    encrypted_data = manager._encrypt_data(license_data)
    with open(manager.license_file, 'wb') as f:
        f.write(encrypted_data)
    
    print("\n✅ 개발자용 영구 라이선스가 활성화되었습니다!")
    print(f"📋 라이선스 키: {license_data['license_key']}")
    print(f"📅 만료일: {license_data['expiry_date']} (영구)")
    print("\n" + "=" * 60)
    print("이제 프로그램을 자유롭게 사용할 수 있습니다.")
    print("=" * 60)

if __name__ == "__main__":
    activate_developer_license()
