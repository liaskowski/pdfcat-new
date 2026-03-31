from PyQt6.QtWidgets import QScrollArea, QWidget
from PyQt6.QtCore import QRect

class ViewportController:
    def __init__(self, scroll_area: QScrollArea, content_widget: QWidget):
        self.scroll_area = scroll_area
        self.content_widget = content_widget

    def get_visible_rect(self) -> QRect:
        """
        Returns the rectangle of the content_widget that is currently visible
        within the scroll area, in the content_widget's coordinate system.
        """
        if not self.content_widget or not self.scroll_area:
            return QRect()
            
        # method 1: using visibleRegion (most accurate for handling obscuring)
        region = self.content_widget.visibleRegion()
        if region.isEmpty():
            return QRect()
        return region.boundingRect()

    def get_viewport_size(self):
        """Returns the size of the scroll area's viewport."""
        return self.scroll_area.viewport().size()
