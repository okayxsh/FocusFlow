"""
sidebar.py — Glassmorphism sidebar for FocusFlow.
"""
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QLineEdit, QScrollArea, QWidget, QMenu)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient, QFont
from PyQt5.QtCore import QRectF


class NavButton(QPushButton):
    """A single nav item button that highlights when active."""
    def __init__(self, icon, label, page_id, parent=None):
        super().__init__(parent)
        self.page_id = page_id
        self._active = False
        self.setText(f"  {icon}  {label}")
        self.setCheckable(False)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()

    def set_active(self, v: bool):
        self._active = v
        self._update_style()

    def _update_style(self):
        if self._active:
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(99,102,241,0.25);
                    color: #F8FAFC;
                    border: 1px solid rgba(99,102,241,0.6);
                    border-radius: 12px;
                    padding: 10px 14px;
                    text-align: left;
                    font-size: 14px;
                    font-weight: 600;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #94A3B8;
                    border: none;
                    border-radius: 12px;
                    padding: 10px 14px;
                    text-align: left;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.06);
                    color: #F8FAFC;
                }
            """)


class PageItem(QPushButton):
    """A page entry in the Notes section."""
    delete_requested = pyqtSignal(int)

    def __init__(self, title, page_id, depth=0, parent=None):
        super().__init__(parent)
        self.page_id = page_id
        indent = "    " * depth
        self.setText(f"{indent}📄  {title[:28]}{'…' if len(title)>28 else ''}")
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._ctx_menu)
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94A3B8;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                text-align: left;
                font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.06);
                color: #F8FAFC;
            }
        """)

    def _ctx_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #1a1f35; border: 1px solid rgba(255,255,255,0.12);
                    border-radius: 10px; color: white; padding: 6px; }
            QMenu::item { padding: 8px 20px; border-radius: 6px; }
            QMenu::item:selected { background: rgba(99,102,241,0.4); }
        """)
        menu.addAction("🗑  Delete Page", lambda: self.delete_requested.emit(self.page_id))
        menu.exec_(self.mapToGlobal(pos))


class Sidebar(QFrame):
    page_selected       = pyqtSignal(int)
    add_page_requested  = pyqtSignal(object)

    NAV_ITEMS = [
        ("🏠", "Dashboard",   -1),
        ("📝", "My Notes",    -5),
        ("✅", "Assignments",  -2),
        ("⏱️", "Focus Timer",  -3),
        ("⚙️", "Settings",    -4),
    ]

    def __init__(self, db_conn, parent=None):
        super().__init__(parent)
        self.db = db_conn
        self.is_collapsed = False
        self._nav_btns = {}
        self._active_id = None

        self.setFixedWidth(260)
        self.setStyleSheet("QFrame { background: transparent; border: none; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 20, 12, 20)
        root.setSpacing(4)

        # ── Logo / Collapse ────────────────────────────────────────────────
        top = QHBoxLayout()
        self.logo = QLabel("FocusFlow")
        self.logo.setStyleSheet(
            "font-size: 20px; font-weight: 800; color: #F8FAFC; "
            "letter-spacing: -0.5px; padding: 4px 6px;"
        )
        top.addWidget(self.logo)
        top.addStretch()

        self.collapse_btn = QPushButton("◀")
        self.collapse_btn.setFixedSize(32, 32)
        self.collapse_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px; color: #64748B; font-size: 12px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.12); color: white; }
        """)
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        top.addWidget(self.collapse_btn)
        root.addLayout(top)

        root.addSpacing(10)

        # ── Search ─────────────────────────────────────────────────────────
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search notes…")
        self.search.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 10px; padding: 9px 14px;
                color: white; font-size: 13px;
            }
            QLineEdit:focus { border-color: rgba(99,102,241,0.7); }
        """)
        self.search.textChanged.connect(self._filter_pages)
        root.addWidget(self.search)

        root.addSpacing(6)

        # ── Fixed nav ──────────────────────────────────────────────────────
        for icon, label, pid in self.NAV_ITEMS:
            btn = NavButton(icon, label, pid)
            btn.clicked.connect(lambda _, p=pid: self._nav_click(p))
            self._nav_btns[pid] = btn
            root.addWidget(btn)

        # ── Notes section ──────────────────────────────────────────────────
        root.addSpacing(10)
        notes_hdr = QHBoxLayout()
        sec_lbl = QLabel("NOTES")
        sec_lbl.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: #475569; "
            "letter-spacing: 1.5px; padding: 0 6px;"
        )
        notes_hdr.addWidget(sec_lbl)
        notes_hdr.addStretch()
        new_btn = QPushButton("＋")
        new_btn.setFixedSize(26, 26)
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setToolTip("New page")
        new_btn.setStyleSheet("""
            QPushButton {
                background: rgba(99,102,241,0.2);
                border: 1px solid rgba(99,102,241,0.4);
                border-radius: 8px; color: #A5B4FC; font-size: 16px; font-weight: 700;
            }
            QPushButton:hover { background: rgba(99,102,241,0.4); color: white; }
        """)
        new_btn.clicked.connect(lambda: self.add_page_requested.emit(None))
        notes_hdr.addWidget(new_btn)
        root.addLayout(notes_hdr)

        # Scrollable page list
        self.page_scroll = QScrollArea()
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.page_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        self.page_container = QWidget()
        self.page_container.setStyleSheet("background: transparent;")
        self.pages_layout = QVBoxLayout(self.page_container)
        self.pages_layout.setAlignment(Qt.AlignTop)
        self.pages_layout.setContentsMargins(0, 0, 0, 0)
        self.pages_layout.setSpacing(2)
        self.page_scroll.setWidget(self.page_container)
        root.addWidget(self.page_scroll, 1)

        self.refresh_pages()

    # ── Public ───────────────────────────────────────────────────────────────
    def refresh_pages(self):
        while self.pages_layout.count():
            w = self.pages_layout.takeAt(0).widget()
            if w: w.deleteLater()

        try:
            cur = self.db.cursor()
            cur.execute(
                "SELECT id, title FROM pages WHERE parent_id IS NULL "
                "AND is_archived = 0 ORDER BY updated_at DESC"
            )
            rows = cur.fetchall()
            if not rows:
                empty = QLabel("  No pages yet.\n  Click ＋ to create one.")
                empty.setStyleSheet("color: #334155; font-size: 13px; padding: 10px 6px;")
                self.pages_layout.addWidget(empty)
            for pid, title in rows:
                item = PageItem(title or "Untitled", pid)
                item.clicked.connect(lambda _, p=pid: self._nav_click(p))
                item.delete_requested.connect(self._delete_page)
                self.pages_layout.addWidget(item)
                self._add_children(pid, depth=1)
        except Exception as e:
            print(f"Sidebar load error: {e}")

    def set_active(self, page_id):
        self._active_id = page_id
        for pid, btn in self._nav_btns.items():
            btn.set_active(pid == page_id)

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.setFixedWidth(60)
            self.logo.hide()
            self.search.hide()
            self.page_scroll.hide()
            self.collapse_btn.setText("▶")
        else:
            self.setFixedWidth(260)
            self.logo.show()
            self.search.show()
            self.page_scroll.show()
            self.collapse_btn.setText("◀")

    # ── Internal ─────────────────────────────────────────────────────────────
    def _add_children(self, parent_id, depth):
        try:
            cur = self.db.cursor()
            cur.execute(
                "SELECT id, title FROM pages WHERE parent_id = ? "
                "AND is_archived = 0 ORDER BY updated_at DESC",
                (parent_id,)
            )
            for pid, title in cur.fetchall():
                item = PageItem(title or "Untitled", pid, depth)
                item.clicked.connect(lambda _, p=pid: self._nav_click(p))
                item.delete_requested.connect(self._delete_page)
                self.pages_layout.addWidget(item)
                self._add_children(pid, depth + 1)
        except Exception as e:
            print(f"Children load error: {e}")

    def _nav_click(self, page_id):
        self.set_active(page_id)
        self.page_selected.emit(page_id)

    def _delete_page(self, page_id):
        try:
            cur = self.db.cursor()
            cur.execute("UPDATE pages SET is_archived = 1 WHERE id = ?", (page_id,))
            self.db.commit()
            self.refresh_pages()
        except Exception as e:
            print(f"Delete page error: {e}")

    def _filter_pages(self, text):
        for i in range(self.pages_layout.count()):
            item = self.pages_layout.itemAt(i).widget()
            if item:
                hidden = text.lower() not in item.text().lower() and text != ""
                item.setVisible(not hidden)

    def paintEvent(self, event):
        """Draw the glass sidebar panel."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height())
        painter.setBrush(QBrush(QColor(10, 10, 26, 200)))
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        painter.drawRoundedRect(rect, 0, 0)
        painter.drawLine(int(self.width()) - 1, 0, int(self.width()) - 1, self.height())
        super().paintEvent(event)
