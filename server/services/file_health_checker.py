#!/usr/bin/env python3
"""
File Health Checker Service
Analyzes PDF files for corruption, encryption, and other issues
"""

import os
import fitz  # PyMuPDF
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class FileHealthStatus:
    """File health status constants"""
    HEALTHY = "healthy"
    ENCRYPTED = "encrypted"
    CORRUPTED = "corrupted"
    UNREADABLE = "unreadable"
    PARTIAL = "partial"

class FileHealthChecker:
    """Service for checking PDF file health"""
    
    def __init__(self):
        self.common_passwords = [
            "", "admin", "password", "document", "file", 
            "123456", "qwerty", "test", "pdf", "1234"
        ]
    
    def check_file_health(self, file_path: str) -> Dict:
        """
        Check the health of a PDF file
        
        Returns:
            Dict with health information:
            - status: FileHealthStatus
            - is_readable: bool
            - is_encrypted: bool
            - page_count: int
            - file_size: int
            - issues: List[str]
            - recommendations: List[str]
            - can_decrypt: bool
        """
        result = {
            "status": FileHealthStatus.HEALTHY,
            "is_readable": False,
            "is_encrypted": False,
            "page_count": 0,
            "file_size": 0,
            "issues": [],
            "recommendations": [],
            "can_decrypt": False
        }
        
        # Check file existence
        if not os.path.exists(file_path):
            result["status"] = FileHealthStatus.UNREADABLE
            result["issues"].append("File does not exist")
            result["recommendations"].append("Delete this document record")
            return result
        
        # Get file size
        try:
            result["file_size"] = os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Error getting file size: {e}")
            result["file_size"] = 0
        
        # Try to open with PyMuPDF
        try:
            doc = fitz.open(file_path)
            
            # Check if encrypted
            result["is_encrypted"] = doc.is_encrypted
            
            if doc.is_encrypted:
                result["status"] = FileHealthStatus.ENCRYPTED
                result["issues"].append("PDF is encrypted with unknown password")
                
                # Try common passwords
                for password in self.common_passwords:
                    try:
                        if doc.authenticate(password):
                            result["can_decrypt"] = True
                            result["status"] = FileHealthStatus.HEALTHY
                            result["issues"].clear()
                            result["recommendations"].append(f"Consider removing password protection")
                            break
                    except:
                        continue
                
                if not result["can_decrypt"]:
                    result["recommendations"].extend([
                        "This file cannot be read or indexed",
                        "Consider deleting this document",
                        "Or obtain the correct password and re-upload"
                    ])
            
            # Get page count
            try:
                result["page_count"] = doc.page_count
                if result["page_count"] == 0:
                    result["status"] = FileHealthStatus.CORRUPTED
                    result["issues"].append("PDF has 0 pages - likely corrupted")
                    result["recommendations"].append("Delete this corrupted document")
            except:
                result["page_count"] = 0
                result["status"] = FileHealthStatus.CORRUPTED
                result["issues"].append("Cannot read page count - file may be corrupted")
                result["recommendations"].append("Delete this corrupted document")
            
            # Check for content extraction
            if result["page_count"] > 0 and (not doc.is_encrypted or result["can_decrypt"]):
                try:
                    # Try to extract some text from first page
                    page = doc[0]
                    text = page.get_text()
                    if len(text.strip()) < 10:
                        result["status"] = FileHealthStatus.PARTIAL
                        result["issues"].append("PDF appears to have little or no readable text")
                        result["recommendations"].append("This may be an image-only PDF")
                except Exception as e:
                    logger.warning(f"Could not extract text: {e}")
                    result["status"] = FileHealthStatus.PARTIAL
                    result["issues"].append("Cannot extract text from PDF")
                    result["recommendations"].append("PDF may contain only images")
            
            # Mark as readable if we got this far
            result["is_readable"] = True
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error opening PDF {file_path}: {e}")
            result["status"] = FileHealthStatus.CORRUPTED
            result["is_readable"] = False
            result["issues"].append(f"Cannot open PDF: {str(e)}")
            result["recommendations"].append("Delete this corrupted document")
        
        return result
    
    def get_health_summary(self, file_path: str) -> str:
        """Get a human-readable health summary"""
        health = self.check_file_health(file_path)
        
        if health["status"] == FileHealthStatus.HEALTHY:
            if health["is_encrypted"] and health["can_decrypt"]:
                return "✅ File is readable (encrypted but accessible)"
            else:
                return "✅ File is healthy and readable"
        
        elif health["status"] == FileHealthStatus.ENCRYPTED:
            return "🔒 File is encrypted - cannot be read"
        
        elif health["status"] == FileHealthStatus.CORRUPTED:
            return "❌ File is corrupted - cannot be read"
        
        elif health["status"] == FileHealthStatus.UNREADABLE:
            return "❌ File is unreadable - may be deleted"
        
        elif health["status"] == FileHealthStatus.PARTIAL:
            return "⚠️ File is partially readable"
        
        return "❓ Unknown file status"
    
    def should_suggest_deletion(self, file_path: str) -> Tuple[bool, str]:
        """
        Determine if file should be suggested for deletion
        
        Returns:
            Tuple[bool, str]: (should_delete, reason)
        """
        health = self.check_file_health(file_path)
        
        if health["status"] in [FileHealthStatus.CORRUPTED, FileHealthStatus.UNREADABLE]:
            return True, "File is corrupted or unreadable and cannot be used"
        
        if health["status"] == FileHealthStatus.ENCRYPTED and not health["can_decrypt"]:
            return True, "File is encrypted with unknown password and cannot be read"
        
        return False, ""
    
    def batch_check_directory(self, directory: str) -> List[Dict]:
        """Check all PDF files in a directory"""
        results = []
        
        try:
            for file_path in Path(directory).glob("*.pdf"):
                health = self.check_file_health(str(file_path))
                health["filename"] = file_path.name
                health["file_path"] = str(file_path)
                results.append(health)
        except Exception as e:
            logger.error(f"Error checking directory {directory}: {e}")
        
        return results
