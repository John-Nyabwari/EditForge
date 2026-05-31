import sys
import os
import json
import traceback
import numpy as np
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QListWidget, QSlider, QComboBox, QLineEdit, 
    QProgressBar, QGroupBox, QFileDialog, QMessageBox, QStatusBar,
    QSizePolicy, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QColor, QPixmap, QPainter, QFont

# ==================== CORE ANALYSIS & EXPORT ====================
class AnalysisEngine(QObject):
    progress = pyqtSignal(int, str)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    cancel_flag = False

    def set_cancel(self):
        self.cancel_flag = True

    def check_dependencies(self):
        self.progress.emit(5, "🔍 Checking system...")
        deps = {"ffmpeg": False, "librosa": False, "pyscenedetect": False, "opencv": False, "demucs": False}
        try:
            import librosa; deps["librosa"] = True
        except ImportError: pass
        try:
            import pyscenedetect; deps["pyscenedetect"] = True
        except ImportError: pass
        try:
            import cv2; deps["opencv"] = True
        except ImportError: pass
        try:
            import subprocess
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=False)
            deps["ffmpeg"] = result.returncode == 0
        except Exception: pass
        try:
            import demucs; deps["demucs"] = True
        except ImportError: pass
        return deps

    def get_video_props(self, path):
        import cv2
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return {"w": 1920, "h": 1080, "fps": 30.0}
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.release()
        return {"w": w, "h": h, "fps": fps}

    def analyze_audio(self, path):
        import librosa
        self.status.emit("🎵 Loading audio...")
        y, sr = librosa.load(path, sr=None, mono=True)
        self.status.emit("🥁 Detecting beats & BPM...")
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr, trim=False)
        beat_times = librosa.frames_to_time(beats, sr=sr)
        return {"bpm": round(tempo, 2), "beats": beat_times.tolist()}

    def analyze_scenes(self, clip_paths):
        from pyscenedetect import SceneManager, ContentDetector, open_video
        all_scenes = []
        for i, path in enumerate(clip_paths):
            if self.cancel_flag: return []
            self.progress.emit(40 + i * (40/max(1, len(clip_paths))), f"🎬 Scanning scenes: {Path(path).name}")
            try:
                video = open_video(path)
                sm = SceneManager()
                sm.add_detector(ContentDetector(threshold=27.0))
                sm.detect_scenes(video, show_progress=False)
                scenes = [s[0].get_frames() for s in sm.get_scene_list()]
                all_scenes.extend(scenes)
            except Exception as e:
                self.error.emit(f"Scene detect failed on {Path(path).name}: {e}")
        return all_scenes

    def generate_jsx(self, audio_path, clip_paths, beat_times, props, output_dir):
        comp_w, comp_h, fps = props["w"], props["h"], props["fps"]
        jsx_path = os.path.join(output_dir, "EditForge_Project.jsx")
        
        # Build valid JSX string
        jsx = f"""// EditForge Auto-Generated Script
app.beginUndoGroup("EditForge Build");

// Main Comp
var mainComp = app.project.items.addComp("EditForge_MAIN", {comp_w}, {comp_h}, 1.0, {len(beat_times) * (60/props.get("bpm", 30))}, {fps});
mainComp.openInViewer();

// Audio Layer
var audioFile = new File("{audio_path.replace(chr(92), "/")}");
mainComp.layers.add(audioFile);

// Beat Markers
var markerProp = new MarkerValue("EditForge Beat Sync");
for (var i=0; i<{len(beat_times)}; i++) {{
    mainComp.layer("Audio").property("Marker").setValueAtTime({beat_times[i]}, markerProp);
}}

// Clip Sub-Comps & Placeholders
"""
        for i, clip in enumerate(clip_paths):
            jsx += f"""
var clipComp = app.project.items.addComp("CLIP_{i+1:02d}", {comp_w}, {comp_h}, 1.0, 5.0, {fps});
var solid = clipComp.layers.addSolid([1.0, 0.4, 0.2], "Mask_Placeholder_{i+1:02d}", {comp_w}, {comp_h}, 1.0);
solid.opacity = 50;
mainComp.layers.add(clipComp);
"""
        jsx += "\napp.endUndoGroup();\n"
        
        with open(jsx_path, "w", encoding="utf-8") as f:
            f.write(jsx)
        return jsx_path

    def run(self, audio_path, clip_paths, output_dir, project_fps):
        try:
            self.progress.emit(0, "Initializing...")
            deps = self.check_dependencies()
            missing = [k for k, v in deps.items() if not v]
            if missing:
                self.error.emit(f"Missing dependencies: {', '.join(missing)}. Install via: pip install -r requirements.txt")
                return

            if not audio_path or not os.path.exists(audio_path):
                self.error.emit("No audio file provided.")
                return
            if not clip_paths:
                self.error.emit("No clips uploaded.")
                return

            # 1. Video Props
            props = self.get_video_props(clip_paths[0])
            props["fps"] = float(project_fps)
            self.progress.emit(20, f"📐 Comp size locked: {props['w']}x{props['h']} @ {props['fps']}fps")

            # 2. Audio
            if self.cancel_flag: return
            audio_data = self.analyze_audio(audio_path)
            self.progress.emit(40, f"🎵 BPM: {audio_data['bpm']} | Beats found: {len(audio_data['beats'])}")

            # 3. Scenes
            if self.cancel_flag: return
            scenes = self.analyze_scenes(clip_paths)
            self.progress.emit(85, f"🎬 Scene boundaries mapped: {len(scenes)} cuts")

            # 4. Export JSX
            if self.cancel_flag: return
            os.makedirs(output_dir, exist_ok=True)
            jsx_path = self.generate_jsx(audio_path, clip_paths, audio_data["beats"], props, output_dir)
            
            self.progress.emit(100, "✅ Generation complete!")
            self.finished.emit({
                "jsx_path": jsx_path,
                "bpm": audio_data["bpm"],
                "beats": len(audio_data["beats"]),
                "scenes": len(scenes),
                "comp_size": f"{props['w']}x{props['h']}"
            })
        except Exception as e:
            self.error.emit(f"Fatal Error: {str(e)}\n{traceback.format_exc()}")

# ==================== WORKER THREAD ====================
class AnalysisThread(QThread):
    progress = pyqtSignal(int, str)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, audio, clips, out_dir, fps):
        super().__init__()
        self.audio = audio
        self.clips = clips
        self.out_dir = out_dir
        self.fps = fps
        self.engine = AnalysisEngine()

    def run(self):
        self.engine.progress.connect(self.progress)
        self.engine.status.connect(self.status)
        self.engine.finished.connect(self.finished)
        self.engine.error.connect(self.error)
        self.engine.run(self.audio, self.clips, self.out_dir, self.fps)

    def cancel(self):
        self.engine.set_cancel()

# ==================== MAIN UI ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EditForge v2.1")
        self.resize(1150, 750)
        self.setAcceptDrops(True)
        self.setup_ui()
        self.apply_dark_theme()
        self.audio_path = None
        self.clip_paths = []
        self.worker = None

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # LEFT: Media & Timeline
        left = QVBoxLayout()
        self.music_label = QLabel("Drag & Drop MP3/WAV/AAC here")
        self.music_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.music_label.setStyleSheet("padding: 25px; border: 2px dashed #444; border-radius: 10px;")
        left.addWidget(self.music_label)

        self.music_slider = QSlider(Qt.Orientation.Horizontal)
        self.music_slider.setRange(0, 100)
        left.addWidget(QLabel("⏱️ Edit Region & Beat Offset"))
        left.addWidget(self.music_slider)

        clips_box = QGroupBox("🎬 Clips to Sync")
        self.clips_list = QListWidget()
        self.clips_list.setAcceptDrops(True)
        self.clips_list.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.clips_list.setStyleSheet("background: #1e1e1e; color: white; border-radius: 8px; padding: 10px;")
        clips_box.setLayout(QVBoxLayout(clips_box))
        clips_box.layout().addWidget(self.clips_list)
        left.addWidget(clips_box)

        # RIGHT: Controls & Status
        right = QVBoxLayout()
        settings = QGroupBox("⚙️ Settings")
        self.proj_name = QLineEdit("EditForge_Project")
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["24", "30", "60"])
        self.presets_btn = QPushButton("📁 Upload Masks/Presets")
        settings_layout = QVBoxLayout(settings)
        settings_layout.addWidget(QLabel("Project Name"))
        settings_layout.addWidget(self.proj_name)
        settings_layout.addWidget(QLabel("Frame Rate"))
        settings_layout.addWidget(self.fps_combo)
        settings_layout.addWidget(self.presets_btn)
        settings_layout.addWidget(QLabel("⚠️ Comp size auto-matches first clip"))
        right.addWidget(settings)

        status_box = QGroupBox("🤖 System Status")
        self.sys_status = QLabel("🔍 Checking dependencies...")
        self.sys_status.setStyleSheet("color: #ffd166; font-weight: bold;")
        self.ai_status = QLabel("Creative Engine: ⏸️ Idle")
        status_box_layout = QVBoxLayout(status_box)
        status_box_layout.addWidget(self.sys_status)
        status_box_layout.addWidget(self.ai_status)
        right.addWidget(status_box)

        actions = QGroupBox("🚀 Export")
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(120)
        self.log_box.setStyleSheet("background: #0f0f0f; color: #aaffaa; font-family: monospace;")

        self.generate_btn = QPushButton("⚡ Analyze & Build .jsx")
        self.generate_btn.setStyleSheet("background: #06d6a0; color: black; font-weight: bold; padding: 14px; border-radius: 8px;")
        self.cancel_btn = QPushButton("⛔ Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("background: #ef476f; color: white; padding: 14px; border-radius: 8px;")
        
        actions_layout = QVBoxLayout(actions)
        actions_layout.addWidget(self.log_box)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.generate_btn)
        btn_row.addWidget(self.cancel_btn)
        actions_layout.addLayout(btn_row)
        right.addWidget(actions)

        self.progress = QProgressBar()
        right.addWidget(self.progress)

        layout.addLayout(left, 1)
        layout.addLayout(right, 1)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        self.generate_btn.clicked.connect(self.start_analysis)
        self.cancel_btn.clicked.connect(self.cancel_analysis)
        self.presets_btn.clicked.connect(self.upload_presets)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background: #121212; color: #ffffff; }
            QGroupBox { border: 1px solid #333; border-radius: 10px; margin-top: 8px; font-weight: bold; padding-top: 15px; }
            QLineEdit, QComboBox, QPushButton, QTextEdit { background: #1e1e1e; border: 1px solid #444; padding: 8px; border-radius: 6px; color: white; }
            QSlider::groove:horizontal { background: #333; height: 8px; border-radius: 4px; }
            QSlider::handle:horizontal { background: #06d6a0; width: 16px; margin: -4px 0; border-radius: 8px; }
            QProgressBar { border: 1px solid #444; border-radius: 6px; background: #1e1e1e; height: 22px; text-align: center; }
            QProgressBar::chunk { background: #06d6a0; border-radius: 5px; }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            f = url.toLocalFile()
            if not os.path.isfile(f): continue
            ext = os.path.splitext(f)[1].lower()
            if ext in [".mp3", ".wav", ".aac", ".flac"]:
                self.audio_path = f
                self.music_label.setText(f"🎵 {os.path.basename(f)}")
            elif ext in [".mp4", ".mov", ".mkv"]:
                self.clip_paths.append(f)
                self.clips_list.addItem(f"🎬 {os.path.basename(f)}")
            self.log_box.append(f"📂 Added: {os.path.basename(f)}")

    def upload_presets(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Upload Masks/Presets", "", "PNG (*.png);;JSON (*.json)")
        for f in files: self.log_box.append(f"🎨 Preset/Mask: {os.path.basename(f)}")

    def start_analysis(self):
        if not self.audio_path:
            QMessageBox.warning(self, "Missing Audio", "Drop an MP3/WAV first.")
            return
        if not self.clip_paths:
            QMessageBox.warning(self, "Missing Clips", "Drop at least one video clip.")
            return

        self.generate_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.log_box.clear()
        self.progress.setValue(0)
        self.ai_status.setText("Creative Engine: 🟡 Processing...")

        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        self.worker = AnalysisThread(self.audio_path, self.clip_paths, out_dir, self.fps_combo.currentText())
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def update_progress(self, val, msg):
        self.progress.setValue(val)
        self.log_box.append(msg)
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def update_status(self, msg):
        self.sys_status.setText(msg)

    def on_finished(self, data):
        self.progress.setValue(100)
        self.ai_status.setText(f"✅ Done | BPM: {data['bpm']} | Comp: {data['comp_size']} | Beats: {data['beats']}")
        self.log_box.append(f"📄 .jsx saved to: {data['jsx_path']}")
        self.statusBar.showMessage(f"✅ Project ready. Open .jsx in After Effects.")
        self.generate_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def on_error(self, msg):
        self.progress.setValue(0)
        self.log_box.append(f"❌ {msg}")
        self.ai_status.setText("Creative Engine: 🔴 Failed")
        self.statusBar.showMessage("❌ Check log for errors.")
        self.generate_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def cancel_analysis(self):
        if self.worker: self.worker.cancel()
        self.log_box.append("⛔ Cancelled by user.")
        self.ai_status.setText("Creative Engine: 🔴 Stopped")
        self.progress.setValue(0)
        self.cancel_btn.setEnabled(False)
        self.generate_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())