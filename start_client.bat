@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo [INFO] PDFLib Client Launcher
echo ============================

:: 1. Define Paths
set "PYTHON_EXE=%~dp0vendor\python\python.exe"
set "UV_EXE=%~dp0vendor\uv\uv.exe"
set "SITE_PACKAGES=%~dp0vendor\python\Lib\site-packages"

:: 2. Sync Dependencies (Fast check)
echo [INFO] Checking libraries...
if not exist "%SITE_PACKAGES%" mkdir "%SITE_PACKAGES%"
"%UV_EXE%" pip install --python "%PYTHON_EXE%" --target "%SITE_PACKAGES%" -r pyproject.toml
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b %errorlevel%
)

:: 3. Launch Client
echo [INFO] Starting Client...
"%PYTHON_EXE%" client/main.py
pause
