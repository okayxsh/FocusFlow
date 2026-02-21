import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QListWidget, QTextEdit, QLineEdit, 
                            QTabWidget, QSpinBox, QComboBox, QListWidgetItem, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

class FocusFlowApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FocusFlow")
        self.setGeometry(100, 100, 1200, 700)
        
        # Apply light theme matching your web app
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QWidget {
                font-family: 'Segoe UI';
                color: #333;
            }
            QFrame {
                background: white;
                border-radius: 0;
            }
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #0069d9;
            }
            QLineEdit, QTextEdit, QComboBox {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
            }
            QSpinBox {
                padding: 5px;
                font-size: 20px;
                border: 1px solid #ddd;
            }
            QListWidget {
                border: none;
                background: transparent;
            }
        """)
        
        # Main container
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QHBoxLayout(self.main_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Create the three panels
        self.create_sidebar()
        self.create_main_content()
        self.create_music_panel()
        
        # Initialize timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.seconds_left = 25 * 60  # 25 minutes default
        
    def create_sidebar(self):
        """Left sidebar for tasks"""
        sidebar = QFrame()
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Tasks")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        sidebar_layout.addWidget(title)
        
        # Task list
        self.task_list = QListWidget()
        sidebar_layout.addWidget(self.task_list)
        
        # Task input
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("New task...")
        sidebar_layout.addWidget(self.task_input)
        
        # Category dropdown
        self.category_combo = QComboBox()
        self.category_combo.addItems(["Work", "Personal"])
        sidebar_layout.addWidget(self.category_combo)
        
        # Add task button
        add_button = QPushButton("Add Task")
        add_button.clicked.connect(self.add_task)
        sidebar_layout.addWidget(add_button)
        
        sidebar_layout.addStretch()
        self.layout.addWidget(sidebar)
    
    def create_main_content(self):
        """Center panel for timer and notes"""
        main = QFrame()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        # App title
        title = QLabel("FocusFlow")
        title.setStyleSheet("font-size: 28px; font-weight: bold; margin-bottom: 30px;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Timer section
        timer_frame = QFrame()
        timer_layout = QHBoxLayout(timer_frame)
        timer_layout.setAlignment(Qt.AlignCenter)
        
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 12)
        self.hours_spin.setValue(0)
        self.hours_spin.setFixedWidth(70)
        
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setValue(25)
        self.minutes_spin.setFixedWidth(70)
        
        self.seconds_spin = QSpinBox()
        self.seconds_spin.setRange(0, 59)
        self.seconds_spin.setValue(0)
        self.seconds_spin.setFixedWidth(70)
        
        timer_layout.addWidget(self.hours_spin)
        timer_layout.addWidget(QLabel(":"))
        timer_layout.addWidget(self.minutes_spin)
        timer_layout.addWidget(QLabel(":"))
        timer_layout.addWidget(self.seconds_spin)
        main_layout.addWidget(timer_frame)
        
        # Timer buttons
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        
        start_btn = QPushButton("Start")
        start_btn.clicked.connect(self.start_timer)
        
        pause_btn = QPushButton("Pause")
        pause_btn.clicked.connect(self.pause_timer)
        
        button_layout.addWidget(start_btn)
        button_layout.addWidget(pause_btn)
        main_layout.addWidget(button_frame)
        
        # Notes section
        notes_label = QLabel("Notes")
        notes_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 30px;")
        main_layout.addWidget(notes_label)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Write your notes here...")
        main_layout.addWidget(self.notes_edit)
        
        self.layout.addWidget(main)
    
    def create_music_panel(self):
        """Right panel for Spotify integration"""
        music_panel = QFrame()
        music_panel.setFixedWidth(250)
        music_layout = QVBoxLayout(music_panel)
        music_layout.setContentsMargins(20, 20, 20, 20)
        
        # Spotify card
        spotify_card = QFrame()
        spotify_card.setStyleSheet("background: #f9f9f9; border-radius: 12px;")
        spotify_layout = QVBoxLayout(spotify_card)
        spotify_layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Serenity")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        subtitle = QLabel("Ambient Sounds")
        subtitle.setStyleSheet("color: #666; margin-bottom: 15px;")
        
        # Spotify embed
        self.spotify_web = QWebEngineView()
        self.spotify_web.load(QUrl("https://open.spotify.com/embed/playlist/37i9dQZF1DWVFeEut75IAL"))
        self.spotify_web.setFixedHeight(80)
        
        spotify_layout.addWidget(title)
        spotify_layout.addWidget(subtitle)
        spotify_layout.addWidget(self.spotify_web)
        music_layout.addWidget(spotify_card)
        
        music_layout.addStretch()
        self.layout.addWidget(music_panel)
    
    def add_task(self):
        """Add a new task to the list"""
        task_text = self.task_input.text().strip()
        if task_text:
            category = self.category_combo.currentText()
            item = QListWidgetItem(f"{task_text} ({category})")
            self.task_list.addItem(item)
            self.task_input.clear()
    
    def start_timer(self):
        """Start the countdown timer"""
        hours = self.hours_spin.value()
        minutes = self.minutes_spin.value()
        seconds = self.seconds_spin.value()
        self.seconds_left = hours * 3600 + minutes * 60 + seconds
        
        if self.seconds_left > 0:
            self.timer.start(1000)
    
    def pause_timer(self):
        """Pause the running timer"""
        self.timer.stop()
    
    def update_timer(self):
        """Update timer display every second"""
        self.seconds_left -= 1
        
        if self.seconds_left <= 0:
            self.timer.stop()
            # Show time's up message
            return
        
        hours = self.seconds_left // 3600
        minutes = (self.seconds_left % 3600) // 60
        seconds = self.seconds_left % 60
        
        self.hours_spin.setValue(hours)
        self.minutes_spin.setValue(minutes)
        self.seconds_spin.setValue(seconds)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FocusFlowApp()
    window.show()
    sys.exit(app.exec_())