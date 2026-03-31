#!/usr/bin/env python3
"""
Test client imports to identify syntax errors
"""

import sys
import os

# Add client to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'client'))

print("Testing client imports...")

try:
    print("1. Testing server_status import...")
    from ui.server_status import ServerStatusWorker, ServerStatusMonitor
    print("   ✅ ServerStatus imports OK")
except Exception as e:
    print(f"   ❌ ServerStatus import failed: {e}")

try:
    print("2. Testing auth_dialog import...")
    from ui.auth_dialog import LoginDialog
    print("   ✅ AuthDialog imports OK")
except Exception as e:
    print(f"   ❌ AuthDialog import failed: {e}")

try:
    print("3. Testing main_layout import...")
    from ui.layouts.main_layout import MainLayout
    print("   ✅ MainLayout imports OK")
except Exception as e:
    print(f"   ❌ MainLayout import failed: {e}")

try:
    print("4. Testing main_window import...")
    from main_window import MainWindow
    print("   ✅ MainWindow imports OK")
except Exception as e:
    print(f"   ❌ MainWindow import failed: {e}")

print("\nImport test completed!")
