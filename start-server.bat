@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "PYTHON_EXE=%ROOT_DIR%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo [ERROR] Python venv not found at "%PYTHON_EXE%"
  echo Create it first from repo root:
  echo   python -m venv .venv
  echo   .venv\Scripts\Activate.ps1
  echo   pip install -r requirements.txt
  exit /b 1
)

cd /d "%ROOT_DIR%server"
set "REDIS_URL=redis://localhost:6379/0"
set "CELERY_BROKER_URL=redis://localhost:6379/0"
set "CELERY_RESULT_BACKEND_URL=redis://localhost:6379/0"
echo Starting ComfyUI local server on http://0.0.0.0:8000
"%PYTHON_EXE%" -m uvicorn app.main:socket_app --host 0.0.0.0 --port 8000

endlocal
