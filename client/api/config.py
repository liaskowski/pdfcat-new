import socket
import logging
import time
import requests
import json
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

    def discover_server(self, timeout: float = 5.0, beacon_port: int = 50010):
        """Listen for UDP beacons from the server with high reliability"""
        logger.info(f"🔍 [Discovery] Listening for beacons on port {beacon_port}...")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            # Bind to all interfaces to listen for broadcast
            sock.bind(('', beacon_port))
        except Exception as e:
            logger.error(f"❌ [Discovery] Could not bind to beacon port: {e}")
            return self.base_url

        sock.settimeout(1.0)
        start_time = time.time()
        found_url = None
        potential_urls = set()

        logger.info(f"⏳ [Discovery] Scanning network for up to {timeout}s...")

        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(2048)
                payload = json.loads(data.decode('utf-8'))
                
                if payload.get("service") == "pdflib":
                    url = payload.get("url")
                    if url not in potential_urls:
                        logger.info(f"📡 [Discovery] Potential server at {url} (from {addr[0]})")
                        potential_urls.add(url)
                        
                        # Immediately try to verify
                        try:
                            logger.info(f"⏳ [Discovery] Verifying {url}...")
                            resp = requests.get(f"{url}/health", timeout=1.5)
                            if resp.status_code == 200:
                                found_url = url
                                break
                        except Exception as e:
                            logger.debug(f"⚠️ [Discovery] Verification failed for {url}: {e}")
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"❌ [Discovery] Listen error: {e}")
                break
        
        sock.close()
        
        if found_url:
            self.base_url = found_url
            logger.info(f"🚀 [Discovery] CONNECTED TO: {self.base_url}")
        else:
            if potential_urls:
                logger.warning(f"⚠️ [Discovery] Found potential servers {potential_urls} but none responded to health checks.")
            else:
                logger.warning(f"⚠️ [Discovery] No beacons received at all. Firewall may be blocking port {beacon_port} UDP.")
            
        return self.base_url

    def set_base_url(self, url: str):
        self.base_url = url.rstrip('/')

    def get_url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint.lstrip('/')}"

# Create global instance
config = AppConfig()
