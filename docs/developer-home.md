# Manual developer-mode home app — historical 0.1 trial

For the current 0.2.2 app and packaging instructions, use the
[Panorama guide](panorama.md). This page retains the original manual-only trial;
the optional [system integration](system-integration.md) is now available separately.
Use an existing root connection on a rooted TV; do not reinstall Developer Mode.

This branch adds a standalone launcher inspired by NaveenDA's original clock, starfield and app/input rows. It opens manually like any other web app. It does not replace the system launcher, intercept Home, start at boot, mask advertising components, or require root. The original project, history, MIT license and author credits are retained.

## Build and install

Prerequisites: Python 3, Node.js, npm, and an existing developer-mode TV connection. webOS CLI 3.2.6 was used for this trial. Follow the [LG CLI guide](https://webostv.developer.lge.com/develop/tools/cli-dev-guide) for CLI usage. For a Developer Mode installation, that mode must remain valid; expiry can remove developer apps. A later rooted migration is documented separately in the [administrator-access record](administrator-access.md); after such migration use a root connection rather than the old prisoner alias.

From this repository:

```sh
npm install
cp developer_home/config.example.json developer_home/config.local.json
# Edit config.local.json: titles, real app IDs and optional input shortcuts.
npm run build -- --config developer_home/config.local.json
```

`*.local.json`, `*.local.js`, `dist/`, credentials and node_modules are ignored by Git. The packager stages only the named launcher files plus a generated config.js, not the repository or SSH configuration. The resulting IPK DOES contain your selected application names and IDs: inspect it before sharing it. Do not publish your local configuration or package by default.

Reuse the configured device name; there is no discovery, pairing, root or key extraction step here:

```sh
npx ares-setup-device --list
# Replace EXISTING_DEVICE_NAME below with the configured alias.
npx ares-install --device EXISTING_DEVICE_NAME dist/com.bnhr.customhome_0.1.0_all.ipk
npx ares-launch --device EXISTING_DEVICE_NAME com.bnhr.customhome
npx ares-launch --device EXISTING_DEVICE_NAME --running
```

The CLI profile must match the existing connection. If Dev Manager exported it under the `ose` profile, select that profile with `npx ares-config --profile ose` rather than recreating the connection. This changes local CLI profile selection only. Standard TV development setups normally use the `tv` profile.

Open **Mon accueil** from the regular LG app list for everyday use. The package ID is `com.bnhr.customhome`; it does not collide with the author's `com.naveen.customhome`. Its appinfo title can be changed before building; the screen title and date locale are configured independently.

## Configuration and actual IDs

`developer_home/config.example.json` is a generic example, not an inventory of your TV. All shortcut names and IDs are configurable. Confirm an ID and title instead of guessing from a brand:

```sh
npx ares-install --device EXISTING_DEVICE_NAME --listfull
```

This developer endpoint may omit system/store apps. The unrestricted `listApps` method is denied on the tested firmware; a failure must not be interpreted as an empty inventory. The manual app checks each configured shortcut using `getAppLoadStatus`. A confirmed missing app is disabled; a denied or failed query is recorded and leaves the launch attempt available, with errors shown if launch fails.

`discoverInputs: true` asks `com.webos.service.eim/getAllInputStatus` for actual HDMI app IDs and labels. It does not invent console names or assume a port count. This internal API may be unavailable on other firmware. If denied, the HDMI row is hidden unless explicit inputs were configured. A manual fallback looks like this, with an ID verified on your own device:

```json
{
  "discoverInputs": false,
  "inputs": [{ "id": "YOUR_VERIFIED_INPUT_APP_ID", "name": "Your input label" }]
}
```

Input existence alone is insufficient: virtual HDMI app IDs can exist for ports the hardware does not have. Use the input inventory. `connected` is not proof of an active video signal.

## Controls and diagnostics

- Left/right changes the selected tile and scrolls it into view. Up/down switches between application and HDMI rows. Missing apps are skipped.
- OK opens the selected app/input through `com.webos.applicationManager/launch`. A pointer click works too.
- Return (webOS keycode 461) exits this app, using the platform back function if available or window.close. The app handles its own navigation only. The physical Home button retains LG behavior.
- Focus restoration is attempted on visibility/relaunch events. A fresh process may start at the first tile.
- Request objects are retained until response, failure or an 8-second timeout. Launch errors appear in the footer. If an app is suspended immediately after a launch, its callback may not be observable.
- No external image, font or analytics service is used. The sky is drawn locally.

For accessible JavaScript errors:

```sh
npx ares-inspect --device EXISTING_DEVICE_NAME com.bnhr.customhome
```

The inspector console has `[customhome]` events and `window.homeDiagnostics`, a bounded in-memory log. Do not publish raw inspector logs or input inventories without reviewing them for private labels/identifiers. Successful installation, an accepted launch request, and a visually working target are different checks.

## Remove only this app

If the optional [system integration](system-integration.md) is installed, disable/remove those mechanisms first with their controller. That removal keeps this app and root/SSH intact; the commands below then remove only the app.

```sh
npx ares-launch --device EXISTING_DEVICE_NAME --close com.bnhr.customhome
npx ares-install --device EXISTING_DEVICE_NAME --remove com.bnhr.customhome
```

Or, with the CLI on PATH:

```sh
PATH="$PWD/node_modules/.bin:$PATH" sh scripts/uninstall.sh EXISTING_DEVICE_NAME
```

The script hardcodes only this package ID and takes the existing device alias as an argument. It has not been executed during the installation trial, so the app remains available for visual testing. Removing it does not change the stock launcher or Homebrew. Generated PC files can be discarded separately.

## Local checks

```sh
npx playwright install chromium
npm test
```

Set CHROMIUM_PATH to use an already installed Chromium binary. These tests mock Luna responses: they cover navigation, a missing app, one OK launch, Back, denied input discovery and visible launch errors. They do not certify the physical remote, TV video playback or HDMI picture/audio.

See [the exact test record](webos25-test-record.md) before drawing firmware compatibility conclusions. Legacy root watchers and ad scripts remain upstream material, outside this developer-mode trial.
