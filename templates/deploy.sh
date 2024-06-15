export SCRIPTS_HOME="/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts"
mkdir -p "$$SCRIPTS_HOME/$surface_name/modules" && \
cp $surface_name.py "$$SCRIPTS_HOME/$surface_name/$surface_name.py" && \
cp modules/$class_name_snake.py "$$SCRIPTS_HOME/$surface_name/modules/$class_name_snake.py"
cp __init__.py "$$SCRIPTS_HOME/$surface_name/__init__.py"
