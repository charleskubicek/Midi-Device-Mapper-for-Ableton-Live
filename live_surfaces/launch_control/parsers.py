# name = 'CK slk - ADRK DT clap [Claps] - [Oneshot] [10]'
import re
from .sample_categories import *

known_instrument_name_types = {
    "grain": 'Atmos',
    "atlas": 'Perc',
    "skaka": 'Perc'
}


def guess_track_type_from_instrument_name(name: str):
    search = re.search(r'\[(.*?)\]', name)
    if search is not None:
        return search.group(1)
    else:
        for part in name.lower().split(' '):
            if part in known_instrument_name_types:
                return known_instrument_name_types[part]


def guess_cat_from_instrument_name(name: str):
    guess = guess_track_type_from_instrument_name(name)

    if guess is not None:
        return sample_category_maps.get(guess)
    else:
        return None


def guess_cat_from_track_name(name: str):
    for delim in [' ', '-']:
        for part in name.lower().split(delim):
            guess = sample_category_for(part)
            if guess is not None:
                return sample_category_maps.get(guess)

    return None


def update_with_track_number(guess, track_name):
    possible_number = try_get_track_number(track_name)
    if possible_number is not None:
        return '# ' + guess

    return guess


def try_get_track_number(name):
    first_part = name.split(' ')[0]
    if first_part.isnumeric():
        return first_part

    first_part = name.split('-')[0]
    if first_part.isnumeric():
        return first_part

    return None


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text  # or whatever
