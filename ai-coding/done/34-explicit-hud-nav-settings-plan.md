# Make HUD/nav settings explicit + documented in every config

## Motivation

The user hit a confusing bug: `hud: on` (content) did not make the HUD stay
shown, because the *separate* `show-hud-on` trigger defaulted to `controller-nav`
(hide on mouse selection). Two orthogonal settings, one silently defaulted.

Goal: the two HUD "nav" settings must be **explicit in every real surface
config**, each documented in-place with all alternatives, and the fallback
default must be "HUD shown" (never silently hidden).

## The two settings (scope of "nav options")

- **`hud`** — *content*: `on` | `device_only` | `off`
- **`show-hud-on`** — *when it appears*: `selection` | `controller-nav`

(`remote_on`, `feedback`, `outputs` are not HUD/nav knobs and are out of scope.)

"Shown at all times" maps to `show-hud-on: selection` — the HUD follows Live's
selected device (mouse or controller). Note it is not literally always-visible:
the app-view listeners still HIDE on browser/arrangement navigation and the
panel auto-dismisses on inactivity. `selection` is the "always follow the
focused device" option; there is no "never hide" flag.

## Design — hard-required (user's choice)

User chose **hard-required**: a config missing `hud` or `show-hud-on` fails.
User also chose **`hud: on` everywhere** (visibility *and* content), so ec4 moves
from `device_only → on`.

1. **`hud` + `show_hud_on` become required** on `RootV2ModesOrModeless` (remove
   their defaults). `read_root` gets a pre-check on the raw dict that raises a
   friendly `GenError` listing the missing key(s) + allowed values (better than
   Pydantic's bare "Field required"). This fires for every `read_root` caller —
   ~30 test fixtures build off a few shared bases (`_BASE`, `_ROOT_BASE`,
   `_root_with_mapping`, `_two_modes`), patched once each.
2. **No fallback default toward hidden anywhere.** `RootV2.show_hud_on` default
   → `Selection` and `gen.py:119 generate_code_as_template_vars` default
   `hud_trigger` → `Selection` (all default sites err toward shown, per review).
3. **Document + set explicitly in every real config** with `hud: on` +
   `show-hud-on: selection`.

## Config format update (review)

Only the *active* value line can't carry a trailing comment; the commented
alternative lines are pure comments and can, which matches the user's "a comment
after the line" better than a detached legend:

```
# HUD content — what the HUD shows:
hud: on
#hud: device_only   — only the focused device's params; other cells blank
#hud: off           — HUD disabled

# show-hud-on — when the HUD appears:
show-hud-on: selection
#show-hud-on: controller-nav   — only a controller device-nav action shows it; mouse/track selection stays hidden
```

## Config format (NestedText — full-line comments only)

Trailing comments corrupt the value (`hud: on # x` → `'on # x'`), so: active
value uncommented, alternatives commented-out value lines, a per-value legend as
comment lines. Applied uniformly:

```
# HUD content — what the HUD shows. Uncomment exactly one:
#   on          every mapped cell shows its label (dials + buttons)
#   device_only only the focused device's params; other cells blank
#   off         HUD disabled
hud: on
#hud: device_only
#hud: off

# show-hud-on — when the HUD appears. Uncomment exactly one:
#   selection      follow Live's selected device; shows on any device
#                  change, mouse or controller (HUD stays with you)
#   controller-nav only a controller device-nav action shows the HUD;
#                  mouse/track selection stays hidden
show-hud-on: selection
#show-hud-on: controller-nav
```

## Files

Configs (set `show-hud-on: selection` everywhere = user's "always shown"; keep
each file's existing `hud` value but make it explicit + documented):
- `live_surfaces/launch_control/ck_launch_control_16.nt` — has `hud: on`, add trigger block.
- `live_surfaces/grid/ck_grid.nt` — has `hud: on`, add trigger block.
- `live_surfaces/ec4/ck_ec4.nt` — `hud: device_only` (keep, document); **remove
  dead `shift_dismisses_hud: true`** (silently ignored — not a model field).
- `live_surfaces/parks/ck_parkstool_buttons.nt` — already `show-hud-on: selection`;
  make `hud` explicit + apply the documented format.
- `live_surfaces/lc_parks/lc_parks.nt` — composition config, no HUD fields; the
  compositor already force-sets Selection in gen.py. Leave, or add a comment
  pointing to the primary. (Leave.)

Model / codegen:
- `model_v2.py` — flip `show_hud_on` default to `Selection`; add
  `require_explicit_hud` to `read_root` + `build_validated_model`; raise on
  missing keys when set.
- `gen.py` — `generate()` and `generate_composition()` pass
  `require_explicit_hud=True`.

Tests:
- `test_show_hud_on.py` — update the two default-assertion tests to expect
  `Selection` (new default). Add: `read_root` lenient when keys absent;
  `build_validated_model(require_explicit_hud=True)` raises listing the missing
  key(s).
- Verify `test_gen.py::test_emits_compositor_and_forwarder` still passes (it
  generates the real lc_parks → launch_control/parks, which now carry the keys).

## Out of scope / not done

- Not hard-requiring the Pydantic fields (would break ~30 minimal fixtures that
  legitimately don't test HUD). Enforcement lives at the generate boundary.
- Not adding `extra='forbid'` to `RootV2ModesOrModeless` (would catch typos like
  `shift_dismisses_hud` but is a broader change; the dead key is removed by hand).
