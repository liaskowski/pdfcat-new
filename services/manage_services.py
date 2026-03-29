#!/usr/bin/env python3
"""
Go Microservices Management Script
Start, stop, and manage all Go microservices
"""

import subprocess
import time
import os
import signal
import sys
from typing import Dict, List

class ServiceManager:
    """Manage Go microservices"""
    
    def __init__(self):
        self.services = {
            "search-service": {
                "port": 8001,
                "path": "search-service",
                "description": "Fast text search with Bluge indexing"
            },
            "pdf-service": {
                "port": 8002, 
                "path": "pdf-service",
                "description": "PDF processing, extraction, and optimization"
            },
            "thumbnail-service": {
                "port": 8003,
                "path": "thumbnail-service", 
                "description": "Parallel thumbnail generation"
            },
            "ocr-service": {
                "port": 8004,
                "path": "ocr-service",
                "description": "Fast OCR processing with Tesseract"
            },
            "upload-service": {
                "port": 8005,
                "path": "upload-service",
                "description": "Non-blocking file uploads with progress"
            },
            "websocket-service": {
                "port": 8006,
                "path": "websocket-service",
                "description": "Real-time collaboration and notifications"
            }
        }
        self.processes: Dict[str, subprocess.Popen] = {}
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
    
    def start_service(self, service_name: str) -> bool:
        """Start a specific service"""
        if service_name not in self.services:
            print(f"❌ Unknown service: {service_name}")
            return False
        
        service = self.services[service_name]
        service_path = os.path.join(self.base_dir, service["path"])
        
        if not os.path.exists(service_path):
            print(f"❌ Service path not found: {service_path}")
            print(f"   Service {service_name} is not implemented yet")
            return False
        
        # Check if service is already running
        if service_name in self.processes:
            if self.processes[service_name].poll() is None:
                print(f"✅ Service {service_name} is already running")
                return True
            else:
                del self.processes[service_name]
        
        print(f"🚀 Starting {service_name} on port {service['port']}...")
        
        try:
            # Start the service
            env = os.environ.copy()
            env["PORT"] = str(service["port"])
            
            process = subprocess.Popen(
                ["go", "run", "main.go"],
                cwd=service_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            self.processes[service_name] = process
            
            # Wait a moment for startup
            time.sleep(2)
            
            if process.poll() is None:
                print(f"✅ {service_name} started successfully (PID: {process.pid})")
                return True
            else:
                print(f"❌ Failed to start {service_name}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting {service_name}: {e}")
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """Stop a specific service"""
        if service_name not in self.processes:
            print(f"⚠️  Service {service_name} is not running")
            return True
        
        process = self.processes[service_name]
        
        try:
            print(f"🛑 Stopping {service_name}...")
            process.terminate()
            
            # Wait for graceful shutdown
            try:
                process.wait(timeout=5)
                print(f"✅ {service_name} stopped gracefully")
            except subprocess.TimeoutExpired:
                print(f"⚠️  Force killing {service_name}...")
                process.kill()
                process.wait()
                print(f"✅ {service_name} force killed")
            
            del self.processes[service_name]
            return True
            
        except Exception as e:
            print(f"❌ Error stopping {service_name}: {e}")
            return False
    
    def start_all(self):
        """Start all available services"""
        print("🚀 Starting all Go microservices...")
        print("=" * 50)
        
        started = 0
        for service_name in self.services:
            if self.start_service(service_name):
                started += 1
            time.sleep(1)  # Brief pause between services
        
        print(f"\n📊 Started {started}/{len(self.services)} services")
        self.show_status()
    
    def stop_all(self):
        """Stop all running services"""
        print("🛑 Stopping all Go microservices...")
        print("=" * 50)
        
        stopped = 0
        for service_name in list(self.processes.keys()):
            if self.stop_service(service_name):
                stopped += 1
        
        print(f"\n📊 Stopped {stopped} services")
    
    def show_status(self):
        """Show status of all services"""
        print("\n📊 Service Status:")
        print("=" * 50)
        
        for service_name, service in self.services.items():
            status = "🔴 Stopped"
            port_info = f":{service['port']}"
            
            if service_name in self.processes:
                process = self.processes[service_name]
                if process.poll() is None:
                    status = "🟢 Running"
                    port_info = f":{service['port']} (PID: {process.pid})"
                else:
                    status = "🔴 Crashed"
                    del self.processes[service_name]
            
            # Check if service exists
            service_path = os.path.join(self.base_dir, service["path"])
            exists = "✅" if os.path.exists(service_path) else "❌"
            
            print(f"{status} {exists} {service_name:<20} {port_info:<15} {service['description']}")
    
    def check_health(self):
        """Check health of running services"""
        print("\n🏥 Health Check:")
        print("=" * 50)
        
        import requests
        
        for service_name, service in self.services.items():
            if service_name in self.processes:
                try:
                    response = requests.get(f"http://localhost:{service['port']}/health", timeout=2)
                    if response.status_code == 200:
                        print(f"✅ {service_name}: Healthy")
                    else:
                        print(f"⚠️  {service_name}: HTTP {response.status_code}")
                except Exception as e:
                    print(f"❌ {service_name}: Unreachable ({e})")
            else:
                print(f"🔴 {service_name}: Not running")
    
    def cleanup_old_folders(self):
        """Clean up old service folders"""
        print("\n🧹 Cleaning up old folders...")
        
        old_folders = ["search-go", "pdf-processing"]
        base_dir = self.base_dir
        
        for folder in old_folders:
            folder_path = os.path.join(base_dir, folder)
            if os.path.exists(folder_path):
                try:
                    import shutil
                    shutil.rmtree(folder_path)
                    print(f"✅ Removed old folder: {folder}")
                except Exception as e:
                    print(f"⚠️  Could not remove {folder}: {e}")
    
    def show_structure(self):
        """Show current services structure"""
        print("\n📁 Services Structure:")
        print("=" * 50)
        
        for service_name, service in self.services.items():
            service_path = os.path.join(self.base_dir, service["path"])
            exists = os.path.exists(service_path)
            
            status = "✅" if exists else "❌"
            print(f"{status} {service_name}/")
            
            if exists:
                # List files in service directory
                try:
                    files = os.listdir(service_path)
                    for file in sorted(files):
                        if not file.startswith('.'):
                            print(f"   📄 {file}")
                except Exception as e:
                    print(f"   ❌ Error listing files: {e}")

def main():
    """Main management interface"""
    manager = ServiceManager()
    
    if len(sys.argv) < 2:
        print("🚀 Go Microservices Manager")
        print("=" * 40)
        print("Usage: python manage_services.py <command>")
        print("\nCommands:")
        print("  start <service>     - Start specific service")
        print("  stop <service>      - Stop specific service") 
        print("  start-all          - Start all services")
        print("  stop-all           - Stop all services")
        print("  status             - Show service status")
        print("  health             - Check health of running services")
        print("  structure          - Show services structure")
        print("  cleanup            - Clean up old folders")
        print("\nAvailable services:")
        for name, service in manager.services.items():
            print(f"  {name:<20} - {service['description']}")
        return
    
    command = sys.argv[1].lower()
    
    if command == "start":
        if len(sys.argv) < 3:
            print("❌ Please specify service name")
            return
        manager.start_service(sys.argv[2])
    
    elif command == "stop":
        if len(sys.argv) < 3:
            print("❌ Please specify service name")
            return
        manager.stop_service(sys.argv[2])
    
    elif command == "start-all":
        manager.start_all()
    
    elif command == "stop-all":
        manager.stop_all()
    
    elif command == "status":
        manager.show_status()
    
    elif command == "health":
        manager.check_health()
    
    elif command == "structure":
        manager.show_structure()
    
    elif command == "cleanup":
        manager.cleanup_old_folders()
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()
