from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import *
from _Framework.EncoderElement import EncoderElement
from _Framework.MixerComponent import MixerComponent
from Launchpad.ConfigurableButtonElement import ConfigurableButtonElement

# from _Framework.EncoderElement import *

class $class_name_camel(ControlSurfaceComponent):
    def __init__(self, manager):
        super().__init__(manager)
        self.class_identifier = "$class_name_snake"

        self.manager = manager

        self.mixer = MixerComponent(124, 24)
        # self.setup_controls()
        # self.setup_listeners()

        $code_setup

    def remove_all_listeners(self):
        $code_remove_listeners


    def setup_controls(self):
        $code_creation

        self.setup_listeners()

    def setup_listeners(self):
        self.log_message("Setting up listeners")
        $code_setup_listeners

    def log_message(self, message):
        self.manager.log_message(message)

    $code_listener_fns
