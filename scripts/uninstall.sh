#!/bin/sh
# Remove only the manual launcher; never remove Homebrew or another app.
set -eu
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 EXISTING_DEVICE_NAME" >&2
  exit 2
fi
exec ares-install --device "$1" --remove com.bnhr.customhome
