import socket
import logging
import threading
import time
import json

logger = logging.getLogger(__name__)

class DiscoveryService:
    """Ultra-reliable UDP Beacon for LAN Discovery"""
    
    def __init__(self, port: int = 8000, beacon_port: int = 50010):
        self.port = port
        self.beacon_port = beacon_port
        self.running = False
        self.thread = None
        self.hostname = socket.gethostname()

    def _get_best_local_ip(self) -> str:
        """Identify primary LAN IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 1))
                return s.getsockname()[0]
            finally:
                s.close()
        except Exception:
            return "127.0.0.1"

    def start(self):
        """Start the background beacon thread"""
        self.running = True
        self.thread = threading.Thread(target=self._beacon_loop, daemon=True)
        self.thread.start()
        logger.info(f"🚀 Reliable UDP Beacon started on port {self.beacon_port}")

    def _beacon_loop(self):
        """Periodically broadcast server location"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        while self.running:
            try:
                ip = self._get_best_local_ip()
                payload = {
                    "service": "pdflib",
                    "hostname": self.hostname,
                    "url": f"http://{ip}:{self.port}",
                    "timestamp": time.time()
                }
                message = json.dumps(payload).encode('utf-8')
                
                # Broadcast to the subnet
                sock.sendto(message, ('<broadcast>', self.beacon_port))
                
            except Exception as e:
                logger.error(f"Beacon error: {e}")
            
            time.sleep(2.0)
        
        sock.close()

    def stop(self):
        """Stop the beacon"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        logger.info("UDP Beacon stopped.")
