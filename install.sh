#!/bin/sh
# VRCHub one-time setup (Linux/macOS - core features; mic is Windows-only)
echo "=== VRCHub setup ==="
if ! command -v python3 >/dev/null; then
    echo "[X] python3 not found - install Python 3.8+ first."; exit 1
fi
python3 -c "import tkinter" 2>/dev/null || \
    { echo "[X] tkinter missing - install python3-tk package."; exit 1; }
echo "[OK] Python + tkinter present."
echo "Installing core extras (Pillow, tinytuya)..."
python3 -m pip install --user --upgrade Pillow tinytuya || \
    echo "[!] pip failed - VRCHub still runs without light sync."
[ -d plugins ] || mkdir plugins
echo "Setup complete. Start with: python3 vrchub.py"
