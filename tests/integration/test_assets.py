#!/usr/bin/env python3
"""
Test assets endpoints
"""

import requests
import os

def test_assets():
    """Test assets endpoints"""
    
    print("🎨 Testing Assets Endpoints")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    # Test endpoints
    endpoints = [
        ("/", "Home page"),
        ("/favicon.ico", "Favicon"),
        ("/assets/logo", "Logo"),
        ("/assets/images/pdfCat.jpg", "Direct image"),
        ("/assets/icons/pdfCat.ico", "Direct icon"),
        ("/health", "Health check")
    ]
    
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', 'unknown')
                size = len(response.content)
                print(f"✅ {description}: {response.status_code} ({content_type}, {size} bytes)")
                
                # Save some files for verification
                if endpoint in ["/favicon.ico", "/assets/logo"]:
                    filename = endpoint.split('/')[-1]
                    if not filename:
                        filename = "favicon.ico"
                    with open(f"test_{filename}", 'wb') as f:
                        f.write(response.content)
                    print(f"   💾 Saved as test_{filename}")
            else:
                print(f"❌ {description}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {description}: Error - {e}")
    
    print("\n🏁 Assets testing complete!")
    print("\n📋 Verification:")
    print("• Check test_favicon.ico and test_pdfCat.jpg files")
    print("• Visit http://localhost:8000 in browser")
    print("• Check favicon in browser tab")

if __name__ == "__main__":
    test_assets()
