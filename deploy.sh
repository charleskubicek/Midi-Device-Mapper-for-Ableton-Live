export SCRIPTS_HOME="/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts"
#pushd css && pytest && popd \
#cp css/*.py "$SCRIPTS_HOME/css_ck_launchcontrol_script" && \
#cp css/*.py "$SCRIPTS_HOME/css_ck_midimix" && \
cp ck_custom/ck_custom.py "$SCRIPTS_HOME/ck_custom/ck_custom.py" && \
cp ck_custom/__init__.py "$SCRIPTS_HOME/ck_custom/__init__.py" && \
mkdir -p "$SCRIPTS_HOME/ck_custom/ableton_control_suface_as_code" && \
cp ck_custom/ableton_control_suface_as_code/custom_ops.py "$SCRIPTS_HOME/ck_custom/ableton_control_suface_as_code/custom_ops.py"