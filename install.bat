@echo off
title VRCHub setup
echo ================================
echo   VRCHub - one-time setup
echo ================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [X] Python not found. Install it from https://python.org
    echo     (check "Add Python to PATH" in the installer), then re-run this file.
    pause
    exit /b 1
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)"
if errorlevel 1 echo [!] Python 3.8+ recommended, continuing anyway.
echo.

python -c "import tkinter" 2>nul
if errorlevel 1 (
    echo [X] tkinter missing. Re-install Python and enable "tcl/tk and IDLE".
    pause
    exit /b 1
)
echo [OK] Python + tkinter present.

echo.
echo Installing core extras (screen light sync + UI color: Pillow, tinytuya)...
python -m pip install --user --upgrade Pillow tinytuya
if errorlevel 1 echo [!] pip failed - VRCHub still runs, just without light sync.

echo.
set /p FT=Install face-tracking extras (opencv-python mediapipe, ~200MB)? [y/N]:
if /i "%FT%"=="y" (
    python -m pip install --user --upgrade opencv-python mediapipe
    if errorlevel 1 echo [!] face-tracking install failed - optional, skipping.
)

echo.
if not exist plugins mkdir plugins
echo [OK] plugins folder ready (drop community .py files there).

echo.
echo ================================
echo   Setup complete. Start with:
echo       python vrchub.py
echo ================================
pause
