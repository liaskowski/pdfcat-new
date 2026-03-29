#!/usr/bin/env python3
"""
pdfCAT Project Setup Script
For new team members to get started quickly
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(cmd, description, check=True):
    """Run command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.stdout.strip():
            print(f"✅ {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"   Details: {e.stderr.strip()}")
        return False

def check_python_version():
    """Check Python version compatibility"""
    version = sys.version_info
    print(f"🐍 Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 12):
        print("❌ Python 3.12+ is required")
        return False
    
    print("✅ Python version compatible")
    return True

def setup_virtual_environment():
    """Create and setup virtual environment"""
    venv_path = Path(".venv")
    
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return True
    
    print("📦 Creating virtual environment...")
    success = run_command(f"{sys.executable} -m venv .venv", "Creating .venv")
    
    if success:
        print("✅ Virtual environment created successfully")
        return True
    else:
        print("❌ Failed to create virtual environment")
        return False

def install_dependencies():
    """Install Python dependencies"""
    requirements_files = [
        "server/requirements.txt",
        "client/requirements.txt"
    ]
    
    python_exe = Path(".venv") / "Scripts" / "python.exe" if platform.system() == "Windows" else Path(".venv") / "bin" / "python"
    python_exe_str = str(python_exe)
    
    for req_file in requirements_files:
        if Path(req_file).exists():
            print(f"📦 Installing dependencies from {req_file}...")
            success = run_command(f'"{python_exe_str}" -m pip install -r {req_file}', f"Installing {req_file}")
            if not success:
                print(f"⚠️  Failed to install {req_file}, continuing...")
        else:
            print(f"⚠️  {req_file} not found, skipping...")

def setup_go_services():
    """Setup Go microservices"""
    print("🐍 Checking Go installation...")
    
    # Check if Go is installed
    try:
        result = subprocess.run(["go", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Go installed: {result.stdout.strip()}")
            
            # Download Go modules
            if Path("services").exists():
                print("📦 Downloading Go modules...")
                success = run_command("cd services && go mod download", "Downloading Go modules", check=False)
                if success:
                    print("✅ Go modules ready")
                else:
                    print("⚠️  Go modules download failed, but continuing...")
            else:
                print("⚠️  services directory not found")
        else:
            print("❌ Go not installed")
            return False
    except FileNotFoundError:
        print("❌ Go not found in PATH")
        return False
    
    return True

def create_env_file():
    """Create .env file if it doesn't exist"""
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    print("📝 Creating .env file...")
    env_content = """# Server Configuration
PORT=8000
HOST=0.0.0.0
DEBUG=false

# Database
DATABASE_URL=sqlite:///./app.db

# Security
SECRET_KEY=change-this-secret-key-in-production
ADMIN_PASSWORD=admin

# OCR (Windows)
TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe

# OCR (Linux/macOS) - uncomment if needed
# TESSERACT_CMD=/usr/bin/tesseract
"""
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        print("✅ .env file created")
        print("⚠️  Please update SECRET_KEY before production use")
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")

def verify_setup():
    """Verify that setup is complete"""
    print("\n🔍 Verifying setup...")
    
    checks = [
        ("Virtual environment", Path(".venv").exists()),
        ("Server requirements", Path("server/requirements.txt").exists()),
        ("Client requirements", Path("client/requirements.txt").exists()),
        ("Start script", Path("start_server.bat").exists() or Path("start_all.py").exists()),
        ("Environment file", Path(".env").exists()),
    ]
    
    all_good = True
    for name, check in checks:
        status = "✅" if check else "❌"
        print(f"  {status} {name}")
        if not check:
            all_good = False
    
    return all_good

def main():
    """Main setup function"""
    print("🚀 pdfCAT Project Setup")
    print("=" * 40)
    print("This script will set up your development environment")
    print()
    
    # Check Python version
    if not check_python_version():
        print("\n❌ Setup failed: Python version incompatible")
        sys.exit(1)
    
    # Setup virtual environment
    if not setup_virtual_environment():
        print("\n❌ Setup failed: Virtual environment")
        sys.exit(1)
    
    # Install dependencies
    install_dependencies()
    
    # Setup Go services
    setup_go_services()
    
    # Create environment file
    create_env_file()
    
    # Verify setup
    if verify_setup():
        print("\n🎉 Setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Activate virtual environment:")
        if platform.system() == "Windows":
            print("   .venv\\Scripts\\activate")
        else:
            print("   source .venv/bin/activate")
        print("2. Start the application:")
        print("   .\\start_server.bat    # Windows")
        print("   python start_all.py   # Cross-platform")
        print("3. Open http://localhost:8000/docs for API documentation")
        print("\n📖 See README.md for more information")
    else:
        print("\n⚠️  Setup completed with some issues")
        print("Please check the errors above and fix them manually")

if __name__ == "__main__":
    main()
