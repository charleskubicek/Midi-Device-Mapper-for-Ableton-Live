import ast
import keyword
from dataclasses import dataclass, field
from string import Template
from typing import List, Tuple

from ableton_control_surface_as_code.core_model import MixerWithMidi, ButtonProviderBaseModel, MidiCoords
from ableton_control_surface_as_code.encoder_coords import EncoderRefinements
from ableton_control_surface_as_code.model_device import DeviceWithMidi, SwitchMidiMapping
from ableton_control_surface_as_code.slots import is_switch_slot
from ableton_control_surface_as_code.model_device_nav import DeviceNavWithMidi
from ableton_control_surface_as_code.model_functions import FunctionsWithMidi
from ableton_control_surface_as_code.model_track_nav import TrackNavWithMidi
from ableton_control_surface_as_code.model_transport import TransportWithMidi


@dataclass
class GeneratedCode:
    array_defs: [(str, [MidiCoords])] = field(default_factory=list)
    init: [str] = field(default_factory=list)
    control_defs: [MidiCoords] = field(default_factory=list)
    listener_fns: [str] = field(default_factory=list)
    setup_listeners: [str] = field(default_factory=list)
    remove_listeners: [str] = field(default_factory=list)
    custom_parameter_mappings: [str] = field(default_factory=list)
    switch_parameter_mappings: [str] = field(default_factory=list)

    def midi_coords_exists_in_control_defs(self, midi_coords: MidiCoords) -> bool:
        return any([c == midi_coords for c in self.control_defs])

    def any_midi_coords_exists_in_control_defs(self, midi_coords: [MidiCoords]) -> bool:
        return any([self.midi_coords_exists_in_control_defs(c) for c in midi_coords])

    def common_midi_coords_in_control_defs(self, other: 'GeneratedCode') -> [MidiCoords]:
        return [c for c in self.control_defs if other.midi_coords_exists_in_control_defs(c)]

    def common_midi_coords_in_any_control_defs(self, other: ['GeneratedCode']) -> [MidiCoords]:
        return [c for c in self.control_defs if any([o.midi_coords_exists_in_control_defs(c) for o in other])]


class GeneratedCodes:
    @classmethod
    def merge_all(cls, codes: [GeneratedCode]) -> GeneratedCode:
        if len(codes) == 0:
            return GeneratedCode()
        else:
            first = codes[0]
            for c in codes[1:]:
                first = cls.merge(first, c)
            return first

    @classmethod
    def common_midi_coords_in_control_defs(cls, one: [GeneratedCode], to: [GeneratedCode]) -> [MidiCoords]:
        listoflists = [o.common_midi_coords_in_any_control_defs(to) for o in one]
        return sum(listoflists, [])

    @classmethod
    def merge(cls, one: GeneratedCode, other: GeneratedCode) -> GeneratedCode:
        if not isinstance(other, GeneratedCode):
            raise ValueError(f"Can't merge with {other}")

        # Slot/switch parameter mappings are per-mapping data (lists of
        # (c_idx, slot_name) tuples), not exclusive alternatives — two device
        # mappings in the same mode each carrying `slots:` must both survive.
        # Concatenate rather than silently dropping the second.
        return GeneratedCode(
            one.array_defs + other.array_defs,
            one.init + other.init,
            one.control_defs + other.control_defs,
            one.listener_fns + other.listener_fns,
            one.setup_listeners + other.setup_listeners,
            one.remove_listeners + other.remove_listeners,
            one.custom_parameter_mappings + other.custom_parameter_mappings,
            one.switch_parameter_mappings + other.switch_parameter_mappings,
        )


def is_valid_function_name(name):
    # Check if the string is a valid identifier
    if not name.isidentifier():
        return False

    # Check if the string is a reserved keyword
    if keyword.iskeyword(name):
        return False

    return True


def generate_parameter_listener_action(parameter, midi_no, track, device, fn_name, toggle: bool, debug_st, doctor: bool = False) -> [str]:
    if not is_valid_function_name(fn_name):
        raise ValueError(f"Invalid function name: {fn_name}")

    doctor_block = f"\n    self._helpers.button_event('{fn_name}', value)" if doctor else ""

    return Template("""
def ${fn_name}(self, value):${doctor_block}
    device = self.find_device("${track}", "${device}")
    if device is None:
        self.log_message(f"device not found: ${track} - ${device}")
        return


    self.device_parameter_action(device, $parameter, $midi_no, value, "$fn_name", toggle=$toggle)
    """).substitute(parameter=parameter, midi_no=midi_no, track=track, device=device, toggle=toggle, fn_name=fn_name,
                    comment=debug_st, doctor_block=doctor_block).split("\n")


def generate_control_value_listener_function_action(fn_name, var_name, callee, toggle: bool, debug_st: str, doctor: bool = False) -> [str]:
    if not is_valid_function_name(fn_name):
        raise ValueError(f"Invalid function name: {fn_name}")

    toggle_fn = "True"
    if toggle:
        # press-once: the edge guard adapts to momentary vs toggle hardware.
        toggle_fn = "self._helpers.should_act_on_edge(value)"

    doctor_block = f"\n    self._helpers.button_event('{fn_name}', value)" if doctor else ""

    return Template("""
# $comment
def ${fn_name}(self, value):${doctor_block}
    if self.manager.debug:
        self.log_message(f"${fn_name} ($comment) callee = ${callee}, value is {value}")

    previous_value = self._previous_values['$fn_name']
    self._previous_values['$fn_name'] = value

    if ${toggle_fn}:
        $callee
    self._hud_client.send_ping()
    """).substitute(callee=callee, var_name=var_name, fn_name=fn_name, comment=debug_st, toggle_fn=toggle_fn,
                    doctor_block=doctor_block).split(
        "\n")


def mixer_templates(mixer_with_midi: MixerWithMidi, mode_name: str) -> [GeneratedCode]:
    codes = []

    for midi_map in mixer_with_midi.midi_maps:
        if midi_map.api_function == "sends":
            var_name = f"{midi_map.midi_coords[0].controller_variable_name()}_{mode_name}_sends"

            codes.append(GeneratedCode(
                # Each coord in the array_def is referenced as `self.<knob>`, so
                # the corresponding EncoderElement must be declared in setup_controls.
                control_defs=list(midi_map.midi_coords),
                array_defs=[(var_name, midi_map.midi_coords)],
                setup_listeners=[midi_map.listener_setup_code(var_name)],
                remove_listeners=[midi_map.listener_remove_code()]
            ))
        else:
            codes.append(GeneratedCode(
                control_defs=[midi_map.only_midi_coord],
                setup_listeners=[midi_map.listener_setup_code()],
                remove_listeners=[midi_map.listener_remove_code()]
            ))

    return codes


def device_templates(device_with_midi: DeviceWithMidi, mode_name: str, controller=None, hud_cells=None):
    """Device mapping codegen, including the optional drum-rack roles.

    A control may carry BOTH a device role (macro encoder / switch button) and a
    drum role (per-step velocity / sequencer step) — the `velocities:`/`sequencer:`
    blocks are declared on the same controls as `encoders:`/`button:`. For a
    shared control we emit ONE dispatching listener that branches at call time:
    a drum rack is focused -> the drum action, otherwise the device action (see
    `ai-coding/plans/drum_rack.md`, precedence revision). Controls with only one
    role keep their plain listener. `pads:` selects the drum pad on press (audition
    — the pad making sound — is the deferred Live-spike seam)."""
    codes = []

    track = device_with_midi.track.name.value
    device = device_with_midi.device

    # Drum roles keyed by the control they sit on, so a device encoder/switch can
    # find its overlapping velocity/step/pad role.
    vel_by_ch = {vm.midi_coords.ch_num: vm for vm in device_with_midi.velocity_maps}
    step_by_ch = {sm.midi_coords.ch_num: sm for sm in device_with_midi.step_maps}
    pad_by_ch = {pm.midi_coords.ch_num: pm for pm in device_with_midi.pad_maps}
    consumed_vel, consumed_step, consumed_pad = set(), set(), set()

    for mm in device_with_midi.midi_maps:
        ch = mm.only_midi_coord.ch_num
        vm = vel_by_ch.get(ch)
        if vm is not None:
            consumed_vel.add(ch)
            codes.append(_dispatch_encoder_template(mm, vm, mode_name, track, device))
        else:
            codes.append(_plain_encoder_template(mm, mode_name, track, device))

    for mb in device_with_midi.switch_maps:
        ch = mb.only_midi_coord.ch_num
        # A button carries at most one drum role in a given mode (pads and steps
        # live in different modes). Prefer step, then pad.
        sm = step_by_ch.get(ch)
        pm = pad_by_ch.get(ch)
        if sm is not None:
            consumed_step.add(ch)
            codes.append(_dispatch_switch_template(mb, sm, mode_name, track, device))
        elif pm is not None:
            consumed_pad.add(ch)
            codes.append(_dispatch_pad_template(mb, pm, mode_name, track, device))
        else:
            codes.append(_switch_template(mb, mode_name, track, device))

    # Drum roles on controls with no device role -> standalone drum listeners
    # (the runtime no-ops when the focused device isn't a drum rack).
    for vm in device_with_midi.velocity_maps:
        if vm.midi_coords.ch_num not in consumed_vel:
            codes.append(_drum_velocity_template(vm, mode_name))
    for sm in device_with_midi.step_maps:
        if sm.midi_coords.ch_num not in consumed_step:
            codes.append(_drum_step_template(sm, mode_name))
    for pm in device_with_midi.pad_maps:
        if pm.midi_coords.ch_num not in consumed_pad:
            codes.append(_drum_pad_template(pm, mode_name))

    custom_mappings = code_from_slot_assignments(device_with_midi.slot_assignments)
    switch_mappings = code_from_switch_slot_assignments(device_with_midi.switch_maps, controller, hud_cells)
    codes.append(GeneratedCode(custom_parameter_mappings=custom_mappings,
                               switch_parameter_mappings=switch_mappings))

    return codes


def _plain_encoder_template(mm, mode_name: str, track: str, device: str) -> 'GeneratedCode':
    enc_name = mm.controller_variable_name()
    enc_listener_name = mm.controller_listener_fn_name(mode_name)
    enc_refs = EncoderRefinements(mm.only_midi_coord.encoder_refs)
    return GeneratedCode(
        control_defs=mm.midi_coords,
        setup_listeners=[f"self.{enc_name}.add_value_listener(self.{enc_listener_name})",
                         f"self._previous_values['{enc_listener_name}'] = 0"],
        remove_listeners=[f"self.{enc_name}.remove_value_listener(self.{enc_listener_name})"],
        listener_fns=generate_parameter_listener_action(
            mm.parameter,
            mm.only_midi_coord.number,
            track,
            device,
            enc_listener_name,
            mm.only_midi_coord.encoder_type.is_button() and not enc_refs.has_momentary(),
            mm.info_string(),
            doctor=mm.only_midi_coord.encoder_type.is_button()),
    )


def _dispatch_encoder_template(mm, vm, mode_name: str, track: str, device: str) -> 'GeneratedCode':
    """One knob, two roles: device-macro parameter normally, per-step velocity on
    a drum rack. A single listener branches on the focused device type."""
    enc_name = mm.controller_variable_name()
    fn_name = mm.controller_listener_fn_name(mode_name)
    fn = _dispatch_encoder_fn(fn_name, vm.step, mm.parameter, mm.only_midi_coord.number,
                              track, device).split("\n")
    return GeneratedCode(
        control_defs=mm.midi_coords,
        setup_listeners=[f"self.{enc_name}.add_value_listener(self.{fn_name})",
                         f"self._previous_values['{fn_name}'] = 0"],
        remove_listeners=[f"self.{enc_name}.remove_value_listener(self.{fn_name})"],
        listener_fns=fn,
    )


def _dispatch_encoder_fn(fn_name: str, step: int, parameter, midi_no, track: str, device: str) -> str:
    return Template("""
def ${fn_name}(self, value):
    if self.drum_rack.is_active():
        self.drum_rack.set_velocity(${step}, value)
        self._hud_client.send_ping()
        return
    device = self.find_device("${track}", "${device}")
    if device is None:
        self.log_message(f"device not found: ${track} - ${device}")
        return
    self.device_parameter_action(device, ${parameter}, ${midi_no}, value, "${fn_name}", toggle=False)
    """).substitute(fn_name=fn_name, step=step, parameter=parameter, midi_no=midi_no,
                    track=track, device=device)


def _dispatch_switch_template(mb, sm, mode_name: str, track: str, device: str) -> 'GeneratedCode':
    """One button, two roles: device switch-slot cycle normally, sequencer step
    toggle on a drum rack. A single listener branches on the focused device type."""
    btn_name = mb.controller_variable_name()
    fn_name = mb.controller_listener_fn_name(mode_name)
    fn = _dispatch_switch_fn(fn_name, sm.step, mb.slot, track, device).split("\n")
    return GeneratedCode(
        control_defs=[mb.only_midi_coord],
        setup_listeners=[f"self.{btn_name}.add_value_listener(self.{fn_name})",
                         f"self._previous_values['{fn_name}'] = 0"],
        remove_listeners=[f"self.{btn_name}.remove_value_listener(self.{fn_name})"],
        listener_fns=fn,
    )


def _dispatch_switch_fn(fn_name: str, step: int, slot: int, track: str, device: str) -> str:
    return Template("""
def ${fn_name}(self, value):
    if self.drum_rack.is_active():
        self.drum_rack.step_event(${step}, value)
        self._hud_client.send_ping()
        return
    self.log_message(f"calling : ${fn_name}")
    self._helpers.button_event("${fn_name}", value)
    device = self.find_device("${track}", "${device}")
    if device is None:
        self.log_message(f"device not found: ${track} - ${device}")
        return
    self._hud_client.send_ping()
    if self._helpers.should_act_on_edge(value):
        self._helpers.switch_slot_action(device, ${slot}, value, "${fn_name}")
    """).substitute(fn_name=fn_name, step=step, slot=slot, track=track, device=device)


def _dispatch_pad_template(mb, pm, mode_name: str, track: str, device: str) -> 'GeneratedCode':
    """One button, two roles: device switch-slot cycle normally, drum-pad SELECT
    on a drum rack. Select-on-press only (a pad tap picks the drum the sequencer
    edits); audition — the pad sounding — is the deferred seam."""
    btn_name = mb.controller_variable_name()
    fn_name = mb.controller_listener_fn_name(mode_name)
    fn = _dispatch_pad_fn(fn_name, pm.index, mb.slot, track, device).split("\n")
    return GeneratedCode(
        control_defs=[mb.only_midi_coord],
        setup_listeners=[f"self.{btn_name}.add_value_listener(self.{fn_name})",
                         f"self._previous_values['{fn_name}'] = 0"],
        remove_listeners=[f"self.{btn_name}.remove_value_listener(self.{fn_name})"],
        listener_fns=fn,
    )


def _dispatch_pad_fn(fn_name: str, index: int, slot: int, track: str, device: str) -> str:
    return Template("""
def ${fn_name}(self, value):
    if self.drum_rack.is_active():
        if self._helpers.should_act_on_edge(value):
            self.drum_rack.select_pad(${index})
        self._hud_client.send_ping()
        return
    self.log_message(f"calling : ${fn_name}")
    self._helpers.button_event("${fn_name}", value)
    device = self.find_device("${track}", "${device}")
    if device is None:
        self.log_message(f"device not found: ${track} - ${device}")
        return
    self._hud_client.send_ping()
    if self._helpers.should_act_on_edge(value):
        self._helpers.switch_slot_action(device, ${slot}, value, "${fn_name}")
    """).substitute(fn_name=fn_name, index=index, slot=slot, track=track, device=device)


def _drum_pad_template(pm, mode_name: str) -> 'GeneratedCode':
    """Pad button with no device role -> standalone pad-select listener."""
    mc = pm.midi_coords
    var_name = mc.controller_variable_name()
    fn_name = mc.controller_listener_fn_name(f"_mode_{mode_name}_drum_pad{pm.index}")
    fn = _drum_pad_action_fn(fn_name, pm.index).split("\n")
    return GeneratedCode(
        control_defs=[mc],
        setup_listeners=[f"self.{var_name}.add_value_listener(self.{fn_name})",
                         f"self._previous_values['{fn_name}'] = 0"],
        remove_listeners=[f"self.{var_name}.remove_value_listener(self.{fn_name})"],
        listener_fns=fn,
    )


def _drum_pad_action_fn(fn_name: str, index: int) -> str:
    # Select-on-press: the runtime no-ops when the focused device isn't a drum rack.
    return Template("""
def ${fn_name}(self, value):
    if self._helpers.should_act_on_edge(value):
        self.drum_rack.select_pad(${index})
    self._hud_client.send_ping()
    """).substitute(fn_name=fn_name, index=index)


def _drum_step_template(sm, mode_name: str) -> 'GeneratedCode':
    mc = sm.midi_coords
    var_name = mc.controller_variable_name()
    fn_name = mc.controller_listener_fn_name(f"_mode_{mode_name}_drum_step{sm.step}")
    fn = _drum_step_action_fn(fn_name, sm.step).split("\n")
    return GeneratedCode(
        control_defs=[mc],
        setup_listeners=[f"self.{var_name}.add_value_listener(self.{fn_name})",
                         f"self._previous_values['{fn_name}'] = 0"],
        remove_listeners=[f"self.{var_name}.remove_value_listener(self.{fn_name})"],
        listener_fns=fn,
    )


def _drum_step_action_fn(fn_name: str, step: int) -> str:
    # Steps forward BOTH edges (press + release) to the runtime: the long-note
    # gesture (hold step A, tap step B) needs the release, and a plain tap
    # toggles on release. The runtime interprets press vs release from `value`.
    return Template("""
def ${fn_name}(self, value):
    self.drum_rack.step_event(${step}, value)
    self._hud_client.send_ping()
    """).substitute(fn_name=fn_name, step=step)


def _drum_velocity_template(vm, mode_name: str) -> 'GeneratedCode':
    mc = vm.midi_coords
    var_name = mc.controller_variable_name()
    fn_name = mc.controller_listener_fn_name(f"_mode_{mode_name}_drum_vel{vm.step}")
    fn = _drum_velocity_action_fn(fn_name, vm.step).split("\n")
    return GeneratedCode(
        control_defs=[mc],
        setup_listeners=[f"self.{var_name}.add_value_listener(self.{fn_name})",
                         f"self._previous_values['{fn_name}'] = 0"],
        remove_listeners=[f"self.{var_name}.remove_value_listener(self.{fn_name})"],
        listener_fns=fn,
    )


def _drum_velocity_action_fn(fn_name: str, step: int) -> str:
    # Absolute encoder -> velocity of the existing note at this step. The runtime
    # no-ops on an empty step (turning a knob there does nothing).
    return Template("""
def ${fn_name}(self, value):
    self.drum_rack.set_velocity(${step}, value)
    self._hud_client.send_ping()
    """).substitute(fn_name=fn_name, step=step)


def _switch_template(mb: SwitchMidiMapping, mode_name: str, track: str = "selected", device: str = "selected") -> 'GeneratedCode':
    btn_name = mb.controller_variable_name()
    btn_listener_name = mb.controller_listener_fn_name(mode_name)

    fn = _switch_action_dispatch_fn(btn_listener_name, mb.slot, track, device).split("\n")

    return GeneratedCode(
        control_defs=[mb.only_midi_coord],
        setup_listeners=[f"self.{btn_name}.add_value_listener(self.{btn_listener_name})",
                         f"self._previous_values['{btn_listener_name}'] = 0"],
        remove_listeners=[f"self.{btn_name}.remove_value_listener(self.{btn_listener_name})"],
        listener_fns=fn,
    )


def _switch_action_dispatch_fn(fn_name: str, slot: int, track: str, device: str) -> str:
    """
    Switch listener — dispatches to the runtime Helpers, which resolves the
    slot against the loaded parameter_mappings JSON (or the identity fallback).
    `slot` is a 1-based device switch-slot index (an int, not a 'switchN' name).
    """
    return Template("""
def ${fn_name}(self, value):
    self.log_message(f"calling : ${fn_name}")
    self._helpers.button_event("${fn_name}", value)
    device = self.find_device("${track}", "${device}")
    if device is None:
        self.log_message(f"device not found: ${track} - ${device}")
        return
    self._hud_client.send_ping()
    # Switch slots act once per press. The edge guard adapts to the controller's
    # hardware button mode (momentary: act on the down, ignore the 0 release;
    # toggle: every alternating edge is its own press). Without it a momentary
    # bool slot toggles twice per press (net nothing); with a 127-only guard a
    # toggle-hardware button fires every *other* press.
    if self._helpers.should_act_on_edge(value):
        self._helpers.switch_slot_action(device, ${slot}, value, "${fn_name}")
    """).substitute(fn_name=fn_name, track=track, device=device, slot=slot)


def code_from_slot_assignments(slot_assignments: List[Tuple[int, str]]) -> List[str]:
    """
    Emit a flat list of (c_idx, slot_name) tuples for the runtime to resolve
    against the loaded parameter_mappings JSON.
    """
    out: List[str] = []
    for c_idx, slot in slot_assignments:
        if is_switch_slot(slot):
            continue
        out.append(f"({c_idx}, '{slot}')")
    return out


def code_from_switch_slot_assignments(switch_maps, controller=None, hud_cells=None) -> List[str]:
    """
    Emit (wire_idx, slot) tuples — wire_idx is the HUD button-array index
    assigned by the global layout allocator. The runtime uses wire_idx for
    HUD lookups; slot (a 1-based device switch-slot int) still drives
    device-table parameter resolution.
    """
    from ableton_control_surface_as_code.hud_layout import find_wire_index
    out: List[str] = []
    seen_slots: set = set()
    for mb in switch_maps:
        if mb.slot in seen_slots:
            continue
        seen_slots.add(mb.slot)
        wire_idx = None
        if controller is not None and hud_cells is not None:
            resolved = find_wire_index(controller, mb.only_midi_coord, hud_cells)
            if resolved is not None and resolved.kind == 'button':
                wire_idx = resolved.index
        if wire_idx is None:
            # Fallback to the legacy logical index when controller info is missing
            wire_idx = mb.slot - 1
        out.append(f"({wire_idx}, {mb.slot})")
    return out


def button_listener_function_caller_templates(midi_map: ButtonProviderBaseModel, mode_name: str):
    button_name = midi_map.controller_variable_name()
    button_listener_name = midi_map.controller_listener_fn_name(mode_name)
    enc_refs = EncoderRefinements(midi_map.only_midi_coord.encoder_refs)

    # Buttons act once on press by default: without the max-value guard the
    # callee fires on both press (127) and release (0), running the action
    # twice per press ("two operations at once"). `momentary` opts back into
    # fire-on-both-edges. Built-in actions (e.g. hud_toggle) are always
    # press-only regardless of refinement.
    press_only = getattr(midi_map, 'builtin', False) or not enc_refs.has_momentary()
    is_button = midi_map.only_midi_coord.encoder_type.is_button()

    return GeneratedCode(
        control_defs=[midi_map.only_midi_coord],
        setup_listeners=[f"self.{button_name}.add_value_listener(self.{button_listener_name})",
                         f"self._previous_values['{button_listener_name}'] = 0"],
        remove_listeners=[f"self.{button_name}.remove_value_listener(self.{button_listener_name})"],
        listener_fns=generate_control_value_listener_function_action(button_listener_name,
                                                                     midi_map.controller_variable_name(),
                                                                     midi_map.template_function_call(),
                                                                     press_only,
                                                                     midi_map.info_string(),
                                                                     doctor=is_button)
    )


def map_controllers(mode_name, midi_maps: List[ButtonProviderBaseModel]):
    return [button_listener_function_caller_templates(m, mode_name) for m in midi_maps]


def track_nav_templates(track_nav_with_midi: TrackNavWithMidi, mode_name) -> [GeneratedCode]:
    return map_controllers(mode_name, track_nav_with_midi.midi_maps)


def device_nav_templates(deivce_nav_with_midi: DeviceNavWithMidi, mode_name) -> [GeneratedCode]:
    return map_controllers(mode_name, deivce_nav_with_midi.midi_maps)


def transport_templates(transport_with_midi: TransportWithMidi, mode_name) -> [GeneratedCode]:
    return map_controllers(mode_name, transport_with_midi.midi_maps)


def functions_templates(functions_with_midi: FunctionsWithMidi, mode_name) -> [GeneratedCode]:
    return map_controllers(mode_name, functions_with_midi.midi_maps)


def generate_clip_encoder_listener_action(fn_name, call, debug_st) -> [str]:
    if not is_valid_function_name(fn_name):
        raise ValueError(f"Invalid function name: {fn_name}")

    return Template("""
# $comment
def ${fn_name}(self, value):
    self.clip_actions.${call}(value)
    self._hud_client.send_ping()
    """).substitute(fn_name=fn_name, call=call, comment=debug_st).split("\n")


def generate_clip_button_listener_action(fn_name, call, debug_st) -> [str]:
    if not is_valid_function_name(fn_name):
        raise ValueError(f"Invalid function name: {fn_name}")

    return Template("""
# $comment
def ${fn_name}(self, value):
    previous_value = self._previous_values['$fn_name']
    self._previous_values['$fn_name'] = value
    if self._helpers.value_is_max(value, 127):
        self.clip_actions.${call}()
    self._hud_client.send_ping()
    """).substitute(fn_name=fn_name, call=call, comment=debug_st).split("\n")


def generate_clip_nudge_listener_action(fn_name, call, step, debug_st) -> [str]:
    """A 'nudge' encoder turns an absolute knob into a relative stepper: each
    value change moves the property one `step` in the direction of the change.
    Works with absolute controllers (no relative MIDI mode needed).

    The baseline starts as None so the *first* event after load only records the
    reference position (it must not be read as a direction — the encoder could
    be sitting anywhere)."""
    if not is_valid_function_name(fn_name):
        raise ValueError(f"Invalid function name: {fn_name}")

    return Template("""
# $comment
def ${fn_name}(self, value):
    previous_value = self._previous_values['$fn_name']
    self._previous_values['$fn_name'] = value
    if previous_value is None:
        return
    if value > previous_value:
        self.clip_actions.${call}($step)
    elif value < previous_value:
        self.clip_actions.${call}(-$step)
    self._hud_client.send_ping()
    """).substitute(fn_name=fn_name, call=call, step=step, comment=debug_st).split("\n")


def clip_templates(clip_with_midi: 'ClipWithMidi', mode_name) -> [GeneratedCode]:
    codes = []
    for mm in clip_with_midi.midi_maps:
        var_name = mm.controller_variable_name()
        listener_name = mm.controller_listener_fn_name(mode_name)

        if mm.kind == 'encoder':
            listener_fns = generate_clip_encoder_listener_action(
                listener_name, mm.runtime_call(), mm.info_string())
            initial_previous = "0"
        elif mm.kind == 'nudge':
            listener_fns = generate_clip_nudge_listener_action(
                listener_name, mm.runtime_call(), mm.nudge_step(), mm.info_string())
            # None so the first event only establishes the reference position.
            initial_previous = "None"
        else:
            listener_fns = generate_clip_button_listener_action(
                listener_name, mm.runtime_call(), mm.info_string())
            initial_previous = "0"

        codes.append(GeneratedCode(
            control_defs=[mm.only_midi_coord],
            setup_listeners=[f"self.{var_name}.add_value_listener(self.{listener_name})",
                             f"self._previous_values['{listener_name}'] = {initial_previous}"],
            remove_listeners=[f"self.{var_name}.remove_value_listener(self.{listener_name})"],
            listener_fns=listener_fns,
        ))

    return codes


def parameter_pager_templates(pager_with_midi, mode_name) -> [GeneratedCode]:
    return map_controllers(mode_name, pager_with_midi.midi_maps)


def get_python_code_error(code):
    try:
        ast.parse(code)
    except SyntaxError as e:
        return e
    else:
        return None


def class_function_code_block(lines: [str]):
    if lines is None or lines == []:
        return ""

    tab_block = "    "
    return f"\n{tab_block}".join(lines) + "\n"


def dict_variable_decleration_block(lines: [str]):
    if lines is None or lines == []:
        return ""

    # Each element is one mode's already-comma-joined block of tuple literals.
    # A mode that binds none of this control type contributes an empty string;
    # dropping those avoids stray separators. Join the surviving blocks with a
    # comma so the rendered list literal stays valid when more than one mode
    # contributes entries (otherwise adjacent tuples read as a call).
    non_empty = [line for line in lines if line]
    if not non_empty:
        return ""

    return ",\n\t\t\t".join(non_empty) + "\n"


def class_function_body_code_block(lines: [str]):
    if lines is None or lines == []:
        return ""

    tab_block = "    "
    return f"\n{tab_block}{tab_block}" + f"\n{tab_block}{tab_block}".join(lines) + "\n"


