# Panorama launcher 0.2.0

Panorama is the native HTML/CSS/JavaScript interface in `developer_home/`.
It preserves the standalone application ID `com.bnhr.customhome`. Optional Home,
boot and wake integration is separate and unchanged by this update. A brief stock
LG Home screen may still appear with that integration. This update does not try
to suppress it. No advertising, update or firmware components are modified.

## Configure and package

Copy `developer_home/config.example.json` to an ignored `config.local.json`.
Use IDs obtained from your own installed-app inventory. Set `category: "tools"`
for technical applications; all other configured apps appear in the main row.
There is no fixed app count. The existing four known Homebrew/maintenance IDs
also default to tools when no category is specified. `discoverInputs: true` uses
`com.webos.service.eim/getAllInputStatus`; failed discovery keeps configured inputs.
A detected HDMI shortcut is not evidence that its launch permission was tested.

```sh
python3 scripts/build.py --config developer_home/config.local.json
```

The builder stages an explicit file list and generates `dist/app/config.js`.
It never packages the entire working directory. Supply `--packager /path/to/ares-package`
if the existing webOS CLI is outside PATH. Root is unnecessary for the app UI;
use your existing supported installation connection. Do not reinstall Developer
Mode on a rooted TV merely to install this app.

With an already configured administrator SSH alias, installation **or restoration**
of a saved previous package is:

```sh
python3 scripts/deploy-launcher.py /path/to/package.ipk \
  --ssh-config /path/to/private-sshconfig --host your-tv-alias
```

This closes, updates and launches only `com.bnhr.customhome`. It verifies the IPK
application ID and transferred SHA-256, and requires the `installed` service state.
The SSH key is used through your existing config, never embedded. Luna stdin stays
open until the command completes. No service restart or integration change is used.
Save the old installed app files, config, assets and a recovery IPK **before** updating.
A file backup is not a system recovery image. Restoration is prepared but a downgrade
of this UI was not executed during testing; app-install policy can differ across TVs.

## Remote and pointer

Left/right selects an application; down reaches inputs/settings, up returns to the
selected application. OK opens; Return closes a dialog, returns from shortcut
organisation to settings, then exits the launcher through the platform back action.
Pointer hover/focus and click use the same selection. The selected tile is scrolled
fully into view. Settings include the installed technical tools and a normal launch
of `com.webos.app.home`. The independent Home integration remains relevant when using
the physical Home key afterwards.

Launch feedback appears immediately. A load-status check detects missing applications;
launch refusal and an eight-second API timeout produce a readable retry/back view.
One opening is accepted at a time. Return dismisses feedback and ignores late callbacks;
it cannot retract an application launch already accepted by webOS.

## Persistent preferences and personal images

Settings choose a local background and 0–70% extra darkening. Shortcut organisation
moves items with the up/down controls and hides/shows them without uninstalling.
Apps and inputs remain separate rows; reordering stays inside each group. Reset
restores configured order and visibility, preserving the chosen background/darkening.
Technical tools remain reachable. Preferences use app-local `localStorage` key
`bnhr.customhome.preferences.v1`; inaccessible/full storage is reported. No cloud,
phone or PC connection is advertised. Existing configuration is preserved by building
with the same local file. The previous session selection is imported when available;
its old session key is not deleted. Subsequent selection is stored persistently.

For a personal image from Fedora, with no JavaScript changes:

1. Place a suitably sized local landscape image in an ignored `private-assets/` folder
   (for example a 1920×1080 JPEG called `bedroom.jpg`; avoid very large originals).
2. Add a background entry in private `config.local.json`:
   `{"id":"personal","name":"Mon image","src":"assets/private/bedroom.jpg"}`.
   Keep the default entries too if desired.
3. Build with `--private-assets-dir private-assets`, then update the same application.
   Select the new image in Settings. Never commit private assets or configuration.

Per-app optional `logo` points to a relative packaged `assets/...` file;
`logoContainsName: true` suppresses the repeated caption; optional
`logoMonochrome: true` applies the white treatment used in the approved design. Missing/failed icons use
an accessible typographic title. Image proportions are preserved with `object-fit: contain`.
No remote image URL is loaded. See [asset provenance](panorama-assets.md).

## Verification and limits

Tested installation: LG 43UR78006LK, webOS 25 / SDK 10.3.2, firmware 33.31.75,
aarch64 kernel, 1920×1080 application surface. Fedora preview: Playwright 1.64.1,
Chromium 148; TV engine generation 120. Local mock tests use no TV transport.
1920×1080 and scaled 1280×720 captures cover initial/last tile, scrolling,
settings, organisation, loading, missing app and refusal. Order, hiding, reset,
background/darkening persistence, pointer, keyboard and duplicate prevention pass.
Preference failure/corruption and newly installed shortcut ordering have Node tests:

```sh
node --test tests/preferences.test.cjs
```

TV-specific measurements and pending physical confirmation are recorded separately
in [the test record](panorama-test-record.md). These checks do not certify all LG models,
long-session stability, subscription playback, or visual comfort at every distance.
No new HDMI test or reboot is required for this UI-only update. Home latency is a
separate future task. There is no new background poller, video layer or continuous
render loop: only a 15-second foreground clock and bounded service calls. The clock
stops and CSS animations pause when the app is hidden.

To remove only the application, first disable the separate Home/power integration
if installed (see [system integration](system-integration.md)), then uninstall only
`com.bnhr.customhome` with your existing app manager. Do not remove root/SSH hooks or
other apps. To roll back just this UI, install the saved previous IPK instead.
