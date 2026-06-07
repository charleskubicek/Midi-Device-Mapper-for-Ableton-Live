from functools import partial

from .css_lib import *

synth_categories = [
    Category('Arp', ['arp'], lead),
    Category('Atmo', ['atmo', 'atm', 'atmos', 'texture'], atmos),
    Category('Bass', ['bs', 'ba', 'bass'], bass),
    Category('Drone', ['drone'], drone),
    Category('Down', ['down'], fx),
    Category('Fx', ['fx', 'sfx'], fx),
    Category('Noise', ['noise'], noise),
    Category('Impacts', ['hit', 'impact'], fx),
    Category('Pad', ['pd', 'pad'], drone),
    Category('Perc', ['perc', 'drm', 'drums'], perc),
    Category('Riser', ['riser'], fx),
    Category('Lead', ['synth', 'chord', 'crd', 'ld', 'sy', 'lead', 'melodic', 'acid', 'poly'], lead),
    Category('Seq', ['seq', 'sequence'], lead),
    Category('Stab', ['pl', 'plk', 'stb', 'pluck', 'stab'], stab)
]

synth_category_maps = dict([(c.name, c) for c in synth_categories])



def lookup_synth_category(name):
    guess = synth_category_for(name)
    return synth_category_maps.get(guess)



def synth_category_for(name):
    for fn in synth_alias_lookup:
        res = fn(name)
        if res is not None:
            return res

    print(' ** Unknown synth category for:', name)
    return None


# private, use cagetory_for instead
def map_synth_aliases(aliases, canonical_name, given_name: str):
    for part in given_name.lower().split(' '):
        if part in aliases:
            return canonical_name

    return None


synth_alias_lookup = [partial(map_synth_aliases, v.aliases, k) for k, v in synth_category_maps.items()]
