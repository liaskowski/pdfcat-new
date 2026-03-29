#!/usr/bin/env python3
"""
File Health Router
Endpoints for checking and managing file health
"""

import os
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict
import logging

from server.database import get_db
from server.models import User, Document
from server.services.file_health_checker import FileHealthChecker, FileHealthStatus
from server.dependencies import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/file-health", tags=["file-health"])

# Global file health checker instance
health_checker = FileHealthChecker()

@router.get("/check/{document_id}")
async def check_document_health(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Check health of a specific document"""
    
    # Get document
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check access
    if doc.owner_id != current_user.id and not current_user.role == "admin":
        if not (doc.is_public or doc.is_public_edit):
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Check file health
    try:
        health = health_checker.check_file_health(doc.file_path)
        health["document_id"] = document_id
        health["filename"] = doc.filename
        health["health_summary"] = health_checker.get_health_summary(doc.file_path)
        
        should_delete, delete_reason = health_checker.should_suggest_deletion(doc.file_path)
        health["should_suggest_deletion"] = should_delete
        health["delete_reason"] = delete_reason
        
        return health
    except Exception as e:
        logger.error(f"Error checking file health: {e}")
        raise HTTPException(status_code=500, detail="Failed to check file health")

@router.get("/check-all")
async def check_all_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Check health of all accessible documents"""
    
    # Get documents accessible to user
    if current_user.role == "admin":
        documents = db.query(Document).all()
    else:
        documents = db.query(Document).filter(
            (Document.owner_id == current_user.id) |
            (Document.is_public == True) |
            (Document.is_public_edit == True)
        ).all()
    
    results = []
    problematic_files = []
    
    for doc in documents:
        try:
            health = health_checker.check_file_health(doc.file_path)
            health["document_id"] = doc.id
            health["filename"] = doc.filename
            health["health_summary"] = health_checker.get_health_summary(doc.file_path)
            
            should_delete, delete_reason = health_checker.should_suggest_deletion(doc.file_path)
            health["should_suggest_deletion"] = should_delete
            health["delete_reason"] = delete_reason
            
            results.append(health)
            
            if should_delete:
                problematic_files.append({
                    "document_id": doc.id,
                    "filename": doc.filename,
                    "reason": delete_reason,
                    "status": health["status"]
                })
            
        except Exception as e:
            logger.error(f"Error checking document {doc.id}: {e}")
            results.append({
                "document_id": doc.id,
                "filename": doc.filename,
                "error": str(e),
                "status": "error"
            })
    
    return {
        "total_documents": len(documents),
        "healthy_files": len([r for r in results if r.get("status") == FileHealthStatus.HEALTHY]),
        "problematic_files": len(problematic_files),
        "results": results,
        "problematic_files_detail": problematic_files
    }

@router.post("/suggest-cleanup")
async def suggest_cleanup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get cleanup suggestions for problematic files"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all documents
    documents = db.query(Document).all()
    
    cleanup_suggestions = []
    
    for doc in documents:
        should_delete, delete_reason = health_checker.should_suggest_deletion(doc.file_path)
        
        if should_delete:
            cleanup_suggestions.append({
                "document_id": doc.id,
                "filename": doc.filename,
                "file_path": doc.file_path,
                "file_size_mb": round(os.path.getsize(doc.file_path) / (1024*1024), 2) if os.path.exists(doc.file_path) else 0,
                "reason": delete_reason,
                "owner_id": doc.owner_id,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            })
    
    # Sort by file size (largest first)
    cleanup_suggestions.sort(key=lambda x: x["file_size_mb"], reverse=True)
    
    total_size_to_free = sum(item["file_size_mb"] for item in cleanup_suggestions)
    
    return {
        "files_to_delete": len(cleanup_suggestions),
        "total_size_to_free_mb": round(total_size_to_free, 2),
        "suggestions": cleanup_suggestions
    }

@router.delete("/cleanup/{document_id}")
async def cleanup_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a problematic document"""
    
    # Get document
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check permissions
    if doc.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if file is problematic
    should_delete, delete_reason = health_checker.should_suggest_deletion(doc.file_path)
    
    if not should_delete:
        raise HTTPException(
            status_code=400, 
            detail="File is not marked as problematic. Use regular delete endpoint."
        )
    
    try:
        # Delete physical file
        import os
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
            logger.info(f"Deleted problematic file: {doc.file_path}")
        
        # Delete database record
        db.delete(doc)
        db.commit()
        
        return {
            "message": f"Document '{doc.filename}' deleted successfully",
            "reason": delete_reason,
            "document_id": document_id
        }
        
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete document")
