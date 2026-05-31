@echo off
title Build EditForge .exe
color 0B
echo  Installing PyInstaller...
pip install pyinstaller -q
echo  Building single-file executable...
pyinstaller --onefile --windowed --name EditForge --icon=NONE main.py
echo.
echo  ✅ Finished! Your .exe is in: dist/EditForge.exe
echo  Copy main.py, requirements.txt, and assets to dist/ folder if needed.
pause