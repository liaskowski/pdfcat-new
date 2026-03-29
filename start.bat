@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo [INFO] PDFLib Cursor Variant Launcher
echo =====================================

:: 1. Cleanup old processes
echo [INFO] Cleaning up old processes...
taskkill /f /im python.exe /t >nul 2>&1

:: 2. Define Paths
set "PYTHON_EXE=%~dp0vendor\python\python.exe"
set "UV_EXE=%~dp0vendor\uv\uv.exe"
set "SITE_PACKAGES=%~dp0vendor\python\Lib\site-packages"

:: 3. Sync Dependencies
echo [INFO] Syncing libraries...
if not exist "%SITE_PACKAGES%" mkdir "%SITE_PACKAGES%"
"%UV_EXE%" pip install --python "%PYTHON_EXE%" --target "%SITE_PACKAGES%" -r pyproject.toml
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b %errorlevel%
)

:: 4. Launch Application
echo [INFO] Starting Server...
start "PDFLib Server" /min "%PYTHON_EXE%" server/main.py

echo [INFO] Waiting for server to initialize...
timeout /t 5 /nobreak >nul

echo [INFO] Starting Client...
start "PDFLib Client" "%PYTHON_EXE%" client/main.py

echo [INFO] Application launched.
exit