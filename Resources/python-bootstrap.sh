#!/bin/sh
# Cold-start bootstrap: macOS system tools only; never invokes system Python.
set -eu
root=$1
resources=$2
manifest="$resources/python-installer.json"
value() { /usr/bin/plutil -extract "platforms.macos-arm64.$1" raw -o - "$manifest"; }
url=$(value url); digest=$(value sha256); size=$(value size); directory=$(value directory)
case "$directory" in cpython-3.11.*-aarch64-apple-darwin) ;; *) exit 2;; esac
[ "$(/usr/bin/uname -m)" = arm64 ] || { echo 'Apple Silicon is required.' >&2; exit 2; }
mkdir -p "$root/python" "$root/downloads"
base="$root/python/$directory"
lock="$root/python/.bootstrap-lock"
locked=0
for attempt in $(/usr/bin/jot 120); do
    if mkdir "$lock" 2>/dev/null; then echo $$ > "$lock/pid"; locked=1; break; fi
    owner=$(cat "$lock/pid" 2>/dev/null || echo '')
    if [ -n "$owner" ] && ! kill -0 "$owner" 2>/dev/null; then rm -f "$lock/pid"; rmdir "$lock" 2>/dev/null || true; fi
    sleep 1
done
[ "$locked" = 1 ] || { echo 'Another Python setup is still running.' >&2; exit 1; }
stage=''
cleanup() { [ -z "$stage" ] || rm -rf "$stage"; rm -f "$lock/pid"; rmdir "$lock" 2>/dev/null || true; }
trap cleanup EXIT HUP INT TERM
probe() { env -u PYTHONHOME -u PYTHONPATH -u __PYVENV_LAUNCHER__ "$1/bin/python3" -I -c 'import ssl,json,venv,platform,sys;assert sys.version_info[:2]==(3,11) and platform.machine()=="arm64"'; }
if [ -f "$base/.anicanto-python-verified" ] && [ "$(cat "$base/.anicanto-python-verified")" = "$digest" ] && probe "$base"; then exit 0; fi
archive="$root/downloads/$directory.tar.gz"
valid() { [ -f "$1" ] && [ "$(/usr/bin/stat -f %z "$1")" = "$size" ] && [ "$(/usr/bin/shasum -a 256 "$1" | /usr/bin/cut -d ' ' -f 1)" = "$digest" ]; }
echo '{"stage":"Runtime","message":"Downloading / verifying private Python; existing downloads are reused."}'
if ! valid "$archive"; then
    partial="$archive.partial"
    if ! valid "$partial"; then
        if [ -f "$partial" ] && [ "$(/usr/bin/stat -f %z "$partial")" -ge "$size" ]; then rm -f "$partial"; fi
        /usr/bin/curl --fail --location --retry 3 --connect-timeout 30 --max-time 1800 --continue-at - --output "$partial" "$url"
    fi
    valid "$partial" || { rm -f "$partial"; echo 'Private Python checksum mismatch; rejected.' >&2; exit 1; }
    mv "$partial" "$archive"
fi
stage=$(/usr/bin/mktemp -d "$root/python/.staging-XXXXXXXX")
/usr/bin/tar -xzf "$archive" -C "$stage"
probe "$stage/python"
printf '%s' "$digest" > "$stage/python/.anicanto-python-verified"
# A working base is never replaced; repairs keep the old directory for recovery.
if [ -e "$base" ]; then mv "$base" "$base.rejected-$(date +%s)-$$"; fi
mv "$stage/python" "$base"
probe "$base"
echo '{"stage":"Runtime","message":"Private Python verified."}'
