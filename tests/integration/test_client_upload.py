#!/usr/bin/env python3
"""
Test client upload functionality
"""

import sys
import os
from pathlib import Path

# Add project root to path
BASE_DIR = str(Path(__file__).resolve().parent)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def test_client_upload():
    """Test client upload using API"""
    
    print("🖥️ Testing Client Upload")
    print("=" * 40)
    
    try:
        from client.api_manager import APIManager
        from client.api.documents import DocumentsAPI
        print("✅ Client imports successful")
    except Exception as e:
        print(f"❌ Client import failed: {e}")
        return
    
    # Initialize API
    api = APIManager(base_url="http://localhost:8000")
    
    # Login
    try:
        api.login("admin", "admin")
        print("✅ Login successful")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return
    
    # Get documents API
    docs_api = DocumentsAPI(base_url="http://localhost:8000", token=api.token)
    
    # Create a test PDF file
    test_file_path = Path(BASE_DIR) / "test_upload.pdf"
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000054 00000 n\n0000000109 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
    
    with open(test_file_path, 'wb') as f:
        f.write(pdf_content)
    
    print(f"📄 Created test file: {test_file_path}")
    
    # Test upload without folder_id
    try:
        print("\n📤 Test 1: Upload without folder_id")
        doc = docs_api.upload_file(
            file_path=str(test_file_path),
            title="Client Test No Folder",
            category_id=None,
            file_type_id=None,
            folder_id=None,
            is_private=False,
            is_public=False,
            is_public_edit=False,
            is_read_only=False,
            encryption_key=None,
            notes="",
            tags=None,
            use_ocr=False
        )
        print(f"✅ Upload successful: ID={doc.id}, Title='{doc.title}'")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
    
    # Test upload with folder_id=0
    try:
        print("\n📤 Test 2: Upload with folder_id=0")
        doc = docs_api.upload_file(
            file_path=str(test_file_path),
            title="Client Test Folder 0",
            category_id=None,
            file_type_id=None,
            folder_id=0,
            is_private=False,
            is_public=False,
            is_public_edit=False,
            is_read_only=False,
            encryption_key=None,
            notes="",
            tags=None,
            use_ocr=False
        )
        print(f"✅ Upload successful: ID={doc.id}, Title='{doc.title}'")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
    
    # Test upload with valid folder_id
    try:
        print("\n📤 Test 3: Upload with folder_id=1")
        doc = docs_api.upload_file(
            file_path=str(test_file_path),
            title="Client Test Folder 1",
            category_id=None,
            file_type_id=None,
            folder_id=1,
            is_private=False,
            is_public=False,
            is_public_edit=False,
            is_read_only=False,
            encryption_key=None,
            notes="",
            tags=None,
            use_ocr=False
        )
        print(f"✅ Upload successful: ID={doc.id}, Title='{doc.title}'")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
    
    # Clean up test file
    try:
        test_file_path.unlink()
        print(f"\n🧹 Cleaned up test file")
    except:
        pass
    
    print("\n🏁 Client upload test complete!")

if __name__ == "__main__":
    test_client_upload()
