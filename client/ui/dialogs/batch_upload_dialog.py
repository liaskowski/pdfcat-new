from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QCheckBox, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings, QThread
from PyQt6.QtGui import QFont
from pathlib import Path
from ...utils.translator import Translator
from ...api_manager import APIManager
from ...utils.task_queue import BatchUploadQueue

class BatchUploadDialog(QDialog):
    # Thread-safe signals for UI updates
    progress_signal = pyqtSignal(int, int, str)  # current, total, message
    log_signal = pyqtSignal(str)  # message
    finished_signal = pyqtSignal(int, int, list)  # completed, failed, [(filename, error), ...]
    
    def __init__(self, api: APIManager, files: list[str], parent=None, target_folder_id: int = None, is_public_default: bool = False):
        super().__init__(parent)
        self.api = api
        self.files = files
        self.target_folder_id = target_folder_id
        self.is_public_default = is_public_default
        self.translator = Translator()

        self.setWindowTitle(self.translator.tr("upload.batch_title"))
        self.resize(800, 600)

        # Connect signals to slots (thread-safe)
        self.progress_signal.connect(self._on_progress_ui)
        self.log_signal.connect(self._on_log_ui)
        self.finished_signal.connect(self._on_finished_ui)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Header with file count
        header_label = QLabel(self.translator.tr("batch_upload.file_count").format(count=len(self.files)))
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header_label)

        # File Table
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels([
            "",  # Checkbox column
            self.translator.tr("batch_upload.file_name"),
            self.translator.tr("batch_upload.file_size"),
            self.translator.tr("batch_upload.file_path")
        ])

        # Configure table
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setWordWrap(True)  # Enable text wrapping

        # Set column stretch
        header = self.file_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self.file_table.setColumnWidth(0, 40)  # Checkbox column width

        # Set minimum row height for better readability
        row_height = 35  # Minimum row height in pixels

        # Populate table
        self.file_table.setRowCount(len(self.files))
        for row, file_path in enumerate(self.files):
            # Set minimum row height
            self.file_table.verticalHeader().setMinimumSectionSize(row_height)

            # Checkbox (with stretch for proper centering)
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addStretch()
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.addStretch()
            checkbox_layout.setContentsMargins(2, 2, 2, 2)  # Small margins for better appearance
            checkbox.stateChanged.connect(lambda state, r=row: self._on_file_checkbox_changed(r, state))
            self.file_table.setCellWidget(row, 0, checkbox_widget)

            # Filename (with bold font for better readability)
            filename_item = QTableWidgetItem(Path(file_path).name)
            filename_item.setFlags(filename_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            font = filename_item.font()
            font.setBold(True)
            filename_item.setFont(font)
            self.file_table.setItem(row, 1, filename_item)

            # File size (center aligned)
            try:
                size_bytes = Path(file_path).stat().st_size
                size_str = self._format_file_size(size_bytes)
            except:
                size_str = "Unknown"
            size_item = QTableWidgetItem(size_str)
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.file_table.setItem(row, 2, size_item)

            # File path (with elided text if too long)
            path_item = QTableWidgetItem(str(file_path))
            path_item.setFlags(path_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            path_item.setToolTip(str(file_path))  # Show full path on hover
            self.file_table.setItem(row, 3, path_item)

            # Set row height
            self.file_table.setRowHeight(row, max(row_height, self.file_table.rowHeight(row)))

        layout.addWidget(self.file_table)
        
        # Select All / Deselect All buttons
        select_btns_layout = QHBoxLayout()
        select_all_btn = QPushButton(self.translator.tr("batch_upload.select_all"))
        select_all_btn.clicked.connect(self._select_all_files)
        deselect_all_btn = QPushButton(self.translator.tr("batch_upload.deselect_all"))
        deselect_all_btn.clicked.connect(self._deselect_all_files)
        select_btns_layout.addWidget(select_all_btn)
        select_btns_layout.addWidget(deselect_all_btn)
        select_btns_layout.addStretch()
        layout.addLayout(select_btns_layout)

        # Visibility/Permissions section
        perms_group = QVBoxLayout()
        perms_label = QLabel(self.translator.tr("upload.permissions"))
        perms_label.setStyleSheet("font-weight: bold;")
        perms_group.addWidget(perms_label)

        perms_checkboxes = QHBoxLayout()

        self.is_private_checkbox = QCheckBox(self.translator.tr("upload.private"))
        self.is_private_checkbox.setChecked(True)
        self.is_private_checkbox.toggled.connect(self._on_private_toggled)
        perms_checkboxes.addWidget(self.is_private_checkbox)

        self.is_public_checkbox = QCheckBox(self.translator.tr("upload.public"))
        self.is_public_checkbox.setChecked(self.is_public_default)
        self.is_public_checkbox.toggled.connect(self._on_public_toggled)
        perms_checkboxes.addWidget(self.is_public_checkbox)

        self.is_public_edit_checkbox = QCheckBox(self.translator.tr("upload.public_edit"))
        self.is_public_edit_checkbox.setChecked(False)
        self.is_public_edit_checkbox.setEnabled(self.is_public_default)
        perms_checkboxes.addWidget(self.is_public_edit_checkbox)

        self.is_read_only_checkbox = QCheckBox(self.translator.tr("upload.read_only"))
        self.is_read_only_checkbox.setChecked(False)
        perms_checkboxes.addWidget(self.is_read_only_checkbox)

        perms_checkboxes.addStretch()
        perms_group.addLayout(perms_checkboxes)
        layout.addLayout(perms_group)

        # Info label
        info_text = self.translator.tr("batch_upload.info_text")
        if "batch_upload.info_text" in info_text:
            info_text = "Files will upload with default metadata. Edit individual files after upload via context menu."
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Buttons
        btns = QHBoxLayout()
        self.upload_btn = QPushButton(self.translator.tr("batch_upload.upload"))
        self.upload_btn.setObjectName("primaryButton")
        self.upload_btn.clicked.connect(self._start_upload)

        self.cancel_btn = QPushButton(self.translator.tr("batch_upload.cancel"))
        self.cancel_btn.clicked.connect(self._cancel_upload)
        self.cancel_btn.setEnabled(False)

        btns.addStretch()
        btns.addWidget(self.cancel_btn)
        btns.addWidget(self.upload_btn)
        layout.addLayout(btns)

        # Restore geometry
        self._restore_geometry()
        
        self._upload_queue = None
        self._selected_files = set(range(len(self.files)))  # Track selected file indices
    
    def _on_file_checkbox_changed(self, row, state):
        """Handle file checkbox state change."""
        if state == Qt.CheckState.Checked.value:
            self._selected_files.add(row)
        else:
            self._selected_files.discard(row)
        
        # Update header with selected count
        header_label = self.layout().itemAt(0).widget()
        if isinstance(header_label, QLabel):
            selected_count = len(self._selected_files)
            header_label.setText(self.translator.tr("batch_upload.file_count").format(count=selected_count))
    
    def _select_all_files(self):
        """Select all files in the table."""
        self._selected_files = set(range(self.file_table.rowCount()))
        for row in range(self.file_table.rowCount()):
            checkbox_widget = self.file_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.blockSignals(True)
                    checkbox.setChecked(True)
                    checkbox.blockSignals(False)
    
    def _deselect_all_files(self):
        """Deselect all files in the table."""
        self._selected_files = set()
        for row in range(self.file_table.rowCount()):
            checkbox_widget = self.file_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.blockSignals(True)
                    checkbox.setChecked(False)
                    checkbox.blockSignals(False)

    def _on_private_toggled(self, checked):
        """Handle private checkbox state change."""
        if checked:
            self.is_public_checkbox.blockSignals(True)
            self.is_public_checkbox.setChecked(False)
            self.is_public_checkbox.blockSignals(False)
            self.is_public_edit_checkbox.setEnabled(False)

    def _on_public_toggled(self, checked):
        """Handle public checkbox state change."""
        if checked:
            self.is_private_checkbox.blockSignals(True)
            self.is_private_checkbox.setChecked(False)
            self.is_private_checkbox.blockSignals(False)
            self.is_public_edit_checkbox.setEnabled(True)
        else:
            self.is_public_edit_checkbox.setEnabled(False)

    def _format_file_size(self, size_bytes):
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def _restore_geometry(self):
        """Restore window geometry from settings."""
        settings = QSettings("PDF cat", "BatchUploadDialog")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def _save_geometry(self):
        """Save window geometry to settings."""
        settings = QSettings("PDF cat", "BatchUploadDialog")
        settings.setValue("geometry", self.saveGeometry())
    
    def closeEvent(self, event):
        """Save geometry on close."""
        self._save_geometry()
        super().closeEvent(event)

    def _start_upload(self):
        # Get selected files
        selected_files = [self.files[i] for i in sorted(self._selected_files)]

        if not selected_files:
            QMessageBox.warning(
                self,
                self.translator.tr("common.warning"),
                self.translator.tr("batch_upload.no_files_selected")
            )
            return

        # Check server health before starting bulk upload
        if not self.api.is_server_available():
            QMessageBox.critical(
                self,
                self.translator.tr("common.error"),
                self.translator.tr("upload.server_unavailable")
            )
            return

        file_count = len(selected_files)
        
        # Create batch queue with concurrency control (3 concurrent uploads)
        # Queue handles encryption and auto-tagging in worker threads
        self._upload_queue = BatchUploadQueue(self.api, max_workers=3, rate_limit=3)
        self._upload_queue.set_progress_callback(self._on_progress)
        self._upload_queue.set_log_callback(self._on_log)

        # Prepare metadata template with values from permission checkboxes
        metadata_template = {
            'category_id': None,
            'file_type_id': None,
            'use_ocr': True,
            'is_private': self.is_private_checkbox.isChecked(),
            'is_public': self.is_public_checkbox.isChecked(),
            'is_public_edit': self.is_public_edit_checkbox.isChecked(),
            'is_read_only': self.is_read_only_checkbox.isChecked(),
            'notes': '',
            'tags': '',
            'folder_id': self.target_folder_id,
        }

        # ALL processing in background thread
        self._worker_thread = QThread()
        self._worker_thread.run = lambda: self._process_queue_setup(selected_files, metadata_template)
        self._worker_thread.finished.connect(self._on_queue_finished)
        self._worker_thread.start()
        
        # Close dialog immediately - don't block UI
        self.accept()
        
        # Show initial status in parent window's status bar
        if self.parent():
            if hasattr(self.parent(), 'set_upload_progress'):
                self.parent().set_upload_progress(0, file_count, f"Starting batch upload of {file_count} files...")

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
        """Handle progress updates - emit signal for thread-safe UI update."""
        self.progress_signal.emit(current, total, message)

    def _on_log(self, message: str):
        """Handle log messages - emit signal for thread-safe UI update."""
        self.log_signal.emit(message)

    def _on_progress_ui(self, current: int, total: int, message: str):
        """Update progress in parent window's status bar (UI thread)."""
        if self.parent():
            if hasattr(self.parent(), 'set_upload_progress'):
                self.parent().set_upload_progress(current, total, message)

    def _on_log_ui(self, message: str):
        """Show log message in parent window's status bar (UI thread)."""
        if self.parent():
            if hasattr(self.parent(), 'statusBar'):
                self.parent().statusBar().showMessage(message, 3000)

    def _on_finished_ui(self, completed: int, failed: int, error_list: list):
        """Show completion notification (UI thread)."""
        total = len(self.files)
        
        # Clear progress bar
        if self.parent():
            if hasattr(self.parent(), 'clear_progress'):
                self.parent().clear_progress()
        
        # Build error message
        error_details = ""
        if error_list:
            error_details = "\n\nFailed files:\n"
            for filename, error in error_list[:10]:  # Show first 10 errors
                error_details += f"  • {filename}: {error}\n"
            if len(error_list) > 10:
                error_details += f"  ... and {len(error_list) - 10} more"

        # Show notification
        if failed > 0:
            msg = self.translator.tr("upload.batch_summary").format(
                completed=completed,
                total=total,
                failed=failed,
                error_details=error_details
            )
            QMessageBox.warning(
                None,  # No parent - non-blocking notification
                self.translator.tr("upload.batch_complete"),
                msg
            )
        else:
            msg = self.translator.tr("upload.batch_success").format(completed=completed)
            QMessageBox.information(
                None,  # No parent - non-blocking notification
                self.translator.tr("common.success"),
                msg
            )

    def _on_queue_finished(self):
        """Handle queue completion - emit signal for thread-safe UI update."""
        stats = self._upload_queue.get_stats()
        summary = self._upload_queue.get_upload_summary()

        completed = stats['completed']
        failed = stats['failed']

        # Build error list for signal
        error_list = []
        if summary['failed']:
            error_list = [(Path(item['file']).name, item['error']) for item in summary['failed']]

        self._upload_queue.shutdown(wait=False)
        
        # Emit signal for thread-safe UI update
        self.finished_signal.emit(completed, failed, error_list)

    def _cancel_upload(self):
        """Cancel ongoing uploads."""
        if self._upload_queue:
            self._upload_queue.cancel(wait=False)
            self._upload_queue.shutdown(wait=False)
        self.reject()
