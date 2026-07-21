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

# Code-sign with a stable local identity so macOS TCC grants (Input Monitoring /
# Accessibility, needed by GlobalInputMonitor) survive rebuilds. Ad-hoc signing
# keys the grant to the binary's hash, which changes every build, forcing a
# re-grant each time. The self-signed "AbletonHUD Local Dev" cert gives a stable
# designated requirement, so you approve the permissions once. Create the cert
# with ./dev-codesign-setup.sh; falls back to ad-hoc (with a warning) if absent.
SIGN_ID="AbletonHUD Local Dev"
if security find-certificate -c "$SIGN_ID" >/dev/null 2>&1; then
    echo "Signing with '$SIGN_ID'..."
    codesign --force --deep -s "$SIGN_ID" "$BUNDLE"
else
    echo "WARNING: '$SIGN_ID' cert not found — ad-hoc signing (Input Monitoring/"
    echo "         Accessibility grants will reset on each rebuild). Run ./dev-codesign-setup.sh."
    codesign --force --deep -s - "$BUNDLE"
fi

echo ""
echo "Done: $BUNDLE"
echo "Run with: open $BUNDLE"
