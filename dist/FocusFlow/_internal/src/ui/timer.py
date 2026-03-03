"""
timer.py — Glassmorphism Pomodoro Timer with ring visual.
"""
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget, QListWidgetItem, QWidget)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRectF, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QConicalGradient, QFont


class TimerRing(QWidget):
    """Custom-painted circular progress ring for the Pomodoro timer."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 1.0   # 0.0 – 1.0
        self._text     = "25:00"
        self._label    = "Focus"
        self.setFixedSize(280, 280)
        self.setStyleSheet("background: transparent;")

    def set_state(self, progress, text, label="Focus"):
        self._progress = max(0.0, min(1.0, progress))
        self._text  = text
        self._label = label
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.width() / 2, self.height() / 2
        r = min(cx, cy) - 20
        span = 360 * self._progress

        # Background ring
        p.setPen(QPen(QColor(255, 255, 255, 18), 14, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # Progress arc (indigo → violet gradient)
        grad = QConicalGradient(cx, cy, 90)
        grad.setColorAt(0.0, QColor(99, 102, 241))
        grad.setColorAt(0.5, QColor(167, 139, 250))
        grad.setColorAt(1.0, QColor(99, 102, 241))
        p.setPen(QPen(QBrush(grad), 14, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2),
                  90 * 16,
                  -int(span * 16))

        # Glow dot at tip
        import math
        angle_rad = math.radians(90 - span)
        dx = cx + r * math.cos(angle_rad)
        dy = cy - r * math.sin(angle_rad)
        p.setBrush(QBrush(QColor(167, 139, 250, 200)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(dx - 7, dy - 7, 14, 14))

        # Center label
        p.setPen(QColor(148, 163, 184))
        font = QFont("Segoe UI Variable Text", 11, QFont.Normal)
        p.setFont(font)
        p.drawText(QRectF(cx - 80, cy - 60, 160, 30), Qt.AlignCenter, self._label.upper())

        p.setPen(QColor(248, 250, 252))
        font.setPointSize(38)
        font.setWeight(QFont.Bold)
        p.setFont(font)
        p.drawText(QRectF(cx - 90, cy - 24, 180, 60), Qt.AlignCenter, self._text)


class PomodoroTimer(QFrame):
    MODES = {"Focus": 25, "Short Break": 5, "Long Break": 15}

    def __init__(self, db_conn, parent=None):
        super().__init__(parent)
        self.db = db_conn
        self.current_page_id   = None
        self.current_page_title = ""
        self.seconds_left = 0
        self.total_seconds = 0
        self.is_running   = False
        self.current_mode = "Focus"

        self.setStyleSheet("QFrame { background: transparent; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(60, 50, 60, 40)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignHCenter)

        # Title
        title = QLabel("Focus Timer")
        title.setStyleSheet(
            "font-size: 28px; font-weight: 800; color: #F8FAFC; background: transparent;"
        )
        root.addWidget(title)

        self.page_lbl = QLabel("No page linked  —  navigate to a note and click ⏱ Focus")
        self.page_lbl.setStyleSheet("color: #475569; font-size: 13px; background: transparent; margin: 4px 0 24px 0;")
        root.addWidget(self.page_lbl)

        # Mode buttons
        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        self._mode_btns = {}
        for mode in self.MODES:
            btn = QPushButton(mode)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(38)
            btn.clicked.connect(lambda _, m=mode: self.set_mode(m))
            self._mode_btns[mode] = btn
            mode_row.addWidget(btn)
        mode_row.addStretch()
        root.addLayout(mode_row)
        root.addSpacing(30)

        # Ring + controls in row
        center_row = QHBoxLayout()
        center_row.setSpacing(50)
        center_row.setAlignment(Qt.AlignHCenter)

        self.ring = TimerRing()
        center_row.addWidget(self.ring)

        # Controls column
        ctrl_col = QVBoxLayout()
        ctrl_col.setAlignment(Qt.AlignCenter)
        ctrl_col.setSpacing(14)

        self.start_btn = self._big_btn("▶  Start Focus", "#6366F1")
        self.start_btn.clicked.connect(self.toggle)
        ctrl_col.addWidget(self.start_btn)

        reset_btn = self._big_btn("↺  Reset", "rgba(255,255,255,0.06)")
        reset_btn.setStyleSheet(reset_btn.styleSheet().replace("font-weight: 700", "font-weight: 500"))
        reset_btn.clicked.connect(self.reset)
        ctrl_col.addWidget(reset_btn)

        skip_btn = self._big_btn("⏭  Skip Break", "rgba(255,255,255,0.04)")
        skip_btn.clicked.connect(self._skip)
        ctrl_col.addWidget(skip_btn)

        center_row.addLayout(ctrl_col)
        root.addLayout(center_row)
        root.addSpacing(36)

        # History
        hist_hdr = QLabel("SESSION HISTORY")
        hist_hdr.setStyleSheet(
            "font-size: 10px; font-weight: 800; letter-spacing: 2px; "
            "color: #475569; background: transparent; margin-bottom: 10px;"
        )
        root.addWidget(hist_hdr)

        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(180)
        self.history_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: #94A3B8; font-size: 13px; }
            QListWidget::item {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
                padding: 10px 16px;
                margin-bottom: 6px;
            }
        """)
        root.addWidget(self.history_list)

        # Internal Qt timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)

        self.set_mode("Focus")
        self._refresh_mode_btns()
        self.load_history()

    # ── Public ───────────────────────────────────────────────────────────────
    def set_linked_page(self, page_id, page_title):
        self.current_page_id    = page_id
        self.current_page_title = page_title
        self.page_lbl.setText(f"📄  Linked: {page_title}")

    def set_mode(self, mode):
        self.current_mode = mode
        self.reset()
        self._refresh_mode_btns()

    # ── Internal ─────────────────────────────────────────────────────────────
    def _big_btn(self, text, bg):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedSize(200, 50)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 14px;
                color: white; font-size: 15px; font-weight: 700;
            }}
            QPushButton:hover {{ opacity: 0.85; border-color: rgba(255,255,255,0.25); }}
        """)
        return btn

    def _refresh_mode_btns(self):
        for mode, btn in self._mode_btns.items():
            active = mode == self.current_mode
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'rgba(99,102,241,0.3)' if active else 'rgba(255,255,255,0.05)'};
                    border: 1px solid {'rgba(99,102,241,0.7)' if active else 'rgba(255,255,255,0.1)'};
                    border-radius: 12px;
                    color: {'#F8FAFC' if active else '#94A3B8'};
                    font-size: 13px; font-weight: {'700' if active else '500'};
                    padding: 6px 18px;
                }}
                QPushButton:hover {{ background: rgba(99,102,241,0.2); color: white; }}
            """)

    def toggle(self):
        if self.is_running:
            self._timer.stop()
            self.is_running = False
            self.start_btn.setText("▶  Resume")
        else:
            if self.seconds_left <= 0:
                self.seconds_left = self.total_seconds = self.MODES[self.current_mode] * 60
            self._timer.start(1000)
            self.is_running = True
            self.start_btn.setText("⏸  Pause")

    def reset(self):
        self._timer.stop()
        self.is_running = False
        self.seconds_left = self.total_seconds = self.MODES[self.current_mode] * 60
        self._update_ring()
        self.start_btn.setText("▶  Start Focus")

    def _skip(self):
        self._timer.stop()
        self.is_running = False
        self.seconds_left = 0
        self._update_ring()
        self.start_btn.setText("▶  Start Focus")

    def _tick(self):
        self.seconds_left -= 1
        self._update_ring()
        if self.seconds_left <= 0:
            self._timer.stop()
            self.is_running = False
            self.start_btn.setText("▶  Start Focus")
            self._on_complete()

    def _update_ring(self):
        m, s = divmod(max(0, self.seconds_left), 60)
        text  = f"{m:02d}:{s:02d}"
        prog  = self.seconds_left / self.total_seconds if self.total_seconds > 0 else 0
        self.ring.set_state(prog, text, self.current_mode)

    def _on_complete(self):
        try:
            cur = self.db.cursor()
            cur.execute(
                "INSERT INTO pomodoro_history (page_id, duration_minutes, type) VALUES (?,?,?)",
                (self.current_page_id, self.MODES[self.current_mode], self.current_mode)
            )
            self.db.commit()
        except Exception as e:
            print(f"Pomo log error: {e}")
        self.load_history()

        # Tray notification
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if hasattr(app, 'tray') and app.tray:
                msg = ("Break time! 🎉" if self.current_mode == "Focus"
                       else "Back to focus! 💪")
                app.tray.showMessage("FocusFlow — Session Complete", msg, msecs=6000)
        except Exception:
            pass

    def load_history(self):
        self.history_list.clear()
        try:
            cur = self.db.cursor()
            cur.execute(
                "SELECT type, duration_minutes, completed_at "
                "FROM pomodoro_history ORDER BY completed_at DESC LIMIT 8"
            )
            for type_, dur, ts in cur.fetchall():
                icon = "🎯" if type_ == "Focus" else "☕"
                item = QListWidgetItem(
                    f"{icon}  {type_}  ·  {dur} min  ·  {ts[:16]}"
                )
                self.history_list.addItem(item)
        except Exception as e:
            print(f"History load error: {e}")
