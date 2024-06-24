import json
from pathlib import Path
script_template = """
from ableton.v2.control_surface import ControlSurface
from ableton.v2.control_surface.components import MixerComponent, SessionComponent
from ableton.v2.control_surface.elements import EncoderElement, ConfigurableButtonElement
from ableton.v2.control_surface.input_control_element import MIDI_NOTE_TYPE, MIDI_CC_TYPE
import Live

class CustomScript(ControlSurface):
    def __init__(self, c_instance):
        super(CustomScript, self).__init__(c_instance)
        with self.component_guard():
            self._setup_controls()
            self._setup_session()
            self._setup_mixer()
            
            #self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            #self._socket.setblocking(0)
            #self._socket.bind(('0.0.0.0', 11111))

    def _setup_controls(self):
{encoder_lines}
{button_lines}

    def tick(self):
        data, addr = self._socket.recvfrom(1024)
        if data == b'reload':
            try:
                #importlib.reload(sys.modules[module_name])
                print('Reloading module')
            except Exception as e:
                print(f'Error reloading module:')
    
    
        self.schedule_message(1, self.tick)

    # def _setup_session(self):
    #     self._session = SessionComponent(num_tracks=8, num_scenes=1)
    #     self._session.set_enabled(True)
    # 
    # def _setup_mixer(self):
    #     self._mixer = MixerComponent(num_tracks=8)
    #     self._mixer.set_enabled(True)
    """

def generate_ableton_script(json_data):
    encoders = json_data.get('encoders', [])
    buttons = json_data.get('buttons', [])

    encoder_lines = []

    for encoder in encoders:
        midi_type = "MIDI_CC_TYPE" if encoder['type'] == 'CC' else "MIDI_NOTE_TYPE"
        encoder_lines.append(f"        self.encoder_{encoder['value']} = EncoderElement({midi_type}, {encoder['midi_channel']}, {encoder['value']}, Live.MidiMap.MapMode.relative_binary_offset)")

    button_lines = []
    for button in buttons:
        midi_type = "MIDI_CC_TYPE" if button['type'] == 'CC' else "MIDI_NOTE_TYPE"
        button_lines.append(f"        self.button_{button['value']} = ConfigurableButtonElement({midi_type}, {button['midi_channel']}, {button['value']})")


    # return "\n".join(script_code)


    return script_template.format(encoder_lines='\n'.join(encoder_lines), button_lines='\n'.join(button_lines))

# Example usage
json_description = '''
{
  "encoders": [
    {"midi_channel": 1, "type": "CC", "value": 21},
    {"midi_channel": 1, "type": "CC", "value": 22}
  ],
  "buttons": [
    {"midi_channel": 1, "type": "note", "value": 36},
    {"midi_channel": 1, "type": "note", "value": 37}
  ]
}
'''

json_data = json.loads(json_description)
script = generate_ableton_script(json_data)
Path("../../out/generated.py").write_text(script)
