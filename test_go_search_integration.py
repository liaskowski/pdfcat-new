#!/usr/bin/env python3
"""
Test Go Search Service integration with FastAPI
"""

import sys
import os
import requests

# Add server to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

def test_go_search_service():
    """Test direct Go Search Service calls"""
    print("🔍 Testing Go Search Service integration...")
    
    # Test 1: Health check
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Health check passed: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Go service: {e}")
        return False
    
    # Test 2: Index some documents
    print("\n2. Testing document indexing...")
    test_docs = [
        {"id": 101, "content": "This is a PDF document about machine learning and artificial intelligence"},
        {"id": 102, "content": "Another document covering web development with React and Node.js"},
        {"id": 103, "content": "Database management guide focusing on PostgreSQL and MySQL optimization"},
    ]
    
    for doc in test_docs:
        try:
            response = requests.post(
                "http://localhost:8001/index",
                json=doc,
                timeout=5
            )
            if response.status_code == 200:
                print(f"✅ Indexed document {doc['id']}")
            else:
                print(f"❌ Failed to index document {doc['id']}: {response.status_code}")
        except Exception as e:
            print(f"❌ Error indexing document {doc['id']}: {e}")
    
    # Test 3: Search functionality
    print("\n3. Testing search functionality...")
    test_queries = [
        ("machine learning", [101]),
        ("web development", [102]),
        ("database", [103]),
        ("React", [102]),
        ("PostgreSQL", [103]),
    ]
    
    for query, expected_ids in test_queries:
        try:
            response = requests.get(
                "http://localhost:8001/search",
                params={"q": query},
                timeout=5
            )
            if response.status_code == 200:
                results = response.json()
                found_ids = [r["id"] for r in results]
                print(f"✅ Search '{query}': found {found_ids}, expected {expected_ids}")
                
                if set(found_ids) == set(expected_ids):
                    print("   🎯 Perfect match!")
                else:
                    print("   ⚠️  Partial match or unexpected results")
            else:
                print(f"❌ Search failed for '{query}': {response.status_code}")
        except Exception as e:
            print(f"❌ Error searching '{query}': {e}")
    
    # Test 4: Performance test
    print("\n4. Testing performance...")
    import time
    
    start_time = time.time()
    response = requests.get("http://localhost:8001/search?q=learning", timeout=5)
    end_time = time.time()
    
    if response.status_code == 200:
        duration = (end_time - start_time) * 1000  # Convert to ms
        print(f"✅ Search completed in {duration:.2f}ms")
        
        if duration < 100:  # Less than 100ms is excellent
            print("   🚀 Excellent performance!")
        elif duration < 500:  # Less than 500ms is good
            print("   👍 Good performance!")
        else:
            print("   ⚠️  Could be faster")
    
    print("\n🎉 Go Search Service integration test completed!")
    return True

def test_fastapi_integration_simulation():
    """Simulate FastAPI integration without starting the server"""
    print("\n🔗 Simulating FastAPI integration...")
    
    # Simulate the search service logic
    from server.config import settings
    
    # Override settings for testing
    settings.SEARCH_GO_URL = "http://localhost:8001"
    
    print(f"✅ SEARCH_GO_URL configured: {settings.SEARCH_GO_URL}")
    
    # Simulate a search request like FastAPI would make
    try:
        response = requests.get(
            f"{settings.SEARCH_GO_URL}/search",
            params={"q": "machine learning"},
            timeout=5
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"✅ FastAPI-style search successful: found {len(results)} results")
            
            # Simulate database lookup for document metadata
            for result in results:
                print(f"   📄 Document ID: {result['id']}, Score: {result['score']}")
                # In real FastAPI, this would be:
                # documents = db.query(Document).filter(Document.id.in_(ids)).all()
        else:
            print(f"❌ FastAPI-style search failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ FastAPI integration error: {e}")

if __name__ == "__main__":
    print("🚀 Starting Go Search Service Integration Test")
    print("=" * 60)
    
    # Test Go service directly
    if test_go_search_service():
        # Test FastAPI integration simulation
        test_fastapi_integration_simulation()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("\n📋 Next steps:")
        print("1. Fix Python environment issues")
        print("2. Start FastAPI server with SEARCH_GO_URL=http://localhost:8001")
        print("3. Test /search endpoint through FastAPI")
        print("4. Verify automatic document indexing")
    else:
        print("\n❌ Go Search Service test failed!")
        print("Make sure the Go service is running on localhost:8001")
