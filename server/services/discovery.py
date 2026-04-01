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
        self.service_name = f"PDFLib-{socket.gethostname()}.__pdflib._tcp.local."

    def _get_all_local_ips(self) -> List[str]:
        """Get all non-loopback IPv4 addresses."""
        ips = []
        try:
            hostname = socket.gethostname()
            logger.info(f"Checking IPs for hostname: {hostname}")
            
            # 1. Try gethostbyname_ex
            try:
                for ip in socket.gethostbyname_ex(hostname)[2]:
                    if not ip.startswith("127."):
                        ips.append(ip)
            except Exception as e:
                logger.debug(f"gethostbyname_ex failed: {e}")
            
            # 2. Try main gateway IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 1))
                main_ip = s.getsockname()[0]
                if main_ip not in ips and not main_ip.startswith("127."):
                    ips.append(main_ip)
            except Exception as e:
                logger.debug(f"Gateway IP detection failed: {e}")
            finally:
                s.close()
        except Exception as e:
            logger.error(f"General IP discovery error: {e}")
            
        final_ips = list(set(ips))
        logger.info(f"Detected local IPs: {final_ips}")
        return final_ips if final_ips else ["127.0.0.1"]

    def start(self):
        """Register the service in the local network"""
        try:
            logger.info("Starting Zeroconf instance...")
            self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            
            local_ips = self._get_all_local_ips()
            hostname = socket.gethostname()
            
            # We pack all IPs into the ServiceInfo
            addresses = [socket.inet_aton(ip) for ip in local_ips]

            desc = {'path': '/', 'hostname': hostname}
            
            self.service_info = ServiceInfo(
                "_pdflib._tcp.local.",
                self.service_name,
                addresses=addresses,
                port=self.port,
                properties=desc,
                server=f"{hostname}.local.",
            )

            logger.info(f"🚀 Registering Zeroconf service: {self.service_name} at {local_ips}:{self.port}")
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
