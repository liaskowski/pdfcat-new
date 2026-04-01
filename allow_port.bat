@echo off
:: Check for administrative privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script must be run as Administrator!
    echo Please right-click and "Run as Administrator".
    pause
    exit /b 1
)

echo [INFO] Configuring Windows Firewall for pdfCAT (Ultra-Reliable Mode)...

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

:: 4. Allow UDP Beacon Port (50010) for Discovery
echo [4/5] Allowing Port 50010 (UDP) for Discovery Beacon...
netsh advfirewall firewall delete rule name="PDFLib_Beacon" >nul 2>&1
netsh advfirewall firewall add rule name="PDFLib_Beacon" dir=in action=allow protocol=UDP localport=50010 profile=any

:: 5. Allow Python executable (General rule)
set "PYTHON_EXE=%~dp0vendor\python\python.exe"
if exist "%PYTHON_EXE%" (
    echo [5/5] Allowing Python executable for all network tasks...
    netsh advfirewall firewall delete rule name="PDFLib_Python" >nul 2>&1
    netsh advfirewall firewall add rule name="PDFLib_Python" dir=in action=allow program="%PYTHON_EXE%" enable=yes profile=any
)

echo.
echo [SUCCESS] Network is now ready. 
echo Discovery now uses ultra-reliable UDP Beacons.
pause
