#!/bin/sh
# Reverses disable_ads.sh - unmounts the overlay from every target, restoring
# the original (never-deleted) app files immediately. No reboot required.

TARGETS="
adoverlay adoverlayex adhdmi1 adhdmi2 adhdmi3 adhdmi4
acrcomponent acroverlay acrhdmi1 acrhdmi2 acrhdmi3 acrhdmi4
dangbei-card dangbei-overlay livepick livepick-full
store-demo sync-demo
"

for t in $TARGETS; do
  path="/usr/palm/applications/com.webos.app.$t"
  while mountpoint -q "$path" 2>/dev/null; do
    umount "$path"
  done
done
