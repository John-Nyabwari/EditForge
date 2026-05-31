import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QListWidget, QListWidgetItem, QSlider, 
    QComboBox, QLineEdit, QProgressBar, QGroupBox, QFileDialog,
    QMessageBox, QStatusBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QColor, QDragEnterEvent, QDropEvent, QMimeData

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EditForge v2.0")
        self.resize(1100, 700)
        self.setMinimumSize(900, 600)
        self.setAcceptDrops(True)
        self.setup_ui()
        self.apply_dark_theme()
        self.cancel_flag = False
        self.loop_active = False

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # LEFT PANEL: Media & Clips
        left_panel = QVBoxLayout()
        
        # Music Upload & Slider
        music_box = QGroupBox("🎵 Song / Audio")
        music_layout = QVBoxLayout()
        self.music_label = QLabel("Drag & Drop MP3/WAV/AAC here")
        self.music_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.music_label.setStyleSheet("padding: 20px; border: 2px dashed #444; border-radius: 8px;")
        self.music_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        music_layout.addWidget(self.music_label)
        
        self.music_slider = QSlider(Qt.Orientation.Horizontal)
        self.music_slider.setRange(0, 100)
        self.music_slider.setEnabled(False)
        music_layout.addWidget(QLabel("Timeline Region (Phase 2: Trim/Start/Beat Offset)"))
        music_layout.addWidget(self.music_slider)
        music_box.setLayout(music_layout)
        left_panel.addWidget(music_box)

        # Clips Pane
        clips_box = QGroupBox("🎬 Clips to Sync")
        clips_layout = QVBoxLayout()
        self.clips_list = QListWidget()
        self.clips_list.setAcceptDrops(True)
        self.clips_list.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.clips_list.setStyleSheet("background: #1e1e1e; color: white; border-radius: 6px; padding: 8px;")
        self.clips_list.setMinimumHeight(200)
        clips_layout.addWidget(self.clips_list)
        clips_box.setLayout(clips_layout)
        left_panel.addWidget(clips_box)

        main_layout.addLayout(left_panel)

        # RIGHT PANEL: Controls & Settings
        right_panel = QVBoxLayout()

        # Project Settings
        proj_box = QGroupBox("⚙️ Project Settings")
        proj_layout = QVBoxLayout()
        proj_layout.addWidget(QLabel("Project Name"))
        self.proj_name = QLineEdit("EditForge_Project")
        proj_layout.addWidget(self.proj_name)
        
        proj_layout.addWidget(QLabel("Frame Rate"))
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["24", "30", "60"])
        proj_layout.addWidget(self.fps_combo)

        proj_layout.addWidget(QLabel("⚠️ Comp size will auto-match first uploaded clip"))
        proj_layout.addWidget(QLabel("Presets: Upload personal masks/LUTs/transitions"))
        self.presets_btn = QPushButton("📁 Upload Personal Presets")
        proj_layout.addWidget(self.presets_btn)
        proj_box.setLayout(proj_layout)
        right_panel.addWidget(proj_box)

        # AI / System Status
        status_box = QGroupBox("🤖 System & AI Tools")
        status_layout = QVBoxLayout()
        self.system_status = QLabel("System Status: 🔍 Checking...")
        self.system_status.setStyleSheet("color: #ffd166; font-weight: bold;")
        status_layout.addWidget(self.system_status)
        
        self.online_toggle = QComboBox()
        self.online_toggle.addItems(["🔴 Offline (Local AI Only)", "🟢 Online (Optional Cloud Fallback)"])
        status_layout.addWidget(self.online_toggle)
        
        self.ai_status = QLabel("Creative Engine: 🟡 Ready (Awaiting Media)")
        status_layout.addWidget(self.ai_status)
        status_box.setLayout(status_layout)
        right_panel.addWidget(status_box)

        # Actions
        action_box = QGroupBox("🚀 Export & Control")
        action_layout = QHBoxLayout()
        self.generate_btn = QPushButton("⚡ Analyze & Generate .jsx")
        self.generate_btn.setStyleSheet("background: #06d6a0; color: black; font-weight: bold; padding: 12px; border-radius: 6px;")
        self.cancel_btn = QPushButton("⛔ Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("background: #ef476f; color: white; padding: 12px; border-radius: 6px;")
        
        self.loop_toggle = QPushButton("🔁 Loop: OFF")
        self.loop_toggle.setCheckable(True)
        self.loop_toggle.setStyleSheet("background: #118ab2; color: white; padding: 12px; border-radius: 6px;")
        
        action_layout.addWidget(self.generate_btn)
        action_layout.addWidget(self.cancel_btn)
        action_layout.addWidget(self.loop_toggle)
        action_box.setLayout(action_layout)
        right_panel.addWidget(action_box)

        # Progress
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setValue(0)
        right_panel.addWidget(self.progress)

        main_layout.addLayout(right_panel)

        # Status Bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready. Drag & drop your audio and clips to begin.")

        # Connect Signals
        self.generate_btn.clicked.connect(self.start_generation)
        self.cancel_btn.clicked.connect(self.cancel_operation)
        self.loop_toggle.clicked.connect(self.toggle_loop)
        self.presets_btn.clicked.connect(self.upload_presets)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background: #121212; color: #ffffff; }
            QGroupBox { border: 1px solid #333; border-radius: 8px; margin-top: 10px; font-weight: bold; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QLineEdit, QComboBox { background: #1e1e1e; border: 1px solid #444; padding: 6px; border-radius: 4px; color: white; }
            QSlider::groove:horizontal { background: #333; height: 6px; border-radius: 3px; }
            QSlider::handle:horizontal { background: #06d6a0; width: 14px; margin: -4px 0; border-radius: 7px; }
            QProgressBar { border: 1px solid #444; border-radius: 4px; background: #1e1e1e; height: 20px; text-align: center; }
            QProgressBar::chunk { background: #06d6a0; border-radius: 3px; }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.handle_files(files)

    def handle_files(self, files):
        for f in files:
            if os.path.isfile(f):
                ext = os.path.splitext(f)[1].lower()
                if ext in [".mp3", ".wav", ".aac", ".flac", ".ogg"]:
                    self.music_label.setText(f"🎵 {os.path.basename(f)}")
                    self.music_slider.setEnabled(True)
                    self.statusBar.showMessage(f"Audio loaded: {os.path.basename(f)}")
                elif ext in [".mp4", ".mov", ".mkv", ".avi"]:
                    self.clips_list.addItem(f"🎬 {os.path.basename(f)}")
                    if self.clips_list.count() == 1:
                        self.statusBar.showMessage(f"Clips pane ready. Comp size will auto-match: {os.path.basename(f)}")
                elif ext in [".png", ".jpg", ".jpeg", ".luts", ".aep", ".json"]:
                    self.statusBar.showMessage(f"Asset/Mask/Preset added: {os.path.basename(f)}")
            else:
                self.statusBar.showMessage(f"Invalid path skipped: {f}")

    def upload_presets(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Upload Personal Presets/Masks", "", "All Files (*);;PNG Masks (*.png);;JSON Presets (*.json)")
        if files:
            self.statusBar.showMessage(f"{len(files)} presets/masks loaded for creative engine.")

    def start_generation(self):
        if self.clips_list.count() == 0 or self.music_label.text().startswith("Drag"):
            QMessageBox.warning(self, "Missing Media", "Please drop an audio file and at least one clip.")
            return
        
        self.generate_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.cancel_flag = False
        self.progress.setValue(0)
        self.statusBar.showMessage("🔍 Analyzing audio & building creative timeline...")
        self.ai_status.setText("Creative Engine: 🟡 Processing...")
        
        # Phase 2 will replace this with actual QThread worker
        QTimer.singleShot(100, self.simulate_phase1_ui_feedback)

    def cancel_operation(self):
        self.cancel_flag = True
        self.statusBar.showMessage("⛔ Operation cancelled by user.")
        self.ai_status.setText("Creative Engine: 🔴 Cancelled")
        self.generate_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress.setValue(0)

    def toggle_loop(self):
        self.loop_active = not self.loop_active
        self.loop_toggle.setText(f"🔁 Loop: {'ON' if self.loop_active else 'OFF'}")

    def simulate_phase1_ui_feedback(self):
        if self.cancel_flag: return
        self.progress.setValue(30)
        QTimer.singleShot(500, lambda: self.progress.setValue(60) if not self.cancel_flag else None)
        QTimer.singleShot(1000, lambda: self.finish_generation() if not self.cancel_flag else None)

    def finish_generation(self):
        if self.cancel_flag: return
        self.progress.setValue(100)
        self.ai_status.setText("Creative Engine: ✅ Ready for Phase 2 (Audio/Scene Analysis)")
        self.statusBar.showMessage("✅ UI Skeleton Complete. Phase 2 will plug in librosa, pyscenedetect & .jsx exporter.")
        self.generate_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())