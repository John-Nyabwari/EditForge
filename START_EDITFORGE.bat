@echo off
title EditForge v2.0 (Desktop)
color 0A
echo.
echo  ==========================================
echo         EDITFORGE  v2.0 DESKTOP
echo  ==========================================
echo.
cd /d "%~dp0"
echo  Folder: %CD%
echo.
echo  Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found!
    echo  Download from: https://python.org/downloads
    pause
    exit /b 1
)

echo  Installing dependencies (first run only)...
pip install -r requirements.txt -q

echo.
echo  Launching EditForge Desktop...
python main.py
echo.
echo  EditForge closed.
pause