# VRCHub — Full Documentation & Tutorial

VRCHub is a single-file (stdlib-only) Python app that combines the useful parts of **VRCX**, **VRCNext**, **VRC-NEXUS**, **VRCOSC**, and **MagicChatbox**: chatbox, avatar control, VRChat account features, media/heart-rate status, Twitch relay, and more — in one Tkinter window with zero dependencies.

- **File:** `vrchub.py` (~2,500 lines, one file)
- **Requires:** Python 3.8+ (Windows recommended for full features; works on Linux with `xdg-open`)
- **Repo:** github.com/Benkillingit/VRCHub
- **Version:** 4.0.0

---

## 1. Install & Quick Start (2 minutes)

```bash
# no pip installs needed — stdlib only
python vrchub.py
```

1. Have **VRChat running** (desktop or VR).
2. In VRChat: **Settings → OSC → enabled** (restart VRChat if you just turned it on).
3. In VRCHub, open the **Chatbox tab**, type something, hit Send. It appears above your head in-game.

That's the core. Everything else builds on it. If nothing appears in-game, see [Troubleshooting](#8-troubleshooting).

Settings live in `vrchub_config.json` next to the app. Delete it to reset everything.

---

## 2. How it all works (the 30-second version)

VRCHub talks to VRChat through four doors:

| Door | What it is | What it gives you |
|---|---|---|
| **OSC out** (UDP 9000) | VRChat's local network protocol | chatbox text, avatar parameters, gestures |
| **OSC in** (listener) | VRChat sends events back over OSC | live traffic, what other apps are doing |
| **VRChat REST API** (api.vrchat.com) | your account login | friends, avatars, worlds, notifications, moderation |
| **WebSockets** | third-party services | HypeRate/Pulsoid heart rate, Twitch chat, VRCX link |

OSC is the same wire VRCX, VRCOSC, and MagicChatbox all use. VRCHub sends to port 9000 (VRChat's ear) and can listen on a port of yours to see everything flying back and forth.

---

## 3. Tab-by-tab guide

### Chatbox
- **Send text** — appears above your head in VRChat. Checkbox controls the notification sound.
- **Typing indicator** — shows the "typing" animation while you compose.
- **Cycle lines** — a list that rotates automatically in your chatbox (great for statuses/pronouns).
- **Scheduled messages (4.0)** — queue a message to send X minutes later; the queue runs in the background.
- **Quick replies** — one-click presets.

### AI Chat
Talk to an AI assistant; its replies can be relayed straight into your VRChat chatbox. Useful for in-game banter or NPC-style roleplay.

### VRChat API
- **Login** — your VRChat email + password; TOTP 2FA supported (enter your authenticator code when prompted).
- **Online friends** — live list with status and world; "Include offline" shows everyone.
- **Friend watch (3.2)** — toggle "Watch (chatbox alerts)": when a friend goes offline or changes world, you get an alert above your head (polls every 60s).
- **Block / Mute** — moderation buttons on the selected friend, with confirm dialogs.
- **Avatars** — "Load my avatars" lists yours; **Equip selected** hot-swaps your avatar *while in a world* (same trick as VRC-NEXUS). Public avatar search included.
- **Wear times & memos (3.2)** — every avatar you equip gets a running wear-time counter and a memo field (your private notes per avatar). Both persist in the config.
- **Profiles (3.1)** — save multiple VRChat sessions (cookies) under names, switch accounts instantly. Multi-account support.
- Session cookies are saved locally in `vrchub_config.json`. Log out of VRChat's website if you want to invalidate them.

### Worlds (3.0)
- **Search** — world search by name; results show author and current occupancy.
- **Instances** — pick a world, show its live instances; double-click one to open the official `vrchat.com/home/launch` link, approve it in your browser, and VRChat jumps in.
- **Notifications** — pulls your VRChat notification feed.

### Avatar Params
- Set **any avatar parameter by exact name** (bool/int/float). Find parameter names in VRCX or your avatar descriptor.
- **Gestures** — one-click gesture buttons (Neutral/Fist/Point/Open/Peace/Rock/Gun/ThumbsUp).

### Media & Chat
- **Media status** — scan windows, pick your player (Spotify, browsers, anything with the track in its title), and it shows in your chatbox. "Only announce on track change" avoids spam (3.3).
- **Twitch relay** — your Twitch chat mirrors into your VRChat chatbox (IRC over TLS).
- **HypeRate** — heart rate from a BLE HR monitor via hypeRate.com; BPM shows in chatbox.
- **Pulsoid (3.1)** — alternative heart-rate source; paste your Pulsoid token.

### Extras
| Feature | What it does |
|---|---|
| **AFK detection** | after X minutes of no VRCHub activity, sends "AFK"; sends "I'm back!" when you act again |
| **Chatbox stopwatch** | running timer in your chatbox |
| **Countdown (4.0)** | counts down from N minutes, then blasts "GO!" with a sound |
| **Clock** | current time in your chatbox, refreshed on an interval |
| **Random gesture cycler** | fires a random gesture for 3s every N seconds |
| **System status** | battery % + RAM in your chatbox (Windows); optional media-title combo line |
| **PiShock** | your own shock collar only — vibe/shock buttons via the PiShock web API; settings are session-only |

Note: AFK counts VRCHub-side activity (messages you send from this app), not keyboard/mouse input.

### Face Track (4.1, experimental)
- **What it does**: reads your webcam with MediaPipe, estimates face blendshapes, and sends them to VRChat as face-tracking parameters (`v2/EyeBlink*`, `v2/JawOpen`, `v2/MouthSmile*`, brows, squints).
- **Setup (once)**: `pip install opencv-python mediapipe`. The ~3.7 MB face model downloads automatically on first run.
- **Use with a face-tracking-enabled avatar.** Desktop webcam quality won't match a dedicated tracker; VRCFT (the dedicated app) remains the gold standard — this is the zero-extra-hardware path.
- Everything else in VRCHub still runs without these dependencies installed; the tab just says what's missing.
- **Stop** before unplugging the camera; Start again with a different camera index if needed.

### Connections (2.1+)
- **App detection** — Scan lists which of VRChat/VRCX/VRCOSC/MagicChatbox are running and whether VRCX's port is open.
- **VRCX WebSocket** — enable VRCX → Settings → WebSocket Server (port 9739), set a token, connect here. You see VRCX's live event stream; friend joins/leaves can be auto-announced in your chatbox. (Protocol verified best-effort; the log shows whatever VRCX sends.)
- **OSC listener** — binds a UDP port (try 9002, VRCX uses 9001) and shows every OSC message flying between VRChat and your other apps. Type in MagicChatbox and watch it appear here — great for learning how it all works.

### Launcher (VRCNext-style)
Autodetect or paste paths for VRChat / VRCX / VRCOSC / MagicChatbox; "Launch all" starts your whole setup. Paths persist.

### Help
The quick-start tutorial, in-app.

---

## 4. Feature → original app map

| VRCHub feature | Origin app |
|---|---|
| Chatbox, typing, cycle lines | MagicChatbox |
| Avatar params, gestures, AFK, clock, gesture cycler, stopwatch | VRCOSC |
| Friends, avatars, worlds, notifications, moderation, profiles, wear times, memos | VRCX / VRCNext |
| Equip hot-swap | VRC-NEXUS |
| Media status, Twitch, HR, launcher | all of them |

---

## 5. Scheduled messages — how the queue works

Queued messages go into an in-memory list with a due-timestamp. A background thread wakes, finds the earliest due message, and sends it to OSC when its time arrives. If you close VRCHub, unsent queue items are gone (they're not persisted on purpose — a stale message sent tomorrow is usually a surprise).

---

## 6. Security & privacy notes

- Your VRChat session cookie and all settings stay in `vrchub_config.json` on your machine.
- PiShock credentials are kept in memory for the session only, never written to disk.
- The AI chat uses your configured key; the NPC relay endpoint is rate-limited per IP.
- VRCHub sends OSC only to 127.0.0.1 unless you change the host.

---

## 7. Version history (short)

- **4.0** — countdown timer, scheduled chatbox messages, in-app Help tab, this documentation
- **3.3** — chatbox clock, media+hardware combo line, announce-on-track-change, Extras layout fix
- **3.2** — avatar wear times, avatar memos, friend watcher, block/mute (top-voted GitHub requests)
- **3.1** — multi-account profiles, Pulsoid HR, PiShock, offline friends
- **3.0** — Worlds tab, instances+join, notifications, favorites, AFK, stopwatch, gesture cycler, system status
- **2.1** — VRCX WebSocket link, OSC listener, app detection
- **2.0** — VRChat API login (TOTP), friends, avatars+equip, public search, Twitch, HypeRate, media status, launcher, AI chat
- **1.0** — OSC chatbox, params, gestures, cycle lines

---

## 8. Troubleshooting

**Nothing shows in my chatbox.**
VRChat: Settings → OSC → enable, then restart VRChat. Check VRCHub's OSC port matches (9000 default). Firewalls rarely block localhost UDP, but try allowing Python.

**Avatar equip does nothing.**
You must be in a world (not the menu/login screen). Wait a few seconds; VRChat rate-limits avatar swaps.

**Login fails.**
Use your authenticator's current code for 2FA. VRChat also locks accounts after repeated failures — wait 15 minutes.

**Twitch relay silent.**
Needs an IRC-capable Twitch account; Twitch now requires an OAuth token for some accounts (anonymous read works for most channels).

**HypeRate shows nothing.**
Your phone/watch must be running HypeRate and paired to your device ID first.

**VRCX connect fails.**
VRCX → Settings → WebSocket Server must be enabled, port 9739, and the token pasted here. The log shows the exact failure.

**System status shows nothing.**
Battery/RAM queries use Windows APIs; on desktops without a battery only RAM appears. Non-Windows: not supported.

**The Extras tab looks squished.** — that was a 3.2 layout bug, fixed in 3.3. Update your file.

---

*Made for Ben, by his Superagent. Stdlib only, one file, forever.*
