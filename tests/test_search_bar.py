import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
import sys

# Ensure we have a QApplication instance
app = QApplication.instance() or QApplication(sys.argv)

from client.ui.search_bar import SearchBar
from client.api_manager import APIManager

class TestSearchBar(unittest.TestCase):
    def setUp(self):
        self.mock_api = MagicMock(spec=APIManager)
        self.search_bar = SearchBar(self.mock_api)
        # We don't need to mock translator as it's already initialized in __init__
        # and has a fallback mechanism, but we can if we want to isolate.

    def test_search_triggered_on_text_change_with_debounce(self):
        """Scenario: search_triggered signal should be emitted after debounce."""
        trigger_count = 0
        def on_triggered():
            nonlocal trigger_count
            trigger_count += 1
        
        self.search_bar.search_triggered.connect(on_triggered)
        
        # Change text
        self.search_bar.search_input.setText("test")
        self.assertEqual(trigger_count, 0, "Signal should be debounced")
        
        # Process events for 400ms (debounce is 350)
        from PyQt6.QtTest import QTest
        QTest.qWait(450)
        
        self.assertGreater(trigger_count, 0, "Signal should be emitted after debounce")

    def test_search_suggestion_trigger(self):
        """Scenario: suggestions should be fetched after typing 2+ chars."""
        with patch('client.ui.search_bar.SearchSuggestionWorker') as MockWorker:
            # Type 1 char
            self.search_bar.search_input.setText("a")
            from PyQt6.QtTest import QTest
            QTest.qWait(300) # debounce is 250
            MockWorker.assert_not_called()
            
            # Type 2nd char
            self.search_bar.search_input.setText("ab")
            QTest.qWait(300)
            MockWorker.assert_called()

    def test_filters_api_integration(self):
        """Scenario: verify filter getters."""
        self.search_bar.category_combo.addItem("Cat", 100)
        self.search_bar.category_combo.setCurrentIndex(1)
        
        self.search_bar.file_type_combo.addItem("Type", 200)
        self.search_bar.file_type_combo.setCurrentIndex(1)
        
        self.assertEqual(self.search_bar.category_id(), 100)
        self.assertEqual(self.search_bar.file_type_id(), 200)

    def test_clear_search_functionality(self):
        """Scenario: clicking clear action resets input."""
        self.search_bar.search_input.setText("hello world")
        self.search_bar.clear_search()
        self.assertEqual(self.search_bar.text(), "")

if __name__ == "__main__":
    unittest.main()
