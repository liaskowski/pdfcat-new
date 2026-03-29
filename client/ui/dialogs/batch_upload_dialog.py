from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout, QLabel, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from pathlib import Path
from ..components.document_form import DocumentMetadataForm
from ...utils.translator import Translator
from ...api_manager import APIManager
from ...utils.task_queue import BatchUploadQueue

class BatchUploadDialog(QDialog):
    def __init__(self, api: APIManager, files: list[str], parent=None):
        super().__init__(parent)
        self.api = api
        self.files = files
        self.translator = Translator()

        self.setWindowTitle(self.translator.tr("upload.batch_title"))
        self.resize(800, 600)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Files List
        layout.addWidget(QLabel(self.translator.tr("upload.selected_files")))
        self.file_list = QListWidget()
        for f in self.files:
            item = QListWidgetItem(Path(f).name)
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.file_list.addItem(item)
        layout.addWidget(self.file_list)

        # Shared Metadata Form
        layout.addWidget(QLabel(self.translator.tr("upload.common_metadata")))
        self.form = DocumentMetadataForm(
            self.api,
            is_edit_mode=False,
            is_public_default=False,
            current_user_id=None,
            is_admin=False
        )
        layout.addWidget(self.form)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status Label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Buttons
        btns = QHBoxLayout()
        self.upload_btn = QPushButton(self.translator.tr("upload.upload_all"))
        self.upload_btn.setObjectName("primaryButton")
        self.upload_btn.clicked.connect(self._start_upload)

        self.cancel_btn = QPushButton(self.translator.tr("common.cancel"))
        self.cancel_btn.clicked.connect(self._cancel_upload)
        self.cancel_btn.setEnabled(False)

        btns.addStretch()
        btns.addWidget(self.cancel_btn)
        btns.addWidget(self.upload_btn)
        layout.addLayout(btns)
        
        self._upload_queue = None

    def _start_upload(self):
        data = self.form.get_data()

        # Check server health before starting bulk upload
        self.status_label.setText("Checking server status...")
        if not self.api.is_server_available():
            QMessageBox.critical(
                self,
                self.translator.tr("common.error"),
                "Server is not available or is overloaded. Please try again later."
            )
            return

        # Disable UI
        self.upload_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.file_list.setEnabled(False)
        self.form.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.files))
        self.progress_bar.setValue(0)
        self.status_label.setText("")

        self.errors = []
        self.completed_count = 0

        # Create batch queue with concurrency control (3 concurrent uploads)
        # Queue handles encryption and auto-tagging in worker threads
        self._upload_queue = BatchUploadQueue(self.api, max_workers=3, rate_limit=3)
        self._upload_queue.set_progress_callback(self._on_progress)
        self._upload_queue.set_log_callback(self._on_log)

        # Prepare metadata template
        metadata_template = {
            'category_id': data.get('category_id'),
            'file_type_id': data.get('file_type_id'),
            'use_ocr': data.get('use_ocr', True),
            'is_private': data.get('is_private', True),
            'is_public': data.get('is_public', False),
            'is_public_edit': data.get('is_public_edit', False),
            'is_read_only': data.get('is_read_only', False),
            'notes': data.get('notes', ''),
            'tags': data.get('tags', ''),
            'folder_id': None,
        }

        # ALL processing in background thread
        self._worker_thread = QThread()
        self._worker_thread.run = lambda: self._process_queue_setup(self.files, metadata_template)
        self._worker_thread.finished.connect(self._on_queue_finished)
        self._worker_thread.start()

    def _process_queue_setup(self, files: list[str], metadata_template: dict):
        """Submit all files to queue in background thread."""
        try:
            for file_path in files:
                metadata = metadata_template.copy()
                metadata['title'] = Path(file_path).stem
                self._upload_queue.submit_upload(file_path, metadata)
            
            # Wait for completion
            self._upload_queue.wait()
        except Exception as e:
            print(f"Queue setup error: {e}")

    def _on_progress(self, current: int, total: int, message: str = ""):
        """Handle progress updates."""
        self.progress_bar.setValue(current)
        self.status_label.setText(f"{current}/{total} - {message}")

    def _on_log(self, message: str):
        """Handle log messages."""
        print(f"[BatchUpload] {message}")

    def _on_queue_finished(self):
        """Handle queue completion."""
        stats = self._upload_queue.get_stats()
        summary = self._upload_queue.get_upload_summary()
        
        completed = stats['completed']
        failed = stats['failed']
        
        # Build detailed error message
        error_details = ""
        if summary['failed']:
            error_details = "\n\nFailed files:\n"
            for item in summary['failed'][:10]:  # Show first 10 errors
                error_details += f"  • {Path(item['file']).name}: {item['error']}\n"
            if len(summary['failed']) > 10:
                error_details += f"  ... and {len(summary['failed']) - 10} more"
        
        self._upload_queue.shutdown(wait=False)
        
        # Show summary
        if failed > 0:
            QMessageBox.warning(
                self,
                self.translator.tr("upload.batch_complete"),
                f"Upload completed: {completed}/{len(self.files)} successful.\n"
                f"Failed: {failed}\n{error_details}"
            )
        else:
            QMessageBox.information(
                self,
                self.translator.tr("common.success"),
                f"Successfully uploaded {completed} files!"
            )
        
        self.accept()

    def _cancel_upload(self):
        """Cancel ongoing uploads."""
        if self._upload_queue:
            self._upload_queue.cancel(wait=False)
            self.status_label.setText("Cancelling...")
            self._upload_queue.shutdown(wait=False)
        self.reject()
