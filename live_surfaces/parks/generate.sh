export PYTHONPATH=.:$PYTHONPATH
( cd ../../ && poetry run python ableton_control_surface_as_code/gen.py live_surfaces/parks/ck_parkstool_12E1.nt )