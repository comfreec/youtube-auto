# -*- coding: utf-8 -*-
"""Local-only seller UI that proxies authenticated requests to Cloudflare Workers."""

import os
import secrets
from pathlib import Path

import requests
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials


ROOT_DIR = Path(__file__).resolve().parent
TOKEN_FILE = ROOT_DIR / ".cloudflare_admin_token.txt"
USERNAME_FILE = ROOT_DIR / ".seller_admin_username.txt"
PASSWORD_FILE = ROOT_DIR / ".seller_admin_password.txt"
WORKER_URL = os.environ.get(
    "LICENSE_WORKER_URL", "https://ai-shorts-license.comfreec1.workers.dev"
).rstrip("/")

app = FastAPI(title="Local License Admin", docs_url=None, redoc_url=None)
security = HTTPBasic()


def require_seller(credentials: HTTPBasicCredentials = Depends(security)):
    expected_user = (
        USERNAME_FILE.read_text(encoding="utf-8").strip()
        if USERNAME_FILE.exists()
        else "seller"
    )
    expected = PASSWORD_FILE.read_text(encoding="utf-8").strip() if PASSWORD_FILE.exists() else ""
    valid_user = bool(expected_user) and secrets.compare_digest(
        credentials.username.encode("utf-8"), expected_user.encode("utf-8")
    )
    valid_password = bool(expected) and secrets.compare_digest(
        credentials.password.encode("utf-8"), expected.encode("utf-8")
    )
    if not (valid_user and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="판매자 인증에 실패했습니다.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def worker_request(method: str, path: str, payload: dict | None = None):
    if not TOKEN_FILE.exists():
        raise HTTPException(status_code=500, detail="Cloudflare 관리자 토큰 파일이 없습니다.")
    try:
        response = requests.request(
            method,
            f"{WORKER_URL}{path}",
            headers={"Authorization": f"Bearer {TOKEN_FILE.read_text(encoding='utf-8').strip()}"},
            json=payload,
            timeout=20,
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Cloudflare 연결 실패: {exc}") from exc


@app.get("/admin", response_class=HTMLResponse)
def admin_page(_seller: str = Depends(require_seller)):
    return """<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'><title>라이선스 관리</title>
<style>:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b1020;color:#f8fafc;font-family:system-ui,-apple-system,'Noto Sans KR',sans-serif}.wrap{width:min(100%,720px);margin:auto;padding:20px 16px calc(32px + env(safe-area-inset-bottom))}h1{font-size:24px;margin:8px 0}p{color:#aeb9cc;margin:0 0 18px}.panel,.item{background:#151d31;border:1px solid #28344f;border-radius:16px;padding:16px;box-shadow:0 8px 24px #0003}.field{margin-bottom:13px}.field label{display:block;font-size:13px;font-weight:700;color:#cbd5e1;margin:0 0 7px}input[type=text],input[type=number]{width:100%;min-height:48px;padding:12px 14px;border:1px solid #3b4968;border-radius:11px;background:#0d1528;color:#fff;font-size:16px;outline:none}input:focus{border-color:#8b5cf6;box-shadow:0 0 0 3px #8b5cf633}input:disabled{opacity:.45}.toggle{display:flex;align-items:center;gap:10px;min-height:48px;padding:10px 12px;background:#0d1528;border:1px solid #3b4968;border-radius:11px;font-weight:700}.toggle input{width:22px;height:22px;accent-color:#8b5cf6}.actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px}button{min-height:48px;padding:11px 14px;border:0;border-radius:11px;background:#7c3aed;color:#fff;font-size:15px;font-weight:800;cursor:pointer}button:active{transform:scale(.98)}button.secondary{background:#334155}.item{margin-top:12px;line-height:1.65;overflow-wrap:anywhere}.item b{font-size:17px}.item button{width:calc(50% - 6px);margin:12px 8px 0 0}.danger{background:#dc2626}.warn{background:#d97706}pre{display:none;white-space:pre-wrap;overflow-wrap:anywhere;background:#07101f;border:1px solid #34415d;border-radius:13px;padding:14px;margin:14px 0 0;font-size:14px;line-height:1.55}pre:not(:empty){display:block}#list{margin-top:18px}@media(max-width:420px){.wrap{padding:14px 12px 28px}h1{font-size:21px}.panel,.item{padding:14px;border-radius:14px}.actions{grid-template-columns:1fr}.item button{width:100%;margin:9px 0 0}}</style></head><body><main class='wrap'>
<h1>라이선스 관리</h1><p>판매자 전용 관리자 화면입니다.</p><section class='panel'><div class='field'><label for='name'>고객명</label><input id='name' type='text' placeholder='고객명을 입력하세요'></div><div class='field'><label>유효기간</label><label class='toggle'><input id='permanent' type='checkbox' checked onchange='days.disabled=this.checked'>영구 라이선스</label></div><div class='field'><label for='days'>기간제 사용 일수</label><input id='days' type='number' value='365' min='1' max='3650' disabled placeholder='유효기간(일)'></div><div class='field'><label for='memo'>메모</label><input id='memo' type='text' placeholder='판매 기록이나 고객 정보를 입력하세요'></div><div class='actions'><button onclick='createKey()'>라이선스 생성</button><button class='secondary' onclick='listKeys()'>목록 새로고침</button></div><pre id='out'></pre></section><div id='list'></div>
<script>
async function call(url,opt={}){opt.headers={'Content-Type':'application/json'};let r=await fetch(url,opt);let t=await r.text();if(!r.ok)throw Error(t);return JSON.parse(t)}
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function expiryLabel(v){return String(v||'').startsWith('9999-12-31')?'영구':String(v||'').slice(0,10)}
async function createKey(){try{let d=await call('/admin/api/licenses',{method:'POST',body:JSON.stringify({customer_name:name.value,days:Number(days.value),permanent:permanent.checked,memo:memo.value})});out.textContent='새 라이선스 키 (지금만 표시됩니다)\n'+d.license_key+'\n유효기간: '+expiryLabel(d.expires_at);await listKeys()}catch(e){out.textContent=e}}
async function listKeys(){try{let rows=await call('/admin/api/licenses');list.innerHTML=rows.map(x=>`<div class="item"><b>${esc(x.customer_name)}</b> · ${x.revoked?'중지됨':'사용 가능'}<br>유효기간: ${esc(expiryLabel(x.expires_at))} · ${x.hardware_id?'PC 등록됨':'미등록'}<br>${esc(x.memo)}<br><button class="warn" onclick="resetHw('${x.id}')">PC 초기화</button><button class="danger" onclick="revoke('${x.id}')">사용 중지</button></div>`).join('')}catch(e){out.textContent=e}}
async function resetHw(id){if(confirm('PC 등록을 초기화할까요?')){await call('/admin/api/licenses/'+id+'/reset-hardware',{method:'POST'});listKeys()}}
async function revoke(id){if(confirm('이 라이선스를 사용 중지할까요?')){await call('/admin/api/licenses/'+id+'/revoke',{method:'POST'});listKeys()}}
listKeys();
</script></main></body></html>"""


@app.post("/admin/api/licenses")
def create_license(data: dict, _seller: str = Depends(require_seller)):
    return worker_request("POST", "/admin/api/licenses", data)


@app.get("/admin/api/licenses")
def list_licenses(_seller: str = Depends(require_seller)):
    return worker_request("GET", "/admin/api/licenses")


@app.post("/admin/api/licenses/{license_id}/{action}")
def update_license(license_id: str, action: str, _seller: str = Depends(require_seller)):
    if action not in {"revoke", "reset-hardware"}:
        raise HTTPException(status_code=404, detail="지원하지 않는 작업입니다.")
    return worker_request("POST", f"/admin/api/licenses/{license_id}/{action}")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8511)
