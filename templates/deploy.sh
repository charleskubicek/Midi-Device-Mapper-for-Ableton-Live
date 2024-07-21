export ABLETON_APP="$ableton_dir"

export SCRIPTS_HOME="$$ABLETON_APP/Contents/App-Resources/MIDI Remote Scripts"
mkdir -p "$$SCRIPTS_HOME/$surface_name/modules" && \
cp $surface_name.py "$$SCRIPTS_HOME/$surface_name/$surface_name.py" && \
cp modules/$class_name_snake.py "$$SCRIPTS_HOME/$surface_name/modules/$class_name_snake.py"
cp modules/functions.py "$$SCRIPTS_HOME/$surface_name/modules/functions.py"
cp modules/helpers.py "$$SCRIPTS_HOME/$surface_name/modules/helpers.py"
cp __init__.py "$$SCRIPTS_HOME/$surface_name/__init__.py"
