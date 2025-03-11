#!/bin/bash

# Ensure a key argument is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <top_level_key> <input_json_file>"
  exit 1
fi

# Assign arguments to variables
TOP_KEY="$1"
INPUT_FILE="${2:-/dev/stdin}"  # Use stdin if no file is provided

# Run jq to extract and format the parameter names
jq -r --arg key "$TOP_KEY" '.[$key].parameters[].name | "- " + .' "$INPUT_FILE"