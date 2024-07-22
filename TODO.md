# TODO

- [x] Non-contiguous rows/columns
- [x] Button toggle
- [x] Modes
- [x] Auto encoder min/max-
- [x] User functions
- [x] Transport functions
- [x] Print ascii text of controller layout
- [x] Device: go to named top-level device
- [x] Track: go to named track

# TOIL
- [x] replace EncoderCoords with EncoderCoordsV2_1

### Next
- [x] Use dashes in row names and mode names (row_2 -> row-2)
- [ ] Deploy from github
- [ ] first/last device toggle
- [ ] inst/last device toggle
- [ ] Test numbered track
- [ ] Test nav buttons on LC
- [x] Switch modes
- [ ] Spike auto-device mode
- [ ] Spike Continuous controllers
- [ ] Spike Grids
- [ ] Encoder value custom min/max
- [ ] More than 2 modes
- [ ] Extract mode to separate class
- [ ] Nicer error messages on validation fail


## Transport

Call methods on song:
- play, stop, record, metronome, tempo_up, tempo_down, loop, overdub, punch_in, punch_out, loop

## Notes

C-2 (MIDI note 0): This is the lowest note that can be represented in the MIDI protocol.
A0 (MIDI note 21): This is often the lowest note on a standard 88-key piano.
C4 (MIDI note 60): This is known as Middle C.
A4 (MIDI note 69): This is the A above Middle C, commonly used as the standard tuning pitch (440 Hz in most cases).
C8 (MIDI note 108): This is the highest C on a standard 88-key piano.
G8 (MIDI note 127): This is the highest note in the MIDI range.

## Non-contiguous rows/columns
- Allow for partial rows
- Allow for a list of buttons to be set


## Button toggle
https://help.ableton.com/hc/en-us/articles/209774945-Toggle-and-Momentary-MIDI-functions

Momentary - Button down sends 127, button up sends 0
Toggle - On sends 127, next on sends 127

https://nickfever.com/music/midi-cc-list