import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import QCoreApplication
import sys
import os

# Ensure we have an application instance
app = QCoreApplication.instance() or QCoreApplication(sys.argv)

from client.utils.workers import SearchSuggestionWorker, IndexingWorker
from client.api.schemas import APIDocument

class TestSearchWorkers(unittest.TestCase):
    def setUp(self):
        self.mock_api = MagicMock()
        self.mock_handler = MagicMock()
        self.mock_handler._cache = {}

    def test_search_suggestion_worker(self):
        """Test that SearchSuggestionWorker calls the API and emits results."""
        query = "test"
        suggestions = ["test doc", "test file", "testing"]
        self.mock_api.get_suggestions.return_value = suggestions
        
        worker = SearchSuggestionWorker(self.mock_api, query)
        
        # Track signal emission
        emitted_suggestions = []
        def on_ready(s): emitted_suggestions.extend(s)
        worker.suggestions_ready.connect(on_ready)
        
        # Run worker logic
        worker.run()
        
        self.mock_api.get_suggestions.assert_called_with(query)
        self.assertEqual(emitted_suggestions, suggestions)

    @patch('tempfile.mkstemp')
    @patch('os.remove')
    @patch('pathlib.Path.write_bytes')
    def test_indexing_worker(self, mock_write, mock_remove, mock_mkstemp):
        """Test that IndexingWorker downloads and indexes documents."""
        # Setup mock file path
        mock_mkstemp.return_value = (99, "temp.pdf")
        
        # We need a proper mock of APIDocument for the IndexingWorker to use
        doc = MagicMock(spec=APIDocument)
        doc.id = 1
        doc.encryption_key = "key"
        
        self.mock_api.download_document.return_value = b"pdf content"
        self.mock_handler.index_document_content.return_value = "extracted text"
        self.mock_handler._cache = {} # Ensure cache check passes
        
        worker = IndexingWorker(self.mock_api, self.mock_handler, [doc])
        
        # Track signal
        indexed_signals = []
        worker.document_indexed.connect(lambda id, text: indexed_signals.append((id, text)))
        
        # Run
        worker.run()
        
        # Verify workflow
        self.mock_api.download_document.assert_called_with(1)
        self.mock_handler.index_document_content.assert_called_with(1, "temp.pdf", password="key")
        self.assertEqual(indexed_signals, [(1, "extracted text")])
        mock_remove.assert_called_with("temp.pdf")

if __name__ == "__main__":
    unittest.main()
