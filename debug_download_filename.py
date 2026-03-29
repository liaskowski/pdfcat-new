#!/usr/bin/env python3
"""
Test download with proper filename from title field
"""

import requests
import os

def test_download_filename():
    """Test download endpoint with title-based filename"""
    
    print("📥 Testing Download Filename")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    # Login first
    login_data = {"username": "admin", "password": "admin"}
    response = requests.post(f"{base_url}/auth/token", data=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print("✅ Login successful")
    
    # Use test document ID 260 directly
    test_doc_id = 260
    
    # Get document details
    response = requests.get(f"{base_url}/documents/{test_doc_id}", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to get document {test_doc_id}: {response.status_code}")
        return
    
    test_doc = response.json()
    print(f"📄 Testing document: ID={test_doc['id']}, Title='{test_doc['title']}', Filename='{test_doc.get('filename', 'N/A')}'")
    
    # Download the document
    response = requests.get(f"{base_url}/documents/{test_doc['id']}/download", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Download failed: {response.status_code}")
        print(f"Error: {response.text}")
        return
    
    # Check Content-Disposition header
    content_disp = response.headers.get('content-disposition', '')
    print(f"📋 Content-Disposition: {content_disp}")
    
    # Extract filename from header
    if 'filename=' in content_disp:
        import re
        match = re.search(r'filename="([^"]+)"', content_disp)
        if match:
            filename = match.group(1)
            print(f"✅ Extracted filename: {filename}")
            
            # Save file to verify
            with open(f"downloaded_{filename}", 'wb') as f:
                f.write(response.content)
            
            print(f"💾 Saved as: downloaded_{filename}")
            print(f"📊 File size: {len(response.content)} bytes")
            
            # Check if filename matches title
            expected_filename = f"{test_doc['title']}.pdf"
            if filename == expected_filename:
                print(f"✅ Filename matches title: {expected_filename}")
            else:
                print(f"⚠️ Filename mismatch. Expected: {expected_filename}, Got: {filename}")
        else:
            print("❌ Could not extract filename from header")
    else:
        print("❌ No filename found in Content-Disposition header")
    
    # Check for PDF status
    pdf_status = response.headers.get('x-pdf-status', '')
    if pdf_status:
        print(f"🔐 PDF Status: {pdf_status}")
    
    print("\n🏁 Download test complete!")

if __name__ == "__main__":
    test_download_filename()
