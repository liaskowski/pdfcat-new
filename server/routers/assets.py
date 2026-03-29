#!/usr/bin/env python3
"""
Assets Router
Serves static assets like images and icons
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import os

router = APIRouter(prefix="/assets", tags=["assets"])

# Define asset paths
ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
ICONS_DIR = ASSETS_DIR / "icons"

@router.get("/images/{image_name}")
async def get_image(image_name: str):
    """Serve image files"""
    image_path = IMAGES_DIR / image_name
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Determine media type based on file extension
    media_type = "image/jpeg"
    if image_name.lower().endswith('.png'):
        media_type = "image/png"
    elif image_name.lower().endswith('.gif'):
        media_type = "image/gif"
    elif image_name.lower().endswith('.svg'):
        media_type = "image/svg+xml"
    
    return FileResponse(
        path=image_path,
        media_type=media_type,
        filename=image_name
    )

@router.get("/icons/{icon_name}")
async def get_icon(icon_name: str):
    """Serve icon files"""
    icon_path = ICONS_DIR / icon_name
    
    if not icon_path.exists():
        raise HTTPException(status_code=404, detail="Icon not found")
    
    # Determine media type based on file extension
    media_type = "image/x-icon"
    if icon_name.lower().endswith('.png'):
        media_type = "image/png"
    elif icon_name.lower().endswith('.jpg') or icon_name.lower().endswith('.jpeg'):
        media_type = "image/jpeg"
    
    return FileResponse(
        path=icon_path,
        media_type=media_type,
        filename=icon_name
    )

@router.get("/logo")
async def get_logo():
    """Serve the main logo"""
    logo_path = IMAGES_DIR / "pdfCat.jpg"
    
    if not logo_path.exists():
        raise HTTPException(status_code=404, detail="Logo not found")
    
    return FileResponse(
        path=logo_path,
        media_type="image/jpeg",
        filename="pdfCat.jpg"
    )

@router.get("/favicon.ico")
async def get_favicon():
    """Serve favicon for web interface"""
    favicon_path = ICONS_DIR / "pdfCat.ico"
    
    if not favicon_path.exists():
        raise HTTPException(status_code=404, detail="Favicon not found")
    
    return FileResponse(
        path=favicon_path,
        media_type="image/x-icon",
        filename="favicon.ico"
    )
