import sys
import os
import json
import subprocess
import logging
import threading
import numpy as np
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QListWidget, QSlider, QComboBox, QLineEdit, 
    QProgressBar, QGroupBox, QFileDialog, QMessageBox, QStatusBar,
    QSizePolicy, QTextEdit, QDoubleSpinBox, QTabWidget, QScrollArea,
    QFrame, QGridLayout, QGraphicsDropShadowEffect, QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QSize
from PyQt6.QtGui import QColor, QBrush, QPen, QPainter, QFont, QMouseEvent, QIcon, QLinearGradient, QRadialGradient, QCursor
from PyQt6.QtWidgets import QGraphicsOpacityEffect

# ==================== LOGGING ====================
os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename="logs/app.log", level=logging.INFO, 
                    format="%(asctime)s | %(levelname)-8s | %(message)s")
logging.info("EditForge v5.1 Sleek UI initialized")

# ==================== CUSTOM WIDGETS ====================
class ModernButton(QPushButton):
    def __init__(self, text, icon="⚡", color="#06d6a0"):
        super().__init__(text)
        self.color = color
        self.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color}, stop:1 {color}dd);
                color: #000;
                border: none;
                border-radius: 12px;
                padding: 14px 24px;
                font-weight: 600;
                text-align: center;
                icon: {icon};
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color}, stop:1 {color}bb);
                transform: scale(1.02);
            }}
            QPushButton:pressed {{
                transform: scale(0.98);
            }}
            QPushButton:disabled {{
                background: #333;
                color: #666;
            }}
        """)
        
class SidebarButton(QPushButton):
    def __init__(self, text, icon, active=False):
        super().__init__()
        self.active = active
        self.setFont(QFont("Segoe UI", 11))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {'#1a3a4a' if active else '#16212e'};
                color: #fff;
                border: {'2px solid #06d6a0' if active else '1px solid #2a3b4c'};
                border-radius: 16px;
                padding: 16px 20px;
                text-align: left;
                font-weight: {'600' if active else '400'};
            }}
            QPushButton:hover {{
                background: #1f4a5a;
                border-color: #06d6a0;
            }}
        """)
        self.setText(f"{icon} {text}")

class CardWidget(QFrame):
    def __init__(self, title="", subtitle=""):
        super().__init__()
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a2332, stop:1 #141b26);
                border: 1px solid #2a3b4c;
                border-radius: 20px;
                padding: 20px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

class ModernSlider(QSlider):
    def __init__(self, orientation=Qt.Orientation.Horizontal):
        super().__init__(orientation)
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #2a3b4c;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06d6a0, stop:1 #06d6a0dd);
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
                border: 2px solid #1a2332;
            }
            QSlider::sub-page:horizontal {
                background: #06d6a0;
                border-radius: 4px;
            }
        """)

class ModernProgressBar(QProgressBar):
    def __init__(self):
        super().__init__()
        self.setTextVisible(True)
        self.setStyleSheet("""
            QProgressBar {
                background: #1a2332;
                border: 1px solid #2a3b4c;
                border-radius: 12px;
                height: 24px;
                text-align: center;
                color: #fff;
                font-weight: 600;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06d6a0, stop:1 #06d6a0dd);
                border-radius: 11px;
            }
        """)

class GlowLabel(QLabel):
    def __init__(self, text, glow_color="#06d6a0"):
        super().__init__(text)
        self.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.setStyleSheet(f"""
            QLabel {{
                color: {glow_color};
                text-shadow: 0 0 20px {glow_color}80, 0 0 40px {glow_color}40;
            }}
        """)

# ==================== MAIN UI ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EditForge v5.1 Creative Engine")
        self.resize(1400, 900)
        self.setMinimumSize(1200, 800)
        self.setAcceptDrops(True)
        self.setup_ui()
        self.apply_theme()
        self.audio_path = None
        self.clip_paths = []
        self.worker = None

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        main.setSpacing(0)
        main.setContentsMargins(0, 0, 0, 0)
        
        # SIDEBAR
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0d1421, stop:1 #16212e);
                border-right: 1px solid #2a3b4c;
            }
        """)
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(20, 30, 20, 30)
        sv.setSpacing(16)
        
        logo = GlowLabel("⚡ EditForge")
        logo.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        sv.addWidget(logo)
        sv.addWidget(QLabel("Creative Engine"))
        sv.addSpacing(20)
        
        self.btn_analyze = SidebarButton("Analyze & Export", "🎵", True)
        self.btn_tools = SidebarButton("Creative Tools", "🛠️")
        self.btn_settings = SidebarButton("Settings", "️")
        
        sv.addWidget(self.btn_analyze)
        sv.addWidget(self.btn_tools)
        sv.addWidget(self.btn_settings)
        sv.addStretch()
        
        sv.addWidget(QLabel("System Status", styleSheet="color: #667; font-size: 10px;"))
        self.sys_indicator = QLabel(" Online", styleSheet="color: #06d6a0; font-weight: 600;")
        sv.addWidget(self.sys_indicator)
        
        main.addWidget(sidebar)
        
        # CONTENT AREA
        content = QFrame()
        content.setStyleSheet("background: #0d1421;")
        cv = QVBoxLayout(content)
        cv.setContentsMargins(30, 30, 30, 30)
        cv.setSpacing(24)
        
        # TOP BAR
        top_bar = QHBoxLayout()
        top_bar.addWidget(GlowLabel("🎬 Project Workspace"))
        top_bar.addStretch()
        self.version_lbl = QLabel("v5.1.0 | Build 2026", styleSheet="color: #667; font-size: 12px;")
        top_bar.addWidget(self.version_lbl)
        cv.addLayout(top_bar)
        
        # WORKSPACE GRID
        workspace = QHBoxLayout()
        workspace.setSpacing(24)
        
        # LEFT PANEL: INPUTS
        left_panel = QVBoxLayout()
        left_panel.setSpacing(16)
        
        # Audio Card
        audio_card = CardWidget("🎵 Audio Source")
        audio_layout = QVBoxLayout(audio_card)
        self.music_lbl = QLabel("Drag & Drop MP3/WAV/AAC here")
        self.music_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.music_lbl.setStyleSheet("""
            QLabel {
                background: #1a2332;
                border: 2px dashed #2a3b4c;
                border-radius: 16px;
                padding: 30px;
                color: #667;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #06d6a0;
                color: #06d6a0;
            }
        """)
        audio_layout.addWidget(self.music_lbl)
        
        # Trim Controls
        trim_card = CardWidget("✂️ Trim & Offset")
        trim_layout = QGridLayout(trim_card)
        trim_layout.setSpacing(12)
        trim_layout.addWidget(QLabel("Start (s)", styleSheet="color: #889;"), 0, 0)
        self.sp_s = QDoubleSpinBox()
        self.sp_s.setRange(0, 300)
        self.sp_s.setStyleSheet("QDoubleSpinBox { background: #1a2332; border: 1px solid #2a3b4c; border-radius: 8px; padding: 8px; color: #fff; }")
        trim_layout.addWidget(self.sp_s, 0, 1)
        trim_layout.addWidget(QLabel("End (s)", styleSheet="color: #889;"), 0, 2)
        self.sp_e = QDoubleSpinBox()
        self.sp_e.setRange(1, 600)
        self.sp_e.setValue(30)
        self.sp_e.setStyleSheet("QDoubleSpinBox { background: #1a2332; border: 1px solid #2a3b4c; border-radius: 8px; padding: 8px; color: #fff; }")
        trim_layout.addWidget(self.sp_e, 0, 3)
        trim_layout.addWidget(QLabel("Beat Offset", styleSheet="color: #889;"), 1, 0)
        self.sp_off = QDoubleSpinBox()
        self.sp_off.setRange(0, 30)
        self.sp_off.setSingleStep(0.1)
        self.sp_off.setStyleSheet("QDoubleSpinBox { background: #1a2332; border: 1px solid #2a3b4c; border-radius: 8px; padding: 8px; color: #fff; }")
        trim_layout.addWidget(self.sp_off, 1, 1)
        left_panel.addWidget(audio_card)
        left_panel.addWidget(trim_card)
        
        # Clips Card
        clips_card = CardWidget("🎬 Clips to Sync")
        clips_layout = QVBoxLayout(clips_card)
        self.clips_list = QListWidget()
        self.clips_list.setAcceptDrops(True)
        self.clips_list.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.clips_list.setStyleSheet("""
            QListWidget {
                background: #1a2332;
                border: 1px solid #2a3b4c;
                border-radius: 12px;
                padding: 10px;
                color: #fff;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 8px;
                margin: 2px 0;
                background: #243040;
            }
            QListWidget::item:hover {
                background: #2a4050;
            }
        """)
        clips_layout.addWidget(self.clips_list)
        left_panel.addWidget(clips_card)
        
        workspace.addLayout(left_panel)
        
        # RIGHT PANEL: PREVIEW & CONTROLS
        right_panel = QVBoxLayout()
        right_panel.setSpacing(16)
        
        # Preview Card
        preview_card = CardWidget("📊 Beat Timeline Preview")
        preview_layout = QVBoxLayout(preview_card)
        self.preview_area = QLabel("Timeline visualization will appear here after analysis")
        self.preview_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_area.setStyleSheet("""
            QLabel {
                background: #1a2332;
                border-radius: 16px;
                padding: 40px;
                color: #667;
                font-size: 14px;
            }
        """)
        preview_layout.addWidget(self.preview_area)
        right_panel.addWidget(preview_card)
        
        # Actions Card
        actions_card = CardWidget("🚀 Generate Project")
        actions_layout = QVBoxLayout(actions_card)
        self.progress = ModernProgressBar()
        self.progress.setValue(0)
        actions_layout.addWidget(self.progress)
        
        btn_row = QHBoxLayout()
        self.gen_btn = ModernButton(" Analyze & Build .jsx", "🎵", "#06d6a0")
        self.cancel_btn = ModernButton(" Cancel", "✕", "#ef476f")
        self.cancel_btn.setEnabled(False)
        btn_row.addWidget(self.gen_btn)
        btn_row.addWidget(self.cancel_btn)
        actions_layout.addLayout(btn_row)
        
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("""
            QTextEdit {
                background: #141b26;
                border: 1px solid #2a3b4c;
                border-radius: 12px;
                padding: 12px;
                color: #06d6a0;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
        """)
        self.log_box.setMaximumHeight(150)
        actions_layout.addWidget(self.log_box)
        right_panel.addWidget(actions_card)

        # --- OUTPUT PANE (Initially Hidden) ---
        self.output_card = CardWidget("📦 Output & Export")
        output_layout = QVBoxLayout(self.output_card)
        
        self.output_status_lbl = QLabel("✅ Project generated successfully!")
        self.output_status_lbl.setStyleSheet("color: #06d6a0; font-size: 16px; font-weight: bold;")
        output_layout.addWidget(self.output_status_lbl)
        
        self.output_path_lbl = QLabel("📁 Location: Waiting for analysis...")
        self.output_path_lbl.setStyleSheet("color: #889; font-size: 12px;")
        self.output_path_lbl.setWordWrap(True)
        output_layout.addWidget(self.output_path_lbl)
        
        out_btn_layout = QHBoxLayout()
        self.btn_open_folder = ModernButton("📂 Open Folder", "", "#118ab2")
        self.btn_open_folder.clicked.connect(self.open_output_folder)
        out_btn_layout.addWidget(self.btn_open_folder)
        
        self.btn_save_as = ModernButton("💾 Save As...", "", "#ffd166")
        self.btn_save_as.clicked.connect(self.save_jsx_as)
        out_btn_layout.addWidget(self.btn_save_as)
        
        output_layout.addLayout(out_btn_layout)
        
        self.output_card.setVisible(False) # Hide until the process finishes
        right_panel.addWidget(self.output_card)
        
        workspace.addLayout(right_panel)
        cv.addLayout(workspace)
        main.addWidget(content)
        
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.setStyleSheet("color: #667; border-top: 1px solid #2a3b4c;")
        
        self.gen_btn.clicked.connect(self.start_analysis)
        self.cancel_btn.clicked.connect(self.cancel_analysis)

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background: #0d1421; color: #fff; }
            QScrollArea { border: none; background: transparent; }
            QTabWidget::pane { border: none; background: transparent; }
            QTabBar::tab { background: #1a2332; border: 1px solid #2a3b4c; border-bottom: none; border-radius: 8px 8px 0 0; padding: 12px 24px; color: #889; }
            QTabBar::tab:selected { background: #243040; color: #06d6a0; font-weight: 600; }
            QComboBox { background: #1a2332; border: 1px solid #2a3b4c; border-radius: 8px; padding: 10px; color: #fff; }
            QComboBox::drop-down { border: none; }
            QDoubleSpinBox { background: #1a2332; border: 1px solid #2a3b4c; border-radius: 8px; padding: 8px; color: #fff; }
            QPushButton { border: none; }
            QLabel { color: #fff; }
        """)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
        
    def dropEvent(self, e):
        for u in e.mimeData().urls():
            f = u.toLocalFile()
            if not os.path.isfile(f): continue
            ext = os.path.splitext(f)[1].lower()
            if ext in [".mp3",".wav",".aac",".flac"]:
                self.audio_path = f
                self.music_lbl.setText(f"🎵 {os.path.basename(f)}")
                self.music_lbl.setStyleSheet("""
                    QLabel {
                        background: #1a3a2a;
                        border: 2px solid #06d6a0;
                        border-radius: 16px;
                        padding: 30px;
                        color: #06d6a0;
                        font-size: 14px;
                        font-weight: 600;
                    }
                """)
                self.log_box.append(f"✅ Audio loaded: {os.path.basename(f)}")
            elif ext in [".mp4",".mov",".mkv"]:
                self.clip_paths.append(f)
                self.clips_list.addItem(f"🎬 {os.path.basename(f)}")
                self.log_box.append(f"✅ Clip added: {os.path.basename(f)}")

    def start_analysis(self):
        if not self.audio_path or not self.clip_paths:
            QMessageBox.warning(self, "Missing Media", "Please drop an audio file and at least one clip.")
            return
            
        self.gen_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.log_box.clear()
        self.progress.setValue(0)
        self.log_box.append("🔍 Starting analysis...")
        self.statusBar.showMessage("Processing...")
        
        # Hide output card if it was previously visible from a past run
        self.output_card.setVisible(False)
        
        # Simulate progress for UI demo
        self._simulate_progress()

    def _simulate_progress(self):
        import random
        steps = [
            (10, "🎵 Loading audio & detecting beats..."),
            (25, "🥁 Analyzing rhythm patterns..."),
            (40, "🎬 Scanning clip boundaries..."),
            (60, "📐 Matching scenes to beats..."),
            (75, "🎨 Applying creative patterns..."),
            (90, "⚡ Generating .jsx script..."),
            (100, "✅ Project ready!")
        ]
        for i, (pct, msg) in enumerate(steps):
            QTimer.singleShot(i * 800, lambda p=pct, m=msg: (
                self.progress.setValue(p),
                self.log_box.append(m),
                self.statusBar.showMessage(m)
            ))
            
        # When finished, show the output pane
        QTimer.singleShot(5600, lambda: (
            self.gen_btn.setEnabled(True),
            self.cancel_btn.setEnabled(False),
            self.statusBar.showMessage("✅ Complete. Open .jsx in After Effects."),
            self.show_output_pane() 
        ))

    def cancel_analysis(self):
        self.progress.setValue(0)
        self.log_box.append("⛔ Operation cancelled by user.")
        self.gen_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.statusBar.showMessage("Cancelled.")

    def show_output_pane(self):
        """Called when analysis finishes to show the output pane and create a file."""
        os.makedirs("output", exist_ok=True)
        self.output_jsx_path = os.path.abspath("output/EditForge_Project.jsx")
        
        # Create a dummy JSX file so it appears in the folder
        with open(self.output_jsx_path, "w") as f:
            f.write("// EditForge Generated JSX Script\n// Replace this with actual generation logic\n")
            
        self.output_status_lbl.setText("✅ Project generated successfully!")
        self.output_path_lbl.setText(f"📁 Location: {self.output_jsx_path}")
        
        # Show the hidden card
        self.output_card.setVisible(True)
        self.log_box.append(f"🎉 Finished! File ready at: {self.output_jsx_path}")

    def open_output_folder(self):
        """Opens the output folder in Windows Explorer and highlights the file."""
        if hasattr(self, 'output_jsx_path') and os.path.exists(self.output_jsx_path):
            # Open folder and highlight the specific file
            subprocess.Popen(f'explorer /select,"{self.output_jsx_path}"')
        else:
            os.startfile(os.path.abspath("output"))

    def save_jsx_as(self):
        """Allows the user to save the file to a custom location."""
        if not hasattr(self, 'output_jsx_path'):
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save JSX File", "EditForge_Project.jsx", "JSX Files (*.jsx);;All Files (*)"
        )
        if file_path:
            import shutil
            shutil.copy(self.output_jsx_path, file_path)
            self.log_box.append(f"💾 Saved to: {file_path}")
            QMessageBox.information(self, "Saved", f"Project saved to:\n{file_path}")

    def check_deps(self):
        # Simplified for UI demo
        self.sys_indicator.setText("🟢 Online")
        self.sys_indicator.setStyleSheet("color: #06d6a0; font-weight: 600;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())