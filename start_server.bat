@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo [INFO] pdfCAT Server Launcher (Portable)
echo ========================================

:: 0. Cleanup ports first
echo [INFO] Cleaning up ports 8000, 8001, 8002...
powershell -ExecutionPolicy Bypass -File "%~dp0cleanup_ports.ps1"
echo.

:: 1. Define Paths
set "PYTHON_EXE=%~dp0vendor\python\python.exe"
set "UV_EXE=%~dp0vendor\uv\uv.exe"
set "GO_EXE=go"

:: 2. Check Portable Python
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Portable Python not found at:
    echo %PYTHON_EXE%
    echo.
    echo Please ensure the 'vendor' directory is correctly populated.
    pause
    exit /b 1
)

echo [INFO] Using Portable Python: %PYTHON_EXE%
"%PYTHON_EXE%" --version

:: 3. Start Go Microservices
echo [INFO] Starting Go Microservices...
echo.

:: Start Search Service
echo [1/6] Starting Search Service (Port 8001)...
start "Search Service" cmd /k "cd services\search-service && go run main.go"

:: Wait a moment for search service
timeout /t 2 /nobreak >nul

:: Start PDF Service  
echo [2/6] Starting PDF Service (Port 8002)...
start "PDF Service" cmd /k "cd services\pdf-service && go run main.go"

:: Wait a moment for PDF service
timeout /t 2 /nobreak >nul

:: Check if services are running
echo [INFO] Checking Go services health...
timeout /t 3 /nobreak >nul

:: Try to check search service
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8001/health' -TimeoutSec 2 -UseBasicParsing; Write-Host '[OK] Search Service is running' } catch { Write-Host '[WARN] Search Service not responding' }"

:: Try to check PDF service
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8002/health' -TimeoutSec 2 -UseBasicParsing; Write-Host '[OK] PDF Service is running' } catch { Write-Host '[WARN] PDF Service not responding' }"

echo.
echo [INFO] Go Microservices Status:
echo   - Search Service: http://localhost:8001/health
echo   - PDF Service:   http://localhost:8002/health
echo.

:: 4. Sync Dependencies (using uv)
echo [INFO] Checking Python libraries...
if exist "%UV_EXE%" (
    echo [INFO] Syncing dependencies with uv...
    "%UV_EXE%" pip install --python "%PYTHON_EXE%" -r server/requirements.txt --quiet
) else (
    echo [WARN] uv not found, skipping dependency sync. Assuming packages are pre-installed.
)

:: 5. Launch FastAPI Server
echo [INFO] Starting FastAPI Server...
echo [INFO] Server will be available at: http://localhost:8000
echo [INFO] API Docs: http://localhost:8000/docs
echo.
echo [INFO] Full Stack Status:
echo   - Go Search Service: http://localhost:8001
echo   - Go PDF Service:   http://localhost:8002  
echo   - FastAPI Server:   http://localhost:8000
echo.
echo [INFO] Press Ctrl+C to stop all services
echo.

"%PYTHON_EXE%" server/main.py

echo.
echo [INFO] Server stopped. Press any key to exit...
pause >nul
