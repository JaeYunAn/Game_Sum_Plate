@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Python environment not found.
    echo Install requirements first.
    pause
    exit /b 1
)

start "번호판 더하기 서버" "%~dp0.venv\Scripts\python.exe" -m uvicorn server:app --host 127.0.0.1 --port 8000
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000"
