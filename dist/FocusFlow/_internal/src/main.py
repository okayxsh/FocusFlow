"""
main.py — FocusFlow shell.
"""
import sys, os

sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QStackedWidget, QShortcut, QSystemTrayIcon)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import (QColor, QKeySequence, QPainter, QLinearGradient,
                         QRadialGradient, QBrush, QFont, QPixmap)

from database import init_db
from ui.sidebar import Sidebar
from ui.dashboard import Dashboard
from ui.editor import Editor
from ui.notes_home import NotesHome
from ui.board import AssignmentBoard
from ui.timer import PomodoroTimer
from ui.settings_view import SettingsView
from core.exporter import Exporter

VIEW_DASH       = 0
VIEW_EDITOR     = 1
VIEW_BOARD      = 2
VIEW_TIMER      = 3
VIEW_SETTINGS   = 4
VIEW_NOTES_HOME = 5


class BgWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._image = None
        self._color = None

    def set_image(self, pix): self._image = pix; self._color = None; self.update()
    def set_color(self, c):   self._color = QColor(c); self._image = None; self.update()
    def clear_custom(self):   self._image = None; self._color = None; self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        if self._image:
            sc = self._image.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            p.drawPixmap((w - sc.width())//2, (h - sc.height())//2, sc)
            p.fillRect(0, 0, w, h, QColor(8, 8, 20, 140))
            return
        if self._color:
            p.fillRect(0, 0, w, h, self._color)
            return

        # Default deep-space gradient
        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0.0, QColor(7,  7, 18))
        g.setColorAt(0.4, QColor(12, 7, 30))
        g.setColorAt(0.8, QColor(7, 14, 32))
        g.setColorAt(1.0, QColor(5,  5, 15))
        p.fillRect(0, 0, w, h, QBrush(g))

        g1 = QRadialGradient(w*.14, h*.18, h*.48)
        g1.setColorAt(0, QColor(90, 50, 210, 40))
        g1.setColorAt(1, QColor(90, 50, 210,  0))
        p.fillRect(0, 0, w, h, QBrush(g1))

        g2 = QRadialGradient(w*.88, h*.82, h*.38)
        g2.setColorAt(0, QColor(30, 80, 200, 28))
        g2.setColorAt(1, QColor(30, 80, 200,  0))
        p.fillRect(0, 0, w, h, QBrush(g2))


class FocusFlowApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FocusFlow")
        self.setMinimumSize(1280, 800)

        self.current_page_id    = None
        self.current_page_title = "Untitled"
        self.distraction_free   = False

        self._save_timer = QTimer()
        self._save_timer.setInterval(2000)
        self._save_timer.timeout.connect(self._auto_save)

        os.makedirs("data", exist_ok=True)
        self.db = init_db("data/focusflow.db")

        # Shell
        self.bg = BgWidget()
        self.setCentralWidget(self.bg)

        shell = QHBoxLayout(self.bg)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.sidebar = Sidebar(self.db, self)
        shell.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        shell.addWidget(self.stack)

        # Views
        self.dashboard  = Dashboard(self)
        self.editor     = Editor(self)
        self.board      = AssignmentBoard(self.db, self)
        self.pomo       = PomodoroTimer(self.db, self)
        self.settings   = SettingsView(self.db, self)
        self.notes_home = NotesHome(self)

        for v in (self.dashboard, self.editor, self.board,
                  self.pomo, self.settings, self.notes_home):
            self.stack.addWidget(v)

        # Signals
        self.sidebar.page_selected.connect(self._navigate)
        self.sidebar.add_page_requested.connect(self._add_page)
        self.editor.attachment_added.connect(self._save_attachment)
        self.editor.export_requested.connect(self._handle_export)
        self.editor.delete_requested.connect(self._delete_page)   # NEW
        self.settings.theme_changed.connect(self._apply_theme)
        self.settings.bg_changed.connect(self._apply_bg)
        self.settings.pomodoro_changed.connect(self._update_pomo_durations)

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+N"),      self, self._new_page)
        QShortcut(QKeySequence("Ctrl+\\"),     self, self.sidebar.toggle_collapse)
        QShortcut(QKeySequence("Ctrl+D"),      self, self._toggle_distraction_free)
        QShortcut(QKeySequence("Ctrl+E"),      self, lambda: self._handle_export("pdf"))
        QShortcut(QKeySequence("Ctrl+Return"), self, self._open_timer)

        # System tray
        try:
            self.tray = QSystemTrayIcon(self)
            self.tray.show()
            QApplication.instance().tray = self.tray
        except Exception:
            pass

        self._apply_saved_settings()
        self._navigate(-1)
        self.dashboard.refresh()

    # ── Navigation ───────────────────────────────────────────────────────────
    def _navigate(self, page_id: int):
        self._auto_save()
        self.current_page_id = page_id
        self.sidebar.set_active(page_id)

        if page_id == -1:
            self._save_timer.stop()
            self.dashboard.refresh()
            self.stack.setCurrentIndex(VIEW_DASH)
        elif page_id == -2:
            self._save_timer.stop()
            self.board.refresh_tasks()
            self.stack.setCurrentIndex(VIEW_BOARD)
        elif page_id == -3:
            self._save_timer.stop()
            self.stack.setCurrentIndex(VIEW_TIMER)
        elif page_id == -4:
            self._save_timer.stop()
            self.stack.setCurrentIndex(VIEW_SETTINGS)
        elif page_id == -5:
            self._save_timer.stop()
            self.notes_home.refresh()
            self.stack.setCurrentIndex(VIEW_NOTES_HOME)
        elif page_id >= 0:
            self._load_page(page_id)
            self.stack.setCurrentIndex(VIEW_EDITOR)
            self._save_timer.start()

    def _open_timer(self):
        self._navigate(-3)
        if self.current_page_id and self.current_page_id >= 0:
            self.pomo.set_linked_page(self.current_page_id, self.current_page_title)

    # ── Page management ──────────────────────────────────────────────────────
    def _new_page(self):
        self._add_page(None)

    def _add_page(self, parent_id):
        try:
            cur = self.db.cursor()
            cur.execute(
                "INSERT INTO pages (parent_id, title, content) VALUES (?,?,?)",
                (parent_id, "Untitled Page", "")
            )
            new_id = cur.lastrowid
            self.db.commit()
            self.sidebar.refresh_pages()
            self._navigate(new_id)
        except Exception as e:
            print(f"Add page error: {e}")

    def _load_page(self, page_id: int):
        try:
            cur = self.db.cursor()
            cur.execute("SELECT title, content FROM pages WHERE id=?", (page_id,))
            row = cur.fetchone()
            if row:
                title, content = row[0], row[1]
                self.current_page_title = title or "Untitled"
                self.editor.set_content(title, content or "")
                self.editor.set_page_id(page_id)   # NEW — lets editor know its own ID

            cur.execute(
                "SELECT file_path FROM attachments WHERE page_id=? "
                "ORDER BY created_at DESC LIMIT 1",
                (page_id,)
            )
            att = cur.fetchone()
            if att:
                self.editor.set_file_to_view(att[0])   # handles missing file gracefully
                self.editor.pdf_toggle_btn.setVisible(True)
            else:
                self.editor.attach_panel.hide()
                self.editor.pdf_toggle_btn.setVisible(False)
        except Exception as e:
            print(f"Load page error: {e}")

    def _auto_save(self):
        if not self.current_page_id or self.current_page_id < 0:
            return
        title = self.editor.get_title()

        def _persist(html):
            try:
                cur = self.db.cursor()
                cur.execute(
                    "UPDATE pages SET title=?, content=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (title, html, self.current_page_id)
                )
                self.db.commit()
                self.current_page_title = title
            except Exception as e:
                print(f"Auto-save error: {e}")

        self.editor.get_content(_persist)

    def _delete_page(self, page_id: int):
        """Archive a page from the editor's delete button."""
        try:
            cur = self.db.cursor()
            cur.execute("UPDATE pages SET is_archived=1 WHERE id=?", (page_id,))
            self.db.commit()
            self.sidebar.refresh_pages()
            self._navigate(-5)           # go to notes home after delete
            self.notes_home.refresh()
        except Exception as e:
            print(f"Delete page error: {e}")

    # ── Attachments ──────────────────────────────────────────────────────────
    def _save_attachment(self, path: str):
        if not self.current_page_id or self.current_page_id < 0:
            return
        try:
            cur   = self.db.cursor()
            fname = os.path.basename(path)
            cur.execute(
                "INSERT INTO attachments (page_id, file_name, file_path) VALUES (?,?,?)",
                (self.current_page_id, fname, path)
            )
            self.db.commit()
            self.editor.insert_attachment_chip(path, fname)
            self.editor.set_file_to_view(path)
        except Exception as e:
            print(f"Attachment error: {e}")

    # ── Export ───────────────────────────────────────────────────────────────
    def _handle_export(self, fmt: str):
        if fmt == "timer":
            self._open_timer()
            return
        exp = Exporter(self.editor, self.current_page_title)
        {"pdf": exp.export_pdf, "md": exp.export_markdown,
         "txt": exp.export_plain, "copy": exp.copy_to_clipboard,
         "email": exp.send_email}.get(fmt, lambda: None)()

    # ── Theme / Background ───────────────────────────────────────────────────
    def _apply_theme(self, theme: str):
        if theme == "light":
            self.bg.set_color("#F0F4FF")
        else:
            self.bg.clear_custom()

    def _apply_bg(self, value: str):
        if os.path.isfile(value):
            pix = QPixmap(value)
            if not pix.isNull():
                self.bg.set_image(pix)
        else:
            self.bg.set_color(value)

    def _update_pomo_durations(self, d: dict):
        self.pomo.MODES["Focus"]       = d["focus"]
        self.pomo.MODES["Short Break"] = d["short"]
        self.pomo.MODES["Long Break"]  = d["long"]

    def _apply_saved_settings(self):
        try:
            cur = self.db.cursor()
            cur.execute("SELECT key, value FROM settings")
            s = dict(cur.fetchall())
            if "theme"      in s: self._apply_theme(s["theme"])
            if "background" in s: self._apply_bg(s["background"])
            if "pomodoro_focus" in s:
                self._update_pomo_durations({
                    "focus": int(s.get("pomodoro_focus", 25)),
                    "short": int(s.get("pomodoro_short",  5)),
                    "long":  int(s.get("pomodoro_long",  15)),
                })
        except Exception as e:
            print(f"Settings load error: {e}")

    # ── Distraction-free ─────────────────────────────────────────────────────
    def _toggle_distraction_free(self):
        self.distraction_free = not self.distraction_free
        if self.distraction_free:
            if not self.sidebar.is_collapsed:
                self.sidebar.toggle_collapse()
        else:
            if self.sidebar.is_collapsed:
                self.sidebar.toggle_collapse()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("FocusFlow")
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI Variable Text", 10))
    win = FocusFlowApp()
    win.show()
    sys.exit(app.exec_())