import socket
import json
import time
from PyQt6.QtCore import QThread, pyqtSignal
from ..utils.logger import get_logger

logger = get_logger("client.discovery")

class DiscoveryWorker(QThread):
    server_found = pyqtSignal(str, str, int)  # ip, hostname, port

    def __init__(self, port: int = 50010):
        super().__init__()
        self.discovery_port = port # Consistent with server beacon_port
        self.running = True
        self._socket = None

    def run(self):
        logger.info(f"Starting network discovery on UDP {self.discovery_port}...")
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # Bind to receive both beacons and responses
            try:
                self._socket.bind(('0.0.0.0', self.discovery_port))
            except Exception as e:
                logger.error(f"Failed to bind to discovery port {self.discovery_port}: {e}")
                # Try to continue without binding? No, we need to bind to receive broadcasts.
                # On Windows, multiple apps can bind to same UDP port if SO_REUSEADDR is set.
                return

            self._socket.settimeout(1.0)
            
            # Initial active scan
            self.scan()
            
            last_scan_time = time.time()
            
            while self.running:
                try:
                    data, addr = self._socket.recvfrom(2048)
                    try:
                        message = json.loads(data.decode('utf-8'))
                    except json.JSONDecodeError:
                        continue # Not our message
                        
                    if message.get("service") == "pdflib":
                        ip = addr[0]
                        hostname = message.get("hostname", "Unknown")
                        # Try to get URL and extract IP from it if possible, 
                        # but addr[0] is usually more reliable for local network
                        url = message.get("url", "")
                        port = message.get("port", 8000)
                        
                        logger.debug(f"Found server: {hostname} at {ip}:{port} (via {message.get('type', 'unknown')})")
                        self.server_found.emit(ip, hostname, port)
                        
                except socket.timeout:
                    # Periodically re-scan if running
                    if time.time() - last_scan_time > 10.0:
                        self.scan()
                        last_scan_time = time.time()
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Discovery receiver error: {e}")
                    
        except Exception as e:
            if self.running: 
                logger.error(f"Discovery worker critical error: {e}")
        finally:
            if self._socket: 
                self._socket.close()
                logger.info("Discovery worker stopped.")

    def scan(self):
        """Sends active broadcast request to discover servers."""
        logger.debug("Performing active network scan...")
        temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            message = b"DISCOVER_PDFLIB"
            # Send to generic broadcast
            temp_sock.sendto(message, ('255.255.255.255', self.discovery_port))
            # Also try to send to all local subnet broadcasts if we can find them
            # (Handled by sending to 255.255.255.255 usually, but some routers are picky)
        except Exception as e:
            logger.error(f"Scan broadcast error: {e}")
        finally:
            temp_sock.close()

    def stop(self):
        self.running = False
        # No need for wait() if it's called from UI thread and we want to be responsive,
        # but QThread.wait() is safer for cleanup.
        self.wait(1000)
