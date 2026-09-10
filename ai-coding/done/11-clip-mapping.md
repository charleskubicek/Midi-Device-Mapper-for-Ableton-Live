Introduce new mappings for clips.

when a clip is selected, and the HUD is visible the user can change clip attributes with the encoders and buttons.

Ableton functions that can be modified are:


"gain" (encoder)
"pitch_coarse", (encoder)
"pitch_fine", (encoder)
"duplicate_loop" (button)
"looping", (button: left/right extend)
"loop_start", (button: left/right extend)
"loop_end", (button: left/right extend)
"warping", (button: on/off)
"start_marker", (button: left/right extend)
"end_marker", (button: left/right extend)

And new buttons we'll add that use these are:

- sync_loop_and_markers: set start_marker = loop_start and end_marker = loop_end
- move_clip_one_beat_forward/backward: moves the clip forward or backward by one beat
- move_clip_one_bar_forward/backward: moves the clip forward or backward by one beat

please see this file for examples of usage: /Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts/AbletonOSC/abletonosc/clip.py
remember to use @dev-docs/Live.md for background info, or even query ocde in directory above.

The HUD MUST tell the user what they are about to edit. If a clip is selected, it shoudl move to the bottom of the ableton window, out of the way.

if there is a clash on mapping encoders with the device mapper, it should be fine as the clip mappings only apply when a clip is selected, and the device mappings only apply when a device is selected, and these two states are mutually exclusive in the current implementation of the HUD. If there is a clash on buttons, then the clip mapping should take precedence over the device mapping when a clip is selected. You should be able to find that out by getting information from the views we used previously.

