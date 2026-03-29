
import os
import fitz
import secrets
import tempfile
from pathlib import Path
from typing import Optional, List

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QWidget, QTabWidget, QHBoxLayout, QPushButton,
    QMessageBox, QSplitter, QScrollArea, QFileDialog, QFrame, QLabel
)
import qtawesome as qta

from ..api_manager import APIManager, APIDocument
from ..widgets.modern_pdf_viewer import ModernPDFViewer
from ..utils.translator import Translator
from ..themes import ThemeManager
from ..logic.tags_engine import TagAnalyzer
from ..workers.tag_worker import TagAnalysisWorker

# Import new components
from .components.history_tab import HistoryTab
from .components.document_form import DocumentMetadataForm

class UploadDialog(QDialog):
    def __init__(
        self,
        api: APIManager,
        file_path: str = None,
        doc_to_edit: Optional[APIDocument] = None,
        is_public: bool = False,
        current_user_id: Optional[int] = None,
        is_admin: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._file_path = file_path
        self._is_public = is_public
        self.doc_to_edit = doc_to_edit
        self.is_edit_mode = self.doc_to_edit is not None
        self.current_user_id = current_user_id
        self.is_admin = is_admin
        
        self.translator = Translator()
        self.theme_manager = ThemeManager()
        self.tag_analyzer = TagAnalyzer() # Used for initial analysis
        self._tag_worker = None
        
        self.resulting_document: Optional[APIDocument] = None

        title = self.translator.tr("upload.title_edit") if self.is_edit_mode else self.translator.tr("upload.title_upload")
        self.setWindowTitle(title)
        self.setModal(True)
        
        # State Persistence
        self.settings = QSettings("pdflib", "client")
        geometry = self.settings.value(f"Geometry/{self.__class__.__name__}")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1000, 700)
            
        self.setMinimumSize(600, 450)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs)

        # --- General Tab ---
        self.general_tab = QWidget()
        self.tabs.addTab(self.general_tab, self.translator.tr("upload.tab_general"))
        self._build_general_tab()

        # --- History Tab (only in edit mode) ---
        if self.is_edit_mode:
            self.history_tab = HistoryTab(self._api, self.doc_to_edit.id)
            self.tabs.addTab(self.history_tab, self.translator.tr("upload.tab_history"))

        # --- Buttons ---
        buttons_row = QWidget()
        buttons_layout = QHBoxLayout(buttons_row)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)

        self.cancel_btn = QPushButton(self.translator.tr("common.cancel"))
        self.cancel_btn.setObjectName("secondaryButton")
        
        btn_text = self.translator.tr("common.save") if self.is_edit_mode else self.translator.tr("upload.title_upload")
        self.save_btn = QPushButton(btn_text)
        self.save_btn.setObjectName("primaryButton")

        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.save_btn)
        root_layout.addWidget(buttons_row)

        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self._on_save_clicked)

        if self.is_edit_mode:
            self.form.fill_from_document(self.doc_to_edit)
            # Connect update button from form
            self.form.update_content_btn.clicked.connect(self._on_update_content_clicked)
            self._render_preview()
        else:
            self.form.display_name_input.setText(Path(self._file_path).name)
            self._render_preview()
            self._run_tag_analysis()

    def closeEvent(self, event):
        if self._tag_worker and self._tag_worker.isRunning():
            self._tag_worker.wait()
        self.settings.setValue(f"Geometry/{self.__class__.__name__}", self.saveGeometry())
        super().closeEvent(event)

    def _build_general_tab(self):
        layout = QVBoxLayout(self.general_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- Left Side: Preview ---
        self.preview_container = QWidget()
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        
        preview_title_label = QLabel(self.translator.tr("upload.doc_preview"))
        preview_title_label.setObjectName("sectionTitle")
        
        self.pdf_viewer = ModernPDFViewer()
        
        preview_layout.addWidget(preview_title_label)
        preview_layout.addWidget(self.pdf_viewer, 1)
        
        self.splitter.addWidget(self.preview_container)

        # --- Right Side: Form ---
        self.form_scroll = QScrollArea()
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        # Initialize Form Component
        self.form = DocumentMetadataForm(
            self._api,
            self.is_edit_mode,
            self._is_public,
            self.current_user_id,
            self.is_admin
        )
        
        self.form_scroll.setWidget(self.form)
        self.splitter.addWidget(self.form_scroll)
        
        # Initial splitter sizes
        self.splitter.setSizes([300, 300])
        
        layout.addWidget(self.splitter)

    def _run_tag_analysis(self):
        if not self._file_path:
            return
            
        self._tag_worker = TagAnalysisWorker(
            self.tag_analyzer, 
            self._api, 
            self._file_path, 
            self.translator.get_locale()
        )
        self._tag_worker.finished.connect(self._on_tags_analyzed)
        self._tag_worker.error.connect(lambda e: print(f"Tag analysis error: {e}"))
        self._tag_worker.start()

    def _on_tags_analyzed(self, tags: List[str]):
        if tags:
            current_tags = self.form.tags_input.get_tags()
            new_tags = set(current_tags)
            for t in tags:
                if t: new_tags.add(t.strip())
            
            self.form.tags_input.set_tags(sorted(list(new_tags)))

    def _render_preview(self) -> None:
        try:
            if self._file_path:
                self.pdf_viewer.load_document(self._file_path)
            elif self.is_edit_mode and self.doc_to_edit:
                content = self._api.download_document(self.doc_to_edit.id)
                self.pdf_viewer.load_document(content, password=self.doc_to_edit.encryption_key)
        except Exception as e:
            QMessageBox.warning(self, self.translator.tr("common.warning"), f"{self.translator.tr('upload.history_failed').format(err=str(e))}")

    def _on_update_content_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select New PDF", "", "PDF Files (*.pdf *.PDF)")
        if not file_path:
            return
        
        confirm = QMessageBox.question(
            self, 
            self.translator.tr("common.warning"), 
            self.translator.tr("upload.replace_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.form.update_content_btn.setEnabled(False)
            self.form.update_content_btn.setText(self.translator.tr("upload.uploading"))
            self.form.update_content_btn.repaint()
            
            self._api.update_document_content(
                document_id=self.doc_to_edit.id,
                file_path=file_path,
                use_ocr=True # Defaulting to True for now
            )
            
            QMessageBox.information(self, self.translator.tr("common.success"), self.translator.tr("upload.content_success"))
            self.accept() # Close dialog to refresh everything
            
        except Exception as e:
            QMessageBox.critical(self, self.translator.tr("common.error"), f"Failed: {e}")
            self.form.update_content_btn.setEnabled(True)
            self.form.update_content_btn.setText(self.translator.tr("upload.update_content"))

    def _on_save_clicked(self) -> None:
        data = self.form.get_data()
        
        if not data["title"]:
            self.form.display_name_input.setFocus()
            return

        try:
            self.save_btn.setEnabled(False)
            self.save_btn.setText(self.translator.tr("upload.saving"))
            self.save_btn.repaint()
            
            encryption_key = None
            upload_path = self._file_path
            temp_encrypted_path = None

            if self.is_edit_mode:
                print(f"DEBUG Dialog: Updating document {self.doc_to_edit.id}")
                self.resulting_document = self._api.update_document(
                    document_id=self.doc_to_edit.id,
                    title=data["title"],
                    category_id=data["category_id"],
                    file_type_id=data["file_type_id"],
                    is_private=data["is_private"],
                    is_public=data["is_public"],
                    is_public_edit=data["is_public_edit"],
                    is_read_only=data["is_read_only"],
                    notes=data["notes"],
                    tags=data["tags"],
                )
                print(f"DEBUG Dialog: Update completed, resulting_document: {self.resulting_document}")
            else:
                # Encrypt new uploads
                try:
                    encryption_key = secrets.token_urlsafe(16)
                    doc = fitz.open(self._file_path)
                    fd, temp_encrypted_path = tempfile.mkstemp(suffix=".pdf")
                    os.close(fd)
                    
                    doc.save(
                        temp_encrypted_path,
                        garbage=4,
                        deflate=True,
                        encrypt=encryption_key
                    )
                    doc.close()
                    upload_path = temp_encrypted_path
                except Exception as e:
                    print(f"Encryption failed, uploading unencrypted: {e}")
                    encryption_key = None
                    upload_path = self._file_path

                try:
                    # Use the display title as the filename for the upload
                    remote_filename = f"{data['title']}.pdf"
                    
                    self.resulting_document = self._api.upload_file(
                        file_path=upload_path,
                        title=data["title"],
                        category_id=data["category_id"],
                        file_type_id=data["file_type_id"],
                        use_ocr=data.get("use_ocr", True),
                        is_private=data["is_private"],
                        is_public=data["is_public"],
                        is_public_edit=data["is_public_edit"],
                        is_read_only=data["is_read_only"],
                        notes=data["notes"],
                        tags=data["tags"],
                        folder_id=data["folder_id"],
                        override_filename=remote_filename # Pass custom filename
                    )
                finally:
                    if temp_encrypted_path and os.path.exists(temp_encrypted_path):
                        try:
                            os.remove(temp_encrypted_path)
                        except:
                            pass

            self.accept()
        except Exception as e:
            print(f"Save error: {e}")
            self.save_btn.setEnabled(True)
            btn_text = self.translator.tr("common.save") if self.is_edit_mode else self.translator.tr("upload.title_upload")
            self.save_btn.setText(btn_text)
            QMessageBox.critical(self, self.translator.tr("common.error"), f"Save failed: {e}")
