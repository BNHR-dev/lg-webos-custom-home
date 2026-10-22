#!/bin/sh
# Masks 18 ad/tracking/demo apps on a rooted LG webOS TV by bind-mounting an
# empty directory over each one. Nothing is deleted - the signed read-only
# partition is never touched, so this is instantly reversible with undo_ads.sh.
#
# Run as root (telnet/ssh after rooting). Safe to re-run; mountpoint checks
# prevent duplicate stacked mounts.

EMPTY_DIR=/media/developer/empty_overlay
mkdir -p "$EMPTY_DIR"

TARGETS="
adoverlay adoverlayex adhdmi1 adhdmi2 adhdmi3 adhdmi4
acrcomponent acroverlay acrhdmi1 acrhdmi2 acrhdmi3 acrhdmi4
dangbei-card dangbei-overlay livepick livepick-full
store-demo sync-demo
"

for t in $TARGETS; do
  path="/usr/palm/applications/com.webos.app.$t"
  if [ -d "$path" ] && ! mountpoint -q "$path" 2>/dev/null; then
    mount --bind "$EMPTY_DIR" "$path"
  fi
done
