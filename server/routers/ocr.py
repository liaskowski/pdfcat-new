from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional
import shutil
import tempfile
import os
from ..services.ocr_service import extract_text
from ..dependencies import get_current_user

router = APIRouter(
    prefix="/ocr",
    tags=["ocr"],
    responses={404: {"description": "Not found"}},
)

@router.post("/recognize")
async def recognize_document(
    file: UploadFile = File(...),
    lang: str = Form("rus+eng"),
    current_user: dict = Depends(get_current_user)
):
    # Save uploaded file to temp
    suffix = os.path.splitext(file.filename)[1]
    fd, temp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        text = extract_text(temp_path, lang)
        return {"text": text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
