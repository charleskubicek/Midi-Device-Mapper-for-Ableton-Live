export PYTHONPATH=.:$PYTHONPATH
( cd ../../ && poetry run python ableton_control_surface_as_code/gen.py live_surfaces/launch_control/ck_launch_control_16.nt )