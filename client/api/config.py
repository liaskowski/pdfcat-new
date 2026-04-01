import socket
import logging
import time
import requests
import json
import threading
from typing import Optional

logger = logging.getLogger(__name__)

class AppConfig:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance.base_url = "http://127.0.0.1:8000" # Fallback
            cls._instance.discover_server()
        return cls._instance

    def discover_server(self, timeout: float = 3.0, beacon_port: int = 50010):
        """Listen for UDP beacons from the server"""
        logger.info(f"🔍 Listening for PDFLib beacon on port {beacon_port}...")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Enable broadcast listening
        try:
            sock.bind(('', beacon_port))
        except Exception as e:
            logger.error(f"Could not bind to beacon port: {e}")
            return self.base_url

        sock.settimeout(0.5)
        start_time = time.time()
        found_url = None

        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(2048)
                payload = json.loads(data.decode('utf-8'))
                
                if payload.get("service") == "pdflib":
                    url = payload.get("url")
                    logger.info(f"📡 Received beacon from {payload.get('hostname')} at {url}")
                    
                    # Quick verify
                    try:
                        resp = requests.get(f"{url}/health", timeout=0.5)
                        if resp.status_code == 200:
                            found_url = url
                            break
                    except Exception:
                        continue
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Discovery listen error: {e}")
                break
        
        sock.close()
        
        if found_url:
            self.base_url = found_url
            logger.info(f"🚀 Connected to discovered server: {self.base_url}")
        else:
            logger.warning(f"⚠️ No beacon received. Using default: {self.base_url}")
            
        return self.base_url

    def set_base_url(self, url: str):
        self.base_url = url.rstrip('/')

    def get_url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint.lstrip('/')}"

# Create global instance
config = AppConfig()
