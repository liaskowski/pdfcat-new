@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo [INFO] pdfCAT Simple Server Launcher
echo =====================================

:: 1. Start Go Services (they don't need Python)
echo [INFO] Starting Go Microservices...
echo.

:: Start Search Service
echo [1/2] Starting Search Service (Port 8001)...
start "Search Service" cmd /k "cd services\search-service && go run main.go"

:: Wait a moment
timeout /t 2 /nobreak >nul

:: Start PDF Service  
echo [2/2] Starting PDF Service (Port 8002)...
start "PDF Service" cmd /k "cd services\pdf-service && go run main.go"

:: Wait for services to start
timeout /t 3 /nobreak >nul

:: Check services
echo [INFO] Checking services...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8001/health' -TimeoutSec 2; Write-Host '[OK] Search Service is running' } catch { Write-Host '[WARN] Search Service not responding' }"
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8002/health' -TimeoutSec 2; Write-Host '[OK] PDF Service is running' } catch { Write-Host '[WARN] PDF Service not responding' }"

echo.
echo [INFO] Go Services Status:
echo   - Search Service: http://localhost:8001/health
echo   - PDF Service:   http://localhost:8002/health
echo.

:: 2. Try to start Python server with fallback
echo [INFO] Attempting to start FastAPI Server...

:: Try different Python locations
set "PYTHON_FOUND=0"

:: Try 1: Virtual environment
if exist ".venv\Scripts\python.exe" (
    echo [INFO] Using virtual environment Python...
    set "PYTHON_CMD=.venv\Scripts\python.exe"
    set "PYTHON_FOUND=1"
)

:: Try 2: System Python
if "%PYTHON_FOUND%"=="0" (
    python --version >nul 2>&1
    if !errorlevel! equ 0 (
        echo [INFO] Using system Python...
        set "PYTHON_CMD=python"
        set "PYTHON_FOUND=1"
    )
)

:: Try 3: py launcher
if "%PYTHON_FOUND%"=="0" (
    py --version >nul 2>&1
    if !errorlevel! equ 0 (
        echo [INFO] Using py launcher...
        set "PYTHON_CMD=py"
        set "PYTHON_FOUND=1"
    )
)

:: Start server if Python found
if "%PYTHON_FOUND%"=="1" (
    echo [INFO] Starting FastAPI with: !PYTHON_CMD!
    echo [INFO] Server will be at: http://localhost:8000
    echo [INFO] API Docs: http://localhost:8000/docs
    echo.
    echo [INFO] Full Stack Status:
    echo   - Go Search Service: http://localhost:8001
    echo   - Go PDF Service:   http://localhost:8002  
    echo   - FastAPI Server:   http://localhost:8000
    echo.
    echo [INFO] Press Ctrl+C to stop all services
    echo.
    
    :: Try to install basic dependencies
    echo [INFO] Installing FastAPI dependencies...
    !PYTHON_CMD! -m pip install fastapi uvicorn --quiet
    
    :: Start FastAPI
    !PYTHON_CMD! server/main.py
) else (
    echo [ERROR] No Python found!
    echo [INFO] Please install Python or create virtual environment
    echo [INFO] Go services are still running on ports 8001 and 8002
)

echo.
echo [INFO] Press any key to exit...
pause >nul
