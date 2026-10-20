#!/bin/bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/anicanto-icons.XXXXXX")"
trap 'rm -rf "$temp_dir"' EXIT

magick -background none "$root/Resources/app-icon.svg" -depth 8 "PNG32:$temp_dir/icon.png"
size="$(sips -g pixelWidth -g pixelHeight "$temp_dir/icon.png")"
[[ "$size" == *"pixelWidth: 1024"* && "$size" == *"pixelHeight: 1024"* ]] || {
  echo "App icon must render at 1024 × 1024 pixels" >&2
  exit 1
}
[[ "$(magick identify -format '%z/%[channels]' "$temp_dir/icon.png")" == 8/srgba* ]] || {
  echo "App icon must be 8-bit RGBA for the desktop host" >&2
  exit 1
}

cp "$temp_dir/icon.png" "$root/Resources/app-icon-art.png"
cp "$temp_dir/icon.png" "$root/Resources/AniCanto-icon.png"
cp "$temp_dir/icon.png" "$root/studio/src-tauri/icons/icon.png"

swift "$root/scripts/app-icon.swift" "$temp_dir/AniCanto.iconset" "$temp_dir/icon.png"
iconutil --convert icns --output "$root/Resources/AniCanto.icns" "$temp_dir/AniCanto.iconset"
magick "$temp_dir/icon.png" -define icon:auto-resize=256,128,64,48,32,24,16 "$root/studio/src-tauri/icons/icon.ico"

echo "Updated macOS, Windows and shared UI icons from Resources/app-icon.svg"
