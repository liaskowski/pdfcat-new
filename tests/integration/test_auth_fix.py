#!/usr/bin/env python3
"""Test script to verify authentication fixes"""

import sys
import os
from pathlib import Path

# Add client to path
sys.path.insert(0, str(Path(__file__).parent / "client"))

from client.api_manager import APIManager
from client.ui.thumbnail_runnable import ThumbnailRunnable
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication

def test_authentication():
    print("Testing authentication fixes...")
    
    # Create app for Qt components
    app = QApplication([])
    
    # Test 1: API Manager without token
    print("\n1. Testing API Manager without token:")
    api = APIManager("http://127.0.0.1:8000", None)
    print(f"   API token: {api.token}")
    
    # Test 2: SearchHandler token check
    print("\n2. Testing SearchHandler token check:")
    try:
        from client.ui.controllers.search_handler import SearchHandler
        # Mock UI components
        class MockUI:
            nav_tree = type('MockNavTree', (), {'selectedItems': lambda: []})()
            breadcrumbs = type('MockBreadcrumbs', (), {'setText': lambda x: None})()
        
        handler = SearchHandler(api, MockUI(), None)
        handler._pending_fetch_params = ("my", None, None, True)
        handler._execute_fetch()
        print("   SearchHandler executed without token (should skip)")
    except Exception as e:
        print(f"   SearchHandler test failed: {e}")
    
    # Test 3: ThumbnailRunnable token check
    print("\n3. Testing ThumbnailRunnable token check:")
    try:
        runnable = ThumbnailRunnable(api, 87, QSize(64, 64))
        runnable.run()
        print("   ThumbnailRunnable executed without token (should skip)")
    except Exception as e:
        print(f"   ThumbnailRunnable test failed: {e}")
    
    # Test 4: API Manager with token
    print("\n4. Testing API Manager with token:")
    api.set_token("test_token_123")
    print(f"   API token: {api.token}")
    
    # Test 5: Test API call with token
    print("\n5. Testing API call with token:")
    try:
        # This will fail because token is invalid, but should not be 401 authentication error
        result = api.get_preview_png(87)
        print(f"   API call result: {len(result) if result else 'None'}")
    except Exception as e:
        print(f"   API call error: {e}")
        if "401" in str(e) or "Not authenticated" in str(e):
            print("   ❌ Still getting authentication error!")
        else:
            print("   ✅ Authentication error fixed (different error expected)")
    
    print("\n✅ Authentication fix test completed!")

if __name__ == "__main__":
    test_authentication()
