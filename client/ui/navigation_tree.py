from typing import Optional, Any, List
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
    QInputDialog,
    QMessageBox,
    QAbstractItemView
)
from ..api.schemas import APIFolder, APIUser
from ..api_manager import APIManager, APIError
from ..utils.translator import Translator
from ..themes import ThemeManager


class TreeRefreshWorker(QThread):
    """Background worker for fetching folder structure and file counts."""
    finished = pyqtSignal(object)  # emits (my_folders, global_folders, my_docs_count, shared_count)
    error = pyqtSignal(str)
    
    def __init__(self, api: APIManager, user_id: Optional[int]):
        super().__init__()
        self.api = api
        self.user_id = user_id
    
    def run(self):
        try:
            # Fetch folders
            my_folders = self.api.get_folders(owner_id=self.user_id)
            global_folders = self.api.get_folders(public_only=True)

            # Fetch file counts (with max allowed limit)
            my_docs_count = len(self.api.list_documents(folder_id=None, view_mode="my", limit=500))
            shared_count = len(self.api.list_documents(folder_id=None, view_mode="community", limit=500))

            self.finished.emit((my_folders, global_folders, my_docs_count, shared_count))
        except Exception as e:
            self.error.emit(str(e))


class UsersLoadWorker(QThread):
    """Async worker for loading users."""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, api):
        super().__init__()
        self.api = api
    
    def run(self):
        try:
            users = self.api.get_public_users()
            self.finished.emit(users)
        except Exception as e:
            self.error.emit(str(e))


class FoldersLoadWorker(QThread):
    """Async worker for loading user folders."""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, api, owner_id: int):
        super().__init__()
        self.api = api
        self.owner_id = owner_id
    
    def run(self):
        try:
            folders = self.api.get_folders(owner_id=self.owner_id, public_only=True)
            self.finished.emit(folders)
        except Exception as e:
            self.error.emit(str(e))


class NavigationTree(QTreeWidget):
    """
    A widget that displays the folder structure and allows navigation.
    """
    folder_selected = pyqtSignal(object) # Emits view_mode, folder_id, owner_id, path_segments
    folder_changed = pyqtSignal() # Emitted when folders are created/deleted/renamed

    def __init__(self, api: APIManager, parent=None):
        super().__init__(parent)
        self.api = api
        self.translator = Translator()
        self._me_id: Optional[int] = None
        self._is_renaming = False
        self.setMinimumWidth(150)

        self.setHeaderHidden(True)
        self.setObjectName("list")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setDragEnabled(False)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.setDropIndicatorShown(True)

        self.customContextMenuRequested.connect(self._show_folder_context_menu)
        self.itemExpanded.connect(self._on_item_expanded)
        self.itemChanged.connect(self._on_item_renamed)
        self.itemSelectionChanged.connect(self._on_selection_changed)

        # Cache for icons
        self._icon_cache = {}
        
        # Debounce for rapid expansion
        from PyQt6.QtCore import QTimer
        self._expand_debounce_timer = QTimer()
        self._expand_debounce_timer.setSingleShot(True)
        self._expand_debounce_timer.setInterval(200)  # 200ms debounce
        self._expand_debounce_timer.timeout.connect(self._execute_expand)
        self._pending_expand_item = None
        self._pending_expand_data = None

    def _get_folder_icon(self, is_public: bool) -> QIcon:
        key = "public" if is_public else "private"
        if key in self._icon_cache:
            return self._icon_cache[key]

        theme_manager = ThemeManager()
        size = 32 # Render at higher res for High DPI
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pix)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)

        # Scale drawing to new size
        painter.scale(size/16.0, size/16.0)

        # Draw basic folder shape (simplified)
        # Use theme colors for folder parts
        painter.setBrush(QBrush(QColor(theme_manager.get_color("text_secondary"))))
        painter.setPen(Qt.PenStyle.NoPen)
        # Tab
        painter.drawRoundedRect(0, 2, 8, 4, 1, 1)
        # Body
        painter.setBrush(QBrush(QColor(theme_manager.get_color("border"))))
        painter.drawRoundedRect(0, 4, 16, 10, 1, 1)

        # Draw Green Dot if public
        if is_public:
            painter.setBrush(QBrush(QColor(theme_manager.get_color("success")))) # Theme Success
            painter.setPen(QColor(theme_manager.get_color("white"))) # White border for contrast
            painter.drawEllipse(0, 6, 5, 5)

        painter.end()

        icon = QIcon(pix)
        self._icon_cache[key] = icon
        return icon

    def set_current_user_id(self, user_id: int | None):
        self._me_id = user_id

    def _on_selection_changed(self):
        selected_items = self.selectedItems()
        view_mode = "my"
        folder_id: Optional[int] = None
        owner_id: Optional[int] = None
        path_segments = []

        if selected_items:
            item = selected_items[0]
            data = item.data(0, Qt.ItemDataRole.UserRole)

            # Build breadcrumbs
            temp_item = item
            while temp_item:
                path_segments.insert(0, temp_item.text(0))
                temp_item = temp_item.parent()

            if data == "Shared Documents":
                view_mode = "community"
            elif data == "Users":
                view_mode = "community"
            elif isinstance(data, APIUser):
                owner_id = data.id
                view_mode = "community"
            elif isinstance(data, APIFolder):
                folder_id = data.id
                if data.owner_id == self._me_id:
                    view_mode = "my"
                else:
                    view_mode = "community"
            else:
                view_mode = "my"
        else:
            path_segments = [self.translator.tr("main.my_documents")]

        self.folder_selected.emit((view_mode, folder_id, owner_id, path_segments))

    def refresh(self):
        # Store current selection to restore it later
        current_item = self.currentItem()
        selected_data = current_item.data(0, Qt.ItemDataRole.UserRole) if current_item else None

        self.clear()

        # 1. My Documents (Root) - temporary text, will be updated with count
        my_docs = QTreeWidgetItem(self)
        my_docs.setText(0, self.translator.tr("main.my_documents"))
        my_docs.setData(0, Qt.ItemDataRole.UserRole, "My Documents")
        my_docs.setIcon(0, self._get_folder_icon(False))
        my_docs.setExpanded(True)

        # 2. Shared - temporary text, will be updated with count
        shared = QTreeWidgetItem(self)
        shared.setText(0, self.translator.tr("main.shared_documents"))
        shared.setData(0, Qt.ItemDataRole.UserRole, "Shared Documents")
        shared.setIcon(0, self._get_folder_icon(True))

        # 3. Users
        users_root = QTreeWidgetItem(self)
        users_root.setText(0, self.translator.tr("main.users"))
        users_root.setData(0, Qt.ItemDataRole.UserRole, "Users")
        users_root.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)

        # Fetch folders and counts in background
        self._refresh_worker = TreeRefreshWorker(self.api, self._me_id)
        self._refresh_worker.finished.connect(lambda data: self._on_refresh_finished(data, my_docs, shared, users_root, selected_data))
        self._refresh_worker.error.connect(lambda e: print(f"Tree refresh error: {e}"))
        self._refresh_worker.start()
    
    def _on_refresh_finished(self, data, my_docs, shared, users_root, selected_data):
        """Handle background refresh completion."""
        my_folders, global_folders, my_docs_count, shared_count = data
        
        # Update root folder text with counts
        my_docs.setText(0, f"{self.translator.tr('main.my_documents')} ({my_docs_count})")
        shared.setText(0, f"{self.translator.tr('main.shared_documents')} ({shared_count})")
        
        # Build folder tree
        for f in my_folders:
            if f.parent_id is None and not f.is_public:
                self._add_folder_node(my_docs, f, my_folders)

        for f in global_folders:
            if f.parent_id is None:
                self._add_folder_node(shared, f, global_folders)

        my_docs.setExpanded(True)
        shared.setExpanded(True)

        if selected_data:
            self._restore_selection(self.invisibleRootItem(), selected_data)

    def _add_folder_node(self, parent_node, folder_obj, all_folders):
        item = QTreeWidgetItem(parent_node)
        
        # Don't fetch file counts synchronously - causes N+1 blocking
        # Just show folder name without count (counts fetched in background worker)
        item.setText(0, folder_obj.name)
        item.setData(0, Qt.ItemDataRole.UserRole, folder_obj)

        # Set Icon based on public status
        item.setIcon(0, self._get_folder_icon(folder_obj.is_public))

        if folder_obj.owner_id == self._me_id:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

        if folder_obj.is_public:
            item.setToolTip(0, self.translator.tr("nav.public_folder"))

        children = [f for f in all_folders if f.parent_id == folder_obj.id]
        for child in children:
            self._add_folder_node(item, child, all_folders)

    def _restore_selection(self, parent_item: QTreeWidgetItem, target_data: Any):
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole)

            match = False
            if isinstance(data, APIFolder) and isinstance(target_data, APIFolder):
                match = data.id == target_data.id
            elif isinstance(data, APIUser) and isinstance(target_data, APIUser):
                match = data.id == target_data.id
            else:
                match = data == target_data

            if match:
                self.setCurrentItem(child)
                p = child.parent()
                while p:
                    p.setExpanded(True)
                    p = p.parent()
                return True

            if self._restore_selection(child, target_data):
                return True
        return False

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Handle item expansion with debouncing to prevent rapid re-loads."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Skip if already has children (not first expand)
        if item.childCount() > 0:
            return
        
        # Store for debounced execution
        self._pending_expand_item = item
        self._pending_expand_data = data
        
        # Restart debounce timer (stop any pending execution)
        self._expand_debounce_timer.stop()
        self._expand_debounce_timer.start()
    
    def _execute_expand(self):
        """Execute expansion after debounce period."""
        if self._pending_expand_item is None:
            return
        
        item = self._pending_expand_item
        data = self._pending_expand_data
        self._pending_expand_item = None
        self._pending_expand_data = None
        
        # Cancel previous workers to avoid race conditions
        if hasattr(self, '_load_users_worker') and self._load_users_worker.isRunning():
            self._load_users_worker.terminate()
            self._load_users_worker.wait()
        
        if hasattr(self, '_load_folders_worker') and self._load_folders_worker.isRunning():
            self._load_folders_worker.terminate()
            self._load_folders_worker.wait()
        
        if data == "Users":
            # Load users asynchronously to prevent UI freeze
            self._load_users_worker = UsersLoadWorker(self.api)
            self._load_users_worker.finished.connect(
                lambda users: self._on_users_loaded(users, item)
            )
            self._load_users_worker.error.connect(
                lambda e: QMessageBox.critical(self, self.translator.tr("common.error"), f"{self.translator.tr('admin.loading_failed')}: {e}")
            )
            self._load_users_worker.start()

        elif isinstance(data, APIUser):
            # Load user folders asynchronously
            self._load_folders_worker = FoldersLoadWorker(self.api, data.id)
            self._load_folders_worker.finished.connect(
                lambda folders: self._on_user_folders_loaded(folders, item)
            )
            self._load_folders_worker.error.connect(
                lambda e: QMessageBox.critical(self, self.translator.tr("common.error"), f"{self.translator.tr('admin.loading_failed')}: {e}")
            )
            self._load_folders_worker.start()
    
    def _on_users_loaded(self, users, parent_item):
        """Handle async users load."""
        for user in users:
            user_node = QTreeWidgetItem(parent_item)
            user_node.setText(0, user.username)
            user_node.setData(0, Qt.ItemDataRole.UserRole, user)
            user_node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
            user_node.setIcon(0, self._get_folder_icon(False))
    
    def _on_user_folders_loaded(self, folders, parent_item):
        """Handle async user folders load."""
        for f in folders:
            if f.parent_id is None:
                self._add_folder_node(parent_item, f, folders)

    def _on_item_renamed(self, item: QTreeWidgetItem, column: int):
        if not self._is_renaming:
            return

        new_name = item.text(column)
        data = item.data(column, Qt.ItemDataRole.UserRole)

        try:
            if isinstance(data, APIFolder):
                if data.name != new_name:
                    updated_folder = self.api.update_folder(data.id, name=new_name)
                    item.setData(column, Qt.ItemDataRole.UserRole, updated_folder)
        except Exception as e:
            QMessageBox.critical(self, self.translator.tr("context_menu.rename"), str(e))
            item.setText(column, data.name if hasattr(data, 'name') else "")
        finally:
            self._is_renaming = False

    def _show_folder_context_menu(self, position):
        item = self.itemAt(position)
        menu = QMenu()
        data = item.data(0, Qt.ItemDataRole.UserRole) if item else None

        if not item or data in ["Shared Documents", "Users"]:
            menu.addAction(self.translator.tr("context_menu.create_global_folder")).triggered.connect(self._create_global_folder)

        if item:
            is_my_folder = isinstance(data, APIFolder) and data.owner_id == self._me_id

            if data == "My Documents" or is_my_folder:
                menu.addAction(self.translator.tr("context_menu.create_folder")).triggered.connect(lambda: self._create_new_folder(item))

            if is_my_folder:
                menu.addAction(self.translator.tr("context_menu.rename")).triggered.connect(lambda: self._rename_item(item))
                menu.addAction(self.translator.tr("context_menu.delete")).triggered.connect(lambda: self._on_delete_folder_clicked(item))

                is_public = data.is_public
                action_text = self.translator.tr("context_menu.make_private") if is_public else self.translator.tr("context_menu.make_public")
                menu.addAction(action_text).triggered.connect(lambda: self._toggle_folder_public(data))

        menu.exec(self.viewport().mapToGlobal(position))

    def _create_global_folder(self):
        name, ok = QInputDialog.getText(self, self.translator.tr("context_menu.create_global_folder"), self.translator.tr("manage.item_name").format(item=""))
        if ok and name:
            try:
                self.api.create_folder(name, parent_id=None, is_public=True)
                self.refresh()
                self.folder_changed.emit()
            except Exception as e:
                QMessageBox.critical(self, self.translator.tr("common.error"), str(e))

    def _rename_item(self, item: QTreeWidgetItem):
        self._is_renaming = True
        self.editItem(item, 0)

    def _on_delete_folder_clicked(self, item: QTreeWidgetItem):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, APIFolder):
            return

        reply = QMessageBox.question(
            self,
            self.translator.tr("admin.confirm_delete_title"),
            self.translator.tr("manage.confirm_delete").format(name=data.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.api.delete_folder(data.id)
                self.refresh()
                self.folder_changed.emit()
            except Exception as e:
                QMessageBox.critical(self, self.translator.tr("common.error"), str(e))

    def _toggle_folder_public(self, folder: APIFolder):
        try:
            self.api.update_folder(folder.id, is_public=not folder.is_public)
            self.refresh()
            self.folder_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, self.translator.tr("common.error"), str(e))

    def _create_new_folder(self, parent_item: QTreeWidgetItem):
        name, ok = QInputDialog.getText(self, self.translator.tr("context_menu.create_folder"), self.translator.tr("manage.item_name").format(item=""))
        if ok and name:
            parent_data = parent_item.data(0, Qt.ItemDataRole.UserRole)
            parent_id = None
            is_public = False

            if isinstance(parent_data, APIFolder):
                parent_id = parent_data.id
                is_public = parent_data.is_public

            try:
                self.api.create_folder(name, parent_id, is_public)
                self.refresh()
                self.folder_changed.emit()
            except Exception as e:
                QMessageBox.critical(self, self.translator.tr("common.error"), str(e))
