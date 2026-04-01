import socket
import logging
import time
import requests
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener, IPVersion
from typing import List, Optional

logger = logging.getLogger(__name__)

class PDFLibDiscoveryListener(ServiceListener):
    def __init__(self):
        self.found_servers = []

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            for addr in addresses:
                url = f"http={addr}:{info.port}"
                url = url.replace("http=", "http://") # Avoid string literal issues
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

    def _get_all_local_ips(self) -> List[str]:
        """Get all non-loopback IPv4 addresses."""
        ips = []
        try:
            hostname = socket.gethostname()
            # 1. Try gethostbyname_ex
            try:
                for ip in socket.gethostbyname_ex(hostname)[2]:
                    if not ip.startswith("127."):
                        ips.append(ip)
            except Exception: pass
            
            # 2. Try main gateway IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 1))
                main_ip = s.getsockname()[0]
                if main_ip not in ips and not main_ip.startswith("127."):
                    ips.append(main_ip)
            except Exception: pass
            finally: s.close()
        except Exception: pass
        return list(set(ips)) if ips else ["127.0.0.1"]

    def discover_server(self, timeout: float = 5.0):
        """Try to discover the server in the local network using Zeroconf"""
        logger.info(f"🔍 Searching for PDFLib server in local network (timeout {timeout}s)...")
        
        local_ips = self._get_all_local_ips()
        # Filter for real LAN IPs to avoid virtual adapter issues (WSL, Docker, etc)
        filtered_ips = [ip for ip in local_ips if ip.startswith(("192.168.", "10.", "172.16.", "172.31."))]
        if not filtered_ips: filtered_ips = local_ips
        
        try:
            # Explicitly passing interfaces avoids EventLoopBlocked on Windows
            # and ensures we look on the right networks
            zeroconf = Zeroconf(interfaces=filtered_ips, ip_version=IPVersion.V4Only)
            listener = PDFLibDiscoveryListener()
            browser = ServiceBrowser(zeroconf, "_pdflib._tcp.local.", listener)
            
            start_time = time.time()
            verified_server = None
            
            while time.time() - start_time < timeout:
                if listener.found_servers:
                    # Try to verify discovered servers
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
                logger.info(f"🚀 Successfully connected to: {self.base_url}")
            else:
                logger.warning(f"⚠️ Server discovery failed or timed out. Using default: {self.base_url}")
                
        except Exception as e:
            logger.error(f"❌ Zeroconf client initialization error: {e}")
            
        return self.base_url

    def set_base_url(self, url: str):
        # Remove trailing slash if present
        self.base_url = url.rstrip('/')

    def get_url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint.lstrip('/')}"

# Create global instance
config = AppConfig()
