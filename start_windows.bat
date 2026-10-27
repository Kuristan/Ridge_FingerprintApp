@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  if errorlevel 1 goto failed
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Open http://127.0.0.1:8000 in your browser. Press Ctrl+C to stop.
.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
pause
exit /b
:failed
echo Setup failed. Install Python 3.11 or 3.12, check your internet connection, then retry.
pause
