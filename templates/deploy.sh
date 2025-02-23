export ABLETON_APP="$ableton_dir"

export SCRIPTS_HOME="$$ABLETON_APP/Contents/App-Resources/MIDI Remote Scripts"
echo "Copying files to $$SCRIPTS_HOME/$surface_name"
mkdir -p "$$SCRIPTS_HOME/$surface_name/modules" && \
mkdir -p "$$SCRIPTS_HOME/$surface_name/modules/pythonosc/parsing" && \
cp *.py "$$SCRIPTS_HOME/$surface_name/" && \
cp modules/*.py "$$SCRIPTS_HOME/$surface_name/modules/"
cp modules/pythonosc/*.py "$$SCRIPTS_HOME/$surface_name/modules/pythonosc/"
cp modules/pythonosc/parsing/*.py "$$SCRIPTS_HOME/$surface_name/modules/pythonosc/parsing/"
