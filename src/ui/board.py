"""
board.py — Glassmorphism Kanban Board for FocusFlow.
"""
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QScrollArea, QWidget, QPushButton, QLineEdit,
                             QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen
from datetime import date


class TaskCard(QFrame):
    def __init__(self, title, due_date=None, status="todo", parent=None):
        super().__init__(parent)
        self.setObjectName("TaskCard")
        overdue = False
        if due_date:
            try:
                overdue = date.fromisoformat(due_date) < date.today()
            except Exception:
                pass

        self.setStyleSheet(f"""
            QFrame#TaskCard {{
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                margin: 0 10px 10px 10px;
            }}
            QFrame#TaskCard:hover {{
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(99, 102, 241, 0.5);
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)

        title_lbl = QLabel(title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: 500; background: transparent;")
        layout.addWidget(title_lbl)

        if due_date:
            color = "#EF4444" if overdue else "#94A3B8"
            badge = "🔴 Overdue" if overdue else f"📅 {due_date}"
            due_lbl = QLabel(badge)
            due_lbl.setStyleSheet(f"""
                QLabel {{
                    color: {color}; font-size: 11px; margin-top: 6px; background: transparent;
                }}
            """)
            layout.addWidget(due_lbl)


class KanbanColumn(QFrame):
    task_added = pyqtSignal(str, str)   # title, status key
    COLORS = {"todo": "#94A3B8", "in_progress": "#6366F1", "done": "#10B981"}

    def __init__(self, title, status_key, parent=None):
        super().__init__(parent)
        self.status_key = status_key
        color = self.COLORS.get(status_key, "#94A3B8")

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 20px;
            }}
            QLabel#ColTitle {{
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 1.5px;
                color: {color};
                padding: 20px 20px 10px 20px;
                background: transparent;
                border: none;
            }}
            QLineEdit {{
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                color: white;
                padding: 10px 14px;
                margin: 0 14px 14px 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: rgba(99, 102, 241, 0.6);
                background: rgba(255, 255, 255, 0.08);
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        col_title = QLabel(title.upper())
        col_title.setObjectName("ColTitle")
        outer.addWidget(col_title)

        # Scrollable card area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background: transparent; border: none; border-radius: 0;")

        self.card_container = QWidget()
        self.card_container.setStyleSheet("background: transparent; border: none;")
        self.cards_layout = QVBoxLayout(self.card_container)
        self.cards_layout.setAlignment(Qt.AlignTop)
        self.cards_layout.setContentsMargins(4, 0, 4, 0)
        self.cards_layout.setSpacing(0)
        self.scroll.setWidget(self.card_container)
        outer.addWidget(self.scroll)

        # Add input
        self.input = QLineEdit()
        self.input.setPlaceholderText("+ New Task…")
        self.input.returnPressed.connect(self._on_add)
        outer.addWidget(self.input)

    def _on_add(self):
        text = self.input.text().strip()
        if text:
            self.task_added.emit(text, self.status_key)
            self.input.clear()

    def add_card(self, title, due_date=None):
        card = TaskCard(title, due_date)
        self.cards_layout.addWidget(card)

    def clear_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()


class AssignmentBoard(QFrame):
    def __init__(self, db_conn, parent=None):
        super().__init__(parent)
        self.db = db_conn
        self.setObjectName("AssignmentBoard")
        self.setStyleSheet("QFrame#AssignmentBoard { background: transparent; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(50, 48, 50, 48)
        root.setSpacing(24)

        header = QLabel("Assignments Board")
        header.setStyleSheet("font-size: 30px; font-weight: 800; color: #F8FAFC; background: transparent;")
        root.addWidget(header)

        col_row = QHBoxLayout()
        col_row.setSpacing(20)

        self.todo_col     = KanbanColumn("📋  To Do",      "todo")
        self.progress_col = KanbanColumn("🔄  In Progress", "in_progress")
        self.done_col     = KanbanColumn("✅  Done",        "done")

        for col in (self.todo_col, self.progress_col, self.done_col):
            col.task_added.connect(self._add_task)
            col_row.addWidget(col)

        root.addLayout(col_row)
        self.refresh_tasks()

    def _add_task(self, title, status):
        try:
            cur = self.db.cursor()
            cur.execute("INSERT INTO tasks (title, status) VALUES (?, ?)", (title, status))
            self.db.commit()
            self.refresh_tasks()
        except Exception as e:
            print(f"Board add task error: {e}")

    def refresh_tasks(self):
        for col in (self.todo_col, self.progress_col, self.done_col):
            col.clear_cards()
        try:
            cur = self.db.cursor()
            cur.execute("SELECT title, status, due_date FROM tasks ORDER BY id DESC")
            for title, status, due_date in cur.fetchall():
                if status == "todo":        self.todo_col.add_card(title, due_date)
                elif status == "in_progress": self.progress_col.add_card(title, due_date)
                elif status == "done":       self.done_col.add_card(title, due_date)
        except Exception as e:
            print(f"Board load error: {e}")
