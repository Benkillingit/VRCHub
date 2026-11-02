# Testing VRCHub without VRChat

VRChat itself needs Windows, a GPU and about 40 GB, so the test suite fakes
VRChat's side of the conversation. Every check below runs headless and never
touches your real config: the probes write to a throwaway folder.

## What the probes cover

| Probe | What it proves |
| --- | --- |
| `probe/mock_vrchat_osc.py` | 30 unit checks: OSC encoding, avatar/world ID validation, event ordering, wildcard expansion, safe degradation when Windows-only modules are missing |
| `probe/click_test.py` | Clicks the real Tk widgets in a live window and asserts the packets VRChat would receive (`/chatbox/input`, `/input/MoveX`, `/input/MoveY`, notes) |
| `probe/handler_test.py` | Calls handlers with empty/garbage input; asserts the VRCNext+ profile Apply reaches the API with all five fields and that nothing raises |
| `probe/plugin_test.py` | Drops a real plugin plus a deliberately broken one into a temp data dir, rescans, asserts the panel renders, `init()` runs, the plugin's button emits OSC, and the broken one is reported in red instead of crashing |
| `probe/tab_probe.py` | Plugins tab prints the folder it actually scans; Face Track refuses politely when `opencv-python`/`mediapipe` are absent |
| `probe/inventory.py` | Every tab still has its controls (catches a tab that silently lost a button) |
| `probe/fuzz_buttons.py` | Invokes every non-destructive button in every tab; skips file dialogs and anything that deletes data |
| `probe/static_audit.py` | Static pass: attributes read but never assigned, `self.foo()` calls with no definition, `self.api.*`/`self.osc.*` calls that do not exist |
| `probe/drill.py` | Layout: measured minimum width of all 14 tabs against a 1360 px window |

## Running them

Linux, headless:

```bash
Xvfb :99 -screen 0 1600x1000x24 &
DISPLAY=:99 python3 probe/mock_vrchat_osc.py
DISPLAY=:99 python3 probe/click_test.py
DISPLAY=:99 python3 probe/handler_test.py
DISPLAY=:99 python3 probe/plugin_test.py
DISPLAY=:99 python3 probe/tab_probe.py
DISPLAY=:99 python3 probe/inventory.py
DISPLAY=:99 python3 probe/static_audit.py vrchub.py
```

Windows: just `python probe\click_test.py` in a normal desktop session. Each
script prints `RESULT: PASS` or `RESULT: FAIL` and exits non-zero on failure.

`fuzz_buttons.py` runs one tab per process to keep a modal file dialog from
blocking the sweep:

```bash
FUZZ_TAB=13 python3 probe/fuzz_buttons.py   # 0..13
```

## Known limits

- The mock cannot check whether VRChat *accepts* a parameter name; only a
  real avatar in a real world proves that.
- Windows-only paths (mic dictation, crash guard, TinyTuya light sync) are
  exercised for graceful failure on Linux, not for real behaviour.
- Rendering differences on Windows (DPI scaling, fonts) still need a human
  eyeball.
