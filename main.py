import sys
import os
import json
import subprocess
import math
import traceback
import numpy as np
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QListWidget, QSlider, QComboBox, QLineEdit, 
    QProgressBar, QGroupBox, QFileDialog, QMessageBox, QStatusBar,
    QSizePolicy, QTextEdit, QDoubleSpinBox, QSplitter, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer, QRectF, QPointF
from PyQt6.QtGui import QColor, QBrush, QPen, QPainter, QFont, QMouseEvent

# ==================== CUSTOM BEAT TIMELINE WIDGET ====================
class BeatTimeline(QWidget):
    beatClicked = pyqtSignal(float)
    
    def __init__(self):
        super().__init__()
        self.beats = []
        self.duration = 0
        self.offset = 0.0
        self.setFixedHeight(80)
        self.setStyleSheet("background: #181818; border-radius: 6px;")

    def set_data(self, beats, duration):
        self.beats = beats
        self.duration = duration
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.duration: return
        
        w, h = self.width(), self.height()
        margin = 10
        draw_w = w - 2 * margin
        
        # Draw base line
        painter.setPen(QPen(QColor("#444"), 2))
        painter.drawLine(margin, h//2, w-margin, h//2)
        
        # Draw beats
        for b in self.beats:
            x = margin + (b / self.duration) * draw_w
            if self.offset > 0 and b >= self.offset:
                painter.setPen(QPen(QColor("#06d6a0"), 3))
            else:
                painter.setPen(QPen(QColor("#888"), 1))
            painter.drawLine(int(x), h//2 - 15, int(x), h//2 + 15)

    def mousePressEvent(self, event: QMouseEvent):
        if not self.duration: return
        w = self.width()
        margin = 10
        draw_w = w - 2 * margin
        x = event.position().x()
        t = ((x - margin) / draw_w) * self.duration
        self.offset = max(0, min(t, self.duration))
        self.beatClicked.emit(self.offset)
        self.update()

# ==================== CORE ANALYSIS & EXPORT ENGINE ====================
class AnalysisEngine(QObject):
    progress = pyqtSignal(int, str)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    cancel_flag = False

    def set_cancel(self): self.cancel_flag = True

    def check_deps(self):
        deps = {"ffmpeg": False, "librosa": False, "pyscenedetect": False, "opencv": False, "demucs": False, "mutagen": False}
        try: import librosa; deps["librosa"] = True
        except ImportError: pass
        try: import pyscenedetect; deps["pyscenedetect"] = True
        except ImportError: pass
        try: import cv2; deps["opencv"] = True
        except ImportError: pass
        try: import mutagen; deps["mutagen"] = True
        except ImportError: pass
        try:
            res = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            deps["ffmpeg"] = res.returncode == 0
        except: pass
        try:
            res = subprocess.run(["demucs", "--version"], capture_output=True, text=True)
            deps["demucs"] = res.returncode == 0
        except: pass
        return deps

    def get_audio_duration(self, path):
        import mutagen
        meta = mutagen.File(path)
        return meta.info.length if meta else 30.0

    def get_video_props(self, path):
        import cv2
        cap = cv2.VideoCapture(path)
        if not cap.isOpened(): return {"w": 1920, "h": 1080, "fps": 30.0}
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.release()
        return {"w": w, "h": h, "fps": fps}

    def extract_vocals(self, audio_path, output_dir):
        if not self._check_demucs():
            return None, "demucs not found. Install via: pip install demucs"
        self.progress.emit(10, "🎤 Downloading/Loading demucs model (htdemucs)...")
        cmd = ["demucs", "--mp3", "-n", "htdemucs", "--two-stems=vocals", "-o", output_dir, audio_path]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore")
            while True:
                if self.cancel_flag: proc.kill(); return None, "Cancelled"
                line = proc.stdout.readline()
                if not line and proc.poll() is not None: break
                if "[" in line and "/" in line:
                    self.progress.emit(int(line.split("[")[1].split("%")[0]), "🎤 Extracting stems...")
            proc.wait()
            vocal_path = os.path.join(output_dir, "htdemucs", Path(audio_path).stem, "vocals.mp3")
            if os.path.exists(vocal_path):
                self.progress.emit(100, "✅ Vocals extracted successfully")
                return vocal_path, None
            return None, "Vocal extraction completed but file missing."
        except Exception as e:
            return None, f"demucs failed: {e}"

    def _check_demucs(self):
        try: return subprocess.run(["demucs", "--version"], capture_output=True, text=True).returncode == 0
        except: return False

    def run_analysis(self, audio_path, clip_paths, start_t, end_t, beat_offset, project_fps, output_dir):
        try:
            self.progress.emit(0, "🔍 Initializing...")
            deps = self.check_deps()
            missing = [k for k, v in deps.items() if not v and k in ["librosa", "pyscenedetect", "opencv", "ffmpeg"]]
            if missing:
                self.error.emit(f"Missing core deps: {', '.join(missing)}. Run: pip install -r requirements.txt")
                return

            if self.cancel_flag: return
            props = self.get_video_props(clip_paths[0])
            props["fps"] = float(project_fps)
            self.progress.emit(10, f"📐 Comp: {props['w']}x{props['h']} @ {props['fps']}fps")

            if self.cancel_flag: return
            import librosa
            self.progress.emit(20, "🎵 Loading audio & detecting beats...")
            y, sr = librosa.load(audio_path, sr=None, mono=True)
            total_dur = len(y)/sr
            start_sec = max(0, start_t)
            end_sec = min(total_dur, end_t)
            if end_sec <= start_sec:
                self.error.emit("End time must be after start time.")
                return
            idx_start = int(start_sec * sr)
            idx_end = int(end_sec * sr)
            y_clip = y[idx_start:idx_end]
            dur_clip = len(y_clip)/sr
            _, beats = librosa.beat.beat_track(y=y_clip, sr=sr, trim=False)
            beat_times = librosa.frames_to_time(beats, sr=sr) + start_sec
            beat_times = [b for b in beat_times if start_sec <= b <= end_sec]
            self.progress.emit(40, f"🥁 {len(beat_times)} beats in region [{start_sec:.1f}s - {end_sec:.1f}s]")

            if self.cancel_flag: return
            from pyscenedetect import SceneManager, ContentDetector, open_video
            self.progress.emit(50, "🎬 Detecting scene cuts...")
            all_scenes = []
            for i, path in enumerate(clip_paths):
                if self.cancel_flag: return
                self.progress.emit(50 + i*(20/len(clip_paths)), f"Scanning {Path(path).name}...")
                video = open_video(path)
                sm = SceneManager()
                sm.add_detector(ContentDetector(threshold=27.0))
                sm.detect_scenes(video, show_progress=False)
                scenes = [s[0].get_frames() for s in sm.get_scene_list()]
                all_scenes.extend(scenes)
            self.progress.emit(80, f"📐 {len(all_scenes)} scene boundaries mapped")

            if self.cancel_flag: return
            os.makedirs(output_dir, exist_ok=True)
            jsx_path = os.path.join(output_dir, "EditForge_Phase3.jsx")
            self._generate_jsx(jsx_path, audio_path, clip_paths, beat_times, beat_offset, props)
            
            self.progress.emit(100, "✅ Generation complete!")
            self.finished.emit({
                "jsx_path": jsx_path,
                "beats": len(beat_times),
                "scenes": len(all_scenes),
                "comp_size": f"{props['w']}x{props['h']}"
            })
        except Exception as e:
            self.error.emit(f"Fatal Error: {str(e)}\n{traceback.format_exc()}")

    def _generate_jsx(self, path, audio, clips, beats, offset, props):
        w, h, fps = props["w"], props["h"], props["fps"]
        comp_dur = (beats[-1] - beats[0]) + 2.0 if beats else 10.0
        jsx = f"""// EditForge v3.0 Auto-Generated
app.beginUndoGroup("EditForge Build");
var main = app.project.items.addComp("EditForge_MAIN", {w}, {h}, 1.0, {comp_dur}, {fps});
main.openInViewer();

// Audio
var aud = main.layers.add(new File("{audio.replace(chr(92), "/")}"));
aud.property("Marker").setValueAtTime({offset}, new MarkerValue("Beat Start Offset"));

// Masks Comp
var masks = app.project.items.addComp("MASKS_REF", {w}, {h}, 1.0, {comp_dur}, {fps});
for(var m=1; m<={len(clips)}; m++) {{
    masks.layers.addSolid([0.5, 0.8, 0.5], "Mask_"+m, {w}, {h}, 1.0);
    masks.layer(m).trackMatteType = TrackMatteType.ALPHA;
}}

// Clip Subcomps with Beat Sync
var beatArr = [{','.join(f'{b:.3f}' for b in beats)}];
"""
        for i, clip in enumerate(clips):
            jsx += f"""
var c = app.project.items.addComp("CLIP_{i+1:02d}", {w}, {h}, 1.0, {comp_dur}, {fps});
var solid = c.layers.addSolid([0.2, 0.2, 0.3], "Footage_Placeholder", {w}, {h}, 1.0);
solid.opacity = 60;

// Mask Layer
var mk = c.layers.add(masks.layer({i+1}));
mk.position.setValue([0,0]);

// Beat-driven scale expression
var s = solid.property("Scale");
s.setValueAtTime(0, [100,100]);
for(var k=0; k<beatArr.length; k++) {{
    s.setValueAtTime(beatArr[k], [108,108]);
    s.setValueAtTime(beatArr[k]+0.15, [100,100]);
}}

// Sync to main
main.layers.add(c);
c.startTime = {offset};
"""
        jsx += "\napp.endUndoGroup();\n"
        with open(path, "w", encoding="utf-8") as f: f.write(jsx)

# ==================== THREADING ====================
class AnalysisThread(QThread):
    progress = pyqtSignal(int, str)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    def __init__(self, audio, clips, start, end, offset, fps, out):
        super().__init__()
        self.args = (audio, clips, start, end, offset, fps, out)
        self.engine = AnalysisEngine()
    def run(self):
        self.engine.progress.connect(self.progress)
        self.engine.status.connect(self.status)
        self.engine.finished.connect(self.finished)
        self.engine.error.connect(self.error)
        self.engine.run_analysis(*self.args)
    def cancel(self): self.engine.set_cancel()

# ==================== MAIN UI ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EditForge v3.0 Desktop")
        self.resize(1250, 800)
        self.setAcceptDrops(True)
        self.setup_ui()
        self.apply_theme()
        self.audio_path = None
        self.clip_paths = []
        self.worker = None
        self.vocal_worker = None

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # LEFT
        left = QWidget()
        lv = QVBoxLayout(left)
        self.music_lbl = QLabel("Drag & Drop Audio (MP3/WAV)")
        self.music_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.music_lbl.setStyleSheet("padding: 20px; border: 2px dashed #555; border-radius: 8px;")
        lv.addWidget(self.music_lbl)
        
        # Trim Controls
        trim_box = QGroupBox("✂️ Trim & Offset")
        tv = QVBoxLayout(trim_box)
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Start (s)"))
        self.start_sp = QDoubleSpinBox(); self.start_sp.setRange(0, 300); self.start_sp.setValue(0)
        h1.addWidget(self.start_sp)
        h1.addWidget(QLabel("End (s)"))
        self.end_sp = QDoubleSpinBox(); self.end_sp.setRange(1, 600); self.end_sp.setValue(30)
        h1.addWidget(self.end_sp)
        tv.addLayout(h1)
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Beat Offset (s)"))
        self.offset_sp = QDoubleSpinBox(); self.offset_sp.setRange(0, 30); self.offset_sp.setSingleStep(0.1)
        h2.addWidget(self.offset_sp)
        tv.addLayout(h2)
        lv.addWidget(trim_box)
        
        # Timeline
        self.timeline = BeatTimeline()
        self.timeline.beatClicked.connect(lambda t: self.offset_sp.setValue(t))
        lv.addWidget(self.timeline)
        
        # Clips
        clips_box = QGroupBox("🎬 Clips")
        self.clips_list = QListWidget()
        self.clips_list.setAcceptDrops(True)
        self.clips_list.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.clips_list.setStyleSheet("background: #1a1a1a; color: #eee; border-radius: 6px;")
        clips_box.setLayout(QVBoxLayout())
        clips_box.layout().addWidget(self.clips_list)
        lv.addWidget(clips_box)
        
        splitter.addWidget(left)
        
        # RIGHT
        right = QWidget()
        rv = QVBoxLayout(right)
        
        # Vocal Extraction
        voc_box = QGroupBox("🎤 Vocal Extractor")
        vv = QVBoxLayout(voc_box)
        self.voc_btn = QPushButton("Extract Vocals (demucs)")
        self.voc_btn.setEnabled(False)
        vv.addWidget(self.voc_btn)
        self.voc_status = QLabel("Status: Idle")
        vv.addWidget(self.voc_status)
        rv.addWidget(voc_box)
        
        # Settings
        set_box = QGroupBox("⚙️ Settings")
        sv = QVBoxLayout(set_box)
        self.fps_cb = QComboBox(); self.fps_cb.addItems(["24", "30", "60"])
        sv.addWidget(QLabel("FPS")); sv.addWidget(self.fps_cb)
        sv.addWidget(QLabel("Comp size auto-matches first clip"))
        sv.addWidget(QLabel("Upload personal masks/presets for mask layer"))
        rv.addWidget(set_box)
        
        # System & Log
        sys_box = QGroupBox("🤖 System")
        self.sys_lbl = QLabel("Checking deps...")
        sys_box.setLayout(QVBoxLayout()); sys_box.layout().addWidget(self.sys_lbl)
        rv.addWidget(sys_box)
        
        log_box = QGroupBox("📜 Log")
        self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(150)
        self.log.setStyleSheet("background: #0f0f0f; color: #aaffaa; font-family: monospace;")
        log_box.setLayout(QVBoxLayout()); log_box.layout().addWidget(self.log)
        rv.addWidget(log_box)
        
        # Actions
        act_box = QGroupBox("🚀 Export")
        av = QVBoxLayout(act_box)
        self.gen_btn = QPushButton("⚡ Analyze & Build .jsx")
        self.gen_btn.setStyleSheet("background: #06d6a0; color: black; font-weight: bold; padding: 12px; border-radius: 6px;")
        self.cancel_btn = QPushButton("⛔ Cancel"); self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("background: #ef476f; color: white; padding: 12px; border-radius: 6px;")
        ah = QHBoxLayout(); ah.addWidget(self.gen_btn); ah.addWidget(self.cancel_btn)
        av.addLayout(ah)
        self.progress = QProgressBar()
        av.addWidget(self.progress)
        rv.addWidget(act_box)
        
        splitter.addWidget(right)
        main.addWidget(splitter)
        
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        self.gen_btn.clicked.connect(self.start_analysis)
        self.cancel_btn.clicked.connect(self.cancel_analysis)
        self.voc_btn.clicked.connect(self.start_vocal)

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background: #111; color: #fff; }
            QGroupBox { border: 1px solid #333; border-radius: 8px; margin-top: 6px; font-weight: bold; padding-top: 12px; }
            QLineEdit, QComboBox, QPushButton, QDoubleSpinBox, QTextEdit, QListWidget { background: #1e1e1e; border: 1px solid #444; padding: 8px; border-radius: 6px; color: #eee; }
            QSlider::groove:horizontal { background: #333; height: 8px; border-radius: 4px; }
            QSlider::handle:horizontal { background: #06d6a0; width: 16px; margin: -4px 0; border-radius: 8px; }
            QProgressBar { border: 1px solid #444; border-radius: 6px; background: #1e1e1e; height: 20px; text-align: center; }
            QProgressBar::chunk { background: #06d6a0; border-radius: 5px; }
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
                self.voc_btn.setEnabled(True)
                self.log.append(f"📂 Audio: {os.path.basename(f)}")
            elif ext in [".mp4",".mov",".mkv"]:
                self.clip_paths.append(f)
                self.clips_list.addItem(f"🎬 {os.path.basename(f)}")
                self.log.append(f"📂 Clip: {os.path.basename(f)}")

    def start_vocal(self):
        if not self.audio_path: return
        self.voc_btn.setEnabled(False)
        self.voc_status.setText("Running demucs...")
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "stems")
        eng = AnalysisEngine()
        eng.progress.connect(lambda v, m: self.voc_status.setText(m))
        def run():
            p, err = eng.extract_vocals(self.audio_path, out)
            if err: self.voc_status.setText(f"❌ {err}")
            else: self.voc_status.setText(f"✅ Saved: {os.path.basename(p)}")
            self.voc_btn.setEnabled(True)
        QTimer.singleShot(100, run)

    def start_analysis(self):
        if not self.audio_path or not self.clip_paths:
            QMessageBox.warning(self, "Missing Media", "Drop audio & clips first.")
            return
        self.gen_btn.setEnabled(False); self.cancel_btn.setEnabled(True)
        self.log.clear(); self.progress.setValue(0)
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        self.worker = AnalysisThread(self.audio_path, self.clip_paths, self.start_sp.value(), self.end_sp.value(), self.offset_sp.value(), self.fps_cb.currentText(), out)
        self.worker.progress.connect(lambda v, m: (self.progress.setValue(v), self.log.append(m)))
        self.worker.status.connect(self.sys_lbl.setText)
        self.worker.finished.connect(self.on_done)
        self.worker.error.connect(self.on_err)
        self.worker.start()

    def on_done(self, d):
        self.progress.setValue(100)
        self.log.append(f"✅ Saved: {d['jsx_path']}")
        self.log.append(f"📐 {d['comp_size']} | 🥁 {d['beats']} beats")
        self.statusBar.showMessage("✅ Ready. Open .jsx in After Effects.")
        self.gen_btn.setEnabled(True); self.cancel_btn.setEnabled(False)

    def on_err(self, m):
        self.log.append(f"❌ {m}")
        self.progress.setValue(0)
        self.gen_btn.setEnabled(True); self.cancel_btn.setEnabled(False)

    def cancel_analysis(self):
        if self.worker: self.worker.cancel()
        self.log.append("⛔ Cancelled")
        self.cancel_btn.setEnabled(False); self.gen_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())