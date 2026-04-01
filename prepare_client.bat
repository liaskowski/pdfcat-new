@echo off
:: Check for administrative privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script must be run as Administrator!
    echo Please right-click and "Run as Administrator".
    pause
    exit /b 1
)

echo [INFO] Configuring Windows Firewall for PDFLib CLIENT...

:: Allow incoming UDP for Discovery
echo Allowing Discovery Beacon (UDP 50010) incoming...
netsh advfirewall firewall delete rule name="PDFLib_Client_Discovery" >nul 2>&1
netsh advfirewall firewall add rule name="PDFLib_Client_Discovery" dir=in action=allow protocol=UDP localport=50010 profile=any

:: Allow Python specifically
set "PYTHON_EXE=%~dp0vendor\python\python.exe"
if exist "%PYTHON_EXE%" (
    echo Allowing Python executable...
    netsh advfirewall firewall delete rule name="PDFLib_Client_Python" >nul 2>&1
    netsh advfirewall firewall add rule name="PDFLib_Client_Python" dir=in action=allow program="%PYTHON_EXE%" enable=yes profile=any
)

echo.
echo [SUCCESS] Client network environment is ready.
echo Now start the client application.
pause
