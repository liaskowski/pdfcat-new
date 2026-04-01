import socket
import logging
import time
import requests
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener

logger = logging.getLogger(__name__)

class PDFLibDiscoveryListener(ServiceListener):
    def __init__(self):
        self.found_servers = []

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            for addr in addresses:
                url = f"http://{addr}:{info.port}"
                if url not in self.found_servers:
                    self.found_servers.append(url)
                    logger.info(f"🌐 Discovered potential PDFLib server: {url}")

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

class AppConfig:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance.base_url = "http://127.0.0.1:8000" # Default fallback
            cls._instance.discover_server()
        return cls._instance

    def discover_server(self, timeout: float = 5.0):
        """Try to discover the server in the local network using Zeroconf"""
        logger.info(f"🔍 Searching for PDFLib server in local network (timeout {timeout}s)...")
        zeroconf = Zeroconf()
        listener = PDFLibDiscoveryListener()
        browser = ServiceBrowser(zeroconf, "_pdflib._tcp.local.", listener)
        
        start_time = time.time()
        verified_server = None
        
        while time.time() - start_time < timeout:
            # Check if we have any servers to verify
            if listener.found_servers:
                # Try to verify each found server
                for url in list(listener.found_servers):
                    try:
                        logger.info(f"⏳ Verifying server at {url}...")
                        resp = requests.get(f"{url}/health", timeout=1.0)
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("status") == "healthy":
                                verified_server = url
                                logger.info(f"✅ Verified PDFLib server found at {url}")
                                break
                    except Exception:
                        continue
            
            if verified_server:
                break
                
            time.sleep(0.5)
        
        zeroconf.close()
        
        if verified_server:
            self.base_url = verified_server
        else:
            logger.warning(f"⚠️ Server discovery failed or timed out. Using default: {self.base_url}")
            
        return self.base_url

    def set_base_url(self, url: str):
        # Remove trailing slash if present
        self.base_url = url.rstrip('/')

    def get_url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint.lstrip('/')}"

# Create global instance
config = AppConfig()
