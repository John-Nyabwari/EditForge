@echo off
title Package EditForge v5.0
color 0B
echo  ==========================================
echo     EDITFORGE  v5.0  PACKAGER
echo  ==========================================
echo.
cd /d "%~dp0"
echo  [1/4] Cleaning old builds...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del /q *.spec

echo  [2/4] Installing dependencies...
pip install -r requirements.txt pyinstaller -q

echo  [3/4] Building executable...
pyinstaller --onefile --windowed --name EditForge --add-data "creative_patterns.json;." main.py
echo  ✅ Executable built in: dist/

echo  [4/4] Creating release package...
set OUT_DIR=EditForge_v5.0_Portable
mkdir "%OUT_DIR%"
copy "dist\EditForge.exe" "%OUT_DIR%\"
copy "requirements.txt" "%OUT_DIR%\"
copy "creative_patterns.json" "%OUT_DIR%\"
copy "README.md" "%OUT_DIR%\"
mkdir "%OUT_DIR%\output"
mkdir "%OUT_DIR%\logs"
tar -a -c -f EditForge_v5.0_Portable.zip "%OUT_DIR%"
rmdir /s /q "%OUT_DIR%"
echo  ✅ Release zip created: EditForge_v5.0_Portable.zip
echo.
pause