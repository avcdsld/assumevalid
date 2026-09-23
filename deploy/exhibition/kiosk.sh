#!/usr/bin/env bash
# Fullscreen the exhibition display on the monitor wired to this Pi.
#
# The local API server (explorer-api.py, port 8080) serves BOTH the page and its
# /api data, so the browser talks only to localhost — no network, same origin.
# Run this from the graphical session (autostart), not before X/Wayland is up.
set -u
URL="${1:-http://localhost:8080/}"

# Keep the screen awake and hide the pointer (X11). Harmless if the tools are absent.
xset s off -dpms s noblank 2>/dev/null || true
command -v unclutter >/dev/null && (unclutter -idle 0 >/dev/null 2>&1 &)

# chromium-browser on Raspberry Pi OS; plain "chromium" on some images.
CHROME="$(command -v chromium-browser || command -v chromium)"
[ -n "$CHROME" ] || { echo "chromium not found (apt install chromium-browser)"; exit 1; }

exec "$CHROME" \
  --kiosk --incognito --noerrdialogs --disable-infobars \
  --disable-session-crashed-bubble --disable-features=Translate,TranslateUI \
  --check-for-update-interval=31536000 --disable-pinch --overscroll-history-navigation=0 \
  --autoplay-policy=no-user-gesture-required \
  "$URL"
