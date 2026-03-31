#!/usr/bin/env python3
"""
Test File Health API
"""

import requests
import json

def test_health_api():
    """Test the new file health endpoints"""
    
    print("🔍 Testing File Health API")
    print("=" * 40)
    
    # Login
    login_data = {'username': 'admin', 'password': 'admin'}
    response = requests.post('http://localhost:8000/auth/token', data=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    print("✅ Login successful")
    
    # Test document 250 health check
    print("\n📄 Checking document 250 health...")
    health_response = requests.get('http://localhost:8000/file-health/check/250', headers=headers)
    
    if health_response.status_code == 200:
        health = health_response.json()
        print(f"✅ Health check successful")
        print(f"📊 Health summary: {health.get('health_summary')}")
        print(f"🗑️  Should suggest deletion: {health.get('should_suggest_deletion')}")
        print(f"❌ Delete reason: {health.get('delete_reason')}")
        print(f"📄 Page count: {health.get('page_count')}")
        print(f"📁 File size: {health.get('file_size')} bytes")
        print(f"🔒 Is encrypted: {health.get('is_encrypted')}")
        print(f"📖 Is readable: {health.get('is_readable')}")
    else:
        print(f"❌ Health check error: {health_response.status_code}")
        print(f"Details: {health_response.text[:200]}")
    
    # Test all documents health
    print("\n📋 Checking all documents health...")
    all_health_response = requests.get('http://localhost:8000/file-health/check-all', headers=headers)
    
    if all_health_response.status_code == 200:
        all_health = all_health_response.json()
        print(f"✅ All documents health check successful")
        print(f"📊 Total documents: {all_health.get('total_documents')}")
        print(f"✅ Healthy files: {all_health.get('healthy_files')}")
        print(f"❌ Problematic files: {all_health.get('problematic_files')}")
        
        # Show problematic files
        problematic = all_health.get('problematic_files_detail', [])
        if problematic:
            print(f"\n❌ Problematic files found:")
            for file in problematic:
                print(f"  • ID {file['document_id']}: {file['filename']} - {file['reason']}")
        else:
            print("\n✅ No problematic files found!")
    else:
        print(f"❌ All documents health check error: {all_health_response.status_code}")
        print(f"Details: {all_health_response.text[:200]}")
    
    # Test cleanup suggestions (admin only)
    print("\n🧹 Getting cleanup suggestions...")
    cleanup_response = requests.get('http://localhost:8000/file-health/suggest-cleanup', headers=headers)
    
    if cleanup_response.status_code == 200:
        cleanup = cleanup_response.json()
        print(f"✅ Cleanup suggestions retrieved")
        print(f"🗑️  Files to delete: {cleanup.get('files_to_delete')}")
        print(f"💾 Space to free: {cleanup.get('total_size_to_free_mb')} MB")
        
        suggestions = cleanup.get('suggestions', [])
        if suggestions:
            print(f"\n🗑️  Suggested files for cleanup:")
            for file in suggestions[:5]:  # Show first 5
                print(f"  • ID {file['document_id']}: {file['filename']} ({file['file_size_mb']} MB)")
                print(f"    Reason: {file['reason']}")
        else:
            print("\n✅ No cleanup needed!")
    else:
        print(f"❌ Cleanup suggestions error: {cleanup_response.status_code}")
        print(f"Details: {cleanup_response.text[:200]}")

if __name__ == "__main__":
    test_health_api()
