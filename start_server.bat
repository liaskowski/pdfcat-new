@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo [INFO] pdfCAT Background Server Launcher
echo ========================================

:: 1. Define Paths
set "PYTHONW_EXE=%~dp0vendor\python\pythonw.exe"
set "PYTHON_EXE=%~dp0vendor\python\python.exe"
set "UV_EXE=%~dp0vendor\uv\uv.exe"

:: 2. Check Portable Python
if not exist "%PYTHONW_EXE%" (
    echo [ERROR] Portable Python (pythonw.exe) not found at:
    echo %PYTHONW_EXE%
    pause
    exit /b 1
)

:: 3. Sync Dependencies (using uv)
echo [INFO] Checking Python libraries...
if exist "%UV_EXE%" (
    "%UV_EXE%" pip install --python "%PYTHON_EXE%" -r server/requirements.txt --quiet
)

:: 4. Launch Tray Manager (Headless)
echo [INFO] Starting Server Manager in System Tray...
echo [INFO] No console windows will be shown.
echo [INFO] Look for the pdfCAT icon in your taskbar tray.

start "" "%PYTHONW_EXE%" server_manager_tray.py

echo.
echo [SUCCESS] Launcher finished. You can close this window.
timeout /t 3
exit
