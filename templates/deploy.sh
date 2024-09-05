export ABLETON_APP="$ableton_dir"

export SCRIPTS_HOME="$$ABLETON_APP/Contents/App-Resources/MIDI Remote Scripts"
mkdir -p "$$SCRIPTS_HOME/$surface_name/modules" && \
cp *.py "$$SCRIPTS_HOME/$surface_name/" && \
cp modules/*.py "$$SCRIPTS_HOME/$surface_name/modules/"
