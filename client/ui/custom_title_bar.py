from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPainterPath
import qtawesome as qta
from ..themes import ThemeManager
from ..utils.translator import Translator
from pathlib import Path

# Get paths to assets
CLIENT_DIR = Path(__file__).parent.parent.parent
ASSETS_DIR = CLIENT_DIR / "client" / "assets"
LOGO_PATH = ASSETS_DIR / "pdfCat.jpg"

class CustomTitleBar(QWidget):
    minimize_clicked = pyqtSignal()
    maximize_restore_clicked = pyqtSignal()
    close_clicked = pyqtSignal()
    profile_clicked = pyqtSignal()
    admin_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()

    def __init__(self, parent=None, is_admin=False, username="User"):
        super().__init__(parent)
        self.theme_manager = ThemeManager()
        self.translator = Translator()
        self.setFixedHeight(40)
        self.setObjectName("titleBar")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(15)

        # Left: Logo & Title
        # Add logo if available
        if LOGO_PATH.exists():
            logo_label = QLabel()
            logo_pixmap = QPixmap(str(LOGO_PATH))
            logo_pixmap = logo_pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
            logo_label.setFixedSize(24, 24)
            layout.addWidget(logo_label)
            layout.addSpacing(10)  # Space between logo and title
        
        self.title_label = QLabel(self.translator.tr("app_title"))
        layout.addWidget(self.title_label)

        # Center: Spacer
        layout.addStretch(1)

        # Right: Actions
        
        # Admin Button
        self.admin_btn = QPushButton(self.translator.tr("admin.title"))
        self.admin_btn.setVisible(is_admin)
        self.admin_btn.clicked.connect(self.admin_clicked)
        layout.addWidget(self.admin_btn)

        # Settings Button
        self.settings_btn = QPushButton()
        self.settings_btn.setToolTip(self.translator.tr("settings.title"))
        self.settings_btn.setMinimumHeight(30)
        self.settings_btn.setProperty("iconOnly", True)
        self.settings_btn.clicked.connect(self.settings_clicked)
        layout.addWidget(self.settings_btn)

        # Avatar
        self.avatar_lbl = QLabel()
        self.avatar_lbl.setFixedSize(24, 24)
        self.set_default_avatar()
        layout.addWidget(self.avatar_lbl)

        # Profile Button
        self.profile_btn = QPushButton()
        self.profile_btn.setToolTip(self.translator.tr("profile.title"))
        self.profile_btn.setMinimumWidth(100)
        self.profile_btn.setStyleSheet("text-align: right; padding-right: 8px;") 
        self._full_username = username
        self._set_elided_text(username)
        self.profile_btn.clicked.connect(self.profile_clicked)
        layout.addWidget(self.profile_btn)

        # Window Controls
        self.win_controls = QFrame()
        wc_layout = QHBoxLayout(self.win_controls)
        wc_layout.setContentsMargins(0, 0, 0, 0)
        wc_layout.setSpacing(0)
        
        self.min_btn = QPushButton()
        self.min_btn.setFixedSize(45, 40)
        self.min_btn.setProperty("iconOnly", True)
        self.min_btn.clicked.connect(self.minimize_clicked)

        self.max_btn = QPushButton()
        self.max_btn.setFixedSize(45, 40)
        self.max_btn.setProperty("iconOnly", True)
        self.max_btn.clicked.connect(self.maximize_restore_clicked)
        
        self.close_btn = QPushButton()
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.setFixedSize(45, 40)
        self.close_btn.setProperty("iconOnly", True)
        self.close_btn.clicked.connect(self.close_clicked)
        
        wc_layout.addWidget(self.min_btn)
        wc_layout.addWidget(self.max_btn)
        wc_layout.addWidget(self.close_btn)
        
        layout.addWidget(self.win_controls)

        self.update_theme(self.theme_manager.current_theme)

        # Drag logic
        self._drag_pos = QPoint()

    def update_theme(self, theme_name: str):
        # Fetch palette based on theme name
        palette = self.theme_manager.PALETTE_LIGHT if theme_name == "Light" else self.theme_manager.PALETTE_DARK
        
        bg_color = palette["background"]
        text_color = palette["text"]
        hover_color = palette["hover"]
        border_color = palette["border"]
        danger_bg = palette["danger"]
        
        # Icon color: dark for light theme, white for dark theme
        icon_color = "#1C1C1E" if theme_name == "Light" else "#EBEBF5"
        
        self.setStyleSheet(f"""
            QWidget#titleBar {{
                background-color: {bg_color}; 
                border-bottom: 1px solid {border_color};
            }}
            QFrame {{
                background-color: transparent;
                border: none;
            }}
            QLabel {{
                color: {text_color};
                font-weight: 600;
                background-color: transparent;
                font-family: "Inter", "Segoe UI", sans-serif;
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {text_color};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton#closeBtn:hover {{
                background-color: {danger_bg};
                color: white;
            }}
        """)
        
        icon_size = QSize(16, 16)
        
        # Update icons
        self.admin_btn.setIcon(qta.icon('fa5s.user-shield', color=icon_color))
        self.admin_btn.setIconSize(icon_size)
        
        self.settings_btn.setIcon(qta.icon('fa5s.cog', color=icon_color))
        self.settings_btn.setIconSize(icon_size)
        
        self.profile_btn.setIcon(qta.icon('fa5s.user', color=icon_color))
        self.profile_btn.setIconSize(icon_size)
        
        self.min_btn.setIcon(qta.icon('fa5s.minus', color=icon_color))
        self.min_btn.setIconSize(icon_size)
        
        is_max = self.window().isMaximized() if self.window() else False
        max_icon = 'fa5s.window-restore' if is_max else 'fa5s.window-maximize'
        self.max_btn.setIcon(qta.icon(max_icon, color=icon_color))
        self.max_btn.setIconSize(icon_size)
        
        self.close_btn.setIcon(qta.icon('fa5s.times', color=icon_color))
        self.close_btn.setIconSize(icon_size)

    def update_scale(self, scale_factor: float):
        icon_size = int(16 * scale_factor)
        btn_w = int(45 * scale_factor)
        btn_h = int(40 * scale_factor)
        
        # Update settings button (keep square)
        settings_size = int(30 * scale_factor)
        self.settings_btn.setFixedSize(settings_size, settings_size)
        self.settings_btn.setIconSize(QSize(icon_size, icon_size))
        
        # Update window controls
        for btn in [self.min_btn, self.max_btn, self.close_btn]:
            btn.setFixedSize(btn_w, btn_h)
            btn.setIconSize(QSize(icon_size, icon_size))
            
        # Update layout margins if needed
        margin = int(15 * scale_factor)
        self.layout().setContentsMargins(margin, 0, 0, 0) # Right margin is handled by buttons
        self.setFixedHeight(btn_h)

    def update_user_info(self, is_admin: bool, username: str):
        self.admin_btn.setVisible(is_admin)
        self._full_username = username
        self._set_elided_text(username)

    def _set_elided_text(self, text: str):
        # Allow button to expand slightly but respect layout constraints
        font_metrics = self.profile_btn.fontMetrics()
        # Use available width or a max constraint
        available_width = 150 # Arbitrary max for username
        elided = font_metrics.elidedText(text, Qt.TextElideMode.ElideRight, available_width)
        self.profile_btn.setText(elided)

    def resizeEvent(self, event):
        if hasattr(self, "_full_username"):
            self._set_elided_text(self._full_username)
        super().resizeEvent(event)

    def set_avatar(self, pixmap: QPixmap):
        # Mask circle
        size = 24
        rounded = QPixmap(size, size)
        rounded.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        painter.end()
        
        self.avatar_lbl.setPixmap(rounded)

    def set_default_avatar(self):
        pix = QPixmap(24, 24)
        pix.fill(Qt.GlobalColor.gray)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, 24, 24)
        painter.setClipPath(path) # Just to be circular
        painter.end()
        self.set_avatar(pix)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # We no longer need complex margin checks here because MainWindow's 
            # eventFilter will catch and consume resize events before they reach here.
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            # Check if maximized - dragging should restore it (standard behavior)
            if self.window().isMaximized():
                # To prevent jumping, we'd need to calculate the new pos, 
                # but for now, just restoring is better than broken drag.
                self.window().showNormal()
                # Update drag pos after restore to avoid jumping to old coordinates
                self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
                
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_restore_clicked.emit()
            event.accept()
