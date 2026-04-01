import sys
import os
from pathlib import Path

# Настройка путей для портативности: корень проекта и локальные библиотеки
BASE_DIR = str(Path(__file__).resolve().parent.parent)
# LOCAL_SITE_PACKAGES = os.path.join(BASE_DIR, "vendor", "python", "Lib", "site-packages")

# if LOCAL_SITE_PACKAGES not in sys.path:
#     sys.path.insert(0, LOCAL_SITE_PACKAGES)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Initialize logging FIRST before any other imports
from client.utils.logger import get_logger, log_info, log_error, log_debug, log_warning, log_critical

logger = get_logger("client.main")

# Initialize hang monitor for debugging
try:
    from client.debug_monitor import get_monitor
    hang_monitor = get_monitor()
    log_info("main", "Hang monitor initialized")
except Exception as e:
    log_error("main", f"Failed to initialize hang monitor: {e}")
    hang_monitor = None

try:
    from client.main_window import MainWindow
    from client.utils.config_manager import ConfigManager
    from client.themes import DARK_THEME_QSS, LIGHT_THEME_QSS
except Exception:
    from client.main_window import MainWindow
    from client.utils.config_manager import ConfigManager
    from client.themes import DARK_THEME_QSS, LIGHT_THEME_QSS


def main() -> int:
    log_info("main", "Starting PDFLib Client")
    
    # Check Python architecture
    import struct
    bits = struct.calcsize("P") * 8
    log_info("main", f"Python architecture: {bits}-bit")
    if bits == 32:
        log_info("main", "NOTE: 32-bit Python detected. For better performance with large documents, consider using 64-bit Python.")
        log_info("main", "64-bit Python can use more RAM for large image buffers.")

    # Force Desktop OpenGL for high performance hardware acceleration
    os.environ["QT_OPENGL"] = "desktop"
    log_debug("main", "OpenGL set to desktop mode")

    # High DPI support
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    log_debug("main", "High DPI settings configured")

    app = QApplication(sys.argv)
    log_info("main", "QApplication initialized")

    # Initialize ThemeManager to register fonts
    from client.themes import ThemeManager
    ThemeManager()
    log_debug("main", "ThemeManager initialized")

    # Apply initial settings from ConfigManager
    try:
        config = ConfigManager()
        theme = config.get("theme")
        font_size = config.get("font_size")

        style = DARK_THEME_QSS if theme == "Dark" else LIGHT_THEME_QSS
        font_qss = f"\nQWidget {{ font-size: {font_size}pt; }}\n"
        app.setStyleSheet(style + font_qss)
        log_info("main", f"Theme applied: {theme}, Font size: {font_size}pt")
    except Exception as e:
        log_error("main", f"Failed to apply initial settings: {e}", exc_info=True)

    w = MainWindow()
    log_info("main", "MainWindow created")

    # Check authentication before showing the window
    if not w.controller.start():
        log_warning("main", "Authentication failed, exiting")
        return 0

    log_info("main", "Authentication successful, showing window")
    w.show()
    
    log_info("main", "Application startup complete")
    
    try:
        exit_code = app.exec()
        log_info("main", f"Application exited with code: {exit_code}")
        return exit_code
    except Exception as e:
        log_critical("main", f"Application crash: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())