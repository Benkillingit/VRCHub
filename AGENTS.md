# AGENTS.md — working on VRCHub in the Base44 sandbox

## What this project is

`vrchub.py` is a single-file, stdlib-only **Tkinter desktop app** (~6,200 lines).
There is no build step, no package manifest, no pip dependency, and no web
server of its own. It talks to VRChat over OSC/UDP and the VRChat web API.

## Running it here

Because it is a desktop GUI, the sandbox runs it on a virtual display and serves
that display to the browser preview:

```
Xvfb :99  ->  x11vnc (localhost:5900)  ->  websockify/noVNC on host port 3000
```

```bash
docker compose -f docker-compose.base44.yml up -d --build   # start
docker compose -f docker-compose.base44.yml logs -f vrchub  # (little output; see files below)
```

- Entry point for the preview: `http://localhost:3000/` → redirects to
  `/vnc.html?autoconnect=1&resize=scale` (the raw noVNC client, `vnc.html`, also
  works directly).
- `.base44/start.sh` boots the four processes above and is the compose command.
  `Dockerfile.base44` installs OS packages only — the repo is bind-mounted, so
  **edits to `vrchub.py` never need a rebuild**.
- Tkinter has no hot reload, so `.base44/start.sh` watches the md5 of
  `vrchub.py` and restarts the app within ~1s of a change. Touching the file
  without changing its content does not restart it.
- Runtime logs live inside the container (they are not in the repo):
  `docker compose -f docker-compose.base44.yml exec vrchub sh -c 'tail -50 /tmp/vrchub.log'`
  — also `/tmp/xvfb.log`, `/tmp/x11vnc.log`, `/tmp/novnc.log`.
  A healthy start leaves `/tmp/vrchub.log` empty.

## Configuration, data and secrets

- **No environment variables or secrets are required to boot.** The app is
  stdlib-only and validates nothing at startup, so the sandbox runs with none.
- Writable app data goes to `$HOME/VRCHub` (`_data_dir()` in `vrchub.py`):
  `vrchub_config.json`, `vrchub_activity.json`, `plugins/`. In the sandbox that
  is the named volume `vrchub_data`, so settings survive container restarts.
  Never point `HOME` at the repo — config would show up as untracked files.
- Optional third-party credentials (GitHub token for the cloud avatar vault,
  Pulsoid token, Base44 report token) are typed into the app's own UI and saved
  in the config. They are not env vars, so do not add them to compose or to the
  secrets schema.

## Verifying a run

```bash
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:3000/vnc.html   # 200
docker compose -f docker-compose.base44.yml exec -T vrchub sh /app/.base44/healthcheck.sh
```

The compose healthcheck runs exactly that script: it checks the noVNC HTTP
endpoint **and** that a VRCHub window exists on the X display (via
`xwininfo -root -tree -display :99 | grep -i vrchub`), so it fails if the GUI
process dies while noVNC stays up. It prints which half failed.

There is no test suite in this repo; the checks above plus a look at the preview
are the verification.

## Non-obvious quirks

- **UTF-8 locale is mandatory.** Without `LANG=C.UTF-8`/`LC_ALL=C.UTF-8`, X
  cannot convert the window title (it contains an em dash) and `xwininfo` prints
  `(failure in conversion from UTF8_STRING to ANSI_X3.4-1968)` — which also
  breaks the healthcheck's window-title match. The compose service sets both.
- `novnc-index.html` is copied over `/usr/share/novnc/index.html` at startup so
  the preview root serves a landing page instead of a directory 404.
- Most features are inert in the sandbox: there is no VRChat client sending OSC
  and no VRChat account, so panels render but report "not connected". That is
  expected, not a bug — don't "fix" it by stubbing network calls.
- Windows-only paths (`xdg-open` fallbacks, `wmic`, TOTP dictation) are already
  guarded in the source; leave them alone.
