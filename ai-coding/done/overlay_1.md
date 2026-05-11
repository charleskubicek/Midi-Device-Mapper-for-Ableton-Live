# Ableton HUD — native macOS overlay for the selected device's mappings

## Context

The user already generates Ableton control surfaces from `.nt` config files in `ableton_control_suface_as_code` (ACSAC). When a device gets focus in Ableton, ACSAC publishes the mapped parameters over OSC — but there's no on-screen confirmation of which knob/button does what. They want a transparent floating HUD that briefly appears over Ableton showing the 8 dials + 8 buttons of the Launch Control XL with the parameter names that ACSAC has resolved for the current device. This makes the slot/family system (`slot1..slot8`, `switch1..switch8`) visible as a glanceable overlay rather than something only the controller knows about.

The companion `live-shortcuts/AbletonShortcuts` project already solves the macOS-overlay-over-Ableton problem and is the reference design — both for the AppKit/SwiftUI overlay pattern AND for the Python↔Swift wire protocol (see `live-shortcuts/AbletonShortcuts/control_script/shortcuts/udp.py`).

## Approach

A new sibling Swift Package at `/Users/ck/current/ableton_hud` that listens on a UDP port for the selected-device's mapping data — pushed from ACSAC whenever device focus changes. **No NestedText parsing in the HUD.** The Python side already has the resolved mapping (slot index → parameter name) at generation/runtime, so it sends everything the HUD needs: device name + 8 dial slots + 8 button slots. The HUD is a dumb renderer.

**Protocol: a tiny line-based pipe-delimited UDP protocol**, modeled directly on `AbletonShortcuts/control_script/shortcuts/udp.py` rather than OSC. Newline-terminated, UTF-8, `COMMAND|arg1|arg2|...`. Reasons:
- AbletonShortcuts already proved this pattern works inside Ableton's Python sandbox without external deps.
- Avoids inventing/maintaining an OSC parser in Swift (~80 LOC saved) and avoids the OSC type-tag/4-byte-alignment fiddliness for what is basically a string blob.
- The HUD only needs one-way push; no need for OSC's address-pattern matching.

### Feedback and testing
- Build a very simple fake ableton live simulator in Python that emits events to the HUD's UDP port
- Allow the state of the app to be inspected via logs and/or a debug menu in the HUD, to confirm it's receiving and parsing the UDP messages correctly
- Allow the app to be resetarted with a script that kills the process and restarts it, to speed up testing during development


## Wire protocol

UDP `127.0.0.1:5006`. Each datagram is one ASCII line, `\n`-terminated, fields separated by `|`. The Python sender emits a burst per device-focus event:

```
DEVICE|<deviceName>
SLOT|dial|<0..7>|<paramName>|<value>|<min>|<max>
SLOT|button|<0..7>|<paramName>|<value>|<min>|<max>
...
COMMIT|<slotCount>
```

- `DEVICE` always comes first and resets HUD state (clears all 16 slots).
- `SLOT` lines may come in any order; missing indices stay empty.
- `COMMIT` is the atomic-swap signal: HUD renders the just-built frame.
- Empty fields are allowed (`SLOT|dial|3|||0|1` for an unmapped slot — though typically the sender just omits unmapped slots).
- Unknown commands are ignored (forward-compat).

Stale-burst handling: each `DEVICE` line increments a generation counter; `SLOT` lines arriving after a newer `DEVICE` are coalesced into the new burst (they came in-order on the same UDP socket from the same sender, so reordering between bursts is not a concern in practice — but the HUD still keys updates by the latest `DEVICE` to be safe).

## Scope of changes

### 1. ACSAC (Python): emit the new protocol on device focus

**File:** `ableton_control_suface_as_code/templates/surface_name/modules/main_component.py:43-46`

Add a HUD client. Two viable shapes — pick whichever is less invasive:

**Option A (preferred):** keep `OSCMultiClient` for the existing two destinations and add a second tiny side-channel object that emits the new pipe protocol over UDP to `127.0.0.1:5006`. This keeps the OSC schema untouched for any other listeners on `:5005`.

**Option B:** repurpose port 5006 to speak the new protocol only (HUD-specific), still alongside the existing OSC traffic on 5005.

A new `source_modules/hud_client.py` (~40 LOC) wraps `socket.SOCK_DGRAM`:
- `send_device(name)` — emits `DEVICE|name\n`
- `send_slot(kind, index, name, value, vmin, vmax)` — emits `SLOT|...\n`
- `commit(count)` — emits `COMMIT|count\n`
- All sends wrapped in `try/except` (mirror `OSCClient.send_message` at `source_modules/helpers.py:534-538`) so an absent HUD listener never stalls Ableton's main thread.

The hook point is the same place ACSAC currently emits `/selected-device/parameter-update*`. The Python side already knows, for each parameter index, whether it's mapped to a dial slot (`slot1..slot8`) or a button slot (`switch1..switch8`) — that mapping is what gets translated into `SLOT|dial|i|...` vs `SLOT|button|i|...` lines. The HUD does not need to know about MIDI, controller layout, or the `.nt` file at all.

After patching, regenerate (`poetry run python ableton_control_surface_as_code/gen.py live_surfaces/launch_control/ck_launch_control_16.nt`) and `./deploy.sh`.

### 2. New repo: `/Users/ck/current/ableton_hud`

**Structure:**
```
ableton_hud/
├── Package.swift
├── Sources/
│   └── AbletonHUD/                   # @main executable (LSUIElement)
│       ├── AbletonHUDApp.swift
│       ├── HUDOverlayManager.swift
│       ├── HUDView.swift
│       ├── DeviceState.swift         # ObservableObject
│       ├── UDPListener.swift         # Network.framework NWListener
│       ├── WireProtocol.swift        # ~50 LOC line/pipe parser
│       └── AbletonFocusMonitor.swift # NSWorkspace notifications
├── Tests/
│   └── WireProtocolTests/
├── create-app-bundle.sh              # adapted from AbletonShortcuts
└── Info.plist                        # LSUIElement=true
```

No `OSCWire/` target. No `NTParser/` target. No file paths to ACSAC. The HUD has zero coupling to ACSAC's repo layout — they only share a UDP port and the protocol described above.

**Reference files** (read these first when implementing):
- `live-shortcuts/AbletonShortcuts/control_script/shortcuts/udp.py` — the protocol shape we're copying
- `live-shortcuts/AbletonShortcuts/Sources/Engine/OverlayManager.swift:187-242` — NSPanel creation pattern
- `live-shortcuts/AbletonShortcuts/Sources/Engine/HotkeyManager.swift:127-148` — NSEvent monitoring
- `live-shortcuts/AbletonShortcuts/create-app-bundle.sh` — bundling
- `live-shortcuts/AbletonShortcuts/Package.swift` — multi-target layout

### 3. Module details

**`WireProtocol.swift`** — splits incoming UDP datagrams on `\n`, then each line on `|`. Returns a typed enum `WireMessage { case device(String); case slot(Kind, Int, Slot); case commit(Int); case unknown }`. Throw/log on malformed numeric fields; don't crash on unknown commands.

**`DeviceState.swift`** (`ObservableObject`):
- `@Published var deviceName: String`
- `@Published var dialSlots: [Slot?]` — fixed length 8
- `@Published var buttonSlots: [Slot?]` — fixed length 8
- where `Slot = (name: String, value: Float, min: Float, max: Float)`
- Pending buffer keyed by `currentGeneration: Int`.

Burst handling:
1. On `DEVICE`: increment generation, clear pending buffer, store name.
2. On `SLOT`: write into `pending[generation][kind][index]`.
3. On `COMMIT`: atomically swap `pending[generation]` → published slots on main actor.
4. Slots not assigned during the burst render as empty placeholders.

**`UDPListener.swift`** — `NWListener` on UDP `127.0.0.1:5006`. For each datagram, decode UTF-8, split on `\n`, feed lines to `WireProtocol` → `DeviceState` on `@MainActor`. Cancel on app quit.

**`HUDOverlayManager.swift`** — direct port of `AbletonShortcuts/Sources/Engine/OverlayManager.swift:187-242`:
- `NSPanel` with `.borderless | .nonactivatingPanel`
- `level = .floating`, `isOpaque = false`, `backgroundColor = .clear`
- `collectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle]`
- Hosts `HUDView()` via `NSHostingController`
- 20% opacity background applied inside SwiftUI
- Esc dismissal: `NSEvent.addLocalMonitorForEvents(matching: .keyDown)` checking `keyCode == 53`
- Show triggers ONLY when `AbletonFocusMonitor.isAbletonFrontmost == true`

**`AbletonFocusMonitor.swift`** — subscribe to `NSWorkspace.shared.notificationCenter` for `didActivateApplicationNotification` / `didDeactivateApplicationNotification`. Match bundle id prefix `com.ableton.live`. Hide overlay immediately when Ableton deactivates.

**`HUDView.swift`** (SwiftUI):
- `RoundedRectangle` background `.fill(Color.black.opacity(0.2))`
- `VStack`:
    - top: `HStack` of 8 dial views (`Circle` + value arc + name `Text` below)
    - bottom: `HStack` of 8 button views (`RoundedRectangle` square + name `Text` below)
- empty slot: dimmed circle/square, no label
- size ~960×280, centered on Ableton's main window via AX API; fall back to screen center

The HUD layout is hardcoded as 8+8 — no config file lookup. If we ever need a different controller, the Python side can send a different number of `SLOT` lines and we'll generalize then.

### 4. Bundling

Adapt `live-shortcuts/AbletonShortcuts/create-app-bundle.sh`: `swift build -c release --product AbletonHUD`, copy binary to `AbletonHUD.app/Contents/MacOS/`, write `Info.plist` with `LSUIElement=true`. No login-item nesting (single executable). No accessibility entitlement required for v1.

## Verification

1. **WireProtocol**: unit tests against hand-crafted byte arrays — `DEVICE|EQ Eight\n`, multi-line bursts, unknown commands, malformed numeric fields.
2. **Burst logic**: unit-test `DeviceState` with synthetic sequences — clean burst, two overlapping bursts (assert second wins), straggler from prior generation (assert dropped or coalesced into the right frame).
3. **End-to-end**:
    - Run `./create-app-bundle.sh && open AbletonHUD.app`
    - Patch `main_component.py` to add the HUD client, regenerate, `./deploy.sh`, restart Ableton.
    - In Ableton, click between two devices on a track that has Launch Control mappings (e.g. an EQ → a compressor).
    - Expect: HUD appears over Ableton each time, shows the device name + dial/button labels resolved by ACSAC, esc dismisses, switching to another app hides it.
    - Confirm via `./bin/tail_logs.sh` that no Python errors fire on the new HUD client.

## Out of scope (v1)

- Settings UI / file picker for the controller path
- Multiple controllers / multiple mode pages
- Live value updates while the user is turning knobs (only on focus change / commit)
- Auto-hide timer (esc-only per user spec)
- Login item / launch-on-boot
- Code signing / notarization
- Two-way protocol (HUD → Ableton). v1 is pure push from ACSAC.
