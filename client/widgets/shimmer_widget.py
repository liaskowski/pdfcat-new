"""
Shimmer loading effect widget for smooth loading states.
"""

from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtGui import QColor, QPainter, QLinearGradient, QPen


class ShimmerWidget(QWidget):
    """
    A widget that displays a shimmer loading effect.
    Used for smooth loading states in file grid and other components.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._offset = 0
        self._animation_speed = 20  # ms
        self._shimmer_width = 200
        
        # Start animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_shimmer)
        self.timer.start(self._animation_speed)
        
    def _update_shimmer(self):
        self._offset += 2
        if self._offset > self.width() + self._shimmer_width:
            self._offset = -self._shimmer_width
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background items (skeleton)
        self._draw_skeleton(painter)
        
        # Draw shimmer effect
        self._draw_shimmer(painter)
    
    def _draw_skeleton(self, painter: QPainter):
        """Draw skeleton placeholders."""
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Get colors from theme or use defaults
        base_color = QColor("#2d3748")  # Dark gray-blue
        item_color = QColor("#4a5568")  # Lighter gray-blue
        
        # Draw multiple skeleton items
        y_offset = 20
        for i in range(6):  # 6 placeholder items
            # Icon placeholder (square)
            painter.setBrush(item_color)
            painter.drawRoundedRect(30, y_offset, 64, 64, 8, 8)
            
            # Text placeholder (rectangle)
            painter.setBrush(base_color)
            painter.drawRoundedRect(30, y_offset + 75, 100, 16, 4, 4)
            
            y_offset += 140
            
            if y_offset > self.height():
                break
    
    def _draw_shimmer(self, painter: QPainter):
        """Draw animated shimmer gradient."""
        # Create gradient for shimmer effect
        gradient = QLinearGradient(self._offset, 0, self._offset + self._shimmer_width, 0)
        gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
        gradient.setColorAt(0.5, QColor(255, 255, 255, 30))  # Subtle white highlight
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())


class ShimmerOverlay(QWidget):
    """
    Overlay widget that shows shimmer effect over another widget.
    """
    
    def __init__(self, target_widget: QWidget, parent=None):
        super().__init__(parent)
        self.target_widget = target_widget
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()
        
        self.shimmer = ShimmerWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.shimmer)
    
    def show_overlay(self):
        """Show shimmer overlay over target widget."""
        self._update_geometry()
        self.show()
        self.shimmer.show()
    
    def hide_overlay(self):
        """Hide shimmer overlay."""
        self.hide()
        self.shimmer.hide()
    
    def _update_geometry(self):
        """Update overlay geometry to match target widget."""
        if self.target_widget:
            self.setGeometry(self.target_widget.rect())
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_geometry()
