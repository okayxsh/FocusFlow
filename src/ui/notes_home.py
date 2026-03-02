"""
notes_home.py — Polished Notes hub with folder management, grid layout,
                inline edit/delete, and active folder highlighting.
"""
import os
import re
import random
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QScrollArea, QWidget, QPushButton, QLineEdit,
                             QInputDialog, QMenu, QDialog, QGridLayout,
                             QSizePolicy, QMessageBox, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QFont

FOLDER_COLORS = [
    "#6366F1", "#10B981", "#F59E0B", "#EF4444",
    "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16",
]

FOLDER_ICONS = ["📁", "📚", "🔬", "💻", "🎨", "📐", "🧪", "🌍", "🎵", "🏛"]


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return f"{r},{g},{b}"


def _btn(text, color="#6366F1", small=False):
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    h = "34px" if small else "40px"
    rgb = _hex_to_rgb(color)
    b.setStyleSheet(f"""
        QPushButton {{
            background: rgba({rgb}, 0.18);
            border: 1px solid rgba({rgb}, 0.40);
            border-radius: 10px; color: white;
            font-size: 13px; font-weight: 600;
            padding: 0 16px; min-height: {h};
        }}
        QPushButton:hover {{
            background: rgba({rgb}, 0.38);
            border-color: rgba({rgb}, 0.7);
        }}
    """)
    return b


# ── Folder Card ──────────────────────────────────────────────────────────────
class FolderCard(QFrame):
    clicked_signal   = pyqtSignal(int)
    edit_requested   = pyqtSignal(int)
    delete_requested = pyqtSignal(int)

    def __init__(self, folder_id, name, color, icon, note_count=0, active=False):
        super().__init__()
        self.folder_id = folder_id
        self._color    = color
        self._active   = active
        self.setFixedSize(158, 102)
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._ctx)
        self._apply_style()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)

        top = QHBoxLayout()
        ico = QLabel(icon)
        ico.setStyleSheet("font-size: 20px; background: transparent;")
        top.addWidget(ico)
        top.addStretch()
        cnt = QLabel(str(note_count))
        cnt.setStyleSheet(
            f"color: {color}; font-size: 20px; font-weight: 800; background: transparent;"
        )
        top.addWidget(cnt)
        lay.addLayout(top)

        lbl = QLabel(name[:20])
        lbl.setStyleSheet(
            "color: #F8FAFC; font-size: 13px; font-weight: 700; background: transparent;"
        )
        sub = QLabel(f"{note_count} note{'s' if note_count != 1 else ''}")
        sub.setStyleSheet("color: #475569; font-size: 11px; background: transparent;")
        lay.addWidget(lbl)
        lay.addWidget(sub)

    def _apply_style(self):
        rgb = _hex_to_rgb(self._color)
        if self._active:
            self.setStyleSheet(f"""
                QFrame {{
                    background: rgba({rgb}, 0.28);
                    border: 2px solid rgba({rgb}, 0.75);
                    border-radius: 16px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background: rgba({rgb}, 0.10);
                    border: 1px solid rgba({rgb}, 0.28);
                    border-radius: 16px;
                }}
                QFrame:hover {{
                    background: rgba({rgb}, 0.20);
                    border-color: rgba({rgb}, 0.55);
                }}
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked_signal.emit(self.folder_id)
        super().mousePressEvent(event)

    def _ctx(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(_menu_style())
        menu.addAction("✏️  Rename", lambda: self.edit_requested.emit(self.folder_id))
        menu.addAction("🗑  Delete",  lambda: self.delete_requested.emit(self.folder_id))
        menu.exec_(self.mapToGlobal(pos))


# ── Note Card ────────────────────────────────────────────────────────────────
class NoteCard(QFrame):
    open_requested   = pyqtSignal(int)
    rename_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)
    move_requested   = pyqtSignal(int)

    def __init__(self, page_id, title, excerpt, date_str,
                 folder_name=None, folder_color="#6366F1"):
        super().__init__()
        self.page_id = page_id
        self.setFixedSize(224, 148)
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._ctx)
        self.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 16px;
            }
            QFrame:hover {
                background: rgba(99,102,241,0.10);
                border-color: rgba(99,102,241,0.38);
            }
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(5)

        # Icon + title
        title_row = QHBoxLayout()
        ic = QLabel("📄")
        ic.setStyleSheet("font-size: 15px; background: transparent;")
        title_row.addWidget(ic)
        t = QLabel((title or "Untitled")[:24])
        t.setStyleSheet(
            "color: #F8FAFC; font-size: 13px; font-weight: 700; background: transparent;"
        )
        title_row.addWidget(t, 1)

        # Inline action buttons (visible on hover via stylesheet trick — always present but subtle)
        self._edit_btn = QPushButton("✏")
        self._del_btn  = QPushButton("🗑")
        for b, tip in [(self._edit_btn, "Rename"), (self._del_btn, "Delete")]:
            b.setToolTip(tip)
            b.setFixedSize(24, 24)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton {
                    background: transparent; border: none;
                    color: #334155; font-size: 13px; border-radius: 6px;
                }
                QPushButton:hover { background: rgba(255,255,255,0.1); color: #F8FAFC; }
            """)
        self._edit_btn.clicked.connect(lambda: self.rename_requested.emit(self.page_id))
        self._del_btn.clicked.connect(lambda: self.delete_requested.emit(self.page_id))
        title_row.addWidget(self._edit_btn)
        title_row.addWidget(self._del_btn)
        lay.addLayout(title_row)

        # Excerpt
        plain = (excerpt or "")[:70] + ("…" if len(excerpt or "") > 70 else "")
        ex = QLabel(plain)
        ex.setWordWrap(True)
        ex.setStyleSheet("color: #475569; font-size: 12px; background: transparent;")
        lay.addWidget(ex)
        lay.addStretch()

        # Footer
        foot = QHBoxLayout()
        foot.setSpacing(6)
        date_lbl = QLabel(date_str)
        date_lbl.setStyleSheet("color: #1E293B; font-size: 10px; background: transparent;")
        foot.addWidget(date_lbl)
        foot.addStretch()

        if folder_name:
            rgb = _hex_to_rgb(folder_color)
            fldr = QLabel(f"📁 {folder_name[:12]}")
            fldr.setStyleSheet(
                f"color: {folder_color}; font-size: 10px; font-weight: 600;"
                f"background: rgba({rgb},0.14); border-radius: 5px; padding: 2px 6px;"
            )
            foot.addWidget(fldr)
        lay.addLayout(foot)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.open_requested.emit(self.page_id)

    def _ctx(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(_menu_style())
        menu.addAction("✏️  Rename",          lambda: self.rename_requested.emit(self.page_id))
        menu.addAction("📁  Move to Folder",  lambda: self.move_requested.emit(self.page_id))
        menu.addSeparator()
        menu.addAction("🗑  Delete",           lambda: self.delete_requested.emit(self.page_id))
        menu.exec_(self.mapToGlobal(pos))


# ── Shared menu style ────────────────────────────────────────────────────────
def _menu_style():
    return """
        QMenu {
            background: rgba(12,14,32,0.98);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 12px; color: white; padding: 6px;
        }
        QMenu::item { padding: 9px 20px; border-radius: 8px; font-size: 13px; }
        QMenu::item:selected { background: rgba(99,102,241,0.35); }
        QMenu::separator { height: 1px; background: rgba(255,255,255,0.07); margin: 4px 0; }
    """


# ── Section label ────────────────────────────────────────────────────────────
def _section_lbl(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "font-size: 10px; font-weight: 800; letter-spacing: 2px; "
        "color: #334155; background: transparent;"
    )
    return lbl


# ── NotesHome ────────────────────────────────────────────────────────────────
class NotesHome(QFrame):
    page_opened = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent        = parent
        self._active_folder = None
        self.setStyleSheet("QFrame { background: transparent; }")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { background: transparent; width: 6px; border-radius: 3px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.12); border-radius: 3px; }"
        )

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.root = QVBoxLayout(container)
        self.root.setContentsMargins(52, 44, 52, 52)
        self.root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("📝  My Notes")
        title.setStyleSheet(
            "font-size: 28px; font-weight: 800; color: #F8FAFC; background: transparent;"
        )
        hdr.addWidget(title)
        hdr.addStretch()

        self.new_folder_btn = _btn("📁  New Folder", "#8B5CF6", small=True)
        self.new_folder_btn.clicked.connect(self._create_folder)
        hdr.addWidget(self.new_folder_btn)

        self.new_note_btn = _btn("✏️  New Note", "#6366F1", small=True)
        self.new_note_btn.clicked.connect(self._new_note)
        hdr.addWidget(self.new_note_btn)

        self.root.addLayout(hdr)
        self.root.addSpacing(20)

        # ── Search ────────────────────────────────────────────────────────
        search_wrap = QFrame()
        search_wrap.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.09);
                border-radius: 14px;
            }
            QFrame:focus-within {
                border-color: rgba(99,102,241,0.6);
            }
        """)
        sw_lay = QHBoxLayout(search_wrap)
        sw_lay.setContentsMargins(16, 0, 16, 0)

        loup = QLabel("🔍")
        loup.setStyleSheet("background: transparent; font-size: 14px;")
        sw_lay.addWidget(loup)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search notes and folders…")
        self.search.setStyleSheet("""
            QLineEdit {
                background: transparent; border: none;
                color: white; font-size: 14px; padding: 12px 4px;
            }
        """)
        self.search.textChanged.connect(self.refresh)
        sw_lay.addWidget(self.search)

        self.root.addWidget(search_wrap)
        self.root.addSpacing(32)

        # ── Folders section ───────────────────────────────────────────────
        f_hdr = QHBoxLayout()
        f_hdr.addWidget(_section_lbl("FOLDERS"))
        f_hdr.addStretch()
        all_btn = _btn("Show All", "#475569", small=True)
        all_btn.clicked.connect(lambda: self._filter_folder(None))
        f_hdr.addWidget(all_btn)
        self.root.addLayout(f_hdr)
        self.root.addSpacing(14)

        # Folders flow — wrapping grid
        self.folders_widget = QWidget()
        self.folders_widget.setStyleSheet("background: transparent;")
        self.folders_layout = QHBoxLayout(self.folders_widget)
        self.folders_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.folders_layout.setSpacing(14)
        self.root.addWidget(self.folders_widget)
        self.root.addSpacing(36)

        # ── Notes section ─────────────────────────────────────────────────
        n_hdr = QHBoxLayout()
        self.notes_title_lbl = QLabel("ALL NOTES")
        self.notes_title_lbl.setStyleSheet(
            "font-size: 10px; font-weight: 800; letter-spacing: 2px; "
            "color: #334155; background: transparent;"
        )
        n_hdr.addWidget(self.notes_title_lbl)
        n_hdr.addStretch()
        self.note_count_lbl = QLabel("")
        self.note_count_lbl.setStyleSheet(
            "color: #1E293B; font-size: 12px; background: transparent;"
        )
        n_hdr.addWidget(self.note_count_lbl)
        self.root.addLayout(n_hdr)
        self.root.addSpacing(14)

        # Notes grid container
        self.notes_widget = QWidget()
        self.notes_widget.setStyleSheet("background: transparent;")
        self.notes_grid = QGridLayout(self.notes_widget)
        self.notes_grid.setSpacing(14)
        self.notes_grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.root.addWidget(self.notes_widget)
        self.root.addStretch()

    # ── Public ───────────────────────────────────────────────────────────────
    def refresh(self, _=None):
        if not self._parent or not hasattr(self._parent, 'db'):
            return
        db = self._parent.db
        _clear_layout(self.folders_layout)
        _clear_grid(self.notes_grid)
        self._build_folders(db)
        self._build_notes(db)

    # ── Builders ─────────────────────────────────────────────────────────────
    def _build_folders(self, db):
        try:
            cur = db.cursor()
            cur.execute("SELECT id, name, color, icon FROM folders ORDER BY name")
            rows = cur.fetchall()

            if not rows:
                lbl = QLabel("No folders yet — click 📁 New Folder to create one.")
                lbl.setStyleSheet("color: #334155; font-size: 13px; background: transparent;")
                self.folders_layout.addWidget(lbl)
                return

            for fid, name, color, icon in rows:
                cur.execute(
                    "SELECT COUNT(*) FROM pages WHERE folder_id=? AND is_archived=0", (fid,)
                )
                cnt    = cur.fetchone()[0]
                active = (self._active_folder == fid)
                card   = FolderCard(fid, name, color or "#6366F1", icon or "📁", cnt, active)
                card.clicked_signal.connect(self._filter_folder)
                card.edit_requested.connect(self._rename_folder)
                card.delete_requested.connect(self._delete_folder)
                self.folders_layout.addWidget(card)

        except Exception as e:
            print(f"Folders build error: {e}")

    def _build_notes(self, db):
        q = self.search.text().lower().strip()
        try:
            cur = db.cursor()
            if self._active_folder is not None:
                cur.execute(
                    "SELECT p.id, p.title, p.content, p.updated_at, f.name, f.color "
                    "FROM pages p LEFT JOIN folders f ON p.folder_id=f.id "
                    "WHERE p.folder_id=? AND p.is_archived=0 ORDER BY p.updated_at DESC",
                    (self._active_folder,)
                )
            else:
                cur.execute(
                    "SELECT p.id, p.title, p.content, p.updated_at, f.name, f.color "
                    "FROM pages p LEFT JOIN folders f ON p.folder_id=f.id "
                    "WHERE p.is_archived=0 ORDER BY p.updated_at DESC"
                )
            rows = cur.fetchall()

            if q:
                rows = [r for r in rows
                        if q in (r[1] or "").lower() or q in (r[2] or "").lower()]

            self.note_count_lbl.setText(f"{len(rows)} note{'s' if len(rows) != 1 else ''}")

            if not rows:
                msg = ("No notes in this folder yet." if self._active_folder
                       else "No notes yet — click ✏️ New Note to get started.")
                lbl = QLabel(msg)
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet(
                    "color: #334155; font-size: 14px; padding: 48px;"
                    "background: rgba(255,255,255,0.02);"
                    "border: 1px dashed rgba(255,255,255,0.07); border-radius: 16px;"
                )
                self.notes_grid.addWidget(lbl, 0, 0, 1, 4)
                return

            col_count = 4
            for i, (pid, title, content, ts, fname, fcolor) in enumerate(rows):
                plain = re.sub(r'<[^>]+>', ' ', content or '')
                plain = re.sub(r'\s+', ' ', plain).strip()
                card  = NoteCard(
                    pid, title, plain, (ts or "")[:10],
                    fname, fcolor or "#6366F1"
                )
                card.open_requested.connect(self._open_note)
                card.rename_requested.connect(self._rename_note)
                card.delete_requested.connect(self._delete_note)
                card.move_requested.connect(self._move_note)
                self.notes_grid.addWidget(card, i // col_count, i % col_count)

        except Exception as e:
            print(f"Notes build error: {e}")

    # ── Actions ───────────────────────────────────────────────────────────────
    def _new_note(self):
        if self._parent:
            self._parent._add_page(None)

    def _open_note(self, page_id):
        if self._parent:
            self._parent._navigate(page_id)

    def _filter_folder(self, folder_id):
        self._active_folder = folder_id
        self.notes_title_lbl.setText(
            "ALL NOTES" if folder_id is None else "NOTES IN FOLDER"
        )
        self.refresh()

    def _create_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name.strip():
            try:
                cur = self._parent.db.cursor()
                color = random.choice(FOLDER_COLORS)
                icon  = random.choice(FOLDER_ICONS)
                cur.execute(
                    "INSERT INTO folders (name, color, icon) VALUES (?,?,?)",
                    (name.strip(), color, icon)
                )
                self._parent.db.commit()
                self.refresh()
                self._parent.sidebar.refresh_pages()
            except Exception as e:
                print(f"Create folder error: {e}")

    def _rename_folder(self, folder_id):
        try:
            cur = self._parent.db.cursor()
            cur.execute("SELECT name FROM folders WHERE id=?", (folder_id,))
            row  = cur.fetchone()
            old  = row[0] if row else ""
            name, ok = QInputDialog.getText(self, "Rename Folder", "New name:", text=old)
            if ok and name.strip():
                cur.execute("UPDATE folders SET name=? WHERE id=?", (name.strip(), folder_id))
                self._parent.db.commit()
                self.refresh()
                self._parent.sidebar.refresh_pages()
        except Exception as e:
            print(f"Rename folder error: {e}")

    def _delete_folder(self, folder_id):
        reply = QMessageBox.question(
            self, "Delete Folder",
            "Delete this folder? Notes inside will become unfoldered.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                cur = self._parent.db.cursor()
                cur.execute("UPDATE pages SET folder_id=NULL WHERE folder_id=?", (folder_id,))
                cur.execute("DELETE FROM folders WHERE id=?", (folder_id,))
                self._parent.db.commit()
                self._active_folder = None
                self.refresh()
                self._parent.sidebar.refresh_pages()
            except Exception as e:
                print(f"Delete folder error: {e}")

    def _rename_note(self, page_id):
        try:
            cur = self._parent.db.cursor()
            cur.execute("SELECT title FROM pages WHERE id=?", (page_id,))
            row  = cur.fetchone()
            old  = row[0] if row else ""
            name, ok = QInputDialog.getText(self, "Rename Note", "New title:", text=old)
            if ok and name.strip():
                cur.execute(
                    "UPDATE pages SET title=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (name.strip(), page_id)
                )
                self._parent.db.commit()
                self.refresh()
                self._parent.sidebar.refresh_pages()
        except Exception as e:
            print(f"Rename note error: {e}")

    def _delete_note(self, page_id):
        reply = QMessageBox.question(
            self, "Delete Note",
            "Move this note to the archive?\nYou can restore it later.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                cur = self._parent.db.cursor()
                cur.execute("UPDATE pages SET is_archived=1 WHERE id=?", (page_id,))
                self._parent.db.commit()
                self.refresh()
                self._parent.sidebar.refresh_pages()
            except Exception as e:
                print(f"Delete note error: {e}")

    def _move_note(self, page_id):
        try:
            cur = self._parent.db.cursor()
            cur.execute("SELECT id, name FROM folders ORDER BY name")
            folders = cur.fetchall()
            if not folders:
                QMessageBox.information(self, "No Folders", "Create a folder first.")
                return
            names  = ["(No folder)"] + [f[1] for f in folders]
            choice, ok = QInputDialog.getItem(
                self, "Move to Folder", "Select folder:", names, 0, False
            )
            if ok:
                if choice == "(No folder)":
                    cur.execute("UPDATE pages SET folder_id=NULL WHERE id=?", (page_id,))
                else:
                    fid = next(f[0] for f in folders if f[1] == choice)
                    cur.execute("UPDATE pages SET folder_id=? WHERE id=?", (fid, page_id))
                self._parent.db.commit()
                self.refresh()
        except Exception as e:
            print(f"Move note error: {e}")


# ── Layout helpers ────────────────────────────────────────────────────────────
def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        w    = item.widget()
        if w:
            w.deleteLater()


def _clear_grid(grid):
    while grid.count():
        item = grid.takeAt(0)
        w    = item.widget()
        if w:
            w.deleteLater()