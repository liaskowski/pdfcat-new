import os
import sys
import tempfile
import requests
import qtawesome as qta
from pathlib import Path
from typing import Optional, Any

from PyQt6.QtCore import Qt, QSettings, QByteArray
from PyQt6.QtWidgets import (
    QMessageBox, QApplication, QDialog
)
from PyQt6.QtGui import QPixmap

from ...api_manager import APIDocument, APIFolder, APIUser
from ..auth_dialog import ServerSelectionDialog, LoginDialog
from ..profile_dialog import ProfileDialog
from ..admin_panel import AdminPanelDialog
from ..settings_dialog import SettingsDialog
from ...utils.config_manager import ConfigManager
from ...utils.shortcuts import ShortcutManager
from ...utils.translator import Translator
from ...utils.logger import get_logger, log_info, log_warning, log_debug
from ...themes import LIGHT_THEME_QSS, DARK_THEME_QSS, ThemeManager

from .file_operations import FileOperations
from .search_handler import SearchHandler
from ...utils.workers import OCRWorker, AvatarWorker
from ...api.config import config

logger = get_logger("client.main_controller")

class MainController:
    def __init__(self, main_window, layout, api_manager):
        self.view = main_window
        self.ui = layout
        self.api = api_manager
        self.config = ConfigManager()
        self.translator = Translator()
        
        self._me: Optional[dict[str, Any]] = None
        self._me_id: Optional[int] = None
        self._clipboard: dict[str, Any] = {"doc_id": None, "action": None}
        
        # Sub-handlers
        self.file_ops = FileOperations(self)
        self.search_handler = SearchHandler(self)
        
        # Shortcut Manager
        self.shortcut_manager = ShortcutManager(self.view)
        
    def start(self) -> bool:
        self._apply_styles()
        self._restore_splitter_state()
        self._connect_signals()
        self._setup_shortcuts()
        
        # Always require explicit authentication on startup
        return self._ensure_authenticated()
    
    def _restore_session(self) -> bool:
        """
        Restore previous session if "Remember Me" was checked.
        Returns True if auto-login successful, False otherwise.
        """
        from PyQt6.QtCore import QSettings
        from ...utils.logger import log_info, log_warning, log_debug
        
        s = QSettings("pdflib", "client")

        token = s.value("token")
        base_url = s.value("base_url")

        if not token or not base_url:
            log_debug("main_controller", "No saved session found")
            return False  # No saved session

        # Fix URL if missing scheme
        if not base_url.startswith("http://") and not base_url.startswith("https://"):
            if base_url.startswith("127.0.0.1") or base_url.startswith("localhost"):
                base_url = f"http://{base_url}:8000"
            else:
                base_url = f"http://{base_url}"
            
            # Save the corrected URL
            s.setValue("base_url", base_url)
            log_info("main_controller", f"Fixed base_url to: {base_url}")

        log_info("main_controller", f"Attempting to restore session... Token: {str(token)[:10]}... URL: {base_url}")

        # Restore settings
        self.api.set_token(str(token))
        # Also update API base_url if needed
        if hasattr(self.api, 'base_url') and self.api.base_url != base_url.rstrip('/'):
            self.api.base_url = base_url.rstrip('/')
            from ...api.config import config
            config.set_base_url(base_url)

        # Try to validate token by fetching user info
        try:
            self._me = self.api.get_me()
            self._me_id = int(self._me["id"]) if self._me else None
            role = self._me.get("role") if self._me else None

            username = str(self._me.get("username", "User")) if self._me else "User"
            is_admin = role == "admin"
            self.ui.title_bar.update_user_info(is_admin, username)

            # Load avatar
            avatar_url = self._me.get("avatar_url") if self._me else None
            if avatar_url:
                self._load_avatar(avatar_url)
            else:
                self.ui.title_bar.set_default_avatar()

            # Initialize UI
            self.ui.file_grid.set_context(self._me_id, role)
            self.search_handler.load_filter_combos()
            self.ui.nav_tree.refresh()

            log_info("main_controller", f"Session restored for user: {username}")
            return True  # Auto-login successful

        except Exception as e:
            # Token expired or invalid
            log_warning("main_controller", f"Session expired, re-authentication required: {e}")
            s.remove("token")
            s.remove("base_url")
            return False

    def update_progress(self, value: int, message: str = ""):
        if hasattr(self.view, "update_progress"):
            self.view.update_progress(value, message)

    def update_status(self, message: str, timeout: int = 3000):
        if hasattr(self.view, "update_status"):
            self.view.update_status(message, timeout)

    def _connect_signals(self):
        self.ui.nav_tree.folder_selected.connect(self._on_folder_selected)
        self.ui.nav_tree.folder_changed.connect(self.search_handler.fetch_from_server)
        self.ui.search_bar.search_triggered.connect(self.search_handler.fetch_from_server)
        self.ui.search_bar.shift_enter_pressed.connect(self._on_search_shift_enter)

        self.ui.file_grid.file_selected.connect(self._on_file_selected_from_grid)
        self.ui.file_grid.file_double_clicked.connect(self._on_file_double_clicked)
        
        # File Grid Actions
        self.ui.file_grid.open_requested.connect(self.file_ops.on_open_file_clicked)
        self.ui.file_grid.download_requested.connect(self.file_ops.on_download_clicked)
        self.ui.file_grid.copy_requested.connect(self._on_copy_clicked)
        self.ui.file_grid.cut_requested.connect(self._on_cut_clicked)
        self.ui.file_grid.paste_requested.connect(self._on_paste_clicked)
        self.ui.file_grid.delete_requested.connect(self.file_ops.on_delete_clicked)
        self.ui.file_grid.edit_requested.connect(self.file_ops.on_edit_clicked)
        self.ui.file_grid.rename_requested.connect(self.file_ops.rename_file)
        
        # Preview Panel Actions
        self.ui.preview_panel.open_file.connect(self.file_ops.on_open_file_clicked)
        self.ui.preview_panel.edit_file.connect(self.file_ops.on_edit_clicked)
        self.ui.preview_panel.download_file.connect(self.file_ops.on_download_clicked)
        self.ui.preview_panel.delete_file.connect(self.file_ops.on_delete_clicked)
        self.ui.preview_panel.tag_clicked.connect(self._on_tag_clicked)
        # Assuming there's an ocr_clicked signal or button in preview_panel
        if hasattr(self.ui.preview_panel, "ocr_clicked"):
            self.ui.preview_panel.ocr_clicked.connect(self.file_ops.on_ocr_clicked)

        self.ui.add_pdf_btn.clicked.connect(self.file_ops.on_add_pdf_clicked)
        self.ui.sort_combo.currentIndexChanged.connect(self._on_sort_changed)

        # Drag and Drop
        self.view.drop_event_requested.connect(self.handle_drop)
        
        # Auto-refresh timer (Sync) - Start with 10 second interval
        from PyQt6.QtCore import QTimer
        self.refresh_timer = QTimer(self.view)
        self.refresh_timer.timeout.connect(self._auto_refresh)
        self.refresh_timer.start(10000) # Every 10 seconds
        
        # Track if recent change occurred for faster sync
        self._recent_change_timer = QTimer(self.view)
        self._recent_change_timer.setSingleShot(True)
        self._recent_change_timer.setInterval(3000)  # 3 seconds of "recent change" state
        self._recent_change_timer.timeout.connect(self._on_recent_change_expired)
        self._has_recent_change = False
        
        # Title Bar Signals
        self.ui.title_bar.minimize_clicked.connect(self.view.showMinimized)
        self.ui.title_bar.maximize_restore_clicked.connect(self._toggle_maximize)
        self.ui.title_bar.close_clicked.connect(self.view.close)
        self.ui.title_bar.admin_clicked.connect(self._on_admin_clicked)
        self.ui.title_bar.profile_clicked.connect(self._on_profile_clicked)
        self.ui.title_bar.settings_clicked.connect(self._on_settings_clicked)

    def _setup_shortcuts(self):
        self.shortcut_manager.setup_standard_shortcuts(
            cut_cb=self._on_cut_shortcut,
            copy_cb=self._on_copy_shortcut,
            paste_cb=self._on_paste_shortcut,
            rename_cb=self._on_rename_shortcut
        )

    def _on_rename_shortcut(self):
        # Get selected doc from grid or preview
        doc = self.ui.preview_panel._document
        if doc:
            self.file_ops.rename_file(doc)

    def _restore_splitter_state(self):
        state_hex = self.config.get("splitter_state")
        if state_hex:
            self.ui.restore_splitter_state(state_hex)

    def save_state(self):
        state = self.ui.save_splitter_state()
        self.config.set("splitter_state", state)
        self.config.save()

    def _toggle_maximize(self):
        if self.view.isMaximized():
            self.view.showNormal()
        else:
            self.view.showMaximized()
        # Update title bar icons to reflect new state
        theme = self.config.get("theme")
        self.ui.title_bar.update_theme(theme)

    def _on_cut_shortcut(self):
        doc = self.ui.preview_panel._document
        if doc: self._on_cut_clicked(doc)

    def _on_copy_shortcut(self):
        doc = self.ui.preview_panel._document
        if doc: self._on_copy_clicked(doc)

    def _on_paste_shortcut(self):
        self._on_paste_clicked()

    def _on_folder_selected(self, data):
        view_mode, folder_id, owner_id, path_segments = data
        self.ui.breadcrumbs.setText(" > ".join(path_segments))
        self.search_handler.fetch_from_server(view_mode, folder_id, owner_id)

    def _on_file_double_clicked(self, doc: APIDocument):
        self.file_ops.on_open_file_clicked(doc.id)
            
    def _on_file_selected_from_grid(self, doc: APIDocument | None):
        is_admin = self._me.get("role") == "admin" if self._me else False
        self.ui.preview_panel.set_document(doc, self._me_id, is_admin)
        if doc:
            self.update_status(self.translator.tr("preview.title") + f": {doc.title}")

    def _on_sort_changed(self, index: int):
        mode = self.ui.sort_combo.currentData()
        if mode:
            # Block signals while sorting to prevent re-triggering
            self.ui.sort_combo.blockSignals(True)
            self.ui.file_grid.sort_items(mode)
            self.ui.sort_combo.blockSignals(False)

    def _on_search_shift_enter(self):
        """
        Handle Shift+Enter from search bar:
        Open the first document from search results and highlight search term.
        """
        query = self.ui.search_bar.text()
        if not query:
            return

        # Get first document from the current view (file_grid)
        items = self.ui.file_grid.files_list.findItems("*", Qt.MatchFlag.MatchWildcard)
        if not items:
            return
            
        first_item = items[0]
        doc = first_item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(doc, APIDocument):
            return

        # Open file in viewer and highlight
        self.file_ops.on_open_file_clicked(doc.id, search_query=query)

    def _on_tag_clicked(self, tag_query: str):
        self.ui.search_bar.search_input.setText(tag_query)
        self.search_handler.fetch_from_server()

    def _on_copy_clicked(self, doc: APIDocument):
        self._clipboard = {"doc_id": doc.id, "action": "copy"}
        self.ui.file_grid.set_clipboard_state(doc.id)
        self.view.statusBar().showMessage(self.translator.tr("main.copied_msg").format(name=doc.title), 3000)

    def _on_cut_clicked(self, doc: APIDocument):
        self._clipboard = {"doc_id": doc.id, "action": "cut"}
        self.ui.file_grid.set_clipboard_state(doc.id)
        self.view.statusBar().showMessage(self.translator.tr("main.cut_msg").format(name=doc.title), 3000)

    def _on_paste_clicked(self):
        if not self._clipboard["doc_id"]:
            return

        # Get target folder from nav tree
        selected_items = self.ui.nav_tree.selectedItems()
        target_folder_id = None
        if selected_items:
            # item.data(0, ...) holds the folder object or None
            data = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, APIFolder):
                target_folder_id = data.id
            else:
                # Might be a virtual node like "My Files" or "Public"
                # Check if it's in a view mode that implies a folder
                pass

        try:
            action = self._clipboard["action"]
            doc_id = self._clipboard["doc_id"]

            logger.info(f"Pasting document {doc_id} (action: {action}) into folder {target_folder_id}")

            if action == "cut":
                # Fetch document metadata to preserve all fields during update
                doc = self.api.get_document(doc_id)
                self.api.update_document(
                    document_id=doc_id,
                    title=doc.title,
                    category_id=doc.category.id if doc.category else None,
                    file_type_id=doc.file_type.id if doc.file_type else None,
                    is_private=doc.is_private,
                    is_public=doc.is_public,
                    is_public_edit=doc.is_public_edit,
                    notes=doc.notes or "",
                    is_read_only=doc.is_read_only,
                    tags=doc.tags,
                    folder_id=target_folder_id
                )
                self.view.statusBar().showMessage(self.translator.tr("main.moved_success"), 3000)
            else:
                self.api.duplicate_document(doc_id, target_folder_id)
                self.view.statusBar().showMessage(self.translator.tr("main.copied_success"), 3000)

            # Clear clipboard and refresh UI
            self._clipboard = {"doc_id": None, "action": None}
            self.ui.file_grid.set_clipboard_state(None)
            
            # Trigger immediate sync for better synchronization
            self._trigger_immediate_sync()
            self.search_handler.fetch_from_server()

        except Exception as e:
            logger.error(f"Paste Failed: {e}")
            self._show_error(self.translator.tr("common.error"), f"Paste Failed: {e}")

    def _auto_refresh(self):
        """Periodically refresh the current view to show changes from other users."""
        if not self._me:
            return

        # Only refresh if the window is active and no dialog is open
        if not self.view.isActiveWindow():
            return

        # Refresh current folder/search view silently (no loading shimmer)
        logger.debug("Auto-refreshing current view...")
        mode, fid, oid = self.search_handler.current_view_params
        self.search_handler.fetch_from_server(view_mode=mode, folder_id=fid, owner_id=oid, load_all=False)
    
    def _trigger_immediate_sync(self):
        """Trigger an immediate synchronization with the server."""
        logger.info("Triggering immediate sync due to recent changes...")
        # Mark that a recent change occurred
        self._has_recent_change = True
        self._recent_change_timer.start()  # Reset the timer
        
        # Force refresh navigation tree to sync folder structure across clients
        self.ui.nav_tree.force_refresh()
        
        # Force fresh fetch of current view (bypass cache)
        mode, fid, oid = self.search_handler.current_view_params
        self.search_handler.fetch_from_server(view_mode=mode, folder_id=fid, owner_id=oid, force_fresh=True)
    
    def _on_recent_change_expired(self):
        """Called when the recent change timer expires."""
        self._has_recent_change = False
        logger.debug("Recent change state expired, returning to normal refresh interval")

    def _ensure_authenticated_or_exit(self) -> None:
        if not self._ensure_authenticated():
            QApplication.instance().quit()

    def _ensure_authenticated(self) -> bool:
        # Step 1: Select Server
        server_dlg = ServerSelectionDialog(parent=None)
        if server_dlg.exec() != QDialog.DialogCode.Accepted or not server_dlg.selected_profile:
            return False
            
        profile = server_dlg.selected_profile
        self.api.base_url = profile['url'].rstrip('/')
        
        # Step 2: Login
        login_dlg = LoginDialog(self.api, profile, parent=None)
        if login_dlg.exec() != QDialog.DialogCode.Accepted or not login_dlg.token:
            return False

        token = login_dlg.token
        
        settings = QSettings("pdflib", "client")
        settings.setValue("token", token)
        self.api.set_token(token)
        try:
            self._me = self.api.get_me()
            self._me_id = int(self._me["id"]) if self._me else None
            role = self._me.get("role") if self._me else None
            
            username = str(self._me.get("username", "User")) if self._me else "User"
            is_admin = role == "admin"
            self.ui.title_bar.update_user_info(is_admin, username)
            
            avatar_url = self._me.get("avatar_url") if self._me else None
            if avatar_url:
                self._load_avatar(avatar_url)
            else:
                self.ui.title_bar.set_default_avatar()

            self.ui.file_grid.set_context(self._me_id, role)
            self.ui.nav_tree.set_current_user_id(self._me_id)

            self.search_handler.load_filter_combos()
            self.ui.nav_tree.refresh()
            return True
        except Exception as e:
            self._show_error(self.translator.tr("auth.login_failed"), str(e))
            return False

    def _load_avatar(self, url: str):
        if not url:
            self.ui.title_bar.set_default_avatar()
            return
            
        full_url = url if url.startswith("http") else f"{self.api.base_url}/{url.lstrip('/')}"
            
        # Use AvatarWorker for non-blocking load
        self._avatar_worker = AvatarWorker(self.api, full_url)
        self._avatar_worker.finished.connect(self.ui.title_bar.set_avatar)
        self._avatar_worker.error.connect(lambda e: self.ui.title_bar.set_default_avatar())
        self._avatar_worker.start()

    def _on_profile_clicked(self):
        if not self._me: return
        dlg = ProfileDialog(self.api, self._me, self.view)
        result = dlg.exec() 
        
        if dlg.logout_requested:
            self._on_logout_clicked()
            return
            
        if result:
            # Refresh user data
            try:
                self._me = self.api.get_me()
                self._me_id = int(self._me["id"])
                username = self._me.get("username", "User")
                is_admin = self._me.get("role") == "admin"
                self.ui.title_bar.update_user_info(is_admin, username)
                
                avatar_url = self._me.get("avatar_url")
                if avatar_url:
                     self._load_avatar(avatar_url)
            except Exception as e:
                self._show_error("Refresh Failed", str(e))

    def _on_admin_clicked(self):
        if not self._me or self._me.get("role") != "admin":
            return
        dlg = AdminPanelDialog(self.api, self.view)
        dlg.exec()

    def _on_settings_clicked(self):
        is_admin = self._me.get("role") == "admin" if self._me else False
        dlg = SettingsDialog(self.api, is_admin, self.view)
        result = dlg.exec()
        if result == 2: # Restart code
            self.restart_app()
        elif result == 1: # Accepted
            self._apply_styles()

    def restart_app(self):
        """Restarts the current application using subprocess for Windows compatibility."""
        import subprocess
        print("DEBUG: Restarting application via subprocess...")
        self.save_state()
        
        # Use sys.executable and -m client.main to ensure proper module loading
        # Wrapping in quotes is handled by subprocess when passing as list
        args = [sys.executable, "-m", "client.main"]
        
        try:
            subprocess.Popen(args)
            QApplication.quit()
            sys.exit(0)
        except Exception as e:
            sys.stderr.write(f"RESTART FAILED: {e}\n")
            QMessageBox.critical(self.view, "Restart Failed", f"Could not restart: {e}")

    def _on_logout_clicked(self) -> None:
        settings = QSettings("pdflib", "client")
        
        # Clear session
        settings.remove("token")
        settings.remove("base_url")
        
        # Clear API token
        self.api.set_token(None)
        
        # Reset user state
        self._me = None
        self._me_id = None
        
        # Update UI
        self.ui.title_bar.update_user_info(False, "User")
        self.ui.title_bar.set_default_avatar()
        self.ui.search_bar.search_input.setText("")
        self.ui.search_bar.populate_filter_combos([], [])
        self.ui.nav_tree.set_current_user_id(None)
        self.ui.nav_tree.refresh()
        self.ui.file_grid.set_context(None, None)
        self.ui.file_grid.rebuild_with_files([], self.view._make_pdf_icon(64))
        self.ui.preview_panel.set_document(None)
        
        # Re-authenticate
        self._ensure_authenticated_or_exit()

    def _show_error(self, title: str, message: str) -> None: 
        QMessageBox.critical(self.view, title, message)

    def _apply_styles(self) -> None:
        theme = self.config.get("theme")
        font_size = self.config.get("font_size")
        scale_percent = self.config.get("scale", 100)
        
        try:
            scale_factor = int(scale_percent) / 100.0
        except:
            scale_factor = 1.0

        self._apply_ui_scale(scale_factor, font_size)
        ThemeManager().set_theme(theme)
        
        # Update Title Bar Theme & Icons
        self.ui.title_bar.update_theme(theme)
        
        tm = ThemeManager()
        icon_color = tm.get_icon_color()
        from PyQt6.QtCore import QSize
        icon_size = QSize(20, 20)
        
        # Update Preview Panel Icons
        self.ui.preview_panel.open_file_btn.setIcon(qta.icon('fa5s.external-link-alt', color=icon_color))
        self.ui.preview_panel.open_file_btn.setIconSize(icon_size)
        
        self.ui.preview_panel.edit_btn.setIcon(qta.icon('fa5s.edit', color=icon_color))
        self.ui.preview_panel.edit_btn.setIconSize(icon_size)
        
        self.ui.preview_panel.download_btn.setIcon(qta.icon('fa5s.download', color=icon_color))
        self.ui.preview_panel.download_btn.setIconSize(icon_size)
        
        self.ui.preview_panel.delete_btn.setIcon(qta.icon('fa5s.trash-alt', color=icon_color))
        self.ui.preview_panel.delete_btn.setIconSize(icon_size)

        style = DARK_THEME_QSS if theme == "Dark" else LIGHT_THEME_QSS
        font_qss = f"\nQWidget {{ font-size: {int(font_size * scale_factor)}pt; }}\n"
        
        # Apply style to the whole application - this is much more efficient
        app = QApplication.instance()
        if app:
            app.setStyleSheet(style + font_qss)
        
        # Specific updates for custom windows that might not auto-refresh
        from ..viewer_window import FileViewerWindow
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, FileViewerWindow):
                widget.apply_theme(theme)
        
        bg = tm.get_color("background")
        text = tm.get_color("text")
        border = tm.get_color("border")
        sel_bg = tm.get_color("primary")
        sel_text = tm.get_color("white")
        
        popup_style = f"""
            QListView {{ background-color: {bg}; color: {text}; border: 1px solid {border}; border-radius: 6px; padding: 4px; }}
            QListView::item {{ padding: 5px 10px; border-radius: 4px; }}
            QListView::item:selected {{ background-color: {sel_bg}; color: {sel_text}; }}
        """
        self.ui.search_bar.set_completer_style(popup_style)

    def _apply_ui_scale(self, factor: float, base_font_size: int):
        if hasattr(self.ui.title_bar, 'update_scale'):
            self.ui.title_bar.update_scale(factor)
        if hasattr(self.ui.preview_panel.preview_widget, 'update_scale'):
            self.ui.preview_panel.preview_widget.update_scale(factor)

    def handle_drop(self, event, tree_pos):
        """Handle drag-and-drop events from MainWindow"""
        self.file_ops.handle_drop(event, tree_pos)
