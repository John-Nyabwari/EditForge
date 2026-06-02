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
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QSize, QRect
from PyQt6.QtGui import QColor, QBrush, QPen, QPainter, QFont, QMouseEvent, QIcon, QLinearGradient, QRadialGradient, QCursor, QPainterPath, QFontDatabase
from PyQt6.QtWidgets import QGraphicsOpacityEffect

# ==================== LOGGING ====================
os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename="logs/app.log", level=logging.INFO,
                    format="%(asctime)s | %(levelname)-8s | %(message)s")
logging.info("EditForge v5.1 Creative Engine initialized")

# ==================== DESIGN TOKENS ====================
TOKENS = {
    "bg": "#0b1117",
    "surface": "#141c27",
    "surface2": "#1c2837",
    "border": "#243040",
    "border_active": "#06d6a0",
    "accent": "#06d6a0",
    "accent2": "#118ab2",
    "warning": "#ffd166",
    "danger": "#ef476f",
    "text": "#e8edf2",
    "text_secondary": "#7a8a9e",
    "text_dim": "#4a5a6e",
    "radius": "14px",
    "radius_sm": "10px",
    "radius_lg": "20px",
    "shadow": "rgba(0,0,0,0.4)",
    "font": "Segoe UI",
    "mono": "Cascadia Code, Consolas, monospace",
}

def _styles(**overrides):
    t = {**TOKENS, **overrides}
    return t

# ==================== BASE WIDGETS ====================
class GlassFrame(QFrame):
    def __init__(self, radius=None):
        super().__init__()
        r = radius or TOKENS["radius_lg"]
        self.setStyleSheet(f"""
            GlassFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(28,40,55,0.85), stop:1 rgba(20,28,39,0.75));
                border: 1px solid {TOKENS["border"]};
                border-radius: {r};
            }}
        """)

class ModernButton(QPushButton):
    def __init__(self, text, icon="", color=TOKENS["accent"], compact=False):
        super().__init__(f" {icon} {text}" if icon else text)
        self._color = color
        p = "10px 18px" if compact else "14px 28px"
        self.setFont(QFont(TOKENS["font"], 10, QFont.Weight.Medium))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {color}, stop:1 {color}cc);
                color: #000;
                border: none;
                border-radius: {TOKENS["radius"]};
                padding: {p};
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {color}, stop:1 {color}aa);
            }}
            QPushButton:pressed {{
                padding-top: 15px; padding-bottom: 13px;
            }}
            QPushButton:disabled {{
                background: #243040;
                color: #4a5a6e;
            }}
        """)

class GhostButton(QPushButton):
    def __init__(self, text, icon=""):
        super().__init__(f" {icon} {text}" if icon else text)
        self.setFont(QFont(TOKENS["font"], 10))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TOKENS["text_secondary"]};
                border: 1px solid {TOKENS["border"]};
                border-radius: {TOKENS["radius"]};
                padding: 10px 18px;
            }}
            QPushButton:hover {{
                background: {TOKENS["surface2"]};
                color: {TOKENS["text"]};
                border-color: {TOKENS["border_active"]};
            }}
        """)

class NavButton(QPushButton):
    def __init__(self, text, icon, active=False):
        super().__init__(f" {icon}  {text}")
        self._active = active
        self.setFont(QFont(TOKENS["font"], 11))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_style()

    def set_active(self, active):
        self._active = active
        self.update_style()

    def update_style(self):
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(6,214,160,0.12), stop:1 transparent);
                    color: {TOKENS["accent"]};
                    border: none;
                    border-left: 3px solid {TOKENS["accent"]};
                    border-radius: 0 12px 12px 0;
                    padding: 14px 20px 14px 16px;
                    font-weight: 700;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {TOKENS["text_secondary"]};
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0 12px 12px 0;
                    padding: 14px 20px 14px 16px;
                }}
                QPushButton:hover {{
                    background: {TOKENS["surface2"]};
                    color: {TOKENS["text"]};
                }}
            """)

class DropZone(QLabel):
    def __init__(self, placeholder, icon):
        super().__init__()
        self._placeholder = placeholder
        self._icon = icon
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.reset()

    def reset(self):
        self.setText(f"{self._icon}\n{self._placeholder}")
        self.setStyleSheet(f"""
            QLabel {{
                background: {TOKENS["surface"]};
                border: 2px dashed {TOKENS["border"]};
                border-radius: {TOKENS["radius_lg"]};
                padding: 24px;
                color: {TOKENS["text_dim"]};
                font-size: 13px;
            }}
        """)

    def set_file(self, path, icon):
        self.setText(f" {icon}  {os.path.basename(path)}")
        self.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(6,214,160,0.10), stop:1 rgba(6,214,160,0.03));
                border: 2px solid {TOKENS["accent"]};
                border-radius: {TOKENS["radius_lg"]};
                padding: 24px;
                color: {TOKENS["accent"]};
                font-size: 14px;
                font-weight: 600;
            }}
        """)

class ModernSpinBox(QDoubleSpinBox):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"""
            QDoubleSpinBox {{
                background: {TOKENS["surface"]};
                border: 1px solid {TOKENS["border"]};
                border-radius: {TOKENS["radius_sm"]};
                padding: 8px 12px;
                color: {TOKENS["text"]};
                font-size: 12px;
            }}
            QDoubleSpinBox:focus {{
                border-color: {TOKENS["accent"]};
            }}
        """)

class ModernProgress(QProgressBar):
    def __init__(self):
        super().__init__()
        self.setTextVisible(True)
        self.setStyleSheet(f"""
            QProgressBar {{
                background: {TOKENS["surface"]};
                border: 1px solid {TOKENS["border"]};
                border-radius: {TOKENS["radius"]};
                height: 22px;
                text-align: center;
                color: {TOKENS["text"]};
                font-weight: 600;
                font-size: 11px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {TOKENS["accent"]}, stop:1 {TOKENS["accent2"]});
                border-radius: 12px;
            }}
        """)

class LogConsole(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumHeight(140)
        self.setStyleSheet(f"""
            QTextEdit {{
                background: {TOKENS["surface"]};
                border: 1px solid {TOKENS["border"]};
                border-radius: {TOKENS["radius"]};
                padding: 12px;
                color: {TOKENS["accent"]};
                font-family: {TOKENS["mono"]};
                font-size: 11px;
            }}
        """)

class TimelinePreview(QLabel):
    def __init__(self):
        super().__init__("Drop audio and clips, then analyze to see the beat timeline")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(180)
        self.setStyleSheet(f"""
            QLabel {{
                background: {TOKENS["surface"]};
                border-radius: {TOKENS["radius_lg"]};
                padding: 32px;
                color: {TOKENS["text_dim"]};
                font-size: 13px;
            }}
        """)

class StatusDot(QLabel):
    def __init__(self, online=True):
        super().__init__()
        self._online = online
        self.update_state(online)

    def update_state(self, online):
        self._online = online
        c = TOKENS["accent"] if online else TOKENS["danger"]
        self.setText(f"  {chr(9679)} {'Online' if online else 'Offline'}")
        self.setStyleSheet(f"color: {c}; font-size: 12px; font-weight: 600;")

class FieldLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet(f"color: {TOKENS['text_secondary']}; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;")

# ==================== MAIN UI ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EditForge Creative Engine")
        self.resize(1440, 920)
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

        # ====== SIDEBAR ======
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {TOKENS["bg"]}, stop:1 {TOKENS["surface"]});
                border-right: 1px solid {TOKENS["border"]};
            }}
        """)
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(0, 0, 0, 20)
        sv.setSpacing(4)

        logo_area = QFrame()
        logo_area.setStyleSheet(f"background: transparent; padding: 24px 20px 16px;")
        logo_layout = QVBoxLayout(logo_area)
        logo_layout.setSpacing(2)

        title = QLabel("EditForge")
        title.setFont(QFont(TOKENS["font"], 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TOKENS['text']}; background: transparent;")
        logo_layout.addWidget(title)

        subtitle = QLabel("Creative Engine")
        subtitle.setFont(QFont(TOKENS["font"], 10))
        subtitle.setStyleSheet(f"color: {TOKENS['text_dim']}; background: transparent; letter-spacing: 2px; text-transform: uppercase;")
        logo_layout.addWidget(subtitle)

        sv.addWidget(logo_area)

        sv.addSpacing(12)
        nav_label = QLabel("   NAVIGATION")
        nav_label.setStyleSheet(f"color: {TOKENS['text_dim']}; font-size: 9px; letter-spacing: 2px; padding: 8px 20px; background: transparent;")
        sv.addWidget(nav_label)

        self.btn_analyze = NavButton("Analyze & Export", "\U0001f3b5", True)
        self.btn_tools = NavButton("Creative Tools", "\U0001f6e0\ufe0f")
        self.btn_settings = NavButton("Settings", "\u2699\ufe0f")
        sv.addWidget(self.btn_analyze)
        sv.addWidget(self.btn_tools)
        sv.addWidget(self.btn_settings)

        sv.addStretch()

        status_area = QFrame()
        status_area.setStyleSheet(f"background: transparent; padding: 16px 20px 0;")
        status_layout = QVBoxLayout(status_area)
        status_layout.setSpacing(8)
        status_label = QLabel("   SYSTEM")
        status_label.setStyleSheet(f"color: {TOKENS['text_dim']}; font-size: 9px; letter-spacing: 2px; background: transparent;")
        status_layout.addWidget(status_label)

        self.sys_indicator = StatusDot(True)
        status_layout.addWidget(self.sys_indicator)

        ver = QLabel("v5.1.0  ·  Build 2026")
        ver.setStyleSheet(f"color: {TOKENS['text_dim']}; font-size: 10px; background: transparent;")
        status_layout.addWidget(ver)

        sv.addWidget(status_area)

        main.addWidget(sidebar)

        # ====== CONTENT ======
        content = QFrame()
        content.setStyleSheet(f"background: {TOKENS['bg']};")
        cv = QVBoxLayout(content)
        cv.setContentsMargins(28, 28, 28, 28)
        cv.setSpacing(20)

        # Top bar
        top_bar = QHBoxLayout()
        page_title = QLabel("Analyze & Export")
        page_title.setFont(QFont(TOKENS["font"], 18, QFont.Weight.Bold))
        page_title.setStyleSheet(f"color: {TOKENS['text']};")
        top_bar.addWidget(page_title)
        top_bar.addStretch()
        top_bar.addWidget(GhostButton("Documentation", "\U0001f4d6"))
        top_bar.addWidget(GhostButton("Feedback", "\U0001f4ac"))
        cv.addLayout(top_bar)

        # ====== WORKSPACE ======
        workspace = QHBoxLayout()
        workspace.setSpacing(20)

        # --- LEFT COLUMN ---
        left_col = QVBoxLayout()
        left_col.setSpacing(16)

        # Audio Card
        audio_card = GlassFrame()
        audio_layout = QVBoxLayout(audio_card)
        audio_header = QHBoxLayout()
        audio_title = QLabel("\U0001f3b5  Audio Source")
        audio_title.setFont(QFont(TOKENS["font"], 13, QFont.Weight.Bold))
        audio_title.setStyleSheet(f"color: {TOKENS['text']};")
        audio_header.addWidget(audio_title)
        audio_header.addStretch()
        format_lbl = QLabel("MP3 · WAV · AAC")
        format_lbl.setStyleSheet(f"color: {TOKENS['text_dim']}; font-size: 10px; background: transparent;")
        audio_header.addWidget(format_lbl)
        audio_layout.addLayout(audio_header)

        self.music_zone = DropZone("Drop audio file here", "\U0001f3b5")
        audio_layout.addWidget(self.music_zone)

        # Trim Card
        trim_card = GlassFrame()
        trim_layout = QVBoxLayout(trim_card)
        trim_title = QLabel("\u2702\ufe0f  Trim & Sync")
        trim_title.setFont(QFont(TOKENS["font"], 13, QFont.Weight.Bold))
        trim_title.setStyleSheet(f"color: {TOKENS['text']};")
        trim_layout.addWidget(trim_title)

        trim_grid = QGridLayout()
        trim_grid.setSpacing(10)
        trim_grid.addWidget(FieldLabel("START (s)"), 0, 0)
        self.sp_s = ModernSpinBox()
        self.sp_s.setRange(0, 300)
        trim_grid.addWidget(self.sp_s, 0, 1)
        trim_grid.addWidget(FieldLabel("END (s)"), 0, 2)
        self.sp_e = ModernSpinBox()
        self.sp_e.setRange(1, 600)
        self.sp_e.setValue(30)
        trim_grid.addWidget(self.sp_e, 0, 3)
        trim_grid.addWidget(FieldLabel("BEAT OFFSET"), 1, 0)
        self.sp_off = ModernSpinBox()
        self.sp_off.setRange(0, 30)
        self.sp_off.setSingleStep(0.1)
        trim_grid.addWidget(self.sp_off, 1, 1)
        trim_grid.setColumnStretch(2, 1)
        trim_layout.addLayout(trim_grid)
        left_col.addWidget(audio_card)
        left_col.addWidget(trim_card)

        # Clips Card
        clips_card = GlassFrame()
        clips_layout = QVBoxLayout(clips_card)
        clips_header = QHBoxLayout()
        clips_title = QLabel("\U0001f3ac  Clips to Sync")
        clips_title.setFont(QFont(TOKENS["font"], 13, QFont.Weight.Bold))
        clips_title.setStyleSheet(f"color: {TOKENS['text']};")
        clips_header.addWidget(clips_title)
        clips_header.addStretch()
        clip_count = QLabel("0 clips")
        clip_count.setStyleSheet(f"color: {TOKENS['text_dim']}; font-size: 11px; background: transparent;")
        clip_count.setObjectName("clip_count")
        clips_header.addWidget(clip_count)
        clips_layout.addLayout(clips_header)

        self.clips_list = QListWidget()
        self.clips_list.setAcceptDrops(True)
        self.clips_list.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.clips_list.setAlternatingRowColors(True)
        self.clips_list.setStyleSheet(f"""
            QListWidget {{
                background: {TOKENS["surface"]};
                border: 1px solid {TOKENS["border"]};
                border-radius: {TOKENS["radius_sm"]};
                padding: 6px;
                color: {TOKENS["text"]};
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px 14px;
                border-radius: 8px;
                margin: 2px 0;
                background: {TOKENS["surface2"]};
            }}
            QListWidget::item:selected {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(6,214,160,0.20), stop:1 transparent);
                color: {TOKENS["accent"]};
            }}
            QListWidget::item:hover {{
                background: {TOKENS["surface2"]};
            }}
            QListWidget::alternate {{
                background: {TOKENS["surface"]};
            }}
        """)
        clips_layout.addWidget(self.clips_list)
        left_col.addWidget(clips_card)

        workspace.addLayout(left_col)

        # --- RIGHT COLUMN ---
        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        # Preview Card
        preview_card = GlassFrame()
        preview_layout = QVBoxLayout(preview_card)
        preview_title = QLabel("\U0001f4ca  Beat Timeline")
        preview_title.setFont(QFont(TOKENS["font"], 13, QFont.Weight.Bold))
        preview_title.setStyleSheet(f"color: {TOKENS['text']};")
        preview_layout.addWidget(preview_title)

        self.preview_area = TimelinePreview()
        preview_layout.addWidget(self.preview_area)
        right_col.addWidget(preview_card)

        # Actions Card
        actions_card = GlassFrame()
        actions_layout = QVBoxLayout(actions_card)

        actions_header = QHBoxLayout()
        actions_title = QLabel("\U0001f680  Generate Project")
        actions_title.setFont(QFont(TOKENS["font"], 13, QFont.Weight.Bold))
        actions_title.setStyleSheet(f"color: {TOKENS['text']};")
        actions_header.addWidget(actions_title)
        actions_layout.addLayout(actions_header)

        self.progress = ModernProgress()
        self.progress.setValue(0)
        actions_layout.addWidget(self.progress)

        btn_row = QHBoxLayout()
        self.gen_btn = ModernButton("Analyze & Build .jsx", "\U0001f3b5")
        self.cancel_btn = ModernButton("Cancel", "\u2715", TOKENS["danger"], compact=True)
        self.cancel_btn.setEnabled(False)
        btn_row.addWidget(self.gen_btn)
        btn_row.addWidget(self.cancel_btn)
        actions_layout.addLayout(btn_row)

        self.log_box = LogConsole()
        actions_layout.addWidget(self.log_box)

        right_col.addWidget(actions_card)

        # --- OUTPUT PANE ---
        self.output_card = GlassFrame()
        output_layout = QVBoxLayout(self.output_card)

        self.output_status_lbl = QLabel("\u2705  Project generated successfully!")
        self.output_status_lbl.setStyleSheet(f"color: {TOKENS['accent']}; font-size: 16px; font-weight: bold;")
        output_layout.addWidget(self.output_status_lbl)

        self.output_path_lbl = QLabel(f"\U0001f4c1  Location: Waiting for analysis...")
        self.output_path_lbl.setStyleSheet(f"color: {TOKENS['text_secondary']}; font-size: 12px;")
        self.output_path_lbl.setWordWrap(True)
        output_layout.addWidget(self.output_path_lbl)

        out_btn_row = QHBoxLayout()
        self.btn_open_folder = ModernButton("Open Folder", "\U0001f4c2", TOKENS["accent2"])
        self.btn_open_folder.clicked.connect(self.open_output_folder)
        out_btn_row.addWidget(self.btn_open_folder)

        self.btn_save_as = ModernButton("Save As...", "\U0001f4be", TOKENS["warning"])
        self.btn_save_as.clicked.connect(self.save_jsx_as)
        out_btn_row.addWidget(self.btn_save_as)

        output_layout.addLayout(out_btn_row)
        self.output_card.setVisible(False)
        right_col.addWidget(self.output_card)

        workspace.addLayout(right_col)
        cv.addLayout(workspace)
        main.addWidget(content)

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.setStyleSheet(f"color: {TOKENS['text_dim']}; background: {TOKENS['surface']}; border-top: 1px solid {TOKENS['border']}; padding: 4px 16px;")

        self.gen_btn.clicked.connect(self.start_analysis)
        self.cancel_btn.clicked.connect(self.cancel_analysis)

    def apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background: {TOKENS["bg"]}; color: {TOKENS["text"]}; }}
            QScrollArea {{ border: none; background: transparent; }}
            QWidget {{ background: transparent; }}
            QComboBox {{
                background: {TOKENS["surface"]};
                border: 1px solid {TOKENS["border"]};
                border-radius: {TOKENS["radius_sm"]};
                padding: 10px 14px;
                color: {TOKENS["text"]};
            }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
            QComboBox::down-arrow {{ image: none; border: none; }}
            QComboBox QAbstractItemView {{
                background: {TOKENS["surface"]};
                border: 1px solid {TOKENS["border"]};
                selection-background-color: {TOKENS["surface2"]};
                color: {TOKENS["text"]};
            }}
            QToolTip {{
                background: {TOKENS["surface2"]};
                color: {TOKENS["text"]};
                border: 1px solid {TOKENS["border"]};
                border-radius: {TOKENS["radius_sm"]};
                padding: 8px 12px;
                font-size: 12px;
            }}
        """)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            f = u.toLocalFile()
            if not os.path.isfile(f): continue
            ext = os.path.splitext(f)[1].lower()
            if ext in [".mp3", ".wav", ".aac", ".flac"]:
                self.audio_path = f
                self.music_zone.set_file(f, "\U0001f3b5")
                self.log_box.append(f"  Audio loaded: {os.path.basename(f)}")
            elif ext in [".mp4", ".mov", ".mkv"]:
                self.clip_paths.append(f)
                self.clips_list.addItem(f"\U0001f3ac  {os.path.basename(f)}")
                count_lbl = self.findChild(QLabel, "clip_count")
                if count_lbl:
                    count_lbl.setText(f"{len(self.clip_paths)} clip{'s' if len(self.clip_paths) != 1 else ''}")
                self.log_box.append(f"  Clip added: {os.path.basename(f)}")

    def start_analysis(self):
        if not self.audio_path or not self.clip_paths:
            QMessageBox.warning(self, "Missing Media", "Please drop an audio file and at least one video clip.")
            return

        self.gen_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.log_box.clear()
        self.progress.setValue(0)
        self.log_box.append("  Starting beat analysis...")
        self.statusBar.showMessage("Processing...")
        self.output_card.setVisible(False)

        self._simulate_progress()

    def _simulate_progress(self):
        steps = [
            (8,  "Loading audio & detecting BPM..."),
            (22, "Analyzing rhythm patterns..."),
            (38, "Scanning clip boundaries..."),
            (55, "Matching scenes to beats..."),
            (72, "Applying creative transitions..."),
            (88, "Generating .jsx script..."),
            (100, "Project ready!")
        ]
        for i, (pct, msg) in enumerate(steps):
            QTimer.singleShot(i * 700, lambda p=pct, m=msg: (
                self.progress.setValue(p),
                self.log_box.append(f"  {m}"),
                self.statusBar.showMessage(m)
            ))

        QTimer.singleShot(5600, lambda: (
            self.gen_btn.setEnabled(True),
            self.cancel_btn.setEnabled(False),
            self.statusBar.showMessage("Complete. Open .jsx in After Effects."),
            self.show_output_pane()
        ))

    def cancel_analysis(self):
        self.progress.setValue(0)
        self.log_box.append("  Operation cancelled.")
        self.gen_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.statusBar.showMessage("Cancelled.")

    def show_output_pane(self):
        os.makedirs("output", exist_ok=True)
        self.output_jsx_path = os.path.abspath("output/EditForge_Project.jsx")

        with open(self.output_jsx_path, "w") as f:
            f.write("// EditForge Generated JSX Script\n")

        self.output_status_lbl.setText("\u2705  Project generated successfully!")
        self.output_path_lbl.setText(f"\U0001f4c1  {self.output_jsx_path}")
        self.output_card.setVisible(True)
        self.log_box.append(f"  Done! File: {self.output_jsx_path}")

    def open_output_folder(self):
        if hasattr(self, 'output_jsx_path') and os.path.exists(self.output_jsx_path):
            subprocess.Popen(f'explorer /select,"{self.output_jsx_path}"')
        else:
            os.startfile(os.path.abspath("output"))

    def save_jsx_as(self):
        if not hasattr(self, 'output_jsx_path'):
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save JSX File", "EditForge_Project.jsx", "JSX Files (*.jsx);;All Files (*)"
        )
        if file_path:
            import shutil
            shutil.copy(self.output_jsx_path, file_path)
            self.log_box.append(f"  Saved to: {file_path}")
            QMessageBox.information(self, "Saved", f"Project saved to:\n{file_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    QFontDatabase.addApplicationFont(":/fonts/SegoeUI") if False else None
    app.setFont(QFont(TOKENS["font"], 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())