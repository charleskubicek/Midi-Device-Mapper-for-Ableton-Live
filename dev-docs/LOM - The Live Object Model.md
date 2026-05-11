---
title: "LOM - The Live Object Model -  Max 8 Documentation"
source: "https://docs.cycling74.com/legacy/max8/vignettes/live_object_model?q=LOM"
author:
published:
created: 2026-05-11
description: "LOM - The Live Object Model Objects which comprise the Live API described by their structure, properties and functions. Introduction The Live Object Model lists"
tags:
  - "clippings"
---
## LOM - The Live Object Model

*Objects which comprise the Live API described by their structure, properties and functions.*

## Introduction

The Live Object Model lists a number of Live object classes with their properties and functions, as well as their parent-child relations through which a hierarchy is formed. Please refer to the [Live API overview chapter](https://docs.cycling74.com/max8/vignettes/live_api_overview) for definitions of the basic Live API terms and a list of the Max objects used to access it.  
  
*This document refers to Ableton Live version 12.1*

## Object Model Overview

*Click on the classes to navigate to their description.*

Expand

## Application

This class represents the Live application. It is reachable by the root path live\_app.

#### Canonical path

###### live\_app

#### Children

##### view

Type Application.View

Accessget

###### Description

##### control\_surfaces

Typelist of ControlSurface

Accessget, observe

###### Description

A list of the control surfaces currently selected in Live's Preferences.  
If None is selected in any of the slots or the script is inactive (e.g. when Push2 is selected, but no Push is connected), id 0 will be returned at those indices.

#### Properties

##### current\_dialog\_button\_count

Type int

Accessget

###### Description

The number of buttons in the current message box.

##### current\_dialog\_message

Type symbol

Accessget

###### Description

The text of the current message box (empty if no message box is currently shown).

##### open\_dialog\_count

Type int

Accessget, observe

###### Description

The number of dialog boxes shown.

##### average\_process\_usage

Type float

Accessget, observe

###### Description

Reports Live's average CPU load.  
  
Note that Live's CPU meter shows the audio processing load but not Live's overall CPU usage.

##### peak\_process\_usage

Type float

Accessget, observe

###### Description

Reports Live's peak CPU load.  
  
Note that Live's CPU meter shows the audio processing load but not Live's overall CPU usage.

#### Functions

##### get\_bugfix\_version

Returns: the 2 in Live 9.1.2.

##### get\_document

Returns: the current Live Set.

##### get\_major\_version

Returns: the 9 in Live 9.1.2.

##### get\_minor\_version

Returns: the 1 in Live 9.1.2.

##### get\_version\_string

Returns: the text 9.1.2 in Live 9.1.2.

##### press\_current\_dialog\_button

Parameter: *index*  
Press the button with the given index in the current dialog box.

## Application.View

This class represents the aspects of the Live application related to viewing the application.

#### Canonical path

###### live\_app view

#### Children

None

#### Properties

##### browse\_mode

Type bool

Accessget, observe

###### Description

1 = Hot-Swap Mode is active for any target.

##### focused\_document\_view

Type unicode

Accessget, observe

###### Description

The name of the currently visible view in the focused Live window ('Session' or 'Arranger').

#### Functions

##### available\_main\_views

Returns: *view names* \[list of symbols\].  
This is a constant list of view names to be used as an argument when calling other functions: Browser Arranger Session Detail Detail/Clip Detail/DeviceChain.

##### focus\_view

Parameter: *view\_name*  
Shows named view and focuses on it. You can also pass an empty view\_name “ ", which refers to the Arrangement or Session View (whichever is visible in the main window).

##### hide\_view

Parameter: *view\_name*  
Hides the named view. You can also pass an empty view\_name “ ", which refers to the Arrangement or Session View (whichever is visible in the main window).

##### is\_view\_visible

Parameter: *view\_name*  
Returns: \[bool\] Whether the specified view is currently visible.

##### scroll\_view

Parameters: *direction view\_name modifier\_pressed*  
*direction* \[int\] is 0 = up, 1 = down, 2 = left, 3 = right  
*modifier\_pressed* \[bool\] If view\_name is "Arranger" and modifier\_pressed is 1 and direction is left or right, then the size of the selected time region is modified, otherwise the position of the playback cursor is moved.  
Not all views are scrollable, and not in all directions. Currently, only the Arranger, Browser, Session, and Detail/DeviceChain views can be scrolled.  
You can also pass an empty view\_name " ", which refers to the Arrangement or Session View (whichever view is visible).

##### show\_view

Parameter: *view\_name*

##### toggle\_browse

Displays the device chain and the browser and activates Hot-Swap Mode for the selected device. Calling this function again deactivates Hot-Swap Mode.

##### zoom\_view

Parameter: *direction view\_name modifier\_pressed*  
*direction* \[int\] - 0 = up, 1 = down, 2 = left, 3 = right  
*modifier\_pressed* \[bool\] If view\_name is 'Arrangement', modifier\_pressed is 1, and direction is left or right, then the size of the selected time region is modified, otherwise the position of the playback cursor is moved. If view\_name is Arrangement and modifier\_pressed is 1 and direction is up or down, then only the height of the highlighted track is changed, otherwise the height of all tracks is changed.  
Only the Arrangement and Session Views can be zoomed. For Session View, the behaviour of zoom\_view is identical to scroll\_view. You can also pass an empty view\_name “ ", which refers to the Arrangement or Session View (whichever is visible in the main window).

## TuningSystem

This class represents a tuning system in Live.

#### Canonical path

###### live\_set tuning\_system

#### Properties

##### name

Type symbol

Accessget, set, observe

###### Description

The name of the currently active tuning system.

##### pseudo\_octave\_in\_cents

Type float

Accessget

###### Description

The pseudo octave in cents of the currently active tuning system.

##### lowest\_note

Type dictionary

Accessget, set, observe

###### Description

The note index within the pseudo octave and octave of the lowest note.

##### highest\_note

Type dictionary

Accessget, set, observe

###### Description

The note index within the pseudo octave and octave of the highest note.

##### reference\_pitch

Type dictionary

Accessget, set, observe

###### Description

The reference pitch of the current tuning system.

##### note\_tunings

Type list

Accessget, set, observe

###### Description

The relative note tunings of the Tuning System in cents.

## Song

This class represents a Live Set. The current Live Set is reachable by the root path live\_set.

#### Canonical path

###### live\_set

#### Children

##### cue\_points

Typelist of CuePoint

Accessget, observe

###### Description

Cue points are the markers in the Arrangement to which you can jump.

##### return\_tracks

Typelist of Track

Accessget, observe

###### Description

##### scenes

Typelist of Scene

Accessget, observe

###### Description

##### tracks

Typelist of Track

Accessget, observe

###### Description

##### visible\_tracks

Typelist of Track

Accessget, observe

###### Description

A track is visible if it's not part of a folded group. If a track is scrolled out of view it's still considered visible.

##### master\_track

Type Track

Accessget

###### Description

##### view

Type Song.View

Accessget

###### Description

##### groove\_pool

Type GroovePool

Accessget

###### Description

Live's groove pool.  
  
*Available since Live 11.0.*

##### tuning\_system

Type TuningSystem

Accessget, observe

###### Description

Live's currently active tuning system.

#### Properties

##### appointed\_device

Type Device

Accessget, observe

###### Description

The appointed device is the one used by a control surface unless the control surface itself chooses which device to use. It is marked by a blue hand.

##### arrangement\_overdub

Type bool

Accessget, set, observe

###### Description

Get/set the state of the MIDI Arrangement Overdub button.

##### back\_to\_arranger

Type bool

Accessget, set, observe

###### Description

Get/set/observe the current state of the Back to Arrangement button located in Live's transport bar (1 = highlighted). This button is used to indicate that the current state of the playback differs from what is stored in the Arrangement.  
  
Setting this property to 0 will make Live go back to playing the content of the arrangement.

##### can\_capture\_midi

Type bool

Accessget, observe

###### Description

1 = Recently played MIDI material exists that can be captured into a Live Track. See *capture\_midi*.

##### can\_jump\_to\_next\_cue

Type bool

Accessget, observe

###### Description

0 = there is no cue point to the right of the current one, or none at all.

##### can\_jump\_to\_prev\_cue

Type bool

Accessget, observe

###### Description

0 = there is no cue point to the left of the current one, or none at all.

##### can\_redo

Type bool

Accessget

###### Description

1 = there is something in the history to redo.

##### can\_undo

Type bool

Accessget

###### Description

1 = there is something in the history to undo.

##### clip\_trigger\_quantization

Type int

Accessget, set, observe

###### Description

Reflects the quantization setting in the transport bar.  
0 = None  
1 = 8 Bars  
2 = 4 Bars  
3 = 2 Bars  
4 = 1 Bar  
5 = 1/2  
6 = 1/2T  
7 = 1/4  
8 = 1/4T  
9 = 1/8  
10 = 1/8T  
11 = 1/16  
12 = 1/16T  
13 = 1/32

##### count\_in\_duration

Type int

Accessget, observe

###### Description

The duration of the Metronome's Count-In setting as an index, mapped as follows:  
0 = None  
1 = 1 Bar  
2 = 2 Bars  
3 = 4 Bars

##### current\_song\_time

Type float

Accessget, set, observe

###### Description

The playing position in the Live Set, in beats.

##### exclusive\_arm

Type bool

Accessget

###### Description

Current status of the exclusive Arm option set in the Live preferences.

##### exclusive\_solo

Type bool

Accessget

###### Description

Current status of the exclusive Solo option set in the Live preferences.

##### file\_path

Type symbol

Accessget

###### Description

The path to the current Live Set, in OS-native format. If the Live Set hasn't been saved, the path is empty.

##### groove\_amount

Type float

Accessget, set, observe

###### Description

The groove amount from the current set's groove pool (0. - 1.0).

##### is\_ableton\_link\_enabled

Type bool

Accessget, set, observe

###### Description

Enable/disable Ableton Link. The Link toggle in the Live's transport bar must be visible to enable Link.

##### is\_ableton\_link\_start\_stop\_sync\_enabled

Type bool

Accessget, set, observe

###### Description

Enable/disable Ableton Link Start Stop Sync.

##### is\_counting\_in

Type bool

Accessget, observe

###### Description

1 = the Metronome is currently counting in.

##### is\_playing

Type bool

Accessget, set, observe

###### Description

Get/set if Live's transport is running.

##### last\_event\_time

Type float

Accessget

###### Description

The beat time of the last event (i.e. automation breakpoint, clip end, cue point, loop end) in the Arrangement.

##### loop

Type bool

Accessget, set, observe

###### Description

Get/set the enabled state of the Arrangement loop.

##### loop\_length

Type float

Accessget, set, observe

###### Description

Arrangement loop length in beats.

##### loop\_start

Type float

Accessget, set, observe

###### Description

Arrangement loop start in beats.

##### metronome

Type bool

Accessget, set, observe

###### Description

Get/set the enabled state of the metronome.

##### midi\_recording\_quantization

Type int

Accessget, set, observe

###### Description

Get/set the current Record Quantization value.  
0 = None  
1 = 1/4  
2 = 1/8  
3 = 1/8T  
4 = 1/8 + 1/8T  
5 = 1/16  
6 = 1/16T  
7 = 1/16 + 1/16T  
8 = 1/32

##### name

Type symbol

Accessget

###### Description

The name of the current Live Set. If the Live Set hasn't been saved, the name is empty.

##### nudge\_down

Type bool

Accessget, set, observe

###### Description

1 = the Tempo Nudge Down button in the transport bar is currently pressed.

##### nudge\_up

Type bool

Accessget, set, observe

###### Description

1 = the Tempo Nudge Up button in the transport bar is currently pressed.

##### tempo\_follower\_enabled

Type bool

Accessget, set, observe

###### Description

1 = the Tempo Follower controls the tempo. The Tempo Follower Toggle must be made visible in the preferences for this property to be effective.

##### overdub

Type bool

Accessget, set, observe

###### Description

1 = MIDI Arrangement Overdub is enabled in the transport.

##### punch\_in

Type bool

Accessget, set, observe

###### Description

1 = the Punch-In button is enabled in the transport.

##### punch\_out

Type bool

Accessget, set, observe

###### Description

1 = the Punch-Out button is enabled in the transport.

##### re\_enable\_automation\_enabled

Type bool

Accessget, observe

###### Description

1 = the Re-Enable Automation button is on.

##### record\_mode

Type bool

Accessget, set, observe

###### Description

1 = the Arrangement Record button is on.

##### root\_note

Type int

Accessget, set, observe

###### Description

The root note of the scale currently selected in Live. The root note can be a number between 0 and 11, where 0 = C and 11 = B.

##### scale\_intervals

Type list

Accessget, observe

###### Description

A list of integers representing the intervals in Live's current scale (see *scale\_name* and *scale\_mode*). An interval is expressed as the difference between the scale degree at the list index and the first scale degree.

##### scale\_mode

Type bool

Accessget, set, observe

###### Description

Access to the Scale Mode setting in Live.  
  
When on, key tracks that belong to the currently selected scale are highlighted in Live's MIDI Note Editor, and pitch-based parameters in MIDI Tools and Devices can be edited in scale degrees rather than semitones.  
  
See also *root\_note*, *scale\_name*, and *scale\_intervals*.

##### scale\_name

Type unicode

Accessget, set, observe

###### Description

The name of the scale selected in Live, as displayed in the Current Scale Name chooser.

##### select\_on\_launch

Type bool

Accessget

###### Description

1 = the "Select on Launch" option is set in Live's preferences.

##### session\_automation\_record

Type bool

Accessget, set, observe

###### Description

The state of the Automation Arm button.

##### session\_record

Type bool

Accessget, set, observe

###### Description

The state of the Session Overdub button.

##### session\_record\_status

Type int

Accessget, observe

###### Description

Reflects the state of the Session Record button.

##### signature\_denominator

Type int

Accessget, set, observe

###### Description

##### signature\_numerator

Type int

Accessget, set, observe

###### Description

##### song\_length

Type float

Accessget, observe

###### Description

A little more than last\_event\_time, in beats.

##### start\_time

Type float

Accessget, set, observe

###### Description

The position in the Live Set where playing will start, in beats.

##### swing\_amount

Type float

Accessget, set, observe

###### Description

Range: 0.0 - 1.0; affects MIDI Recording Quantization and all direct calls to Clip.quantize.

##### tempo

Type float

Accessget, set, observe

###### Description

Current tempo of the Live Set in BPM, 20.0... 999.0. The tempo may be automated, so it can change depending on the current song time.

#### Functions

##### capture\_and\_insert\_scene

Capture the currently playing clips and insert them as a new scene below the selected scene.

##### capture\_midi

Parameter: *destination* \[int\]  
0 = auto, 1 = session, 2 = arrangement  
Capture recently played MIDI material from audible tracks into a Live Clip.  
If *destinaton* is not set or it is set to *auto*, the Clip is inserted into the view currently visible in the focused Live window. Otherwise, it is inserted into the specified view.

##### continue\_playing

From the current playback position.

##### create\_audio\_track

Parameter: *index*  
Index determines where the track is added, it is only valid between 0 and len(song.tracks). Using an index of -1 will add the new track at the end of the list.

##### create\_midi\_track

Parameter: *index*  
Index determines where the track is added, it is only valid between 0 and len(song.tracks). Using an index of -1 will add the new track at the end of the list.

##### create\_return\_track

Adds a new return track at the end.

##### create\_scene

Parameter: *index*  
Returns: The new scene  
Index determines where the scene is added. It is only valid between 0 and len(song.scenes). Using an index of -1 will add the new scene at the end of the list.

##### delete\_scene

Parameter: *index*  
Delete the scene at the given index.

##### delete\_track

Parameter: *index*  
Delete the track at the given index.

##### delete\_return\_track

Parameter: *index*  
Delete the return track at the given index.

##### duplicate\_scene

Parameter: *index*  
Index determines which scene to duplicate.

##### duplicate\_track

Parameter: *index*  
Index determines which track to duplicate.

##### find\_device\_position

Parameter:  
*device* \[live object\]  
*target* \[live object\]  
*target position* \[int\]  
Returns:  
\[int\] The position in the target's chain where the device can be inserted that is the closest possible to the target position.

##### force\_link\_beat\_time

Force the Link timeline to jump to Live's current beat time.

##### get\_beats\_loop\_length

Returns: *bars.beats.sixteenths.ticks* \[symbol\]  
The Arrangement loop length.

##### get\_beats\_loop\_start

Returns: *bars.beats.sixteenths.ticks* \[symbol\]  
The Arrangement loop start.

##### get\_current\_beats\_song\_time

Returns: *bars.beats.sixteenths.ticks* \[symbol\]  
The current Arrangement playback position.

##### get\_current\_smpte\_song\_time

Parameter: *format*  
*format* \[int\] is the time code type to be returned  
0 = the frame position shows the milliseconds  
1 = Smpte24  
2 = Smpte25  
3 = Smpte30  
4 = Smpte30Drop  
5 = Smpte29  
Returns: *hours:min:sec:frames* \[symbol\]  
The current Arrangement playback position.

##### is\_cue\_point\_selected

Returns: bool 1 = the current Arrangement playback position is at a cue point

##### jump\_by

Parameter: *beats*  
*beats* \[double\] is the amount to jump relatively to the current position

##### jump\_to\_next\_cue

Jump to the right, if possible.

##### jump\_to\_prev\_cue

Jump to the left, if possible.

##### move\_device

Parameter:  
*device* \[live object\]  
*target* \[live object\]  
*target position* \[int\]  
Returns: \[int\] The position in the target's chain where the device was inserted.  
Move the device to the specified position in the target chain. If the device cannot be moved to the specified position, the nearest possible position is chosen.

##### play\_selection

Do nothing if no selection is set in Arrangement, or play the current selection.

##### re\_enable\_automation

Trigger 'Re-Enable Automation', re-activating automation in all running Session clips.

##### redo

Causes the Live application to redo the last operation.

##### scrub\_by

Parameter: *beats*  
*beats* \[double\] the amount to scrub relative to the current Arrangement playback position  
Same as jump\_by, at the moment.

##### set\_or\_delete\_cue

Toggle cue point at current Arrangement playback position.

##### start\_playing

Start playback from the insert marker.

##### stop\_all\_clips

Parameter (optional): *quantized*  
Calling the function with 0 will stop all clips immediately, independent of the launch quantization. The default is '1'.

##### stop\_playing

Stop the playback.

##### tap\_tempo

Same as pressing the Tap Tempo button in the transport bar. The new tempo is calculated based on the time between subsequent calls of this function.

##### trigger\_session\_record

Parameter: *record\_length (optional)*  
Starts recording in either the selected slot or the next empty slot, if the track is armed. If *record\_length* is provided, the slot will record for the given length in beats.  
If triggered while recording, recording will stop and clip playback will start.

##### undo

Causes the Live application to undo the last operation.

## Song.View

This class represents the view aspects of a Live document: the Session and Arrangement Views.

#### Canonical path

###### live\_set view

#### Children

##### detail\_clip

Type Clip

Accessget, set, observe

###### Description

The clip currently displayed in the Live application's Detail View.

##### highlighted\_clip\_slot

Type ClipSlot

Accessget, set

###### Description

The slot highlighted in the Session View.

##### selected\_chain

Type Chain

Accessget, set, observe

###### Description

The highlighted chain, or "id 0"

##### selected\_parameter

Type DeviceParameter

Accessget, observe

###### Description

The selected parameter, or "id 0"

##### selected\_scene

Type Scene

Accessget, set, observe

###### Description

##### selected\_track

Type Track

Accessget, set, observe

###### Description

#### Properties

##### draw\_mode

Type bool

Accessget, set, observe

###### Description

Reflects the state of the envelope/automation Draw Mode Switch in the transport bar, as toggled with Cmd/Ctrl-B.  
0 = breakpoint editing (shows arrow), 1 = drawing (shows pencil)

##### follow\_song

Type bool

Accessget, set, observe

###### Description

Reflects the state of the Follow switch in the transport bar as toggled with Cmd/Ctrl-F.  
0 = don't follow playback position, 1 = follow playback position

#### Functions

##### select\_device

Parameter: *id NN*  
Selects the given device object in its track.  
You may obtain the id using a [live.path](https://docs.cycling74.com/max8/refpages/live.path) or by using get devices on a track, for example.  
The track containing the device will not be shown automatically, and the device gets the appointed device (blue hand) only if its track is selected.

## GroovePool

This class represents the groove pool in Live. It provides access to the current set's list of grooves.

#### Canonical path

###### live\_set groove\_pool

#### Children

##### grooves

Typelist of Groove

Accessget, observe

###### Description

List of grooves in the groove pool from top to bottom, can be accessed via index.

## Track

This class represents a track in Live. It can either be an audio track, a MIDI track, a return track or the master track. The master track and at least one Audio or MIDI track will be always present. Return tracks are optional.  
  
Not all properties are supported by all types of tracks. The properties are marked accordingly.

#### Canonical path

###### live\_set tracks N

#### Children

##### clip\_slots

Typelist of ClipSlot

Accessget, observe

###### Description

##### arrangement\_clips

Typelist of Clip

Accessget, observe

###### Description

The list of this track's Arrangement View clip IDs  
  
*Available since Live 11.0.*

##### devices

Typelist of Device

Accessget, observe

###### Description

Includes mixer device.

##### group\_track

Type Track

Accessget

###### Description

The Group Track, if the Track is grouped. If it is not, *id 0* is returned.

##### mixer\_device

Type MixerDevice

Accessget

###### Description

##### view

Type Track.View

Accessget

###### Description

#### Properties

##### arm

Type bool

Accessget, set, observe

###### Description

1 = track is armed for recording. \[not in return/master tracks\]

##### available\_input\_routing\_channels

Type dictionary

Accessget, observe

###### Description

The list of available source channels for the track's input routing. It's represented as a *dictionary* with the following key:  
*available\_input\_routing\_channels* \[list\]  
The list contains *dictionaries* as described in *input\_routing\_channel*.  
Only available on MIDI and audio tracks.

##### available\_input\_routing\_types

Type dictionary

Accessget, observe

###### Description

The list of available source types for the track's input routing. It's represented as a *dictionary* with the following key:  
*available\_input\_routing\_types* \[list\]  
The list contains *dictionaries* as described in *input\_routing\_type*.  
Only available on MIDI and audio tracks.

##### available\_output\_routing\_channels

Type dictionary

Accessget, observe

###### Description

The list of available target channels for the track's output routing. It's represented as a *dictionary* with the following key:  
*available\_output\_routing\_channels* \[list\]  
The list contains *dictionaries* as described in *output\_routing\_channel*.  
Not available on the master track.

##### available\_output\_routing\_types

Type dictionary

Accessget, observe

###### Description

The list of available target types for the track's output routing. It's represented as a *dictionary* with the following key:  
*available\_output\_routing\_types* \[list\]  
The list contains *dictionaries* as described in *output\_routing\_type*.  
Not available on the master track.

##### back\_to\_arranger

Type bool

Accessget, set, observe

###### Description

Get/set/observe the current state of the Single Track Back to Arrangement button (1 = highlighted). This button is used to indicate that the current state of the playback differs from what is stored in the Arrangement.  
  
Setting this property to 0 will make Live go back to playing the track's arrangement content. For group tracks, this means that all of the tracks that belong to the group and any subgroups will go back to playing the arrangement.

##### can\_be\_armed

Type bool

Accessget

###### Description

0 for return and master tracks.

##### can\_be\_frozen

Type bool

Accessget

###### Description

1 = the track can be frozen, 0 = otherwise.

##### can\_show\_chains

Type bool

Accessget

###### Description

1 = the track contains an Instrument Rack device that can show chains in Session View.

##### color

Type int

Accessget, set, observe

###### Description

The RGB value of the track's color in the form 0x00rrggbb or (2^16 \* red) + (2^8) \* green + blue, where red, green and blue are values from 0 (dark) to 255 (light).  
  
When setting the RGB value, the nearest color from the track color chooser is taken.

##### color\_index

Type long

Accessget, set, observe

###### Description

The color index of the track.

##### fired\_slot\_index

Type int

Accessget, observe

###### Description

Reflects the blinking clip slot.  
\-1 = no slot fired, -2 = Clip Stop Button fired  
First clip slot has index 0.  
\[not in return/master tracks\]

##### fold\_state

Type int

Accessget, set

###### Description

0 = tracks within the Group Track are visible, 1 = Group Track is folded and the tracks within the Group Track are hidden  
\[only available if is\_foldable = 1\]

##### has\_audio\_input

Type bool

Accessget

###### Description

1 for audio tracks.

##### has\_audio\_output

Type bool

Accessget

###### Description

1 for audio tracks and MIDI tracks with instruments.

##### has\_midi\_input

Type bool

Accessget

###### Description

1 for MIDI tracks.

##### has\_midi\_output

Type bool

Accessget

###### Description

1 for MIDI tracks with no instruments and no audio effects.

##### implicit\_arm

Type bool

Accessget, set, observe

###### Description

A second arm state, only used by Push so far.

##### input\_meter\_left

Type float

Accessget, observe

###### Description

Smoothed momentary peak value of left channel input meter, 0.0 to 1.0. For tracks with audio output only. This value corresponds to the meters shown in Live. Please take into account that the left/right audio meters put a significant load onto the GUI part of Live.

##### input\_meter\_level

Type float

Accessget, observe

###### Description

Hold peak value of input meters of audio and MIDI tracks, 0.0... 1.0. For audio tracks it is the maximum of the left and right channels. The hold time is 1 second.

##### input\_meter\_right

Type float

Accessget, observe

###### Description

Smoothed momentary peak value of right channel input meter, 0.0 to 1.0. For tracks with audio output only. This value corresponds to the meters shown in Live.

##### input\_routing\_channel

Type dictionary

Accessget, set, observe

###### Description

The currently selected source channel for the track's input routing. It's represented as a *dictionary* with the following keys:  
*display\_name* \[symbol\]  
*identifier* \[symbol\]  
Can be set to all values found in the track's *available\_input\_routing\_channels*.  
Only available on MIDI and audio tracks.

##### input\_routing\_type

Type dictionary

Accessget, set, observe

###### Description

The currently selected source type for the track's input routing. It's represented as a *dictionary* with the following keys:  
*display\_name* \[symbol\]  
*identifier* \[symbol\]  
Can be set to all values found in the track's *available\_input\_routing\_types*.  
Only available on MIDI and audio tracks.

##### is\_foldable

Type bool

Accessget

###### Description

1 = track can be (un)folded to hide or reveal the contained tracks. This is currently the case for Group Tracks. Instrument and Drum Racks return 0 although they can be opened/closed. This will be fixed in a later release.

##### is\_frozen

Type bool

Accessget, observe

###### Description

1 = the track is currently frozen.

##### is\_grouped

Type bool

Accessget

###### Description

1 = the track is contained within a Group Track.

##### is\_part\_of\_selection

Type bool

Accessget

###### Description

##### is\_showing\_chains

Type bool

Accessget, set, observe

###### Description

Get or set whether a track with an Instrument Rack device is currently showing its chains in Session View.

##### is\_visible

Type bool

Accessget

###### Description

0 = track is hidden in a folded Group Track.

##### mute

Type bool

Accessget, set, observe

###### Description

\[not in master track\]

##### muted\_via\_solo

Type bool

Accessget, observe

###### Description

1 = the track or chain is muted due to Solo being active on at least one other track.

##### name

Type symbol

Accessget, set, observe

###### Description

As shown in track header.

##### output\_meter\_left

Type float

Accessget, observe

###### Description

Smoothed momentary peak value of left channel output meter, 0.0 to 1.0. For tracks with audio output only. This value corresponds to the meters shown in Live. Please take into account that the left/right audio meters add a significant load to Live GUI resource usage.

##### output\_meter\_level

Type float

Accessget, observe

###### Description

Hold peak value of output meters of audio and MIDI tracks, 0.0 to 1.0. For audio tracks, it is the maximum of the left and right channels. The hold time is 1 second.

##### output\_meter\_right

Type float

Accessget, observe

###### Description

Smoothed momentary peak value of right channel output meter, 0.0 to 1.0. For tracks with audio output only. This value corresponds to the meters shown in Live.

##### performance\_impact

Type float

Accessget, observe

###### Description

Reports the performance impact of this track.

##### output\_routing\_channel

Type dictionary

Accessget, set, observe

###### Description

The currently selected target channel for the track's output routing. It's represented as a *dictionary* with the following keys:  
*display\_name* \[symbol\]  
*identifier* \[symbol\]  
Can be set to all values found in the track's *available\_output\_routing\_channels*.  
Not available on the master track.

##### output\_routing\_type

Type dictionary

Accessget, set, observe

###### Description

The currently selected target type for the track's output routing. It's represented as a *dictionary* with the following keys:  
*display\_name* \[symbol\]  
*identifier* \[symbol\]  
Can be set to all values found in the track's *available\_output\_routing\_types*.  
Not available on the master track.

##### playing\_slot\_index

Type int

Accessget, observe

###### Description

First slot has index 0, -2 = Clip Stop slot fired in Session View, -1 = Arrangement recording with no Session clip playing. \[not in return/master tracks\]

##### solo

Type bool

Accessget, set, observe

###### Description

Remark: when setting this property, the exclusive Solo logic is bypassed, so you have to unsolo the other tracks yourself. \[not in master track\]

#### Functions

##### create\_audio\_clip

Parameters:  
*file\_path* \[symbol\]  
*position* \[float\]  
Given an absolute path to a valid audio file in a supported format, creates an audio clip that references the file at the specified position in the arrangement view. Prints an error if the track is not an audio track, if the track is frozen, or if the track is being recorded into. The position must be within the range \[0., 1576800\].  
  
See the *ClipSlot.create\_audio\_clip* function if you need to create audio clips in session view instead.

##### delete\_clip

Parameter: *clip*  
Delete the given clip.

##### delete\_device

Parameter: *index*  
Delete the device at the given index.

##### duplicate\_clip\_slot

Parameter: *index*  
Works like 'Duplicate' in a clip's context menu.

##### duplicate\_clip\_to\_arrangement

Parameters: *clip*  
*destination\_time* \[double\]  
Duplicate the given clip to the Arrangement, placing it at the given *destination\_time* in beats.

##### jump\_in\_running\_session\_clip

Parameter: *beats*  
*beats* \[double\] is the amount to jump relatively to the current clip position.  
Modify playback position in running Session clip, if any.

##### stop\_all\_clips

Stops all playing and fired clips in this track.

## Track.View

Representing the view aspects of a track.

#### Canonical path

###### live\_set tracks N view

#### Children

##### selected\_device

Type Device

Accessget, observe

###### Description

The selected device or the first selected device (in case of multi/group selection).

#### Properties

##### device\_insert\_mode

Type int

Accessget, set, observe

###### Description

Determines where a device will be inserted when loaded from the browser. 0 = add device at the end, 1 = add device to the left of the selected device, 2 = add device to the right of the selected device.

##### is\_collapsed

Type bool

Accessget, set, observe

###### Description

In Arrangement View: 1 = track collapsed, 0 = track opened.

#### Functions

##### select\_instrument

Returns: bool 0 = there are no devices to select  
Selects track's instrument or first device, makes it visible and focuses on it.

## ClipSlot

This class represents an entry in Live's Session View matrix.  
  
The properties playing\_status, is\_playing and is\_recording are useful for clip slots of Group Tracks. These are always empty and represent the state of the clips in the tracks within the Group Track.

#### Canonical path

###### live\_set tracks N clip\_slots M

#### Children

##### clip

Type Clip

Accessget

###### Description

id 0 if slot is empty

#### Properties

##### color

Type long

Accessget, observe

###### Description

The color of the first clip in the Group Track if the clip slot is a Group Track slot.

##### color\_index

Type long

Accessget, observe

###### Description

The color index of the first clip in the Group Track if the clip slot is a Group Track slot.

##### controls\_other\_clips

Type bool

Accessget, observe

###### Description

1 for a Group Track slot that has non-deactivated clips in the tracks within its group.  
Control of empty clip slots doesn't count.

##### has\_clip

Type bool

Accessget, observe

###### Description

1 = a clip exists in this clip slot.

##### has\_stop\_button

Type bool

Accessget, set, observe

###### Description

1 = this clip stops its track (or tracks within a Group Track).

##### is\_group\_slot

Type bool

Accessget

###### Description

1 = this clip slot is a Group Track slot.

##### is\_playing

Type bool

Accessget

###### Description

1 = playing\_status!= 0, otherwise 0.

##### is\_recording

Type bool

Accessget

###### Description

1 = playing\_status == 2, otherwise 0.

##### is\_triggered

Type bool

Accessget, observe

###### Description

1 = clip slot button (Clip Launch, Clip Stop or Clip Record) or button of contained clip are blinking.

##### playing\_status

Type int

Accessget, observe

###### Description

0 = all clips in tracks within a Group Track stopped or all tracks within a Group Track are empty.  
1 = at least one clip in a track within a Group Track is playing.  
2 = at least one clip in a track within a Group Track is playing or recording.  
Equals 0 if this is not a clip slot of a Group Track.

##### will\_record\_on\_start

Type bool

Accessget

###### Description

1 = clip slot will record on start.

#### Functions

##### create\_audio\_clip

Parameter: *path*  
Given an absolute path to a valid audio file in a supported format, creates an audio clip that references the file in the clip slot. Throws an error if the clip slot doesn't belong to an audio track or if the track is frozen.

##### create\_clip

Parameter: *length*  
Length is given in beats and must be a greater value than 0.0. Can only be called on empty clip slots in MIDI tracks.

##### delete\_clip

Deletes the contained clip.

##### duplicate\_clip\_to

Parameter: *target\_clip\_slot* \[ClipSlot\]  
Duplicates the slot's clip to the given clip slot, overriding the target clip slot's clip if it's not empty.

##### fire

Parameter: *record\_length (optional)*  
*launch\_quantization (optional)*  
Fires the clip or triggers the Stop Button, if any. Starts recording if slot is empty and track is armed. Starts recording of armed and empty tracks within a Group Track if Preferences->Launch->Start Recording on Scene Launch is ON. If *record\_length* is provided, the slot will record for the given length in beats. *launch\_quantization* overrides the global quantization if provided.

##### set\_fire\_button\_state

Parameter: *state* \[bool\]  
1 = Live simulates pressing of Clip Launch button until the state is set to 0 or until the slot is stopped otherwise.

##### stop

Stops playing or recording clips in this track or the tracks within the group, if any. It doesn't matter on which slot of the track you call this function.

## Clip

This class represents a clip in Live. It can be either an audio clip or a MIDI clip in the Arrangement or Session View, depending on the track / slot it lives in.

#### Canonical path

###### live\_set tracks N clip\_slots M clip

#### Canonical path

###### live\_set tracks N arrangement\_clips M

#### Children

##### view

Type Clip.View

Accessget

###### Description

#### Properties

##### available\_warp\_modes

Type list

Accessget

###### Description

Returns the list of indexes of the Warp Modes available for the clip. Only valid for audio clips.

##### color

Type int

Accessget, set, observe

###### Description

The RGB value of the clip's color in the form 0x00rrggbb or (2^16 \* red) + (2^8) \* green + blue, where red, green and blue are values from 0 (dark) to 255 (light).  
  
When setting the RGB value, the nearest color from the clip color chooser is taken.

##### color\_index

Type int

Accessget, set, observe

###### Description

The clip's color index.

##### end\_marker

Type double

Accessget, set, observe

###### Description

The end marker of the clip in beats, independent of the loop state. Cannot be set before the start marker.

##### end\_time

Type double

Accessget, observe

###### Description

The end time of the clip. For Session View clips, if Loop is on, this is the Loop End, otherwise it's the End Marker. For Arrangement View clips, this is always the position of the clip's rightmost edge in the Arrangement.

##### gain

Type double

Accessget, set, observe

###### Description

The gain of the clip (range is 0.0 to 1.0). Only valid for audio clips.

##### gain\_display\_string

Type symbol

Accessget

###### Description

Get the gain display value of the clip as a string (e.g. "1.3 dB"). Can only be called on audio clips.

##### file\_path

Type symbol

Accessget

###### Description

Get the location of the audio file represented by the clip. Only available for audio clips.

##### groove

Type Groove

Accessget, set, observe

###### Description

Get/set/observe access to the groove associated with this clip.  
  
*Available since Live 11.0.*

##### has\_envelopes

Type bool

Accessget, observe

###### Description

Get/observe whether the clip has any automation.

##### has\_groove

Type bool

Accessget

###### Description

Returns true if a groove is associated with this clip.  
  
*Available since Live 11.0.*

##### is\_arrangement\_clip

Type bool

Accessget

###### Description

1 = The clip is an Arrangement clip.  
A clip can be either an Arrangement or a Session clip.

##### is\_audio\_clip

Type bool

Accessget

###### Description

0 = MIDI clip, 1 = audio clip

##### is\_midi\_clip

Type bool

Accessget

###### Description

The opposite of is\_audio\_clip.

##### is\_overdubbing

Type bool

Accessget, observe

###### Description

1 = clip is overdubbing.

##### is\_playing

Type bool

Accessget, set

###### Description

1 = clip is playing or recording.

##### is\_recording

Type bool

Accessget, observe

###### Description

1 = clip is recording.

##### is\_triggered

Type bool

Accessget

###### Description

1 = Clip Launch button is blinking.

##### launch\_mode

Type int

Accessget, set, observe

###### Description

The Launch Mode of the Clip as an integer index. Available Launch Modes are:  
0 = Trigger (default)  
1 = Gate  
2 = Toggle  
3 = Repeat  
  
*Available since Live 11.0.*

##### launch\_quantization

Type int

Accessget, set, observe

###### Description

The Launch Quantization of the Clip as an integer index. Available Launch Quantization values are:  
0 = Global (default)  
1 = None  
2 = 8 Bars  
3 = 4 Bars  
4 = 2 Bars  
5 = 1 Bar  
6 = 1/2  
7 = 1/2T  
8 = 1/4  
9 = 1/4T  
10 = 1/8  
11 = 1/8T  
12 = 1/16  
13 = 1/16T  
14 = 1/32  
  
*Available since Live 11.0.*

##### legato

Type bool

Accessget, set, observe

###### Description

1 = Legato Mode switch in the Clip's Launch settings is on.  
  
*Available since Live 11.0.*

##### length

Type double

Accessget

###### Description

For looped clips: loop length in beats. Otherwise it's the distance in beats from start to end marker. Makes no sense for unwarped audio clips.

##### loop\_end

Type double

Accessget, set, observe

###### Description

For looped clips: loop end.  
For unlooped clips: clip end.

##### loop\_jump

Type bang

Accessobserve

###### Description

Bangs when the clip play position is crossing the loop start marker (possibly projected into the loop).

##### loop\_start

Type double

Accessget, set, observe

###### Description

For looped clips: loop start.  
For unlooped clips: clip start.  
  
loop\_start and loop\_end are in absolute clip beat time if clip is MIDI or warped. The 1.1.1 position has beat time 0. If the clip is unwarped audio, they are given in seconds, 0 is the time of the first sample in the audio material.

##### looping

Type bool

Accessget, set, observe

###### Description

1 = clip is looped. Unwarped audio cannot be looped.

##### muted

Type bool

Accessget, set, observe

###### Description

1 = muted (i.e. the Clip Activator button of the clip is off).

##### name

Type symbol

Accessget, set, observe

###### Description

##### notes

Type bang

Accessobserve

###### Description

Observer sends bang when the list of notes changes.  
Available for MIDI clips only.

##### warp\_markers

Type dict/bang

Accessget, observe

###### Description

The Clip's Warp Markers as a dict. Observing this property bangs when the warp\_markers change.  
  
The last Warp Marker in the dict is not visible in the Live interface. This hidden marker is used to calculate the BPM of the last segment.  
  
Available for audio clips only.  
  
*Getting is available since Live 11.0.*

##### pitch\_coarse

Type int

Accessget, set, observe

###### Description

Pitch shift in semitones ("Transpose"), -48... 48.  
Available for audio clips only.

##### pitch\_fine

Type float

Accessget, set, observe

###### Description

Extra pitch shift in cents ("Detune"), -50... 49.  
Available for audio clips only.

##### playing\_position

Type float

Accessget, observe

###### Description

Current playing position of the clip.  
  
For MIDI and warped audio clips, the value is given in beats of absolute clip time. The clip's beat time of 0 is where 1 is shown in the bar/beat/16th time scale at the top of the clip view.  
  
For unwarped audio clips, the position is given in seconds, according to the time scale shown at the bottom of the clip view.  
  
Stopped clips have a playing position of 0.

##### playing\_status

Type bang

Accessobserve

###### Description

Observer sends bang when playing/trigger status changes.

##### position

Type float

Accessget, observe

###### Description

Get and set the clip's loop position. The value will always equal loop\_start, however setting this property, unlike setting loop\_start, preserves the loop length.

##### ram\_mode

Type bool

Accessget, set, observe

###### Description

1 = an audio clip’s RAM switch is enabled.

##### sample\_length

Type int

Accessget

###### Description

Length of the Clip's sample, in samples.

##### sample\_rate

Type float

Accessget

###### Description

Get the Clip's sample rate.

##### signature\_denominator

Type int

Accessget, set, observe

###### Description

##### signature\_numerator

Type int

Accessget, set, observe

###### Description

##### start\_marker

Type double

Accessget, set, observe

###### Description

The start marker of the clip in beats, independent of the loop state. Cannot be set behind the end marker.

##### start\_time

Type double

Accessget

###### Description

The start time of the clip, relative to the global song time. For Session View clips, this is the time the clip was started. For Arrangement View clips, this is the offset within the arrangement. The value is in beats.

##### velocity\_amount

Type float

Accessget, set, observe

###### Description

How much the velocity of the note that triggers the clip affects its volume, 0 = no effect, 1 = full effect.  
  
*Available since Live 11.0.*

##### warp\_mode

Type int

Accessget, set, observe

###### Description

The Warp Mode of the clip as an integer index. Available Warp Modes are:  
0 = Beats Mode  
1 = Tones Mode  
2 = Texture Mode  
3 = Re-Pitch Mode  
4 = Complex Mode  
5 = REX Mode  
6 = Complex Pro Mode  
Available for audio clips only.

##### warping

Type bool

Accessget, set, observe

###### Description

1 = Warp switch is on.  
Available for audio clips only.

##### will\_record\_on\_start

Type bool

Accessget

###### Description

1 for MIDI clips which are in triggered state, with the track armed and MIDI Arrangement Overdub on.

#### Functions

##### add\_new\_notes

Parameter:  
*dictionary*  
Key: *"notes"* \[list of note specification dictionaries\]  
Note specification dictionaries have the following keys:  
*pitch*: \[int\] the MIDI note number, 0...127, 60 is C3.  
*start\_time*: \[float\] the note start time in beats of absolute clip time.  
*duration*: \[float\] the note length in beats.  
*velocity (optional)*: \[float\] the note velocity, 0... 127 *(100 by default)*.  
*mute (optional)*: \[bool\] 1 = the note is deactivated *(0 by default)*.  
*probability (optional)*: \[float\] the chance that the note will be played:  
1.0 = the note is always played  
0.0 = the note is never played  
*(1.0 by default)*.  
*velocity\_deviation (optional)*: \[float\] the range of velocity values at which the note can be played:  
0.0 = no deviation; the note will always play at the velocity specified by the *velocity* property  
\-127.0 to 127.0 = the note will be assigned a velocity value between *velocity* and *velocity + velocity\_deviation*, inclusive; if the resulting range exceeds the limits of MIDI velocity (0 to 127), then it will be clamped within those limits  
*(0.0 by default)*.  
*release\_velocity (optional)*: \[float\] the note release velocity *(64 by default)*.  
Returns a list of note IDs of the added notes.  
  
For MIDI clips only.  
  
*Available since Live 11.0.*

##### add\_warp\_marker

Only available for warped Audio Clips. Adds the specified warp marker, if possible.  
  
The warp marker is specified as a dict which can have a *beat\_time* and a *sample\_time* key, both associated with float values.  
The *sample\_time* key may be omitted; in this case, Live will calculate the appropriate sample time to create a warp marker at the specified beat time without changing the Clip's playback timing, similar to what would happen if you were to double-click in the upper half of the Sample Display in Clip View.  
  
If *sample\_time* is specified, certain limitations must be taken into account:

- The sample time must lie within the range *\[0, s\]*, where *s* is the sample's length. The *sample\_length* Clip property helps with this.
- The sample time must lie between the left and right adjacents markers' respective sample times (this is a logical constraint).
- Within these constraints, there are limitations on the resulting segments' BPM. The allowed BPM range is *\[5, 999\]*.

##### apply\_note\_modifications

Parameter:  
*dictionary*  
Key: *"notes"* \[list of note dictionaries\] as returned from get\_notes\_extended.  
The list of note dictionaries passed to the function can be a subset of notes in the clip, but will be ignored if it contains any notes that are not present in the clip.  
  
For MIDI clips only.  
  
*Available since Live 11.0. Replaces modifying notes with remove\_notes followed by set\_notes.*

##### clear\_all\_envelopes

Removes all automation in the clip.

##### clear\_envelope

Parameter:  
*device\_parameter* \[id\]  
Removes the automation of the clip for the given parameter.

##### crop

Crops the clip: if the clip is looped, the region outside the loop is removed; if it isn't, the region outside the start and end markers.

##### deselect\_all\_notes

Call this before replace\_selected\_notes if you just want to add some notes.  
Output:  
deselect\_all\_notes id 0  
  
For MIDI clips only.

##### duplicate\_loop

Makes the loop two times longer by moving loop\_end to the right, and duplicates both the notes and the envelopes. If the clip is not looped, the clip start/end range is duplicated. Available for MIDI clips only.

##### duplicate\_notes\_by\_id

Parameter:  
*list* of note IDs.  
Or *dictionary*  
Keys:  
*note\_ids* \[list of note IDs\] as returned from get\_notes\_extended  
*destination\_time (optional)* \[double/int\]  
*transposition\_amount (optional)* \[int\]  
Duplicates all notes matching the given note IDs.  
Provided note IDs must be associated with existing notes in the clip. Existing notes can be queried with get\_notes\_extended.  
The selection of notes will be duplicated to *destination\_time*, if provided. Otherwise the new notes will be inserted after the last selected note. This behavior can be observed when duplicating notes in the Live GUI.  
If the *transposition\_amount* is specified, the duplicated notes will be transposed by the number of semitones.  
Available for MIDI clips only.  
  
*Available since Live 11.1.2*

##### duplicate\_region

Parameter:  
*region\_start* \[double/int\]  
*region\_length* \[double/int\]  
*destination\_time* \[double/int\]  
*pitch (optional)* \[int\]  
*transposition\_amount (optional)* \[int\]  
Duplicate the notes in the specified region to the *destination\_time*. Only notes of the specified pitch are duplicated or all if *pitch* is -1. If the *transposition\_amount* is not 0, the notes in the region will be transposed by the *transpose\_amount* of semitones. Available for MIDI clips only.

##### fire

Same effect as pressing the Clip Launch button.

##### get\_all\_notes\_extended

Parameter:  
*dict (optional)* \[dict\]  
(See below for a discussion of this argument).  
  
Returns a dictionary of all of the notes in the clip, regardless of where they are positioned with respect to the start/end markers and the loop start/loop end, as a list of note dictionaries. Each note dictionary consists of the following key-value pairs:  
*note\_id*: \[int\] the unique note identifier.  
*pitch*: \[int\] the MIDI note number, 0...127, 60 is C3.  
*start\_time*: \[float\] the note start time in beats of absolute clip time.  
*duration*: \[float\] the note length in beats.  
*velocity*: \[float\] the note velocity, 0... 127.  
*mute*: \[bool\] 1 = the note is deactivated.  
*probability*: \[float\] the chance that the note will be played:  
1.0 = the note is always played;  
0.0 = the note is never played.  
*velocity\_deviation*: \[float\] the range of velocity values at which the note can be played:  
0.0 = no deviation; the note will always play at the velocity specified by the *velocity* property  
\-127.0 to 127.0 = the note will be assigned a velocity value between *velocity* and *velocity + velocity\_deviation*, inclusive; if the resulting range exceeds the limits of MIDI velocity (0 to 127), then it will be clamped within those limits.  
*release\_velocity*: \[float\] the note release velocity.  
  
It is possible to optionally provide a single \[dict\] argument to this function, containing a single key-value pair: the key is "return" and the associated value is a list of the note properties as listed above in the discussion of the returned note dictionaries, e.g. \["note\_id", "pitch", "velocity"\]. The effect of this will be that the returned note dictionaries will only contain the key-value pairs for the specified properties, which can be useful to improve patch performance when processing large notes dictionaries.  
  
For MIDI clips only.  
  
*Available since Live 11.1*

##### get\_notes\_by\_id

Parameter:  
*list* of note IDs.  
  
Provided note IDs must be associated with existing notes in the clip. Existing notes can be queried with get\_notes\_extended.  
  
Returns a dictionary of notes associated with the provided IDs, as a list of note dictionaries. Each note dictionary consists of the following key-value pairs:  
*note\_id*: \[int\] the unique note identifier.  
*pitch*: \[int\] the MIDI note number, 0...127, 60 is C3.  
*start\_time*: \[float\] the note start time in beats of absolute clip time.  
*duration*: \[float\] the note length in beats.  
*velocity*: \[float\] the note velocity, 0... 127.  
*mute*: \[bool\] 1 = the note is deactivated.  
*probability*: \[float\] the chance that the note will be played:  
1.0 = the note is always played;  
0.0 = the note is never played.  
*velocity\_deviation*: \[float\] the range of velocity values at which the note can be played:  
0.0 = no deviation; the note will always play at the velocity specified by the *velocity* property  
\-127.0 to 127.0 = the note will be assigned a velocity value between *velocity* and *velocity + velocity\_deviation*, inclusive; if the resulting range exceeds the limits of MIDI velocity (0 to 127), then it will be clamped within those limits.  
*release\_velocity*: \[float\] the note release velocity.  
  
It is possible to optionally provide the argument to this function in the form of a dictionary instead. The dictionary must include the "note\_ids" key associated with a list of \[int\]s, which are the ID values you would like to pass to the function.  
  
If you use this method, you can optionally provide an additional key-value pair: the key is "return" and the associated value is a list of the note properties as listed above in the discussion of the returned note dictionaries, e.g. \["note\_id", "pitch", "velocity"\]. The effect of this will be that the returned note dictionaries will only contain the key-value pairs for the specified properties, which can be useful to improve patch performance when processing large notes dictionaries.  
  
For MIDI clips only.  
  
*Available since Live 11.0.*

##### get\_notes\_extended

Parameters:  
*from\_pitch* \[int\]  
*pitch\_span* \[int\]  
*from\_time* \[float\]  
*time\_span* \[float\]  
  
*from\_time* and *time\_span* are given in beats.  
  
Returns a dictionary of notes that have their start times in the given area, as a list of note dictionaries. Each note dictionary consists of the following key-value pairs:  
*note\_id*: \[int\] the unique note identifier.  
*pitch*: \[int\] the MIDI note number, 0...127, 60 is C3.  
*start\_time*: \[float\] the note start time in beats of absolute clip time.  
*duration*: \[float\] the note length in beats.  
*velocity*: \[float\] the note velocity, 0... 127.  
*mute*: \[bool\] 1 = the note is deactivated.  
*probability*: \[float\] the chance that the note will be played:  
1.0 = the note is always played;  
0.0 = the note is never played.  
*velocity\_deviation*: \[float\] the range of velocity values at which the note can be played:  
0.0 = no deviation; the note will always play at the velocity specified by the *velocity* property  
\-127.0 to 127.0 = the note will be assigned a velocity value between *velocity* and *velocity + velocity\_deviation*, inclusive; if the resulting range exceeds the limits of MIDI velocity (0 to 127), then it will be clamped within those limits.  
*release\_velocity*: \[float\] the note release velocity.  
  
It is possible to optionally provide the arguments to this function in the form of a single dictionary instead. The dictionary must include all of the parameter names given above as its keys; the associated values are the parameter values you wish to pass to the function.  
  
If you use this method, you can optionally provide an additional key-value pair: the key is "return" and the associated value is a list of the note properties as listed above in the discussion of the returned note dictionaries, e.g. \["note\_id", "pitch", "velocity"\]. The effect of this will be that the returned note dictionaries will only contain the key-value pairs for the specified properties, which can be useful to improve patch performance when processing large notes dictionaries.  
  
For MIDI clips only.  
  
*Available since Live 11.0. Replaces get\_notes.*

##### get\_selected\_notes\_extended

Parameter:  
*dict (optional)* \[dict\]  
(See below for a discussion of this argument).  
  
Returns a dictionary of the selected notes in the clip, as a list of note dictionaries. Each note dictionary consists of the following key-value pairs:  
*note\_id*: \[int\] the unique note identifier.  
*pitch*: \[int\] the MIDI note number, 0...127, 60 is C3.  
*start\_time*: \[float\] the note start time in beats of absolute clip time.  
*duration*: \[float\] the note length in beats.  
*velocity*: \[float\] the note velocity, 0... 127.  
*mute*: \[bool\] 1 = the note is deactivated.  
*probability*: \[float\] the chance that the note will be played:  
1.0 = the note is always played;  
0.0 = the note is never played.  
*velocity\_deviation*: \[float\] the range of velocity values at which the note can be played:  
0.0 = no deviation; the note will always play at the velocity specified by the *velocity* property  
\-127.0 to 127.0 = the note will be assigned a velocity value between *velocity* and *velocity + velocity\_deviation*, inclusive; if the resulting range exceeds the limits of MIDI velocity (0 to 127), then it will be clamped within those limits.  
*release\_velocity*: \[float\] the note release velocity.  
  
It is possible to optionally provide a single \[dict\] argument to this function, containing a single key-value pair: the key is "return" and the associated value is a list of the note properties as listed above in the discussion of the returned note dictionaries, e.g. \["note\_id", "pitch", "velocity"\]. The effect of this will be that the returned note dictionaries will only contain the key-value pairs for the specified properties, which can be useful to improve patch performance when processing large notes dictionaries.  
  
For MIDI clips only.  
  
*Available since Live 11.0. Replaces get\_selected\_notes.*

##### move\_playing\_pos

Parameter: *beats*  
*beats* \[double\] relative jump distance in beats. Negative beats jump backwards.  
Jumps by given amount, unquantized.  
Unwarped audio clips, recording audio clips and recording non-overdub MIDI clips cannot jump.

##### move\_warp\_marker

Parameters: *beat\_time* \[double\]  
*beat\_time\_distance* \[double\]  
Moves the warp marker specified by *beat\_time* the specified beat time distance.

##### quantize

Parameter:  
*quantization\_grid* \[int\]  
*amount* \[double\]  
Quantizes all notes in the clip to the quantization\_grid taking the song's swing\_amount into account.

##### quantize\_pitch

Parameter:  
*pitch* \[int\]  
*quantization\_grid* \[int\]  
*amount* \[double\]  
Same as *quantize*, but only for notes in the given pitch.

##### remove\_notes\_by\_id

Parameter:  
*list* of note IDs.  
Deletes all notes associated with the provided IDs.  
Provided note IDs must be associated with existing notes in the clip. Existing notes can be queried with get\_notes\_extended.  
  
*Available since Live 11.0.*

##### remove\_notes\_extended

Parameter:  
*from\_pitch* \[int\]  
*pitch\_span* \[int\]  
*from\_time* \[float\]  
*time\_span* \[float\]  
Deletes all notes that start in the given area. *from\_time* and *time\_span* are given in beats.  
  
*Available since Live 11.0. Replaces remove\_notes.*

##### remove\_warp\_marker

Parameter: *beat\_time* \[float\]  
Removes the warp marker at the given beat time.

##### scrub

Parameter: *beat\_time* \[double\]  
Scrub the clip to a time, specified in beats. This behaves exactly like scrubbing with the mouse; the scrub will respect Global Quantization, starting and looping in time with the transport. The scrub will continue until stop\_scrub() is called.

##### select\_all\_notes

Use this function to process all notes of a clip, independent of the current selection.  
  
Output:  
select\_all\_notes id 0  
  
For MIDI clips only.

##### select\_notes\_by\_id

Parameter:  
*list* of note IDs.  
Selects all notes associated with the provided IDs.  
  
Note that this function will *not* print a warning or error if the list contains nonexistent IDs.  
  
*Available since Live 11.0.6*

##### set\_fire\_button\_state

Parameter: *state* \[bool\]  
If the state is set to 1, Live simulates pressing the clip start button until the state is set to 0, or until the clip is otherwise stopped.

##### stop

Same effect as pressing the stop button of the track, but only if this clip is actually playing or recording. If this clip is triggered or if another clip in this track is playing, it has no effect.

##### stop\_scrub

Stops an active scrub on a clip.

## Clip.View

Representing the view aspects of a Clip.

#### Canonical path

###### live\_set tracks N clip\_slots M clip view

#### Properties

##### grid\_is\_triplet

Type bool

Accessget, set

###### Description

Get/set whether the clip is displayed with a triplet grid.

##### grid\_quantization

Type int

Accessget, set

###### Description

Get/set the grid quantization.

#### Functions

##### hide\_envelope

Hide the Envelopes box.

##### select\_envelope\_parameter

Parameter: \[DeviceParameter\]  
Select the specified device parameter in the Envelopes box.

##### show\_envelope

Show the Envelopes box.

##### show\_loop

If the clip is visible in Live's Detail View, this function will make the current loop visible there.

## Groove

This class represents a groove in Live.  
  
*Available since Live 11.0.*  
All grooves are stored in Live's groove pool.

#### Canonical path

###### live\_set groove\_pool grooves N

#### Canonical path

###### live\_set tracks N clip\_slots M clip groove

#### Children

##### base

Type int

Accessget, set

###### Description

Get/set the groove's base grid (index based setter).  
0 = 1/4  
1 = 1/8  
2 = 1/8T  
3 = 1/16  
4 = 1/16T  
5 = 1/32

##### name

Type symbol

Accessget, set, observe

###### Description

Get/set/observe the name of the groove.

##### quantization\_amount

Type float

Accessget, set, observe

###### Description

Get/set/observe the groove's quantization amount.

##### random\_amount

Type float

Accessget, set, observe

###### Description

Get/set/observe the groove's random amount.

##### timing\_amount

Type float

Accessget, set, observe

###### Description

Get/set/observe the groove's timing amount.

##### velocity\_amount

Type float

Accessget, set, observe

###### Description

Get/set/observe the groove's velocity amount.

## Device

This class represents a MIDI or audio device in Live.

#### Canonical path

###### live\_set tracks N devices M

#### Canonical path

###### live\_set tracks N devices M chains L devices K

#### Canonical path

###### live\_set tracks N devices M return\_chains L devices K

#### Children

##### parameters

Typelist of DeviceParameter

Accessget, observe

###### Description

Only automatable parameters are accessible. See DeviceParameter to learn how to modify them.

##### view

Type Device.View

Accessget

###### Description

#### Properties

##### can\_have\_chains

Type bool

Accessget

###### Description

0 for a single device  
1 for a device Rack

##### can\_have\_drum\_pads

Type bool

Accessget

###### Description

1 for Drum Racks

##### class\_display\_name

Type symbol

Accessget

###### Description

Get the original name of the device (e.g. Operator, Auto Filter).

##### class\_name

Type symbol

Accessget

###### Description

Live device type such as MidiChord, Operator, Limiter, MxDeviceAudioEffect, or PluginDevice.

##### is\_active

Type bool

Accessget, observe

###### Description

0 = either the device itself or its enclosing Rack device is off.

##### name

Type symbol

Accessget, set, observe

###### Description

This is the string shown in the title bar of the device.

##### type

Type int

Accessget

###### Description

The type of the device. Possible types are: 0 = undefined, 1 = instrument, 2 = audio\_effect, 4 = midi\_effect.

##### latency\_in\_samples

Type int

Accessget, observe

###### Description

Device latency in samples.

##### latency\_in\_ms

Type float

Accessget, observe

###### Description

Device latency in milliseconds.

#### Functions

##### store\_chosen\_bank

Parameters:  
*script\_index* \[int\]  
*bank\_index* \[int\]  
(This is related to hardware control surfaces and is usually not relevant.)

## Device.View

Representing the view aspects of a Device.

#### Canonical path

###### live\_set tracks N devices M view

#### Canonical path

###### live\_set tracks N devices M chains L devices K view

#### Canonical path

###### live\_set tracks N devices M return\_chains L devices K view

#### Properties

##### is\_collapsed

Type bool

Accessget, set, observe

###### Description

1 = the device is shown collapsed in the device chain.

## DeviceParameter

This class represents an (automatable) parameter within a MIDI or audio device. To modify a device parameter, set its value property or send its object ID to [live.remote~](https://docs.cycling74.com/max8/refpages/live.remote~).

#### Canonical path

###### live\_set tracks N devices M parameters L

#### Properties

##### automation\_state

Type int

Accessget, observe

###### Description

Get the automation state of the parameter.  
0 = no automation.  
1 = automation active.  
2 = automation overridden.

##### default\_value

Type float

Accessget

###### Description

Get the default value for this parameter.  
Only available for parameters that aren't quantized (see *is\_quantized*).

##### is\_enabled

Type bool

Accessget

###### Description

1 = the parameter value can be modified directly by the user, by sending set to a [live.object](https://docs.cycling74.com/max8/refpages/live.object), by automation or by an assigned MIDI message or keystroke.  
Parameters can be disabled because they are macro-controlled, or they are controlled by a live-remote~ object, or because Live thinks that they should not be moved.

##### is\_quantized

Type bool

Accessget

###### Description

1 for booleans and enums  
0 for int/float parameters  
Although parameters like MidiPitch.Pitch appear quantized to the user, they actually have an is\_quantized value of 0.

##### max

Type float

Accessget

###### Description

Largest allowed value.

##### min

Type float

Accessget

###### Description

Lowest allowed value.

##### name

Type symbol

Accessget

###### Description

The short parameter name as shown in the (closed) automation chooser.

##### original\_name

Type symbol

Accessget

###### Description

The name of a Macro parameter before its assignment.

##### state

Type int

Accessget, observe

###### Description

The active state of the parameter.  
0 = the parameter is active and can be changed.  
1 = the parameter can be changed but isn't active, so changes won't have an audible effect.  
2 = the parameter cannot be changed.

##### value

Type float

Accessget, set, observe

###### Description

Linear-to-GUI value between min and max.

##### value\_items

Type StringVector

Accessget

###### Description

Get a list of the possible values for this parameter.  
Only available for parameters that are quantized (see *is\_quantized*).

#### Functions

##### re\_enable\_automation

Re-enable automation for this parameter.

##### str\_for\_value

Parameter: *value* \[float\] Returns: \[symbol\] String representation of the specified value.

##### \_\_str\_\_

Returns: \[symbol\] String representation of the current parameter value.

## RackDevice

This class represents a Live Rack Device.  
A RackDevice is a type of Device, meaning that it has all the children, properties and functions that a Device has. Listed below are members unique to RackDevice.

#### Children

##### chain\_selector

Type DeviceParameter

Accessget

###### Description

Convenience accessor for the Rack's chain selector.

##### chains

Typelist of Chain

Accessget, observe

###### Description

The Rack's chains.

##### drum\_pads

Typelist of DrumPad

Accessget, observe

###### Description

All 128 Drum Pads for the topmost Drum Rack. Inner Drum Racks return a list of 0 entries.

##### return\_chains

Typelist of Chain

Accessget, observe

###### Description

The Rack's return chains.

##### visible\_drum\_pads

Typelist of DrumPad

Accessget, observe

###### Description

All 16 visible DrumPads for the topmost Drum Rack. Inner Drum Racks return a list of 0 entries.

#### Properties

##### can\_show\_chains

Type bool

Accessget

###### Description

1 = The Rack contains an instrument device that is capable of showing its chains in Session View.

##### has\_drum\_pads

Type bool

Accessget, observe

###### Description

1 = the device is a Drum Rack with pads. A nested Drum Rack is a Drum Rack without pads.  
Only available for Drum Racks.

##### has\_macro\_mappings

Type bool

Accessget, observe

###### Description

1 = any of a Rack's Macros are mapped to a parameter.

##### is\_showing\_chains

Type bool

Accessget, set, observe

###### Description

1 = The Rack contains an instrument device that is showing its chains in Session View.

##### variation\_count

Type int

Accessget, observe

###### Description

The number of currently stored macro variations.  
  
*Available since Live 11.0.*

##### selected\_variation\_index

Type int

Accessget, set

###### Description

Get/set the currently selected variation.  
  
*Available since Live 11.0.*

##### visible\_macro\_count

Type int

Accessget, observe

###### Description

The number of currently visible macros.

#### Functions

##### copy\_pad

Parameters:  
*source\_index* \[int\]  
*destination\_index* \[int\]  
Copies all content of a Drum Rack pad from a source pad to a destination pad. The source\_index and destination\_index refer to pad indices inside a Drum Rack.

##### add\_macro

Increases the number of visible macro controls.  
  
*Available since Live 11.0.*

##### remove\_macro

Decreases the number of visible macro controls.  
  
*Available since Live 11.0.*

##### randomize\_macros

Randomizes the values of eligible macro controls.  
  
*Available since Live 11.0.*

##### store\_variation

Stores a new variation of the values of all currently mapped macros.  
  
*Available since Live 11.0.*

##### recall\_selected\_variation

Recalls the currently selected macro variation.  
  
*Available since Live 11.0.*

##### recall\_last\_used\_variation

Recalls the macro variation that was recalled most recently.  
  
*Available since Live 11.0.*

##### delete\_selected\_variation

Deletes the currently selected macro variation. Does nothing if there is no selected variation.  
  
*Available since Live 11.0.*

## RackDevice.View

Represents the view aspects of a Rack Device.  
A RackDevice.View is a type of Device.View, meaning that it has all the properties that a Device.View has. Listed below are the members unique to RackDevice.View.

#### Children

##### selected\_drum\_pad

Type DrumPad

Accessget, set, observe

###### Description

Currently selected Drum Rack pad.  
Only available for Drum Racks.

##### selected\_chain

Type Chain

Accessget, set, observe

###### Description

Currently selected chain.

#### Properties

##### drum\_pads\_scroll\_position

Type int

Accessget, set, observe

###### Description

Lowest row of pads visible, range: 0 - 28.  
Only available for Drum Racks.

##### is\_showing\_chain\_devices

Type bool

Accessget, set, observe

###### Description

1 = the devices in the currently selected chain are visible.

## DrumPad

This class represents a Drum Rack pad in Live.

#### Canonical path

###### live\_set tracks N devices M drum\_pads L

#### Children

##### chains

Type Chain

Accessget, observe

###### Description

#### Properties

##### mute

Type bool

Accessget, set, observe

###### Description

1 = muted

##### name

Type symbol

Accessget, observe

###### Description

##### note

Type int

Accessget

###### Description

##### solo

Type bool

Accessget, set, observe

###### Description

1 = soloed (Solo switch on)  
Does not automatically turn Solo off in other chains.

#### Functions

##### delete\_all\_chains

## Chain

This class represents a group device chain in Live.

#### Canonical path

###### live\_set tracks N devices M chains L

#### Canonical path

###### live\_set tracks N devices M return\_chains L

#### Canonical path

###### live\_set tracks N devices M chains L devices K chains P...

#### Canonical path

###### live\_set tracks N devices M return\_chains L devices K chains P...

#### Children

##### devices

Type Device

Accessget, observe

###### Description

##### mixer\_device

Type ChainMixerDevice

Accessget

###### Description

#### Properties

##### color

Type int

Accessget, set, observe

###### Description

The RGB value of the chain's color in the form 0x00rrggbb or (2^16 \* red) + (2^8) \* green + blue, where red, green and blue are values from 0 (dark) to 255 (light).  
  
When setting the RGB value, the nearest color from the color chooser is taken.

##### color\_index

Type long

Accessget, set, observe

###### Description

The color index of the chain.

##### is\_auto\_colored

Type bool

Accessget, set, observe

###### Description

1 = the chain will always have the color of the containing track or chain.

##### has\_audio\_input

Type bool

Accessget

###### Description

##### has\_audio\_output

Type bool

Accessget

###### Description

##### has\_midi\_input

Type bool

Accessget

###### Description

##### has\_midi\_output

Type bool

Accessget

###### Description

##### mute

Type bool

Accessget, set, observe

###### Description

1 = muted (Chain Activator off)

##### muted\_via\_solo

Type bool

Accessget, observe

###### Description

1 = muted due to another chain being soloed.

##### name

Type unicode

Accessget, set, observe

###### Description

##### solo

Type bool

Accessget, set, observe

###### Description

1 = soloed (Solo switch on)  
does not automatically turn Solo off in other chains.

#### Functions

##### delete\_device

Parameter: index \[int\]  
Delete the device at the given index.

## DrumChain

This class represents a Drum Rack device chain in Live.  
  
A DrumChain is a type of Chain, meaning that it has all the children, properties and functions that a Chain has. Listed below are the members unique to DrumChain.

#### Properties

##### out\_note

Type int

Accessget, set, observe

###### Description

Get/set the MIDI note sent to the devices in the chain.

##### choke\_group

Type int

Accessget, set, observe

###### Description

Get/set the chain's choke group.

## ChainMixerDevice

This class represents a chain's mixer device in Live.

#### Canonical path

###### live\_set tracks N devices M chains L mixer\_device

#### Canonical path

###### live\_set tracks N devices M return\_chains L mixer\_device

#### Children

##### sends

Typelist of DeviceParameter

Accessget, observe

###### Description

\[in Audio Effect Racks and Instrument Racks only\]  
For Drum Racks, otherwise empty.

##### chain\_activator

Type DeviceParameter

Accessget

###### Description

##### panning

Type DeviceParameter

Accessget

###### Description

\[in Audio Effect Racks and Instrument Racks only\]

##### volume

Type DeviceParameter

Accessget

###### Description

\[in Audio Effect Racks and Instrument Racks only\]

## ShifterDevice

This class represents an instance of the Shifter audio effect.  
A ShifterDevice is a type of device, meaning that it has all the children, properties and functions that a device has. Listed below are members unique to ShifterDevice.

#### Properties

##### pitch\_bend\_range

Type int

Accessget, set, observe

###### Description

The pitch bend range used in MIDI Pitch Mode.

##### pitch\_mode\_index

Type int

Accessget, set, observe

###### Description

The current pitch mode index: 0 = Internal, 1 = MIDI

## SimplerDevice

This class represents an instance of Simpler.  
A SimplerDevice is a type of device, meaning that it has all the children, properties and functions that a device has. Listed below are members unique to SimplerDevice.

#### Children

##### sample

Type Sample

Accessget, observe

###### Description

The sample currently loaded into Simpler.

#### Properties

##### can\_warp\_as

Type bool

Accessget, observe

###### Description

1 = warp\_as is available.

##### can\_warp\_double

Type bool

Accessget, observe

###### Description

1 = warp\_double is available.

##### can\_warp\_half

Type bool

Accessget, observe

###### Description

1 = warp\_half is available.

##### multi\_sample\_mode

Type bool

Accessget, observe

###### Description

1 = Simpler is in multisample mode.

##### pad\_slicing

Type bool

Accessget, set, observe

###### Description

1 = slices can be added in Slicing Mode by playing notes which are not yet assigned to existing slices.

##### playback\_mode

Type int

Accessget, set, observe

###### Description

Get/set Simpler's playback mode.  
0 = Classic Mode  
1 = One-Shot Mode  
2 = Slicing Mode

##### playing\_position

Type float

Accessget, observe

###### Description

The current playing position in the sample, expressed as a value between 0. and 1.

##### playing\_position\_enabled

Type bool

Accessget, observe

###### Description

1 = Simpler is playing back the sample and showing the playing position.

##### retrigger

Type bool

Accessget, set, observe

###### Description

1 = Retrigger is enabled in Simpler.

##### slicing\_playback\_mode

Type int

Accessget, set, observe

###### Description

Get/set Simpler's Slicing Playback Mode.  
0 = Mono  
1 = Poly  
2 = Thru

##### voices

Type int

Accessget, set, observe

###### Description

Get/set the number of Voices.

#### Functions

##### crop

Crop the loaded sample to the active region between the start and end markers.

##### guess\_playback\_length

Returns: \[float\] An estimated beat time for the playback length between the start and end markers.

##### reverse

Reverse the loaded sample.

##### warp\_as

Parameters: *beats* \[int\]  
Warp the active region between the start and end markers as the specified number of beats.

##### warp\_double

Double the playback tempo of the active region between the start and end markers.

##### warp\_half

Halve the playback tempo for the active region between the start and end markers.

## SimplerDevice.View

Represents the view aspects of a SimplerDevice.  
A SimplerDevice.View is a type of Device.View, meaning that it has all the properties that a Device.View has. Listed below are the members unique to SimplerDevice.View.

#### Properties

##### selected\_slice

Type int

Accessget, set, observe

###### Description

The currenctly selected slice, identified by its slice time.

## Sample

This class represents a sample file loaded into Simpler.

#### Canonical path

###### live\_set tracks N devices N sample

#### Properties

##### beats\_granulation\_resolution

Type int

Accessget, set, observe

###### Description

Get/set which divisions to preserve in the sample in Beats Mode.  
0 = 1 Bar  
1 = 1/2  
2 = 1/4  
3 = 1/8  
4 = 1/16  
5 = 1/32  
6 = Transients

##### beats\_transient\_envelope

Type float

Accessget, set, observe

###### Description

Get/set the duration of a volume fade applied to each segment of audio in Beats Mode.  
  
0 = fastest decay  
100 = no fade

##### beats\_transient\_loop\_mode

Type int

Accessget, set, observe

###### Description

Get/set the Transient Loop Mode applied to each segment of audio in Beats Mode.  
0 = Off  
1 = Loop Forward  
2 = Loop Back-and-Forth

##### complex\_pro\_envelope

Type float

Accessget, set, observe

###### Description

Get/set the Envelope parameter in Complex Pro Mode.

##### complex\_pro\_formants

Type float

Accessget, set, observe

###### Description

Get/set the Formants parameter in Complex Pro Mode.

##### end\_marker

Type int

Accessget, set, observe

###### Description

Get/set the position of the sample's end marker.

##### file\_path

Type unicode

Accessget, observe

###### Description

Get the path of the sample file.

##### gain

Type float

Accessget, set, observe

###### Description

Get/set the sample gain.

##### length

Type int

Accessget

###### Description

Get the length of the sample file in sample frames.

##### sample\_rate

Type int

Accessget

###### Description

The sample rate of the loaded sample.  
  
*Available since Live 11.0.*

##### slices

Typelist of int

Accessget, observe

###### Description

The positions of all playable slices in the sample, in sample frames. Divide these values by the sample\_rate to get the slice times in seconds.  
  
*Available since Live 11.0.*

##### slicing\_sensitivity

Type float

Accessget, set, observe

###### Description

Get/set the slicing sensitivity. Values are between 0.0 and 1.0.

##### start\_marker

Type int

Accessget, set, observe

###### Description

Get/set the position of the sample's start marker.

##### texture\_flux

Type float

Accessget, set, observe

###### Description

Get/set the Flux parameter in Texture Mode.

##### texture\_grain\_size

Type float

Accessget, set, observe

###### Description

Get/set the Grain Size parameter in Texture Mode.

##### tones\_grain\_size

Type float

Accessget, set, observe

###### Description

Get/set the Grain Size parameter in Tones Mode.

##### warp\_markers

Type dict/bang

Accessget, observe

###### Description

The Sample's Warp Markers as a dict. Observing this property bangs when the warp\_markers change.  
  
The last Warp Marker in the dict is not visible in the Live interface. This hidden, or "shadow" marker is used to calculate the BPM of the last segment.  
  
*Available since Live 11.0.*

##### warp\_mode

Type int

Accessget, set, observe

###### Description

Get/set the Warp Mode.  
0 = Beats Mode  
1 = Tones Mode  
2 = Texture Mode  
3 = Re-Pitch Mode  
4 = Complex Mode  
6 = Complex Pro Mode

##### warping

Type bool

Accessget, set, observe

###### Description

1 = warping is enabled.

##### slicing\_style

Type int

Accessget, set, observe

###### Description

Get/set the Slicing Mode.  
0 = Transient  
1 = Beat  
2 = Region  
3 = Manual

##### slicing\_beat\_division

Type int

Accessget, set, observe

###### Description

Get/set the slice beat division in Beat Slicing Mode.  
0 = 1/16  
1 = 1/16T  
2 = 1/8  
3 = 1/8T  
4 = 1/4  
5 = 1/4T  
6 = 1/2  
7 = 1/2T  
8 = 1 Bar  
9 = 2 Bars  
10 = 4 Bars

##### slicing\_region\_count

Type int

Accessget, set, observe

###### Description

Get/set the number of slice regions in Region Slicing Mode.

#### Functions

##### gain\_display\_string

Returns: \[list of symbols\] The sample's gain value as a string, e.g. "0.0 dB".

##### insert\_slice

Parameters: *slice\_time* \[int\]  
Insert a new slice at the specified time if there is none.

##### move\_slice

Parameters: *source\_time* \[int\] *destination\_time* \[int\]  
Move an existing slice to a specified time.

##### remove\_slice

Parameters: *slice\_time* \[int\]  
Remove a slice at the specified time if it exists.

##### clear\_slices

Clear all slices created in Manual Slicing Mode.

##### reset\_slices

Reset all edited slices to their original positions.

## WavetableDevice

This class represents a Wavetable instrument.  
  
A WavetableDevice shares all of the children, functions and properties that a Device has. Listed below are members unique to it.

#### Properties

##### filter\_routing

Type int

Accessget, set, observe

###### Description

Access to the current filter routing. 0 = Serial, 1 = Parallel, 2 = Split.

##### mono\_poly

Type int

Accessget, set, observe

###### Description

Access to Wavetable's Poly/Mono switch. 0 = Mono, 1 = Poly.

##### oscillator\_1\_effect\_mode

Type int

Accessget, set, observe

###### Description

Access to oscillator 1's effect mode. 0 = None, 1 = Fm, 2 = Classic, 3 = Modern.

##### oscillator\_2\_effect\_mode

Type int

Accessget, set, observe

###### Description

Access to oscillator 2's effect mode.

##### oscillator\_1\_wavetable\_category

Type

Accessget, set, observe

###### Description

Access to oscillator 1's wavetable category selector.

##### oscillator\_2\_wavetable\_category

Type

Accessget, set, observe

###### Description

Access to oscillator 2's wavetable category selector.

##### oscillator\_1\_wavetable\_index

Type

Accessget, set, observe

###### Description

Access to oscillator 1's wavetable index selector.

##### oscillator\_2\_wavetable\_index

Type

Accessget, set, observe

###### Description

Access to oscillator 2's wavetable index selector.

##### oscillator\_1\_wavetables

Type StringVector

Accessget, observe

###### Description

List of names of the wavetables currently available for oscillator 1. Depends on the current wavetable category selection (see *oscillator\_1\_wavetable\_category*).

##### oscillator\_2\_wavetables

Type StringVector

Accessget, observe

###### Description

List of names of the wavetables currently available for oscillator 2. Depends on the current wavetable category selection (see *oscillator\_2\_wavetable\_category*).

##### oscillator\_wavetable\_categories

Type StringVector

Accessget

###### Description

List of the names of the available wavetable categories.

##### poly\_voices

Type int

Accessget, set, observe

###### Description

The current number of polyphonic voices.

##### unison\_mode

Type int

Accessget, set, observe

###### Description

Access to Wavetable's unison mode parameter.  
  
0 = None  
1 = Classic  
2 = Shimmer  
3 = Noise  
4 = Phase Sync  
5 = Position Spread  
6 = Random Note

##### unison\_voice\_count

Type int

Accessget, set, observe

###### Description

Access to the number of unison voices.

##### visible\_modulation\_target\_names

Type StringVector

Accessget, observe

###### Description

List of the names of modulation targets currently visible in the modulation matrix.

#### Functions

##### add\_parameter\_to\_modulation\_matrix

Parameter: *parameter\_to\_add* \[DeviceParameter\]  
Add an instrument parameter to the modulation matrix. Only works for parameters that can be modulated (see *is\_parameter\_modulatable*).

##### get\_modulation\_target\_parameter\_name

Parameter: *index* \[int\]  
Return the modulation target parameter name at *index* in the modulation matrix as a \[symbol\].

##### get\_modulation\_value

Parameters: *modulation\_target\_index* \[int\] *modulation\_source\_index* \[int\]  
Return the amount of the modulation of the parameter at *modulation\_target\_index* by the modulation source at *modulation\_source\_index* in Wavetable's modulation matrix.

##### is\_parameter\_modulatable

Parameter: *parameter* \[DeviceParameter\]  
1 = *parameter* can be modulated. Call this before *add\_parameter\_to\_modulation\_matrix*.

##### set\_modulation\_value

Parameters: *modulation\_target\_index* \[int\] *modulation\_source\_index* \[int\]  
Set the amount of the modulation of the parameter at *modulation\_target\_index* by the modulation source at *modulation\_source\_index* in Wavetable's modulation matrix.

## CompressorDevice

This class represents a Compressor device in Live.  
A CompressorDevice shares all of the children, functions and properties of a Device; listed below are the members unique to it.

#### Properties

##### available\_input\_routing\_channels

Type dict

Accessget, observe

###### Description

The list of available source channels for the compressor's input routing in the sidechain. It's represented as a dictionary with the following key:  
*available\_input\_routing\_channels* \[list\]  
The list contains dictionaries as described in *input\_routing\_channel*.

##### available\_input\_routing\_types

Type dict

Accessget, observe

###### Description

The list of available source types for the compressor's input routing in the sidechain. It's represented as a dictionary with the following key:  
*available\_input\_routing\_types* \[list\]  
The list contains dictionaries as described in *input\_routing\_type*.

##### input\_routing\_channel

Type dict

Accessget, set, observe

###### Description

The currently selected source channel for the compressor's input routing in the sidechain. It's represented as a dictionary with the following keys:  
*display\_name* \[symbol\]  
*identifier* \[symbol\]  
Can be set to all values found in the compressor's *available\_input\_routing\_channels*.

##### input\_routing\_type

Type dict

Accessget, set, observe

###### Description

The currently selected source type for the compressor's input routing in the sidechain. It's represented as a dictionary with the following keys:  
*display\_name* \[symbol\]  
*identifier* \[symbol\]  
Can be set to all values found in the track's *available\_input\_routing\_types*.

## PluginDevice

This class represents a plug-in device.  
  
A PluginDevice is a type of Device, meaning that it has all the children, properties and functions that a Device has. Listed below are the members unique to PluginDevice.

#### Properties

##### presets

Type StringVector

Accessget, observe

###### Description

Get the list of the plug-in's presets.

##### selected\_preset\_index

Type int

Accessget, set, observe

###### Description

Get/set the index of the currently selected preset.

## MaxDevice

This class represents a Max for Live device in Live.  
  
A MaxDevice is a type of Device, meaning that it has all the children, properties and functions that a Device has. Listed below are the members unique to MaxDevice.

#### Properties

##### audio\_inputs

Typelist of DeviceIO

Accessget, observe

###### Description

List of the audio inputs that the MaxDevice offers.

##### audio\_outputs

Typelist of DeviceIO

Accessget, observe

###### Description

List of the audio outputs that the MaxDevice offers.

##### midi\_inputs

Typelist of DeviceIO

Accessget, observe

###### Description

List of the midi inputs that the MaxDevice offers.  
  
*Available since Live 11.0.*

##### midi\_outputs

Typelist of DeviceIO

Accessget, observe

###### Description

List of the midi outputs that the MaxDevice offers.  
  
*Available since Live 11.0.*

#### Functions

##### get\_bank\_count

Returns: \[int\] the number of parameter banks.

##### get\_bank\_name

Parameters: *bank\_index* \[int\]  
Returns: \[list of symbols\] The name of the parameter bank specified by bank\_index.

##### get\_bank\_parameters

Parameters: *bank\_index* \[int\]  
Returns: \[list of ints\] The indices of the parameters contained in the bank specified by bank\_index. Empty slots are marked as -1. Bank index -1 refers to the "Best of" bank.

## MixerDevice

This class represents a mixer device in Live. It provides access to volume, panning and other DeviceParameter objects. See DeviceParameter to learn how to modify them.

#### Canonical path

###### live\_set tracks N mixer\_device

#### Children

##### sends

Typelist of DeviceParameter

Accessget, observe

###### Description

One send per return track.

##### cue\_volume

Type DeviceParameter

Accessget

###### Description

\[in master track only\]

##### crossfader

Type DeviceParameter

Accessget

###### Description

\[in master track only\]

##### left\_split\_stereo

Type DeviceParameter

Accessget

###### Description

The Track's Left Split Stereo Pan Parameter.

##### panning

Type DeviceParameter

Accessget

###### Description

##### right\_split\_stereo

Type DeviceParameter

Accessget

###### Description

The Track's Right Split Stereo Pan Parameter.

##### song\_tempo

Type DeviceParameter

Accessget

###### Description

\[in master track only\]

##### track\_activator

Type DeviceParameter

Accessget

###### Description

##### volume

Type DeviceParameter

Accessget

###### Description

#### Properties

##### crossfade\_assign

Type int

Accessget, set, observe

###### Description

0 = A, 1 = none, 2 = B \[not in master track\]

##### panning\_mode

Type int

Accessget, set, observe

###### Description

Access to the Track mixer's pan mode: 0 = Stereo, 1 = Split Stereo.

## Eq8Device

This class represents an instance of an EQ Eight device in Live.  
An Eq8Device has all the properties, functions and children of a Device. Listed below are members unique to Eq8Device.

#### Properties

##### edit\_mode

Type bool

Accessget, set, observe

###### Description

Access to EQ Eight's edit mode, which toggles the channel currently available for editing. The available edit modes depend on the global mode (see *global\_mode*) and are encoded as follows:  
  
In L/R mode: 0 = L, 1 = R  
In M/S mode: 0 = M, 1 = S  
In Stereo mode: 0 = A, 1 = B (inactive)

##### global\_mode

Type int

Accessget, set, observe

###### Description

Access to EQ Eight's global mode. The modes are encoded as follows:  
  
0 = Stereo  
1 = L/R  
2 = M/S

##### oversample

Type bool

Accessget, set, observe

###### Description

Access to EQ Eight's Oversampling parameter. 0 = Off, 1 = On.

## Eq8Device.View

Represents the view aspects of an Eq8Device.  
An Eq8Device.View has all the children, properties and functions of a Device.View. Listed below are members unique to it.

#### Properties

##### selected\_band

Type int

Accessget, set, observe

###### Description

The index of the currently selected filter band.

## DriftDevice

This class represents an instance of a Drift device in Live.  
A DriftDevice has all the properties, functions and children of a Device.

#### Properties

##### mod\_matrix\_filter\_source\_1\_index

Type int

Accessget, set, observe

###### Description

The index of the available sources for modulating the Filter Frequency for the first modulation slot.

##### mod\_matrix\_filter\_source\_1\_list

Type StringVector

Accessget

###### Description

The list of the available sources for modulating the Filter Frequency for the first modulation slot.

##### mod\_matrix\_filter\_source\_2\_index

Type int

Accessget, set, observe

###### Description

The index of the available sources for modulating the Filter Frequency for the second modulation slot.

##### mod\_matrix\_filter\_source\_2\_list

Type StringVector

Accessget

###### Description

The list of the available sources for modulating the Filter Frequency for the second modulation slot.

##### mod\_matrix\_lfo\_source\_index

Type int

Accessget, set, observe

###### Description

The index of the available sources for modulating the LFO Amount.

##### mod\_matrix\_lfo\_source\_list

Type StringVector

Accessget

###### Description

The list of the available sources for modulating the LFO Amount.

##### mod\_matrix\_pitch\_source\_1\_index

Type int

Accessget, set, observe

###### Description

The index of the available sources for modulating the Pitch for the first modulation slot.

##### mod\_matrix\_pitch\_source\_1\_list

Type StringVector

Accessget

###### Description

The list of the available sources for modulating the Pitch for the first modulation slot.

##### mod\_matrix\_pitch\_source\_2\_index

Type int

Accessget, set, observe

###### Description

The index of the available sources for modulating the Pitch for the second modulation slot.

##### mod\_matrix\_pitch\_source\_2\_list

Type StringVector

Accessget

###### Description

The list of the available sources for modulating the Pitch for the second modulation slot.

##### mod\_matrix\_shape\_source\_index

Type int

Accessget, set, observe

###### Description

The index of the available sources for modulating Shape.

##### mod\_matrix\_shape\_source\_list

Type StringVector

Accessget

###### Description

The list of the available sources for modulating Shape.

##### mod\_matrix\_source\_1\_index

Type int

Accessget, set, observe

###### Description

The index of the available sources for the first custom modulation slot.

##### mod\_matrix\_source\_1\_list

Type StringVector

Accessget

###### Description

The list of the available sources for the first custom modulation slot.

##### mod\_matrix\_source\_2\_index

Type int

Accessget, set, observe

###### Description

The index of the available sources for the second custom modulation slot.

##### mod\_matrix\_source\_2\_list

Type StringVector

Accessget

###### Description

The list of the available sources for the second custom modulation slot.

##### mod\_matrix\_source\_3\_index

Type int

Accessget, set, observe

###### Description

The index of the available sources for the third custom modulation slot.

##### mod\_matrix\_source\_3\_list

Type StringVector

Accessget

###### Description

The list of the available sources for the third custom modulation slot.

##### mod\_matrix\_target\_1\_index

Type int

Accessget, set, observe

###### Description

The index of the available targets for the first custom modulation slot.

##### mod\_matrix\_target\_1\_list

Type StringVector

Accessget

###### Description

The list of the available targets for the first custom modulation slot.

##### mod\_matrix\_target\_2\_index

Type int

Accessget, set, observe

###### Description

The index of the available targets for the second custom modulation slot.

##### mod\_matrix\_target\_2\_list

Type StringVector

Accessget

###### Description

The list of the available targets for the second custom modulation slot.

##### mod\_matrix\_target\_3\_index

Type int

Accessget, set, observe

###### Description

The index of the available targets for the third custom modulation slot.

##### mod\_matrix\_target\_3\_list

Type StringVector

Accessget

###### Description

The list of the available targets for the third custom modulation slot.

##### pitch\_bend\_range

Type int

Accessget, set, observe

###### Description

The amount for the MIDI Pitch Bend range in semitones.

##### voice\_count\_index

Type int

Accessget, set, observe

###### Description

The index of the voice count parameter.

##### voice\_count\_list

Type StringVector

Accessget

###### Description

The list of available voice count settings.

##### voice\_mode\_index

Type int

Accessget, set, observe

###### Description

The index of the voice mode utilized by Drift.

##### voice\_mode\_list

Type StringVector

Accessget

###### Description

The list of available voice modes.

## DrumCellDevice

This class represents an instance of a Drum Sampler device in Live.  
A DrumCell has all the properties, functions and children of a Device. Listed below are members unique to DrumCell Device.

#### Properties

##### gain

Type float

Accessget, set, observe

###### Description

The sample gain, as normalized value.

## HybridReverbDevice

This class represents an instance of a Hybrid Reverb device in Live.  
A HybridReverbDevice has all the properties, functions and children of a Device. Listed below are members unique to HybridReverbDevice.

#### Properties

##### ir\_attack\_time

Type float

Accessget, set, observe

###### Description

The attack time of the amplitude envelope for the impulse response, in seconds.

##### ir\_category\_index

Type int

Accessget, set, observe

###### Description

The index of the selected impulse response category.

##### ir\_category\_list

Type StringVector

Accessget

###### Description

The list of impulse response categories.

##### ir\_decay\_time

Type float

Accessget, set, observe

###### Description

The decay time of the amplitude envelope for the impulse response, in seconds.

##### ir\_file\_index

Type int

Accessget, set, observe

###### Description

The index of the selected impulse response files from the current category.

##### ir\_file\_list

Type StringVector

Accessget, observe

###### Description

The list of impulse response files from the selected category.

##### ir\_size\_factor

Type float

Accessget, set, observe

###### Description

The relative size of the impulse response, 0.0 to 1.0.

##### ir\_time\_shaping\_on

Type bool

Accessget, set, observe

###### Description

Enables transforming the current selected impulse response with an amplitude envelope and size parameter.  
1 = enabled.

## MeldDevice

This class represents an instance of a Meld device in Live.  
A MeldDevice has all the properties, functions and children of a Device.

#### Properties

##### selected\_engine

Type int

Accessget, set, observe

###### Description

Meld's oscillator engine selector. The modes are encoded as follows:  
0 = Engine A  
1 = Engine B

##### unison\_voices

Type int

Accessget, set, observe

###### Description

Selects the Unison voice count. The modes are encoded as follows:  
  
0 = off  
1 = two  
2 = three  
3 = four

##### mono\_poly

Type int

Accessget, set, observe

###### Description

Selects the polyphony mode. The modes are encoded as follows:  
  
0 = mono  
1 = poly

##### poly\_voices

Type int

Accessget, set, observe

###### Description

Selects the polyphony voice count. The modes are encoded as follows:  
  
0 = two  
1 = three  
2 = four  
3 = five  
4 = six  
5 = eight  
6 = twelve

## RoarDevice

This class represents an instance of a Roar device in Live.  
A RoarDevice has all the properties, functions and children of a Roar Device.

#### Properties

##### routing\_mode\_index

Type int

Accessget, set, observe

###### Description

The index of the routing mode utilized by Roar.

##### routing\_mode\_list

Type StringVector

Accessget

###### Description

The list of available routing modes.

##### env\_listen

Type bool

Accessget, set, observe

###### Description

Get, set and observe the Envelope Input Listen toogle.

## SpectralResonatorDevice

This class represents an instance of a Spectral Resonator device in Live.  
An SpectralResonatorDevice has all the properties, functions and children of a Device. Listed below are members unique to SpectralResonatorDevice.

#### Properties

##### frequency\_dial\_mode

Type int

Accessget, set, observe

###### Description

Get, set and observe the Freq control's mode.  
0 = Hertz, 1 = MIDI note values.

##### midi\_gate

Type int

Accessget, set, observe

###### Description

Get, set and observe the MIDI gate switch's state.  
0 = Off, 1 = On.

##### mod\_mode

Type int

Accessget, set, observe

###### Description

Get, set and observe the Modulation Mode.  
0 = None, 1 = Chorus, 2 = Wander, 3 = Granular.

##### mono\_poly

Type int

Accessget, set, observe

###### Description

Get, set and observe the Mono/Poly switch's state.  
0 = Mono, 1 = Poly.

##### pitch\_mode

Type int

Accessget, set, observe

###### Description

Get, set and observe the Pitch Mode.  
0 = Internal, 1 = MIDI.

##### pitch\_bend\_range

Type int

Accessget, set, observe

###### Description

Get, set and observe the Pitch Bend Range.

##### polyphony

Type int

Accessget, set, observe

###### Description

Get, set and observe the Polyphony.  
0 = 2, 1 = 4, 2 = 8, 3 = 16 voices.

## LooperDevice

This class represents an instance of a Looper device in Live.  
An LooperDevice has all the properties, functions and children of a Device. Listed below are members unique to LooperDevice.

#### Properties

##### loop\_length

Type double

Accessget, observe

###### Description

The length of Looper's buffer.

##### overdub\_after\_record

Type bool

Accessget, set, observe

###### Description

1 = Looper will switch to overdub after recording, when recording a fixed number of bars. 0 = switch to playback without overdubbing.

##### record\_length\_index

Type int

Accessget, set, observe

###### Description

Access to the Record Length chooser entry index.

##### record\_length\_list

Type StringVector

Accessget

###### Description

Access to the list of Record Length chooser entry strings.

##### tempo

Type double

Accessget, observe

###### Description

The tempo of Looper's buffer.

#### Functions

##### clear

Erase Looper's recorded content.

##### double\_speed

Double the speed of Looper's playback.

##### half\_speed

Halve the speed of Looper's playback.

##### double\_length

Double the length of Looper's buffer.

##### half\_length

Halve the length of Looper's buffer.

##### record

Record incoming audio.

##### overdub

Play back while adding additional layers of incoming audio.

##### play

Play back without overdubbing.

##### stop

Stop Looper's playback.

##### undo

Erase everything that was recorded since the last time Overdub was enabled. Calling a second time will restore the material erased by the previous undo operation.

##### export\_to\_clip\_slot

Parameter: *clip\_slot* \[ClipSlot\]  
The target clip slot.  
  
Given a valid LOM ID of an empty clip slot on a non-frozen audio track, will export Looper's content to a clip in that slot. This is similar to using the Drag Me! control on the Looper device, and the same restrictions apply: the audio engine must be turned on, the Looper must actually hold audio content, the content must have a fixed length (i.e. Looper must not be recording), etc.

## DeviceIO

This class represents an input or output bus of a Live device.

#### Properties

##### available\_routing\_channels

Type dictionary

Accessget, observe

###### Description

The available channels for this input/output bus. The channels are represented as a *dictionary* with the following key:  
*available\_routing\_channels* \[list\]  
The list contains *dictionaries* as described in *routing\_channel*.

##### available\_routing\_types

Type dictionary

Accessget, observe

###### Description

The available types for this input/output bus. The types are represented as a *dictionary* with the following key:  
*available\_routing\_types* \[list\]  
The list contains *dictionaries* as described in *routing\_type*.

##### default\_external\_routing\_channel\_is\_none

Type bool

Accessget, set

###### Description

1 = the default routing channel for External routing types is none.  
  
*Available since Live 11.0.*

##### routing\_channel

Type dictionary

Accessget, set, observe

###### Description

The current routing channel for this input/output bus. It is represented as a *dictionary* with the following keys:  
*display\_name* \[symbol\]  
*identifier* \[symbol\]  
Can be set to any of the values found in *available\_routing\_channels.*

##### routing\_type

Type dictionary

Accessget, set, observe

###### Description

The current routing type for this input/output bus. It is represented as a *dictionary* with the following keys:  
*display\_name* \[symbol\]  
*identifier* \[symbol\]  
Can be set to any of the values found in *available\_routing\_types.*

## Scene

This class represents a series of clip slots in Live's Session View matrix.

#### Canonical path

###### live\_set scenes N

#### Children

##### clip\_slots

Typelist of ClipSlot

Accessget, observe

###### Description

#### Properties

##### color

Type int

Accessget, set, observe

###### Description

The RGB value of the scene's color in the form 0x00rrggbb or (2^16 \* red) + (2^8) \* green + blue, where red, green and blue are values from 0 (dark) to 255 (light).  
  
When setting the RGB value, the nearest color from the Scene color chooser is taken.

##### color\_index

Type long

Accessget, set, observe

###### Description

The color index of the scene.

##### is\_empty

Type bool

Accessget

###### Description

1 = none of the slots in the scene is filled.

##### is\_triggered

Type bool

Accessget, observe

###### Description

1 = scene is blinking.

##### name

Type symbol

Accessget, set, observe

###### Description

The name of the scene.

##### tempo

Type float

Accessget, set, observe

###### Description

The scene's tempo.  
Returns -1 if the scene tempo is disabled.

##### tempo\_enabled

Type bool

Accessget, set, observe

###### Description

The active state of the scene tempo.  
When disabled, the scene will use the song's tempo,  
and the tempo value returned will be -1.

##### time\_signature\_numerator

Type int

Accessget, set, observe

###### Description

The scene's time signature numerator.  
Returns -1 if the scene time signature is disabled.

##### time\_signature\_denominator

Type int

Accessget, set, observe

###### Description

The scene's time signature denominator.  
Returns -1 if the scene time signature is disabled.

##### time\_signature\_enabled

Type bool

Accessget, set, observe

###### Description

The active state of the scene time signature.  
When disabled, the scene will use the song's time signature,  
and the time signature values returned will be -1.

#### Functions

##### fire

Parameter: force\_legato (optional) \[bool\]  
can\_select\_scene\_on\_launch (optional) \[bool\]  
Fire all clip slots contained within the scene and select this scene.  
Starts recording of armed and empty tracks within a Group Track in this scene if Preferences->Launch->Start Recording on Scene Launch is ON.  
Calling with force\_legato = 1 (default = 0) will launch all clips immediately in Legato, independent of their launch mode.  
When calling with can\_select\_scene\_on\_launch = 0 (default = 1) the scene is fired without selecting it.

##### fire\_as\_selected

Parameter: force\_legato (optional) \[bool\]  
Fire the selected scene, then select the next scene.  
It doesn't matter on which scene you are calling this function.  
Calling with force\_legato = 1 (default = 0) will launch all clips immediately in Legato, independent of their launch mode.

##### set\_fire\_button\_state

Parameter: *state* \[bool\]  
If the state is set to 1, Live simulates pressing of scene button until the state is set to 0 or until the scene is stopped otherwise.

## CuePoint

Represents a locator in the Arrangement View.

#### Canonical path

###### live\_set cue\_points N

#### Properties

##### name

Type symbol

Accessget, set, observe

###### Description

##### time

Type float

Accessget, observe

###### Description

Arrangement position of the marker in beats.

#### Functions

##### jump

Set current Arrangement playback position to marker, quantized if song is playing.

## ControlSurface

A ControlSurface can be reached either directly by the root path control\_surfaces *N* or by getting a list of active control surface IDs, via calling *get control\_surfaces* on an Application object.  
The latter list is in the same order in which control surfaces appear in Live's Link/MIDI Preferences. Note the same order is not guaranteed when getting a control surface via the control\_surfaces *N* path.  
  
A control surface can be thought of as a software layer between the Live API and, in this case, Max for Live. Individiual controls on the surface are represented by objects that can be grabbed and released via Max for Live, to obtain and give back exclusive control (see *grab\_control* and *release\_control*). In this way, parts of the hardware can be controlled via Max for Live while other parts can retain their default functionality.  
  
Additionally, Live offers a special *MaxForLive* control surface that has a *register\_midi\_control* function. Using this, Max for Live developers can set up entirely custom control surfaces by adding and grabbing arbitrary controls.

#### Canonical path

###### control\_surfaces N

#### Functions

##### get\_control

Parameter: name  
Returns the control with the given name.

##### get\_control\_names

Returns the list of all control names.

##### grab\_control

Parameter: control  
Take ownership of the *control*. This releases all standard functionality of the control, so that it can be used exclusively via Max for Live.

##### grab\_midi

Forward MIDI messages received from the control surface to Max for Live.

##### release\_control

Parameter: control  
Re-establishes the standard functionality for the control.

##### release\_midi

Stop forwarding MIDI messages received from the control surface to Max for Live.

##### send\_midi

Parameter: *midi\_message* \[list of int\]  
Send *midi\_message* to the control surface.

##### send\_receive\_sysex

Parameters:  
*sysex\_message* \[list of int\]  
*timeout* \[symbol, int\]  
Send *sysex\_message* to the control surface and await a response.  
If the message is followed by the word *timeout* and a float, this sets the response timeout accordingly. The default timeout value is 0.2.  
If the response times out and MIDI has not been grabbed via *grab\_midi*, it's not forwarded to Max for Live. If MIDI has been grabbed via Max for Live, received messages are always forwarded, but the timeout is still reported.

## this\_device

This root path represents the device containing the [live.path](https://docs.cycling74.com/max8/refpages/live.path) object to which the goto this\_device message is sent. The class of this object is Device.