from functools import partial

from .css_lib import *

sample_categories = [
    Category('Arp', ['arp'], synth),
    Category('Atmo', ['atmo', 'atmos'], atmos),
    Category('Bass', ['bass'], bass),
    Category('Chords', ['chord'], synth),
    Category('Claps', ['clap'], claps),
    Category('Cymbals', ['cymbal'], crash),
    Category('Crashes', ['crash'], crash),
    Category('Drone', ['drone'], drone),
    Category('Down', ['down'], fx),
    Category('Fx', ['fx', 'sfx'], fx),
    Category('Foley', ['foley'], fx),
    Category('HiHats', ['hihat', 'hi-hats', 'hat'], hats),
    Category("Kicks", ['kick'], kick_blue),
    Category('Noise', ['noise'], noise),
    Category('Impacts', ['impact'], fx),
    Category('OHH', ['ohh', 'open'], hats),
    Category('CHH', ['chh', 'closed'], hats),
    Category('Pad', ['pad'], drone),
    Category('Perc', ['perc', 'clav'], perc),
    Category('Rides', ['ride'], hats),
    Category('Riser', ['riser'], fx),
    Category("Snare", ['snare'], claps),
    Category("Tom", ['tom'], perc),
    Category("Top", ['top'], hats),
    Category("Text", ['text'], noise),
    Category("Rumble", ['rumble'], kick_blue),
    Category('Shaker', ['shaker'], hats),
    Category('Synth', ['synth', 'syn',  'lead', 'melodic'], synth),
    Category('Stab', ['stab'], synth),
    Category('Vocal', ['vocal', 'vox'], vox),
]

sample_category_maps = dict([(c.name, c) for c in sample_categories])


def lookup_sample_category(name):
    guess = sample_category_for(name)
    return sample_category_maps.get(guess)

def sample_category_for(name):
    for fn in sample_alias_lookup:
        res = fn(name)
        if res is not None:
            return res

    print(' ** Unknown category for:', name)
    return None


# private, use cagetory_for instead
def sample_map_aliases(aliases, canonical_name, given_name: str):
    for delim in [' ', '_', '-']:
        for part in given_name.lower().split(delim):
            for alias in aliases:
                if part.startswith(alias):
                    return canonical_name

    return None


sample_alias_lookup = [partial(sample_map_aliases, v.aliases, k) for k, v in sample_category_maps.items()]
