"""
High-Performance Document Grid. 
Manual painting for zero-clipping, zero-crash, and fluid animations.
"""
from typing import Optional, List
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QThreadPool, QStandardPaths, QByteArray, QBuffer, QTimer, QRect, QPoint, QPointF, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QIcon, QPainter, QColor, QBrush, QPixmap, QPen, QLinearGradient, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QMenu, QWidget,
    QScrollArea, QGridLayout, QSizePolicy, QLayout
)
import json, os, sys

from ..api_manager import APIManager, APIDocument
from .thumbnail_runnable import ThumbnailRunnable
from ..utils.translator import Translator
from ..themes import ThemeManager


class DocumentTileWidget(QWidget):
    clicked = pyqtSignal(object)

    def __init__(self, doc: APIDocument, parent=None):
        super().__init__(parent)
        self.doc = doc; self._sel = False; self._hover = False
        self._opacity = 0.0; self._scale = 1.0; self._thumb_pm = None
        self.setFixedSize(180, 220)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        
        # Tooltip with clear colors
        tm = ThemeManager(); dark = tm.current_theme == "Dark"
        txt_sec = tm.get_color("text_secondary")
        size_str = f"{doc.file_size / (1024*1024):.1f} MB" if doc.file_size and doc.file_size > 1024*1024 else f"{(doc.file_size or 0)/1024:.1f} KB"
        path_str = doc.folder_full_path if hasattr(doc, 'folder_full_path') and doc.folder_full_path else "Root"
        
        info = [
            f"<b>{doc.title}</b>",
            f"Size: {size_str}",
            f"Owner: {doc.owner_username or 'N/A'}",
            f"<span style='color:{txt_sec}'>At: 📂 {path_str}</span>"
        ]
        if doc.notes: info.append(f"<hr><i>{doc.notes[:60]}...</i>")
        self.setToolTip("<br>".join(info))

        self._sel_col = QColor("#3b82f6" if dark else "#007AFF")
        self._bg_muted = QColor(tm.get_color("hover") if dark else "#E8E8E8")
        self._txt_col = QColor(tm.get_color("text"))

    @pyqtProperty(float)
    def scale_val(self): return self._scale
    @scale_val.setter
    def scale_val(self, v): self._scale = v; self.update()

    def start_entrance_anim(self, delay=0):
        self._t = QTimer(self); self._t.timeout.connect(self._fade_tick)
        # Fix: PyQt6 singleShot doesn't support passing arguments to slot directly as 3rd param
        QTimer.singleShot(delay, lambda: self._t.start(16))

    def _fade_tick(self):
        self._opacity += 0.08
        if self._opacity >= 1.0: self._opacity = 1.0; self._t.stop()
        self.update()

    def set_thumbnail(self, pm):
        if not pm.isNull():
            self._thumb_pm = pm.scaled(160, 105, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.update()

    def enterEvent(self, ev):
        self._hover = True
        self._anim = QPropertyAnimation(self, b"scale_val")
        self._anim.setDuration(150); self._anim.setEndValue(1.04); self._anim.start()
        
        # UX: Show detailed info in status bar
        p = self.parent()
        while p and not hasattr(p, 'api'): p = p.parent()
        if hasattr(p, 'view') and hasattr(p.view, 'statusBar'):
            path_str = self.doc.folder_full_path if hasattr(self.doc, 'folder_full_path') and self.doc.folder_full_path else "Root"
            size_str = f"{self.doc.file_size / (1024*1024):.1f} MB" if self.doc.file_size and self.doc.file_size > 1024*1024 else f"{(self.doc.file_size or 0)/1024:.1f} KB"
            msg = f"📄 {self.doc.title} | {size_str} | 📂 {path_str} | Owner: {self.doc.owner_username or 'N/A'}"
            p.view.statusBar().showMessage(msg)
            
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        self._hover = False
        self._anim = QPropertyAnimation(self, b"scale_val")
        self._anim.setDuration(150); self._anim.setEndValue(1.0); self._anim.start()
        
        # UX: Clear status bar
        p = self.parent()
        while p and not hasattr(p, 'api'): p = p.parent()
        if hasattr(p, 'view') and hasattr(p.view, 'statusBar'):
            p.view.statusBar().clearMessage()
            
        super().leaveEvent(ev)

    def set_selected(self, sel): self._sel = sel; self.update()

    def paintEvent(self, ev):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._opacity)
        
        # 1. Coordinate System for Zoom
        if self._scale != 1.0:
            p.translate(self.width()/2, self.height()/2)
            p.scale(self._scale, self._scale)
            p.translate(-self.width()/2, -self.height()/2)

        # 2. Draw Selection/Hover Background
        rect = self.rect().adjusted(6, 6, -6, -6)
        if self._sel or self._hover:
            col = QColor(self._sel_col)
            if self._hover and not self._sel: col.setAlpha(100)
            p.setPen(QPen(col, 2))
            p.setBrush(QBrush(QColor(col.red(), col.green(), col.blue(), 25)))
            p.drawRoundedRect(rect, 10, 10)

        # 3. Draw Thumbnail Area
        thumb_r = QRect(10, 10, 160, 110)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(self._bg_muted)
        p.drawRoundedRect(thumb_r, 6, 6)
        
        if self._thumb_pm:
            # Center thumb in area
            tx = thumb_r.x() + (thumb_r.width() - self._thumb_pm.width()) // 2
            ty = thumb_r.y() + (thumb_r.height() - self._thumb_pm.height()) // 2
            p.drawPixmap(tx, ty, self._thumb_pm)

        # 4. Draw Title
        p.setPen(self._txt_col)
        font = p.font(); font.setBold(True); font.setPixelSize(11); p.setFont(font)
        title_rect = QRect(12, 125, 156, 40)
        p.drawText(title_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap, self.doc.title or "Untitled")

        # 5. Draw Tags (Simple labels)
        if self.doc.tags:
            tags = [t.strip() for t in self.doc.tags.split(',') if t.strip()]
            cur_x = 12
            font.setBold(False); font.setPixelSize(9); p.setFont(font)
            for tag in tags[:2]:
                txt = f"#{tag}"
                tw = QFontMetrics(font).horizontalAdvance(txt) + 8
                if cur_x + tw > 168: break
                tag_r = QRect(cur_x, 175, tw, 16)
                p.setBrush(QBrush(QColor(self._sel_col.red(), self._sel_col.green(), self._sel_col.blue(), 40)))
                p.drawRoundedRect(tag_r, 4, 4)
                p.setPen(self._txt_col if self.doc.is_private else self._sel_col)
                p.drawText(tag_r, Qt.AlignmentFlag.AlignCenter, txt)
                cur_x += tw + 4
        
        p.end()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton: self.clicked.emit(self.doc)
        super().mousePressEvent(ev)

    def mouseDoubleClickEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            p = self.parent()
            while p and not hasattr(p, 'file_double_clicked'): p = p.parent()
            if p: p.file_double_clicked.emit(self.doc)
        super().mouseDoubleClickEvent(ev)


class FileGrid(QFrame):
    file_selected = pyqtSignal(object); file_double_clicked = pyqtSignal(object)
    open_requested = pyqtSignal(int); download_requested = pyqtSignal(object)
    copy_requested = pyqtSignal(object); cut_requested = pyqtSignal(object)
    paste_requested = pyqtSignal(); delete_requested = pyqtSignal(object)
    edit_requested = pyqtSignal(object); rename_requested = pyqtSignal(object)

    def __init__(self, api: APIManager, parent=None):
        super().__init__(parent)
        self.api = api; self.translator = Translator()
        self._me_id = None; self._me_role = None; self._clip = None; self._sel = None
        self.setObjectName("card"); self._pool = QThreadPool(); self._pool.setMaxThreadCount(4)
        self._cache = {}; self._files = []; self._loading = set(); self._sort = None; self._tiles = {}; self._last_cols = -1
        
        # UX Improvements
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAcceptDrops(True)
        
        self._load_cache(); self._build()

    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls(): ev.acceptProposedAction()
    
    def dropEvent(self, ev):
        urls = ev.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.toLocalFile().lower().endswith(('.pdf', '.dxf'))]
        if paths:
            # Emit a signal or call a method to handle upload
            # We can use the parent's controller to trigger upload
            p = self.parent()
            while p and not hasattr(p, 'api'): p = p.parent()
            if hasattr(p, 'file_ops'):
                # Get current folder from navigation tree
                selected_items = p.ui.nav_tree.selectedItems()
                folder_id = None; is_public = False
                if selected_items:
                    data = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
                    from ..api_manager import APIFolder
                    if isinstance(data, APIFolder):
                        folder_id = data.id; is_public = data.is_public
                
                p.file_ops.start_upload_worker(paths, folder_id, is_public)
        ev.acceptProposedAction()

    def keyPressEvent(self, ev):
        if not self._files: return super().keyPressEvent(ev)
        
        idx = -1
        if self._sel:
            try: idx = self._files.index(self._sel.doc)
            except: pass
            
        cols = max(3, self._sa.width() // 200 if self._sa.width() > 0 else 4)
        
        if ev.key() == Qt.Key.Key_Right: idx += 1
        elif ev.key() == Qt.Key.Key_Left: idx -= 1
        elif ev.key() == Qt.Key.Key_Down: idx += cols
        elif ev.key() == Qt.Key.Key_Up: idx -= cols
        elif ev.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._sel: self.open_requested.emit(self._sel.doc.id)
            return
        else:
            return super().keyPressEvent(ev)
            
        if 0 <= idx < len(self._files):
            self._clk(self._files[idx])
            # Ensure visible
            tile = self._tiles.get(self._files[idx].id)
            if tile: self._sa.ensureWidgetVisible(tile)
        ev.accept()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(12,12,12,12); lay.setSpacing(10)
        t = QLabel(self.translator.tr("main.my_documents")); t.setObjectName("sectionTitle")
        lay.addWidget(t)
        sa = QScrollArea(); sa.setWidgetResizable(True); sa.setFrameShape(QFrame.Shape.NoFrame)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sa.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        gc = QWidget(); gc.setStyleSheet("background:transparent;")
        gl = QGridLayout(gc); gl.setContentsMargins(4,4,4,4); gl.setSpacing(12); gl.setAlignment(Qt.AlignmentFlag.AlignTop)
        sa.setWidget(gc); lay.addWidget(sa, 1)
        self._sa, self._gc, self._gl = sa, gc, gl
        self._timer = QTimer(self); self._timer.setSingleShot(True); self._timer.timeout.connect(self._load_vis)
        sa.verticalScrollBar().valueChanged.connect(lambda: self._timer.start(100))
        gc.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); gc.customContextMenuRequested.connect(self._ctx)

    def set_loading(self, loading: bool): pass # Implementation for status indicator if needed
    def set_context(self, u, r): self._me_id, self._me_role = u, r
    def set_clipboard_state(self, d): self._clip = d

    def rebuild_with_files(self, files, _icon=None, owner_id=None):
        self._pool.clear(); self._tiles = {}; self._sel = None; self._last_cols = -1
        while self._gl.count():
            c = self._gl.takeAt(0)
            if c.widget(): c.widget().deleteLater()
        self._files = list(files); self._loading.clear()
        if not files: self.file_selected.emit(None); return
        cols = max(3, self._sa.width() // 200 if self._sa.width() > 0 else 4)
        r, c = 0, 0
        for i, f in enumerate(self._files):
            t = DocumentTileWidget(f); self._tiles[f.id] = t
            t.setProperty("did", f.id); t.clicked.connect(self._clk); self._gl.addWidget(t, r, c)
            t.start_entrance_anim(min(600, i * 20))
            if f.id in self._cache:
                pm = self._cache[f.id].pixmap(QSize(160, 105))
                if not pm.isNull(): t.set_thumbnail(pm)
            c += 1
            if c >= cols: c, r = 0, r+1
        if self._sort: self._sort_int(self._sort); self._repos()
        QTimer.singleShot(80, self._load_vis)

    def _repos(self):
        cols = max(3, self._sa.width() // 200 if self._sa.width() > 0 else 4)
        if cols == self._last_cols: return
        self._last_cols = cols; tiles = {}
        while self._gl.count():
            c = self._gl.takeAt(0)
            if c.widget() and isinstance(c.widget(), DocumentTileWidget): tiles[c.widget().property("did")] = c.widget()
        r, c = 0, 0
        for d in self._files:
            if d.id in tiles: self._gl.addWidget(tiles[d.id], r, c)
            c += 1
            if c >= cols: c, r = 0, r+1

    def _clk(self, doc):
        if self._sel and self._sel.doc.id != doc.id: self._sel.set_selected(False)
        t = self._tiles.get(doc.id)
        if t: t.set_selected(True); self._sel = t
        self.file_selected.emit(doc)

    def _ctx(self, pt):
        w = self._gc.childAt(pt)
        while w and not isinstance(w, DocumentTileWidget): w = w.parent()
        doc = w.doc if isinstance(w, DocumentTileWidget) else None
        m = QMenu()
        
        # UX: Apply theme style to menu
        m.setWindowFlags(m.windowFlags() | Qt.WindowType.FramelessWindowHint)
        m.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        if doc:
            own, adm = (self._me_id is not None and doc.owner_id == self._me_id), (self._me_role == "admin")
            ce, cd, cdl = own or adm or doc.is_public_edit, own or adm, own or adm or not doc.is_read_only
            m.addAction(self.translator.tr("context_menu.open")).triggered.connect(lambda: self.open_requested.emit(doc.id))
            dl = m.addAction(self.translator.tr("context_menu.download")); dl.triggered.connect(lambda: self.download_requested.emit(doc)); dl.setEnabled(cdl)
            m.addSeparator(); m.addAction(self.translator.tr("context_menu.copy")).triggered.connect(lambda: self.copy_requested.emit(doc))
            if own or adm: m.addAction(self.translator.tr("context_menu.cut")).triggered.connect(lambda: self.cut_requested.emit(doc))
            if ce:
                m.addSeparator(); m.addAction(self.translator.tr("context_menu.rename")).triggered.connect(lambda: self.rename_requested.emit(doc))
                m.addAction(self.translator.tr("context_menu.edit_metadata")).triggered.connect(lambda: self.edit_requested.emit(doc))
            if cd:
                if not ce: m.addSeparator()
                m.addAction(self.translator.tr("context_menu.delete")).triggered.connect(lambda: self.delete_requested.emit(doc))
        else:
            # Context menu for empty grid space
            m.addAction(self.translator.tr("main.btn_upload")).triggered.connect(self._trigger_upload_dialog)
            m.addAction(self.translator.tr("admin.refresh")).triggered.connect(self._trigger_refresh)

        if self._clip:
            if doc: m.addSeparator()
            m.addAction(self.translator.tr("context_menu.paste")).triggered.connect(lambda: self.paste_requested.emit())
        m.exec(self._gc.mapToGlobal(pt))

    def _trigger_upload_dialog(self):
        p = self.parent()
        while p and not hasattr(p, 'file_ops'): p = p.parent()
        if p: p.file_ops.on_add_pdf_clicked()

    def _trigger_refresh(self):
        p = self.parent()
        while p and not hasattr(p, 'search_handler'): p = p.parent()
        if p: p.search_handler.fetch_from_server(force_fresh=True)

    def _load_vis(self):
        if not self._files: return
        sb = self._sa.verticalScrollBar(); vp = self._sa.viewport().height(); tot, pos = sb.maximum()+vp, sb.value()
        if tot <= 0: return
        s, e = max(0, int(max(0,pos/tot-0.05)*len(self._files))), min(len(self._files), int(min(1,(pos+vp)/tot+0.1)*len(self._files)))
        for i in range(s, e):
            d = self._files[i]
            if d.id not in self._cache and d.id not in self._loading:
                self._loading.add(d.id); w = ThumbnailRunnable(self.api, d.id, QSize(328, 210))
                w.signals.finished.connect(self._thumb); self._pool.start(w)

    def _thumb(self, did, img):
        self._loading.discard(did); doc = next((d for d in self._files if d.id == did), None)
        if not doc: return
        pm = QPixmap.fromImage(img); pm = self._dot(pm) if doc.is_public else pm
        self._cache[did] = QIcon(pm); t = self._tiles.get(did)
        if t: t.set_thumbnail(pm)

    def _dot(self, pm):
        c = QPixmap(pm); p = QPainter(c)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing); sz, mg = max(7,int(c.width()*0.09)), max(2,int(c.width()*0.03))
            p.setBrush(QBrush(QColor("#22c55e"))); p.setPen(QPen(QColor("#fff"), 1)); p.drawEllipse(int(c.width()-sz-mg), int(mg), int(sz), int(sz))
        finally: p.end()
        return c

    def find_and_select_document(self, did):
        if self._sel: self._sel.set_selected(False); self._sel = None
        t = self._tiles.get(did)
        if t: t.set_selected(True); self._sel = t

    def update_single_document(self, doc):
        t = self._tiles.get(doc.id)
        if not t: return False
        t.doc = doc; self._cache.pop(doc.id, None); self._loading.discard(doc.id)
        w = ThumbnailRunnable(self.api, doc.id, QSize(328, 210)); w.signals.finished.connect(self._thumb); self._loading.add(doc.id); self._pool.start(w)
        return True

    def sort_items(self, mode):
        if not self._files: return
        self._sort = mode; cid = self._sel.property("did") if self._sel else None; self._sort_int(mode); self._repos()
        if cid: self.find_and_select_document(cid)
        QTimer.singleShot(0, self._load_vis)

    def _sort_int(self, mode):
        def k(d):
            if mode=='name_asc': return (d.title or "").lower()
            if mode=='date_desc': return d.upload_date or ""
            return d.id
        self._files.sort(key=k, reverse=(mode=='date_desc'))

    def has_same_documents(self, docs): return len(self._files)==len(docs) and {d.id for d in self._files}=={d.id for d in docs}

    def _load_cache(self, force_clear=False):
        if force_clear: self._cache = {}; return
        cd = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation); cf = os.path.join(cd, "pdflib", "thumbnail_cache.json")
        if not os.path.exists(cf): return
        try:
            with open(cf, 'r', encoding='utf-8') as f: ca = json.load(f)
            for k, b in ca.items():
                try:
                    d = QByteArray.fromBase64(b.encode()); pm = QPixmap(); pm.loadFromData(d, "PNG")
                    if not pm.isNull(): self._cache[int(k)] = QIcon(pm)
                except: pass
        except: pass

    def _save_cache(self):
        try:
            cd = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation); os.makedirs(os.path.join(cd, "pdflib"), exist_ok=True)
            ca = {}
            for did, ic in self._cache.items():
                try:
                    pm = ic.pixmap(180, 220)
                    if not pm.isNull():
                        d = QByteArray(); buf = QBuffer(d); buf.open(QBuffer.OpenModeFlag.WriteOnly); pm.save(buf, "PNG", 80)
                        ca[str(did)] = bytes(d.toBase64()).decode('ascii')
                except: pass
            with open(os.path.join(cd, "pdflib", "thumbnail_cache.json"), 'w', encoding='utf-8') as f: json.dump(ca, f, indent=2)
        except: pass

    def clear_thumbnail_cache(self):
        try:
            self._cache = {}; self._loading.clear()
            cd = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation); cf = os.path.join(cd, "pdflib", "thumbnail_cache.json")
            if os.path.exists(cf): os.remove(cf)
            self._pool.clear(); self._pool.waitForDone(1000)
            if self._files: self._load_vis()
            return True
        except Exception as e: print(f"Error clearing thumbnail cache: {e}"); return False

    def _save_thumbnail_cache(self): self._save_cache()
    def closeEvent(self, ev): self._save_cache(); self._pool.clear(); self._pool.waitForDone(1000); super().closeEvent(ev) if hasattr(super(), 'closeEvent') else None
    def resizeEvent(self, ev): super().resizeEvent(ev); self._repos()
