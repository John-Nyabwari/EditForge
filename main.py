import sys
import os
import json
import subprocess
import math
import traceback
import logging
import threading
import requests
import numpy as np
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QListWidget, QSlider, QComboBox, QLineEdit, 
    QProgressBar, QGroupBox, QFileDialog, QMessageBox, QStatusBar,
    QSizePolicy, QTextEdit, QDoubleSpinBox, QSplitter, QCheckBox, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer, QRectF
from PyQt6.QtGui import QColor, QBrush, QPen, QPainter, QFont, QMouseEvent

# ==================== LOGGING & CRASH RECOVERY ====================
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
def log_exception(exc_type, exc_value, exc_tb):
    logging.error("UNHANDLED EXCEPTION", exc_info=(exc_type, exc_value, exc_tb))
sys.excepthook = log_exception
logging.info("EditForge v5.0 initialized")

# ==================== CUSTOM BEAT TIMELINE ====================
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
        m = 10; dw = w - 2*m
        painter.setPen(QPen(QColor("#444"), 2))
        painter.drawLine(m, h//2, w-m, h//2)
        for b in self.beats:
            x = m + (b / self.duration) * dw
            c = QColor("#06d6a0") if b >= self.offset else QColor("#888")
            painter.setPen(QPen(c, 3 if b >= self.offset else 1))
            painter.drawLine(int(x), h//2 - 15, int(x), h//2 + 15)
    def mousePressEvent(self, event: QMouseEvent):
        if not self.duration: return
        m = 10; dw = self.width() - 2*m
        t = ((event.position().x() - m) / dw) * self.duration
        self.offset = max(0, min(t, self.duration))
        self.beatClicked.emit(self.offset)
        self.update()

# ==================== CORE ENGINE ====================
class AnalysisEngine(QObject):
    progress = pyqtSignal(int, str)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    cancel_flag = False

    def set_cancel(self): self.cancel_flag = True

    def _check_dep(self, cmd):
        try: return subprocess.run(cmd, capture_output=True, text=True).returncode == 0
        except: return False

    def get_video_props(self, path):
        import cv2
        cap = cv2.VideoCapture(path)
        if not cap.isOpened(): return {"w": 1920, "h": 1080, "fps": 30.0}
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.release()
        return {"w": w, "h": h, "fps": fps}

    def load_patterns(self, path):
        try:
            with open(path, "r") as f: return json.load(f)
        except: return None

    def auto_mask_assist(self, clip_paths, out_dir):
        self.progress.emit(5, "🎭 Initializing mask engine...")
        masks_dir = os.path.join(out_dir, "masks")
        os.makedirs(masks_dir, exist_ok=True)
        try:
            from ultralytics import YOLO
            model = YOLO("yolov8n-seg.pt")
            self.progress.emit(20, "🧠 Loading YOLOv8-seg...")
        except ImportError:
            model = None
            self.progress.emit(20, "⚠️ ultralytics missing. Using OpenCV fallback...")

        for i, path in enumerate(clip_paths):
            if self.cancel_flag: return []
            self.progress.emit(30 + i*(40/max(1, len(clip_paths))), f"Masking {Path(path).name}...")
            mask_path = os.path.join(masks_dir, f"mask_{i+1:02d}.png")
            if model:
                try:
                    res = model(path, conf=0.25, verbose=False)
                    if res[0].masks is not None: res[0].save(mask_path); continue
                except: pass
            import cv2
            cap = cv2.VideoCapture(path)
            _, frame = cap.read()
            cap.release()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            mask = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)
            mask[thresh == 0] = [0, 0, 0]
            mask[thresh == 255] = [255, 255, 255]
            cv2.imwrite(mask_path, mask)
        return masks_dir

    def render_preview(self, clips, audio, beats, out_dir, patterns):
        self.progress.emit(60, "🎬 Building preview timeline...")
        props = self.get_video_props(clips[0])
        w, h, fps = props["w"], props["h"], props["fps"]
        out_vid = os.path.join(out_dir, "EditForge_Preview.mp4")
        tmp_dir = os.path.join(out_dir, "tmp_concat")
        os.makedirs(tmp_dir, exist_ok=True)
        concat = os.path.join(tmp_dir, "list.txt")
        with open(concat, "w") as f:
            for i, c in enumerate(clips):
                f.write(f"file '{c.replace(chr(92), '/')}'\n")
                if i < len(clips)-1:
                    f.write(f"duration {(beats[i+1]-beats[i]) if i+1<len(beats) else 2.0}\n")
            f.write("outpoint 0\n")
        self.progress.emit(75, "⚡ Rendering via ffmpeg...")
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat,
               "-i", audio, "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
               "-c:a", "aac", "-b:a", "128k", "-shortest", "-t", str(beats[-1]+1),
               "-vf", f"scale={w//2}:{h//2},drawtext=text='EditForge Preview':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2",
               out_vid]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return out_vid if res.returncode == 0 else None

    def fetch_cc_inspiration(self, query, out_dir):
        self.progress.emit(10, "🌐 Fetching public domain inspiration...")
        headers = {"Authorization": "YOUR_PEXELS_API_KEY_HERE"}
        url = f"https://api.pexels.com/videos/search?query={query}&per_page=3"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                vids = r.json().get("videos", [])
                out = os.path.join(out_dir, "inspiration")
                os.makedirs(out, exist_ok=True)
                for i, v in enumerate(vids[:2]):
                    link = v["video_files"][0]["link"]
                    p = os.path.join(out, f"cc_insp_{i+1}.mp4")
                    with open(p, "wb") as f: f.write(requests.get(link, timeout=15).content)
                self.progress.emit(40, "✅ Downloaded CC clips")
                return out
        except Exception as e:
            logging.warning(f"CC Fetch failed: {e}")
        self.progress.emit(40, "⚠️ API missing or offline. Add key to fetch_cc_inspiration()")
        return None

    def generate_jsx(self, path, audio, clips, beats, offset, props, patterns):
        w, h, fps = props["w"], props["h"], props["fps"]
        dur = beats[-1] + 2.0 if beats else 10.0
        p = patterns or {"transitions": ["fade", "zoom"], "zoom_curves": [0.9, 1.1]}
        jsx = f"""// EditForge v5.0 Auto-Generated
app.beginUndoGroup("EditForge Build");
var main = app.project.items.addComp("EditForge_MAIN", {w}, {h}, 1.0, {dur}, {fps});
main.openInViewer();
var aud = main.layers.add(new File("{audio.replace(chr(92), "/")}"));
aud.property("Marker").setValueAtTime({offset}, new MarkerValue("Beat Start"));
var masks = app.project.items.addComp("MASKS_REF", {w}, {h}, 1.0, {dur}, {fps});
for(var m=1; m<={len(clips)}; m++) {{ masks.layers.addSolid([0.4, 0.9, 0.4], "Mask_"+m, {w}, {h}, 1.0); masks.layer(m).trackMatteType = TrackMatteType.ALPHA; }}
"""
        for i, clip in enumerate(clips):
            b_start = beats[i] if i < len(beats) else i*1.5
            b_end = beats[i+1] if i+1 < len(beats) else b_start + 1.0
            jsx += f"""
var c = app.project.items.addComp("CLIP_{i+1:02d}", {w}, {h}, 1.0, {dur}, {fps});
var ph = c.layers.addSolid([0.15, 0.15, 0.25], "Footage_Placeholder", {w}, {h}, 1.0); ph.opacity = 50;
var mk = c.layers.add(masks.layer({i+1}));
var s = ph.property("Scale"); s.setValueAtTime(0, [{p['zoom_curves'][0]*100},{p['zoom_curves'][0]*100}]);
s.setValueAtTime({b_start-b_start}, [{p['zoom_curves'][1]*100},{p['zoom_curves'][1]*100}]);
main.layers.add(c); c.startTime = {offset + b_start};
"""
        jsx += "\napp.endUndoGroup();\n"
        with open(path, "w", encoding="utf-8") as f: f.write(jsx)

    def run_full(self, audio, clips, start, end, offset, fps, out, pattern_path=None):
        try:
            self.progress.emit(0, "🔍 Checking environment...")
            missing = [d for d in ["librosa", "pyscenedetect", "opencv", "ffmpeg"] if not self._check_dep([d, "-version" if d=="ffmpeg" else "--help"])]
            if missing: self.error.emit(f"Missing: {', '.join(missing)}"); return
            props = self.get_video_props(clips[0])
            props["fps"] = float(fps)
            self.progress.emit(10, f"📐 Comp: {props['w']}x{props['h']} @ {props['fps']}fps")
            if self.cancel_flag: return
            import librosa
            self.progress.emit(20, "🎵 Loading audio...")
            y, sr = librosa.load(audio, sr=None, mono=True)
            s, e = max(0, start), min(len(y)/sr, end)
            idx_s, idx_e = int(s*sr), int(e*sr)
            _, beats = librosa.beat.beat_track(y=y[idx_s:idx_e], sr=sr, trim=False)
            bt = librosa.frames_to_time(beats, sr=sr) + s
            bt = [b for b in bt if s <= b <= e]
            self.progress.emit(40, f"🥁 {len(bt)} beats mapped")
            patterns = self.load_patterns(pattern_path) if pattern_path else None
            if self.cancel_flag: return
            os.makedirs(out, exist_ok=True)
            jsx = os.path.join(out, "EditForge_v5.jsx")
            self.generate_jsx(jsx, audio, clips, bt, offset, props, patterns)
            self.progress.emit(70, "✅ .jsx generated")
            if self.cancel_flag: return
            preview = self.render_preview(clips, audio, bt, out, patterns)
            self.progress.emit(100, "✅ Phase 5 complete!")
            self.finished.emit({"jsx": jsx, "preview": preview or "N/A", "beats": len(bt), "comp": f"{props['w']}x{props['h']}"})
        except Exception as ex:
            logging.error(f"Engine run failed: {ex}\n{traceback.format_exc()}")
            self.error.emit(f"Fatal: {str(ex)}\nCheck logs/app.log for details")

# ==================== THREADING ====================
class WorkerThread(QThread):
    progress = pyqtSignal(int, str)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    def __init__(self, audio, clips, s, e, off, fps, out, pat=None):
        super().__init__()
        self.args = (audio, clips, s, e, off, fps, out, pat)
        self.eng = AnalysisEngine()
    def run(self):
        self.eng.progress.connect(self.progress)
        self.eng.finished.connect(self.finished)
        self.eng.error.connect(self.error)
        self.eng.run_full(*self.args)
    def cancel(self): self.eng.set_cancel()

# ==================== MAIN UI ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.version = "5.0.0"
        self.setWindowTitle(f"EditForge v{self.version} Desktop")
        self.resize(1300, 850)
        self.setAcceptDrops(True)
        self.setup_ui()
        self.apply_theme()
        self.audio_path = None
        self.clip_paths = []
        self.worker = None
        QTimer.singleShot(1500, self.check_updates)
        logging.info(f"UI initialized | v{self.version}")

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        tabs = QTabWidget()
        t1 = QWidget()
        lv = QVBoxLayout(t1)
        self.music_lbl = QLabel("Drag & Drop Audio")
        self.music_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.music_lbl.setStyleSheet("padding: 15px; border: 2px dashed #555; border-radius: 8px;")
        lv.addWidget(self.music_lbl)
        trim = QGroupBox("✂️ Trim & Offset")
        tv = QVBoxLayout(trim)
        h1, h2 = QHBoxLayout(), QHBoxLayout()
        h1.addWidget(QLabel("Start")); self.sp_s = QDoubleSpinBox(); self.sp_s.setRange(0,300)
        h1.addWidget(self.sp_s); h1.addWidget(QLabel("End")); self.sp_e = QDoubleSpinBox(); self.sp_e.setRange(1,600); self.sp_e.setValue(30)
        h1.addWidget(self.sp_e)
        h2.addWidget(QLabel("Beat Offset")); self.sp_off = QDoubleSpinBox(); self.sp_off.setRange(0,30); self.sp_off.setSingleStep(0.1)
        h2.addWidget(self.sp_off)
        tv.addLayout(h1); tv.addLayout(h2)
        lv.addWidget(trim)
        self.timeline = BeatTimeline()
        self.timeline.beatClicked.connect(lambda t: self.sp_off.setValue(t))
        lv.addWidget(self.timeline)
        clips_box = QGroupBox("🎬 Clips")
        self.clips_list = QListWidget()
        self.clips_list.setAcceptDrops(True); self.clips_list.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.clips_list.setStyleSheet("background: #1a1a1a; color: #eee; border-radius: 6px;")
        clips_box.setLayout(QVBoxLayout()); clips_box.layout().addWidget(self.clips_list)
        lv.addWidget(clips_box)
        tabs.addTab(t1, "⚡ Analyze & Export")
        t2 = QWidget()
        tv2 = QVBoxLayout(t2)
        masks_box = QGroupBox("🎭 Auto-Mask Assist")
        mv = QVBoxLayout(masks_box)
        self.mask_btn = QPushButton("Generate Masks from Clips"); self.mask_btn.setEnabled(False)
        mv.addWidget(self.mask_btn)
        self.mask_status = QLabel("Status: Idle"); mv.addWidget(self.mask_status)
        tv2.addWidget(masks_box)
        patterns_box = QGroupBox("🎨 Creative Patterns")
        pv = QVBoxLayout(patterns_box)
        self.pat_btn = QPushButton("Upload patterns.json"); pv.addWidget(self.pat_btn)
        pv.addWidget(QLabel("Define transitions, zoom curves, glitch probability in JSON"))
        tv2.addWidget(patterns_box)
        online_box = QGroupBox("🌐 Online Inspiration (CC)")
        ov = QVBoxLayout(online_box)
        self.online_btn = QPushButton("Fetch Public Domain Clips"); ov.addWidget(self.online_btn)
        self.online_status = QLabel("Status: Offline (Add API key in code)"); ov.addWidget(self.online_status)
        tv2.addWidget(online_box)
        tabs.addTab(t2, "🛠️ Creative Tools")
        main.addWidget(tabs, 1)
        right = QWidget()
        rv = QVBoxLayout(right)
        set_box = QGroupBox("⚙️ Settings")
        self.fps_cb = QComboBox(); self.fps_cb.addItems(["24", "30", "60"])
        sv = QVBoxLayout(set_box)
        sv.addWidget(QLabel("FPS")); sv.addWidget(self.fps_cb)
        sv.addWidget(QLabel("Comp size auto-matches first clip"))
        rv.addWidget(set_box)
        sys_box = QGroupBox("🤖 System")
        self.sys_lbl = QLabel(f"v{self.version} | Checking deps...")
        sys_box.setLayout(QVBoxLayout()); sys_box.layout().addWidget(self.sys_lbl)
        rv.addWidget(sys_box)
        log_box = QGroupBox("📜 Log")
        self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(180)
        self.log.setStyleSheet("background: #0f0f0f; color: #aaffaa; font-family: monospace;")
        log_box.setLayout(QVBoxLayout()); log_box.layout().addWidget(self.log)
        rv.addWidget(log_box)
        act_box = QGroupBox("🚀 Export")
        av = QVBoxLayout(act_box)
        self.gen_btn = QPushButton("⚡ Analyze, Mask & Build")
        self.gen_btn.setStyleSheet("background: #06d6a0; color: black; font-weight: bold; padding: 12px; border-radius: 6px;")
        self.cancel_btn = QPushButton("⛔ Cancel"); self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("background: #ef476f; color: white; padding: 12px; border-radius: 6px;")
        ah = QHBoxLayout(); ah.addWidget(self.gen_btn); ah.addWidget(self.cancel_btn)
        av.addLayout(ah)
        self.progress = QProgressBar()
        av.addWidget(self.progress)
        rv.addWidget(act_box)
        main.addWidget(right, 1)
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.gen_btn.clicked.connect(self.start_analysis)
        self.cancel_btn.clicked.connect(self.cancel_analysis)
        self.mask_btn.clicked.connect(self.start_masking)
        self.pat_btn.clicked.connect(self.upload_pattern)
        self.online_btn.clicked.connect(self.fetch_cc)

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background: #111; color: #fff; }
            QGroupBox { border: 1px solid #333; border-radius: 8px; margin-top: 6px; font-weight: bold; padding-top: 12px; }
            QLineEdit, QComboBox, QPushButton, QDoubleSpinBox, QTextEdit, QListWidget { background: #1e1e1e; border: 1px solid #444; padding: 8px; border-radius: 6px; color: #eee; }
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
                self.mask_btn.setEnabled(True)
                self.log.append(f"📂 Audio: {os.path.basename(f)}")
            elif ext in [".mp4",".mov",".mkv"]:
                self.clip_paths.append(f)
                self.clips_list.addItem(f"🎬 {os.path.basename(f)}")
                self.log.append(f"📂 Clip: {os.path.basename(f)}")
            logging.info(f"File dropped: {os.path.basename(f)}")

    def start_analysis(self):
        if not self.audio_path or not self.clip_paths:
            QMessageBox.warning(self, "Missing Media", "Drop audio & clips first.")
            return
        self.gen_btn.setEnabled(False); self.cancel_btn.setEnabled(True)
        self.log.clear(); self.progress.setValue(0)
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        pat = getattr(self, "_pat_path", None)
        self.worker = WorkerThread(self.audio_path, self.clip_paths, self.sp_s.value(), self.sp_e.value(), self.sp_off.value(), self.fps_cb.currentText(), out, pat)
        self.worker.progress.connect(lambda v, m: (self.progress.setValue(v), self.log.append(m)))
        self.worker.finished.connect(self.on_done)
        self.worker.error.connect(self.on_err)
        self.worker.start()
        logging.info("Analysis started")

    def on_done(self, d):
        self.progress.setValue(100)
        self.log.append(f"✅ .jsx: {d['jsx']}")
        self.log.append(f"🎬 Preview: {d['preview']}")
        self.statusBar.showMessage("✅ Ready. Open .jsx in After Effects.")
        self.gen_btn.setEnabled(True); self.cancel_btn.setEnabled(False)
        logging.info(f"Analysis complete | JSX: {d['jsx']}")

    def on_err(self, m):
        self.log.append(f"❌ {m}")
        self.progress.setValue(0)
        self.gen_btn.setEnabled(True); self.cancel_btn.setEnabled(False)
        logging.error(f"Analysis failed: {m}")

    def cancel_analysis(self):
        if self.worker: self.worker.cancel()
        self.log.append("⛔ Cancelled")
        self.cancel_btn.setEnabled(False); self.gen_btn.setEnabled(True)
        logging.info("Operation cancelled by user")

    def start_masking(self):
        if not self.clip_paths: return
        self.mask_btn.setEnabled(False)
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        eng = AnalysisEngine()
        eng.progress.connect(lambda v, m: self.mask_status.setText(m))
        def run():
            p = eng.auto_mask_assist(self.clip_paths, out)
            self.mask_status.setText(f"✅ Masks saved: {p}")
            self.mask_btn.setEnabled(True)
        QTimer.singleShot(50, run)

    def upload_pattern(self):
        f, _ = QFileDialog.getOpenFileName(self, "Load Creative Patterns", "", "JSON (*.json)")
        if f:
            self._pat_path = f
            self.log.append(f"🎨 Loaded: {os.path.basename(f)}")
            logging.info(f"Pattern loaded: {f}")

    def fetch_cc(self):
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        eng = AnalysisEngine()
        eng.progress.connect(lambda v, m: self.online_status.setText(m))
        def run():
            p = eng.fetch_cc_inspiration("cinematic transition", out)
            self.online_status.setText(f"✅ Downloaded to: {p or 'N/A'}")
        QTimer.singleShot(50, run)

    def check_updates(self):
        try:
            # 🔑 REPLACE WITH YOUR GITHUB USERNAME & REPO
            url = "https://api.github.com/repos/YOUR_USERNAME/EditForge/releases/latest"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                latest = r.json().get("tag_name", "0.0.0").lstrip("v")
                if latest > self.version:
                    QMessageBox.information(self, "Update Available", f"New version v{latest} is ready.\nDownload at:\n{r.json().get('html_url', '#')}")
                    logging.info(f"Update found: v{latest}")
        except Exception as e:
            logging.warning(f"Update check failed: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("QToolTip { color: white; background: #333; }")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())