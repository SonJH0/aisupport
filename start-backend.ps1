$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 설치 상태를 확인해 주세요.' }
}
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw '패키지 설치에 실패했습니다.' }
if (-not $env:OPENAI_API_KEY -and -not $env:CODYSSEY_API_KEY -and -not (Test-Path '.env')) {
    $secureKey = Read-Host '코디세이 API 키를 입력하세요' -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    try { $env:CODYSSEY_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer).Trim() }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}
& $python -m uvicorn backend.main:app --reload
