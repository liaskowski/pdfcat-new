#!/usr/bin/env python3
"""
Debug upload endpoint to understand folder_id issue
"""

import requests
import json

def debug_upload():
    """Test upload with different folder_id values"""
    
    print("🔍 Debug Upload Endpoint")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    # Login first
    login_data = {"username": "admin", "password": "admin"}
    response = requests.post(f"{base_url}/auth/token", data=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print("✅ Login successful")
    
    # Test 1: Upload without folder_id
    print("\n📤 Test 1: Upload without folder_id")
    
    # Create a dummy PDF file
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000054 00000 n\n0000000109 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
    
    files = {
        'file': ('test.pdf', pdf_content, 'application/pdf')
    }
    
    data = {
        'title': 'Test Document No Folder',
        'category_id': '',
        'file_type_id': '',
        'folder_id': '',
        'is_private': 'false',
        'is_public': 'false',
        'is_public_edit': 'false',
        'is_read_only': 'false',
        'encryption_key': '',
        'notes': '',
        'tags': '',
        'use_ocr': 'true'
    }
    
    response = requests.post(f"{base_url}/documents/upload", files=files, data=data, headers=headers)
    
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: {response.text}")
    else:
        print("✅ Upload successful without folder_id")
    
    # Test 2: Upload with folder_id=0
    print("\n📤 Test 2: Upload with folder_id=0")
    
    data['folder_id'] = '0'
    data['title'] = 'Test Document Folder 0'
    
    response = requests.post(f"{base_url}/documents/upload", files=files, data=data, headers=headers)
    
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: {response.text}")
    else:
        print("✅ Upload successful with folder_id=0")
    
    # Test 3: Upload with folder_id=None
    print("\n📤 Test 3: Upload with folder_id=None")
    
    data['folder_id'] = 'None'
    data['title'] = 'Test Document Folder None'
    
    response = requests.post(f"{base_url}/documents/upload", files=files, data=data, headers=headers)
    
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: {response.text}")
    else:
        print("✅ Upload successful with folder_id=None")
    
    # Test 4: Get available folders
    print("\n📁 Get available folders")
    
    response = requests.get(f"{base_url}/folders", headers=headers)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        folders = response.json()
        print(f"Found {len(folders)} folders:")
        for folder in folders[:3]:  # Show first 3
            print(f"  - ID: {folder['id']}, Name: {folder['name']}")
        
        # Test 5: Upload with valid folder_id
        if folders:
            print(f"\n📤 Test 5: Upload with valid folder_id={folders[0]['id']}")
            
            data['folder_id'] = str(folders[0]['id'])
            data['title'] = 'Test Document Valid Folder'
            
            response = requests.post(f"{base_url}/documents/upload", files=files, data=data, headers=headers)
            
            print(f"Status: {response.status_code}")
            if response.status_code != 200:
                print(f"Error: {response.text}")
            else:
                print("✅ Upload successful with valid folder_id")
    
    print("\n🏁 Debug upload complete!")

if __name__ == "__main__":
    debug_upload()
