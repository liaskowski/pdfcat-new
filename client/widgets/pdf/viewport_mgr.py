from PyQt6.QtWidgets import QScrollArea, QWidget
from PyQt6.QtCore import QRect
import fitz

class ViewportManager:
    def __init__(self, scroll_area: QScrollArea, content_widget: QWidget):
        self.scroll_area = scroll_area
        self.content_widget = content_widget

    def get_visible_region(self) -> QRect:
        """Returns the visible QRect of the content_widget."""
        if not self.content_widget:
            return QRect()
        region = self.content_widget.visibleRegion()
        if region.isEmpty():
            return QRect()
        return region.boundingRect()

    def get_render_params(self, page: fitz.Page, zoom: float, rotation: int) -> tuple[fitz.Matrix, fitz.Rect, QRect]:
        """
        Calculates params for a SINGLE viewport region.
        Page rotation is handled by the page object itself.
        """
        visible_rect = self.get_visible_region()
        if visible_rect.isEmpty():
            visible_rect = QRect(0, 0, 800, 600)
            
        # Add padding for smooth scrolling
        padding = 200
        render_rect = visible_rect.adjusted(-padding, -padding, padding, padding)
        
        content_rect = self.content_widget.rect()
        render_rect = render_rect.intersected(content_rect)
        
        # 1. Strict integer snap for screen pixels
        rx, ry = int(render_rect.x()), int(render_rect.y())
        rw, rh = int(render_rect.width()), int(render_rect.height())
        render_rect = QRect(rx, ry, rw, rh)

        # Matrix now only needs to handle scaling because page.set_rotation 
        # already adjusted the coordinate system of the page object.
        matrix = fitz.Matrix(zoom, zoom)
        inv_matrix = ~matrix
        
        # 2. Map screen pixels to PDF points
        pix_rect = fitz.Rect(float(rx), float(ry), float(rx + rw), float(ry + rh))
        clip_rect = pix_rect * inv_matrix
            
        return matrix, clip_rect, render_rect
