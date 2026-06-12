from typing import Optional, Any, List
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, QSize, QTimer, QRect, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath
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
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    def __init__(self, api: APIManager, user_id: Optional[int]):
        super().__init__()
        self.api = api; self.user_id = user_id
    def run(self):
        try:
            my_f = self.api.get_folders(owner_id=self.user_id)
            pub_f = self.api.get_folders(public_only=True)
            my_c = len(self.api.list_documents(folder_id=None, view_mode="my", limit=500))
            pub_c = len(self.api.list_documents(folder_id=None, view_mode="community", limit=500))
            self.finished.emit((my_f, pub_f, my_c, pub_c))
        except Exception as e: self.error.emit(str(e))

class UsersLoadWorker(QThread):
    finished = pyqtSignal(list); error = pyqtSignal(str)
    def __init__(self, api): super().__init__(); self.api = api
    def run(self):
        try: u = self.api.get_public_users(); self.finished.emit(u)
        except Exception as e: self.error.emit(str(e))

class FoldersLoadWorker(QThread):
    finished = pyqtSignal(list); error = pyqtSignal(str)
    def __init__(self, api, owner_id: int): super().__init__(); self.api = api; self.owner_id = owner_id
    def run(self):
        try: f = self.api.get_folders(owner_id=self.owner_id, public_only=True); self.finished.emit(f)
        except Exception as e: self.error.emit(str(e))

class NavigationTree(QTreeWidget):
    folder_selected = pyqtSignal(object)
    folder_changed = pyqtSignal()

    def __init__(self, api: APIManager, parent=None):
        super().__init__(parent)
        self.api = api; self.translator = Translator(); self._me_id = None; self._is_renaming = False
        self._workers = []
        self.setMinimumWidth(180); self.setHeaderHidden(True); self.setObjectName("list")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setIndentation(20); self.setAnimated(True); self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setRootIsDecorated(True)
        self.itemExpanded.connect(self._on_item_expanded)
        self.itemChanged.connect(self._on_item_renamed)
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.customContextMenuRequested.connect(self._show_folder_context_menu)
        self._icon_cache = {}
        self._expand_timer = QTimer(self); self._expand_timer.setSingleShot(True)
        self._expand_timer.timeout.connect(self._do_expand)
        self._pending_item = None

    def _stop_workers(self):
        for w in self._workers:
            if w.isRunning():
                w.blockSignals(True); w.terminate(); w.wait()
        self._workers.clear()

    def _start_worker(self, w): self._workers.append(w); w.start(); return w

    def drawBranches(self, painter, rect, index):
        if not self.model().hasChildren(index): return
        painter.save(); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tm = ThemeManager()
        is_sel = self.selectionModel().isSelected(index)
        col = QColor(tm.get_color("primary") if is_sel else tm.get_color("text_secondary"))
        painter.setPen(QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        cx, cy = rect.center().x() + 2, rect.center().y()
        if self.isExpanded(index):
            painter.drawLine(cx-3, cy-1, cx, cy+2); painter.drawLine(cx, cy+2, cx+3, cy-1)
        else:
            painter.drawLine(cx-2, cy-3, cx+1, cy); painter.drawLine(cx+1, cy, cx-2, cy+3)
        painter.restore()

    def _get_folder_icon(self, is_public: bool) -> QIcon:
        key = "pub" if is_public else "priv"
        if key in self._icon_cache: return self._icon_cache[key]
        tm = ThemeManager(); pix = QPixmap(24, 24); pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix); p.setRenderHints(QPainter.RenderHint.Antialiasing); p.scale(24/16.0, 24/16.0)
        col = QColor(tm.get_color("primary")); p.setPen(QPen(col, 1.2))
        p.setBrush(QBrush(QColor(col.red(), col.green(), col.blue(), 40)))
        tab = QPainterPath(); tab.addRoundedRect(1, 2, 6, 4, 1, 1); p.drawPath(tab)
        p.drawRoundedRect(1, 4, 14, 10, 2, 2)
        if is_public:
            p.setBrush(QBrush(QColor(tm.get_color("success")))); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(12, 10, 3, 3)
        p.end(); ic = QIcon(pix); self._icon_cache[key] = ic; return ic

    def set_current_user_id(self, uid): self._me_id = uid

    def _on_selection_changed(self):
        items = self.selectedItems()
        mode, fid, oid, path = "my", None, None, []
        if items:
            it = items[0]; data = it.data(0, Qt.ItemDataRole.UserRole)
            tmp = it
            while tmp: path.insert(0, tmp.text(0)); tmp = tmp.parent()
            if data == "Shared Documents": mode = "community"
            elif data == "Users": mode = "community"
            elif isinstance(data, APIUser): oid, mode = data.id, "community"
            elif isinstance(data, APIFolder):
                fid = data.id; mode = "my" if data.owner_id == self._me_id else "community"
        else: path = [self.translator.tr("main.my_documents")]
        self.folder_selected.emit((mode, fid, oid, path))

    def refresh(self):
        self._stop_workers(); cur = self.currentItem()
        sel_data = cur.data(0, Qt.ItemDataRole.UserRole) if cur else None
        self.clear()
        my = QTreeWidgetItem(self); my.setText(0, self.translator.tr("main.my_documents"))
        my.setData(0, Qt.ItemDataRole.UserRole, "My Documents"); my.setIcon(0, self._get_folder_icon(False))
        my.setData(0, Qt.ItemDataRole.SizeHintRole, QSize(0, 32)); my.setExpanded(True)
        sh = QTreeWidgetItem(self); sh.setText(0, self.translator.tr("main.shared_documents"))
        sh.setData(0, Qt.ItemDataRole.UserRole, "Shared Documents"); sh.setIcon(0, self._get_folder_icon(True))
        sh.setData(0, Qt.ItemDataRole.SizeHintRole, QSize(0, 32))
        us = QTreeWidgetItem(self); us.setText(0, self.translator.tr("main.users"))
        us.setData(0, Qt.ItemDataRole.UserRole, "Users"); us.setData(0, Qt.ItemDataRole.SizeHintRole, QSize(0, 32))
        us.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        w = TreeRefreshWorker(self.api, self._me_id)
        w.finished.connect(lambda d: self._on_ref_done(d, my, sh, us, sel_data))
        self._start_worker(w)

    def _on_ref_done(self, data, my_node, sh_node, us_root, sel):
        my_f, pub_f, my_c, pub_c = data
        my_node.setText(0, f"{self.translator.tr('main.my_documents')} ({my_c})")
        sh_node.setText(0, f"{self.translator.tr('main.shared_documents')} ({pub_c})")
        for f in my_f:
            if f.parent_id is None and not f.is_public: self._add_node(my_node, f, my_f)
        for f in pub_f:
            if f.parent_id is None: self._add_node(sh_node, f, pub_f)
        my_node.setExpanded(True); sh_node.setExpanded(True)
        if sel: self._restore_sel(self.invisibleRootItem(), sel)

    def _add_node(self, parent, folder, all_f):
        it = QTreeWidgetItem(parent); it.setText(0, folder.name); it.setData(0, Qt.ItemDataRole.UserRole, folder)
        it.setIcon(0, self._get_folder_icon(folder.is_public)); it.setData(0, Qt.ItemDataRole.SizeHintRole, QSize(0, 30))
        if folder.owner_id == self._me_id: it.setFlags(it.flags() | Qt.ItemFlag.ItemIsEditable)
        for c in [f for f in all_f if f.parent_id == folder.id]: self._add_node(it, c, all_f)

    def _restore_sel(self, parent, target):
        for i in range(parent.childCount()):
            c = parent.child(i); d = c.data(0, Qt.ItemDataRole.UserRole)
            match = False
            if isinstance(d, APIFolder) and isinstance(target, APIFolder): match = d.id == target.id
            elif isinstance(d, APIUser) and isinstance(target, APIUser): match = d.id == target.id
            else: match = d == target
            if match:
                self.setCurrentItem(c); p = c.parent()
                while p: p.setExpanded(True); p = p.parent()
                return True
            if self._restore_sel(c, target): return True
        return False

    def _on_item_expanded(self, it):
        if it.childCount() > 0: return
        self._pending_item = it; self._expand_timer.start(150)

    def _do_expand(self):
        if not self._pending_item: return
        it = self._pending_item; self._pending_item = None
        data = it.data(0, Qt.ItemDataRole.UserRole)
        if data == "Users":
            w = UsersLoadWorker(self.api); w.finished.connect(lambda u: self._fill_users(u, it)); self._start_worker(w)
        elif isinstance(data, APIUser):
            w = FoldersLoadWorker(self.api, data.id); w.finished.connect(lambda f: self._fill_user_f(f, it)); self._start_worker(w)

    def _fill_users(self, users, parent):
        for u in users:
            n = QTreeWidgetItem(parent); n.setText(0, u.username); n.setData(0, Qt.ItemDataRole.UserRole, u)
            n.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator); n.setIcon(0, self._get_folder_icon(False))
            n.setData(0, Qt.ItemDataRole.SizeHintRole, QSize(0, 30))

    def _fill_user_f(self, folders, parent):
        for f in folders:
            if f.parent_id is None: self._add_node(parent, f, folders)

    def _on_item_renamed(self, it, col):
        if not self._is_renaming: return
        name, data = it.text(col), it.data(col, Qt.ItemDataRole.UserRole)
        try:
            if isinstance(data, APIFolder) and data.name != name:
                new_f = self.api.update_folder(data.id, name=name); it.setData(col, Qt.ItemDataRole.UserRole, new_f)
                self.folder_changed.emit()
        except Exception as e: QMessageBox.critical(self, "Error", str(e)); it.setText(col, data.name)
        finally: self._is_renaming = False

    def _show_folder_context_menu(self, pos):
        it = self.itemAt(pos); m = QMenu(); d = it.data(0, Qt.ItemDataRole.UserRole) if it else None
        if not it or d in ["Shared Documents", "Users"]:
            m.addAction(self.translator.tr("context_menu.create_global_folder")).triggered.connect(self._create_global)
        if it:
            is_own = isinstance(d, APIFolder) and d.owner_id == self._me_id
            if d == "My Documents" or is_own: m.addAction(self.translator.tr("context_menu.create_folder")).triggered.connect(lambda: self._create_new(it))
            if is_own:
                m.addAction(self.translator.tr("context_menu.rename")).triggered.connect(lambda: self._start_ren(it))
                m.addAction(self.translator.tr("context_menu.delete")).triggered.connect(lambda: self._del_f(it))
                txt = self.translator.tr("context_menu.make_private" if d.is_public else "context_menu.make_public")
                m.addAction(txt).triggered.connect(lambda: self._toggle_pub(d))
        m.exec(self.viewport().mapToGlobal(pos))

    def _create_global(self):
        n, ok = QInputDialog.getText(self, "Global Folder", "Name:")
        if ok and n: self.api.create_folder(n, is_public=True); self.refresh()
    def _create_new(self, it):
        n, ok = QInputDialog.getText(self, "New Folder", "Name:")
        if ok and n:
            d = it.data(0, Qt.ItemDataRole.UserRole)
            pid = d.id if isinstance(d, APIFolder) else None
            pub = d.is_public if isinstance(d, APIFolder) else (True if d == "Shared Documents" else False)
            self.api.create_folder(n, parent_id=pid, is_public=pub); self.refresh()
    def _start_ren(self, it): self._is_renaming = True; self.editItem(it, 0)
    def _del_f(self, it):
        d = it.data(0, Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self, "Delete", f"Delete {d.name}?") == QMessageBox.StandardButton.Yes:
            self.api.delete_folder(d.id); self.refresh()
    def _toggle_pub(self, f): self.api.update_folder(f.id, is_public=not f.is_public); self.refresh()
    def closeEvent(self, ev): self._stop_workers(); super().closeEvent(ev)
