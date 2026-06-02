"""
Document grid. Senior-level optimization: hardware-accelerated animations & zero-clipping UI.
"""
from typing import Optional, List
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QThreadPool, QStandardPaths, QByteArray, QBuffer, QTimer, QRect, QPoint, QPointF, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QIcon, QPainter, QColor, QBrush, QPixmap, QPen, QLinearGradient
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QMenu, QWidget,
    QScrollArea, QGridLayout, QSizePolicy, QLayout, QGraphicsOpacityEffect
)
import json, os, sys, subprocess

from ..api_manager import APIManager, APIDocument
from .thumbnail_runnable import ThumbnailRunnable
from ..utils.translator import Translator
from ..themes import ThemeManager
import qtawesome as qta

class FlowLayout(QLayout):
    def __init__(self, parent=None, sp=3):
        super().__init__(parent); self._sp = sp; self._it = []
    def addItem(self, i): self._it.append(i)
    def count(self): return len(self._it)
    def itemAt(self, i): return self._it[i] if 0 <= i < len(self._it) else None
    def takeAt(self, i): return self._it.pop(i) if 0 <= i < len(self._it) else None
    def expandingDirections(self): return Qt.Orientation(0)
    def hasHeightForWidth(self): return True
    def heightForWidth(self, w): return self._do(QRect(0,0,w,0), True)
    def setGeometry(self, r): super().setGeometry(r); self._do(r, False)
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        s = QSize(); m = self.contentsMargins()
        for i in self._it: s = s.expandedTo(i.minimumSize())
        return s + QSize(m.left()+m.right(), m.top()+m.bottom())
    def _do(self, r, t):
        x,y,lh = r.x(),r.y(),0
        for i in self._it:
            w = i.sizeHint().width()
            if x+w > r.right() and lh>0: x,y,lh = r.x(),y+lh+self.spacing(),0
            if not t: i.setGeometry(QRect(QPoint(x,y), i.sizeHint()))
            x += w+self._sp; lh = max(lh, i.sizeHint().height())
        return y+lh-r.y()


class DocumentTileWidget(QWidget):
    clicked = pyqtSignal(object)

    def __init__(self, doc: APIDocument, parent=None):
        super().__init__(parent)
        self.doc = doc; self._sel = False; self._hover = False
        self._scale = 1.0
        self.setFixedSize(185, 235)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        
        # Opacity effect specifically for entrance, will be disabled after animation to save GPU
        self._eff = QGraphicsOpacityEffect(self)
        self._eff.setOpacity(0.0)
        self.setGraphicsEffect(self._eff)

        # Tooltip
        size_str = f"{doc.file_size / (1024*1024):.1f} MB" if doc.file_size and doc.file_size > 1024*1024 else f"{(doc.file_size or 0)/1024:.1f} KB"

        tm = ThemeManager()
        secondary_col = tm.get_color("text_secondary")
        path_str = doc.folder_full_path if hasattr(doc, 'folder_full_path') and doc.folder_full_path else None
        loc_str = f"Location: 📂 {path_str}" if path_str else "Location: 🏠 Root"

        info = [
            f"<p style='white-space:pre'><b>{doc.title}</b></p>",
            f"Size: {size_str}",
            f"Owner: {doc.owner_username or 'N/A'}",
            f"<span style='color:{secondary_col}'>{loc_str}</span>"
        ]
        if doc.notes: info.append(f"<hr><i>{doc.notes[:60]}...</i>")
        self.setToolTip("<br>".join(info))

        tm = ThemeManager(); dark = tm.current_theme == "Dark"
        txt = tm.get_color("text"); muted = tm.get_color("hover") if dark else "#E8E8E8"

        lay = QVBoxLayout(self); lay.setContentsMargins(12, 12, 12, 12); lay.setSpacing(5)
        
        self.thumb_container = QFrame()
        self.thumb_container.setFixedSize(162, 110)
        self.thumb_container.setStyleSheet(f"background-color:{muted}; border-radius:6px;")
        t_lay = QVBoxLayout(self.thumb_container); t_lay.setContentsMargins(0,0,0,0)
        
        self.thumb = QLabel()
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_lay.addWidget(self.thumb)
        lay.addWidget(self.thumb_container, 0, Qt.AlignmentFlag.AlignHCenter)

        self.title_lbl = QLabel(doc.title or "Untitled")
        self.title_lbl.setWordWrap(True); self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        f = self.title_lbl.font(); f.setBold(True); f.setPixelSize(11); self.title_lbl.setFont(f)
        self.title_lbl.setStyleSheet(f"color:{txt};")
        lay.addWidget(self.title_lbl)

        self.tags_box = QWidget(); self.tags_fl = FlowLayout(self.tags_box, sp=3)
        lay.addWidget(self.tags_box)
        self._tag_bg = tm.get_color("primary") if dark else "rgba(0,122,255,0.12)"
        self._tag_fg = tm.get_color("white") if dark else "rgba(0,0,0,0.75)"
        self._tags()
        self._sel_col = "#3b82f6" if dark else "#007AFF"
        
        # Pre-render folder shortcut icon
        self._folder_icon_px = None
        if doc.folder_id:
            icon_color = tm.get_color("primary")
            self._folder_icon_px = qta.icon('fa5s.folder', color=icon_color).pixmap(16, 16)
        elif hasattr(doc, 'folder_full_path') and doc.folder_full_path:
            # Backup check if folder_id is not enough
            icon_color = tm.get_color("primary")
            self._folder_icon_px = qta.icon('fa5s.folder', color=icon_color).pixmap(16, 16)

    @pyqtProperty(float)
    def scale_val(self): return self._scale
    @scale_val.setter
    def scale_val(self, v): self._scale = v; self.update()

    def _tags(self):
        while self.tags_fl.count(): self.tags_fl.takeAt(0)
        if not self.doc.tags: self.tags_box.hide(); return
        self.tags_box.show()
        tags = [t.strip() for t in self.doc.tags.split(',') if t.strip()]
        for tag in tags[:2]:
            lb = QLabel(f"#{tag}")
            lb.setStyleSheet(f"background-color:{self._tag_bg}; color:{self._tag_fg}; border-radius:4px; padding:1px 4px; font-size:9px;")
            self.tags_fl.addWidget(lb)

    def start_entrance_anim(self, delay=0):
        self._anim = QPropertyAnimation(self._eff, b"opacity")
        self._anim.setDuration(500); self._anim.setStartValue(0.0); self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        # Cleanup effect after animation to prevent scroll lag
        self._anim.finished.connect(lambda: self.setGraphicsEffect(None))
        QTimer.singleShot(delay, self._anim.start)

    def set_thumbnail(self, pm):
        if not pm.isNull(): self.thumb.setPixmap(pm.scaled(160, 105, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def enterEvent(self, ev):
        self._hover = True
        self._h_anim = QPropertyAnimation(self, b"scale_val")
        self._h_anim.setDuration(150); self._h_anim.setEndValue(1.05); self._h_anim.start()
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        self._hover = False
        self._h_anim = QPropertyAnimation(self, b"scale_val")
        self._h_anim.setDuration(150); self._h_anim.setEndValue(1.0); self._h_anim.start()
        super().leaveEvent(ev)

    def set_selected(self, sel): self._sel = sel; self.update()

    def paintEvent(self, ev):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Scale the whole canvas slightly on hover
        if self._scale != 1.0:
            p.translate(self.width()/2, self.height()/2)
            p.scale(self._scale, self._scale)
            p.translate(-self.width()/2, -self.height()/2)

        # Draw Folder Shortcut Indicator if document is in a subfolder
        if self._folder_icon_px:
            # Position: bottom right of the thumbnail area
            p.drawPixmap(self.width() - 32, 95, self._folder_icon_px)

        if self._sel or self._hover:
            r = self.rect().adjusted(6, 6, -6, -6).toRectF()
            col = QColor(self._sel_col)
            if self._hover and not self._sel: col.setAlpha(100)
            p.setPen(QPen(col, 2))
            p.setBrush(QBrush(QColor(col.red(), col.green(), col.blue(), 25)))
            p.drawRoundedRect(r, 10, 10)
        p.end()
        super().paintEvent(ev)

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
        self._load_cache(); self._build()

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
            t.start_entrance_anim(min(800, i * 25))
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
        if self._clip:
            if doc: m.addSeparator()
            m.addAction(self.translator.tr("context_menu.paste")).triggered.connect(lambda: self.paste_requested.emit())
        m.exec(self._gc.mapToGlobal(pt))

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
            p.setBrush(QBrush(QColor("#22c55e"))); p.setPen(QPen(QColor("#fff"), 1)); p.drawEllipse(c.width()-sz-mg, mg, sz, sz)
        finally: p.end()
        return c

    def find_and_select_document(self, did):
        if self._sel: self._sel.set_selected(False); self._sel = None
        t = self._tiles.get(did)
        if t: t.set_selected(True); self._sel = t

    def update_single_document(self, doc):
        t = self._tiles.get(doc.id)
        if not t: return False
        t.doc = doc; t.title_lbl.setText(doc.title or "Untitled"); t._tags(); self._cache.pop(doc.id, None); self._loading.discard(doc.id)
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
                    pm = ic.pixmap(185, 235)
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
    def set_loading(self, l): pass
    def set_context(self, u, r): self._me_id, self._me_role = u, r
    def set_clipboard_state(self, d): self._clip = d
    def closeEvent(self, ev): self._save_cache(); self._pool.clear(); self._pool.waitForDone(1000); super().closeEvent(ev) if hasattr(super(), 'closeEvent') else None
    def resizeEvent(self, ev): super().resizeEvent(ev); self._repos()
