#!/usr/bin/env python3
"""
Check recent documents to find test ones
"""

import requests

def check_documents():
    """Check recent documents"""
    
    print("📄 Checking Documents")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    # Login
    login_data = {"username": "admin", "password": "admin"}
    response = requests.post(f"{base_url}/auth/token", data=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get documents
    response = requests.get(f"{base_url}/documents/", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to get documents: {response.status_code}")
        return
    
    documents = response.json()
    print(f"📄 Found {len(documents)} documents")
    
    # Show recent documents
    print("\n📋 Recent documents:")
    for i, doc in enumerate(documents[:10]):
        print(f"  {i+1}. ID: {doc['id']}, Title: '{doc.get('title', 'N/A')}', Filename: '{doc.get('filename', 'N/A')}'")
    
    # Find documents with "Test" in title
    test_docs = [doc for doc in documents if 'Test' in doc.get('title', '')]
    
    if test_docs:
        print(f"\n📄 Found {len(test_docs)} test documents:")
        for doc in test_docs[:5]:
            print(f"  - ID: {doc['id']}, Title: '{doc['title']}'")
    else:
        print("\n❌ No test documents found")
        print("Let's create one...")
        
        # Create a test document
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000054 00000 n\n0000000109 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
        
        files = {
            'file': ('test_document.pdf', pdf_content, 'application/pdf')
        }
        
        data = {
            'title': 'Test Document Download',
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
        
        if response.status_code == 200:
            print("✅ Test document created successfully")
            new_doc = response.json()
            print(f"   ID: {new_doc['id']}, Title: '{new_doc['title']}'")
            return new_doc['id']
        else:
            print(f"❌ Failed to create test document: {response.status_code}")
            print(f"   Error: {response.text}")
    
    return test_docs[0]['id'] if test_docs else None

if __name__ == "__main__":
    check_documents()
