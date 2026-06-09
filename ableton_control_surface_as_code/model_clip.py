from dataclasses import dataclass
from typing import Literal, List, Dict

from pydantic import BaseModel, field_validator

from ableton_control_surface_as_code.core_model import (
    MidiCoords, parse_coords, ButtonProviderBaseModel,
)
from ableton_control_surface_as_code.encoder_coords import EncoderCoords

# Beats moved per step for nudge encoders and inc/dec buttons.
CLIP_STEP_BEATS = 1.0


@dataclass(frozen=True)
class ClipActionSpec:
    key: str          # hyphenated mapping key, e.g. "pitch-coarse"
    kind: str         # 'encoder' (absolute) | 'nudge' (turn = step) | 'button' (press)
    call: str         # method on the runtime ClipActions, e.g. "set_gain"
    audio_only: bool  # only meaningful for audio clips (documented; runtime also guards)
    hud_label: str    # short label shown in the HUD cell for this control


# Single source of truth for the clip attribute set.
#  - `encoder` actions map an absolute 0..127 encoder onto a bounded property
#    range (gain, pitch); they pass `value` to the runtime call.
#  - `nudge` actions turn an absolute knob into a relative stepper: each value
#    change moves the property +/-CLIP_STEP_BEATS in the direction of the turn.
#    Use these for the unbounded loop/marker positions on a knob.
#  - `button` actions fire once per press (inc/dec, toggle, method, composite)
#    and call a no-arg runtime method.
# See source_modules/clip_actions.py for the implementations these `call`s name.
CLIP_ACTIONS = {
    # absolute encoders (bounded ranges)
    "gain":                  ClipActionSpec("gain", "encoder", "set_gain", True, "gain"),
    "pitch-coarse":          ClipActionSpec("pitch-coarse", "encoder", "set_pitch_coarse", True, "pitch"),
    "pitch-fine":            ClipActionSpec("pitch-fine", "encoder", "set_pitch_fine", True, "pitch fine"),
    # nudge encoders (turn a knob to step beats)
    "move-loop":             ClipActionSpec("move-loop", "nudge", "nudge_move_loop", False, "move loop"),
    "loop-start":            ClipActionSpec("loop-start", "nudge", "nudge_loop_start", False, "loop start"),
    "loop-end":              ClipActionSpec("loop-end", "nudge", "nudge_loop_end", False, "loop end"),
    "start-marker":          ClipActionSpec("start-marker", "nudge", "nudge_start_marker", False, "start mark"),
    "end-marker":            ClipActionSpec("end-marker", "nudge", "nudge_end_marker", False, "end mark"),
    # inc/dec buttons (press to step a beat)
    "loop-start-inc":        ClipActionSpec("loop-start-inc", "button", "loop_start_inc", False, "loopSt +"),
    "loop-start-dec":        ClipActionSpec("loop-start-dec", "button", "loop_start_dec", False, "loopSt -"),
    "loop-end-inc":          ClipActionSpec("loop-end-inc", "button", "loop_end_inc", False, "loopEnd +"),
    "loop-end-dec":          ClipActionSpec("loop-end-dec", "button", "loop_end_dec", False, "loopEnd -"),
    "start-marker-inc":      ClipActionSpec("start-marker-inc", "button", "start_marker_inc", False, "stMark +"),
    "start-marker-dec":      ClipActionSpec("start-marker-dec", "button", "start_marker_dec", False, "stMark -"),
    "end-marker-inc":        ClipActionSpec("end-marker-inc", "button", "end_marker_inc", False, "endMark +"),
    "end-marker-dec":        ClipActionSpec("end-marker-dec", "button", "end_marker_dec", False, "endMark -"),
    "move-loop-forward":     ClipActionSpec("move-loop-forward", "button", "move_loop_forward", False, "loop fwd"),
    "move-loop-backward":    ClipActionSpec("move-loop-backward", "button", "move_loop_backward", False, "loop back"),
    # toggles / methods / composites
    "looping":               ClipActionSpec("looping", "button", "toggle_looping", False, "loop on"),
    "warping":               ClipActionSpec("warping", "button", "toggle_warping", True, "warp"),
    "duplicate-loop":        ClipActionSpec("duplicate-loop", "button", "duplicate_loop", False, "dup loop"),
    "sync-loop-and-markers": ClipActionSpec("sync-loop-and-markers", "button", "sync_loop_and_markers", False, "sync mk"),
}


class Clip(BaseModel):
    type: Literal['clip'] = "clip"
    mappings: Dict[str, str]

    @field_validator('mappings')
    @classmethod
    def _known_actions(cls, v):
        # Reject unknown keys so typos (e.g. "start-loop-inc") fail loudly at
        # generate time instead of being silently dropped. CLIP_ACTIONS is the
        # single source of truth; the message names the valid keys.
        unknown = set(v) - set(CLIP_ACTIONS)
        if unknown:
            raise ValueError(
                f"Unknown clip action(s): {sorted(unknown)} — "
                f"expected one of: {', '.join(sorted(CLIP_ACTIONS))}")
        return v

    def as_parsed_dict(self) -> dict[str, EncoderCoords]:
        # Keys are the hyphenated action names, which index directly into CLIP_ACTIONS.
        return {key: parse_coords(value) for key, value in self.mappings.items()}


class ClipMidiMapping(ButtonProviderBaseModel):
    type: Literal['clip'] = 'clip'
    midi_coords: List[MidiCoords]
    action: str  # CLIP_ACTIONS key

    @property
    def spec(self) -> ClipActionSpec:
        return CLIP_ACTIONS[self.action]

    @property
    def kind(self) -> str:
        return self.spec.kind

    @property
    def only_midi_coord(self) -> MidiCoords:
        return self.midi_coords[0]

    def is_encoder(self) -> bool:
        return self.spec.kind in ("encoder", "nudge")

    def runtime_call(self) -> str:
        return self.spec.call

    def nudge_step(self) -> float:
        return CLIP_STEP_BEATS

    def info_string(self):
        return (f"ch{self.only_midi_coord.channel}_no{self.only_midi_coord.number}"
                f"_{self.only_midi_coord.type.value}__{self.short_info_string()}")

    def short_info_string(self):
        return f"clip {self.action}"

    def create_controller_element(self):
        return self.only_midi_coord.create_controller_element()

    def template_function_call(self):
        return f"self.clip_actions.{self.spec.call}()"

    def controller_variable_name(self):
        return self.only_midi_coord.controller_variable_name()

    def controller_listener_fn_name(self, mode_name):
        return self.only_midi_coord.controller_listener_fn_name(
            f"_mode_{mode_name}_clip_{self.action}")


class ClipWithMidi(BaseModel):
    type: Literal['clip'] = 'clip'
    midi_maps: list[ClipMidiMapping]


def build_clip_model_v2(controller, mapping: Clip) -> ClipWithMidi:
    midi_maps = []
    for key, enc_coords in mapping.as_parsed_dict().items():
        coords_list, _type = controller.build_midi_coords(enc_coords)
        midi_maps.append(ClipMidiMapping(midi_coords=coords_list, action=key))

    return ClipWithMidi(midi_maps=midi_maps)
