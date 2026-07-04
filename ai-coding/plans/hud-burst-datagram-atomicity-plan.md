# HUD burst datagram atomicity

## Problem

A HUD device-focus burst (`LAYOUT → DEVICE → PAGE → SLOT×n → COMMIT`) is emitted as
**N separate UDP datagrams** — `hud_client.py` does one `sendto` per line. Burst
atomicity therefore relies on *every* frame datagram arriving. On loopback UDP is
very reliable but not guaranteed: under receive-buffer pressure (exactly what a
rapid device-switch flurry produces) a datagram can be dropped.

Walking each single-datagram loss against the receiver (`DeviceState.apply`):

| Lost datagram | Result |
|---|---|
| `SLOT` | one blank/stale cell — safe |
| `COMMIT` | stays on previous device — stale but **consistent** — safe |
| `PAGE` | wrong page number — cosmetic |
| **`DEVICE`** | **previous device's name + new device's params** — a real cross-device mix |

`DEVICE` is special: it carries *both* the pending-buffer clear **and**
`pendingName` (`DeviceState.swift`). `COMMIT` publishes `deviceName = pendingName`
assuming `DEVICE` was delivered. Drop `DEVICE-B` and `pendingName` is still `"A"`
from the prior burst, while B's dense `SLOT`s overwrite every index → `COMMIT-B`
publishes **B's parameters under name "A"**. This is the "partial update from
multiple devices" failure. It is the *only* single-loss case that mixes devices.

Likelihood is low (loopback loss is rare; reordering effectively never happens on
loopback), so this is a latent correctness gap, not a routinely-observed bug.

### Explicitly out of scope: the stale-index bug

The observed "Operator burst opened on page 4 with Wavetable's index" is a
**different mechanism** — an assembly-time mix from a funnel bypass where
`focus()` did not run, so the resolver kept the previous device's index/paging.
That is fixed by a `selected_device() != _last_selected_device → focus()` guard,
not by anything on the wire. The `param_resolver.py` self-heal (live re-fetch by
index) already repairs the dead-handle half. Wire hardening does not touch the
stale-index bug and the `focus()` guard does not touch DEVICE-loss. Keep separate.

## Fix: coalesce the whole burst into one datagram

Buffer every line of a burst on the sender and flush as a **single** `sendto` at
commit. Then the burst is datagram-atomic: it all lands or none does. Loss =
"stay on last good device", never a mix.

Receiver-transparent by construction — both receivers already split a datagram on
`\n`:
- Swift `WireProtocol.parseAll` (`components(separatedBy: "\n")`)
- Python `hud_protocol.parse_all` (region path via `region_state.handle_data`)

The **only** receiver-side change is the read-buffer size. Both read buffers are
4096 bytes today (`UDPListener.swift` recv loop; `region_listener.py` recvfrom). A
coalesced burst — especially the `lc_parks` combined stream — can exceed 4096 and
a UDP datagram over the read length is **truncated**, dropping the trailing
`COMMIT`. Bump both to 65536. Burst size is bounded by *physical controller slots*
(not device parameter count), so it stays a few KB — comfortably under the
loopback datagram limit.

### Send-side cap (measured)

A single `sendto` is also OS-capped: `net.inet.udp.maxdgram` = **9216** on macOS.
Over it, `sendto` raises `EMSGSIZE`, which the client's `except` would swallow →
the whole burst silently dropped (a *worse* failure than the mix this fixes).
Measured budgets: lc_parks primary layout = 16 dials + 16 buttons = 32 slots
(~1.3KB); the appended parks region brings the combined burst to ~48 slots
(~3KB) — comfortable ~3× headroom under 9216. To stay provably "never worse than
before" for any config, `flush_burst` degrades to per-line datagrams (the old
behavior) above an 8192-byte threshold instead of risking `EMSGSIZE`.

## Changes

### Sender
- `source_modules/hud_client.py`
  - Add `_burst_buffer` (None = pass-through). `_send` appends to the buffer when
    buffering, else emits immediately via a single `_sendto` chokepoint.
  - `begin_burst()` starts buffering; `flush_burst()` joins the buffer and emits
    it as one datagram (no-op on empty; per-line fallback above `_max_datagram`
    = 8192 so an oversized burst is delivered non-atomically, never dropped).
  - Mirror `begin_burst` / `flush_burst` no-ops on `NullHudClient`.
- `source_modules/helpers.py` `Remote.refresh_burst`
  - Wrap the burst body: `begin_burst()` before, `flush_burst()` in the `finally`
    beside `_in_burst = False`. Suppressed bursts buffer nothing → flush no-ops.

### Receiver
- `ableton_hud/Sources/AbletonHUD/UDPListener.swift` — recv buffer 4096 → 65536.
- `source_modules/region_listener.py` — `recvfrom(4096)` → `recvfrom(65536)`.

### Diagnostics cleanup (bundled)
- Strip the three `TEMP diag (operator-paging-dead-param-plan)` traces
  (`param_resolver.py` ×2, `helpers.py` ×1). The `param_resolver.py` self-heal and
  its two regression tests stay.

## Tests

- `tests/test_hud_client.py`
  - Burst between `begin_burst`/`flush_burst` → exactly **one** datagram
    containing all lines, `\n`-terminated, in order (fake socket capturing
    `sendto`).
  - Outside a burst, each `send_*` is its own datagram (pass-through unchanged).
- `tests/test_helpers.py`
  - `refresh_burst` calls `begin_burst` then `flush_burst` exactly once around the
    wire sends (burst-atomic wrapping), including the `suppress_hud` path.
- Swift `WireProtocolTests` — a coalesced multi-line burst string through
  `parseAll` yields the messages in order and applying them commits correctly
  (receiver-transparency of coalescing, no socket needed).

## Rollout

Spans sender + HUD app: regen affected surfaces, redeploy, rebuild/restart the
HUD. User runs deploy + Ableton restart.
