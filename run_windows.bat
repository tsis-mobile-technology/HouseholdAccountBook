@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ===================================================
echo   🌸 HouseholdAccountBook (스마트 파스텔 가계부)
echo ===================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않거나 PATH에 등록되지 않았습니다.
    echo https://www.python.org 에서 Python 3.10 이상을 설치해주세요.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [안내] 가상환경(.venv)을 생성합니다...
    python -m venv .venv
)

echo [안내] 의존성 패키지를 확인하고 설치합니다...
call .venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

echo.
echo [안내] 가계부 서버를 시작합니다...
echo 브라우저에서 잠시 후 자동으로 열립니다.
start http://localhost:8000
python -m app.main

pause
