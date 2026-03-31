#!/usr/bin/env python3
"""
Quick authentication consistency checker
"""

import os
import re

def check_client_api():
    """Check client API for direct requests calls"""
    issues = []
    client_dir = "client/api"
    
    if os.path.exists(client_dir):
        for filename in os.listdir(client_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(client_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for direct requests calls
                direct_requests = re.findall(r'requests\.(get|post|put|patch|delete)\(', content)
                if direct_requests:
                    issues.append(f"❌ {filename}: {len(direct_requests)} direct requests calls")
                
                # Check for session usage
                session_calls = re.findall(r'self\._session\.(get|post|put|patch|delete)\(', content)
                print(f"📊 {filename}: {len(session_calls)} session calls, {len(direct_requests)} direct calls")
    
    return issues

def check_server_endpoints():
    """Check server endpoints for auth inconsistencies"""
    issues = []
    server_file = "server/routers/documents.py"
    
    if os.path.exists(server_file):
        with open(server_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for problematic patterns
        if 'get_current_active_user_optional' in content:
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if 'get_current_active_user_optional' in line:
                    # Check if this is in download/preview endpoint
                    context = '\n'.join(lines[max(0, i-5):i+5])
                    if '/download' in context or '/preview' in context:
                        issues.append(f"❌ Line {i}: get_current_active_user_optional in download/preview endpoint")
                    else:
                        print(f"✅ Line {i}: get_current_active_user_optional in appropriate context")
        
        if 'get_current_active_user' in content:
            print("✅ Found get_current_active_user usage (proper Authorization header)")
    
    return issues

if __name__ == "__main__":
    print("🔍 Quick Authentication Check")
    print("=" * 40)
    
    print("\n📡 Client API Check:")
    client_issues = check_client_api()
    
    print("\n🖥️  Server Endpoints Check:")
    server_issues = check_server_endpoints()
    
    print("\n" + "=" * 40)
    all_issues = client_issues + server_issues
    
    if all_issues:
        print("🚨 ISSUES FOUND:")
        for issue in all_issues:
            print(f"  {issue}")
        print(f"\nTotal: {len(all_issues)} issues")
    else:
        print("✅ No authentication issues found!")
    
    print(f"\n📋 Summary:")
    print(f"  Client issues: {len(client_issues)}")
    print(f"  Server issues: {len(server_issues)}")
    print(f"  Total issues: {len(all_issues)}")
