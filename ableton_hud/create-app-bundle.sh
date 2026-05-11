#!/bin/bash
set -e

APP_NAME="AbletonHUD"
BUNDLE="$APP_NAME.app"
CONTENTS="$BUNDLE/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

echo "Building $APP_NAME..."
swift build -c release --product "$APP_NAME"

echo "Assembling $BUNDLE..."
rm -rf "$BUNDLE"
mkdir -p "$MACOS" "$RESOURCES"

cp ".build/release/$APP_NAME" "$MACOS/"
cp "Info.plist" "$CONTENTS/"
echo -n "APPL????" > "$CONTENTS/PkgInfo"

echo ""
echo "Done: $BUNDLE"
echo "Run with: open $BUNDLE"
