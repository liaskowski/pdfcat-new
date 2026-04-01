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
echo [1/5] Allowing Port 8000 (Main API)...
netsh advfirewall firewall delete rule name="PDFLib_Server" >nul 2>&1
netsh advfirewall firewall add rule name="PDFLib_Server" dir=in action=allow protocol=TCP localport=8000 profile=any

:: 2. Allow Port 8001 (Search Service)
echo [2/5] Allowing Port 8001 (Search Service)...
netsh advfirewall firewall delete rule name="PDFLib_Search" >nul 2>&1
netsh advfirewall firewall add rule name="PDFLib_Search" dir=in action=allow protocol=TCP localport=8001 profile=any

:: 3. Allow Port 8002 (PDF Service)
echo [3/5] Allowing Port 8002 (PDF Service)...
netsh advfirewall firewall delete rule name="PDFLib_PDFSvc" >nul 2>&1
netsh advfirewall firewall add rule name="PDFLib_PDFSvc" dir=in action=allow protocol=TCP localport=8002 profile=any

:: 4. Allow mDNS (Multicast DNS) for Zeroconf Discovery
echo [4/5] Allowing Port 5353 (UDP) for Zeroconf/mDNS...
netsh advfirewall firewall delete rule name="PDFLib_Zeroconf" >nul 2>&1
netsh advfirewall firewall add rule name="PDFLib_Zeroconf" dir=in action=allow protocol=UDP localport=5353 profile=any

:: 5. Allow Python App specifically (very important for discovery)
if exist "%PYTHON_EXE%" (
    echo [5/5] Allowing Python executable for Network Discovery...
    netsh advfirewall firewall delete rule name="PDFLib_Python" >nul 2>&1
    netsh advfirewall firewall add rule name="PDFLib_Python" dir=in action=allow program="%PYTHON_EXE%" enable=yes profile=any
) else (
    echo [SKIP] Portable Python not found at %PYTHON_EXE%
)

echo.
echo [SUCCESS] Network environment is now configured.
echo 1. Ports 8000-8002 are open (TCP).
echo 2. Port 5353 is open (UDP) for Discovery.
echo 3. Python is allowed through firewall (enables Zeroconf/mDNS).
echo.
echo Your LAN computers can now connect to this server AUTOMATICALLY.
pause
