# Setup Vendor Environment for pdfCAT
# This script downloads and extracts Python embeddable and UV to the vendor/ folder.

$ErrorActionPreference = "Stop"

$VENDOR_DIR = Join-Path $PSScriptRoot "..\vendor"
$PYTHON_DIR = Join-Path $VENDOR_DIR "python"
$UV_DIR = Join-Path $VENDOR_DIR "uv"

# URLs
$PYTHON_URL = "https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-amd64.zip"
$UV_URL = "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"

Write-Host "🚀 Starting Vendor Setup..." -ForegroundColor Cyan

# Create directories
if (-not (Test-Path $VENDOR_DIR)) {
    New-Item -ItemType Directory -Path $VENDOR_DIR | Out-Null
}

# Setup Python
if (-not (Test-Path $PYTHON_DIR)) {
    Write-Host "📦 Downloading Python 3.12.9 Embeddable..." -ForegroundColor Yellow
    $tempZip = Join-Path $env:TEMP "python-embed.zip"
    Invoke-WebRequest -Uri $PYTHON_URL -OutFile $tempZip
    
    New-Item -ItemType Directory -Path $PYTHON_DIR | Out-Null
    Write-Host "📂 Extracting Python..." -ForegroundColor Yellow
    Expand-Archive -Path $tempZip -DestinationPath $PYTHON_DIR -Force
    Remove-Item $tempZip
    
    # Enable site-packages in ._pth if it exists
    $pthFile = Get-ChildItem -Path $PYTHON_DIR -Filter "*._pth" | Select-Object -First 1
    if ($pthFile) {
        Write-Host "⚙️ Configuring Python ._pth..." -ForegroundColor Yellow
        $content = Get-Content $pthFile.FullName
        $content = $content -replace "#import site", "import site"
        $content | Set-Content $pthFile.FullName
    }
} else {
    Write-Host "✅ Python already exists in vendor/python" -ForegroundColor Green
}

# Setup UV
if (-not (Test-Path $UV_DIR)) {
    Write-Host "📦 Downloading UV Package Manager..." -ForegroundColor Yellow
    $tempZip = Join-Path $env:TEMP "uv.zip"
    Invoke-WebRequest -Uri $UV_URL -OutFile $tempZip
    
    New-Item -ItemType Directory -Path $UV_DIR | Out-Null
    Write-Host "📂 Extracting UV..." -ForegroundColor Yellow
    Expand-Archive -Path $tempZip -DestinationPath $UV_DIR -Force
    Remove-Item $tempZip
    
    # Check if uv.exe is inside a subdirectory
    $uvExe = Get-ChildItem -Path $UV_DIR -Filter "uv.exe" -Recurse | Select-Object -First 1
    if ($uvExe -and $uvExe.DirectoryName -ne $UV_DIR) {
        Move-Item $uvExe.FullName $UV_DIR -Force
        # Optional: Clean up empty subdirectories if needed
    }
} else {
    Write-Host "✅ UV already exists in vendor/uv" -ForegroundColor Green
}

Write-Host "`n✨ Vendor setup complete!" -ForegroundColor Cyan
Write-Host "You can now use start.bat or other scripts that rely on the vendor environment."
