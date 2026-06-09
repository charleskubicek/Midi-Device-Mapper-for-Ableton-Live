from typing import List

from dataclasses import dataclass

deep_green = 19
synth_purple = 11

kick_blue = 22
bass = 24
lead = synth_purple
synth = synth_purple
stab = 52
drone = 62
claps = deep_green
perc = deep_green
vox = 14
crash = 17
hats = 17
atmos = 27
fx = 41
noise = 41



@dataclass(frozen=True)
class Category:
    name: str
    aliases: List[str]
    colour: int


synth_categories = [
    Category('Arp', ['arp'], lead),
    Category('Atmo', ['atmo','atm', 'atmos', 'texture'], atmos),
    Category('Bass', ['bs', 'ba', 'bass'], bass),
    Category('Drone', ['drone'], drone),
    Category('Down', ['down'], fx),
    Category('Fx', ['fx', 'sfx'], fx),
    Category('Noise', ['noise'], noise),
    Category('Impacts', ['hit', 'impact'], fx),
    Category('Pad', ['pd', 'pad'], drone),
    Category('Perc', ['perc','drm', 'drums'], perc),
    Category('Riser', ['riser'], fx),
    Category('Lead', ['synth', 'chord', 'crd', 'ld', 'sy', 'lead', 'melodic', 'acid','poly' ], lead),
    Category('Seq', ['seq', 'sequence'], lead),
    Category('Stab', ['pl','plk','stb', 'pluck', 'stab'], stab)
]
