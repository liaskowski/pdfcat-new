"""
High-performance HTTP connection pooling with retry logic and caching
Optimized for API calls to FastAPI backend
"""

import time
import threading
from typing import Dict, Any, Optional, Tuple
from collections import OrderedDict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hashlib
import json

class ConnectionPool:
    """
    Thread-safe HTTP connection pool with caching and retry logic
    """
    
    def __init__(self, pool_connections: int = 10, pool_maxsize: int = 20,
                 max_retries: int = 3, backoff_factor: float = 0.3,
                 cache_size: int = 100, cache_ttl: int = 300):  # 5 minutes cache TTL
        
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl
        
        # Create session with optimized connection pooling
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        
        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Response cache with LRU eviction
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._cache_lock = threading.RLock()
        
        # Performance statistics
        self._stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'retries': 0,
            'total_time': 0.0,
            'avg_response_time': 0.0
        }
        
        print(f"🔗 ConnectionPool initialized: {pool_connections} connections, {pool_maxsize} pool size")
    
    def _generate_cache_key(self, method: str, url: str, params: Optional[Dict] = None,
                           data: Optional[Dict] = None, json_data: Optional[Dict] = None) -> str:
        """Generate cache key for request"""
        key_parts = [method.upper(), url]
        
        if params:
            # Sort params for consistent key generation
            sorted_params = sorted(params.items())
            key_parts.append(f"params={sorted_params}")
        
        if data:
            key_parts.append(f"data={data}")
        
        if json_data:
            key_parts.append(f"json={json.dumps(sorted(json_data.items()), sort_keys=True)}")
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cached response is still valid"""
        return (time.time() - timestamp) < self.cache_ttl
    
    def _evict_if_needed(self):
        """Evict old cache entries if cache is full"""
        while len(self._cache) >= self.cache_size:
            self._cache.popitem(last=False)  # Remove oldest
    
    def get(self, url: str, params: Optional[Dict] = None, 
            use_cache: bool = True, timeout: float = 30.0, **kwargs) -> requests.Response:
        """GET request with caching and connection pooling"""
        return self._request('GET', url, params=params, use_cache=use_cache, timeout=timeout, **kwargs)
    
    def post(self, url: str, data: Optional[Dict] = None, json: Optional[Dict] = None,
             use_cache: bool = False, timeout: float = 30.0, **kwargs) -> requests.Response:
        """POST request with connection pooling"""
        return self._request('POST', url, data=data, json=json, use_cache=use_cache, timeout=timeout, **kwargs)
    
    def put(self, url: str, data: Optional[Dict] = None, json: Optional[Dict] = None,
            timeout: float = 30.0, **kwargs) -> requests.Response:
        """PUT request with connection pooling"""
        return self._request('PUT', url, data=data, json=json, use_cache=False, timeout=timeout, **kwargs)
    
    def delete(self, url: str, timeout: float = 30.0, **kwargs) -> requests.Response:
        """DELETE request with connection pooling"""
        return self._request('DELETE', url, use_cache=False, timeout=timeout, **kwargs)
    
    def _request(self, method: str, url: str, use_cache: bool = True, **kwargs) -> requests.Response:
        """Core request method with caching and monitoring"""
        start_time = time.time()
        self._stats['total_requests'] += 1
        
        # Check cache for GET requests
        if use_cache and method.upper() == 'GET':
            cache_key = self._generate_cache_key(method, url, kwargs.get('params'), 
                                                 kwargs.get('data'), kwargs.get('json'))
            
            with self._cache_lock:
                if cache_key in self._cache:
                    cached_response, cache_time = self._cache[cache_key]
                    if self._is_cache_valid(cache_time):
                        self._stats['cache_hits'] += 1
                        # Move to end (mark as recently used)
                        self._cache.move_to_end(cache_key)
                        
                        response_time = (time.time() - start_time) * 1000
                        print(f"🎯 Cache hit: {method} {url} ({response_time:.2f}ms)")
                        return cached_response
        
        # Make actual request
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Cache successful GET responses
            if use_cache and method.upper() == 'GET' and response.status_code == 200:
                cache_key = self._generate_cache_key(method, url, kwargs.get('params'), 
                                                     kwargs.get('data'), kwargs.get('json'))
                
                with self._cache_lock:
                    self._evict_if_needed()
                    self._cache[cache_key] = (response, time.time())
            
            self._stats['cache_misses'] += 1
            
        except Exception as e:
            self._stats['retries'] += 1
            raise e
        
        finally:
            # Update statistics
            request_time = time.time() - start_time
            self._stats['total_time'] += request_time
            self._stats['avg_response_time'] = self._stats['total_time'] / self._stats['total_requests']
            
            response_time_ms = request_time * 1000
            if response_time_ms > 1000:  # Slow request warning
                print(f"⚠️  Slow request: {method} {url} ({response_time_ms:.2f}ms)")
            else:
                print(f"🌐 Request: {method} {url} ({response_time_ms:.2f}ms)")
        
        return response
    
    def clear_cache(self):
        """Clear response cache"""
        with self._cache_lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            print(f"🧹 Cleared {cleared_count} cached responses")
    
    def get_stats(self) -> Dict:
        """Get connection pool statistics"""
        cache_hit_rate = 0
        if self._stats['total_requests'] > 0:
            cache_hit_rate = (self._stats['cache_hits'] / self._stats['total_requests']) * 100
        
        return {
            'total_requests': self._stats['total_requests'],
            'cache_hits': self._stats['cache_hits'],
            'cache_misses': self._stats['cache_misses'],
            'cache_hit_rate_percent': cache_hit_rate,
            'retries': self._stats['retries'],
            'avg_response_time_ms': self._stats['avg_response_time'] * 1000,
            'cache_size': len(self._cache),
            'pool_connections': self.pool_connections,
            'pool_maxsize': self.pool_maxsize
        }
    
    def close(self):
        """Close connection pool"""
        self.session.close()
        print("🔗 ConnectionPool closed")

# Global connection pool instance
_connection_pool: Optional[ConnectionPool] = None

def get_connection_pool() -> ConnectionPool:
    """Get global connection pool instance"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPool()
    return _connection_pool

def close_connection_pool():
    """Close global connection pool"""
    global _connection_pool
    if _connection_pool:
        _connection_pool.close()
        _connection_pool = None

# Enhanced API client using connection pool
class OptimizedAPIClient:
    """API client optimized with connection pooling and caching"""
    
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.pool = get_connection_pool()
        
        # Set auth headers
        if token:
            self.pool.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> requests.Response:
        """Optimized GET request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self.pool.get(url, params=params, **kwargs)
    
    def post(self, endpoint: str, data: Optional[Dict] = None, json: Optional[Dict] = None, **kwargs) -> requests.Response:
        """Optimized POST request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self.pool.post(url, data=data, json=json, **kwargs)
    
    def put(self, endpoint: str, data: Optional[Dict] = None, json: Optional[Dict] = None, **kwargs) -> requests.Response:
        """Optimized PUT request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self.pool.put(url, data=data, json=json, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Optimized DELETE request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self.pool.delete(url, **kwargs)
    
    def get_stats(self) -> Dict:
        """Get API client statistics"""
        return self.pool.get_stats()

# Usage example:
# client = OptimizedAPIClient("http://localhost:8000", token="your_token")
# response = client.get("/documents", params={"limit": 50})
# stats = client.get_stats()
