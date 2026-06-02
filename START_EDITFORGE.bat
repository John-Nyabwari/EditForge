@echo off
title EditForge v5.0 Desktop
color 0A
echo.
echo  ==========================================
echo         EDITFORGE  v5.0 DESKTOP
echo  ==========================================
echo.
cd /d "%~dp0"
echo  Folder: %CD%
echo.
echo  Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  ❌ Python not found!
    echo  Download from: https://python.org/downloads
    echo  IMPORTANT: Check "Add Python to PATH" during install
    pause
    exit /b 1
)

echo  ✅ Installing/verifying dependencies...
pip install -r requirements.txt -q

echo  ✅ Creating output & log directories...
if not exist "output" mkdir output
if not exist "logs" mkdir logs

echo.
echo  🚀 Launching EditForge Desktop...
python main.py
echo.
echo  EditForge closed. Check logs/app.log for details.
pause