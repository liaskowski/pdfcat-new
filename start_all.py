#!/usr/bin/env python3
"""
Simple Python script to start all services
Works around Python path issues
"""

import subprocess
import sys
import time
import os
import socket
from pathlib import Path

# Import Windows-specific constants
if os.name == 'nt':
    import subprocess
    CREATE_NEW_CONSOLE = 0x00000010
else:
    CREATE_NEW_CONSOLE = 0

def cleanup_ports():
    """Clean up ports 8000, 8001, 8002"""
    print("🧹 Cleaning up ports...")
    
    ports = [8000, 8001, 8002]
    
    for port in ports:
        try:
            # Check if port is in use
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                print(f"Port {port} is in use, killing processes...")
                # Kill processes using the port on Windows
                if os.name == 'nt':
                    subprocess.run(f'netstat -ano | findstr ":{port}"', shell=True, capture_output=True)
                    subprocess.run(f'for /f "tokens=5" %a in (\'netstat -ano ^| findstr ":{port}"^) do taskkill /F /PID %a', shell=True, capture_output=True)
                else:
                    subprocess.run(f'lsof -ti :{port} | xargs kill -9', shell=True, capture_output=True)
                
                time.sleep(1)  # Wait for port to be released
            else:
                print(f"Port {port} is free")
        except Exception as e:
            print(f"Error checking port {port}: {e}")
    
    print("✅ Port cleanup complete")

def run_command(cmd, cwd=None, shell=True):
    """Run command and return success"""
    try:
        result = subprocess.run(cmd, shell=shell, cwd=cwd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_service(url, name):
    """Check if service is responding"""
    try:
        import requests
        response = requests.get(url, timeout=2)
        return response.status_code == 200
    except:
        return False

def start_go_service(service_name, service_path, port):
    """Start a Go service"""
    print(f"[{service_name}] Starting on port {port}...")
    
    service_dir = Path(__file__).parent / service_path
    if not service_dir.exists():
        print(f"[{service_name}] ❌ Service directory not found: {service_dir}")
        return False
    
    # Start service in background
    try:
        if os.name == 'nt':  # Windows
            cmd = f'cd "{service_dir}" && go run main.go'
            proc = subprocess.Popen(
                cmd,
                shell=True,
                cwd=service_dir
            )
        else:  # Unix
            proc = subprocess.Popen(
                ["go", "run", "main.go"],
                cwd=service_dir
            )
        
        time.sleep(3)  # Wait for startup
        return True
    except Exception as e:
        print(f"[{service_name}] ❌ Failed to start: {e}")
        return False

def find_python():
    """Find working Python executable"""
    candidates = [
        ".venv/Scripts/python.exe",
        ".venv/bin/python",
        "python",
        "python3",
        "py"
    ]
    
    for candidate in candidates:
        try:
            result = subprocess.run([candidate, "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"[Python] ✅ Found: {candidate}")
                print(f"[Python] Version: {result.stdout.strip()}")
                return candidate
        except:
            continue
    
    print("[Python] ❌ No working Python found")
    return None

def main():
    print("🚀 pdfCAT Full Stack Launcher")
    print("=" * 40)
    
    base_dir = Path(__file__).parent
    
    # 0. Cleanup ports first
    cleanup_ports()
    
    # 1. Start Go services
    print("\n📦 Starting Go Microservices...")
    
    services = [
        ("Search Service", "services/search-service", 8001),
        ("PDF Service", "services/pdf-service", 8002)
    ]
    
    started_services = []
    
    for name, path, port in services:
        if start_go_service(name, path, port):
            started_services.append((name, port))
    
    # Wait for services to be ready
    print("\n⏳ Waiting for services to start...")
    time.sleep(3)
    
    # Check service health
    print("\n🏥 Health Check:")
    for name, port in started_services:
        url = f"http://localhost:{port}/health"
        if check_service(url, name):
            print(f"  ✅ {name}: Healthy")
        else:
            print(f"  ❌ {name}: Not responding")
    
    # 2. Start FastAPI server
    print("\n🐍 Starting FastAPI Server...")
    
    python_exe = find_python()
    if not python_exe:
        print("\n❌ Cannot start FastAPI - no Python found")
        print("📦 Go services are still running:")
        for name, port in started_services:
            print(f"   - {name}: http://localhost:{port}")
        return
    
    # Install basic dependencies
    print("[FastAPI] Installing dependencies...")
    success, stdout, stderr = run_command(f"{python_exe} -m pip install fastapi uvicorn")
    if not success:
        print("[FastAPI] ⚠️  Warning: Could not install dependencies")
    
    # Start FastAPI
    print(f"[FastAPI] 🚀 Starting server with {python_exe}")
    print("[FastAPI] 📖 API Docs: http://localhost:8000/docs")
    print("\n📊 Full Stack Status:")
    for name, port in started_services:
        print(f"   - {name}: http://localhost:{port}")
    print(f"   - FastAPI:   http://localhost:8000")
    print("\n⚠️  Press Ctrl+C to stop all services")
    print("-" * 40)
    
    # Start FastAPI server
    try:
        subprocess.run([python_exe, "server/main.py"], cwd=base_dir)
    except KeyboardInterrupt:
        print("\n🛑 Services stopped by user")
    except Exception as e:
        print(f"\n❌ FastAPI error: {e}")

if __name__ == "__main__":
    main()
