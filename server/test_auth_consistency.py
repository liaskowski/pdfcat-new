"""
Authentication consistency tests to prevent 401 errors.
Run this script to verify all endpoints use consistent authentication.
"""

import inspect
from fastapi import APIRouter
from server.routers import documents
from server.security import oauth2_scheme as require_auth


def check_endpoint_auth_consistency():
    """Check if all document endpoints use consistent authentication."""
    issues = []
    
    # Get all endpoints from documents router
    router = documents.router
    routes = router.routes
    
    for route in routes:
        if hasattr(route, 'endpoint') and hasattr(route, 'path'):
            endpoint_name = route.endpoint.__name__
            path = route.path
            
            # Check if endpoint uses proper authentication
            sig = inspect.signature(route.endpoint)
            dependencies = []
            
            for param_name, param in sig.parameters.items():
                if hasattr(param, 'default') and hasattr(param.default, 'dependency'):
                    dependencies.append(param.default.dependency.__name__ if hasattr(param.default.dependency, '__name__') else str(param.default.dependency))
            
            # Check for authentication inconsistencies
            if '/download' in path or '/preview' in path:
                if 'get_current_active_user_optional' in str(dependencies):
                    issues.append(f"❌ {endpoint_name} ({path}): Uses optional auth - should use require_auth()")
                elif 'get_current_active_user' not in str(dependencies) and 'require_auth' not in str(dependencies):
                    issues.append(f"❌ {endpoint_name} ({path}): Missing authentication")
                else:
                    print(f"✅ {endpoint_name} ({path}): Proper authentication")
    
    if issues:
        print("\n🚨 AUTHENTICATION ISSUES FOUND:")
        for issue in issues:
            print(f"  {issue}")
        print(f"\nTotal issues: {len(issues)}")
        return False
    else:
        print("\n✅ All endpoints use consistent authentication!")
        return True


def check_client_api_consistency():
    """Check if client API uses session for all authenticated calls."""
    import os
    import re
    
    client_dir = "client/api"
    issues = []
    
    if os.path.exists(client_dir):
        for filename in os.listdir(client_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(client_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for direct requests calls without session
                direct_requests = re.findall(r'requests\.(get|post|put|patch|delete)\(', content)
                if direct_requests:
                    issues.append(f"❌ {filename}: Found {len(direct_requests)} direct requests calls")
                
                # Check for session usage
                session_calls = re.findall(r'self\._session\.(get|post|put|patch|delete)\(', content)
                print(f"📊 {filename}: {len(session_calls)} session calls, {len(direct_requests)} direct calls")
    
    if issues:
        print("\n🚨 CLIENT API ISSUES FOUND:")
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print("\n✅ All client API calls use authenticated session!")
        return True


if __name__ == "__main__":
    print("🔍 Checking authentication consistency...")
    print("\n" + "="*50)
    print("SERVER ENDPOINT CHECK:")
    server_ok = check_endpoint_auth_consistency()
    
    print("\n" + "="*50)
    print("CLIENT API CHECK:")
    client_ok = check_client_api_consistency()
    
    print("\n" + "="*50)
    if server_ok and client_ok:
        print("🎉 ALL AUTHENTICATION CHECKS PASSED!")
        exit(0)
    else:
        print("❌ AUTHENTICATION ISSUES DETECTED - Fix before deploying!")
        exit(1)
