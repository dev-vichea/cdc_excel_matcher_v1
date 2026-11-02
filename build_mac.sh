#!/usr/bin/env bash
set -e

echo "=== Building CDC Excel Matcher for macOS ==="

# 1. Install desktop packaging dependencies if missing
python3 -m pip install -r requirements.txt pyinstaller pywebview

# 2. Run PyInstaller with desktop.spec
python3 -m PyInstaller desktop.spec --noconfirm

# 3. Create macOS DMG installer image
echo "=== Packaging DMG Image ==="
hdiutil create -volname "CDC_Excel_Matcher" -srcfolder "dist/CDC_Excel_Matcher.app" -ov -format UDZO "dist/CDC_Excel_Matcher_macOS.dmg"

echo "=== Build Complete! ==="
echo "App bundle: dist/CDC_Excel_Matcher.app"
echo "DMG disk image: dist/CDC_Excel_Matcher_macOS.dmg"
