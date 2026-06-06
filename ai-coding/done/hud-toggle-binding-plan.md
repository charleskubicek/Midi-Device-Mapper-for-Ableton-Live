# Plan: `hud_toggle` binding — replace `shift_dismisses_hud`

## Why
`shift_dismisses_hud` hides the HUD while shift is held, but shift enters a mode with
*different* button values the user needs to read off the HUD — it removes the readout
exactly when it's most needed. Decision: **remove it entirely** and replace the use case
with an explicit, on-demand dismiss the user binds to a spare button.

The HUD already has three dismiss paths (auto-dismiss timer, sticky `HIDE` on
navigate-away, Esc key). The only gap is an intentional dismiss *from the controller*.
This adds that as a reserved `functions: hud_toggle` action.

## Part A — Remove `shift_dismisses_hud`
- `ableton_control_surface_as_code/model_v2.py`: drop the field from `RootV2` (~L107),
  `RootV2ModesOrModeless` (~L123), and the pass-through in `buildRootV2` (~L137).
- `ableton_control_surface_as_code/gen.py`: remove the `shift_dismiss_hud_call` var (~L331).
- `templates/surface_name/modules/main_component.py`: remove the two `$shift_dismiss_hud_call`
  lines + their comments in `mode_button_listener` (~L238-246). The listener keeps its
  `goto_mode` / `send_mode` behavior.
- `tests/test_shift_dismisses_hud.py`: delete.
- Grep `live_surfaces/**/*.nt` for `shift_dismisses_hud:` and remove any usages (flag to user
  if found — those configs lose the behavior).

## Part B — Add `hud_toggle` reserved builtin function
Route `functions: hud_toggle` to a built-in method on `main_component` (which holds
`_hud_client` + `_helpers`), NOT to the user's `functions.py` class.

1. **Reserve the name.** In `model_functions.py` add
   `RESERVED_BUILTIN_FUNCTIONS = {'hud_toggle'}` and a `builtin: bool = False` field on
   `FunctionsMidiMapping`.
2. **Skip user-file lookup.** In `build_functions_model_v2`: if `fn in
   RESERVED_BUILTIN_FUNCTIONS`, skip `FunctionLookup.inspect_python_file` (it would raise —
   the fn isn't in functions.py), set `parameter_len=0`, `builtin=True`.
3. **Emit a builtin call.** `FunctionsMidiMapping.template_function_call()`: if `builtin`,
   return `self.hud_toggle()` (no `self.functions.` prefix); else unchanged.
4. **Press-only guard.** In `gen_code.py` `button_listener_function_caller_templates`,
   compute `toggle = enc_refs.has_toggle() or getattr(midi_map, 'builtin', False)` so the
   builtin fires only on press (value 127), not on release — otherwise it flips twice per
   press and nets zero.
5. **The builtin method + state.** In `templates/surface_name/modules/main_component.py`:
   - init `self._hud_dismissed = False` in `__init__`.
   - add:
     ```python
     def hud_toggle(self):
         self._hud_dismissed = not self._hud_dismissed
         if self._hud_dismissed:
             self._hud_client.send_hide()
         else:
             # re-burst clears the HUD's sticky dismissed flag and repopulates labels
             self._helpers.refresh_hud_for_mode(self.current_mode['name'], self.selected_device())
     ```
   `current_mode` carries a `'name'` key (set in the generated `_modes` dict).

## Known wart (document, don't fix)
Python tracks dismiss *intent* locally; the HUD's actual visibility can drift (auto-timer,
navigate-away HIDE). If the HUD auto-hid and intent is still "shown", the first toggle press
sends a redundant HIDE and you press again to show. Acceptable for a manual toggle; note it.

## TDD order
1. `tests/test_hud_toggle.py` (new), failing first:
   - `build_functions_model_v2` with `{'hud_toggle': 'row-x:y'}` does NOT raise and yields a
     mapping with `builtin=True`, `parameter_len=0`.
   - generated code for a `hud_toggle` binding contains `self.hud_toggle()` and NOT
     `self.functions.hud_toggle`.
   - the listener uses the press-only guard (`value_is_max(value, 127)`).
2. Implement Part B until green.
3. Part A removal; run full `poetry run pytest` (test_shift_dismisses_hud.py gone).
4. Add the binding to a real surface (`live_surfaces/launch_control/...nt`) only if the user
   wants it wired; otherwise leave configs untouched. Confirm `gen.py` runs clean.

## Out of scope
- HUD app (Swift) changes — none needed; `HIDE` + re-burst already exist.
- Tuning the auto-dismiss timer window.
