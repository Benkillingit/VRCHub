# VRCHub — Full Documentation & Tutorial

VRCHub is a single-file (stdlib-only) Python app that combines the useful parts of **VRCX**, **VRCNext**, **VRC-NEXUS**, **VRCOSC**, and **MagicChatbox**: chatbox, avatar control, the full VRChat web API, OSC input/MIDI, media/heart-rate status, Twitch relay, smart lighting, and more — in one Tkinter window with zero required dependencies.

- **File:** `vrchub.py` (~5,500 lines, one file)
- **Requires:** Python 3.8+ (Windows recommended for full features; works on Linux with `xdg-open`)
- **Repo:** github.com/Benkillingit/VRCHub
- **Version:** 6.4.1

---

## 1. Install & Quick Start (2 minutes)

```bash
# no pip installs needed — stdlib only
python vrchub.py
```

1. Have **VRChat running** (desktop or VR).
2. In VRChat: **Settings → OSC → enabled** (restart VRChat if you just turned it on).
3. Start VRCHub, go to the **Chatbox** tab, type, Send. Your words appear above your head in-game.
4. Optional extras: run `install.bat` (Windows) or `install.sh` (Linux/macOS) to set up Pillow, tinytuya (light sync), and optional face tracking.

Config is saved to `vrchub_config.json` next to the script.

---

## 2. How it all works (the 30-second version)

VRCHub talks to VRChat through four doors:

| Door | Tech | What it gives you |
|---|---|---|
| **Web API** | `api.vrchat.com` (login + auth cookie) | friends, avatars, worlds, instances, groups, favorites, quests, notifications |
| **OSC** | UDP 9000/9001 to/from the game | chatbox, avatar parameters, input control, MIDI, tracking |
| **WebSockets** | third-party services | HypeRate/Pulsoid heart rate, Twitch chat, VRCX link |
| **Local** | your machine | screen light sync, mic chatbox, weather/clock, face tracking, plugins |

---

## 3. Tab-by-tab guide

### Chatbox
Type text, send it to the game. Scheduled messages, typing indicator, media/heart-rate status lines, AFK responder, mic-to-chatbox (voice suite), auto-translate.

### VRChat API
Login with username/password (TOTP 2FA supported). Online/offline friends with instance info, block/mute/unfriend, invites, notifications (accept friend requests), avatar management (search public avatars, equip, favorites, wear times, memos), world search + instance list + join, group management, gallery/files, profile editing.

### Web API
The rest of the web API: search **all** VRChat users, view profiles, send friend requests/messages, manage favorites for avatars/worlds/friends, quests, VRC+ status.

### Avatar Params
Live parameter sliders. Any parameter your avatar exposes over OSC can be driven from here.

### Worlds
Search worlds, list instances, join, or paste a full `vrchat.com/home/launch?...` link into the search box to open it instantly.

### Media & Chat
Spotify/media status in the chatbox, Twitch chat relay, HypeRate/Pulsoid heart rate, lyrics (LRCLIB), server status check.

### Connections
Discord RPC, VRCX relay (live events), OSC router echo, phone remote keyboard (type on your phone, appears in chatbox).

### Extras
OSC input control (move/jump/run your avatar from the app), MIDI piano for piano worlds, head nod/shake, avatar quick-swap by ID, crash guard, net speed test, PiShock, clock+weather.

### Face Track
Optional webcam face tracking → OSC (needs `opencv-python mediapipe`, offered by the installer).

### AI Chat
Talk to the Bas44 ghost inside the app; optionally relay replies to your chatbox.

### Plugins
Drop a `.py` in `plugins/` and it appears as a panel — see **PLUGINS.md**.

### Launcher
Launch VRChat and manage launch options.

### Help
In-app quick start and feature map.

---

## 4. Troubleshooting

- **Nothing appears in-game:** OSC is off in VRChat settings, or a firewall blocks UDP 9000.
- **Login fails:** check username/password; TOTP codes rotate fast — use the current one.
- **Light sync does nothing:** needs `pip install Pillow tinytuya` and your bulb's local key.
- **Face track missing:** run the installer and answer `y` to the face-tracking extras.
- **A button silently fails:** check the status bar at the bottom of the window first.

---

## 5. FAQ

**Is my password stored?** Login cookies are saved locally in your config only if you choose to stay logged in; the password itself is never written to disk after login.

**Is this allowed by VRChat?** It uses the same public API and OSC endpoints that VRCX and friends use. Don't automate spam and you'll be fine.

**Why single file?** Portability — one file, no installer, no dependencies, runs from a USB stick.
