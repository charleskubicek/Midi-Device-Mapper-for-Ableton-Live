export ABLETON_APP="$ableton_dir"

export SCRIPTS_HOME="$$ABLETON_APP/Contents/App-Resources/MIDI Remote Scripts"
echo "Copying files to $$SCRIPTS_HOME/$surface_name"
mkdir -p "$$SCRIPTS_HOME/$surface_name/modules" && \
cp *.py "$$SCRIPTS_HOME/$surface_name/" && \
cp -R modules/. "$$SCRIPTS_HOME/$surface_name/modules/"
