# Panorama 0.2.2 — visuals, Home routing and navigation

Tested 2026-10-27 on LG 43UR78006LK, firmware 33.31.75, webOS 25 /
SDK 10.3.2, aarch64 kernel, 32-bit Python userspace, 1920×1080 app surface.
This is a single-device result, not certification for other models or firmware.
Root/SSH were prerequisites and remain separate. The implementation is native
HTML/CSS/JavaScript, retaining the Panorama B composition and application ID.

## Changes and preserved state

- Native SAM Home routing with a passive, bounded exception for Home begun on LG.
  See [management and method](system-integration.md). The old passive mode remains.
- Cached app-row geometry, invalidated on render/resize; scrolling only as needed
  to expose the full selected tile; constant-width focus borders and no tile
  background-color transition. No forced app retention or continuous render loop.
- Four previously typographic visuals finalized in the private configuration;
  [provenance and redistribution boundaries](panorama-assets.md) are recorded.
  Existing accepted service logos were retained, not replaced with TV package icons.
- Background, dimming, order and hidden-shortcut preferences compared with backup
  and preserved. The version-1 localStorage key is unchanged. Selection naturally
  changes during navigation trials. Installed apps were not removed.

## Home measurement

Times start at physical **Home release**, captured on the TV, not at first visible
pixels. Holds were approximately 168–175 ms. Baseline: six trials. Native: three
corrected trials. A first native collection suffered two observers writing the
same file; it is excluded. No figures were reconstructed from corrupt data.

| Marker, seconds: minimum / median / maximum | Before | Native |
| --- | --- | --- |
| Panorama declared foreground | 1.674 / 1.773 / 2.322 | 1.256 / 1.366 / 2.074 |
| Two browser rendering opportunities | 1.927 / 2.026 / 2.544 | 1.536 / 1.614 / 2.289 |

The old observer detected release within roughly 1–4 ms; LG was declared foreground
121–214 ms after release. No LG foreground event preceded Panorama in the native
sample, and the owner confirmed **no visible LG Home on Home from YouTube**.
API acceptance, foreground, DOM readiness and double requestAnimationFrame are
not proof of the final usable display. App-ready instrumentation was not consistent
enough across both samples for a separate comparison. No optical latency was measured.

All measured returns from YouTube required a real load: webOS reported Panorama
closed with `memoryReclaim`, even after earlier opening. There is no demonstrated
retained-instance warm result, nor proof that total TV RAM was exhausted. The native
LG-origin exception was added after this timed sample and verified separately;
it does not alter the primary video-to-Home route.

## Navigation measurement

Three series each of 14 synthetic DOM arrows at 350 ms intervals, then three at
100 ms for repeat input, on the actual TV webview. This is normal-cadence simulation,
not physical key latency or the older every-frame stress test.

| Median across series | 0.2.0 | Optimized UI |
| --- | --- | --- |
| TaskDuration, normal cadence | 0.460 s | 0.172 s |
| TaskDuration, repeat cadence | 0.297 s | 0.187 s |
| Median next-frame delay, repeat series | 32.9 ms | 7.8 ms |

Normal-series TaskDuration ranged 0.442–0.549 s before, 0.171–0.193 s after;
repeat series 0.287–0.302 s before, 0.179–0.201 s after. The layout counter remained
around 28 per series, so it was not halved. These results concern the combined
change, not isolated attribution to each optimization. Sampled JS heap was about
0.67–0.79 MB before and 0.68–0.79 MB after: not renderer/TV total RAM, a GC-controlled
leak test, whole-TV CPU consumption or a 60-fps guarantee. Long-session performance
remains unmeasured. The clock and CSS animations pause in the background.

## Checks and owner confirmations

- Local mock preview: 12 checks, 1080p and scaled 720p captures actually inspected;
  final selected tile visible, settings, preferences, order/hiding/reset, pointer,
  loading, missing/refused app, duplicate-launch prevention and Return.
- Automated checks: 16 integration tests, 4 route tests, 3 preference tests.
- Owner: new visuals, navigation, held arrows and pointer satisfactory; repeated
  Home stable, Return reaches LG, long Home retains native zoom.
- Home from LG initially failed; fixed with the passive LG-origin exception.
  Owner then confirmed Home works. Double Return while on LG opens LG's recents;
  that native behavior is preserved.
- Stopped integration: owner confirmed Home leaves LG displayed. Restart/reconnect
  during YouTube did not change the declared foreground app.
- Standby/wake: Suspend → Active and one wake launch; owner sees LG, loading, then
  Panorama. This transition has not been eliminated.
- True reboot: SSH interrupted, uptime reset (42.52 s at check), old temporary
  sentinel absent, UID 0, native Home mapping retained, one boot launch and target
  foreground. Actual webview capture inspected. No additional owner confirmation
  of that last reboot's visible transition was requested before the pause.
- Final state: one daemon, one passive input descriptor, one power subscription,
  one native lifecycle subscription; no temporary observers or Fedora dependency.
  Official Homebrew startup, existing SSH hook and project hook unchanged.
- No new HDMI trials; no edits to video apps, firmware, ads or update settings.

## File backup and rollback

Before updating, privately preserve the installed app files/assets/config, recovery
IPK, exported preferences, integration code/config and current default-app mapping.
This is a file backup, not a system image. Keep credentials, branded assets, raw
logs and personal images out of Git. The generic installer stages explicit files;
`--update` stops the old daemon and archives its code/config, leaving it stopped.
Keep a separately named backup before subsequent updates overwrite that archive.

For an older app without the Home category, use this order through existing root SSH:

1. Run the **current** controller's `stop`: it restores the prior SAM Home mapping.
2. Install your saved app IPK using `scripts/deploy-launcher.py` and your private
   SSH config. The script verifies app ID, transfer checksum and installed status.
3. Restore saved `engine.py`, `control.py`, `config.json` in the project directory.
   Remove only the added `home_route.py` if absent in the saved version.
4. Start the restored controller without `--boot`, preserving root/SSH hooks.

A phase-specific private restoration wrapper was prepared and validated offline
against the actual backup. Full downgrade was **not executed**. Compatible current
preferences are retained, not replaced blindly by old exports. To restore ordinary
LG behavior without downgrading, use `home off` (and `power off` independently).
`stop` alone retains feature goals for a future start/boot. `remove` restores routing
and removes only the project integration, keeping apps and root/SSH.
