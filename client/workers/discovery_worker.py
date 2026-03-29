import socket
import json
from PyQt6.QtCore import QThread, pyqtSignal

class DiscoveryWorker(QThread):
    server_found = pyqtSignal(str, str, int)  # ip, hostname, port

    def __init__(self, port: int = 50000):
        super().__init__()
        self.server_port = port # 50000 (where server listens)
        self.client_port = port + 1 # 50001 (where we listen)
        self.running = True
        self._socket = None

    def run(self):
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # Bind to 50001 to receive server broadcasts and responses
            self._socket.bind(('0.0.0.0', self.client_port))
            self._socket.settimeout(1.0)
            
            # Initial active scan
            self.scan()
            
            while self.running:
                try:
                    data, addr = self._socket.recvfrom(1024)
                    message = json.loads(data.decode('utf-8'))
                    
                    if message.get("service") == "pdflib":
                        ip = addr[0]
                        hostname = message.get("hostname", "Unknown")
                        port = message.get("port", 8000)
                        self.server_found.emit(ip, hostname, port)
                except (socket.timeout, json.JSONDecodeError): continue
                except Exception:
                    if self.running: pass
                    
        except Exception as e:
            if self.running: print(f"Discovery worker error: {e}")
        finally:
            if self._socket: self._socket.close()

    def scan(self):
        """Sends active request to server port (50000)."""
        temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            temp_sock.sendto(b"DISCOVER_PDFLIB", ('255.255.255.255', self.server_port))
        except Exception as e:
            print(f"Scan error: {e}")
        finally:
            temp_sock.close()

    def stop(self):
        self.running = False
        self.wait()
