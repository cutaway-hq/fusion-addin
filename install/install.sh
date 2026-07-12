#!/usr/bin/env bash
# Cutaway — macOS install script.
# Copies the add-in to Fusion's per-user AddIns folder so Fusion will pick it
# up the next time Scripts and Add-Ins is opened.

set -euo pipefail

TARGET="$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/Cutaway"
SOURCE="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$TARGET"

cp "$SOURCE/Cutaway.py"       "$TARGET/"
cp "$SOURCE/Cutaway.manifest" "$TARGET/"
cp "$SOURCE/version.json"     "$TARGET/"
rm -rf "$TARGET/src"
cp -R "$SOURCE/src"           "$TARGET/src"
rm -rf "$TARGET/resources"
cp -R "$SOURCE/resources"     "$TARGET/resources"

cat <<MSG

Cutaway installed to:
  $TARGET

Next steps:
  1. Open Fusion 360 (or restart if it was running).
  2. Open: UTILITIES tab → Add-Ins → Scripts and Add-Ins → Add-Ins tab.
  3. Find "Cutaway" in the My Add-Ins list and click Run.
  4. Tick "Run on Startup" so it launches automatically next time.

MSG
