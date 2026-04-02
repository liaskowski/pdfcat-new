import socket
import logging
import time
import requests
import json
from typing import Optional, List, Dict

logger = logging.getLogger("client.api_config")

class AppConfig:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance.base_url = "http://127.0.0.1:8000" # Default Fallback
            cls._instance.last_discovered_servers: List[Dict] = []
        return cls._instance

    def discover_servers(self, timeout: float = 3.0, beacon_port: int = 50010) -> List[Dict]:
        """Active discovery: sends a request and listens for responses/beacons."""
        logger.info(f"🔍 [Discovery] Scanning for servers on UDP {beacon_port}...")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        found_servers = []
        seen_urls = set()

        try:
            # Bind to listen for responses
            sock.bind(('', 0)) # Use any available port for responses
            sock.settimeout(0.5)
            
            # Send active discovery request
            message = b"DISCOVER_PDFLIB"
            sock.sendto(message, ('255.255.255.255', beacon_port))
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(2048)
                    payload = json.loads(data.decode('utf-8'))
                    
                    if payload.get("service") == "pdflib":
                        url = payload.get("url")
                        if url and url not in seen_urls:
                            hostname = payload.get("hostname", "Unknown")
                            logger.info(f"📡 [Discovery] Found server: {hostname} at {url}")
                            seen_urls.add(url)
                            found_servers.append({
                                "name": hostname,
                                "url": url,
                                "ip": addr[0]
                            })
                except socket.timeout:
                    # Periodically re-send discovery request
                    sock.sendto(message, ('255.255.255.255', beacon_port))
                    continue
                except Exception as e:
                    logger.error(f"❌ [Discovery] Receive error: {e}")
                    break
        except Exception as e:
            logger.error(f"❌ [Discovery] Setup error: {e}")
        finally:
            sock.close()
        
        self.last_discovered_servers = found_servers
        return found_servers

    def set_base_url(self, url: str):
        logger.info(f"Config: Setting base_url to {url}")
        self.base_url = url.rstrip('/')

    def get_url(self, endpoint: str) -> str:
        # Note: This is now less preferred than using base_url from API classes
        return f"{self.base_url}/{endpoint.lstrip('/')}"

# Create global instance
config = AppConfig()
