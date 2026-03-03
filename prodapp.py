import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QTextEdit, QLineEdit, 
                             QTabWidget, QSpinBox, QComboBox, QListWidgetItem, QFrame,
                             QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QTimer, QSize, QUrl
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon
from PyQt5.QtWebEngineWidgets import QWebEngineView

class FocusFlowApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FocusFlow")
        self.setMinimumSize(1100, 750)
        
        # Modern Dark Theme Stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0F172A;
            }
            QWidget {
                font-family: 'Segoe UI Variable Display', 'Segoe UI', system-ui;
                color: #F8FAFC;
            }
            QFrame#Panel {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 16px;
            }
            QLabel#Header {
                font-size: 24px;
                font-weight: 800;
                color: #F8FAFC;
                margin-bottom: 20px;
            }
            QLabel#SubHeader {
                font-size: 16px;
                font-weight: 600;
                color: #94A3B8;
            }
            QPushButton {
                background: #6366F1;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #4F46E5;
            }
            QPushButton#Secondary {
                background: #334155;
                color: #F8FAFC;
            }
            QPushButton#Secondary:hover {
                background: #475569;
            }
            QLineEdit, QTextEdit, QComboBox, QSpinBox {
                background: #0F172A;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 10px;
                color: #F8FAFC;
                selection-background-color: #6366F1;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #6366F1;
            }
            QListWidget {
                border: none;
                background: transparent;
                outline: none;
            }
            QListWidget::item {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 12px;
                margin-bottom: 8px;
            }
            QListWidget::item:selected {
                border-color: #6366F1;
                background: #1E293B;
                color: #F8FAFC;
            }
            QScrollBar:vertical {
                border: none;
                background: #0F172A;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(24)

        # UI Components
        self.init_ui()
        
        # Timer logic initialization
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.seconds_left = 0

    def init_ui(self):
        # 1. Left Sidebar (Tasks)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Panel")
        self.sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 20, 20, 20)

        task_header = QLabel("Focus Tasks")
        task_header.setObjectName("Header")
        sidebar_layout.addWidget(task_header)

        self.task_list = QListWidget()
        sidebar_layout.addWidget(self.task_list)

        task_input_container = QVBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("What needs focus?")
        
        self.category_combo = QComboBox()
        self.category_combo.addItems(["Deep Work", "Personal", "Meetings", "Learning"])
        
        self.add_btn = QPushButton("Add Task")
        self.add_btn.clicked.connect(self.add_task)
        
        task_input_container.addWidget(self.task_input)
        task_input_container.addWidget(self.category_combo)
        task_input_container.addWidget(self.add_btn)
        sidebar_layout.addLayout(task_input_container)

        # 2. Main Content (Timer & Notes)
        self.content_panel = QVBoxLayout()
        
        # Timer Card
        self.timer_card = QFrame()
        self.timer_card.setObjectName("Panel")
        timer_layout = QVBoxLayout(self.timer_card)
        timer_layout.setAlignment(Qt.AlignCenter)
        timer_layout.setContentsMargins(40, 40, 40, 40)

        self.timer_label = QLabel("Focus Mode")
        self.timer_label.setObjectName("SubHeader")
        self.timer_label.setAlignment(Qt.AlignCenter)
        timer_layout.addWidget(self.timer_label)

        # Huge Timer Display
        timer_inputs = QHBoxLayout()
        self.h_spin = self.create_timer_spin(0, 12, 0)
        self.m_spin = self.create_timer_spin(0, 59, 25)
        self.s_spin = self.create_timer_spin(0, 59, 0)
        
        timer_inputs.addWidget(self.h_spin)
        timer_inputs.addWidget(self.create_separator())
        timer_inputs.addWidget(self.m_spin)
        timer_inputs.addWidget(self.create_separator())
        timer_inputs.addWidget(self.s_spin)
        timer_layout.addLayout(timer_inputs)

        timer_controls = QHBoxLayout()
        self.start_btn = QPushButton("Start Focus Session")
        self.start_btn.clicked.connect(self.start_timer)
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setObjectName("Secondary")
        self.pause_btn.clicked.connect(self.pause_timer)
        
        timer_controls.addWidget(self.start_btn)
        timer_controls.addWidget(self.pause_btn)
        timer_layout.addLayout(timer_controls)
        self.content_panel.addWidget(self.timer_card)

        # Notes Panel
        self.notes_card = QFrame()
        self.notes_card.setObjectName("Panel")
        notes_layout = QVBoxLayout(self.notes_card)
        
        notes_header = QLabel("Session Notes")
        notes_header.setObjectName("SubHeader")
        notes_layout.addWidget(notes_header)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Capture your thoughts...")
        notes_layout.addWidget(self.notes_edit)
        self.content_panel.addWidget(self.notes_card)

        # 3. Right Panel (Atmosphere/Spotify)
        self.music_panel = QFrame()
        self.music_panel.setObjectName("Panel")
        self.music_panel.setFixedWidth(300)
        music_layout = QVBoxLayout(self.music_panel)
        
        music_header = QLabel("Atmosphere")
        music_header.setObjectName("Header")
        music_layout.addWidget(music_header)
        
        # Spotify Integration Container
        spotify_container = QFrame()
        spotify_container.setStyleSheet("background: #000; border-radius: 12px; padding: 0;")
        spotify_layout = QVBoxLayout(spotify_container)
        spotify_layout.setContentsMargins(0, 0, 0, 0)
        
        self.spotify_web = QWebEngineView()
        self.spotify_web.load(QUrl("https://open.spotify.com/embed/playlist/37i9dQZF1DWVFeEut75IAL?utm_source=generator&theme=0"))
        self.spotify_web.setFixedHeight(350) 
        spotify_layout.addWidget(self.spotify_web)
        
        music_layout.addWidget(spotify_container)
        music_layout.addStretch()

        # Assemble main layout
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addLayout(self.content_panel, 2)
        self.main_layout.addWidget(self.music_panel)

    def create_timer_spin(self, min_val, max_val, val):
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(val)
        spin.setButtonSymbols(QSpinBox.NoButtons)
        spin.setAlignment(Qt.AlignCenter)
        spin.setStyleSheet("font-size: 64px; font-weight: 800; border: none; background: transparent; min-width: 100px;")
        return spin

    def create_separator(self):
        sep = QLabel(":")
        sep.setStyleSheet("font-size: 48px; font-weight: 300; color: #334155;")
        return sep

    def add_task(self):
        text = self.task_input.text().strip()
        if text:
            category = self.category_combo.currentText()
            item = QListWidgetItem(f"{text} • {category}")
            self.task_list.addItem(item)
            self.task_input.clear()

    def start_timer(self):
        h = self.h_spin.value()
        m = self.m_spin.value()
        s = self.s_spin.value()
        self.seconds_left = h * 3600 + m * 60 + s
        
        if self.seconds_left > 0:
            self.timer.start(1000)
            self.start_btn.setText("Session Running...")
            self.start_btn.setEnabled(False)

    def pause_timer(self):
        self.timer.stop()
        self.start_btn.setText("Resume Session")
        self.start_btn.setEnabled(True)

    def update_timer(self):
        if self.seconds_left > 0:
            self.seconds_left -= 1
            h = self.seconds_left // 3600
            m = (self.seconds_left % 3600) // 60
            s = self.seconds_left % 60
            
            self.h_spin.setValue(h)
            self.m_spin.setValue(m)
            self.s_spin.setValue(s)
        else:
            self.timer.stop()
            self.start_btn.setText("Start Focus Session")
            self.start_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("FocusFlow")
    window = FocusFlowApp()
    window.show()
    sys.exit(app.exec_())
