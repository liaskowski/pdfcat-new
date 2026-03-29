"""
Updated configuration for Go microservices
Clean service URLs and environment variables
"""

import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Updated settings with clean Go microservice URLs"""
    
    # Database Settings
    DATABASE_URL: Optional[str] = None  # e.g., "postgresql://user:pass@localhost:5432/db"
    
    # Go Microservices Settings
    SEARCH_SERVICE_URL: str = "http://localhost:8001"
    PDF_SERVICE_URL: str = "http://localhost:8002" 
    THUMBNAIL_SERVICE_URL: str = "http://localhost:8003"
    OCR_SERVICE_URL: str = "http://localhost:8004"
    UPLOAD_SERVICE_URL: str = "http://localhost:8005"
    WEBSOCKET_SERVICE_URL: str = "http://localhost:8006"
    
    # Legacy compatibility
    SEARCH_GO_URL: Optional[str] = None  # Deprecated, use SEARCH_SERVICE_URL
    
    # Task Settings
    TASK_MODE: str = "LOCAL"  # LOCAL (Thread-based) or SERVER (Dramatiq/Redis)
    REDIS_URL: Optional[str] = None  # e.g., "redis://localhost:6379/0"
    
    # File Settings
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # Security Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Performance Settings
    ENABLE_CACHING: bool = True
    CACHE_TTL: int = 300  # 5 minutes
    
    class Config:
        env_file = ".env"

settings = Settings()

# Backward compatibility
if settings.SEARCH_GO_URL and not settings.SEARCH_SERVICE_URL.startswith("http"):
    settings.SEARCH_SERVICE_URL = settings.SEARCH_GO_URL

# Default to local SQLite if no DATABASE_URL is provided
if not settings.DATABASE_URL:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    settings.DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"

# Auto-detect mode if REDIS_URL is provided in .env
if settings.REDIS_URL:
    settings.TASK_MODE = "SERVER"

# Create upload directory
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Service availability check
def check_service_availability() -> dict:
    """Check which Go microservices are available"""
    import requests
    
    services = {
        "search": settings.SEARCH_SERVICE_URL,
        "pdf": settings.PDF_SERVICE_URL,
        "thumbnail": settings.THUMBNAIL_SERVICE_URL,
        "ocr": settings.OCR_SERVICE_URL,
        "upload": settings.UPLOAD_SERVICE_URL,
        "websocket": settings.WEBSOCKET_SERVICE_URL,
    }
    
    availability = {}
    
    for service_name, url in services.items():
        try:
            response = requests.get(f"{url}/health", timeout=2)
            availability[service_name] = response.status_code == 200
        except:
            availability[service_name] = False
    
    return availability

def get_service_status_summary() -> str:
    """Get human-readable service status"""
    availability = check_service_availability()
    
    total_services = len(availability)
    available_services = sum(availability.values())
    
    status = f"Services: {available_services}/{total_services} available\n"
    
    for service_name, is_available in availability.items():
        icon = "✅" if is_available else "❌"
        status += f"{icon} {service_name.title()}\n"
    
    return status.strip()

# Export settings for backward compatibility
SEARCH_GO_URL = settings.SEARCH_SERVICE_URL  # Legacy compatibility
