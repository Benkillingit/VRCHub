#!/bin/sh
# Read-only healthcheck for the sandbox service: both halves of the preview
# must work (the noVNC web endpoint AND the VRCHub GUI window), and it says
# which one failed.
fail=0

if ! curl -fsS -o /dev/null http://127.0.0.1:3000/vnc.html; then
    echo "noVNC web endpoint (port 3000) not responding"
    fail=1
fi

if ! xwininfo -root -tree -display "${DISPLAY:-:99}" 2>/dev/null \
        | grep -qi vrchub; then
    echo "VRCHub window not on display ${DISPLAY:-:99}"
    fail=1
fi

exit $fail
