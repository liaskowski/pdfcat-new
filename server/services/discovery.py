import socket
import logging
import threading
import time
import json

logger = logging.getLogger(__name__)

class DiscoveryService:
    """Ultra-reliable UDP Beacon that broadcasts on all interfaces"""
    
    def __init__(self, port: int = 8000, beacon_port: int = 50010):
        self.port = port
        self.beacon_port = beacon_port
        self.running = False
        self.thread = None
        self.hostname = socket.gethostname()

    def _get_all_broadcast_ips(self):
        """Get all potential broadcast addresses from local interfaces"""
        broadcasts = ['<broadcast>', '255.255.255.255']
        try:
            # Try to get more specific broadcasts from hostname
            ips = socket.gethostbyname_ex(self.hostname)[2]
            for ip in ips:
                if not ip.startswith('127.'):
                    parts = ip.split('.')
                    if len(parts) == 4:
                        # Add subnet broadcast (e.g., 192.168.1.255)
                        broadcasts.append(f"{parts[0]}.{parts[1]}.{parts[2]}.255")
        except Exception:
            pass
        return list(set(broadcasts))

    def _get_all_local_ips(self):
        """Get all non-loopback IPv4 addresses."""
        ips = []
        try:
            for ip in socket.gethostbyname_ex(self.hostname)[2]:
                if not ip.startswith("127."):
                    ips.append(ip)
            
            # Plus gateway IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 1))
                main_ip = s.getsockname()[0]
                if main_ip not in ips and not main_ip.startswith("127."):
                    ips.append(main_ip)
            finally:
                s.close()
        except Exception: pass
        return list(set(ips))

    def start(self):
        """Start the background beacon thread"""
        self.running = True
        self.thread = threading.Thread(target=self._beacon_loop, daemon=True)
        self.thread.start()
        logger.info(f"🚀 Multi-Interface UDP Beacon started on port {self.beacon_port}")

    def _beacon_loop(self):
        """Periodically broadcast server location on all interfaces"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(1.0)
        
        while self.running:
            try:
                ips = self._get_all_local_ips()
                broadcast_targets = self._get_all_broadcast_ips()
                
                for ip in ips:
                    payload = {
                        "service": "pdflib",
                        "hostname": self.hostname,
                        "url": f"http://{ip}:{self.port}",
                        "timestamp": time.time()
                    }
                    message = json.dumps(payload).encode('utf-8')
                    
                    # Send to each broadcast target
                    for target in broadcast_targets:
                        try:
                            sock.sendto(message, (target, self.beacon_port))
                        except Exception: continue
                
            except Exception as e:
                logger.error(f"Beacon loop error: {e}")
            
            time.sleep(2.0)
        
        sock.close()

    def stop(self):
        """Stop the beacon"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        logger.info("UDP Beacon stopped.")
