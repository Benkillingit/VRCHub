# VRCHub

**Your VRChat toolkit in one place.** A single-file, stdlib-only Python app that takes the feature set of VRCX, VRCNext, VRC-NEXUS, VRCOSC and MagicChatbox and combines it into one lightweight window. No dependencies, no installer.

## Features by category

<details open><summary><b>Chat & communication</b></summary>

- Chatbox with typing indicator, quick replies, scheduled messages (VRCOSC / MagicChatbox)
- Mic-to-chatbox dictation + speech translation (Windows built-in speech)
- Auto-translate typed messages (8 languages, free, no key)
- Phone keyboard — type on your phone into VRChat (local web page)
- Media now-playing (Spotify/window title), lyrics sync, Twitch chat relay, AI relay chat
- AFK auto-responder, cycling message lines, status presets

</details>

<details><summary><b>Avatar & parameters</b></summary>

- My avatars list + one-click hot-swap equip; public avatar search
- Avatar vault: wear-time tracking + memos, cloud-synced to your private GitHub repo
- Parameter control (bool/int/float), gesture quick-fire, param presets, param smoothing
- Rules engine: IF param =/>/< value THEN chatbox or param action
- World OSC console (Udon parameters), OSC router echo

</details>

<details><summary><b>Social & presence</b></summary>

- VRChat login (username/password + TOTP 2FA), online friends with status + world
- Friend join/leave alerts (chatbox + VRCX relay), favorite-friend status
- Block/mute tools, Discord Rich Presence
- Face tracking (webcam -> VRChat FT params; optional opencv + mediapipe)

</details>

<details><summary><b>Hardware & smart home</b></summary>

- HypeRate heart rate -> chatbox (WebSocket)
- Ambilight: screen light sync for Tuya bulbs (optional Pillow + tinytuya)
- Dynamic UI color-shifting

</details>

<details><summary><b>Desktop & convenience</b></summary>

- Launcher: VRChat / VRCX / VRCOSC / MagicChatbox, autodetect, launch-all
- Hardware stats in chatbox, stopwatch, banner slot, movement nudge sliders
- Manual-only update check (never phones home), one-click installers (install.bat / install.sh)

</details>

<details><summary><b>Extend it</b></summary>

- Plugin system: drop a .py in plugins/, get a new panel (see PLUGINS.md)
- Config lives in vrchub_config.json; DOCS.md covers everything

</details>

<details><summary><b>Full version history (changelog)</b></summary>

### Feature map — where each feature comes from

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
| **NEW in 5.9 — VRCNext parity** | |
| Full VRCNext feature sweep: profile editor (status/bio/pronouns/languages), VRChat messenger (invite/response/requestInvite), instance creator + self-invite + multi-friend invites + join-friend's-world, "who is with me", friend request/unfriend/mutuals, groups (list/search/join/leave), VRC+ gallery management, local playtime stats (time per world, time with each friend) + timeline; avatar list now shows PC/Quest + CURRENT badges; launcher adds SlimeVR/VRCVideoCacher/VRCFaceTracking | VRCNext |
| **NEW in 5.7** | |
| Discord Rich Presence (stdlib IPC, JSON frames, own App ID) - status on your Discord profile; Rules engine - IF param ==/>/< value THEN chatbox or param action, saved in config | user request |
| **NEW in 5.6** | |
| Phone keyboard (local web page on your phone -> VRChat chatbox, same WiFi), param smoothing (OSCmooth-style), movement nudge sliders (/input/, OSCLeash-style) | ecosystem sweep 3 |
| **NEW in 5.5** | |
| One-click setup: `install.bat` (Windows) / `install.sh` checks Python, installs all optional extras (Pillow, tinytuya, face-tracking on demand), creates plugins folder | user request |
| **NEW in 5.4** | |
| Voice suite — mic to chatbox (built-in Windows speech), speech + typed auto-translate (free, no key), OSC router echo with delay (OscGoesBrrr-style) | ecosystem sweep 2 |
| **NEW in 5.3** | |
| Community plugin system — anyone can add features: drop a .py in plugins/, panel appears in a Plugins tab; PLUGINS.md guide + template for contributors | user request |
| **NEW in 5.2** | |
| Chatbox animations (wave/bounce/typewriter/pulse), per-avatar param profiles, accept/hide invites + friend requests, time-spent-with-friends tracker | ecosystem sweep |
| **NEW in 5.1** | |
| Lyrics in chatbox (LRCLIB sync), social status presets, live VRChat server-status check, activity heatmap (day x hour) | ecosystem sweep |
| **NEW in 5.0** | |
| World OSC console — see and talk to OSC-enabled worlds (Popcorn Palace style): /world/ filter, double-click a line to load its address, send values back | user request |
| **NEW in 4.9** | |
| Banner slot — slim top bar with your text + clickable link, off by default, toggled + configured in Extras | user request |
| **NEW in 4.8** | |
| Dynamic UI toggle — whole window tints to the game's screen color (dark blend, easy on eyes) | user request |
| **NEW in 4.7** | |
| Screen light sync (Ambilight) — room bulb color matches the game screen; works with Tuya-based Geeni bulbs | user request |
| **NEW in 4.6** | |
| Desktop overlay — always-on-top mini window (clock, status, quick chatbox send) | MagicChatbox-style |
| Remaining official input endpoints (Spin, QuickMenu toggle) + VR compatibility notes | VRChat OSC |
| **NEW in 4.5** | |
| Search ALL sources — one search across VRChat public DB (popularity sort), your avatars, local vault + cloud vault | user request |
| **NEW in 4.4** | |
| CLOUD DATABASE — avatar vault syncs to a private GitHub repo, access anywhere, any PC | user request |
| **NEW in 4.3** | |
| Unlimited local avatar vault — save/equip/delete avatars, no VRChat favorite-slot limit | user request |
| Login accepts VRChat username OR email | user request |
| **NEW in 4.2** | |
| VRChat native input controls — Run, Walk, Comfort turn, Drop, Grab, Use, Voice, Panic (official /input/ endpoints) | VRChat OSC |
| Switch avatar by avtr_ ID via OSC — no login needed | VRCX-style |
| **NEW in 4.1** | |
| Face tracking tab — webcam blendshapes to VRChat FT params (optional pip deps) | VRCFT-style |
| **NEW in 4.0** | |
| Full documentation — DOCS.md (tutorial, every tab, troubleshooting) | |
| In-app Help tab with quick start | |
| Countdown timer in chatbox | |
| Scheduled chatbox messages (send later) | |
| **NEW in 3.3 — more from the trackers** | |
| Clock in chatbox | VRCOSC (clock module) |
| Media + hardware stats combined in one chatbox line | VRCOSC (most-commented request) |
| "Only announce on track change" media option | VRCOSC (feature request) |
| Fixed: Extras panel overlap bug (PiShock log) | |
| **NEW in 3.2 — top-voted user requests from all five apps' GitHub trackers** | |
| Avatar wear-time tracking | VRCX (7👍) |
| Avatar memos (your notes per avatar) | VRCX (6👍) |
| Friend watch — chatbox alert when a friend goes offline / changes world | VRCX (13👍) |
| Block / mute / unmute buttons (with confirm) | VRCX (5👍) |
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

</details>

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
