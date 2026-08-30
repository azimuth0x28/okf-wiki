#!/usr/bin/env bash
# Register the Brain Capture native-messaging host into installed browsers.
#
# The host is STAGED into ~/.config/okf-wiki/brain-capture/ (a private copy of
# brain_capture_host.py + the okf_wiki package + a launcher). Chrome-launched
# processes inherit the browser's sandbox/TCC context: on macOS a host living
# inside ~/Documents or an office checkout can't be traversed, which surfaces
# only as the opaque "Native host has exited". A staged copy under the home
# directory plus a baked-in PATH avoids that class of failure entirely.
#
# Usage: install.sh <extension-id>
#        (the ID is shown on chrome://extensions after "Load unpacked")
set -euo pipefail

EXT_ID="${1:-}"
if [[ -z "$EXT_ID" ]]; then
  echo "usage: $0 <extension-id>" >&2
  echo "  the ID appears on chrome://extensions after loading the extension" >&2
  exit 2
fi

HOST_NAME="com.okf_wiki.brain_capture"
HOST_SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$HOST_SRC_DIR/../../.." && pwd)"
STAGE_DIR="$HOME/.config/okf-wiki/brain-capture"
LIB_DIR="$STAGE_DIR/lib"
LAUNCHER="$STAGE_DIR/run-host.sh"

mkdir -p "$STAGE_DIR"
cp "$HOST_SRC_DIR/brain_capture_host.py" "$STAGE_DIR/brain_capture_host.py"
chmod +x "$STAGE_DIR/brain_capture_host.py"

# Stage the okf_wiki package the host imports for config resolution.
if [[ -d "$REPO_DIR/okf_wiki" ]]; then
  rm -rf "$LIB_DIR"
  mkdir -p "$LIB_DIR"
  cp -R "$REPO_DIR/okf_wiki" "$LIB_DIR/okf_wiki"
  find "$LIB_DIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
elif ! python3 -c "import okf_wiki" >/dev/null 2>&1; then
  echo "error: okf_wiki package not found (expected $REPO_DIR/okf_wiki or importable)" >&2
  exit 1
fi

# The host shells out to `okf-wiki capture`; bake its location into the launcher.
OKF_WIKI_BIN="$(command -v okf-wiki || true)"
if [[ -z "$OKF_WIKI_BIN" && -x "$REPO_DIR/.venv/bin/okf-wiki" ]]; then
  OKF_WIKI_BIN="$REPO_DIR/.venv/bin/okf-wiki"
fi
if [[ -z "$OKF_WIKI_BIN" ]]; then
  echo "error: okf-wiki CLI not found (pip install -e '$REPO_DIR' first)" >&2
  exit 1
fi
"$OKF_WIKI_BIN" capture --help 2>/dev/null | grep -q "capture" || {
  echo "error: $OKF_WIKI_BIN does not support 'capture'" >&2
  exit 1
}

cat > "$LAUNCHER" <<LAUNCHER
#!/bin/bash
export PYTHONPATH="$LIB_DIR\${PYTHONPATH:+:\$PYTHONPATH}"
export PATH="$REPO_DIR/.venv/bin:\$PATH"
export HOME="$HOME"
export USER="$(id -un)"
export LOGNAME="$(id -un)"
export SHELL="$(command -v bash || echo /bin/bash)"
exec python3 "$STAGE_DIR/brain_capture_host.py"
LAUNCHER
chmod +x "$LAUNCHER"

MANIFEST_JSON="$STAGE_DIR/$HOST_NAME.json"
cat > "$MANIFEST_JSON" <<MANIFEST
{
  "name": "$HOST_NAME",
  "description": "Brain Capture native host for okf-wiki",
  "path": "$LAUNCHER",
  "type": "stdio",
  "allowed_origins": ["chrome-extension://$EXT_ID/"]
}
MANIFEST

TARGETS=(
  "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
  "$HOME/Library/Application Support/Google/Chrome Canary/NativeMessagingHosts"
  "$HOME/Library/Application Support/Chromium/NativeMessagingHosts"
  "$HOME/Library/Application Support/BraveSoftware/Brave-Browser/NativeMessagingHosts"
  "$HOME/.config/google-chrome/NativeMessagingHosts"
  "$HOME/.config/chromium/NativeMessagingHosts"
  "$HOME/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
)

registered=0
for target in "${TARGETS[@]}"; do
  [[ -d "$(dirname "$target")" ]] || continue
  mkdir -p "$target"
  cp "$MANIFEST_JSON" "$target/$HOST_NAME.json"
  echo "registered: $target/$HOST_NAME.json"
  registered=$((registered + 1))
done

if [[ "$registered" -eq 0 ]]; then
  echo "no browser profile directories found — install a browser, then re-run"
fi

echo
echo "staged host:  $STAGE_DIR"
echo "extension ID: $EXT_ID"
echo "next step:    reload the extension on chrome://extensions, then reopen the popup (⌘Q restarts Chrome if the host was just added)"
