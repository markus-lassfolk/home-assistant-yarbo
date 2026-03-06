#!/usr/bin/env bash
# Install latest home-assistant-yarbo integration and python-yarbo into a Home Assistant
# instance for testing before release.
#
# Usage:
#   ./scripts/install_latest_to_hass.sh [HASS_CONFIG_DIR] [PYTHON_YARBO_DIR]
#
# Examples:
#   ./scripts/install_latest_to_hass.sh
#     → uses HASS_CONFIG_DIR=./config (default), PYTHON_YARBO_DIR=../python-yarbo
#   ./scripts/install_latest_to_hass.sh /path/to/ha/config /path/to/python-yarbo
#
# For HA in a venv: after running this, activate the HA venv and run the printed
#   pip install ... command to install the built python-yarbo wheel.
# For HA OS / Supervised: copy the integration via Samba/SSH; install python-yarbo
#   via Terminal & SSH add-on (see docs/testing-before-release.md).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_HASS_CONFIG="${HASS_CONFIG:-$REPO_ROOT/config}"
DEFAULT_PYTHON_YARBO="${PYTHON_YARBO:-$REPO_ROOT/../python-yarbo}"

HASS_CONFIG="${1:-$DEFAULT_HASS_CONFIG}"
PYTHON_YARBO_DIR="${2:-$DEFAULT_PYTHON_YARBO}"

echo "=== Install latest Yarbo for HASS testing ==="
echo "  Integration repo:  $REPO_ROOT"
echo "  HASS config dir:   $HASS_CONFIG"
echo "  python-yarbo repo:  $PYTHON_YARBO_DIR"
echo ""

# 1) Copy integration into HASS custom_components
DEST="$HASS_CONFIG/custom_components/yarbo"
mkdir -p "$HASS_CONFIG/custom_components"
if [[ -d "$REPO_ROOT/custom_components/yarbo" ]]; then
  echo "1) Copying integration to $DEST ..."
  rm -rf "$DEST"
  cp -a "$REPO_ROOT/custom_components/yarbo" "$DEST"
  echo "   Done. Integration version: $(grep -E '"version"' "$DEST/manifest.json" | head -1)"
else
  echo "1) ERROR: $REPO_ROOT/custom_components/yarbo not found"
  exit 1
fi

# 2) Build python-yarbo wheel
if [[ ! -d "$PYTHON_YARBO_DIR" ]]; then
  echo "2) python-yarbo not found at $PYTHON_YARBO_DIR — skip wheel build."
  echo "   To install the library from PyPI instead, ensure python-yarbo>=2026.3.60 is installed in HA's environment."
  exit 0
fi

echo "2) Building python-yarbo wheel ..."
WHEEL_DIR="$REPO_ROOT/dist_wheels"
mkdir -p "$WHEEL_DIR"
pip install -q build 2>/dev/null || true
(cd "$PYTHON_YARBO_DIR" && python3 -m build -o "$WHEEL_DIR" -w 2>/dev/null) || {
  (cd "$PYTHON_YARBO_DIR" && pip wheel -w "$WHEEL_DIR" .)
}
WHEEL=$(ls -t "$WHEEL_DIR"/python_yarbo-*.whl 2>/dev/null | head -1)
if [[ -n "$WHEEL" && -f "$WHEEL" ]]; then
  echo "   Built: $WHEEL"
  echo ""
  echo "--- Install python-yarbo into Home Assistant's environment ---"
  echo "Run this where Home Assistant's Python/pip is available (e.g. HA venv, or Terminal & SSH add-on):"
  echo ""
  echo "  pip install --force-reinstall \"$WHEEL\""
  echo ""
  echo "If HA runs in a container, copy the wheel into the container and run the same command there."
else
  echo "   WARNING: No wheel produced; install python-yarbo manually (e.g. pip install -e $PYTHON_YARBO_DIR)."
fi

echo ""
echo "--- Next steps ---"
echo "1. Restart Home Assistant."
echo "2. Verify: Settings → Devices & Services → Yarbo → Diagnostics — check integration_version and (if available) that telemetry is updating."
echo "3. See docs/testing-before-release.md for verification with script-driven and HASS-only polling."
