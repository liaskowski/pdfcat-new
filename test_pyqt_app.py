#!/usr/bin/env python3
"""
Test PyQt6 application with logo and icon
"""

import sys
import os
from pathlib import Path

# Add project root to path
BASE_DIR = str(Path(__file__).resolve().parent)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def test_pyqt_app():
    """Test PyQt6 application startup and asset loading"""
    
    print("🖥️ Testing PyQt6 Application")
    print("=" * 40)
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QIcon
        print("✅ PyQt6 imports successful")
    except Exception as e:
        print(f"❌ PyQt6 import failed: {e}")
        return
    
    # Check asset paths
    client_assets_dir = Path(BASE_DIR) / "client" / "assets"
    logo_path = client_assets_dir / "pdfCat.jpg"
    icon_path = client_assets_dir / "pdfCat.ico"
    
    print(f"\n📁 Asset paths:")
    print(f"  Client assets dir: {client_assets_dir}")
    print(f"  Logo path: {logo_path} - {'✅ Exists' if logo_path.exists() else '❌ Missing'}")
    print(f"  Icon path: {icon_path} - {'✅ Exists' if icon_path.exists() else '❌ Missing'}")
    
    # Try to create application
    app = QApplication(sys.argv)
    
    # Set application icon
    if icon_path.exists():
        try:
            app_icon = QIcon(str(icon_path))
            app.setWindowIcon(app_icon)
            print("✅ Application icon set successfully")
        except Exception as e:
            print(f"❌ Failed to set application icon: {e}")
    else:
        print("❌ Icon file not found")
    
    # Try to create main window
    try:
        from client.main_window import MainWindow
        print("✅ MainWindow import successful")
        
        main_window = MainWindow()
        print("✅ MainWindow created successfully")
        
        # Check if icon was set
        window_icon = main_window.windowIcon()
        if window_icon.isNull():
            print("❌ Window icon is null")
        else:
            print("✅ Window icon set successfully")
        
        # Show window briefly for testing
        main_window.show()
        print("✅ Window shown successfully")
        
        # Close after 2 seconds for testing
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, app.quit)
        
        print("🏁 Starting application (will close in 2 seconds)...")
        app.exec()
        
    except Exception as e:
        print(f"❌ Failed to create MainWindow: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🏁 PyQt6 test complete!")

if __name__ == "__main__":
    test_pyqt_app()
