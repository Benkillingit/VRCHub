# Writing VRCHub plugins

Anyone can add features to VRCHub without touching the core file. A plugin is one `.py` file dropped into the `plugins/` folder next to `vrchub.py`. Hit **Rescan** in the Plugins tab (or restart) and it appears as its own panel.

## Template

```python
NAME = "My Plugin"
VERSION = "1.0"
DESCRIPTION = "What my plugin does in one line."

def init(app):
    """Optional. Runs once when VRCHub starts / rescans."""
    pass

def build(app, parent):
    """Required. Build your UI inside the given frame."""
    import tkinter as tk
    from tkinter import ttk
    ttk.Label(parent, text="Hello from %s!" % NAME).pack()
    ttk.Button(parent, text="Send hi to chatbox",
               command=lambda: app.osc.chatbox("hi from %s" % NAME)).pack()

def on_osc(app, address, args):
    """Optional. Called for every live OSC event from VRChat."""
    pass
```

## What your plugin gets (the `app` object)

- `app.osc` — send OSC: `.chatbox(text)`, `.send("/avatar/parameters/NAME", value)`
- `app.cfg` — the saved config dict (yours + user settings persist via `save_config(app.cfg)`)
- `app.status("msg")` — show a message in the status bar
- `app.api` — VRChat API client (works if the user logged in on the API tab)
- `app.after(ms, fn)` — run something on the UI thread (use this from threads)

## Rules

1. Python stdlib + tkinter only (keep VRCHub dependency-free; import extras inside your functions and fail gracefully).
2. Never crash the app: wrap risky code in try/except. A crashed `build()` just shows an error line in your panel.
3. Don't edit files outside your own; store data in the `plugins/` folder or config keys prefixed with your plugin name.
4. Users install plugins at their own risk — plugins are plain Python, same trust model as VRCOSC modules. Sign your work with your GitHub handle in DESCRIPTION.

## Sharing

Open a pull request adding `plugins/your_plugin.py`. Interesting ones get linked in the README. Bug reports and ideas: GitHub Issues.
