$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath ".cloudflare_admin_token.txt")) {
    throw "Cloudflare 관리자 토큰 파일이 없습니다. 이 파일은 판매자 PC에만 보관해야 합니다."
}

Write-Host "Cloudflare 라이선스 서버 상태를 확인합니다." -ForegroundColor Cyan
$health = Invoke-RestMethod -Uri "https://ai-shorts-license.comfreec1.workers.dev/health" -TimeoutSec 15
if (-not $health.ok) { throw "Cloudflare 라이선스 서버가 응답하지 않습니다." }

Write-Host "판매자 관리 페이지: http://localhost:8511/admin" -ForegroundColor Green
Start-Process "http://localhost:8511/admin"
python cloudflare_license_admin.py
