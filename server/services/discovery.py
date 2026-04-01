import socket
import logging
from zeroconf import IPVersion, ServiceInfo, Zeroconf
from typing import Optional

logger = logging.getLogger(__name__)

class DiscoveryService:
    """Zeroconf/mDNS Discovery Service for PDFLib"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.zeroconf: Optional[Zeroconf] = None
        self.service_info: Optional[ServiceInfo] = None
        self.service_name = f"PDFLib-{socket.gethostname()}.__pdflib._tcp.local."

    def start(self):
        """Register the service in the local network"""
        try:
            self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            
            # Get local IP address
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            # Try to find a more reliable local IP if 127.0.0.1 is returned
            if local_ip == "127.0.0.1":
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    # doesn't even have to be reachable
                    s.connect(('8.8.8.8', 1))
                    local_ip = s.getsockname()[0]
                except Exception:
                    pass
                finally:
                    s.close()

            desc = {'path': '/'}
            
            self.service_info = ServiceInfo(
                "_pdflib._tcp.local.",
                self.service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties=desc,
                server=f"{hostname}.local.",
            )

            logger.info(f"🚀 Registering Zeroconf service: {self.service_name} at {local_ip}:{self.port}")
            self.zeroconf.register_service(self.service_info)
            
        except Exception as e:
            logger.error(f"❌ Failed to start Zeroconf discovery: {e}")

    def stop(self):
        """Unregister the service"""
        if self.zeroconf and self.service_info:
            logger.info("Stopping Zeroconf discovery...")
            self.zeroconf.unregister_service(self.service_info)
            self.zeroconf.close()
            self.zeroconf = None
            self.service_info = None
