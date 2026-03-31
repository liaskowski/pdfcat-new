#!/usr/bin/env python3
"""
Test client download functionality
"""

import sys
import os
from pathlib import Path

# Add project root to path
BASE_DIR = str(Path(__file__).resolve().parent)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def test_client_download():
    """Test client download using API"""
    
    print("🖥️ Testing Client Download")
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
    
    # Try to get document 260
    try:
        doc = docs_api.get_document(260)
        print(f"✅ Got document: ID={doc.id}, Title='{doc.title}'")
    except Exception as e:
        print(f"❌ Failed to get document: {e}")
        return
    
    # Test download
    try:
        print("📥 Testing download...")
        
        # This would normally download the file
        # For testing, we'll just check the download URL
        download_url = f"http://localhost:8000/documents/{doc.id}/download"
        
        import requests
        response = requests.get(download_url, headers={"Authorization": f"Bearer {docs_api._token}"})
        
        if response.status_code == 200:
            content_disp = response.headers.get('content-disposition', '')
            print(f"📋 Content-Disposition: {content_disp}")
            
            if 'filename=' in content_disp:
                import re
                match = re.search(r'filename="([^"]+)"', content_disp)
                if match:
                    filename = match.group(1)
                    print(f"✅ Download filename: {filename}")
                    
                    expected = f"{doc.title}.pdf"
                    if filename == expected:
                        print(f"✅ Filename matches title!")
                    else:
                        print(f"⚠️ Filename mismatch. Expected: {expected}, Got: {filename}")
            else:
                print("❌ No filename in Content-Disposition")
        else:
            print(f"❌ Download failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Download error: {e}")
    
    print("\n🏁 Client download test complete!")

if __name__ == "__main__":
    test_client_download()
