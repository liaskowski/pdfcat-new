from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QWidget
from typing import Callable

class ShortcutManager:
    def __init__(self, parent: QWidget):
        self.parent = parent

    def register(self, key_sequence: str, callback: Callable):
        QShortcut(QKeySequence(key_sequence), self.parent).activated.connect(callback)

    def setup_standard_shortcuts(self, cut_cb: Callable, copy_cb: Callable, paste_cb: Callable, rename_cb: Callable = None):
        self.register("Ctrl+X", cut_cb)
        self.register("Ctrl+C", copy_cb)
        self.register("Ctrl+V", paste_cb)
        if rename_cb:
            self.register("F2", rename_cb)
