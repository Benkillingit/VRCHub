# VRCHub

**Your VRChat toolkit in one place.** A single-file, stdlib-only Python app that takes the feature set of VRCX, VRCNext, VRC-NEXUS, VRCOSC and MagicChatbox and combines it into one lightweight window. No dependencies, no installer.

## Feature map — where each feature comes from

| VRCHub feature | From |
|---|---|
| OSC Chatbox (typing indicator, quick replies, notify) | VRCOSC / MagicChatbox |
| Cycle lines — auto-send a rotating list every N sec | VRC-NEXUS |
| Media status — show the Spotify track / active window in your chatbox | MagicChatbox / VRC-NEXUS |
| VRChat login (username/password + TOTP 2FA, session saved) | VRCX |
| Online friends list with status + world | VRCX / VRCNext |
| My avatars list + one-click equip (hot-swap in-game) | VRCX / VRCNext |
| Public avatar search + equip | VRC-NEXUS |
| Avatar parameter control (bool/int/float) + gesture quick-fire + inputs | VRCOSC |
| Twitch chat relay → chatbox (anonymous read) | VRCOSC |
| HypeRate heart rate → chatbox (WebSocket) | VRCOSC |
| Launcher: VRChat / VRCX / VRCOSC / MagicChatbox, autodetect, launch-all | VRCNext |
| **NEW in 3.1** | |
| Multi-account profiles — save/load several VRChat sessions | VRCNext |
| Pulsoid heart rate (alternative to HypeRate, token at pulsoid.net) | VRCOSC |
| PiShock module (your collar only, session-only settings) | VRCOSC |
| Friends list: include-offline toggle | VRCX |
| **NEW in 3.0** | |
| World search + live instances + join via launch link | VRCX |
| Notifications feed (+ accept/hide) | VRCX |
| Favorite avatars list with equip | VRCX |
| AFK detection — auto 'AFK' / 'I'm back!' in chatbox | VRCOSC |
| Chatbox stopwatch, random gesture cycler | VRCOSC |
| System status — battery + RAM in chatbox | VRCNext |
| **Connections tab (NEW in 2.1)** | |
| Connect to VRCX via its WebSocket server (live events, friend join/leave announces in chatbox) | VRCX |
| OSC listener — see the live wire traffic between VRChat and all your apps (VRCX/VRCOSC/MCB all speak OSC) | all five |
| App detection — scan which of the five apps are running and whether VRCX's port is open | all five |
| AI Chat with relay to chatbox (ghost persona) | Bas44 NPC project |

The full apps stay separate installs (they're excellent — this hub covers the parts you use daily in one window).

## Install (Windows)

1. Install Python 3.8+ ([python.org](https://www.python.org/downloads/), check "Add to PATH").
2. Download `vrchub.py`.
3. Double-click it, or run:

```
python vrchub.py
```

Works on Linux/macOS too (window-title media detection and autodetect are Windows-only).

## Setup

- **Chatbox / Params / Media**: enable OSC in VRChat — Settings → OSC → ON (port 9000). Nothing else needed.
- **VRChat API tab**: log in with your VRChat username/password (+ 2FA code if enabled). The session cookie is saved locally in `vrchub_config.json` — your password is never stored, and everything only ever talks to VRChat's own API. (2FA must be an authenticator-app code, not email/SMS.)
- **Avatar equip**: select an avatar in the list and hit "Equip selected" — it swaps in-game, just like VRCX hot-swap.
- **Twitch**: type a channel name, Connect. Anonymous read-only; messages optionally relay to your chatbox.
- **HypeRate**: enter the join code shown in the HypeRate phone/watch app, Connect. BPM shows in the window and optionally in your chatbox.
- **Connections tab**: 
  - In VRCX open Settings → WebSocket Server, enable it (default port 9739), set a token, then enter host/port/token here and Connect. You'll see live VRCX events in the log; friend joins/leaves can be announced automatically in your chatbox.
  - OSC listener: pick a free UDP port (VRCX uses 9001, so try 9002 to avoid clashing) and hit Listen — every OSC message flying between VRChat and your other apps shows up live.
  - App detection: Scan shows which of the tools are running right now.
- **Launcher**: hit "Autodetect" or paste paths; they're saved to `vrchub_config.json`.

## Notes

- VRChat API calls are rate-limited by VRChat — hit refresh, don't spam.
- If the API session expires, the tab says so; just log in again.
- The AI endpoint is a small free service; if it's down, the chat says so.
- `vrchub_config.json` holds your settings/session — delete it to reset everything.

## Credits

Standing on the shoulders of [VRCX](https://github.com/vrcx/VRCX), [VRCOSC](https://github.com/vrcx/VRCOSC), and [MagicChatbox](https://github.com/you-need-to/MagicChatbox) — install them too, they're free. The AI ghost runs on a tiny endpoint built with Base44.

## License

MIT — see [LICENSE](LICENSE).
