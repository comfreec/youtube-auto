# -*- coding: utf-8 -*-
"""Local-only seller UI that proxies authenticated requests to Cloudflare Workers."""

import os
from pathlib import Path

import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse


ROOT_DIR = Path(__file__).resolve().parent
TOKEN_FILE = ROOT_DIR / ".cloudflare_admin_token.txt"
WORKER_URL = os.environ.get(
    "LICENSE_WORKER_URL", "https://ai-shorts-license.comfreec1.workers.dev"
).rstrip("/")

app = FastAPI(title="Local License Admin", docs_url=None, redoc_url=None)


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
def admin_page():
    return """<!doctype html><html lang='ko'><meta charset='utf-8'><title>라이선스 관리</title>
<style>body{font-family:sans-serif;max-width:760px;margin:40px auto;padding:20px;background:#111827;color:#eee}input,button{padding:10px;margin:5px;box-sizing:border-box}input{width:95%}button{background:#7c3aed;color:white;border:0;border-radius:6px}.item{background:#1f2937;padding:15px;margin:10px 0;border-radius:8px}.danger{background:#dc2626}.warn{background:#d97706}pre{white-space:pre-wrap;background:#1f2937;padding:15px}</style>
<h2>판매자 전용 라이선스 관리</h2><p>이 화면은 판매자 PC에서만 열립니다.</p><input id='name' placeholder='고객명'><input id='days' type='number' value='365'><input id='memo' placeholder='메모'><button onclick='createKey()'>라이선스 생성</button><button onclick='listKeys()'>목록 새로고침</button><pre id='out'></pre><div id='list'></div>
<script>
async function call(url,opt={}){opt.headers={'Content-Type':'application/json'};let r=await fetch(url,opt);let t=await r.text();if(!r.ok)throw Error(t);return JSON.parse(t)}
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function createKey(){try{let d=await call('/admin/api/licenses',{method:'POST',body:JSON.stringify({customer_name:name.value,days:Number(days.value),memo:memo.value})});out.textContent='새 라이선스 키 (지금만 표시됩니다)\n'+d.license_key+'\n만료: '+d.expires_at;await listKeys()}catch(e){out.textContent=e}}
async function listKeys(){try{let rows=await call('/admin/api/licenses');list.innerHTML=rows.map(x=>`<div class="item"><b>${esc(x.customer_name)}</b> · ${x.revoked?'중지됨':'사용 가능'}<br>만료: ${esc(x.expires_at.slice(0,10))} · ${x.hardware_id?'PC 등록됨':'미등록'}<br>${esc(x.memo)}<br><button class="warn" onclick="resetHw('${x.id}')">PC 초기화</button><button class="danger" onclick="revoke('${x.id}')">사용 중지</button></div>`).join('')}catch(e){out.textContent=e}}
async function resetHw(id){if(confirm('PC 등록을 초기화할까요?')){await call('/admin/api/licenses/'+id+'/reset-hardware',{method:'POST'});listKeys()}}
async function revoke(id){if(confirm('이 라이선스를 사용 중지할까요?')){await call('/admin/api/licenses/'+id+'/revoke',{method:'POST'});listKeys()}}
listKeys();
</script></html>"""


@app.post("/admin/api/licenses")
def create_license(data: dict):
    return worker_request("POST", "/admin/api/licenses", data)


@app.get("/admin/api/licenses")
def list_licenses():
    return worker_request("GET", "/admin/api/licenses")


@app.post("/admin/api/licenses/{license_id}/{action}")
def update_license(license_id: str, action: str):
    if action not in {"revoke", "reset-hardware"}:
        raise HTTPException(status_code=404, detail="지원하지 않는 작업입니다.")
    return worker_request("POST", f"/admin/api/licenses/{license_id}/{action}")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8511)
