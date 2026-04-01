@echo off
:: Check for administrative privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script must be run as Administrator!
    echo Please right-click and "Run as Administrator".
    pause
    exit /b 1
)

set "PYTHON_EXE=%~dp0vendor\python\python.exe"

echo [INFO] Configuring Windows Firewall for pdfCAT...

:: 1. Allow Port 8000 (Main API)
echo [1/4] Allowing Port 8000 (Main API)...
netsh advfirewall firewall delete rule name="PDFLib_Server" >nul 2>&1
netsh advfirewall firewall add rule name="PDFLib_Server" dir=in action=allow protocol=TCP localport=8000 profile=any

:: 2. Allow Port 8001 (Search Service)
echo [2/4] Allowing Port 8001 (Search Service)...
netsh advfirewall firewall delete rule name="PDFLib_Search" >nul 2>&1
netsh advfirewall firewall add rule name="PDFLib_Search" dir=in action=allow protocol=TCP localport=8001 profile=any

:: 3. Allow Port 8002 (PDF Service)
echo [3/4] Allowing Port 8002 (PDF Service)...
netsh advfirewall firewall delete rule name="PDFLib_PDFSvc" >nul 2>&1
netsh advfirewall firewall add rule name="PDFLib_PDFSvc" dir=in action=allow protocol=TCP localport=8002 profile=any

:: 4. Allow Python App specifically (very important for discovery)
if exist "%PYTHON_EXE%" (
    echo [4/4] Allowing Python executable for Network Discovery...
    netsh advfirewall firewall delete rule name="PDFLib_Python" >nul 2>&1
    netsh advfirewall firewall add rule name="PDFLib_Python" dir=in action=allow program="%PYTHON_EXE%" enable=yes profile=any
) else (
    echo [SKIP] Portable Python not found at %PYTHON_EXE%
)

:: 5. Allow Go Services (by port is enough, but we could add program rules if needed)

echo.
echo [SUCCESS] Network environment is now configured.
echo 1. Ports 8000-8002 are open.
echo 2. Python is allowed through firewall (enables Zeroconf/mDNS).
echo.
echo Your LAN computers can now connect to this server AUTOMATICALLY.
pause
