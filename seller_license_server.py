# -*- coding: utf-8 -*-
"""Seller-only license server. Never include this file or its private key in customer builds."""

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parent
PRIVATE_KEY_FILE = ROOT_DIR / "license_server_private.pem"
PUBLIC_KEY_FILE = ROOT_DIR / "resource" / "license_public_key.pem"
DATABASE_FILE = ROOT_DIR / "license_server_database.json"
DB_LOCK = threading.Lock()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def initialize_keys() -> None:
    if PRIVATE_KEY_FILE.exists():
        raise RuntimeError("개인키가 이미 존재합니다. 기존 키를 삭제하거나 덮어쓰지 마세요.")
    private_key = Ed25519PrivateKey.generate()
    PRIVATE_KEY_FILE.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    PUBLIC_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_KEY_FILE.write_bytes(
        private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print(f"개인키 생성: {PRIVATE_KEY_FILE}")
    print(f"고객용 공개키 생성: {PUBLIC_KEY_FILE}")


def import_legacy_database(source: Path) -> None:
    if not source.exists():
        raise RuntimeError(f"기존 라이선스 기록 파일이 없습니다: {source}")
    legacy_records = json.loads(source.read_text(encoding="utf-8"))
    with DB_LOCK:
        records = load_database()
        known_hashes = {item["key_hash"] for item in records}
        imported = 0
        for legacy in legacy_records:
            license_key = legacy.get("license_key", "").strip().upper()
            expiry_date = legacy.get("expiry_date", "")
            if not license_key or not expiry_date:
                continue
            key_hash = hashlib.sha256(license_key.encode()).hexdigest()
            if key_hash in known_hashes:
                continue
            expires_at = datetime.fromisoformat(expiry_date).replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            ).isoformat()
            records.append({
                "id": secrets.token_hex(12),
                "key_hash": key_hash,
                "customer_name": legacy.get("customer_name", "기존 고객"),
                "memo": f"기존 시스템에서 이전: {legacy.get('memo', '')}",
                "created_at": legacy.get("created_at", utc_now().isoformat()),
                "expires_at": expires_at,
                "hardware_id": legacy.get("hardware_id", ""),
                "activated_at": legacy.get("activated_at", ""),
                "revoked": False,
            })
            known_hashes.add(key_hash)
            imported += 1
        save_database(records)
    print(f"기존 라이선스 {imported}개를 가져왔습니다.")


def load_database() -> list[dict]:
    if not DATABASE_FILE.exists():
        return []
    return json.loads(DATABASE_FILE.read_text(encoding="utf-8"))


def save_database(records: list[dict]) -> None:
    temporary = DATABASE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(DATABASE_FILE)


def get_private_key() -> Ed25519PrivateKey:
    if not PRIVATE_KEY_FILE.exists():
        raise RuntimeError("판매자 개인키가 없습니다. --init-keys를 한 번 실행해주세요.")
    key = serialization.load_pem_private_key(PRIVATE_KEY_FILE.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise RuntimeError("개인키 형식이 올바르지 않습니다.")
    return key


def issue_certificate(record: dict, hardware_id: str) -> dict:
    payload = {
        "version": 1,
        "license_id": record["id"],
        "hardware_id": hardware_id,
        "status": "active",
        "expires_at": record["expires_at"],
        "issued_at": utc_now().isoformat(),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = get_private_key().sign(payload_bytes)
    return {
        "payload": base64.urlsafe_b64encode(payload_bytes).decode("ascii"),
        "signature": base64.urlsafe_b64encode(signature).decode("ascii"),
    }


def admin_password() -> str:
    value = os.environ.get("LICENSE_ADMIN_PASSWORD", "")
    if len(value) < 10:
        raise RuntimeError("LICENSE_ADMIN_PASSWORD를 10자 이상으로 설정해야 합니다.")
    return value


def require_admin(password: str | None) -> None:
    if not password or not hmac.compare_digest(password, admin_password()):
        raise HTTPException(status_code=403, detail="관리자 인증 실패")


def find_record(records: list[dict], license_key: str) -> dict:
    key_hash = hashlib.sha256(license_key.strip().upper().encode()).hexdigest()
    record = next((item for item in records if item.get("key_hash") == key_hash), None)
    if not record:
        raise HTTPException(status_code=404, detail="등록되지 않은 라이선스 키입니다.")
    if record.get("revoked"):
        raise HTTPException(status_code=403, detail="사용이 중지된 라이선스입니다.")
    if utc_now() > datetime.fromisoformat(record["expires_at"]):
        raise HTTPException(status_code=403, detail="만료된 라이선스입니다.")
    return record


class CreateLicenseRequest(BaseModel):
    customer_name: str = Field(min_length=1, max_length=100)
    days: int = Field(default=365, ge=1, le=3650)
    memo: str = Field(default="", max_length=500)


class ActivateRequest(BaseModel):
    license_key: str = Field(min_length=10, max_length=100)
    hardware_id: str = Field(min_length=32, max_length=128)


public_app = FastAPI(title="AI Shorts Public License API", docs_url=None, redoc_url=None)
admin_app = FastAPI(title="AI Shorts Local License Admin", docs_url=None, redoc_url=None)
# Backward-compatible name for imports and local tests.
app = public_app


@public_app.get("/health")
def health():
    return {"ok": True}


@admin_app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return """<!doctype html><html lang='ko'><meta charset='utf-8'><title>라이선스 관리</title>
<style>body{font-family:sans-serif;max-width:760px;margin:40px auto;padding:20px;background:#111827;color:#eee}input,button{padding:10px;margin:5px;box-sizing:border-box}input{width:95%}button{background:#7c3aed;color:white;border:0;border-radius:6px}.item{background:#1f2937;padding:15px;margin:10px 0;border-radius:8px}.danger{background:#dc2626}.warn{background:#d97706}pre{white-space:pre-wrap;background:#1f2937;padding:15px}</style>
<h2>판매자 전용 라이선스 관리</h2><input id='pw' type='password' placeholder='관리자 비밀번호'><input id='name' placeholder='고객명'><input id='days' type='number' value='365'><input id='memo' placeholder='메모'><button onclick='createKey()'>라이선스 생성</button><button onclick='listKeys()'>목록 새로고침</button><pre id='out'></pre><div id='list'></div>
<script>
async function call(url,opt={}){opt.headers={...(opt.headers||{}),'X-Admin-Password':document.getElementById('pw').value,'Content-Type':'application/json'};let r=await fetch(url,opt);let t=await r.text();if(!r.ok)throw Error(t);return JSON.parse(t)}
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function createKey(){try{let d=await call('/admin/api/licenses',{method:'POST',body:JSON.stringify({customer_name:name.value,days:Number(days.value),memo:memo.value})});out.textContent='새 라이선스 키 (지금만 표시됩니다)\n'+d.license_key+'\n만료: '+d.expires_at;await listKeys()}catch(e){out.textContent=e}}
async function listKeys(){try{let rows=await call('/admin/api/licenses');list.innerHTML=rows.slice().reverse().map(x=>`<div class="item"><b>${esc(x.customer_name)}</b> · ${x.revoked?'중지됨':'사용 가능'}<br>만료: ${esc(x.expires_at.slice(0,10))} · ${x.hardware_id?'PC 등록됨':'미등록'}<br>${esc(x.memo)}<br><button class="warn" onclick="resetHw('${x.id}')">PC 초기화</button><button class="danger" onclick="revoke('${x.id}')">사용 중지</button></div>`).join('')}catch(e){out.textContent=e}}
async function resetHw(id){if(confirm('이 라이선스의 PC 등록을 초기화할까요?')){await call('/admin/api/licenses/'+id+'/reset-hardware',{method:'POST'});listKeys()}}
async function revoke(id){if(confirm('이 라이선스를 사용 중지할까요?')){await call('/admin/api/licenses/'+id+'/revoke',{method:'POST'});listKeys()}}
</script></html>"""


@admin_app.post("/admin/api/licenses")
def create_license(data: CreateLicenseRequest, x_admin_password: str | None = Header(default=None)):
    require_admin(x_admin_password)
    license_key = "ASG-" + "-".join(secrets.token_hex(3).upper() for _ in range(4))
    expires_at = (utc_now() + timedelta(days=data.days)).replace(hour=23, minute=59, second=59).isoformat()
    record = {
        "id": secrets.token_hex(12),
        "key_hash": hashlib.sha256(license_key.encode()).hexdigest(),
        "customer_name": data.customer_name,
        "memo": data.memo,
        "created_at": utc_now().isoformat(),
        "expires_at": expires_at,
        "hardware_id": "",
        "activated_at": "",
        "revoked": False,
    }
    with DB_LOCK:
        records = load_database()
        records.append(record)
        save_database(records)
    return {"license_key": license_key, "expires_at": expires_at}


@admin_app.get("/admin/api/licenses")
def list_licenses(x_admin_password: str | None = Header(default=None)):
    require_admin(x_admin_password)
    records = load_database()
    return [{k: v for k, v in item.items() if k != "key_hash"} for item in records]


@admin_app.post("/admin/api/licenses/{license_id}/revoke")
def revoke_license(license_id: str, x_admin_password: str | None = Header(default=None)):
    require_admin(x_admin_password)
    with DB_LOCK:
        records = load_database()
        record = next((item for item in records if item["id"] == license_id), None)
        if not record:
            raise HTTPException(status_code=404, detail="라이선스를 찾을 수 없습니다.")
        record["revoked"] = True
        save_database(records)
    return {"ok": True}


@admin_app.post("/admin/api/licenses/{license_id}/reset-hardware")
def reset_hardware(license_id: str, x_admin_password: str | None = Header(default=None)):
    require_admin(x_admin_password)
    with DB_LOCK:
        records = load_database()
        record = next((item for item in records if item["id"] == license_id), None)
        if not record:
            raise HTTPException(status_code=404, detail="라이선스를 찾을 수 없습니다.")
        record["hardware_id"] = ""
        record["activated_at"] = ""
        save_database(records)
    return {"ok": True}


def activate_or_verify(data: ActivateRequest, allow_binding: bool) -> dict:
    with DB_LOCK:
        records = load_database()
        record = find_record(records, data.license_key)
        registered = record.get("hardware_id", "")
        if not registered and allow_binding:
            record["hardware_id"] = data.hardware_id
            record["activated_at"] = utc_now().isoformat()
            save_database(records)
        elif registered != data.hardware_id:
            raise HTTPException(status_code=403, detail="이미 다른 컴퓨터에서 활성화된 라이선스입니다.")
        return {"certificate": issue_certificate(record, data.hardware_id)}


@public_app.post("/api/v1/licenses/activate")
def activate(data: ActivateRequest):
    return activate_or_verify(data, allow_binding=True)


@public_app.post("/api/v1/licenses/verify")
def verify(data: ActivateRequest):
    return activate_or_verify(data, allow_binding=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--init-keys", action="store_true")
    parser.add_argument("--import-legacy", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8510)
    parser.add_argument("--mode", choices=("public", "admin"), default="public")
    args = parser.parse_args()
    if args.init_keys:
        initialize_keys()
    elif args.import_legacy:
        import_legacy_database(args.import_legacy)
    else:
        admin_password()
        get_private_key()
        import uvicorn

        selected_app = public_app if args.mode == "public" else admin_app
        if args.mode == "admin" and args.host not in ("127.0.0.1", "localhost"):
            raise RuntimeError("관리자 서버는 로컬 주소에서만 실행할 수 있습니다.")
        uvicorn.run(selected_app, host=args.host, port=args.port)
