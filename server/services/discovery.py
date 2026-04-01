import socket
import logging
from zeroconf import IPVersion, ServiceInfo, Zeroconf
from typing import Optional, List

logger = logging.getLogger(__name__)

class DiscoveryService:
    """Zeroconf/mDNS Discovery Service for PDFLib"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.zeroconf: Optional[Zeroconf] = None
        self.service_info: Optional[ServiceInfo] = None
        # Sanitize hostname for mDNS (replace _ with -)
        hostname = socket.gethostname()
        self.clean_hostname = hostname.replace("_", "-")
        self.type = "_pdflib._tcp.local."
        self.service_name = f"PDFLib-{self.clean_hostname}.{self.type}"

    def _get_best_local_ip(self) -> str:
        """Identify the most likely primary LAN IP address."""
        try:
            # Try to connect to an external IP to see which local interface is used
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # doesn't even have to be reachable
                s.connect(('8.8.8.8', 1))
                primary_ip = s.getsockname()[0]
                if not primary_ip.startswith("127.") and not primary_ip.startswith("192.168.56."):
                    logger.info(f"🎯 Identified primary IP via gateway: {primary_ip}")
                    return primary_ip
            finally:
                s.close()
        except Exception as e:
            logger.debug(f"Gateway IP detection failed: {e}")

        # Fallback to general lookup
        try:
            hostname = socket.gethostname()
            ips = socket.gethostbyname_ex(hostname)[2]
            # Exclude loopback and VirtualBox
            valid_ips = [ip for ip in ips if not ip.startswith("127.") and not ip.startswith("192.168.56.")]
            if valid_ips:
                logger.info(f"📋 Found valid IPs via hostname: {valid_ips}")
                return valid_ips[0]
        except Exception:
            pass

        return "127.0.0.1"

    def start(self):
        """Register the service in the local network"""
        try:
            best_ip = self._get_best_local_ip()
            
            if best_ip == "127.0.0.1":
                logger.warning("⚠️ Only loopback IP found. Discovery might not work across LAN.")

            logger.info(f"Starting Zeroconf instance on primary interface: {best_ip}...")
            
            # Using a single stable interface avoids EventLoopBlocked on Windows
            self.zeroconf = Zeroconf(interfaces=[best_ip], ip_version=IPVersion.V4Only)
            
            # Pack the IP into ServiceInfo
            addresses = [socket.inet_aton(best_ip)]

            desc = {'path': '/', 'hostname': self.clean_hostname}
            
            self.service_info = ServiceInfo(
                self.type,
                self.service_name,
                addresses=addresses,
                port=self.port,
                properties=desc,
                server=f"{self.clean_hostname}.local.",
            )

            logger.info(f"🚀 Registering Zeroconf service: {self.service_name} at {best_ip}:{self.port}")
            self.zeroconf.register_service(self.service_info)
            
        except Exception as e:
            logger.error(f"❌ Failed to start Zeroconf discovery: {e}", exc_info=True)

    def stop(self):
        """Unregister the service"""
        if self.zeroconf and self.service_info:
            logger.info("Stopping Zeroconf discovery...")
            try:
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
            except Exception:
                pass
            self.zeroconf = None
            self.service_info = None
