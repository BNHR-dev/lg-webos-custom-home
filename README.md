> **BNHR Panorama launcher — branch `bnhr-webos25`**
>
> [Panorama 0.2.2: configuration, settings and UI rollback](docs/panorama.md).
> [Current Home/navigation measurements and rollback](docs/panorama-022-test-record.md).
> A standalone home app is available in [`developer_home/`](developer_home/).
> Start with the [installation/configuration/removal guide](docs/developer-home.md) and the
> [firmware-specific test record](docs/webos25-test-record.md).
> It does not require root or change Home, boot behavior or advertising components.
> The original project and instructions below are retained with credit to NaveenDA;
> their root-dependent launcher features are not validated on webOS 25 by this fork.
> Administrator access was verified separately: [root/SSH test record](docs/administrator-access.md).
> Optional system integration is documented in [Home, boot and wake](docs/system-integration.md),
> with independent controls and rollback. The legacy scripts below remain separate from this implementation.

# LG webOS Custom Home Screen

Replaces the stock LG webOS home screen with a custom HTML/CSS/JS launcher,
auto-triggered on the TV's own power-on and Home-button events. Built live
against a rooted LG TV (`UR78006LK`, webOS 9 / firmware `23.25.60`) in an
agentic Claude Code session - this repo is that session's output, cleaned up
for others to adapt.

It also disables 18 ad/tracking packages (sponsored home-screen banners,
ACR viewing-habit tracking, third-party ad partner tiles, retail demo
bloatware) without deleting anything, fully reversible.


<img width="1501" height="938" alt="file-51768aad5a2f5b57f4580095c218136b" src="https://github.com/user-attachments/assets/2af07711-4fd0-47ff-8f31-f3a10afdad72" />


## How it works

1. **Root the TV.** This repo doesn't root anything itself - use
   [SlopBro](https://github.com/throwaway96/slopbro) or whichever exploit
   matches your model/firmware (check
   [CanIRootMyTV](https://canirootmy.tv/) first). Rooting installs
   [Homebrew Channel](https://www.webosbrew.org/), which is the thing that
   actually gives you telnet/SSH and a place to run scripts at boot.

2. **Disable the ad/tracking apps** ([`ads/`](ads/)) by bind-mounting an
   empty directory over each one. The underlying signed, read-only partition
   is never written to - undo is one script, no reboot needed.

3. **Build a custom home page** ([`custom_home/index.html`](custom_home/index.html)).
   It's a plain webOS web app: a clock, a row of app tiles, a row of HDMI
   input tiles. Tiles launch other apps via the `PalmServiceBridge` /
   `luna://com.webos.applicationManager/launch` call every webOS web app can
   make. **You will need to change the app IDs, icons, and HDMI mapping to
   match your own installed apps and inputs** - see
   [Finding your own app IDs](#finding-your-own-app-ids) below.

4. **Install it as a real (dev-mode) app**, not just files dropped on disk -
   webOS's app manager doesn't pick up new manifests from a bare directory
   the way it does for a proper install. See
   [Installing the launcher app](#installing-the-launcher-app).

5. **Wire up the triggers** ([`watchers/`](watchers/), persisted via
   [`init.d/`](init.d/)):
   - `homekey_watcher.py` reads raw input events straight from the remote's
     kernel input device (`/dev/input/eventN`) and launches the custom home
     app when it sees the Home key go down. It never grabs the device
     exclusively, so the TV's own normal Home-button handling (which still
     shows the *real* system home) is completely unaffected - this app just
     races it and wins a moment later. Expect a brief flash of the stock
     home screen first; a clean instant replace would need exclusively
     grabbing the input device and manually re-forwarding every other key,
     which is a real risk (a crashed daemon could leave the remote dead) and
     wasn't worth it for this.
   - `powerstate_watcher.py` subscribes to webOS's own
     `luna://com.webos.service.tvpower/power/getPowerState` and launches the
     app whenever the TV transitions from standby into `Active` - this is
     what makes it come up automatically when you turn the TV on with the
     remote (most webOS TVs suspend rather than reboot on power-off, so a
     boot-time hook alone won't catch this).

## Finding your own app IDs

Every app on a webOS TV has an ID like `netflix`, `youtube.leanback.v4`,
`amazon`, `now.tv`. Some match what you'd guess, some don't. Pull the real
list from the TV itself:

```sh
luna-send -n 1 -f luna://com.webos.applicationManager/listApps '{}' > apps_listing.json
```

Then grep for the app's visible title (`"title": "Netflix"`) and read the
`"id"` field a few lines above/below it, or just read the matching app's own
`appinfo.json` under `/usr/palm/applications/<id>/` or
`/media/cryptofs/apps/usr/palm/applications/<id>/` (DRM/partner apps like
Netflix often live on a separate `cryptofs` mount, not the usual path).

## Finding your remote's Home-key code

`homekey_watcher.py` is hardcoded to `code=773` on `/dev/input/event1`
because that's what *this* remote ("LGE RCU") sends on *this* TV. Yours will
likely differ. To find your own:

```sh
# on the TV, as root:
cat /proc/bus/input/devices   # find the remote's device, note its eventN
cat /dev/input/eventN > /tmp/cap.bin &   # start a passive, non-grabbing capture
# press Home a couple of times on the physical remote, then:
kill %1
```

Each input event is a 16-byte struct (`<IIHHi`: sec, usec, type, code,
value on a 32-bit system - adjust if yours differs). Decode it in Python:

```python
import struct
data = open("/tmp/cap.bin", "rb").read()
for i in range(0, len(data), 16):
    sec, usec, typ, code, val = struct.unpack("<IIHHi", data[i:i+16])
    print(typ, code, val)
```

Look for `type=1` (key event) entries with a consistent `code` appearing once
per press (`value=1` on press, `value=0` on release). That's your Home code.

## Installing the launcher app

Just copying `index.html`/`appinfo.json` into
`/media/developer/apps/usr/palm/applications/<your-app-id>/` isn't enough -
webOS's app manager won't register it. Package and install it properly:

```sh
# on the TV, as root, with your app's files already at $APPDIR:
mkdir -p /tmp/ipkbuild/control
cat > /tmp/ipkbuild/control/control << 'EOF'
Package: your.app.id
Version: 1.0.0
Section: misc
Priority: optional
Architecture: all
OS: webos
Maintainer: you
Description: Custom home launcher
EOF
tar czf /tmp/ipkbuild/control.tar.gz -C /tmp/ipkbuild/control .
tar czf /tmp/ipkbuild/data.tar.gz -C /media/developer/apps ./usr/palm/applications/your.app.id
echo "2.0" > /tmp/ipkbuild/debian-binary

# BusyBox's `ar` can only extract, not create archives - build the ipk by hand:
python3 - << 'EOF'
import time
def ar_member(name, data):
    hdr = (name.ljust(16) + str(int(time.time())).ljust(12) +
           "0".ljust(6) + "0".ljust(6) + "100644".ljust(8) +
           str(len(data)).ljust(10) + "\x60\x0a")
    out = hdr.encode("ascii") + data
    if len(data) % 2: out += b"\n"
    return out
members = ["debian-binary", "control.tar.gz", "data.tar.gz"]
with open("/tmp/ipkbuild/app.ipk", "wb") as f:
    f.write(b"!<arch>\n")
    for m in members:
        f.write(ar_member(m, open(f"/tmp/ipkbuild/{m}", "rb").read()))
EOF

restart appinstalld
sleep 3
luna-send -n 20 -f luna://com.webos.appInstallService/dev/install \
  '{"id":"com.ares.defaultName","ipkUrl":"/tmp/ipkbuild/app.ipk","subscribe":true}'
```

Watch the subscribed response stream for `"state": "installed"`.

**Trust level matters.** Don't use `"trustLevel": "trusted"` in your
`appinfo.json` for a third-party app - that tier appears reserved for
LG-signed first-party apps and got silently rejected by the app manager
(`"Unsupported Application Type"`) in testing. Use `"trustLevel": "default"`,
same as other sideloaded apps like Jellyfin.

## Transferring large files over telnet

If you're pushing files over telnet (no `scp`/`sftp` on a bare rooted TV),
a heredoc (`cat > file << EOF`) works for small files but can **silently
truncate** large ones - this embedded shell/tty stack appears to choke on
very long individual lines (minified SVG paths, for instance), not on total
size or transfer speed. Fix: base64-encode first (wraps every line to a
fixed, short width), transfer *that*, then decode on-device:

```sh
# on your machine:
base64 -b 76 -i index.html -o index.html.b64   # -b wraps lines; macOS base64 needs it explicitly

# send index.html.b64 over telnet as a heredoc, then on the TV:
base64 -d index.html.b64 > index.html
```

Always verify with `wc -c` on both ends afterward - don't assume it worked.

## Updating an already-running web app

`luna://com.webos.applicationManager/launch` on an app that's already
running just resurfaces the existing (stale) instance - it does not reload
the page. Close it first:

```sh
luna-send -n 1 -f luna://com.webos.applicationManager/closeByAppId '{"id":"your.app.id"}'
luna-send -n 1 -f luna://com.webos.applicationManager/launch '{"id":"your.app.id"}'
```

Both watchers in this repo already do this.

## Disclaimer

Rooting voids your warranty and carries real risk (a bad firmware update
after rooting, an interrupted flash, etc. could require a factory reset or
worse). Everything here was built to be reversible where possible (ads:
one script undo; custom home: unmount + remove the init.d script + reboot
restores the stock native home), but you're modifying your own TV's
software at your own risk. This is not affiliated with LG, Homebrew
Channel, or any of the exploit authors linked above.
