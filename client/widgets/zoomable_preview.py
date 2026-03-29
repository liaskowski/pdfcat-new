from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QPixmap, QPainter, QWheelEvent, QMouseEvent

class ZoomablePreview(QGraphicsView):
    """
    A widget that displays an image with support for:
    - Zoom (Ctrl + Wheel)
    - Pan (Middle Mouse or Space + Drag)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(Qt.GlobalColor.lightGray)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)
        
        self._zoom_factor = 1.15
        self._current_zoom = 1.0

    def set_pixmap(self, pixmap: QPixmap):
        self._scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        self._pixmap_item.setPixmap(pixmap)
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._current_zoom = 1.0

    def clear(self):
        self._pixmap_item.setPixmap(QPixmap())
        self._scene.update()

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Zoom
            if event.angleDelta().y() > 0:
                self.scale(self._zoom_factor, self._zoom_factor)
                self._current_zoom *= self._zoom_factor
            else:
                self.scale(1 / self._zoom_factor, 1 / self._zoom_factor)
                self._current_zoom /= self._zoom_factor
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            original_event = event.clone() # Needed? QGraphicsView handles DragMode logic usually
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
             self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # Reset to default if changed
        super().mouseReleaseEvent(event)
