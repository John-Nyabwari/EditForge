# EditForge v5.0 — Desktop Beat-Sync Editor
Automatically create After Effects projects synced to music beats, with AI-assisted masks, creative pattern injection, and instant preview rendering.

## 🚀 Quick Start (Windows)
1. Install Python 3.10+ from [python.org](https://python.org/downloads) (✅ Check "Add to PATH")
2. Install `ffmpeg` and add `C:\ffmpeg\bin` to your Windows PATH
3. Double-click `START_EDITFORGE.bat`
4. The desktop app opens instantly. No browser, no local server.

## 💡 How It Works
- Drag & drop your song (MP3/WAV) and video clips (MP4/MOV)
- Set trim range, beat offset, and FPS
- Click `⚡ Analyze, Mask & Build`
- EditForge outputs:
  - A `.jsx` script that auto-builds a beat-synced After Effects project
  - A low-res preview MP4 for quick verification
  - Optional AI-generated character/foreground masks

## 🛠️ Features
| Feature | Description |
|--------|-------------|
| 🔊 Beat Detection | `librosa` finds BPM & exact beat timestamps in your selected region |
| 🎬 Scene Sync | `pyscenedetect` maps visual cuts to audio beats |
| 🎭 Auto-Mask Assist | YOLOv8-seg (or OpenCV fallback) extracts foreground masks per clip |
| 🎨 Creative Patterns | JSON-driven transitions, zoom curves, glitch probability |
| 🌐 CC Inspiration | Fetches public-domain reference clips (API key optional) |
| 📐 Auto Comp Size | Reads resolution/FPS from first uploaded clip |
| 🔄 Auto-Update | Checks GitHub Releases on startup |
| 📝 Crash Logging | Saves full tracebacks to `logs/app.log` for debugging |

## 📂 Project Structure