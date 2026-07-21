import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ableton_control_surface_as_code.gen_code import functions_templates
from ableton_control_surface_as_code.model_functions import FunctionLookup, Functions, \
    build_functions_model_v2
from ableton_control_surface_as_code.model_v2 import build_validated_model
from tests.builders import build_functions_with_midi, build_1_group_controller
from tests.custom_assertions import CustomAssertions


class TestFunctionsTemplates(unittest.TestCase, CustomAssertions):
    def test_function_generated(self):
        midi = build_functions_with_midi(channel=1, number=51, type="CC", function="toggle")

        result = functions_templates(midi, "mode_1")[0]

        self.assert_string_in_one('def button_ch1_51_CC__mode_mode_1_fn_toggle_listener(self, value):', result.listener_fns)


class TestHudNameDecorator(unittest.TestCase):
    """The generator reads an `@hud_name("...")` decorator on a Functions method
    statically and uses the string as that button's HUD label."""

    def _inspect(self, source, fn_name):
        with TemporaryDirectory() as d:
            path = Path(d) / "functions.py"
            path.write_text(textwrap.dedent(source))
            return FunctionLookup.inspect_python_file(path, fn_name)

    def test_no_decorator_yields_none_hud_name(self):
        parameter_len, hud_name, hud_glyph = self._inspect(
            """
            class Functions:
                def back8(self):
                    pass
            """, "back8")
        self.assertEqual(parameter_len, 0)
        self.assertIsNone(hud_name)
        self.assertIsNone(hud_glyph)

    def test_decorator_label_is_extracted(self):
        parameter_len, hud_name, hud_glyph = self._inspect(
            """
            class Functions:
                @hud_name("Back 8")
                def back8(self):
                    pass
            """, "back8")
        self.assertEqual(parameter_len, 0)
        self.assertEqual(hud_name, "Back 8")
        self.assertIsNone(hud_glyph)

    def test_decorator_coexists_with_a_value_parameter(self):
        parameter_len, hud_name, _glyph = self._inspect(
            """
            class Functions:
                @hud_name("Set X")
                def set_x(self, value):
                    pass
            """, "set_x")
        self.assertEqual(parameter_len, 1)
        self.assertEqual(hud_name, "Set X")

    def test_glyph_from_second_positional_arg(self):
        parameter_len, hud_name, hud_glyph = self._inspect(
            """
            class Functions:
                @hud_name("Loop Expand", "arrow.left.and.right")
                def loop_expand(self):
                    pass
            """, "loop_expand")
        self.assertEqual(hud_name, "Loop Expand")
        self.assertEqual(hud_glyph, "arrow.left.and.right")

    def test_glyph_from_keyword_arg(self):
        parameter_len, hud_name, hud_glyph = self._inspect(
            """
            class Functions:
                @hud_name("Loop Move", glyph="arrowshape.right.fill")
                def loop_move(self):
                    pass
            """, "loop_move")
        self.assertEqual(hud_name, "Loop Move")
        self.assertEqual(hud_glyph, "arrowshape.right.fill")


# A minimal button controller so `row-1:1` resolves in the model-integration
# test below.
_BUTTON_CONTROLLER_NT = textwrap.dedent("""\
    light_colors:
        off: 12
    control_groups:
      -
        layout: row
        number: 1
        type: button
        midi_channel: 1
        midi_type: note
        midi_range: C2-G2
    """)


class TestSharedFunctionsFile(unittest.TestCase, CustomAssertions):
    """A single shared functions file (e.g. ck_functions.py) can back many
    surfaces instead of a per-surface functions.py copy. See
    ai-coding/plans/shared-functions-file-plan.md."""

    def test_functions_resolved_from_explicit_shared_path(self):
        # A function that exists ONLY in the shared file (not next to the
        # mapping) must resolve when functions_path points at the shared file.
        with TemporaryDirectory() as d:
            shared = Path(d) / "ck_functions.py"
            shared.write_text(textwrap.dedent("""\
                class Functions:
                    def only_in_shared(self, value):
                        pass
                """))
            mapping = Functions(mappings={'only_in_shared': 'row-1:1'})
            result = build_functions_model_v2(
                build_1_group_controller(), mapping,
                root_dir=Path('/nonexistent'), functions_path=shared)

            self.assertEqual(1, len(result.midi_maps))
            self.assertEqual('only_in_shared', result.midi_maps[0].function_name)
            self.assertEqual(1, result.midi_maps[0].parameter_len)

    def test_defaults_to_functions_py_next_to_mapping(self):
        # Backward compatibility: with no functions_path, resolution still reads
        # functions.py next to the mapping.
        with TemporaryDirectory() as d:
            (Path(d) / "functions.py").write_text(textwrap.dedent("""\
                class Functions:
                    def local_fn(self):
                        pass
                """))
            mapping = Functions(mappings={'local_fn': 'row-1:1'})
            result = build_functions_model_v2(
                build_1_group_controller(), mapping, root_dir=Path(d))

            self.assertEqual('local_fn', result.midi_maps[0].function_name)

    def test_functions_file_key_threads_through_the_model(self):
        # End-to-end through the parser: `functions_file:` in the mapping points
        # resolution at a shared file, resolved relative to the mapping.
        with TemporaryDirectory() as d:
            root_dir = Path(d)
            (root_dir / "shared").mkdir()
            (root_dir / "shared" / "ck_functions.py").write_text(textwrap.dedent("""\
                class Functions:
                    def shared_only(self):
                        pass
                """))
            mapping_text = textwrap.dedent("""\
                controller: controller.nt
                ableton_dir: /tmp
                hud: off
                show-hud-on: selection
                functions_file: shared/ck_functions.py
                mappings:
                    -
                        type: functions
                        mappings:
                            shared_only: row-1:1
                """)

            def resolve_controller(root):
                return _BUTTON_CONTROLLER_NT, "controller.nt"

            root, _controller, mode_with_midi = build_validated_model(
                mapping_text, root_dir, resolve_controller=resolve_controller)

            self.assertEqual(root.functions_file, "shared/ck_functions.py")
            fn_names = [
                m.function_name
                for _mode, mappings in mode_with_midi.mappings
                for mapping in mappings if getattr(mapping, 'type', None) == 'functions'
                for m in mapping.midi_maps
            ]
            self.assertIn('shared_only', fn_names)

