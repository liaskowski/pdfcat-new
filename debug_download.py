#!/usr/bin/env python3
"""
Debug script to test document download endpoint
"""

import requests
import sqlite3
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

def test_direct_download():
    """Test download endpoint directly"""
    print("🔍 Testing direct document download...")
    
    try:
        # Test without auth first
        response = requests.get("http://localhost:8000/documents/250/download", timeout=5)
        print(f"❌ No auth - Status: {response.status_code}")
        if response.status_code == 401:
            print("✅ Authentication required (expected)")
        else:
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Direct request failed: {e}")
    
    try:
        # Test with basic auth (admin:admin)
        response = requests.get(
            "http://localhost:8000/documents/250/download",
            auth=("admin", "admin"),
            timeout=10
        )
        print(f"🔐 With auth - Status: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Download successful! Size: {len(response.content)} bytes")
            # Save to test file
            with open("debug_download_test.pdf", "wb") as f:
                f.write(response.content)
            print("💾 Saved as debug_download_test.pdf")
        else:
            print(f"❌ Download failed: {response.text[:300]}")
    except Exception as e:
        print(f"❌ Auth request failed: {e}")

def test_database():
    """Test database connection and document info"""
    print("\n🗄️ Testing database...")
    
    try:
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        
        # Check document
        cursor.execute('SELECT id, filename, file_path, owner_id, is_public FROM documents WHERE id = 250')
        doc = cursor.fetchone()
        if doc:
            print(f"✅ Document found: {doc}")
        else:
            print("❌ Document 250 not found")
            return
        
        # Check user
        cursor.execute('SELECT id, username, role FROM users WHERE id = ?', (doc[3],))
        user = cursor.fetchone()
        if user:
            print(f"✅ Owner found: {user}")
        else:
            print("❌ Owner not found")
        
        conn.close()
    except Exception as e:
        print(f"❌ Database error: {e}")

def test_file_access():
    """Test physical file access"""
    print("\n📁 Testing file access...")
    
    file_path = "uploads/20260317_202821_tmppp8sfhdr.pdf"
    
    if os.path.exists(file_path):
        print(f"✅ File exists: {file_path}")
        size = os.path.getsize(file_path)
        print(f"📊 File size: {size:,} bytes")
        
        # Test PyMuPDF
        try:
            import fitz
            doc = fitz.open(file_path)
            print(f"✅ PyMuPDF: {doc.page_count} pages")
            doc.close()
        except Exception as e:
            print(f"❌ PyMuPDF error: {e}")
    else:
        print(f"❌ File not found: {file_path}")

def test_server_status():
    """Test server endpoints"""
    print("\n🌐 Testing server status...")
    
    endpoints = [
        "/",
        "/docs",
        "/health",
        "/auth/login"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"http://localhost:8000{endpoint}", timeout=3)
            print(f"✅ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")

def main():
    print("🐛 pdfCAT Download Debug Tool")
    print("=" * 40)
    
    # Test server status first
    test_server_status()
    
    # Test database
    test_database()
    
    # Test file access
    test_file_access()
    
    # Test download endpoint
    test_direct_download()
    
    print("\n🏁 Debug complete!")

if __name__ == "__main__":
    main()
