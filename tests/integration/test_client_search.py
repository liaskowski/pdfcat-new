import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
import sys

# Ensure we have a QApplication instance for tests that might touch UI logic
app = QApplication.instance() or QApplication(sys.argv)

from client.ui.controllers.search_handler import SearchHandler
from client.api.schemas import APIDocument, APICategory, APIFileType

class TestClientSearch(unittest.TestCase):
    def setUp(self):
        # Mocking the dependencies
        self.mock_view = MagicMock()
        self.mock_ui = MagicMock()
        self.mock_api = MagicMock()
        self.mock_controller = MagicMock()
        
        self.mock_controller.view = self.mock_view
        self.mock_controller.ui = self.mock_ui
        self.mock_controller.api = self.mock_api
        self.mock_controller.translator.tr.side_effect = lambda x: x
        self.mock_controller._me_id = 1

        # SearchBar mocks
        self.mock_ui.search_bar.text.return_value = ""
        self.mock_ui.search_bar.category_id.return_value = None
        self.mock_ui.search_bar.file_type_id.return_value = None
        
        # FileGrid mocks
        self.mock_ui.file_grid.rebuild_with_files = MagicMock()

        self.handler = SearchHandler(self.mock_controller)

    def create_mock_doc(self, **kwargs):
        defaults = {
            "id": 1,
            "title": "Title",
            "filename": "file.pdf",
            "upload_date": "2023-01-01",
            "owner_id": 1,
            "category": None,
            "file_type": None,
            "is_private": False,
            "is_public": False,
            "is_public_edit": False,
            "is_read_only": False,
            "content": None
        }
        defaults.update(kwargs)
        return APIDocument(**defaults)

    def test_fetch_from_server_basic_search(self):
        """Scenario: User enters text and triggers search."""
        query = "test query"
        self.mock_ui.search_bar.text.return_value = query
        
        # Mock API response
        mock_docs = [
            self.create_mock_doc(id=1, title="Test Doc 1"),
            self.create_mock_doc(id=2, title="Other Doc")
        ]
        self.mock_api.search_documents.return_value = mock_docs
        
        self.handler.fetch_from_server()
        
        # Verify API called correctly
        self.mock_api.search_documents.assert_called_once_with(query=query)
        
        # Verify grid rebuild with filtered results
        rebuild_args = self.mock_ui.file_grid.rebuild_with_files.call_args[0][0]
        self.assertEqual(len(rebuild_args), 1)
        self.assertEqual(rebuild_args[0].title, "Test Doc 1")

    def test_fetch_from_server_with_filters(self):
        """Scenario: Search with category and file type filters."""
        self.mock_ui.search_bar.text.return_value = ""
        self.mock_ui.search_bar.category_id.return_value = 10
        self.mock_ui.search_bar.file_type_id.return_value = 20
        
        # Mock docs with different categories/types
        cat10 = APICategory(id=10, name="Cat 10")
        type20 = APIFileType(id=20, name="Type 20")
        
        mock_docs = [
            self.create_mock_doc(id=1, title="Match", category=cat10, file_type=type20),
            self.create_mock_doc(id=2, title="No Match Cat", category=None, file_type=type20),
            self.create_mock_doc(id=3, title="No Match Type", category=cat10, file_type=None)
        ]
        self.mock_api.list_documents.return_value = mock_docs
        
        self.handler.fetch_from_server(view_mode="my")
        
        rebuild_args = self.mock_ui.file_grid.rebuild_with_files.call_args[0][0]
        self.assertEqual(len(rebuild_args), 1)
        self.assertEqual(rebuild_args[0].title, "Match")

    def test_empty_results_handling(self):
        """Scenario: Search returns no results."""
        self.mock_ui.search_bar.text.return_value = "nonexistent"
        self.mock_api.search_documents.return_value = []
        
        self.handler.fetch_from_server()
        
        self.mock_ui.file_grid.rebuild_with_files.assert_called_once_with([], unittest.mock.ANY, unittest.mock.ANY)

    def test_search_error_handling(self):
        """Scenario: API returns an error (e.g., timeout)."""
        self.mock_ui.search_bar.text.return_value = "search"
        self.mock_api.search_documents.side_effect = Exception("Network Error")
        
        self.handler.fetch_from_server()
        
        # Verify error dialog was shown
        self.mock_controller._show_error.assert_called_once()
        self.assertIn("Network Error", self.mock_controller._show_error.call_args[0][1])

    def test_cache_usage(self):
        """Scenario: Search handler updates and uses its local cache."""
        self.mock_ui.search_bar.text.return_value = "cached"
        doc = self.create_mock_doc(id=1, title="Cached Title", content="Some content")
        self.mock_api.search_documents.return_value = [doc]
        
        self.handler.fetch_from_server()
        
        # Check if cache was updated
        self.assertIn(1, self.handler._cache)
        self.assertEqual(self.handler._cache[1]["title"], "Cached Title")
        
        # Subsequent search should match on content from cache
        self.mock_ui.search_bar.text.return_value = "content"
        self.mock_api.search_documents.return_value = [doc]
        
        self.handler.fetch_from_server()
        rebuild_args = self.mock_ui.file_grid.rebuild_with_files.call_args[0][0]
        self.assertEqual(len(rebuild_args), 1)

    @patch('client.ui.controllers.search_handler.IndexingWorker')
    def test_background_indexing_start(self, MockWorker):
        """Scenario: Indexing worker starts after fetching documents."""
        self.mock_ui.search_bar.text.return_value = ""
        mock_docs = [self.create_mock_doc(id=1, title="Doc")]
        self.mock_api.list_documents.return_value = mock_docs
        
        self.handler.fetch_from_server(view_mode="my")
        
        # Verify IndexingWorker was created and started
        MockWorker.assert_called_once()
        MockWorker.return_value.start.assert_called_once()

if __name__ == "__main__":
    unittest.main()
