"""The `@hud_name(...)` decorator for Functions methods.

At runtime this is a no-op that just tags the method with the label (so the
generated surface imports cleanly inside Ableton). The code generator reads the
same decorator statically — see FunctionLookup in model_functions.py — and uses
the label as the HUD cell name for every mapping that references the function.
"""


def hud_name(label):
    def decorator(fn):
        fn._hud_name = label
        return fn

    return decorator
