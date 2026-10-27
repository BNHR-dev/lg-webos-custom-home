# Developer-mode trial — 2026-10-27

This record describes the original manual-launcher trial. A later [administrator-access phase](administrator-access.md) verified root/SSH persistence and preserved this launcher unchanged; it did not validate Home replacement or automatic launcher startup.

For the later optional integration, see the separate [Home/boot/wake record](system-integration.md).

Hardware/firmware scope: one LG **43UR78006LK**, firmware **33.31.75**. The TV UI version was reported by the owner as **webOS 25**; `com.webos.service.tv.systemproperty/getSystemInfo` independently returned the model, firmware and **SDK 10.3.2**. Do not generalize this trial to all webOS 25 TVs.

Host: Fedora KDE, webOS CLI 3.2.6; application `com.bnhr.customhome` version 0.1.0, `trustLevel: default`. Existing developer SSH session UID 6672 (`prisoner`); no root procedure. Homebrew's `checkRoot` returned false and Updater's `status` returned a nonzero UID. No elevated service was used.

## Observed results

| Check | Result and scope |
| --- | --- |
| Package | Built on Fedora with ares-package; installation returned Success. |
| Registration/start | ares-launch returned Launched; dev/running included this app; its own inspector DOM reached readyState complete. |
| Installed shortcuts | Developer inventory returned seven real IDs/titles. Local trial includes all seven; the public example contains only two generic community app examples. |
| YouTube AdFree | Manifest/inventory confirms `youtube.leanback.v4` 0.5.3. Triggering its tile from the actual launcher was followed by YouTube in dev/running. The owner subsequently confirmed that opening YouTube AdFree from the launcher works and the application functions correctly. Separate picture/audio quality checks were not itemized. |
| Twitch AdFree | Manifest/inventory confirms `twitch.adamffdev.v1` 1.6.6. Triggering its actual tile was followed by Twitch in dev/running. The owner subsequently confirmed that opening Twitch AdFree from the launcher works and the application functions correctly. Separate stream/audio quality checks were not itemized. |
| Shortcut availability | getAppLoadStatus returned true/exist true in the app's own context for all configured shortcuts. |
| HDMI discovery | getAllInputStatus succeeded from the app context and returned three hardware entries with app IDs `com.webos.app.hdmi1`, `com.webos.app.hdmi2`, `com.webos.app.hdmi3`. All three tiles rendered. |
| HDMI launch | A tile-triggered HDMI 1 request was observed in the launcher's inspector; its response was not captured after context loss/suspension. A separate launch call over the existing non-root public Luna connection returned returnValue true for HDMI 1. The owner subsequently confirmed that the HDMI 1 shortcut switches to the expected input screen. No source device was connected, so picture/audio with an active source were not tested. HDMI 2 and HDMI 3 launch actions remain unverified. |
| TV rendering | Capture of the actual launcher inspected locally: clock/date, seven app shortcuts in a horizontal row, three inputs, readable footer and visible focus. No TV screenshot or raw inventory is published. |
| TV navigation code | Six synthetic ArrowRight events inside the real app selected the final shortcut and scrolled it fully into the viewport. No JavaScript error in the accessible in-memory log at inspection. The owner subsequently confirmed successful opening of both media apps during the requested remote-control trial; all navigation paths have not been exhaustively checked. |
| Local browser tests | Two tests passed with mocked Luna: navigation, disabled missing app, one OK launch, Back, denied HDMI discovery, launch error display, bridge cleanup and footer layout. |
| Return key | The owner pressed Return from Mon accueil and confirmed arrival at the LG system home. |
| Uninstall | Exact-package removal command/script prepared; not executed because the app is retained for testing. |

## API limits and correction to the preliminary diagnosis

The initial SSH diagnostic closed stdin immediately. `luna-send-pub` then exited without reporting responses. Keeping stdin open fixes these queries; exit status 0 alone was never evidence of a successful service call.

Verified accessible: developer `dev/listApps`, `getAppLoadStatus`, systemproperty/getSystemInfo, eim/getAllInputStatus and the tested launch requests. The unqualified listApps and getForegroundAppInfo calls are denied from the developer shell. The guessed service `com.webos.service.tv.externaldevice` does not exist here; the app uses the verified eim endpoint instead.

Root-only `luna-send` remains unavailable. Kernel raw-input format and Python watcher execution are irrelevant to this manual app and have not been validated.

## Owner feedback and remaining physical validation

On 2026-10-27, after the requested visual/remote-control trial, the owner confirmed that YouTube AdFree and Twitch AdFree both opened and functioned correctly. This is owner-reported validation, in addition to the earlier API/inspector observations. The owner also confirmed expected HDMI 1 switching with no source connected, and Return from Mon accueil leading to the LG system home. HDMI 2/3, HDMI picture/audio with an active source and exhaustive navigation remain unconfirmed. No separate playback-duration, audio-quality or login-state test was reported.

The stock launcher, physical Home handling, power-on behavior and ad components were left unchanged. This branch makes **no compatibility claim for replacing Home, automatic startup, the legacy watchers, root persistence or ad masking on webOS 25**.

## Credits and reproducibility

This is a real fork of NaveenDA/lg-webos-custom-home, preserving its history and MIT license. New work lives in developer_home/, scripts/, tests/ and docs/ on branch bnhr-webos25. The original custom_home/, watchers/, init.d/ and ads/ remain unchanged.

The private trial configuration is ignored by Git. Public code uses configurable app IDs and runtime input discovery; no target IP, SSH key, passphrase, Dev Manager export, serial number or raw service/inspector log is part of this record.
