"""
dashboard.py — Glassmorphism Dashboard for FocusFlow.
"""
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QScrollArea, QWidget, QPushButton, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient, QFont
from PyQt5.QtCore import QRectF
from datetime import date


def _glass_card(radius=16, alpha=18, border_alpha=35):
    """Return a QFrame styled as a glass card."""
    f = QFrame()
    f.setStyleSheet(f"""
        QFrame {{
            background: rgba(255,255,255,{alpha});
            border: 1px solid rgba(255,255,255,{border_alpha});
            border-radius: {radius}px;
        }}
    """)
    return f


class Dashboard(QFrame):
    navigate_to = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent
        self.setStyleSheet("QFrame { background: transparent; }")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.root = QVBoxLayout(container)
        self.root.setContentsMargins(50, 48, 50, 48)
        self.root.setSpacing(0)

        # ── Greeting ──────────────────────────────────────────────────────
        day_name  = date.today().strftime("%A")
        month_day = date.today().strftime("%B") + " " + str(date.today().day)

        greet = QLabel(f"Good day 👋  {day_name}, {month_day}")
        greet.setStyleSheet(
            "font-size: 30px; font-weight: 800; color: #F8FAFC; background: transparent;"
        )
        self.root.addWidget(greet)

        sub = QLabel("Here's what's happening today.")
        sub.setStyleSheet("font-size: 14px; color: #64748B; background: transparent; margin-bottom: 32px;")
        self.root.addWidget(sub)

        # ── Quick Actions ─────────────────────────────────────────────────
        self.root.addWidget(self._section_heading("QUICK ACTIONS"))
        qa_row = QHBoxLayout()
        qa_row.setSpacing(14)
        actions = [
            ("✏️  New Note",        -1,  "#6366F1"),
            ("✅  Assignments",      -2,  "#10B981"),
            ("⏱️  Start Focus",      -3,  "#F59E0B"),
            ("⚙️  Settings",         -4,  "#8B5CF6"),
        ]
        for label, pid, color in actions:
            btn = self._action_btn(label, color)
            btn.clicked.connect(lambda _, p=pid: self._navigate(p))
            qa_row.addWidget(btn)
        self.root.addLayout(qa_row)
        self.root.addSpacing(30)

        # ── Stats row ─────────────────────────────────────────────────────
        self.root.addWidget(self._section_heading("TODAY AT A GLANCE"))
        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(16)
        self.root.addLayout(self.stats_row)
        self.root.addSpacing(30)

        # ── Recent pages ──────────────────────────────────────────────────
        self.root.addWidget(self._section_heading("RECENT PAGES"))
        self.recent_grid = QHBoxLayout()
        self.recent_grid.setSpacing(14)
        self.root.addLayout(self.recent_grid)
        self.root.addSpacing(30)

        # ── Tasks ─────────────────────────────────────────────────────────
        self.root.addWidget(self._section_heading("DUE TODAY & UPCOMING"))
        self.tasks_col = QVBoxLayout()
        self.tasks_col.setSpacing(8)
        self.root.addLayout(self.tasks_col)

        self.root.addStretch()

    # ── Public ───────────────────────────────────────────────────────────────
    def refresh(self):
        if not self._parent or not hasattr(self._parent, 'db'):
            return
        db = self._parent.db
        self._clear(self.stats_row)
        self._clear(self.recent_grid)
        self._clear(self.tasks_col)
        self._build_stats(db)
        self._build_recent(db)
        self._build_tasks(db)

    # ── Builders ─────────────────────────────────────────────────────────────
    def _build_stats(self, db):
        try:
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) FROM pages WHERE is_archived = 0")
            pages = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM tasks WHERE status != 'done'")
            tasks = cur.fetchone()[0]
            cur.execute(
                "SELECT COALESCE(SUM(duration_minutes),0) FROM pomodoro_history "
                "WHERE date(completed_at)=date('now')"
            )
            mins = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM tasks WHERE status='done'")
            done = cur.fetchone()[0]

            for val, lbl, color in [
                (str(pages), "Total Pages",   "#6366F1"),
                (str(tasks), "Open Tasks",    "#F59E0B"),
                (f"{mins}m", "Focus Today",   "#10B981"),
                (str(done),  "Tasks Done",    "#EC4899"),
            ]:
                self.stats_row.addWidget(self._stat_card(val, lbl, color))
            self.stats_row.addStretch()
        except Exception as e:
            print(f"Stats error: {e}")

    def _build_recent(self, db):
        try:
            cur = db.cursor()
            cur.execute(
                "SELECT id, title, updated_at FROM pages WHERE is_archived=0 "
                "ORDER BY updated_at DESC LIMIT 4"
            )
            rows = cur.fetchall()
            if not rows:
                self.recent_grid.addWidget(self._empty("No pages yet.\nClick 'New Note' to get started."))
            else:
                for pid, title, ts in rows:
                    self.recent_grid.addWidget(self._page_card(pid, title, ts[:10]))
            self.recent_grid.addStretch()
        except Exception as e:
            print(f"Recent error: {e}")

    def _build_tasks(self, db):
        try:
            cur = db.cursor()
            cur.execute(
                "SELECT title, due_date, status FROM tasks "
                "WHERE status!='done' ORDER BY due_date ASC LIMIT 6"
            )
            rows = cur.fetchall()
            if not rows:
                self.tasks_col.addWidget(
                    self._empty("No upcoming tasks 🎉\nAdd tasks in the Assignments board.")
                )
            else:
                for title, due, status in rows:
                    self.tasks_col.addWidget(self._task_row(title, due))
        except Exception as e:
            print(f"Tasks error: {e}")

    # ── Widget factories ──────────────────────────────────────────────────────
    def _section_heading(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "font-size: 10px; font-weight: 800; letter-spacing: 2px; "
            "color: #475569; background: transparent; margin-bottom: 12px;"
        )
        return lbl

    def _action_btn(self, label, color):
        btn = QPushButton(label)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(52)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 14px;
                color: #F8FAFC;
                font-size: 14px;
                font-weight: 600;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background: {color}33;
                border-color: {color}80;
                color: white;
            }}
            QPushButton:pressed {{
                background: {color}55;
            }}
        """)
        return btn

    def _stat_card(self, value, label, color):
        card = QFrame()
        card.setFixedHeight(100)
        card.setMinimumWidth(150)
        card.setStyleSheet(f"""
            QFrame {{
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 18px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(
            f"font-size: 32px; font-weight: 800; color: {color}; background: transparent;"
        )
        lbl_lbl = QLabel(label)
        lbl_lbl.setStyleSheet("font-size: 12px; color: #64748B; background: transparent;")
        lay.addWidget(val_lbl)
        lay.addWidget(lbl_lbl)
        return card

    def _page_card(self, page_id, title, ts):
        card = QFrame()
        card.setFixedSize(200, 110)
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 16px;
            }
            QFrame:hover {
                background: rgba(99,102,241,0.12);
                border-color: rgba(99,102,241,0.5);
            }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)

        icon = QLabel("📄")
        icon.setStyleSheet("font-size: 20px; background: transparent;")
        t = QLabel((title or "Untitled")[:26])
        t.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #F8FAFC; background: transparent;"
        )
        d = QLabel(ts)
        d.setStyleSheet("font-size: 11px; color: #475569; background: transparent;")
        lay.addWidget(icon)
        lay.addWidget(t)
        lay.addWidget(d)

        card.mousePressEvent = lambda _: self._navigate(page_id)
        return card

    def _task_row(self, title, due):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
            }
        """)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(16, 10, 16, 10)

        overdue = due and due < str(date.today())
        dot_color = "#EF4444" if overdue else "#6366F1"
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {dot_color}; font-size: 10px; background: transparent;")
        lay.addWidget(dot)

        t = QLabel(title[:60])
        t.setStyleSheet("font-size: 14px; color: #F8FAFC; background: transparent;")
        lay.addWidget(t)
        lay.addStretch()

        if due:
            badge_color = "#EF444420" if overdue else "rgba(255,255,255,0.06)"
            badge_border = "#EF4444" if overdue else "rgba(255,255,255,0.1)"
            badge_text = "🔴 Overdue" if overdue else f"📅 {due}"
            due_lbl = QLabel(badge_text)
            due_lbl.setStyleSheet(f"""
                QLabel {{
                    background: {badge_color}; border: 1px solid {badge_border};
                    border-radius: 8px; padding: 3px 10px;
                    font-size: 11px; color: {'#EF4444' if overdue else '#94A3B8'};
                }}
            """)
            lay.addWidget(due_lbl)
        return card

    def _empty(self, msg):
        lbl = QLabel(msg)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            "color: #334155; font-size: 14px; background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 30px;"
        )
        return lbl

    def _navigate(self, page_id):
        if self._parent:
            if page_id == -1:
                self._parent._add_page(None)
            else:
                self._parent._navigate(page_id)

    @staticmethod
    def _clear(layout):
        while layout.count():
            w = layout.takeAt(0).widget()
            if w: w.deleteLater()
