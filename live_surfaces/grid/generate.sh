export PYTHONPATH=.:$PYTHONPATH
( cd ../../ && poetry run python ableton_control_surface_as_code/gen.py live_surfaces/grid/ck_grid.nt )