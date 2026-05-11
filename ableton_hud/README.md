# AbletonHUD

Native macOS floating overlay that shows the current Ableton Live device's mapped parameters whenever Ableton is in focus.

**Data flow:** Ableton Live → [ableton_control_suface_as_code](../ableton_control_suface_as_code) Python surface → UDP `:5006` → AbletonHUD overlay

The HUD is a dumb renderer. All protocol logic, controller layout, and parameter resolution lives in the sibling repo. See [`source_modules/hud_client.py`](../ableton_control_suface_as_code/source_modules/hud_client.py) there for the full wire protocol.

## Build & run

```bash
./create-app-bundle.sh   # build + bundle
open AbletonHUD.app

# During development
pkill -f AbletonHUD; sleep 0.5; open AbletonHUD.app

swift test               # unit tests
```

Requires macOS 13+.
