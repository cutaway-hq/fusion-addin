#!/usr/bin/env bash
# Cutaway — macOS uninstall script.

set -euo pipefail

TARGET="$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/Cutaway"

if [ ! -d "$TARGET" ]; then
  echo "Cutaway not found at:"
  echo "  $TARGET"
  echo "Nothing to remove."
  exit 0
fi

rm -rf "$TARGET"
echo "Cutaway removed from:"
echo "  $TARGET"
echo "Restart Fusion if it was running."
