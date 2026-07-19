import ast
import unittest
from pathlib import Path

from ableton_control_surface_as_code.core_model import EncoderType, MidiType
from ableton_control_surface_as_code.gen import generate_code_as_template_vars
from ableton_control_surface_as_code.gen_code import device_templates, GeneratedCodes
from ableton_control_surface_as_code.gen_error import GenError
from ableton_control_surface_as_code.model_controller import (
    ControllerV2, ControllerRawV2, ControlGroupPartV2,
)
from ableton_control_surface_as_code.model_device import (
    DeviceV2, DeviceWithMidi, build_device_model_v2_1,
)
from ableton_control_surface_as_code.model_v2 import (
    ModeGroupWithMidi, validate_mappings, build_validated_model,
)
from source_modules.drum_rack import (
    DrumRackController, NoteSpec, STEP_BEATS, DEFAULT_VELOCITY, BAR_BEATS,
)

_SURFACE_DIR = Path(__file__).resolve().parent / 'fixtures' / 'drum_rack_surface'


# ---- controller: 4 grid blocks, mirroring the real grid controller ----------

def _grid_controller():
    return ControllerV2.build_from(ControllerRawV2(**{
        'light_colors': {},
        'control_groups': [
            ControlGroupPartV2(layout='grid', number=1, type=EncoderType.button,
                               midi_channel=1, midi_type=MidiType.note,
                               midi_range='C-2-DS-1', rows=4, columns=4),
            ControlGroupPartV2(layout='grid', number=2, type=EncoderType.knob,
                               midi_channel=1, midi_type=MidiType.CC,
                               midi_range='16-31', rows=4, columns=4, right_of=1),
            ControlGroupPartV2(layout='grid', number=3, type=EncoderType.knob,
                               midi_channel=1, midi_type=MidiType.CC,
                               midi_range='32-47', rows=4, columns=4, right_of=2),
            ControlGroupPartV2(layout='grid', number=4, type=EncoderType.button,
                               midi_channel=1, midi_type=MidiType.note,
                               midi_range='C2-DS3', rows=4, columns=4, right_of=3),
        ],
    }))


def _device(mappings: dict) -> DeviceV2:
    return DeviceV2(track='selected', device='selected', mappings=mappings)


def _build(mappings: dict) -> DeviceWithMidi:
    return build_device_model_v2_1(_grid_controller(), _device(mappings), None)


class TestDrumRackModelBuild(unittest.TestCase):
    def test_builds_all_three_ranges(self):
        model = _build({
            'pads': {'range': 'grid-1:1-16'},
            'sequencer': {'range': 'grid-4:1-16'},
            'velocities': {'range': 'grid-2:1-16'},
        })
        self.assertIsInstance(model, DeviceWithMidi)
        self.assertEqual(model.type, 'device')
        self.assertEqual([p.index for p in model.pad_maps], list(range(16)))
        self.assertEqual([s.step for s in model.step_maps], list(range(16)))
        self.assertEqual([v.step for v in model.velocity_maps], list(range(16)))

    def test_ranges_are_optional(self):
        model = _build({'sequencer': {'range': 'grid-4:1-8'}})
        self.assertEqual(model.pad_maps, [])
        self.assertEqual(len(model.step_maps), 8)
        self.assertEqual(model.velocity_maps, [])

    def test_plain_device_mapping_has_no_drum_maps(self):
        model = _build({'encoders': {'range': 'grid-2:1-16', 'parameters': '1-16'}})
        self.assertEqual(model.pad_maps, [])
        self.assertEqual(model.step_maps, [])
        self.assertEqual(model.velocity_maps, [])
        self.assertEqual(len(model.midi_maps), 16)

    def test_device_encoders_and_drum_blocks_coexist(self):
        model = _build({
            'encoders': {'range': 'grid-3:1-16', 'parameters': '1-16'},
            'pads': {'range': 'grid-1:1-16'},
        })
        self.assertEqual(len(model.midi_maps), 16)
        self.assertEqual(len(model.pad_maps), 16)

    def test_pads_must_be_exactly_16(self):
        with self.assertRaises(GenError) as ctx:
            _build({'pads': {'range': 'grid-1:1-8'}})
        self.assertIn('pads', str(ctx.exception))

    def test_sequencer_rejects_bad_count(self):
        with self.assertRaises(GenError):
            _build({'sequencer': {'range': 'grid-4:1-12'}})

    def test_sequencer_accepts_8_and_16(self):
        for span in ('grid-4:1-8', 'grid-4:1-16'):
            model = _build({'sequencer': {'range': span}})
            self.assertIn(len(model.step_maps), (8, 16))

    def test_pads_must_be_buttons(self):
        with self.assertRaises(GenError) as ctx:
            _build({'pads': {'range': 'grid-2:1-16'}})  # knobs
        self.assertIn('button', str(ctx.exception))

    def test_velocities_must_be_knobs(self):
        with self.assertRaises(GenError) as ctx:
            _build({'velocities': {'range': 'grid-1:1-16'}})  # buttons
        self.assertIn('knob', str(ctx.exception))

    def test_unknown_mapping_key_rejected(self):
        with self.assertRaises(Exception):
            _device({'padz': {'range': 'grid-1:1-16'}})

    def test_sequencer_rejects_toggle_hardware(self):
        # Toggle hardware alternates 127/0, so only every second tap would register;
        # the step sequencer needs momentary buttons (one clean edge per tap).
        ctrl = ControllerV2.build_from(ControllerRawV2(**{
            'light_colors': {},
            'button-behaviour': 'toggle',
            'control_groups': [
                ControlGroupPartV2(layout='grid', number=1, type=EncoderType.button,
                                   midi_channel=1, midi_type=MidiType.note,
                                   midi_range='C-2-DS-1', rows=4, columns=4),
            ],
        }))
        with self.assertRaises(GenError) as ctx:
            build_device_model_v2_1(ctrl, _device({'sequencer': {'range': 'grid-1:1-16'}}), None)
        self.assertIn('momentary', str(ctx.exception))

    def test_velocities_allowed_on_toggle_hardware(self):
        # Velocities are absolute knobs — no release-edge dependency, so toggle
        # button-behaviour must not block them.
        ctrl = ControllerV2.build_from(ControllerRawV2(**{
            'light_colors': {},
            'button-behaviour': 'toggle',
            'control_groups': [
                ControlGroupPartV2(layout='grid', number=1, type=EncoderType.knob,
                                   midi_channel=1, midi_type=MidiType.CC,
                                   midi_range='16-31', rows=4, columns=4),
            ],
        }))
        model = build_device_model_v2_1(ctrl, _device({'velocities': {'range': 'grid-1:1-16'}}), None)
        self.assertEqual(len(model.velocity_maps), 16)


class TestDrumRackClashValidation(unittest.TestCase):
    def test_two_mappings_clashing_on_pads_still_raise(self):
        # Cross-mapping conflict: two device mappings both binding grid-1 as pads.
        a = _build({'pads': {'range': 'grid-1:1-16'}})
        b = _build({'pads': {'range': 'grid-1:1-16'}})
        with self.assertRaises(GenError):
            validate_mappings([a, b])

    def test_intra_mapping_overlap_is_allowed_precedence(self):
        # Same control as a macro encoder AND a per-step velocity — intentional
        # precedence overlap, must NOT read as a clash.
        model = _build({
            'encoders': {'range': 'grid-2:1-16', 'parameters': '1-16'},
            'velocities': {'range': 'grid-2:1-16'},
        })
        validate_mappings([model])  # must not raise

    def test_genuine_cross_mapping_same_type_still_clashes(self):
        a = _build({'encoders': {'range': 'grid-2:1-16', 'parameters': '1-16'}})
        b = _build({'encoders': {'range': 'grid-2:1-16', 'parameters': '1-16'}})
        with self.assertRaises(GenError):
            validate_mappings([a, b])


class TestDrumRackCodegen(unittest.TestCase):
    def _merged(self, mappings):
        codes = device_templates(_build(mappings), 'main', controller=_grid_controller())
        return GeneratedCodes.merge_all(codes)

    def test_generated_listeners_are_valid_python(self):
        merged = self._merged({
            'encoder-list': [
                {'range': 'grid-3:1-16', 'parameters': '1-16'},
                {'range': 'grid-2:1-16', 'parameters': '17-32'},
            ],
            'pads': {'range': 'grid-1:1-16'},
            'sequencer': {'range': 'grid-4:1-16'},
            'velocities': {'range': 'grid-2:1-16'},
        })
        ast.parse("\n".join(merged.listener_fns))

    def test_step_listeners_wired_on_dedicated_buttons(self):
        merged = self._merged({'sequencer': {'range': 'grid-4:1-16'}})
        body = "\n".join(merged.listener_fns)
        for step in range(16):
            self.assertIn(f'self.drum_rack.step_event({step},', body)

    def test_velocity_listener_on_dedicated_knob(self):
        merged = self._merged({'velocities': {'range': 'grid-2:1-16'}})
        body = "\n".join(merged.listener_fns)
        self.assertIn('self.drum_rack.set_velocity(', body)

    def test_pads_wired_as_select(self):
        merged = self._merged({'pads': {'range': 'grid-1:1-16'}})
        body = "\n".join(merged.listener_fns)
        # Pads select the drum on press; audition (sound) stays deferred.
        for index in range(16):
            self.assertIn(f'self.drum_rack.select_pad({index})', body)


class TestDrumRackPrecedenceDispatch(unittest.TestCase):
    """A control carrying BOTH a device role and a drum role gets a SINGLE
    dispatching listener that branches on is_active()."""

    def _shared(self):
        # grid-2 knobs are both macro encoders (params 1-16) and velocities.
        codes = device_templates(_build({
            'encoders': {'range': 'grid-2:1-16', 'parameters': '1-16'},
            'velocities': {'range': 'grid-2:1-16'},
        }), 'main', controller=_grid_controller())
        return GeneratedCodes.merge_all(codes)

    def test_one_listener_per_shared_control_not_two(self):
        merged = self._shared()
        setups = "\n".join(merged.setup_listeners)
        # 16 shared knobs -> 16 add_value_listener calls, not 32.
        self.assertEqual(setups.count('.add_value_listener('), 16)

    def test_dispatch_fn_branches_to_both_actions(self):
        merged = self._shared()
        body = "\n".join(merged.listener_fns)
        self.assertIn('if self.drum_rack.is_active():', body)
        self.assertIn('self.drum_rack.set_velocity(', body)
        self.assertIn('self.device_parameter_action(', body)
        # Exactly 16 velocity branches (one per shared knob), no standalone extras.
        self.assertEqual(body.count('self.drum_rack.set_velocity('), 16)

    def test_shared_switch_dispatches_step_vs_slot(self):
        # grid-1 buttons are both device switch slots AND sequencer steps.
        codes = device_templates(_build({
            'button': {'range': 'grid-1:1-16', 'slots': '1-16'},
            'sequencer': {'range': 'grid-1:1-16'},
        }), 'main', controller=_grid_controller())
        merged = GeneratedCodes.merge_all(codes)
        body = "\n".join(merged.listener_fns)
        setups = "\n".join(merged.setup_listeners)
        self.assertEqual(setups.count('.add_value_listener('), 16)
        self.assertIn('self.drum_rack.step_event(', body)
        self.assertIn('self._helpers.switch_slot_action(', body)

    def test_shared_button_dispatches_pad_select_vs_slot(self):
        # grid-1 buttons are both device switch slots AND drum pads (main mode).
        codes = device_templates(_build({
            'button': {'range': 'grid-1:1-16', 'slots': '1-16'},
            'pads': {'range': 'grid-1:1-16'},
        }), 'main', controller=_grid_controller())
        merged = GeneratedCodes.merge_all(codes)
        body = "\n".join(merged.listener_fns)
        setups = "\n".join(merged.setup_listeners)
        self.assertEqual(setups.count('.add_value_listener('), 16)  # one per button, not two
        self.assertIn('self.drum_rack.select_pad(', body)
        self.assertIn('self._helpers.switch_slot_action(', body)


class TestDrumRackFullGeneration(unittest.TestCase):
    def test_generate_code_as_template_vars_compiles(self):
        model = _build({
            'pads': {'range': 'grid-1:1-16'},
            'sequencer': {'range': 'grid-4:1-16'},
            'velocities': {'range': 'grid-2:1-16'},
        })
        modes = ModeGroupWithMidi(mappings=[('main', [model])], mode_button=None)
        vars = generate_code_as_template_vars(modes, controller=_grid_controller())
        for key in ('code_listener_fns', 'code_setup_listeners'):
            ast.parse("class C:\n" + "\n".join(
                "    " + line for line in vars[key].split("\n")))


class TestDrumRackSurfaceEndToEnd(unittest.TestCase):
    """Build the drum-rack surface fixture from disk through the whole
    validation + codegen pipeline, asserting it parses, resolves, clash-checks
    (with an intra-mapping precedence overlap on grid-2) and renders valid python."""

    def _build_surface(self):
        mapping_path = _SURFACE_DIR / 'ck_drum_rack.nt'

        def _resolve_controller(root):
            p = mapping_path.parent / root.controller
            return p.read_text(), p.name

        return build_validated_model(
            mapping_path.read_text(), mapping_path.parent,
            resolve_controller=_resolve_controller,
            mapping_source=mapping_path.name)

    def test_surface_builds_and_wires_all_ranges(self):
        _root, controller, mode_with_midi = self._build_surface()
        maps = [m for _, mode_maps in mode_with_midi.mappings for m in mode_maps]
        dev = next(m for m in maps if m.type == 'device')
        self.assertEqual(len(dev.pad_maps), 16)
        self.assertEqual(len(dev.step_maps), 16)
        self.assertEqual(len(dev.velocity_maps), 16)
        self.assertEqual(len(dev.midi_maps), 32)  # grid-3 + grid-2 macro encoders

        vars = generate_code_as_template_vars(mode_with_midi, controller=controller)
        ast.parse("class C:\n" + "\n".join(
            "    " + line for line in vars['code_listener_fns'].split("\n")))


# ---- runtime: fakes ---------------------------------------------------------

class FakeNote:
    def __init__(self, pitch, start_time, duration=STEP_BEATS, velocity=DEFAULT_VELOCITY):
        self.pitch = pitch
        self.start_time = start_time
        self.duration = duration
        self.velocity = velocity


class FakeClip:
    is_midi_clip = True

    def __init__(self, notes=None, start_time=0.0):
        self.notes = list(notes or [])
        # Arrangement-clip fields: a session clip leaves these at their defaults.
        self.start_time = start_time
        self.looping = False
        self.loop_start = 0.0
        self.loop_end = 0.0

    def get_notes_extended(self, from_pitch, pitch_span, from_time, time_span):
        return [n for n in self.notes
                if from_pitch <= n.pitch < from_pitch + pitch_span
                and from_time <= n.start_time < from_time + time_span]

    def add_new_notes(self, specs):
        for s in specs:
            self.notes.append(FakeNote(s.pitch, s.start_time, s.duration, s.velocity))

    def remove_notes_extended(self, from_pitch, pitch_span, from_time, time_span):
        self.notes = [n for n in self.notes
                      if not (from_pitch <= n.pitch < from_pitch + pitch_span
                              and from_time <= n.start_time < from_time + time_span)]

    def apply_note_modifications(self, notes):
        pass  # notes are mutated in place in these fakes


class FakePad:
    def __init__(self, note, name='Kick'):
        self.note = note
        self.name = name


class FakeDeviceView:
    def __init__(self, selected_pad):
        self.selected_drum_pad = selected_pad


class FakeDrumRack:
    def __init__(self, selected_pad_note=36, bank=None):
        self.can_have_drum_pads = True
        # Real Live API: RackDevice.visible_drum_pads (the current 4x4 bank).
        self.visible_drum_pads = bank
        self.view = FakeDeviceView(FakePad(selected_pad_note))


class FakeTrackView:
    def __init__(self, device):
        self.selected_device = device


class FakeTrack:
    def __init__(self, device):
        self.view = FakeTrackView(device)
        # Live.Track.arrangement_clips (RO list). create_midi_clip inserts here.
        self.arrangement_clips = []

    def create_midi_clip(self, start_time, length):
        clip = FakeClip(start_time=start_time)
        clip._created_length = length
        self.arrangement_clips.append(clip)
        return clip


class FakeClipSlot:
    def __init__(self, clip=None):
        self.clip = clip
        self.has_clip = clip is not None
        self.created_with = None

    def create_clip(self, length):
        self.created_with = length
        self.clip = FakeClip()
        self.has_clip = True


class FakeSongView:
    def __init__(self, device, clip, highlighted_slot=None):
        self.selected_track = FakeTrack(device)
        self.detail_clip = clip
        self.highlighted_clip_slot = highlighted_slot


class FakeSong:
    def __init__(self, device, clip, highlighted_slot=None,
                 loop_start=0.0, loop_length=BAR_BEATS * 4):
        self.view = FakeSongView(device, clip, highlighted_slot)
        self.loop_start = loop_start
        self.loop_length = loop_length


class FakeApplicationView:
    def __init__(self, focused_document_view='Session'):
        self.focused_document_view = focused_document_view


class FakeApplication:
    def __init__(self, focused_document_view='Session'):
        self.view = FakeApplicationView(focused_document_view)


class FakeManager:
    def __init__(self, device, clip, highlighted_slot=None,
                 focused_document_view='Session',
                 loop_start=0.0, loop_length=BAR_BEATS * 4):
        self._song = FakeSong(device, clip, highlighted_slot,
                              loop_start=loop_start, loop_length=loop_length)
        self._app = FakeApplication(focused_document_view)

    def song(self):
        return self._song

    def application(self):
        return self._app

    def log_message(self, *a, **k):
        pass


def _controller_with(clip, device=None, hud=None):
    device = device if device is not None else FakeDrumRack(36)
    return DrumRackController(FakeManager(device, clip), hud_client=hud)


class TestDrumRackRuntimeToggle(unittest.TestCase):
    def test_tap_adds_note_on_empty_step(self):
        clip = FakeClip()
        c = _controller_with(clip)
        c.step_event(3, 127)  # press
        c.step_event(3, 0)    # release -> toggle
        self.assertEqual(len(clip.notes), 1)
        n = clip.notes[0]
        self.assertEqual(n.pitch, 36)
        self.assertAlmostEqual(n.start_time, 3 * STEP_BEATS)
        self.assertAlmostEqual(n.duration, STEP_BEATS)
        self.assertEqual(n.velocity, DEFAULT_VELOCITY)

    def test_tap_removes_note_on_filled_step(self):
        clip = FakeClip([FakeNote(36, 3 * STEP_BEATS)])
        c = _controller_with(clip)
        c.step_event(3, 127)
        c.step_event(3, 0)
        self.assertEqual(clip.notes, [])

    def test_toggle_targets_selected_pad_pitch(self):
        clip = FakeClip()
        c = _controller_with(clip, device=FakeDrumRack(40))
        c.step_event(0, 127)
        c.step_event(0, 0)
        self.assertEqual(clip.notes[0].pitch, 40)

    def test_inert_when_not_drum_rack(self):
        clip = FakeClip()
        device = FakeDrumRack(36)
        device.can_have_drum_pads = False
        c = _controller_with(clip, device=device)
        c.step_event(0, 127)
        c.step_event(0, 0)
        self.assertEqual(clip.notes, [])


class TestDrumRackClipCreate(unittest.TestCase):
    def test_creates_one_bar_clip_when_no_detail_clip(self):
        from source_modules.drum_rack import BAR_BEATS
        slot = FakeClipSlot(clip=None)  # empty highlighted slot, no detail clip
        c = DrumRackController(FakeManager(FakeDrumRack(36), None, highlighted_slot=slot))
        c.step_event(2, 127)
        c.step_event(2, 0)  # first interaction hits the create-clip fallback
        self.assertEqual(slot.created_with, BAR_BEATS)
        self.assertTrue(slot.has_clip)
        self.assertEqual(len(slot.clip.notes), 1)
        self.assertAlmostEqual(slot.clip.notes[0].start_time, 2 * STEP_BEATS)

    def test_no_clip_and_no_slot_is_safe_noop(self):
        c = DrumRackController(FakeManager(FakeDrumRack(36), None, highlighted_slot=None))
        c.step_event(0, 127)
        c.step_event(0, 0)  # nothing to edit, must not raise

    def test_session_mode_still_uses_highlighted_slot(self):
        # focused view defaults to 'Session': the arrangement branch must not fire.
        slot = FakeClipSlot(clip=None)
        mgr = FakeManager(FakeDrumRack(36), None, highlighted_slot=slot)
        c = DrumRackController(mgr)
        c.step_event(2, 127)
        c.step_event(2, 0)
        self.assertTrue(slot.has_clip)
        self.assertEqual(mgr.song().view.selected_track.arrangement_clips, [])


class TestDrumRackArrangementClip(unittest.TestCase):
    def _arranger_manager(self, loop_start=0.0, loop_length=BAR_BEATS * 4):
        return FakeManager(FakeDrumRack(36), None, highlighted_slot=None,
                           focused_document_view='Arranger',
                           loop_start=loop_start, loop_length=loop_length)

    def test_creates_single_looping_clip_spanning_the_loop(self):
        mgr = self._arranger_manager(loop_start=0.0, loop_length=BAR_BEATS * 4)
        c = DrumRackController(mgr)
        c.step_event(2, 127)
        c.step_event(2, 0)  # first tap -> create the arrangement clip
        clips = mgr.song().view.selected_track.arrangement_clips
        self.assertEqual(len(clips), 1)  # ONE clip, not four tiled copies
        clip = clips[0]
        self.assertAlmostEqual(clip.start_time, 0.0)
        self.assertAlmostEqual(clip._created_length, BAR_BEATS * 4)  # fills the loop
        self.assertTrue(clip.looping)                                # repeats...
        self.assertAlmostEqual(clip.loop_start, 0.0)
        self.assertAlmostEqual(clip.loop_end, BAR_BEATS)             # ...every bar
        self.assertEqual(len(clip.notes), 1)                         # step edit landed
        self.assertAlmostEqual(clip.notes[0].start_time, 2 * STEP_BEATS)

    def test_clip_created_at_loop_start_offset(self):
        mgr = self._arranger_manager(loop_start=BAR_BEATS * 8, loop_length=BAR_BEATS * 2)
        c = DrumRackController(mgr)
        c.step_event(0, 127)
        c.step_event(0, 0)
        clip = mgr.song().view.selected_track.arrangement_clips[0]
        self.assertAlmostEqual(clip.start_time, BAR_BEATS * 8)
        self.assertAlmostEqual(clip._created_length, BAR_BEATS * 2)

    def test_created_clip_becomes_detail_clip(self):
        mgr = self._arranger_manager()
        c = DrumRackController(mgr)
        c.step_event(0, 127)
        c.step_event(0, 0)
        clip = mgr.song().view.selected_track.arrangement_clips[0]
        self.assertIs(mgr.song().view.detail_clip, clip)

    def test_second_edit_reuses_same_clip(self):
        # Idempotency: repeated taps must not spawn a new clip each time.
        mgr = self._arranger_manager()
        c = DrumRackController(mgr)
        c.step_event(0, 127)
        c.step_event(0, 0)
        c.step_event(4, 127)
        c.step_event(4, 0)
        clips = mgr.song().view.selected_track.arrangement_clips
        self.assertEqual(len(clips), 1)
        self.assertEqual(len(clips[0].notes), 2)

    def test_loop_shorter_than_a_bar_still_makes_at_least_one_bar(self):
        mgr = self._arranger_manager(loop_start=0.0, loop_length=BAR_BEATS / 2)
        c = DrumRackController(mgr)
        c.step_event(0, 127)
        c.step_event(0, 0)
        clip = mgr.song().view.selected_track.arrangement_clips[0]
        self.assertAlmostEqual(clip._created_length, BAR_BEATS)
        self.assertAlmostEqual(clip.loop_end, BAR_BEATS)


class TestDrumRackIsActive(unittest.TestCase):
    def test_active_on_drum_rack(self):
        c = _controller_with(FakeClip())
        self.assertTrue(c.is_active())

    def test_inactive_on_non_drum_rack(self):
        device = FakeDrumRack(36)
        device.can_have_drum_pads = False
        c = _controller_with(FakeClip(), device=device)
        self.assertFalse(c.is_active())


class TestPadOrientationMapping(unittest.TestCase):
    """Controller pads are numbered top-down; Live's drum bank is bottom-up."""

    def test_corners_flip_vertically(self):
        from source_modules.drum_rack import bank_index_from_controller as m
        self.assertEqual(m(0), 12)   # controller top-left    -> Live top-left
        self.assertEqual(m(3), 15)   # controller top-right    -> Live top-right
        self.assertEqual(m(12), 0)   # controller bottom-left  -> Live bottom-left (note 36)
        self.assertEqual(m(15), 3)   # controller bottom-right -> Live bottom-right

    def test_columns_are_preserved(self):
        from source_modules.drum_rack import bank_index_from_controller as m
        # Same column, walking top-down the controller = bottom-up the bank.
        self.assertEqual([m(i) for i in (1, 5, 9, 13)], [13, 9, 5, 1])

    def test_is_an_involution(self):
        # Flipping twice returns the original index.
        from source_modules.drum_rack import bank_index_from_controller as m
        self.assertEqual([m(m(i)) for i in range(16)], list(range(16)))


class TestDrumRackPadSelect(unittest.TestCase):
    def _bank(self):
        return [FakePad(36 + i, name=f"Pad{i}") for i in range(16)]

    def test_top_left_controller_selects_top_row_of_bank(self):
        # Regression for the top-down/bottom-up mismatch: tapping the top-left
        # controller pad must select note 48 (Live's top-left), not note 36.
        bank = self._bank()
        clip = FakeClip()
        c = _controller_with(clip, device=FakeDrumRack(36, bank=bank))
        c.select_pad(0)
        c.step_event(0, 127)
        c.step_event(0, 0)
        self.assertEqual(clip.notes[0].pitch, 48)

    def test_bottom_left_controller_selects_note_36(self):
        bank = self._bank()
        clip = FakeClip()
        c = _controller_with(clip, device=FakeDrumRack(36, bank=bank))
        c.select_pad(12)
        c.step_event(0, 127)
        c.step_event(0, 0)
        self.assertEqual(clip.notes[0].pitch, 36)

    def test_select_pad_redirects_step_edits(self):
        # Controller index 5 (2nd row, 2nd col from the top) flips to bank index 9
        # (note 45) because Live lays the bank out bottom-up.
        bank = self._bank()
        clip = FakeClip()
        c = _controller_with(clip, device=FakeDrumRack(36, bank=bank))
        c.select_pad(5)
        c.step_event(0, 127)
        c.step_event(0, 0)
        self.assertEqual(clip.notes[0].pitch, 45)

    def test_select_pad_mirrors_to_live_ui(self):
        # Controller index 3 (top-right) mirrors to Live's top-right pad = bank[15].
        bank = self._bank()
        device = FakeDrumRack(36, bank=bank)
        c = _controller_with(FakeClip(), device=device)
        c.select_pad(3)
        self.assertIs(device.view.selected_drum_pad, bank[15])

    def test_selection_falls_back_to_live_selected_pad(self):
        # No controller selection yet -> edits Live's mouse-selected pad.
        clip = FakeClip()
        c = _controller_with(clip, device=FakeDrumRack(44))
        c.step_event(2, 127)
        c.step_event(2, 0)
        self.assertEqual(clip.notes[0].pitch, 44)

    def test_select_pad_inert_on_non_drum_rack(self):
        device = FakeDrumRack(36, bank=self._bank())
        device.can_have_drum_pads = False
        c = _controller_with(FakeClip(), device=device)
        c.select_pad(5)  # must not raise; selection index recorded but no device edit
        self.assertFalse(c.is_active())


class TestDrumRackNoLongNote(unittest.TestCase):
    """The hold-A-tap-B long-note gesture was removed; overlapping presses are now
    just two independent single-step toggles."""

    def test_overlapping_presses_make_two_independent_one_step_notes(self):
        clip = FakeClip()
        c = _controller_with(clip)
        c.step_event(2, 127)   # press A=2
        c.step_event(6, 127)   # press B=6 while A still held
        c.step_event(6, 0)     # release B -> toggle step 6
        c.step_event(2, 0)     # release A -> toggle step 2
        self.assertEqual(len(clip.notes), 2)
        by_start = sorted(clip.notes, key=lambda n: n.start_time)
        self.assertAlmostEqual(by_start[0].start_time, 2 * STEP_BEATS)
        self.assertAlmostEqual(by_start[0].duration, STEP_BEATS)
        self.assertAlmostEqual(by_start[1].start_time, 6 * STEP_BEATS)
        self.assertAlmostEqual(by_start[1].duration, STEP_BEATS)


class TestDrumRackVelocity(unittest.TestCase):
    def test_sets_velocity_of_existing_note(self):
        note = FakeNote(36, 4 * STEP_BEATS)
        clip = FakeClip([note])
        c = _controller_with(clip)
        c.set_velocity(4, 100)
        self.assertEqual(note.velocity, 100)

    def test_empty_step_is_noop(self):
        clip = FakeClip()
        c = _controller_with(clip)
        c.set_velocity(4, 100)  # nothing there
        self.assertEqual(clip.notes, [])

    def test_velocity_clamped_to_1_127(self):
        note = FakeNote(36, 0.0)
        clip = FakeClip([note])
        c = _controller_with(clip)
        c.set_velocity(0, 0)
        self.assertEqual(note.velocity, 1)


class TestDrumRackPattern(unittest.TestCase):
    def test_pattern_reflects_filled_steps(self):
        clip = FakeClip([FakeNote(36, 0.0), FakeNote(36, 4 * STEP_BEATS)])
        c = _controller_with(clip)
        p = c.pattern()
        self.assertEqual(len(p), 16)
        self.assertEqual(p[0], 'X')
        self.assertEqual(p[4], 'X')
        self.assertEqual(p[1], '.')

    def test_hud_emitted_on_edit(self):
        sent = []

        class FakeHud:
            def send_drum(self, name, pattern):
                sent.append((name, pattern))

        clip = FakeClip()
        c = _controller_with(clip, hud=FakeHud())
        c.step_event(0, 127)
        c.step_event(0, 0)
        self.assertTrue(sent)
        name, pattern = sent[-1]
        self.assertEqual(name, 'Kick')
        self.assertEqual(pattern[0], 'X')


if __name__ == '__main__':
    unittest.main()
