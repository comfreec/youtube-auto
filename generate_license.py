#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""라이선스 키 생성 도구 (판매자용)"""

import sys
from app.services.license import LicenseManager

def main():
    """라이선스 키 생성"""
    print("=" * 60)
    print("라이선스 키 생성 도구")
    print("=" * 60)
    
    # 고객 정보 입력
    customer_name = input("\n고객 이름 (선택사항): ").strip()
    
    # 유효 기간 입력
    while True:
        try:
            days = input("유효 기간 (일, 기본 365일): ").strip()
            days = int(days) if days else 365
            if days <= 0:
                print("❌ 유효 기간은 1일 이상이어야 합니다.")
                continue
            break
        except ValueError:
            print("❌ 숫자를 입력해주세요.")
    
    # 라이선스 키 생성
    manager = LicenseManager()
    license_key = manager.generate_license_key(days=days, customer_name=customer_name)
    
    print("\n" + "=" * 60)
    print("✅ 라이선스 키 생성 완료!")
    print("=" * 60)
    print(f"\n📋 라이선스 키: {license_key}")
    print(f"👤 고객 이름: {customer_name if customer_name else '(없음)'}")
    print(f"📅 유효 기간: {days}일")
    print(f"📆 만료일: {manager.generate_license_key.__doc__}")
    print("\n" + "=" * 60)
    print("💡 이 라이선스 키를 고객에게 전달하세요.")
    print("=" * 60)

if __name__ == "__main__":
    main()
