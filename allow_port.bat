@echo off
echo Opening TCP Port 8000 in Windows Firewall...
netsh advfirewall firewall add rule name="PDFLib_Server" dir=in action=allow protocol=TCP localport=8000
echo Done! You can now connect to this server from other computers on the LAN.
pause
