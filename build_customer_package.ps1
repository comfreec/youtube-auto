param([string]$Version = "v1.4_초기설정개선")

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$folderName = "AI쇼츠생성기_배포판_$Version"
$target = Join-Path $PSScriptRoot $folderName
$zipPath = Join-Path $PSScriptRoot "AI쇼츠생성기_$Version.zip"

if (Test-Path -LiteralPath $target) { throw "이미 배포 폴더가 있습니다: $target" }
if (Test-Path -LiteralPath $zipPath) { throw "이미 배포 ZIP이 있습니다: $zipPath" }

New-Item -ItemType Directory -Path $target | Out-Null

$directories = @("app", "webui", "resource", ".streamlit")
foreach ($directory in $directories) {
    if (Test-Path -LiteralPath $directory) {
        Copy-Item -LiteralPath $directory -Destination $target -Recurse
    }
}

$files = @(
    "setup_for_customer.bat",
    "install_customer.ps1",
    "프로그램실행.bat",
    "고객용_빠른시작.md",
    "requirements.txt",
    "config.example.toml",
    "main.py",
    "mobile_server_simple.py",
    "LICENSE"
)
foreach ($file in $files) {
    if (-not (Test-Path -LiteralPath $file)) { throw "필수 파일이 없습니다: $file" }
    Copy-Item -LiteralPath $file -Destination $target
}

# Copy application helpers used by mobile/external access when present.
$optionalFiles = @("외부접속.bat", "외부접속.py", "모바일앱실행.bat", "cloudflared.exe")
foreach ($file in $optionalFiles) {
    if (Test-Path -LiteralPath $file) { Copy-Item -LiteralPath $file -Destination $target }
}

$resolvedRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$resolvedTarget = (Resolve-Path -LiteralPath $target).Path
if (-not $resolvedTarget.StartsWith($resolvedRoot, [StringComparison]::OrdinalIgnoreCase) -or
    (Split-Path -Leaf $resolvedTarget) -ne $folderName) {
    throw "안전하지 않은 배포 경로입니다."
}

Get-ChildItem -LiteralPath $target -Directory -Recurse -Force |
    Where-Object Name -eq "__pycache__" |
    Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $target -File -Recurse -Force |
    Where-Object Extension -in @(".pyc", ".log", ".pid") |
    Remove-Item -Force

$forbiddenNames = @(
    "client_secrets.json", "token.pickle", "token_timer.pickle",
    "license.dat", "license_database.json", "license_server_database.json",
    "license_server_private.pem", "seller_license_server.py", ".env", "secrets.toml"
)
$leaks = @(Get-ChildItem -LiteralPath $target -File -Recurse -Force |
    Where-Object { $forbiddenNames -contains $_.Name })
$rootConfig = Join-Path $target "config.toml"
if (Test-Path -LiteralPath $rootConfig) { $leaks += Get-Item -LiteralPath $rootConfig }
if ($leaks) {
    $names = ($leaks.FullName -join ", ")
    throw "민감한 파일이 발견되어 배포를 중단했습니다: $names"
}

Compress-Archive -LiteralPath $target -DestinationPath $zipPath -CompressionLevel Optimal
Write-Host "고객용 배포본 생성 완료: $zipPath" -ForegroundColor Green
