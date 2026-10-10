$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Write-Step([string]$Message) {
    Write-Host "`n$Message" -ForegroundColor Cyan
}

function Find-CompatiblePython {
    $candidates = @(
        @{ Command = "py"; Args = @("-3.11") },
        @{ Command = "py"; Args = @("-3.12") },
        @{ Command = "python"; Args = @() },
        @{ Command = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"; Args = @() }
    )
    foreach ($candidate in $candidates) {
        try {
            $candidateArgs = $candidate.Args
            $version = & $candidate.Command @candidateArgs -c "import sys; print(int((3,10) <= sys.version_info[:2] < (3,14)))" 2>$null
            if ($LASTEXITCODE -eq 0 -and $version -eq "1") { return $candidate }
        } catch { }
    }
    return $null
}

Write-Step "[1/6] 실행 환경을 확인합니다."
$python = Find-CompatiblePython
if (-not $python) {
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw "Python 3.10~3.13이 없고 자동 설치 기능(winget)도 없습니다. Microsoft Store의 앱 설치 관리자를 먼저 업데이트해주세요."
    }
    Write-Host "Python 3.11을 자동 설치합니다. Windows 확인 창이 나타날 수 있습니다."
    & winget.exe install --id Python.Python.3.11 --exact --scope user --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Python 자동 설치에 실패했습니다." }
    $python = Find-CompatiblePython
    if (-not $python) { throw "설치된 Python을 찾지 못했습니다. Windows를 다시 시작한 뒤 설치 파일을 다시 실행해주세요." }
}

Write-Step "[2/6] 프로그램 전용 실행 환경을 만듭니다."
if (-not (Test-Path -LiteralPath "venv\Scripts\python.exe")) {
    $pythonArgs = $python.Args
    & $python.Command @pythonArgs -m venv venv
    if ($LASTEXITCODE -ne 0) { throw "가상환경 생성에 실패했습니다." }
}
$venvPython = Join-Path $PSScriptRoot "venv\Scripts\python.exe"

Write-Step "[3/6] 필수 구성 요소를 설치합니다."
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip 업데이트에 실패했습니다." }
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "필수 구성 요소 설치에 실패했습니다. 인터넷 연결을 확인해주세요." }

Write-Step "[4/6] 개인 설정 파일을 준비합니다."
if (-not (Test-Path -LiteralPath "config.toml")) {
    Copy-Item -LiteralPath "config.example.toml" -Destination "config.toml"
}

Write-Step "[5/6] 설치 상태를 검사합니다."
& $venvPython -c "import streamlit, moviepy, edge_tts; print('필수 구성 요소 확인 완료')"
if ($LASTEXITCODE -ne 0) { throw "설치 검사에 실패했습니다." }

Write-Step "[6/6] 바탕화면 바로가기를 만듭니다."
try {
    $shell = New-Object -ComObject WScript.Shell
    $shortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "AI 쇼츠 생성기.lnk"
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = Join-Path $PSScriptRoot "프로그램실행.bat"
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.Description = "AI 쇼츠 생성기 실행"
    $shortcut.Save()
} catch {
    Write-Warning "바탕화면 바로가기는 만들지 못했지만 프로그램 설치는 완료되었습니다."
}

Write-Host "`n설치 완료! 처음 실행하면 화면에서 API 키 설정을 안내합니다." -ForegroundColor Green
