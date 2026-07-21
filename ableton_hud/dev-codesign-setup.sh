#!/bin/bash
# One-time: create a stable self-signed code-signing certificate so the HUD's
# macOS TCC grants (Input Monitoring / Accessibility, needed by
# GlobalInputMonitor for input-driven auto-hide) survive rebuilds.
#
# Ad-hoc signing keys a permission grant to the binary's exact code hash, which
# changes on every build — so the grant resets each rebuild. Signing with a
# stable cert instead keys the grant to the cert identity, so you approve the
# permissions once and never again.
#
# create-app-bundle.sh signs with this cert automatically when present.
#
# After running this once, you must re-grant Input Monitoring + Accessibility to
# AbletonHUD ONE more time (its identity changed from ad-hoc to cert-signed);
# after that the grant persists across all future rebuilds.
set -e

CERT_NAME="AbletonHUD Local Dev"
KC="$HOME/Library/Keychains/login.keychain-db"

if security find-certificate -c "$CERT_NAME" >/dev/null 2>&1; then
    echo "Certificate '$CERT_NAME' already exists — nothing to do."
    exit 0
fi

echo "Creating self-signed code-signing certificate '$CERT_NAME'..."
CONF="$(mktemp)"
KEY="$(mktemp)"
CRT="$(mktemp)"
cat > "$CONF" <<'EOF'
[req]
distinguished_name = dn
x509_extensions = v3
prompt = no
[dn]
CN = AbletonHUD Local Dev
[v3]
keyUsage = critical, digitalSignature
extendedKeyUsage = critical, codeSigning
basicConstraints = critical, CA:false
EOF

# PEM key + cert imported separately: macOS `security` chokes on OpenSSL 3.x
# PKCS12 MAC, but imports PEMs directly and matches them by public key.
openssl req -x509 -newkey rsa:2048 -keyout "$KEY" -out "$CRT" -days 3650 -nodes -config "$CONF" >/dev/null 2>&1
security import "$KEY" -k "$KC" -T /usr/bin/codesign -A
security import "$CRT" -k "$KC" -T /usr/bin/codesign -A
rm -f "$CONF" "$KEY" "$CRT"

echo ""
echo "Done. The first codesign after this will pop a keychain prompt —"
echo "click 'Always Allow' so future rebuilds don't prompt."
echo "Then rebuild (./create-app-bundle.sh) and re-grant Input Monitoring +"
echo "Accessibility to AbletonHUD once. The grant persists after that."
