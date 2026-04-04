from typing import Optional, TYPE_CHECKING, Dict, Any
from PyQt6.QtCore import Qt, QStandardPaths, QMutex, QMutexLocker
import fitz
import json
import os

from ...api.schemas import APIUser, APIFolder
if TYPE_CHECKING:
    from .main_controller import MainController
from ...utils.workers import IndexingWorker

class SearchHandler:
    def __init__(self, controller: "MainController"):
        self.controller = controller
        self.view = controller.view
        self.ui = controller.ui
        self.api = controller.api
        self._cache: Dict[int, Dict[str, Any]] = {}
        self._indexing_worker: Optional[IndexingWorker] = None
        self._cache_mutex = QMutex()  # Thread-safe cache access
        
        # Folder content cache to avoid re-fetching
        self._folder_cache: Dict[str, List] = {}  # key: (view_mode, folder_id, owner_id)
        self._folder_cache_mutex = QMutex()
        
        # Debounce timer for rapid folder switches
        from PyQt6.QtCore import QTimer
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(150)  # 150ms debounce
        self._debounce_timer.timeout.connect(self._execute_fetch)
        self._pending_fetch_params = None
        self.current_view_params = ("my", None, None) # (view_mode, folder_id, owner_id)

        # Load persistent document cache
        self._load_cache()

    def index_document_content(self, doc_id: int, file_path: str, password: str = None) -> str:
        """Extracts text from PDF or falls back to OCR."""
        text = ""
        try:
            doc = fitz.open(file_path)
            if password:
                doc.authenticate(password)
                
            text = chr(12).join([page.get_text() for page in doc])
            doc.close()
            
            if not text.strip():
                # Fallback: try to get OCR text from server or metadata if available
                # For now, we just return empty if no text in PDF
                pass
        except Exception as e:
            print(f"Indexing error for {file_path}: {e}")
            
        if doc_id not in self._cache:
            self._cache[doc_id] = {}
        self._cache[doc_id]["content"] = text
        return text

    def fetch_from_server(self, view_mode=None, folder_id=None, owner_id=None, load_all=True) -> None:
        """Schedule fetch with debouncing to avoid rapid re-fetches."""
        # Update current view params for auto-refresh
        self.current_view_params = (view_mode, folder_id, owner_id)

        # 1. If view mode changed, clear folder cache to ensure strict privacy
        if self._pending_fetch_params:
            old_mode = self._pending_fetch_params[0]
            if old_mode != view_mode:
                with QMutexLocker(self._folder_cache_mutex):
                    self._folder_cache.clear()

        # Store parameters for debounced execution
        self._pending_fetch_params = (view_mode, folder_id, owner_id, load_all)
        
        # Restart debounce timer
        self._debounce_timer.start()
    
    def _execute_fetch(self):
        """Execute the actual fetch after debounce period."""
        if self._pending_fetch_params is None:
            return
            
        # Check if API has authentication token
        if not self.api.token:
            print("SearchHandler: No authentication token, skipping fetch")
            return
            
        view_mode, folder_id, owner_id, load_all = self._pending_fetch_params
        self._pending_fetch_params = None
        
        # Update breadcrumbs for immediate feedback
        selected_items = self.ui.nav_tree.selectedItems()
        if selected_items:
            item = selected_items[0]
            path_segments = []
            temp_item = item
            while temp_item:
                path_segments.insert(0, temp_item.text(0))
                temp_item = temp_item.parent()
            self.ui.breadcrumbs.setText(" > ".join(path_segments))
        
        # Check cache first (only for non-search queries and when NOT loading all)
        # IF load_all is True, we want FRESH data from server (used by auto-refresh)
        cache_key = f"{view_mode}_{folder_id}_{owner_id}"
        query = self.ui.search_bar.text()

        with QMutexLocker(self._folder_cache_mutex):
            # If we're NOT searching and NOT forcing a full reload (auto-refresh), use cache
            if not query and cache_key in self._folder_cache and not load_all:
                # Use cached data - instant response!
                cached_docs = self._folder_cache[cache_key]
                self._update_grid_with_docs(cached_docs)
                return
        
        # Not in cache or refresh requested - fetch from server
        
        # Stop any pending search
        if hasattr(self, '_search_worker') and self._search_worker.isRunning():
            self._search_worker.terminate()
            self._search_worker.wait()

        # Show loading only for manual triggers, not for background sync
        if not hasattr(self.controller, 'refresh_timer') or not self.controller.refresh_timer.isActive():
             self.view.statusBar().showMessage("Loading folder contents...", 2000)

        from ...utils.workers import SearchWorker
        self._search_worker = SearchWorker(
            self.api, 
            query, 
            view_mode, 
            folder_id, 
            owner_id,
            load_all=True # Always load all when fetching from server to ensure sync
        )
        self._search_worker.finished.connect(lambda docs: self._on_search_finished(docs, query, cache_key, view_mode))
        self._search_worker.error.connect(lambda e: self.controller._show_error(self.controller.translator.tr("common.error"), str(e)))
        self._search_worker.start()

    def _on_search_finished(self, documents, query, cache_key=None, view_mode=None):
        query_lower = query.lower() if query else ""
        print(f"🔍 DEBUG: Client received {len(documents)} docs from server for mode={view_mode}")

        # Thread-safe cache update
        with QMutexLocker(self._cache_mutex):
            # Update local cache with documents from server
            for d in documents:
                if d.id not in self._cache:
                    self._cache[d.id] = {"title": d.title, "content": d.content or ""}
                else:
                    self._cache[d.id]["title"] = d.title
                    if d.content:
                        self._cache[d.id]["content"] = d.content

        category_id = self.ui.search_bar.category_id()
        file_type_id = self.ui.search_bar.file_type_id()

        filtered = []
        for d in documents:
            # SAFETY FILTER: Client-side privacy enforcement
            # If we are in 'community' mode, NEVER show private docs
            if view_mode == "community":
                if d.is_private:
                    print(f"   - Rejected doc {d.id} ('{d.title}'): is_private is True")
                    continue
                if not (d.is_public or d.is_public_edit):
                    print(f"   - Rejected doc {d.id} ('{d.title}'): is_public is False")
                    continue
            
            # If we are in 'my' mode, only show my docs (unless admin)
            elif view_mode == "my":
                if d.owner_id != self.controller._me_id and self.controller._me.get("role") != "admin":
                    continue

            if category_id is not None and (not d.category or d.category.id != category_id):
                continue
            if file_type_id is not None and (not d.file_type or d.file_type.id != file_type_id):
                continue

            # Only apply tag filter on client side (hashtag search)
            if query_lower.startswith("#") and len(query_lower) > 1:
                tag_to_find = query_lower[1:]
                if not (d.tags and tag_to_find in d.tags.lower()):
                    continue

            filtered.append(d)

        print(f"🔍 DEBUG: Client filtered list contains {len(filtered)} docs")

        # Cache the filtered results for instant switching
        if cache_key:
            with QMutexLocker(self._folder_cache_mutex):
                self._folder_cache[cache_key] = filtered

        # Update grid
        self._update_grid_with_docs(filtered)

        # Start background indexing for newly fetched documents
        if not query and not category_id and not file_type_id:
            self.start_indexing(filtered)
    
    def _update_grid_with_docs(self, documents):
        """Update file grid with documents (non-blocking)."""
        # Skip rebuild if document set hasn't changed (prevents sort/filter reset on auto-refresh)
        if self.ui.file_grid.has_same_documents(documents):
            return

        # Ensure UI icon is handled
        pdf_icon = self.view._make_pdf_icon(64) if hasattr(self.view, '_make_pdf_icon') else None

        # Clear loading state
        self.ui.file_grid.set_loading(False)

        # Rebuild grid with files (now uses lazy loading)
        self.ui.file_grid.rebuild_with_files(documents, pdf_icon)
    
    def start_indexing(self, documents):
        """Start background indexing of documents with safeguards."""
        if not documents:
            return

        # 1. Stop existing worker if running
        if self._indexing_worker and self._indexing_worker.isRunning():
            self._indexing_worker.stop()
            self._indexing_worker.wait(500) # Give it 0.5s to stop gracefully

        # 2. Filter out already cached documents locally before starting thread
        # to prevent even spawning the thread if nothing to do
        to_index = []
        with QMutexLocker(self._cache_mutex):
            for d in documents:
                cached = self._cache.get(d.id)
                if not cached or not cached.get("content"):
                    to_index.append(d)
        
        if not to_index:
            return

        # 3. Start new worker with filtered list
        self._indexing_worker = IndexingWorker(self.api, self, to_index)
        self._indexing_worker.start()

    def load_filter_combos(self):
        try:
            categories = self.api.get_categories()
            file_types = self.api.get_file_types()
            self.ui.search_bar.populate_filter_combos(categories, file_types)
        except Exception as e:
            self.controller._show_error(self.controller.translator.tr("common.error"), f"{self.controller.translator.tr('manage.loading_failed')}: {e}")

    def _load_cache(self):
        """Load document metadata cache from disk"""
        cache_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
        cache_file = os.path.join(cache_dir, "pdflib", "document_cache.json")
        
        if not os.path.exists(cache_file):
            return
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                loaded_cache = json.load(f)
            
            # Convert string keys back to int
            for doc_id_str, data in loaded_cache.items():
                self._cache[int(doc_id_str)] = data
            
            print(f"[INFO] Loaded {len(self._cache)} documents from cache")
        except Exception as e:
            print(f"[WARNING] Failed to load document cache: {e}")
    
    def _save_cache(self):
        """Save document metadata cache to disk"""
        try:
            cache_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
            cache_path = os.path.join(cache_dir, "pdflib")
            
            if not os.path.exists(cache_path):
                os.makedirs(cache_path, exist_ok=True)
            
            cache_file = os.path.join(cache_path, "document_cache.json")
            
            # Serialize cache (exclude large 'content' field to save space)
            clean_cache = {}
            for doc_id, data in self._cache.items():
                clean_cache[str(doc_id)] = {
                    'title': data.get('title', ''),
                    'filename': data.get('filename', ''),
                    # Skip 'content' - too large for persistent cache
                }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(clean_cache, f, indent=2)
            
            print(f"[INFO] Saved {len(clean_cache)} documents to cache")
        except Exception as e:
            print(f"[WARNING] Failed to save document cache: {e}")

