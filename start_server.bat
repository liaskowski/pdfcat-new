@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo [INFO] pdfCAT Background Server Launcher
echo ========================================

:: 1. Define Paths
set "PYTHON_DIR=%~dp0vendor\python"
set "PYTHONW_EXE=%PYTHON_DIR%\pythonw.exe"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "UV_EXE=%~dp0vendor\uv\uv.exe"
set "SITE_PACKAGES=%PYTHON_DIR%\Lib\site-packages"
set "PYTHONIOENCODING=utf-8"

:: 2. Check Portable Python
if not exist "%PYTHONW_EXE%" (
    echo [ERROR] Portable Python not found at: "%PYTHONW_EXE%"
    pause
    exit /b 1
)

:: 3. Sync Dependencies (if UV exists)
if exist "%UV_EXE%" (
    echo [INFO] Syncing libraries with UV...
    if not exist "%SITE_PACKAGES%" mkdir "%SITE_PACKAGES%"
    "%UV_EXE%" pip install --python "%PYTHON_EXE%" --target "%SITE_PACKAGES%" -r pyproject.toml --quiet
)

:: 4. Launch Tray Manager
echo [INFO] Starting Server Manager in System Tray...
start "" "%PYTHONW_EXE%" "%~dp0server_manager_tray.py"

echo [INFO] Launcher finished. You can close this window.
timeout /t 3
exit
