from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QSlider, QComboBox, QFileDialog,
                             QWidget, QScrollArea, QSizePolicy, QColorDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QPalette, QColor

class SettingsView(QFrame):
    theme_changed   = pyqtSignal(str)    # "dark" | "light"
    bg_changed      = pyqtSignal(str)    # path or hex color
    pomodoro_changed = pyqtSignal(dict)  # {focus, short, long}

    # ── Presets ────────────────────────────────────────────────────────────
    BG_PRESETS = [
        ("Slate",   "#0F172A"),
        ("Abyss",   "#06080F"),
        ("Forest",  "#0D1F0F"),
        ("Ocean",   "#0A1628"),
        ("Dusk",    "#1a0a2e"),
        ("Rose",    "#1F0E0E"),
    ]

    def __init__(self, db_conn, parent=None):
        super().__init__(parent)
        self.db = db_conn
        self.setObjectName("SettingsView")

        self._base_style = """
            QFrame#SettingsView { background: #0F172A; }
            QLabel#PageTitle {
                font-size: 28px; font-weight: 800; color: #F8FAFC;
                margin-bottom: 30px;
            }
            QLabel#SectionTitle {
                font-size: 16px; font-weight: 700; color: #6366F1;
                margin-top: 30px; margin-bottom: 12px;
            }
            QLabel#SettingLabel {
                font-size: 14px; color: #94A3B8;
            }
            QPushButton#OptionBtn {
                background: #1E293B; color: #94A3B8;
                border: 1px solid #334155; border-radius: 10px;
                padding: 10px 22px; font-size: 14px;
            }
            QPushButton#OptionBtn:hover {
                background: #334155; color: white;
            }
            QPushButton#OptionBtn[active=true] {
                background: #6366F1; color: white; border-color: #6366F1;
            }
            QPushButton#BgBtn {
                border-radius: 12px;
                min-width: 60px; min-height: 60px;
                border: 2px solid transparent;
            }
            QPushButton#BgBtn:hover { border-color: #6366F1; }
            QPushButton#BgBtn[active=true] { border-color: #6366F1; }
            QSlider::groove:horizontal {
                height: 6px; background: #334155; border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #6366F1; width: 16px; height: 16px;
                margin: -5px 0; border-radius: 8px;
            }
            QSlider::sub-page:horizontal { background: #6366F1; border-radius: 3px; }
        """
        self.setStyleSheet(self._base_style)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(60, 50, 60, 40)
        self.layout.setSpacing(8)

        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        self.layout.addWidget(title)

        self._build_theme_section()
        self._build_bg_section()
        self._build_pomodoro_section()
        self._build_shortcuts_section()

        self.layout.addStretch()

        self._load_saved_settings()

    # ── Theme ──────────────────────────────────────────────────────────────
    def _build_theme_section(self):
        self.layout.addWidget(self._section("🎨 Appearance"))
        row = QHBoxLayout()
        self.dark_btn  = self._option_btn("🌙  Dark",  lambda: self._set_theme("dark"))
        self.light_btn = self._option_btn("☀️  Light", lambda: self._set_theme("light"))
        row.addWidget(self.dark_btn)
        row.addWidget(self.light_btn)
        row.addStretch()
        self.layout.addLayout(row)

    # ── Background ─────────────────────────────────────────────────────────
    def _build_bg_section(self):
        self.layout.addWidget(self._section("🖼️ Background"))
        self.layout.addWidget(self._label("Choose a preset or pick a custom image."))

        self.bg_row = QHBoxLayout()
        self.bg_row.setSpacing(12)
        self._bg_btns = {}

        for name, color in self.BG_PRESETS:
            btn = QPushButton("")
            btn.setObjectName("BgBtn")
            btn.setToolTip(name)
            btn.setStyleSheet(f"QPushButton#BgBtn {{ background: {color}; border-radius: 12px;"
                              f"min-width:60px;min-height:60px;border:2px solid transparent;}}"
                              f"QPushButton#BgBtn:hover{{border-color:#6366F1;}}")
            btn.clicked.connect(lambda _, c=color: self._set_bg_color(c))
            self._bg_btns[color] = btn
            self.bg_row.addWidget(btn)

        custom_btn = QPushButton("🖼  Custom Image")
        custom_btn.setObjectName("OptionBtn")
        custom_btn.clicked.connect(self._pick_bg_image)
        self.bg_row.addWidget(custom_btn)
        self.bg_row.addStretch()
        self.layout.addLayout(self.bg_row)

    # ── Pomodoro ───────────────────────────────────────────────────────────
    def _build_pomodoro_section(self):
        self.layout.addWidget(self._section("⏱️ Pomodoro Durations"))

        self.focus_slider = self._slider_row("Focus", 10, 90, 25)
        self.short_slider = self._slider_row("Short Break", 1, 20, 5)
        self.long_slider  = self._slider_row("Long Break",  5, 45, 15)

    def _slider_row(self, label, min_, max_, default):
        row = QHBoxLayout()
        lbl = QLabel(f"{label}:")
        lbl.setObjectName("SettingLabel")
        lbl.setFixedWidth(120)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_, max_)
        slider.setValue(default)
        slider.setFixedWidth(220)
        val_lbl = QLabel(f"{default} min")
        val_lbl.setObjectName("SettingLabel")
        val_lbl.setFixedWidth(60)
        slider.valueChanged.connect(lambda v: val_lbl.setText(f"{v} min"))
        slider.sliderReleased.connect(self._save_pomodoro)
        row.addWidget(lbl)
        row.addWidget(slider)
        row.addWidget(val_lbl)
        row.addStretch()
        self.layout.addLayout(row)
        return slider

    # ── Shortcuts ──────────────────────────────────────────────────────────
    def _build_shortcuts_section(self):
        self.layout.addWidget(self._section("⌨️ Keyboard Shortcuts"))
        shortcuts = [
            ("Ctrl + N",     "New Page"),
            ("Ctrl + F",     "Focus Search"),
            ("Ctrl + Enter", "Start Pomodoro"),
            ("Ctrl + E",     "Export Current Note"),
            ("Ctrl + \\",    "Toggle Sidebar"),
            ("Ctrl + D",     "Distraction-Free Mode"),
        ]
        for keys, action in shortcuts:
            row = QHBoxLayout()
            k = QLabel(f"  {keys}  ")
            k.setStyleSheet("background:#1E293B; color:#6366F1; border-radius:6px; "
                            "padding:4px 8px; font-family:monospace; font-size:13px;")
            a = QLabel(action)
            a.setObjectName("SettingLabel")
            a.setContentsMargins(12, 0, 0, 0)
            row.addWidget(k, 0)
            row.addWidget(a, 0)
            row.addStretch()
            self.layout.addLayout(row)

    # ── Helpers ────────────────────────────────────────────────────────────
    def _section(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("SectionTitle")
        return lbl

    def _label(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("SettingLabel")
        return lbl

    def _option_btn(self, text, slot):
        btn = QPushButton(text)
        btn.setObjectName("OptionBtn")
        btn.clicked.connect(slot)
        return btn

    # ── Actions ────────────────────────────────────────────────────────────
    def _set_theme(self, theme):
        active = theme == "dark"
        for btn, is_dark in [(self.dark_btn, True), (self.light_btn, False)]:
            btn.setProperty("active", active == is_dark)
            btn.style().unpolish(btn); btn.style().polish(btn)
        self._save_setting("theme", theme)
        self.theme_changed.emit(theme)

    def _set_bg_color(self, color):
        for c, btn in self._bg_btns.items():
            btn.setProperty("active", c == color)
            btn.style().unpolish(btn); btn.style().polish(btn)
        self._save_setting("background", color)
        self.bg_changed.emit(color)

    def _pick_bg_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose Background Image", "",
                                              "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if path:
            self._save_setting("background", path)
            self.bg_changed.emit(path)

    def _save_pomodoro(self):
        d = {"focus": self.focus_slider.value(),
             "short": self.short_slider.value(),
             "long":  self.long_slider.value()}
        self._save_setting("pomodoro_focus",  str(d["focus"]))
        self._save_setting("pomodoro_short",  str(d["short"]))
        self._save_setting("pomodoro_long",   str(d["long"]))
        self.pomodoro_changed.emit(d)

    def _save_setting(self, key, value):
        try:
            cursor = self.db.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            self.db.commit()
        except Exception as e:
            print(f"Settings save error: {e}")

    def _load_saved_settings(self):
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT key, value FROM settings")
            s = dict(cursor.fetchall())
            # Theme
            theme = s.get("theme", "dark")
            btn = self.dark_btn if theme == "dark" else self.light_btn
            btn.setProperty("active", True)
            btn.style().unpolish(btn); btn.style().polish(btn)
            # Pomodoro
            if "pomodoro_focus" in s:
                self.focus_slider.setValue(int(s["pomodoro_focus"]))
            if "pomodoro_short" in s:
                self.short_slider.setValue(int(s["pomodoro_short"]))
            if "pomodoro_long" in s:
                self.long_slider.setValue(int(s["pomodoro_long"]))
        except Exception as e:
            print(f"Settings load error: {e}")
