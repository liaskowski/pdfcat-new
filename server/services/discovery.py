import socket
import time
import json
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

class DiscoveryService(threading.Thread):
    def __init__(self, port: int = 8000, broadcast_port: int = 50010):
        super().__init__()
        self.port = port
        self.server_listen_port = broadcast_port # 50010
        self.client_listen_port = broadcast_port + 1 # 50011
        self.daemon = True
        self.running = True
        self._socket: Optional[socket.socket] = None

    def run(self):
        logger.info(f"Starting Discovery Service. Listening on {self.server_listen_port}, Broadcasting to {self.client_listen_port}")
        self._setup_socket()
        
        # Start a listener thread for directed discovery requests
        self.listener_thread = threading.Thread(target=self._listen_for_requests, daemon=True)
        self.listener_thread.start()
        
        while self.running:
            try:
                self._broadcast()
            except Exception as e:
                logger.error(f"Discovery broadcast error: {e}")
                time.sleep(5)
                self._setup_socket()
            
            time.sleep(3)

    def _listen_for_requests(self):
        """Listens for 'DISCOVER_PDFLIB' requests on 50000."""
        listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(('0.0.0.0', self.server_listen_port))
            listener.settimeout(2.0)
            while self.running:
                try:
                    data, addr = listener.recvfrom(1024)
                    if data.decode('utf-8') == "DISCOVER_PDFLIB":
                        self._respond_to(addr, listener)
                except (socket.timeout, UnicodeDecodeError): continue
                except Exception as e:
                    logger.error(f"Discovery listener error: {e}")
                    time.sleep(1)
        finally: listener.close()

    def _respond_to(self, addr, sock):
        payload = {"hostname": socket.gethostname(), "port": self.port, "service": "pdflib", "type": "response"}
        message = json.dumps(payload).encode('utf-8')
        try:
            # Send to client's listening port (50001)
            sock.sendto(message, (addr[0], self.client_listen_port))
        except Exception as e: logger.error(f"Response error: {e}")

    def _setup_socket(self):
        try:
            if self._socket: self._socket.close()
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception as e: logger.error(f"Socket setup failed: {e}")

    def _broadcast(self):
        if not self._socket: return
        payload = {"hostname": socket.gethostname(), "port": self.port, "service": "pdflib"}
        message = json.dumps(payload).encode('utf-8')
        try:
            self._socket.sendto(message, ('255.255.255.255', self.client_listen_port))
        except Exception: pass
