# Integration idle-work pass — 2026-10-28

Test target remains LG 43UR78006LK, firmware 33.31.75, webOS 25 / SDK 10.3.2.
The application stays Panorama 0.2.2. Only integration `engine.py` was replaced;
no app package, private preferences, Home mapping goal, power hook or root/SSH
startup was changed. This is not another Home latency or memory-retention trial.

## Change

Previously each event-loop iteration read/parsed config.json and atomically rewrote
status.json even when nothing had changed. The loop remains at its existing cadence
(maximum selector wait 150 ms, reduced to a pending Home deadline when necessary).

- Compare config inode, nanosecond mtime and size; re-read after replacement/change.
  The controller writes configuration atomically, so same-size changes are detected.
- Publish status only when its observable contents change, including counters,
  child IDs, input devices, feature flags and power state. An unchanged file's mtime
  is no longer a heartbeat: use the controller's live PID check for liveness.
- Temporary lease expiry is still checked every iteration, independent of file changes.
- Input handling, native Home routing, bounded jobs and power transitions are unchanged.
  A restart without `--boot` observes power state without launching an app.

No forced retention, swap tuning, OOM priority, LG service shutdown, hidden
keepalive launch or exclusive input capture is introduced. Both status and its
replacement file are under `/tmp`; reducing these writes is not a flash-wear claim.

## Verification

19 integration tests and 4 Home-routing tests pass. New cases cover config cache
invalidation after atomic replacement, status publication on meaningful changes,
and temporary expiry with cached config. Existing short/long Home, duplicate
suppression, no-focus restart/reconnect, boot deduplication and bounded wake tests
remain passing.

On the TV: backup saved first; old engine matched its recorded SHA-256; staged
engine compiled before replacement. Stop current controller, atomically replace
only engine.py, then start without `--boot`. The original SAM route was restored
by stop and the configured native route reapplied by start. Before/after foreground
was YouTube; no app launch or TV reboot was requested. Saved config, controller,
Home-routing module, official Homebrew startup and project boot hook hashes were
unchanged. Final state: one daemon, one power subscription, one native lifecycle
subscription; native route still points to Panorama. No temporary observer remains.

Read-only `/proc` samples, three intervals of approximately 3 seconds each, before
and after, of only our daemon/subscriptions:

| Daemon metric per interval | Before | After |
| --- | --- | --- |
| CPU, percent of one core | 0.67 / 1.00 / 1.00 | 0.33 / 0.33 / 0.00 |
| Write syscalls (syscw delta) | 19 / 20 / 20 | 0 / 0 / 0 |
| Characters written (wchar delta) | 6137 / 6460 / 6460 | 0 / 0 / 0 |

Subscriptions had zero measured CPU ticks and writes in those short windows.
This is a low-resolution, short idle observation, not whole-TV consumption or a
long-session benchmark. During events the status file is written normally. Memory
was not retuned. No new physical Home, boot or wake series was run: scheduling and
launch logic were not changed. Those earlier user confirmations remain historical.
No additional app launch speedup or optical latency improvement is demonstrated.

## Backup and rollback

Privately save the exact installed engine and its SHA-256 before replacement, plus
configuration/protected-file hashes to check scope. Restore with the current project
controller: stop; replace only engine.py with the verified saved copy; start **without
`--boot`**. Keep current configuration, app files/preferences and root/SSH hooks.
The stop/start briefly restores/reapplies the SAM route, so avoid a physical Home
press during it. The local phase-specific restore wrapper was hash-verified offline,
not actually executed. No full system recovery image is claimed.

## RAM and future startup work

Existing video-to-Home trials required a reload after `memoryReclaim`; a retained
warm instance has not been demonstrated. Reusing an instance can avoid a cold load
if webOS retains it. The [LG lifecycle documentation](https://webostv.developer.lge.com/develop/guides/app-lifecycle-management)
explains relaunch of an already-running app, but that is not a retention guarantee.
[requiredMemory](https://webostv.developer.lge.com/develop/references/appinfo-json)
is a declared minimum requirement, not an allocation or a promise to keep an app
resident. No manifest flag or system memory policy was changed here. A future
startup pass should distinguish process creation, document/assets, first rendering
opportunities and user-visible readiness before considering retention-policy changes.
