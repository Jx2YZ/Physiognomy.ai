#!/usr/bin/env bash
# Builds the standalone Physiognomy.ai macOS app into dist/Physiognomy.app.
# Run this ON A MAC:  bash packaging/build_macos.sh
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo"

# Use the repo venv if present, else fall back to python3 on PATH.
if [ -x "$repo/venv/bin/python" ]; then
  py="$repo/venv/bin/python"
else
  py="python3"
fi

"$py" -m PyInstaller Physiognomy-macos.spec --noconfirm

# Stage the user-editable/user-visible files next to the .app. main.py looks
# for them relative to the executable's parent dir when frozen.
out="$repo/dist"
cp "$repo/config.yaml" "$out/"
rm -rf "$out/assets"
cp -R "$repo/assets" "$out/assets"
mkdir -p "$out/models"
cp "$repo/models/"*.task "$out/models/"
cp "$repo/packaging/README-macos.txt" "$out/README.txt"

echo ""
echo "Build complete: $out/Physiognomy.app"
echo "Ship the whole dist/ folder (the .app plus config.yaml, assets/, models/)."
