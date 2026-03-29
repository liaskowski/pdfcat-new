#!/usr/bin/env python3
"""
Test simple UI without full client
"""

import sys
from pathlib import Path

# Add project root to path
BASE_DIR = str(Path(__file__).resolve().parent)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def test_simple_upload():
    """Test upload using only API, no UI"""
    
    print("🖥️ Testing Simple Upload (No UI)")
    print("=" * 40)
    
    try:
        from client.api_manager import APIManager
        from client.api.documents import DocumentsAPI
        print("✅ API imports successful")
    except Exception as e:
        print(f"❌ API import failed: {e}")
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
    
    # Test upload with folder_id=None (simulating UI form)
    try:
        print("\n📤 Testing upload like UI would do...")
        
        # Create test file
        test_file_path = Path(BASE_DIR) / "simple_test.pdf"
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000054 00000 n\n0000000109 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
        
        with open(test_file_path, 'wb') as f:
            f.write(pdf_content)
        
        # Simulate UI form data
        form_data = {
            "title": "Simple UI Test",
            "category_id": None,
            "file_type_id": None,
            "is_private": False,
            "is_public": False,
            "is_public_edit": False,
            "is_read_only": False,
            "notes": "",
            "tags": "",
            "use_ocr": False,
            "folder_id": None  # This is what was missing!
        }
        
        print(f"📋 Form data: {form_data}")
        
        doc = docs_api.upload_file(
            file_path=str(test_file_path),
            title=form_data["title"],
            category_id=form_data["category_id"],
            file_type_id=form_data["file_type_id"],
            folder_id=form_data["folder_id"],
            is_private=form_data["is_private"],
            is_public=form_data["is_public"],
            is_public_edit=form_data["is_public_edit"],
            is_read_only=form_data["is_read_only"],
            encryption_key=None,
            notes=form_data["notes"],
            tags=form_data["tags"],
            use_ocr=form_data["use_ocr"]
        )
        
        print(f"✅ Upload successful: ID={doc.id}, Title='{doc.title}'")
        
        # Clean up
        test_file_path.unlink()
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🏁 Simple upload test complete!")

if __name__ == "__main__":
    test_simple_upload()
