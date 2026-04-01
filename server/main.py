import os
import sys
import socket

# Настройка путей для портативности: корень проекта и локальные библиотеки
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# LOCAL_SITE_PACKAGES = os.path.join(BASE_DIR, "vendor", "python", "Lib", "site-packages")

# if LOCAL_SITE_PACKAGES not in sys.path:
#     sys.path.insert(0, LOCAL_SITE_PACKAGES)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Принудительная установка TESSDATA_PREFIX для портативности
tessdata_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "bin", "tesseract", "tessdata"))
os.environ["TESSDATA_PREFIX"] = tessdata_path

import logging
import fitz

# Подавляем синтаксические ошибки MuPDF (не влияют на работу, но шумят в логах)
fitz.TOOLS.mupdf_display_errors(False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.database import engine, Base, SessionLocal
from server.models import User
from server.security import get_password_hash
from server.utils.tesseract_config import setup_tesseract
from server.services.discovery import DiscoveryService
from server.routers import auth, users, documents, folders, admin, ocr, file_health, assets
from contextlib import asynccontextmanager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_port_in_use(host: str, port: int) -> bool:
    """Check if a port is already in use on the specified host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            result = s.connect_ex((host, port))
            return result == 0
        except socket.error:
            return False


def check_existing_server_process(host: str, port: int) -> bool:
    """
    Check if server is already running by:
    1. Checking if port is in use
    2. Making a health check request to the existing server
    
    Returns True if server is already running and responsive.
    """
    if not is_port_in_use(host, port):
        return False
    
    # Port is in use, check if it's our server
    try:
        import requests
        # Try to hit a known endpoint to verify it's our server
        response = requests.get(f"http://{host}:{port}/docs", timeout=2)
        # If we get any response, server is running
        return response.status_code in [200, 401, 403]  # 401/403 means auth required = our server
    except Exception:
        # Port is in use but not responding to HTTP - might be a zombie process
        logger.warning(f"Port {port} is in use but not responding. Another process may be using it.")
        return True

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    try:
        # Startup logic
        setup_tesseract()
        Base.metadata.create_all(bind=engine)

        # Initialize PDF processing queue with concurrency control
        from server.services.pdf_processor import init_pdf_processor
        init_pdf_processor(max_workers=2)  # Limit to 2 concurrent PDF processing tasks

        # Start Discovery Service (mDNS/Zeroconf)
        port_raw = os.environ.get("PDFLIB_PORT", os.environ.get("PORT", "8000"))
        try:
            service_port = int(port_raw)
        except Exception:
            service_port = 8000

        discovery = DiscoveryService(port=service_port)
        discovery.start()
        app.state.discovery = discovery

        # Init Admin
        db = SessionLocal()
        try:
            if db.query(User).count() == 0:
                admin_user = User(
                    username="admin",
                    email="admin@example.com",
                    hashed_password=get_password_hash("admin"),
                    role="admin",
                    is_active=True
                )
                db.add(admin_user)
                db.commit()
                print("Admin credentials verified/created: admin/admin")
            else:
                # Check if admin exists and verify default password
                admin_found = db.query(User).filter(User.username == "admin").first()
                if admin_found:
                    from server.security import verify_password
                    if verify_password("admin", admin_found.hashed_password):
                        print("\n" + "!"*60)
                        print("SECURITY WARNING: Default admin password 'admin' is in use!")
                        print("Please change it immediately in the admin panel.")
                        print("!"*60 + "\n")
        except Exception as e:
            logger.error(f"Admin initialization error: {e}")
        finally:
            db.close()
        
        logger.info("Server startup complete")

    except Exception as e:
        logger.critical(f"Server startup failed: {e}", exc_info=True)
        raise

    yield

    # Shutdown logic
    logger.info("Shutting down server...")
    try:
        from server.services.pdf_processor import process_pdf_async
        # Cancel any pending PDF processing tasks
        logger.info("Cleaning up PDF processing queue...")
    except Exception as e:
        logger.debug(f"Cleanup info: {e}")
    # Stop discovery service
    if hasattr(app.state, "discovery"):
        app.state.discovery.stop()
    
    logger.info("Cleanup complete.")

app.mount("/static", StaticFiles(directory="server/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware (after CORS, before routers)
from server.utils.rate_limiter import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for server monitoring."""
    import time
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/")
async def root():
    """Root endpoint - serve HTML page or JSON"""
    from fastapi.responses import FileResponse
    from fastapi import Request
    
    # For browser requests, serve HTML page
    index_path = os.path.join(BASE_DIR, "assets", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    
    # Fallback to JSON for API clients
    return {
        "message": "pdfCAT - PDF Library Management System",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "api": "/api",
            "health": "/health",
            "favicon": "/favicon.ico",
            "logo": "/assets/logo"
        }
    }

@app.get("/favicon.ico")
async def favicon():
    """Serve favicon"""
    from fastapi.responses import FileResponse
    favicon_path = os.path.join(BASE_DIR, "assets", "icons", "pdfCat.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    return {"message": "Favicon not found"}

# Подключение роутеров
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(documents.router)
app.include_router(folders.router)
app.include_router(admin.router)
app.include_router(ocr.router)
app.include_router(file_health.router)
app.include_router(assets.router)

if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("PDFLIB_HOST", "0.0.0.0")
    port_raw = os.environ.get("PDFLIB_PORT", os.environ.get("PORT", "8000"))
    try:
        port = int(port_raw)
    except Exception:
        port = 8000

    # Check if server is already running
    check_host = "127.0.0.1" if host == "0.0.0.0" else host
    if check_existing_server_process(check_host, port):
        print("\n" + "="*60)
        print(f"WARNING: Server is already running on port {port}!")
        print("If you want to run multiple instances, use different ports.")
        print("Existing server should be accessible at:")
        print(f"  - http://{check_host}:{port}")
        print("="*60 + "\n")
        # Continue anyway - allow multiple instances if user explicitly starts them
    else:
        print("\n" + "="*60)
        print(f"Server starting on port {port}...")
        print("Available Local IP Addresses:")
        try:
            hostname = socket.gethostname()
            local_ips = socket.gethostbyname_ex(hostname)[2]
            for ip in local_ips:
                print(f"  - http://{ip}:{port}")
        except Exception as e:
            print(f"  (Could not resolve local IPs: {e})")
        print("="*60 + "\n")

    uvicorn.run(app, host=host, port=port)
