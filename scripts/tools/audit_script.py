import requests
import time
import os
import io

BASE_URL = "http://127.0.0.1:8000"

def test_audit_manual():
    print("Starting Manual Audit via Requests...")
    
    # 1. Login
    try:
        resp = requests.post(f"{BASE_URL}/auth/token", data={"username": "admin", "password": "admin"}, timeout=5)
    except Exception as e:
        print(f"FAILED: Could not connect to server at {BASE_URL}: {e}")
        return

    if resp.status_code != 200:
        print(f"FAILED: Login (Is server running? {resp.text})")
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("SUCCESS: Login")

    # 2. Upload
    pdf_content = b"%PDF-1.4\n%%EOF"
    resp = requests.post(
        f"{BASE_URL}/documents/upload",
        data={"title": "Audit Doc", "use_ocr": "false"},
        files={"file": ("audit.pdf", io.BytesIO(pdf_content), "application/pdf")},
        headers=headers
    )
    if resp.status_code != 200:
        print(f"FAILED: Upload ({resp.text})")
        return
    doc = resp.json()
    doc_id = doc["id"]
    print(f"SUCCESS: Upload (doc_id={doc_id})")

    # 3. Duplicate
    resp = requests.post(f"{BASE_URL}/documents/{doc_id}/duplicate", data={}, headers=headers)
    if resp.status_code != 200:
        print(f"FAILED: Duplicate ({resp.text})")
        return
    dup_doc = resp.json()
    print(f"SUCCESS: Duplicate (new_doc_id={dup_doc['id']})")
    
    if dup_doc.get('file_path') == doc.get('file_path'):
        print("ISSUE FOUND: Duplicated document points to the same file path as original!")

    # 4. Delete Original and check Duplicate
    requests.delete(f"{BASE_URL}/documents/{doc_id}", headers=headers)
    print(f"DELETED: Original doc {doc_id}")
    
    resp = requests.get(f"{BASE_URL}/documents/{dup_doc['id']}/download", headers=headers)
    if resp.status_code != 200:
        print(f"ISSUE FOUND: Duplicate document file is missing or inaccessible after original deletion! ({resp.status_code})")
    else:
        print("INFO: Duplicate document still has its file.")

    # 5. Orphan Folder Check
    resp = requests.post(f"{BASE_URL}/folders/", json={"name": "Audit Folder"}, headers=headers)
    folder_id = resp.json()["id"]
    
    resp = requests.post(
        f"{BASE_URL}/documents/upload",
        data={"title": "Orphan Doc", "folder_id": folder_id, "use_ocr": "false"},
        files={"file": ("orphan.pdf", io.BytesIO(pdf_content), "application/pdf")},
        headers=headers
    )
    orphan_doc_id = resp.json()["id"]
    
    requests.delete(f"{BASE_URL}/folders/{folder_id}", headers=headers)
    print(f"DELETED: Folder {folder_id}")
    
    resp = requests.get(f"{BASE_URL}/documents/{orphan_doc_id}", headers=headers)
    if resp.status_code == 200:
        doc_data = resp.json()
        print(f"INFO: Orphan doc folder_id is {doc_data.get('folder_id')}")
        if doc_data.get('folder_id') is not None:
            print("ISSUE FOUND: Document still points to deleted folder_id!")
    else:
        print("INFO: Document was deleted with folder.")

if __name__ == "__main__":
    test_audit_manual()
