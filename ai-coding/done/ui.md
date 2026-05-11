1. Kill the Transparency (The #1 Fix)
   The biggest enemy of readability right now is the Ableton mixer bleeding through from the background.
   •	Action: Change the background of your overlay panel to 100% opacity (solid dark grey/near-black)
2. High-Contrast Dial Indicators
   Overall Layout
   •	Shape: An incomplete circular ring (an arc) resembling a typical volume or gain knob, with a gap at the bottom.
   
Dial Components
   The Track (Background Arc): * A thick, black or very dark gray arc.
   •	It starts at roughly the 7 o'clock position (around 225 degrees) and sweeps clockwise to the 5 o'clock position (around 135 degrees).
   •	The stroke has rounded caps (lineCap: .round).
   The Fill (Active Arc):

   •	A thick, bright cyan/light blue arc that sits directly on top of the track and represents the parameter value
   •	It starts at the exact same bottom-left point (7 o'clock) and sweeps clockwise, ending precisely at the top-center (12 o'clock position).
   •	This stroke also has rounded caps.

   The Indicator (Needle):
   •	A thick vertical line matching the color of the dark background track.
   •	It originates from the center of the circle and points straight up (12 o'clock), stopping right where the cyan arc ends.
   •	It features rounded caps on both ends.
3. Font Weight and Color
   The text is slightly thin, which makes it harder to read against a dark, busy background.
   •	Action: Increase the font weight from Regular to Medium or Semi-Bold.
4. Breathing Room (Whitespace)
   The text is sitting very tightly against the dials and buttons.
   •	Action: Add a few pixels of padding/margin between the bottom of the dial and the top of the text. Just a tiny bit of negative space will stop the elements from blending together into a single vertical blob.
   Are you drawing these dials using standard CSS/HTML, or are you rendering them on a canvas using something like Python or Javascript?