#!/usr/bin/env pwsh
"""
Cleanup script for ports 8000, 8001, 8002 on Windows
"""

Write-Host "🧹 Cleaning up ports for pdfCAT services..." -ForegroundColor Green

# Ports to clean up
$ports = @(8000, 8001, 8002)

foreach ($port in $ports) {
    Write-Host "Checking port ${port}..." -ForegroundColor Yellow
    
    # Get processes using the port
    $connections = netstat -ano | findstr ":${port}"
    
    if ($connections) {
        Write-Host "Found connections on port ${port}:" -ForegroundColor Red
        Write-Host $connections
        
        # Extract PIDs and kill processes
        $connections | ForEach-Object {
            if ($_ -match '(\d+)$') {
                $processId = $matches[1]
                try {
                    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
                    if ($process) {
                        Write-Host "Killing process ${processId} ($($process.ProcessName)) using port ${port}" -ForegroundColor Red
                        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                    } else {
                        Write-Host "Process ${processId} not found, port might be released" -ForegroundColor Yellow
                    }
                } catch {
                    Write-Host "Failed to kill process ${processId}: $($_.Exception.Message)" -ForegroundColor Red
                }
            }
        }
    } else {
        Write-Host "Port ${port} is free" -ForegroundColor Green
    }
}

# Wait a moment for ports to be released
Write-Host "Waiting 2 seconds for ports to be released..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

# Verify ports are free
Write-Host "Verifying ports are free..." -ForegroundColor Yellow
$allClear = $true

foreach ($port in $ports) {
    $connections = netstat -ano | findstr ":${port}"
    if ($connections) {
        Write-Host "⚠️ Port ${port} still in use:" -ForegroundColor Red
        Write-Host $connections
        $allClear = $false
    } else {
        Write-Host "✅ Port ${port} is free" -ForegroundColor Green
    }
}

if ($allClear) {
    Write-Host "🎉 All ports are clean! Ready to start services." -ForegroundColor Green
} else {
    Write-Host "⚠️ Some ports are still in use. You may need to restart your computer." -ForegroundColor Yellow
}

Write-Host "Port cleanup complete!" -ForegroundColor Green
