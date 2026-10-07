#!/bin/sh
# Base44 dev launcher for VRCHub.
#
# VRCHub is a Tkinter desktop app, so instead of a dev server the sandbox runs:
#   Xvfb        -> virtual X display the Tk window draws on
#   x11vnc      -> VNC server for that display (localhost only)
#   websockify  -> noVNC web client on port 3000 = the preview entry point
#   vrchub.py   -> the app itself, restarted whenever the source file changes
set -eu

DISP="${DISPLAY:-:99}"
SCREEN="${VRCHUB_SCREEN:-1280x800x24}"
WEB_DIR=/tmp/novnc-web

# noVNC assets + our landing page for "/"
mkdir -p "$WEB_DIR"
cp -r /usr/share/novnc/. "$WEB_DIR"/
cp /app/.base44/novnc-index.html "$WEB_DIR"/index.html

Xvfb "$DISP" -screen 0 "$SCREEN" -nolisten tcp >/tmp/xvfb.log 2>&1 &

x11vnc -display "$DISP" -forever -shared -nopw -localhost -rfbport 5900 \
       -quiet >/tmp/x11vnc.log 2>&1 &

websockify --web="$WEB_DIR" 0.0.0.0:3000 127.0.0.1:5900 \
    >/tmp/novnc.log 2>&1 &

# wait for the X server before the app tries to open a window
i=0
while ! xdpyinfo -display "$DISP" >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -gt 50 ]; then
        echo "Xvfb did not come up on $DISP" >&2
        exit 1
    fi
    sleep 0.2
done

# Tkinter has no hot reload: restart the app when vrchub.py changes so edits
# reach the preview without recreating the container.
while true; do
    sum=$(md5sum /app/vrchub.py | cut -d' ' -f1)
    DISPLAY="$DISP" python3 /app/vrchub.py >>/tmp/vrchub.log 2>&1 &
    pid=$!
    while kill -0 "$pid" 2>/dev/null; do
        sleep 1
        [ "$(md5sum /app/vrchub.py | cut -d' ' -f1)" = "$sum" ] && continue
        echo "vrchub.py changed - restarting the app"
        kill "$pid" 2>/dev/null || true
        break
    done
    wait "$pid" 2>/dev/null || true
    sleep 1
done
