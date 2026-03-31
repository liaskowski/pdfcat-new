#!/usr/bin/env python3
"""
Test cleanup suggestions
"""

import requests

def test_cleanup():
    """Test cleanup suggestions endpoint"""
    
    # Login
    login_data = {'username': 'admin', 'password': 'admin'}
    response = requests.post('http://localhost:8000/auth/token', data=login_data)
    token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test cleanup suggestions with POST
    cleanup_response = requests.post('http://localhost:8000/file-health/suggest-cleanup', headers=headers)
    print(f'Cleanup suggestions status: {cleanup_response.status_code}')
    
    if cleanup_response.status_code == 200:
        cleanup = cleanup_response.json()
        print(f'Files to delete: {cleanup.get("files_to_delete")}')
        print(f'Space to free: {cleanup.get("total_size_to_free_mb")} MB')
        
        suggestions = cleanup.get('suggestions', [])
        print(f'\nTop 5 largest problematic files:')
        for i, file in enumerate(suggestions[:5]):
            print(f'{i+1}. ID {file["document_id"]}: {file["filename"]} ({file["file_size_mb"]} MB)')
    else:
        print(f'Error: {cleanup_response.text[:200]}')

if __name__ == "__main__":
    test_cleanup()
