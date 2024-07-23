export ABLETON_APP="$ableton_dir"

export SCRIPTS_HOME="$$ABLETON_APP/Contents/App-Resources/MIDI Remote Scripts"
mkdir -p "$$SCRIPTS_HOME/$surface_name/modules" && \
cp $surface_name.py "$$SCRIPTS_HOME/$surface_name/$surface_name.py" && \
cp modules/*.py "$$SCRIPTS_HOME/$surface_name/modules/"
