@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "START_SERVER=%ROOT_DIR%start-server.bat"
set "START_WORKER=%ROOT_DIR%start-worker.bat"

if not exist "%START_SERVER%" (
  echo [ERROR] Missing "%START_SERVER%"
  exit /b 1
)

if not exist "%START_WORKER%" (
  echo [ERROR] Missing "%START_WORKER%"
  exit /b 1
)

echo Launching backend server and Celery worker in separate windows...
start "ComfyUI Local Server" cmd /k ""%START_SERVER%""
start "ComfyUI Worker" cmd /k ""%START_WORKER%""

echo Done.
endlocal
