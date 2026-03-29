"""
Tests for search functionality bug fix.

Bug: Search results were empty when searching by document content because:
1. Server correctly finds documents by content (DocumentIndex.content_text)
2. Client was re-filtering results using local cache
3. Local cache was empty for unindexed documents
4. All results were filtered out on client side

Fix: Trust server search results and only apply category/file_type/tag filters on client.
"""

import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
import sys


def setup_qapplication():
    """Create QApplication if it doesn't exist"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app

# Initialize at module load
setup_qapplication()


class TestSearchHandler(unittest.TestCase):
    """Test SearchHandler search result filtering"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock controller
        self.mock_controller = MagicMock()
        self.mock_controller.view = MagicMock()
        self.mock_controller.ui = MagicMock()
        self.mock_controller.api = MagicMock()
        self.mock_controller._me_id = 1
        self.mock_controller._me = {'role': 'user'}
        self.mock_controller.translator = MagicMock()
        self.mock_controller.translator.tr = lambda x: x
        self.mock_controller.search_handler = MagicMock()
        
        # Create mock UI components
        self.mock_controller.ui.search_bar = MagicMock()
        self.mock_controller.ui.search_bar.text.return_value = ""
        self.mock_controller.ui.search_bar.category_id.return_value = None
        self.mock_controller.ui.search_bar.file_type_id.return_value = None
        self.mock_controller.ui.nav_tree = MagicMock()
        self.mock_controller.ui.file_grid = MagicMock()
        self.mock_controller.ui.breadcrumbs = MagicMock()
        
        # Create mock document
        self.mock_doc = MagicMock()
        self.mock_doc.id = 1
        self.mock_doc.title = "Test Document"
        self.mock_doc.tags = ""
        self.mock_doc.category = None
        self.mock_doc.file_type = None
        
    def test_search_handler_initialization(self):
        """Test SearchHandler initializes correctly"""
        try:
            from client.ui.controllers.search_handler import SearchHandler
        except ImportError:
            self.skipTest("Client modules not available")
        
        handler = SearchHandler(self.mock_controller)
        
        self.assertIsNotNone(handler._cache)
        self.assertIsNone(handler._indexing_worker)
    
    def test_on_search_finished_with_empty_cache(self):
        """Test that search results are displayed even when cache is empty"""
        try:
            from client.ui.controllers.search_handler import SearchHandler
        except ImportError:
            self.skipTest("Client modules not available")
        
        handler = SearchHandler(self.mock_controller)
        
        # Mock IndexingWorker to avoid thread issues
        handler._indexing_worker = MagicMock()
        handler._indexing_worker.isRunning.return_value = False
        
        # Simulate server returning documents found by content search
        mock_docs = [
            MagicMock(id=1, title="Doc1", tags="", category=None, file_type=None),
            MagicMock(id=2, title="Doc2", tags="", category=None, file_type=None),
            MagicMock(id=3, title="Doc3", tags="", category=None, file_type=None),
        ]
        
        # Cache is empty (documents not yet indexed locally)
        self.assertEqual(len(handler._cache), 0)
        
        # Call _on_search_finished with empty query (show all)
        handler._on_search_finished(mock_docs, "")
        
        # Should display all documents
        self.mock_controller.ui.file_grid.rebuild_with_files.assert_called_once()
        displayed_docs = self.mock_controller.ui.file_grid.rebuild_with_files.call_args[0][0]
        self.assertEqual(len(displayed_docs), 3)
    
    def test_on_search_finished_with_content_search(self):
        """Test that content search results from server are trusted"""
        try:
            from client.ui.controllers.search_handler import SearchHandler
        except ImportError:
            self.skipTest("Client modules not available")
        
        handler = SearchHandler(self.mock_controller)
        handler._indexing_worker = MagicMock()
        handler._indexing_worker.isRunning.return_value = False
        
        # Simulate server returning documents found by content search
        # These documents have content in server response
        mock_docs = [
            MagicMock(
                id=1, 
                title="Untitled",  # Title doesn't match search
                tags="",
                category=None, 
                file_type=None,
                content="This document contains searchterm123"  # Content matches
            ),
        ]
        
        # Empty cache
        handler._cache = {}
        
        # Search for text that only appears in content, not title
        handler._on_search_finished(mock_docs, "searchterm123")
        
        # Should display the document (server found it by content)
        displayed_docs = self.mock_controller.ui.file_grid.rebuild_with_files.call_args[0][0]
        self.assertEqual(len(displayed_docs), 1)
    
    def test_on_search_finished_category_filter(self):
        """Test category filter is applied correctly"""
        try:
            from client.ui.controllers.search_handler import SearchHandler
        except ImportError:
            self.skipTest("Client modules not available")
        
        handler = SearchHandler(self.mock_controller)
        handler._indexing_worker = MagicMock()
        handler._indexing_worker.isRunning.return_value = False
        
        # Set up category filter
        self.mock_controller.ui.search_bar.category_id.return_value = 999
        
        mock_docs = [
            MagicMock(id=1, title="Doc1", tags="", 
                     category=MagicMock(id=999), file_type=None),
            MagicMock(id=2, title="Doc2", tags="", 
                     category=MagicMock(id=111), file_type=None),  # Wrong category
            MagicMock(id=3, title="Doc3", tags="", category=None, file_type=None),  # No category
        ]
        
        handler._on_search_finished(mock_docs, "")
        
        displayed_docs = self.mock_controller.ui.file_grid.rebuild_with_files.call_args[0][0]
        
        # Only first doc should be displayed (matches category 999)
        self.assertEqual(len(displayed_docs), 1)
        self.assertEqual(displayed_docs[0].id, 1)
    
    def test_on_search_finished_file_type_filter(self):
        """Test file type filter is applied correctly"""
        try:
            from client.ui.controllers.search_handler import SearchHandler
        except ImportError:
            self.skipTest("Client modules not available")
        
        handler = SearchHandler(self.mock_controller)
        handler._indexing_worker = MagicMock()
        handler._indexing_worker.isRunning.return_value = False
        
        # Set up file type filter
        self.mock_controller.ui.search_bar.file_type_id.return_value = 555
        
        mock_docs = [
            MagicMock(id=1, title="Doc1", tags="", category=None,
                     file_type=MagicMock(id=555)),
            MagicMock(id=2, title="Doc2", tags="", category=None,
                     file_type=MagicMock(id=222)),  # Wrong type
            MagicMock(id=3, title="Doc3", tags="", category=None, file_type=None),  # No type
        ]
        
        handler._on_search_finished(mock_docs, "")
        
        displayed_docs = self.mock_controller.ui.file_grid.rebuild_with_files.call_args[0][0]
        
        # Only first doc should be displayed (matches type 555)
        self.assertEqual(len(displayed_docs), 1)
        self.assertEqual(displayed_docs[0].id, 1)
    
    def test_on_search_finished_hashtag_filter(self):
        """Test hashtag search filter is applied on client side"""
        try:
            from client.ui.controllers.search_handler import SearchHandler
        except ImportError:
            self.skipTest("Client modules not available")
        
        handler = SearchHandler(self.mock_controller)
        handler._indexing_worker = MagicMock()
        handler._indexing_worker.isRunning.return_value = False
        
        mock_docs = [
            MagicMock(id=1, title="Doc1", tags="important work", 
                     category=None, file_type=None),
            MagicMock(id=2, title="Doc2", tags="personal", 
                     category=None, file_type=None),  # Wrong tag
            MagicMock(id=3, title="Doc3", tags="", 
                     category=None, file_type=None),  # No tags
        ]
        
        # Search by hashtag
        handler._on_search_finished(mock_docs, "#work")
        
        displayed_docs = self.mock_controller.ui.file_grid.rebuild_with_files.call_args[0][0]
        
        # Only first doc should be displayed (has "work" tag)
        self.assertEqual(len(displayed_docs), 1)
        self.assertEqual(displayed_docs[0].id, 1)
    
    def test_on_search_finished_updates_cache(self):
        """Test that search results update the cache"""
        try:
            from client.ui.controllers.search_handler import SearchHandler
        except ImportError:
            self.skipTest("Client modules not available")
        
        handler = SearchHandler(self.mock_controller)
        handler._indexing_worker = MagicMock()
        handler._indexing_worker.isRunning.return_value = False
        
        mock_docs = [
            MagicMock(
                id=1, 
                title="Cached Doc", 
                tags="", 
                category=None, 
                file_type=None,
                content="Some content here"
            ),
        ]
        
        handler._on_search_finished(mock_docs, "")
        
        # Cache should be updated
        self.assertIn(1, handler._cache)
        self.assertEqual(handler._cache[1]["title"], "Cached Doc")
        self.assertEqual(handler._cache[1]["content"], "Some content here")
    
    def test_on_search_finished_mixed_filters(self):
        """Test combination of category and file type filters"""
        try:
            from client.ui.controllers.search_handler import SearchHandler
        except ImportError:
            self.skipTest("Client modules not available")
        
        handler = SearchHandler(self.mock_controller)
        handler._indexing_worker = MagicMock()
        handler._indexing_worker.isRunning.return_value = False
        
        # Set up both filters
        self.mock_controller.ui.search_bar.category_id.return_value = 100
        self.mock_controller.ui.search_bar.file_type_id.return_value = 200
        
        mock_docs = [
            # Match both
            MagicMock(id=1, title="Doc1", tags="", 
                     category=MagicMock(id=100), file_type=MagicMock(id=200)),
            # Wrong category
            MagicMock(id=2, title="Doc2", tags="", 
                     category=MagicMock(id=999), file_type=MagicMock(id=200)),
            # Wrong file type
            MagicMock(id=3, title="Doc3", tags="", 
                     category=MagicMock(id=100), file_type=MagicMock(id=999)),
            # Match both
            MagicMock(id=4, title="Doc4", tags="", 
                     category=MagicMock(id=100), file_type=MagicMock(id=200)),
        ]
        
        handler._on_search_finished(mock_docs, "")
        
        displayed_docs = self.mock_controller.ui.file_grid.rebuild_with_files.call_args[0][0]
        
        # Should display docs 1 and 4 (both match)
        self.assertEqual(len(displayed_docs), 2)
        displayed_ids = [d.id for d in displayed_docs]
        self.assertIn(1, displayed_ids)
        self.assertIn(4, displayed_ids)


class TestSearchWorker(unittest.TestCase):
    """Test SearchWorker functionality"""
    
    def test_search_worker_initialization(self):
        """Test SearchWorker initializes correctly"""
        try:
            from client.utils.workers import SearchWorker
        except ImportError:
            self.skipTest("Client modules not available")
        
        mock_api = MagicMock()
        worker = SearchWorker(mock_api, query="test", view_mode="my")
        
        self.assertEqual(worker.query, "test")
        self.assertEqual(worker.view_mode, "my")
    
    def test_search_worker_with_empty_query(self):
        """Test SearchWorker handles empty query"""
        try:
            from client.utils.workers import SearchWorker
        except ImportError:
            self.skipTest("Client modules not available")
        
        mock_api = MagicMock()
        mock_api.list_documents.return_value = [
            MagicMock(id=1, title="Doc1"),
            MagicMock(id=2, title="Doc2"),
        ]
        
        worker = SearchWorker(mock_api, query=None, view_mode="my")
        
        results = []
        worker.finished.connect(lambda docs: results.append(docs))
        worker.run()
        
        # Should call list_documents for empty query
        mock_api.list_documents.assert_called_once()
        self.assertEqual(len(results), 1)
        self.assertEqual(len(results[0]), 2)
    
    def test_search_worker_with_query(self):
        """Test SearchWorker uses search_documents for query"""
        try:
            from client.utils.workers import SearchWorker
        except ImportError:
            self.skipTest("Client modules not available")
        
        mock_api = MagicMock()
        mock_api.search_documents.return_value = [
            MagicMock(id=1, title="Matching Doc"),
        ]
        
        worker = SearchWorker(mock_api, query="test", view_mode="my")
        
        results = []
        worker.finished.connect(lambda docs: results.append(docs))
        worker.run()
        
        # Should call search_documents for non-empty query
        mock_api.search_documents.assert_called_once_with(query="test")
        self.assertEqual(len(results), 1)
        self.assertEqual(len(results[0]), 1)


if __name__ == "__main__":
    unittest.main()
