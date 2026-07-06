# Operator paging / stale-index bug

## Symptom

Switching device (e.g. Wavetable → Operator) sometimes opened the new device's
HUD burst on the **previous** device's encoder page and name index — "Operator
burst opened on page 4 with Wavetable's index." Two distinct mechanisms fed it.

## Mechanism 1 — dead Live parameter handle (self-heal, pre-existing)

The name indices cached the *parameter object*. Devices that rebuild their
parameter list in place (Live 12.4 Operator, as oscillators/filters toggle) leave
a cached object as a dead Boost.Python handle that raises `ArgumentError` (a
`TypeError` subclass, so `getattr` defaults don't shield it) on any access.

**Fix (`param_resolver.py`):** cache name → *integer index* into
`device.parameters`, and re-fetch the live entry by index in `_live_param`,
revalidating against `original_name` / `name`. If the list reordered/resized so
the cached index no longer matches — or is dead — rebuild the index once and
retry. `_attr` treats a dead-handle read as "absent" rather than raising.
Regression tests: `test_resolve_refetches_live_param_after_handle_swap`,
`test_resolve_rebuilds_index_when_list_reordered`.

## Mechanism 2 — funnel bypass leaves paging/index stale (this change)

The self-heal repairs the *index*, but per-device **paging** (`encoder_page`,
`button_page`) is reset only by `ParameterResolver.focus()`, called from the
`Helpers.selected_device_changed` funnel. A burst assembled for a device the
funnel never reset (a bypassed selection path — the exact path was left
un-instrumented; we took the defensive fix over capture-to-diagnose) inherits the
previous device's page.

**Fix — make the burst the single source of truth:**
- `ParameterResolver.ensure_focused(device)` — records the focused device; if a
  later call names a *different* device, hard-resets (drop name index + paging to
  page 1). Idempotent on the same device, so live paging (pager, group-selector
  refresh) is never disturbed.
- `HudPresenter.emit_burst` calls `ensure_focused(device)` at the top — the one
  burst-assembly chokepoint every burst path funnels through. Any burst for a
  device the funnel skipped self-corrects its index + page.
- `Helpers.selected_device_changed` calls `ensure_focused` (was `focus()`) so the
  same-device guard's device is recorded and the emit_burst guard no-ops on the
  normal path; the reset still runs before group-selector listeners re-attach.

Tests: `test_ensure_focused_resets_on_device_change`,
`test_ensure_focused_is_noop_on_same_device` (resolver),
`test_emit_burst_resets_paging_for_new_device_bypassing_funnel` (presenter).

## Deliberately NOT done

- **`refresh_hud_for_mode` funnel routing.** A bare `_last_selected_device`
  assignment there is safe: `refresh_for_mode → emit_current_burst → emit_burst`
  runs `ensure_focused`, so a changed device's index/page still reset. Routing it
  through `selected_device_changed` would add a `source='selection'` DeviceFocus
  that fires a HIDE→re-show churn in controller-nav mode — untested behavior for
  no benefit to the reported bug.
- **Group-selector listener re-attach** on a simultaneous mode+device change is
  the only residual; it self-heals on the next real selection. Follow-up if it
  ever bites in practice.

## Diagnostics

The three always-on `[idx]` / `[focuschg]` TEMP diag traces added for
capture-to-diagnose are removed now that the defensive fix lands.
