from _Framework.ControlSurface import ControlSurface

class Functions(ControlSurface):
    def __init__(self, c_instance=None, publish_self=True, *a, **k):
        super().__init__(c_instance=c_instance)

    def selected_device(self):
        return self.song().view.selected_track.view.selected_device
