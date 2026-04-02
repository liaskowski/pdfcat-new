import socket
import logging
import platform
import subprocess
from typing import List, Dict, Any

logger = logging.getLogger("client.network_check")

def get_local_interfaces() -> List[Dict[str, Any]]:
    """Returns a list of local network interfaces with their IPs."""
    interfaces = []
    try:
        hostname = socket.gethostname()
        ips = socket.gethostbyname_ex(hostname)[2]
        for ip in ips:
            if not ip.startswith("127."):
                interfaces.append({"name": hostname, "ip": ip})
    except Exception as e:
        logger.error(f"Error getting local interfaces: {e}")
    
    # Try another way for more detail
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        main_ip = s.getsockname()[0]
        s.close()
        if not any(i["ip"] == main_ip for i in interfaces):
            interfaces.append({"name": "Primary", "ip": main_ip})
    except Exception:
        pass
        
    return interfaces

def check_udp_port_available(port: int) -> bool:
    """Checks if a UDP port is available for binding."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', port))
        sock.close()
        return True
    except Exception as e:
        logger.warning(f"UDP port {port} check failed: {e}")
        return False

def check_firewall_rules() -> Dict[str, Any]:
    """
    Checks if firewall rules for pdfCAT exist (Windows specific).
    Returns a dict with status of rules.
    """
    if platform.system() != "Windows":
        return {"status": "unknown", "message": "Firewall check only implemented for Windows"}
    
    rules_to_check = ["PDFLib_Server", "PDFLib_Beacon"]
    results = {}
    
    try:
        # Use netsh to list rules
        output = subprocess.check_output(
            ["netsh", "advfirewall", "firewall", "show", "rule", "name=all"],
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding='cp866' # Windows encoding
        )
        
        for rule in rules_to_check:
            results[rule] = rule in output
            
    except Exception as e:
        logger.error(f"Firewall check failed: {e}")
        return {"status": "error", "message": str(e)}
        
    all_ok = all(results.values())
    return {
        "status": "ok" if all_ok else "warning",
        "rules": results,
        "message": "All firewall rules present" if all_ok else "Some firewall rules are missing"
    }

def perform_full_network_check() -> Dict[str, Any]:
    """Performs a comprehensive check of network capability."""
    discovery_port = 50010
    
    interfaces = get_local_interfaces()
    udp_ok = check_udp_port_available(discovery_port)
    firewall = check_firewall_rules()
    
    return {
        "interfaces": interfaces,
        "udp_discovery_port_ok": udp_ok,
        "firewall": firewall,
        "can_discover": udp_ok and len(interfaces) > 0,
        "is_connected_to_network": len(interfaces) > 0
    }
