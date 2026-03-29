from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox, QProgressBar, QTextEdit, QFrame
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt


class AutoTagWorker(QThread):
    """Worker thread for auto-tagging operation"""
    started = pyqtSignal()
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)  # current, total

    def __init__(self, api):
        super().__init__()
        self.api = api

    def run(self):
        try:
            self.started.emit()
            # Call auto-tag API
            message = self.api.auto_tag()
            self.finished.emit(message)
        except Exception as e:
            self.error.emit(str(e))


class AutoTagWidget(QWidget):
    """Widget for automatic document tagging"""
    
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("<h2>Auto-Tag Documents</h2>")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)
        
        # Description
        desc_label = QLabel(
            "Automatically generate tags for all documents based on their content.\n"
            "The system will analyze document text and extract relevant keywords as tags.\n\n"
            "<b>Note:</b> This process runs in the background and may take several minutes\n"
            "depending on the number of documents."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("padding: 10px; background-color: #f5f5f5; border-radius: 5px;")
        layout.addWidget(desc_label)
        
        # Status frame
        self.status_frame = QFrame()
        self.status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        status_layout = QVBoxLayout(self.status_frame)
        
        # Status label
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        status_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        status_layout.addWidget(self.progress_bar)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(150)
        self.log_output.setPlaceholderText("Operation log will appear here...")
        status_layout.addWidget(self.log_output)
        
        layout.addWidget(self.status_frame)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.start_btn = QPushButton("Start Auto-Tagging")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 12px 24px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.start_btn.clicked.connect(self.start_auto_tag)
        btn_layout.addWidget(self.start_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Info label
        info_label = QLabel(
            "💡 Tip: Tags are extracted using keyword frequency analysis.\n"
            "Stop words in Russian, English, and Polish are automatically filtered out."
        )
        info_label.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
    
    def start_auto_tag(self):
        """Start the auto-tagging process"""
        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Confirm Auto-Tagging",
            "This will analyze all documents and generate tags automatically.\n\n"
            "The process may take several minutes depending on the number of documents.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Disable button
        self.start_btn.setEnabled(False)
        self.start_btn.setText("Auto-Tagging in Progress...")
        self.progress_bar.setVisible(True)
        self.log_output.clear()
        self.log_output.append("Starting auto-tagging process...")
        self.status_label.setText("Status: Running")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2196F3;")
        
        # Start worker
        self.worker = AutoTagWorker(self.api)
        self.worker.started.connect(self.on_started)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_started(self):
        """Called when auto-tagging starts"""
        self.log_output.append("Analyzing documents...")
    
    def on_finished(self, message):
        """Called when auto-tagging completes"""
        self.start_btn.setEnabled(True)
        self.start_btn.setText("Start Auto-Tagging")
        self.progress_bar.setVisible(False)
        self.status_label.setText("Status: Completed")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #4CAF50;")
        self.log_output.append(f"✓ {message}")
        
        QMessageBox.information(
            self,
            "Auto-Tagging Complete",
            f"{message}\n\n"
            "Tags have been automatically generated based on document content."
        )
    
    def on_error(self, error_msg):
        """Called when auto-tagging fails"""
        self.start_btn.setEnabled(True)
        self.start_btn.setText("Start Auto-Tagging")
        self.progress_bar.setVisible(False)
        self.status_label.setText("Status: Failed")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #f44336;")
        self.log_output.append(f"✗ Error: {error_msg}")
        
        QMessageBox.critical(
            self,
            "Auto-Tagging Failed",
            f"An error occurred during auto-tagging:\n\n{error_msg}"
        )
