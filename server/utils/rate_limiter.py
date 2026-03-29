"""
Rate limiting middleware for FastAPI.
Prevents server overload during bulk operations.
"""

import time
import logging
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window algorithm.
    Tracks requests per client IP.
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = {}
    
    def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        """
        Check if request is allowed for the given IP.
        Returns (is_allowed, retry_after_seconds).
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        if client_ip in self._requests:
            self._requests[client_ip] = [
                ts for ts in self._requests[client_ip]
                if ts > window_start
            ]
        else:
            self._requests[client_ip] = []
        
        # Check limit
        if len(self._requests[client_ip]) >= self.max_requests:
            retry_after = int(self._requests[client_ip][0] + self.window_seconds - now)
            return False, max(1, retry_after)
        
        # Record request
        self._requests[client_ip].append(now)
        return True, 0
    
    def cleanup(self):
        """Remove old entries to prevent memory leak."""
        now = time.time()
        window_start = now - self.window_seconds
        
        for ip in list(self._requests.keys()):
            self._requests[ip] = [ts for ts in self._requests[ip] if ts > window_start]
            if not self._requests[ip]:
                del self._requests[ip]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to apply rate limiting to API requests.
    Exempts health check, static files, and document operations.
    """
    
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.limiter = RateLimiter(max_requests, window_seconds)
        # Exempt paths that shouldn't be rate limited
        self.exempt_paths = [
            "/health", "/docs", "/redoc", "/openapi.json", "/static",
            "/documents/", "/search", "/folders/", "/categories/", "/file_types/"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check if path is exempt
        path = request.url.path
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            return await call_next(request)
        
        # Check rate limit
        allowed, retry_after = self.limiter.is_allowed(client_ip)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for IP: {client_ip} on {path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.limiter.max_requests)
        response.headers["X-RateLimit-Window"] = str(self.limiter.window_seconds)
        
        return response


# Bulk upload specific rate limiter
class BulkUploadLimiter:
    """
    Specialized rate limiter for bulk upload operations.
    Limits concurrent uploads and total upload size.
    """
    
    def __init__(self, max_concurrent_uploads: int = 5, max_total_size_mb: int = 500):
        self.max_concurrent = max_concurrent_uploads
        self.max_total_size = max_total_size_mb * 1024 * 1024
        self._current_uploads = 0
        self._current_size = 0
        self._lock = None  # Will be asyncio.Lock when used
        
    async def acquire(self, file_size: int) -> bool:
        """Try to acquire a slot for upload. Returns True if successful."""
        import asyncio
        
        if self._lock is None:
            self._lock = asyncio.Lock()
        
        async with self._lock:
            if self._current_uploads >= self.max_concurrent:
                return False
            
            if self._current_size + file_size > self.max_total_size:
                return False
            
            self._current_uploads += 1
            self._current_size += file_size
            return True
    
    def release(self, file_size: int):
        """Release an upload slot."""
        self._current_uploads -= 1
        self._current_size -= file_size


# Global instances
_upload_limiter = None

def get_upload_limiter() -> BulkUploadLimiter:
    """Get or create the global upload limiter."""
    global _upload_limiter
    if _upload_limiter is None:
        _upload_limiter = BulkUploadLimiter(max_concurrent_uploads=5)
    return _upload_limiter
