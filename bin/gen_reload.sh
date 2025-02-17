poetry run python3 ableton_control_surface_as_code/gen.py && \
cd out/ck_test_novation_xl && \
sh deploy.sh && \
poetry run python3 update.py reload
