import socket
import logging
import time
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener

logger = logging.getLogger(__name__)

class PDFLibDiscoveryListener(ServiceListener):
    def __init__(self):
        self.found_server = None

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            if addresses:
                self.found_server = f"http://{addresses[0]}:{info.port}"
                logger.info(f"🌐 Found PDFLib server via Zeroconf: {self.found_server}")

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

    def discover_server(self, timeout: float = 2.0):
        """Try to discover the server in the local network using Zeroconf"""
        logger.info("🔍 Searching for PDFLib server in local network...")
        zeroconf = Zeroconf()
        listener = PDFLibDiscoveryListener()
        browser = ServiceBrowser(zeroconf, "_pdflib._tcp.local.", listener)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if listener.found_server:
                self.base_url = listener.found_server
                break
            time.sleep(0.1)
        
        zeroconf.close()
        if not listener.found_server:
            logger.warning(f"⚠️ Server discovery timed out. Using default: {self.base_url}")
        return self.base_url

    def set_base_url(self, url: str):
        # Remove trailing slash if present
        self.base_url = url.rstrip('/')

    def get_url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint.lstrip('/')}"

# Create global instance
config = AppConfig()
