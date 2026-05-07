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
echo Starting Celery worker on queue gpu_render_queue
"%PYTHON_EXE%" -m celery -A app.queue.celery_app:celery_app worker --pool=solo --loglevel=INFO --concurrency=1 --queues=gpu_render_queue --prefetch-multiplier=1

endlocal
