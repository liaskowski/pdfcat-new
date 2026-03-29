#!/usr/bin/env python3
"""
Debug server startup to find where it hangs
"""

import os
import sys
import logging
import time

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

print("🔍 Debug: Starting server startup analysis...")

# Test imports step by step
try:
    print("1. Importing FastAPI...")
    from fastapi import FastAPI
    print("✅ FastAPI imported")
except Exception as e:
    print(f"❌ FastAPI import failed: {e}")
    sys.exit(1)

try:
    print("2. Importing database...")
    from server.database import engine, Base, SessionLocal
    print("✅ Database imported")
except Exception as e:
    print(f"❌ Database import failed: {e}")
    sys.exit(1)

try:
    print("3. Importing models...")
    from server.models import User
    print("✅ Models imported")
except Exception as e:
    print(f"❌ Models import failed: {e}")
    sys.exit(1)

try:
    print("4. Importing security...")
    from server.security import get_password_hash
    print("✅ Security imported")
except Exception as e:
    print(f"❌ Security import failed: {e}")
    sys.exit(1)

try:
    print("5. Importing tesseract config...")
    from server.utils.tesseract_config import setup_tesseract
    print("✅ Tesseract config imported")
except Exception as e:
    print(f"❌ Tesseract config import failed: {e}")
    sys.exit(1)

try:
    print("6. Importing discovery service...")
    from server.services.discovery import DiscoveryService
    print("✅ Discovery service imported")
except Exception as e:
    print(f"❌ Discovery service import failed: {e}")
    sys.exit(1)

try:
    print("7. Importing routers...")
    from server.routers import auth, users, documents, folders, admin, ocr
    print("✅ Routers imported")
except Exception as e:
    print(f"❌ Routers import failed: {e}")
    sys.exit(1)

try:
    print("8. Importing context manager...")
    from contextlib import asynccontextmanager
    print("✅ Context manager imported")
except Exception as e:
    print(f"❌ Context manager import failed: {e}")
    sys.exit(1)

print("9. Creating FastAPI app...")
app = FastAPI(title="pdfCAT Debug Server")

print("10. Adding routers...")
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(documents.router)
app.include_router(folders.router)
app.include_router(admin.router)
app.include_router(ocr.router)
print("✅ Routers added")

print("11. Testing basic app creation...")
try:
    @app.get("/")
    async def root():
        return {"message": "Debug server is running"}
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    print("✅ Basic routes added")
except Exception as e:
    print(f"❌ Basic routes failed: {e}")
    sys.exit(1)

print("12. Testing without discovery service...")
try:
    import uvicorn
    print("✅ Uvicorn imported")
    print("13. Starting minimal server...")
    
    # Start without discovery service
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
    
except Exception as e:
    print(f"❌ Server start failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
