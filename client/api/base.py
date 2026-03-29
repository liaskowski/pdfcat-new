from typing import Optional
import requests
from urllib.parse import urlparse

class APIError(RuntimeError):
    def __init__(self, status_code: int, message: str, response_text: str = "") -> None:
        super().__init__(f"{message} ({status_code}): {response_text}")
        self.status_code = status_code
        self.response_text = response_text

class APIBase:
    def __init__(self, base_url: str, token: Optional[str] = None, timeout_seconds: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout_seconds
        
        # Import hang monitor
        try:
            from ..debug_monitor import start_operation, end_operation
            self._start_operation = start_operation
            self._end_operation = end_operation
        except ImportError:
            self._start_operation = lambda x: None
            self._end_operation = lambda: None
        
        # Connection pooling for better performance
        # Configure for network stability with retry logic
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        self._session = requests.Session()
        if token:
            self._session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Configure retry strategy for network resilience
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
        
        # Enable HTTP keep-alive
        self._session.headers.update({"Connection": "keep-alive"})

    @property
    def token(self) -> Optional[str]:
        return self._token

    def set_token(self, token: Optional[str]) -> None:
        print(f"DEBUG API: Setting token: {bool(token)}")
        print(f"DEBUG API: Token first 20 chars: {token[:20] if token else 'None'}")
        self._token = token
        # Update session headers
        if token:
            self._session.headers.update({"Authorization": f"Bearer {token}"})
            print(f"DEBUG API: Updated session headers with Authorization")
        else:
            self._session.headers.pop("Authorization", None)
            print(f"DEBUG API: Removed Authorization from session headers")
        
        print(f"DEBUG API: Final session headers: {dict(self._session.headers)}")

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def get_resource(self, url: str) -> bytes:
        try:
            parsed_url = urlparse(url)
            parsed_base = urlparse(self.base_url)

            # Send token ONLY if hostnames match AND it's not a static file
            # Static files are mounted at /static and don't need auth
            is_internal = not parsed_url.netloc or parsed_url.netloc == parsed_base.netloc
            is_static = parsed_url.path.startswith("/static/") or parsed_url.path.startswith("/uploads/")
            headers = self._headers() if (is_internal and not is_static) else {}
            
            # Start monitoring
            operation_name = f"GET {parsed_url.path}"
            self._start_operation(operation_name)

            # Use session for connection pooling with retry
            resp = self._session.get(url, headers=headers, timeout=self._timeout)
            if resp.status_code != 200:
                print(f"API Error: Failed to get resource {url}. Status: {resp.status_code}")
                raise APIError(resp.status_code, "Resource not found", resp.text)
            
            # End monitoring
            self._end_operation()
            return resp.content
            
        except Exception as e:
            self._end_operation()
            raise
        
        except requests.exceptions.ConnectionError as e:
            print(f"Network Error: Cannot connect to {url}. Check if server is running and accessible.")
            print(f"Details: {e}")
            raise APIError(0, f"Cannot connect to server at {self.base_url}. Check network connection.", str(e))
        except requests.exceptions.Timeout:
            print(f"Timeout Error: Request to {url} timed out after {self._timeout}s")
            raise APIError(0, "Request timed out. Server may be slow or unreachable.", "")
        except Exception as e:
            if not isinstance(e, APIError):
                print(f"Network Error loading {url}: {e}")
            raise
    
    def check_health(self) -> dict:
        """
        Check server health status.
        Returns health status dict or raises APIError if unhealthy.
        """
        url = f"{self.base_url}/health"
        try:
            resp = self._session.get(url, timeout=5)
            if resp.status_code != 200:
                raise APIError(resp.status_code, "Health check failed", resp.text)
            return resp.json()
        except requests.exceptions.ConnectionError as e:
            raise APIError(0, f"Cannot connect to server at {self.base_url}", str(e))
        except requests.exceptions.Timeout:
            raise APIError(0, f"Health check timed out after 5s", "")

    def is_server_available(self) -> bool:
        """
        Quick check if server is available without raising exceptions.
        Returns True if server is reachable and healthy.
        """
        try:
            health = self.check_health()
            return health.get("status") in ["healthy", "degraded"]
        except Exception:
            return False
    
    def handle_api_error(self, error: APIError) -> bool:
        """
        Handle API errors centrally.
        Returns True if error was handled (e.g., token refreshed).
        Returns False if caller should handle it.
        """
        # Handle 401 Unauthorized - token expired
        if error.status_code == 401:
            print(f"Token expired or invalid. User should re-authenticate.")
            # Don't auto-logout - let the UI handle it
            return False
        
        # Handle 403 Forbidden
        if error.status_code == 403:
            print(f"Access forbidden: {error.response_text}")
            return False
        
        # Other errors - not handled here
        return False

    def close(self):
        """Close the session and release resources"""
        if hasattr(self, '_session'):
            self._session.close()
