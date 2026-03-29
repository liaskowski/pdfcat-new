import os
import tempfile
import fitz
import secrets
from pathlib import Path
from typing import Optional, Any, TYPE_CHECKING

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QThreadPool, QRunnable, QObject
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QInputDialog, QProgressDialog, QDialog

from ...api.schemas import APIDocument, APIFolder
if TYPE_CHECKING:
    from .main_controller import MainController

from ..upload_dialog import UploadDialog
from ..dialogs.batch_upload_dialog import BatchUploadDialog
from ..viewer_window import FileViewerWindow
from ...utils.workers import UploadWorker, OCRWorker
from ...utils.logger import log_debug, log_error


class UploadSignalEmitter(QObject):
    """Signal emitter for upload tasks."""
    progress = pyqtSignal(int, int)  # current, total
    log_message = pyqtSignal(str)
    file_complete = pyqtSignal(str)  # filename
    file_error = pyqtSignal(str)  # error message


class UploadTask(QRunnable):
    """Single file upload task for thread pool with duplicate detection."""
    
    def __init__(self, api, file_path: str, target_folder_id: Optional[int], 
                 is_public: bool, signal_emitter: UploadSignalEmitter, task_id: int,
                 existing_docs: list = None):
        super().__init__()
        self.api = api
        self.file_path = file_path
        self.target_folder_id = target_folder_id
        self.is_public = is_public
        self.signal_emitter = signal_emitter
        self.task_id = task_id
        self.existing_docs = existing_docs or []
        self._stop_flag = False
    
    def run(self):
        """Execute single file upload with duplicate check."""
        try:
            filename = Path(self.file_path).name
            log_debug("upload_task", f"Task {self.task_id} STARTED: {filename}")
            self.signal_emitter.log_message.emit(f"Checking: {filename}")
            
            # Check for duplicates
            if self.existing_docs:
                from ...services.duplicate_detector import DuplicateDetector
                detector = DuplicateDetector(self.api)
                similar_files = detector.check_duplicates(self.file_path, self.existing_docs)
                
                if similar_files:
                    log_debug("upload_task", f"Task {self.task_id} found {len(similar_files)} similar files")
                    # Emit signal for UI to handle duplicate
                    # For now, we'll just skip if high similarity found
                    if detector.should_show_dialog(similar_files):
                        log_debug("upload_task", f"Task {self.task_id} skipped due to duplicate")
                        self.signal_emitter.file_error.emit(
                            f"Skipped '{filename}': Potential duplicate detected"
                        )
                        return
            
            self.signal_emitter.log_message.emit(f"Uploading: {filename}")
            
            # Encrypt file
            log_debug("upload_task", f"Task {self.task_id} encrypting: {filename}")
            encryption_key = secrets.token_urlsafe(16)
            doc = fitz.open(self.file_path)
            fd, temp_path = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)

            doc.save(
                temp_path,
                encryption=fitz.PDF_ENCRYPT_AES_256,
                owner_pw=encryption_key,
                user_pw=encryption_key
            )
            doc.close()
            log_debug("upload_task", f"Task {self.task_id} encrypted: {filename}")

            # Upload
            log_debug("upload_task", f"Task {self.task_id} uploading: {filename}")
            self.api.upload_file(
                file_path=temp_path,
                title=Path(self.file_path).stem,
                category_id=None,
                file_type_id=None,
                use_ocr=True,
                is_private=not self.is_public,
                is_public=self.is_public,
                is_public_edit=False,
                is_read_only=False,
                encryption_key=encryption_key,
                notes='',
                tags='',
                folder_id=self.target_folder_id,
            )
            log_debug("upload_task", f"Task {self.task_id} COMPLETED: {filename}")
            
            # Cleanup
            os.remove(temp_path)
            
            self.signal_emitter.file_complete.emit(filename)
            
        except Exception as e:
            log_error("upload_task", f"Task {self.task_id} ERROR: {e}", exc_info=True)
            self.signal_emitter.file_error.emit(f"Error uploading {Path(self.file_path).name}: {str(e)}")


class BatchUploadWorker(QThread):
    """Worker thread for managing parallel uploads with duplicate detection."""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)  # current, total
    log_message = pyqtSignal(str)
    duplicate_found = pyqtSignal(object, list)  # file_path, [(doc, score), ...]

    def __init__(self, api, paths: list[str], target_folder_id: Optional[int], 
                 is_public: bool, max_workers: int = 3, check_duplicates: bool = True):
        super().__init__()
        self.api = api
        self.paths = paths
        self.target_folder_id = target_folder_id
        self.is_public = is_public
        self.max_workers = max_workers
        self.check_duplicates = check_duplicates
        self._stop_flag = False
        self._completed = 0
        self._failed = 0
        self._skipped = 0
        
    def run(self):
        """Manage parallel uploads using QThreadPool."""
        from PyQt6.QtCore import QMutex, QMutexLocker
        
        log_debug("batch_upload_worker", f"Starting with {len(self.paths)} files, {self.max_workers} workers")
        total = len(self.paths)
        
        # Create signal emitter (must be done in thread)
        self.signal_emitter = UploadSignalEmitter()
        self.signal_emitter.file_complete.connect(self._on_file_complete)
        self.signal_emitter.file_error.connect(self._on_file_error)
        
        # Create thread pool
        pool = QThreadPool()
        pool.setMaxThreadCount(self.max_workers)
        log_debug("batch_upload_worker", f"ThreadPool created with {pool.maxThreadCount()} threads")
        
        # Get existing documents for duplicate check
        existing_docs = []
        if self.check_duplicates:
            try:
                existing_docs = self.api.list_documents(limit=1000)
                log_debug("batch_upload_worker", f"Loaded {len(existing_docs)} existing docs for duplicate check")
            except Exception as e:
                log_debug("batch_upload_worker", f"Failed to load existing docs: {e}")
        
        # Submit all tasks
        for i, file_path in enumerate(self.paths):
            if self._stop_flag:
                break
            
            task = UploadTask(
                self.api, 
                file_path, 
                self.target_folder_id, 
                self.is_public,
                self.signal_emitter,
                task_id=i+1,
                existing_docs=existing_docs if self.check_duplicates else []
            )
            log_debug("batch_upload_worker", f"Submitting task {i+1}/{total}")
            pool.start(task)
        
        # Wait for all tasks to complete
        pool.waitForDone()
        
        log_debug("batch_upload_worker", f"All tasks complete. Success: {self._completed}, Failed: {self._failed}, Skipped: {self._skipped}")
        self.progress.emit(total, total)
        log_debug("batch_upload_worker", "Emitting finished signal")
        self.finished.emit()
        log_debug("batch_upload_worker", "Finished signal emitted")
    
    def _on_file_complete(self, filename: str):
        """Called when a file upload completes."""
        self._completed += 1
        self.progress.emit(self._completed + self._failed + self._skipped, len(self.paths))
        log_debug("batch_upload_worker", f"File complete: {filename} ({self._completed}/{len(self.paths)})")
    
    def _on_file_error(self, error_msg: str):
        """Called when a file upload fails."""
        self._failed += 1
        self.progress.emit(self._completed + self._failed + self._skipped, len(self.paths))
        self.error.emit(error_msg)
    
    def _on_file_skipped(self, filename: str):
        """Called when a file is skipped (duplicate cancelled)."""
        self._skipped += 1
        self.progress.emit(self._completed + self._failed + self._skipped, len(self.paths))

    def stop(self):
        self._stop_flag = True


class FileOperations:
    def __init__(self, controller: "MainController"):
        self.controller = controller
        self.view = controller.view
        self.ui = controller.ui
        self.api = controller.api
        self._ocr_temp_path: Optional[str] = None

    def on_ocr_clicked(self):
        """Handles the OCR button click. Downloads the current document and runs OCR."""
        doc = self.ui.preview_panel._document
        if not doc:
            self.controller.update_status("No document selected for OCR")
            return

        self.controller.update_status("Downloading document for OCR...", 0)

        try:
            content = self.api.download_document(doc.id)
            suffix = Path(doc.filename).suffix if doc.filename else ".pdf"

            fd, self._ocr_temp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            Path(self._ocr_temp_path).write_bytes(content)

            self.controller.update_status("Recognizing text...", 0)
            self.ocr_worker = OCRWorker(self.api, self._ocr_temp_path)
            self.ocr_worker.finished.connect(self._on_ocr_finished)
            self.ocr_worker.error.connect(self._on_ocr_error)
            self.ocr_worker.start()

        except Exception as e:
            self.controller._show_error("OCR Start Failed", str(e))
            self.controller.update_status("Error starting OCR")

    def _on_ocr_finished(self, text: str):
        self.controller.update_status("OCR Complete")
        from PyQt6.QtWidgets import QTextEdit, QVBoxLayout, QDialogButtonBox
        d = QDialog(self.view)
        d.setWindowTitle("OCR Result")
        d.resize(600, 400)
        l = QVBoxLayout(d)
        t = QTextEdit()
        t.setPlainText(text)
        l.addWidget(t)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btns.accepted.connect(d.accept)
        l.addWidget(btns)
        d.exec()
        self._cleanup_ocr_temp()

    def _on_ocr_error(self, error_msg: str):
        self.controller.update_status("OCR Failed")
        self.controller._show_error("OCR Error", error_msg)
        self._cleanup_ocr_temp()

    def _cleanup_ocr_temp(self):
        if self._ocr_temp_path and os.path.exists(self._ocr_temp_path):
            try:
                os.remove(self._ocr_temp_path)
            except:
                pass
        self._ocr_temp_path = None

    def on_download_clicked(self, doc: APIDocument):
        is_owner = self.controller._me_id is not None and doc.owner_id == self.controller._me_id
        is_admin = self.controller._me.get("role") == "admin" if self.controller._me else False

        if doc.is_read_only and not (is_owner or is_admin):
            self.controller._show_error(
                self.controller.translator.tr("errors.access_denied"),
                self.controller.translator.tr("preview.read_only_access")
            )
            return

        default_name = doc.filename or f"document_{doc.id}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(
            self.view, 
            self.controller.translator.tr("context_menu.download"), 
            default_name, 
            "PDF Files (*.pdf *.PDF)"
        )
        if not save_path:
            return

        self.controller.update_status(self.controller.translator.tr("common.loading"), 0)
        from ...utils.workers import DownloadWorker
        self._download_worker = DownloadWorker(self.api, doc.id)
        self._download_worker.finished.connect(lambda content: self._on_download_finished(content, doc, save_path))
        self._download_worker.error.connect(lambda e: self.controller._show_error(self.controller.translator.tr("common.error"), str(e)))
        self._download_worker.start()

    def _on_download_finished(self, content: bytes, doc: APIDocument, save_path: str):
        try:
            if doc.encryption_key:
                try:
                    with fitz.open(stream=content, filetype="pdf") as pdf:
                        pdf.authenticate(doc.encryption_key)
                        pdf.save(save_path)
                    self.controller.update_status(self.controller.translator.tr("common.success"))
                    return
                except Exception as e:
                    print(f"Decryption failed during download: {e}")

            Path(save_path).write_bytes(content)
            self.controller.update_status(self.controller.translator.tr("common.success"))
        except Exception as e:
            self.controller._show_error(self.controller.translator.tr("common.error"), str(e))

    def on_edit_clicked(self, doc: APIDocument):
        is_admin = self.controller._me.get("role") == "admin" if self.controller._me else False
        dialog = UploadDialog(
            api=self.api, 
            doc_to_edit=doc, 
            current_user_id=self.controller._me_id, 
            is_admin=is_admin, 
            parent=self.view
        )
        if dialog.exec() == 1:
            # Update only the specific document instead of rebuilding entire grid
            print(f"DEBUG: Dialog exec result: 1, resulting_document: {dialog.resulting_document}")
            if dialog.resulting_document:
                print(f"DEBUG: Updating document {dialog.resulting_document.id} in grid")
                success = self.ui.file_grid.update_single_document(dialog.resulting_document)
                if success:
                    self.ui.preview_panel.set_document(dialog.resulting_document, self.controller._me_id, is_admin)
                    self.ui.file_grid.find_and_select_document(dialog.resulting_document.id)
                    print("DEBUG: Single document update successful")
                else:
                    print("DEBUG: Single document update failed, falling back to fetch_from_server")
                    # Fallback to old method if single update fails
                    self.controller.search_handler.fetch_from_server()
            else:
                print("DEBUG: No resulting_document from dialog, skipping grid update")
            
            self.controller.update_status(self.controller.translator.tr("main.saved_msg"))
            
            # Force UI refresh to ensure data sync
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._force_ui_refresh())

    def _force_ui_refresh(self):
        """Force refresh of UI components to ensure data sync."""
        print("DEBUG: Forcing UI refresh to sync data")
        
        # Refresh current document in preview panel
        current_item = self.ui.file_grid.files_list.currentItem()
        if current_item:
            current_doc = current_item.data(Qt.ItemDataRole.UserRole)
            if isinstance(current_doc, APIDocument):
                print(f"DEBUG: Refreshing preview panel for doc {current_doc.id}")
                self.ui.preview_panel.set_document(current_doc, self.controller._me_id, 
                    self.controller._me.get("role") == "admin" if self.controller._me else False)
        
        # Force grid repaint
        self.ui.file_grid.files_list.viewport().update()
        self.ui.file_grid.files_list.update()
        
        print("DEBUG: UI refresh completed")

    def on_delete_clicked(self, doc: APIDocument):
        if self.controller._me_id is not None and doc.owner_id != self.controller._me_id:
            is_admin = self.controller._me.get("role") == "admin" if self.controller._me else False
            if not is_admin:
                self.controller._show_error(
                    self.controller.translator.tr("errors.access_denied"), 
                    self.controller.translator.tr("admin.self_delete_error")
                )
                return

        reply = QMessageBox.question(
            self.view,
            self.controller.translator.tr("admin.confirm_delete_title"),
            self.controller.translator.tr("admin.confirm_delete_msg").format(name=doc.title),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.controller.update_status(self.controller.translator.tr("common.loading"), 0)
        from ...utils.workers import DeleteWorker
        self._delete_worker = DeleteWorker(self.api, doc.id)
        self._delete_worker.finished.connect(self._on_delete_finished)
        self._delete_worker.error.connect(lambda e: self.controller._show_error(self.controller.translator.tr("common.error"), str(e)))
        self._delete_worker.start()

    def _on_delete_finished(self):
        self.controller.search_handler.fetch_from_server()
        self.controller.update_status(self.controller.translator.tr("common.success"))

    def on_open_file_clicked(self, doc_id: int, search_query: str = None):
        self.controller.update_status(self.controller.translator.tr("common.loading"), 0)
        from ...utils.workers import MetadataWorker
        self._metadata_worker = MetadataWorker(self.api, doc_id)
        self._metadata_worker.finished.connect(lambda doc: self._start_open_download(doc, search_query))
        self._metadata_worker.error.connect(lambda e: self.controller._show_error(self.controller.translator.tr("common.error"), str(e)))
        self._metadata_worker.start()

    def _start_open_download(self, doc: APIDocument, search_query: str):
        from ...utils.workers import DownloadWorker
        self._open_worker = DownloadWorker(self.api, doc.id)
        self._open_worker.finished.connect(lambda content: self._on_open_finished(content, doc, search_query))
        self._open_worker.error.connect(lambda e: self.controller._show_error(self.controller.translator.tr("common.error"), str(e)))
        self._open_worker.start()

    def _on_open_finished(self, content: bytes, doc: APIDocument, search_query: str):
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            Path(tmp_path).write_bytes(content)

            # Use original TITLE from database (user-entered name), not server filename
            window_title = doc.title or doc.filename or f"Document_{doc.id}"

            self.controller._viewer_window = FileViewerWindow(
                tmp_path,
                self.controller.config.get("theme") == "Dark",
                title=window_title,  # Use original title as window title
                password=doc.encryption_key
            )
            self.controller._viewer_window.show()

            if search_query:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(500, lambda: self.controller._viewer_window.viewer.highlight_search_result(search_query))

            self.controller.update_status(self.controller.translator.tr("common.ready"))
        except Exception as e:
            self.controller._show_error(self.controller.translator.tr("common.error"), str(e))

    def on_add_pdf_clicked(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self.view, 
            self.controller.translator.tr("upload.title_upload"), 
            "", 
            "PDF Files (*.pdf *.PDF)"
        )
        if not files:
            return

        if len(files) == 1:
            file_path = files[0]
            selected_items = self.ui.nav_tree.selectedItems()
            folder_id = None
            is_public = False
            if selected_items:
                item = selected_items[0]
                data = item.data(0, Qt.ItemDataRole.UserRole)
                from ...api_manager import APIFolder
                if isinstance(data, APIFolder):
                    folder_id = data.id
                    is_public = data.is_public
                elif data == "Shared Documents":
                    is_public = True

            is_admin = self.controller._me is not None and self.controller._me.get("role") == "admin"
            dlg = UploadDialog(
                file_path=file_path, 
                api=self.api, 
                is_public=is_public, 
                current_user_id=self.controller._me_id, 
                is_admin=is_admin, 
                parent=self.view
            )
            if dlg.exec() == UploadDialog.DialogCode.Accepted:
                self.controller.search_handler.fetch_from_server()
        else:
            dlg = BatchUploadDialog(self.api, files, self.view)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.controller.search_handler.fetch_from_server()

    def start_upload_worker(self, paths: list[str], target_folder_id: Optional[int], is_public: bool):
        """Start batch upload with non-blocking progress in status bar."""
        log_debug("file_operations", f"start_upload_worker CALLED with {len(paths)} files")

        # Validate file count
        if len(paths) > 100:
            reply = QMessageBox.question(
                self.view,
                self.controller.translator.tr("common.warning"),
                f"You are uploading {len(paths)} files. This may take a while. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Show progress in status bar (non-blocking)
        self.view.set_upload_progress(0, len(paths), "Starting...")

        # Create worker - processes files with controlled concurrency
        self._upload_worker = BatchUploadWorker(self.api, paths, target_folder_id, is_public, max_workers=3)
        self._upload_worker.progress.connect(
            lambda value, total: self.view.set_upload_progress(value, total, "")
        )
        self._upload_worker.log_message.connect(
            lambda msg: self.view.statusBar().showMessage(msg, 2000)
        )
        self._upload_worker.finished.connect(self._on_upload_finished)
        self._upload_worker.error.connect(lambda e: self.controller._show_error("Upload Error", e))
        self._upload_worker.start()
        log_debug("file_operations", "BatchUploadWorker started")

    def _on_upload_finished(self):
        """Handle upload completion."""
        log_debug("file_operations", "_on_upload_finished CALLED")
        self.view.clear_progress()
        self.controller.update_status(self.controller.translator.tr("common.success"))
        self.controller.search_handler.fetch_from_server()
        self.ui.nav_tree.refresh()

    def handle_drop(self, event, tree_pos):
        """Handle drag-and-drop events - non-blocking for large file sets."""
        from ...utils.logger import log_debug, log_error
        from ...api_manager import APIFolder, APIDocument
        
        log_debug("file_operations", f"handle_drop called, tree_pos={tree_pos}")

        # Internal file grid move operation
        if event.source() == self.ui.file_grid.files_list:
            item = self.ui.nav_tree.itemAt(tree_pos)
            if not item:
                event.ignore()
                return

            data = item.data(0, Qt.ItemDataRole.UserRole)
            target_folder_id: Optional[int] = None
            is_public_target = False

            if isinstance(data, APIFolder):
                target_folder_id = data.id
                is_public_target = data.is_public
            elif data == "My Documents":
                target_folder_id = None
                is_public_target = False
            elif data == "Shared Documents":
                target_folder_id = None
                is_public_target = True
            else:
                event.ignore()
                return

            source_item = self.ui.file_grid.files_list.currentItem()
            if not source_item:
                event.ignore()
                return

            doc = source_item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(doc, APIDocument):
                event.ignore()
                return

            try:
                new_is_public = doc.is_public
                if is_public_target and not doc.is_public:
                    if data == "Shared Documents":
                        new_is_public = True
                    else:
                        reply = QMessageBox.question(
                            self.view,
                            self.controller.translator.tr("common.warning"),
                            self.controller.translator.tr("upload.make_public_confirm").format(name=doc.title),
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            new_is_public = True

                self.api.update_document(
                    document_id=doc.id,
                    title=None,
                    category_id=None,
                    file_type_id=None,
                    is_private=None,
                    is_public=new_is_public,
                    is_public_edit=None,
                    notes=None,
                    folder_id=target_folder_id
                )

                self.controller.search_handler.fetch_from_server()
                self.ui.nav_tree.refresh()
                event.acceptProposedAction()
            except Exception as e:
                self.controller._show_error(self.controller.translator.tr("common.error"), str(e))
                event.ignore()
            return

        # External file drop - Process asynchronously to prevent UI freeze
        if event.mimeData().hasUrls():
            log_debug("file_operations", f"External drop detected, urlCount={len(event.mimeData().urls())}")
            # Accept immediately to prevent blocking
            event.acceptProposedAction()

            # Collect paths first (quick operation)
            paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            log_debug("file_operations", f"Collected {len(paths)} local file paths")
            if not paths:
                log_debug("file_operations", "No local files found, ignoring drop")
                return

            # Show immediate feedback
            file_count = len(paths)
            if file_count > 10:
                self.controller.update_status(f"Preparing {file_count} files for upload...")
            else:
                self.controller.update_status(f"Preparing {file_count} file(s) for upload...")

            # Get target folder info (quick operation)
            item = self.ui.nav_tree.itemAt(tree_pos)
            target_folder_id: Optional[int] = None
            is_public = False

            if item:
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(data, APIFolder):
                    target_folder_id = data.id
                    is_public = data.is_public

            log_debug("file_operations", f"Starting upload worker with {len(paths)} files")
            # Start upload in background using QTimer
            from PyQt6.QtCore import QTimer
            self._defer_timer = QTimer()
            self._defer_timer.setSingleShot(True)
            self._defer_timer.timeout.connect(lambda: self.start_upload_worker(paths, target_folder_id, is_public))
            self._defer_timer.start(0)
            log_debug("file_operations", "QTimer started")
        else:
            log_debug("file_operations", "No URLs in mimeData, ignoring drop")
            event.ignore()

    def rename_file(self, doc: APIDocument):
        new_name, ok = QInputDialog.getText(
            self.view, 
            self.controller.translator.tr("context_menu.rename"), 
            self.controller.translator.tr("upload.display_name") + ":", 
            text=doc.title
        )
        if ok and new_name and new_name != doc.title:
            try:
                # Update document on server
                updated_doc = self.api.update_document(
                    document_id=doc.id,
                    title=new_name,
                    category_id=doc.category.id if doc.category else None,
                    file_type_id=doc.file_type.id if doc.file_type else None,
                    is_private=doc.is_private,
                    is_public=doc.is_public,
                    is_public_edit=doc.is_public_edit,
                    notes=doc.notes or ""
                )
                
                # Update only the specific document in the grid
                self.ui.file_grid.update_single_document(updated_doc)
                self.ui.file_grid.find_and_select_document(updated_doc.id)
                
            except Exception as e:
                self.controller._show_error(self.controller.translator.tr("common.error"), str(e))
