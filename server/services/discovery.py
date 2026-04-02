import socket
import logging
import threading
import time
import json
import os

logger = logging.getLogger(__name__)

class DiscoveryService:
    """Ultra-reliable UDP Beacon that broadcasts and responds to discovery requests"""
    
    def __init__(self, port: int = 8000, beacon_port: int = 50010):
        self.port = port
        self.beacon_port = beacon_port
        self.running = False
        self.threads = []
        self.hostname = socket.gethostname()
        self.service_name = "pdflib"

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
            # Method 1: hostname lookup
            for ip in socket.gethostbyname_ex(self.hostname)[2]:
                if not ip.startswith("127."):
                    ips.append(ip)
            
            # Method 2: Connection to external IP (best for identifying main interface)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Doesn't actually connect, just picks local IP that would be used
                s.connect(('8.8.8.8', 1))
                main_ip = s.getsockname()[0]
                if main_ip not in ips and not main_ip.startswith("127."):
                    ips.append(main_ip)
            finally:
                s.close()
        except Exception as e: 
            logger.debug(f"IP discovery error: {e}")
        
        if not ips:
            ips = ["127.0.0.1"] # Fallback
        return list(set(ips))

    def start(self):
        """Start the background discovery threads"""
        if self.running:
            return
            
        self.running = True
        
        # Thread 1: Periodic Beacon (Broadcaster)
        beacon_thread = threading.Thread(target=self._beacon_loop, name="DiscoveryBeacon", daemon=True)
        beacon_thread.start()
        self.threads.append(beacon_thread)
        
        # Thread 2: Discovery Listener (Responder)
        listener_thread = threading.Thread(target=self._listener_loop, name="DiscoveryListener", daemon=True)
        listener_thread.start()
        self.threads.append(listener_thread)
        
        logger.info(f"🚀 Discovery Service started on UDP {self.beacon_port} (Responding to 'DISCOVER_{self.service_name.upper()}')")
        logger.info(f"📍 Broadcasting server at port {self.port}")

    def _get_payload(self, ip):
        return {
            "service": self.service_name,
            "hostname": self.hostname,
            "url": f"http://{ip}:{self.port}",
            "port": self.port,
            "timestamp": time.time(),
            "type": "beacon"
        }

    def _beacon_loop(self):
        """Periodically broadcast server location on all interfaces"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        while self.running:
            try:
                ips = self._get_all_local_ips()
                broadcast_targets = self._get_all_broadcast_ips()
                
                for ip in ips:
                    payload = self._get_payload(ip)
                    message = json.dumps(payload).encode('utf-8')
                    
                    for target in broadcast_targets:
                        try:
                            sock.sendto(message, (target, self.beacon_port))
                        except Exception: continue
                
            except Exception as e:
                logger.error(f"Discovery Beacon error: {e}")
            
            time.sleep(5.0) # Send every 5 seconds
        
        sock.close()

    def _listener_loop(self):
        """Listen for active discovery requests and respond immediately"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Bind to all interfaces on the discovery port
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.beacon_port))
            sock.settimeout(1.0)
            
            logger.info(f"📡 Listening for discovery requests on port {self.beacon_port}...")
            
            search_pattern = f"DISCOVER_{self.service_name.upper()}".encode('utf-8')
            
            while self.running:
                try:
                    data, addr = sock.recvfrom(1024)
                    if data == search_pattern:
                        logger.info(f"🔍 Discovery request from {addr[0]}")
                        
                        # Respond with all local IPs to ensure one of them works
                        ips = self._get_all_local_ips()
                        for ip in ips:
                            payload = self._get_payload(ip)
                            payload["type"] = "response"
                            response = json.dumps(payload).encode('utf-8')
                            sock.sendto(response, addr)
                            
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Discovery Listener error: {e}")
        finally:
            sock.close()

    def stop(self):
        """Stop the discovery service"""
        self.running = False
        for t in self.threads:
            t.join(timeout=1.0)
        self.threads = []
        logger.info("UDP Discovery Service stopped.")
