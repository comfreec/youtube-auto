#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""라이선스 정보 조회 도구"""

from app.services.license import license_manager

def view_license():
    """라이선스 정보 조회"""
    print("=" * 60)
    print("라이선스 정보 조회")
    print("=" * 60)
    
    # 라이선스 검증
    is_valid, message = license_manager.verify_license()
    
    if is_valid:
        print(f"\n✅ 상태: {message}\n")
        
        # 상세 정보
        info = license_manager.get_license_info()
        if info:
            print("📋 라이선스 상세 정보:")
            print(f"  - 라이선스 키: {info.get('license_key', 'N/A')}")
            print(f"  - 활성화 날짜: {info.get('activated_at', 'N/A')}")
            print(f"  - 만료일: {info.get('expiry_date', 'N/A')}")
            print(f"  - 남은 기간: {info.get('days_left', 0)}일")
            print(f"  - 하드웨어 ID: {info.get('hardware_id', 'N/A')}")
    else:
        print(f"\n❌ 상태: {message}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    view_license()
