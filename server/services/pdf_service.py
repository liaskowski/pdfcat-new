"""
PDF Processing Service integration with Go microservice
Handles PDF text extraction, preview generation, and optimization
"""

import os
import requests
import logging
from typing import Dict, Any, Optional
from ..config import settings

logger = logging.getLogger(__name__)

class PDFService:
    """Service for PDF operations using Go microservice"""
    
    def __init__(self):
        self.pdf_service_url = getattr(settings, 'PDF_SERVICE_URL', 'http://localhost:8002')
        self.timeout = 30  # 30 seconds timeout
    
    def _make_request(self, endpoint: str, data: Dict[str, str]) -> Dict[str, Any]:
        """Make request to PDF processing service"""
        try:
            url = f"{self.pdf_service_url}{endpoint}"
            response = requests.post(url, data=data, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"PDF service error: {response.status_code} - {response.text}")
                return {"error": f"Service error: {response.status_code}"}
                
        except requests.exceptions.Timeout:
            logger.error("PDF service timeout")
            return {"error": "Service timeout"}
        except requests.exceptions.ConnectionError:
            logger.error("PDF service connection error")
            return {"error": "Service unavailable"}
        except Exception as e:
            logger.error(f"PDF service unexpected error: {e}")
            return {"error": f"Unexpected error: {str(e)}"}
    
    def extract_text_async(self, document_id: int) -> Dict[str, Any]:
        """Extract text from PDF asynchronously"""
        data = {"document_id": str(document_id)}
        return self._make_request("/extract", data)
    
    def generate_preview_async(self, document_id: int, page: int = 1, 
                                width: int = 200, height: int = 200) -> Dict[str, Any]:
        """Generate preview asynchronously"""
        data = {
            "document_id": str(document_id),
            "page": str(page),
            "width": str(width),
            "height": str(height)
        }
        return self._make_request("/preview", data)
    
    def optimize_pdf_async(self, document_id: int) -> Dict[str, Any]:
        """Optimize PDF asynchronously"""
        data = {"document_id": str(document_id)}
        return self._make_request("/optimize", data)
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status from PDF service"""
        try:
            url = f"{self.pdf_service_url}/job/{job_id}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Job not found: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return {"error": f"Error: {str(e)}"}
    
    def wait_for_job(self, job_id: str, max_wait_time: int = 60) -> Dict[str, Any]:
        """Wait for job completion with timeout"""
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status = self.get_job_status(job_id)
            
            if "error" in status:
                return status
            
            job_status = status.get("status", "")
            if job_status == "completed":
                return status
            elif job_status == "failed":
                return status
            
            # Wait before checking again
            time.sleep(0.5)
        
        return {"error": "Job timeout"}
    
    def extract_text_sync(self, document_id: int, max_wait_time: int = 60) -> Optional[Dict[str, Any]]:
        """Extract text synchronously (wait for completion)"""
        # Start async job
        job_result = self.extract_text_async(document_id)
        
        if "error" in job_result:
            logger.error(f"Failed to start text extraction: {job_result['error']}")
            return None
        
        job_id = job_result.get("job_id")
        if not job_id:
            logger.error("No job_id returned from PDF service")
            return None
        
        # Wait for completion
        final_status = self.wait_for_job(job_id, max_wait_time)
        
        if final_status.get("status") == "completed":
            return final_status.get("result")
        else:
            logger.error(f"Text extraction failed: {final_status}")
            return None
    
    def is_available(self) -> bool:
        """Check if PDF service is available"""
        try:
            response = requests.get(f"{self.pdf_service_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get PDF service statistics"""
        try:
            response = requests.get(f"{self.pdf_service_url}/stats", timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        return {"error": "Service unavailable"}

# Global PDF service instance
_pdf_service: Optional[PDFService] = None

def get_pdf_service() -> PDFService:
    """Get global PDF service instance"""
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFService()
    return _pdf_service

def extract_text_with_fallback(document_id: int) -> Optional[Dict[str, Any]]:
    """Extract text with fallback to Python if Go service unavailable"""
    pdf_service = get_pdf_service()
    
    # Try Go service first
    if pdf_service.is_available():
        logger.info(f"Using Go PDF service for document {document_id}")
        result = pdf_service.extract_text_sync(document_id)
        if result:
            return result
        else:
            logger.warning(f"Go PDF service failed for document {document_id}, falling back to Python")
    
    # Fallback to Python implementation
    logger.info(f"Using Python PDF extraction for document {document_id}")
    return _extract_text_python_fallback(document_id)

def _extract_text_python_fallback(document_id: int) -> Optional[Dict[str, Any]]:
    """Python fallback for PDF text extraction"""
    try:
        # Import here to avoid circular imports
        from ..routers.documents import get_document_content
        from ..database import SessionLocal
        
        db = SessionLocal()
        try:
            content = get_document_content(document_id, db)
            if content:
                return {
                    "text": content,
                    "pages": 1,  # Would need to count pages properly
                    "metadata": {
                        "title": f"Document {document_id}",
                        "author": "Unknown"
                    }
                }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Python PDF extraction fallback failed: {e}")
    
    return None
