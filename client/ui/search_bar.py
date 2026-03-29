from PyQt6.QtCore import pyqtSignal, QTimer, QStringListModel, Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QCompleter,
)
import qtawesome as qta

from ..api_manager import APIManager
from ..themes import ThemeManager
from ..utils.workers import SearchSuggestionWorker
from ..utils.translator import Translator

class SearchBar(QFrame):
    """
    A widget containing the search input, category and file type filters.
    """
    search_triggered = pyqtSignal()
    shift_enter_pressed = pyqtSignal()

    def __init__(self, api: APIManager, parent=None):
        super().__init__(parent)
        self.api = api
        self.translator = Translator()
        self.theme_manager = ThemeManager()
        self.setObjectName("card")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # --- Completer and Timers ---
        self._suggestion_model = QStringListModel()
        self._completer = QCompleter(self._suggestion_model, self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setMaxVisibleItems(10)  # Show up to 10 suggestions
        
        # Set popup properties for better visibility
        popup = self._completer.popup()
        popup.setWindowFlags(popup.windowFlags() | Qt.WindowType.FramelessWindowHint)
        popup.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(350)  # Debounce for main search

        self._suggestion_timer = QTimer(self)
        self._suggestion_timer.setSingleShot(True)
        self._suggestion_timer.setInterval(150)  # Faster debounce for suggestions (150ms)

        self._suggestion_worker: SearchSuggestionWorker | None = None
        self._last_suggestion_query = ""  # Track last query to prevent stale results

        # --- Widgets ---
        self.search_input = QLineEdit()
        self.search_input.setObjectName("input")
        self.search_input.setPlaceholderText(self.translator.tr("main.search_placeholder"))
        self.search_input.setCompleter(self._completer)
        
        # Add clear action
        self.clear_action = self.search_input.addAction(
            qta.icon('fa5s.times', color=self.theme_manager.get_color("text_secondary")),
            QLineEdit.ActionPosition.TrailingPosition
        )
        self.clear_action.setVisible(False)
        self.clear_action.triggered.connect(self.clear_search)
        self.search_input.textChanged.connect(lambda t: self.clear_action.setVisible(bool(t)))

        self.category_combo = QComboBox()
        self.category_combo.setObjectName("input")
        self.category_combo.setMinimumWidth(120)

        self.file_type_combo = QComboBox()
        self.file_type_combo.setObjectName("input")
        self.file_type_combo.setMinimumWidth(120)

        layout.addWidget(self.search_input, 1)
        layout.addWidget(self.category_combo, 0)
        layout.addWidget(self.file_type_combo, 0)

        self._connect_signals()

    def clear_search(self):
        self.search_input.clear()
        self._last_suggestion_query = ""
        self.search_triggered.emit()

    def __del__(self):
        """Cleanup workers on destruction."""
        if hasattr(self, '_suggestion_worker') and self._suggestion_worker:
            if self._suggestion_worker.isRunning():
                self._suggestion_worker.wait(1000)  # Wait up to 1s

    def _connect_signals(self):
        self._search_timer.timeout.connect(self.search_triggered)
        self._suggestion_timer.timeout.connect(self._fetch_suggestions)

        self.search_input.textChanged.connect(self._suggestion_timer.start)
        self.search_input.textChanged.connect(self._search_timer.start)
        self.search_input.returnPressed.connect(self.search_triggered)

        # Trigger search immediately when a suggestion is selected
        self._completer.activated.connect(self._on_completer_activated)

        self.category_combo.currentIndexChanged.connect(self.search_triggered)
        self.file_type_combo.currentIndexChanged.connect(self.search_triggered)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.shift_enter_pressed.emit()
                return
        super().keyPressEvent(event)

    def _on_completer_activated(self, text: str):
        self._search_timer.stop() # Cancel pending debounce search
        self.search_triggered.emit()

    def text(self) -> str:
        return self.search_input.text().strip()

    def category_id(self) -> int | None:
        data = self.category_combo.currentData()
        return int(data) if data is not None else None

    def file_type_id(self) -> int | None:
        data = self.file_type_combo.currentData()
        return int(data) if data is not None else None
    
    def set_completer_style(self, style_sheet: str):
        self._completer.popup().setStyleSheet(style_sheet)

    def _fetch_suggestions(self):
        query = self.search_input.text().strip()

        # ONLY fetch suggestions for 2+ characters
        if len(query) < 2:
            self._suggestion_model.setStringList([])
            return

        # Store current query to prevent stale results
        self._last_suggestion_query = query

        # Gracefully stop previous worker
        if hasattr(self, '_suggestion_worker') and self._suggestion_worker:
            try:
                if self._suggestion_worker.isRunning():
                    self._suggestion_worker.wait(500)  # Wait up to 0.5s
            except RuntimeError:
                # Worker was already deleted - that's fine
                pass
        
        # Create and start new worker
        self._suggestion_worker = SearchSuggestionWorker(self.api, query, limit=10)
        self._suggestion_worker.suggestions_ready.connect(self._on_suggestions_ready)
        self._suggestion_worker.error.connect(lambda e: None)  # Silently ignore errors
        self._suggestion_worker.finished.connect(self._suggestion_worker.deleteLater)
        self._suggestion_worker.start()

    def _on_suggestions_ready(self, suggestions: list[str]):
        """Update suggestions list."""
        # Only update if query hasn't changed (prevent stale results)
        current_query = self.search_input.text().strip()
        if len(current_query) >= 2 and current_query == self._last_suggestion_query:
            self._suggestion_model.setStringList(suggestions)
            # Force popup to show if there are suggestions
            if suggestions and self.search_input.hasFocus():
                # Use QTimer to ensure popup shows after model update
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(10, lambda: self._completer.complete())

    def populate_filter_combos(self, categories: list, file_types: list):
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem(self.translator.tr("main.all_categories"), None)
        for cat in categories:
            self.category_combo.addItem(cat.name, cat.id)
        self.category_combo.blockSignals(False)

        self.file_type_combo.blockSignals(True)
        self.file_type_combo.clear()
        self.file_type_combo.addItem(self.translator.tr("main.all_file_types"), None)
        for ft in file_types:
            self.file_type_combo.addItem(ft.name, ft.id)
        self.file_type_combo.blockSignals(False)
        
        # Reset suggestion query when filters change
        self._last_suggestion_query = ""

