#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""라이선스 키 생성 GUI 프로그램 (판매자용)"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

class LicenseGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("라이선스 키 생성기 (판매자용)")
        self.root.geometry("700x600")
        self.root.resizable(False, False)
        
        # 라이선스 기록 파일
        self.license_db = Path("license_database.json")
        self.licenses = self.load_licenses()
        
        self.create_widgets()
        self.refresh_license_list()
    
    def load_licenses(self):
        """저장된 라이선스 목록 불러오기"""
        if self.license_db.exists():
            try:
                with open(self.license_db, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_licenses(self):
        """라이선스 목록 저장"""
        with open(self.license_db, 'w', encoding='utf-8') as f:
            json.dump(self.licenses, indent=2, ensure_ascii=False, fp=f)
    
    def create_widgets(self):
        """UI 생성"""
        # 제목
        title_frame = tk.Frame(self.root, bg="#667eea", height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame, 
            text="🔑 라이선스 키 생성기",
            font=("맑은 고딕", 18, "bold"),
            bg="#667eea",
            fg="white"
        )
        title_label.pack(pady=15)
        
        # 메인 프레임
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 입력 섹션
        input_frame = tk.LabelFrame(main_frame, text="라이선스 정보 입력", font=("맑은 고딕", 10, "bold"), padx=10, pady=10)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 고객 이름
        tk.Label(input_frame, text="고객 이름:", font=("맑은 고딕", 9)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.customer_name_entry = tk.Entry(input_frame, width=40, font=("맑은 고딕", 9))
        self.customer_name_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
        
        # 유효 기간
        tk.Label(input_frame, text="유효 기간 (일):", font=("맑은 고딕", 9)).grid(row=1, column=0, sticky=tk.W, pady=5)
        days_frame = tk.Frame(input_frame)
        days_frame.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        self.days_var = tk.StringVar(value="365")
        self.days_entry = tk.Entry(days_frame, textvariable=self.days_var, width=10, font=("맑은 고딕", 9))
        self.days_entry.pack(side=tk.LEFT)
        
        tk.Label(days_frame, text="일 (365일 = 1년)", font=("맑은 고딕", 8), fg="gray").pack(side=tk.LEFT, padx=(5, 0))
        
        # 메모
        tk.Label(input_frame, text="메모:", font=("맑은 고딕", 9)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.memo_entry = tk.Entry(input_frame, width=40, font=("맑은 고딕", 9))
        self.memo_entry.grid(row=2, column=1, pady=5, padx=(10, 0))
        
        # 생성 버튼
        generate_btn = tk.Button(
            input_frame,
            text="🔑 라이선스 키 생성",
            command=self.generate_license,
            bg="#667eea",
            fg="white",
            font=("맑은 고딕", 10, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=20,
            pady=10
        )
        generate_btn.grid(row=3, column=0, columnspan=2, pady=(15, 5))
        
        # 생성된 라이선스 표시
        result_frame = tk.LabelFrame(main_frame, text="생성된 라이선스 키", font=("맑은 고딕", 10, "bold"), padx=10, pady=10)
        result_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.result_text = tk.Text(result_frame, height=4, font=("Consolas", 11), wrap=tk.WORD)
        self.result_text.pack(fill=tk.X)
        
        copy_btn = tk.Button(
            result_frame,
            text="📋 복사",
            command=self.copy_license,
            font=("맑은 고딕", 9),
            cursor="hand2"
        )
        copy_btn.pack(pady=(5, 0))
        
        # 라이선스 목록
        list_frame = tk.LabelFrame(main_frame, text="생성된 라이선스 목록", font=("맑은 고딕", 10, "bold"), padx=10, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 트리뷰
        columns = ("고객명", "라이선스 키", "유효기간", "생성일")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column("고객명", width=100)
        self.tree.column("라이선스 키", width=200)
        self.tree.column("유효기간", width=80)
        self.tree.column("생성일", width=120)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 하단 버튼
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        
        refresh_btn = tk.Button(
            bottom_frame,
            text="🔄 새로고침",
            command=self.refresh_license_list,
            font=("맑은 고딕", 9)
        )
        refresh_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        export_btn = tk.Button(
            bottom_frame,
            text="💾 내보내기",
            command=self.export_licenses,
            font=("맑은 고딕", 9)
        )
        export_btn.pack(side=tk.LEFT)
    
    def generate_license(self):
        """라이선스 키 생성"""
        customer_name = self.customer_name_entry.get().strip()
        memo = self.memo_entry.get().strip()
        
        try:
            days = int(self.days_var.get())
            if days <= 0:
                messagebox.showerror("오류", "유효 기간은 1일 이상이어야 합니다.")
                return
        except ValueError:
            messagebox.showerror("오류", "유효 기간은 숫자로 입력해주세요.")
            return
        
        # 라이선스 키 생성
        expiry_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        
        license_data = {
            "customer": customer_name,
            "expiry": expiry_date,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "memo": memo
        }
        
        data_string = json.dumps(license_data, sort_keys=True)
        license_hash = hashlib.sha256(data_string.encode()).hexdigest()
        
        license_key = f"{license_hash[:4]}-{license_hash[4:8]}-{license_hash[8:12]}-{license_hash[12:16]}".upper()
        
        # 결과 표시
        result = f"라이선스 키: {license_key}\n"
        result += f"고객명: {customer_name if customer_name else '(없음)'}\n"
        result += f"유효기간: {days}일\n"
        result += f"만료일: {expiry_date}"
        
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, result)
        
        # 데이터베이스에 저장
        license_record = {
            "license_key": license_key,
            "customer_name": customer_name,
            "days": days,
            "expiry_date": expiry_date,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "memo": memo
        }
        
        self.licenses.append(license_record)
        self.save_licenses()
        self.refresh_license_list()
        
        # 입력 필드 초기화
        self.customer_name_entry.delete(0, tk.END)
        self.memo_entry.delete(0, tk.END)
        
        messagebox.showinfo("성공", "라이선스 키가 생성되었습니다!")
    
    def copy_license(self):
        """라이선스 키 복사"""
        text = self.result_text.get(1.0, tk.END).strip()
        if text:
            self.root.clipboard_clear()
            # 라이선스 키만 추출
            for line in text.split('\n'):
                if line.startswith("라이선스 키:"):
                    license_key = line.split(":")[1].strip()
                    self.root.clipboard_append(license_key)
                    messagebox.showinfo("복사 완료", f"라이선스 키가 클립보드에 복사되었습니다:\n{license_key}")
                    return
    
    def refresh_license_list(self):
        """라이선스 목록 새로고침"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for lic in reversed(self.licenses):  # 최신순
            self.tree.insert("", tk.END, values=(
                lic.get("customer_name", ""),
                lic.get("license_key", ""),
                f"{lic.get('days', 0)}일",
                lic.get("created_at", "")
            ))
    
    def export_licenses(self):
        """라이선스 목록 내보내기"""
        if not self.licenses:
            messagebox.showinfo("알림", "내보낼 라이선스가 없습니다.")
            return
        
        filename = f"licenses_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("라이선스 키 목록\n")
            f.write("=" * 80 + "\n\n")
            
            for i, lic in enumerate(self.licenses, 1):
                f.write(f"[{i}] {lic.get('customer_name', '(이름 없음)')}\n")
                f.write(f"    라이선스 키: {lic.get('license_key', '')}\n")
                f.write(f"    유효 기간: {lic.get('days', 0)}일\n")
                f.write(f"    만료일: {lic.get('expiry_date', '')}\n")
                f.write(f"    생성일: {lic.get('created_at', '')}\n")
                if lic.get('memo'):
                    f.write(f"    메모: {lic.get('memo', '')}\n")
                f.write("\n")
        
        messagebox.showinfo("내보내기 완료", f"라이선스 목록이 저장되었습니다:\n{filename}")


def main():
    root = tk.Tk()
    app = LicenseGeneratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
