# System integration: native or passive Home, boot and wake

The launcher and integration are separate. Root access is a prerequisite; see
[administrator access](administrator-access.md). No firmware, advertising, update,
compositor key-filter or root/SSH startup file is changed. Native mode changes the
SAM default Home category reversibly; passive mode leaves that mapping unchanged.
The Home-routing test record is [Panorama 0.2.2](panorama-022-test-record.md).
A later [idle-work pass](integration-idle-pass.md) reduces redundant config/status
work without changing launch timing or the app version.

## Method and boundaries

**Native mode**, tested with app 0.2.2, requires SAM to recognize the manifest
`appCategory: ["home"]`. The controller saves the original `general/defaultApps.home`
setting before calling `applicationManager/setDefaultApp`. Home from a video app
then routes directly to Panorama. A positive API reply is verified by reading the
mapping back. Stop, Home off and removal restore the previous Home category,
including its original absence, preserving other current categories and an
independent third-party Home change. Do not delete the saved `home_original` data.

LG Home itself has a special close/retain path which can bypass the default category.
One passive input reader plus one lifecycle subscription qualifies only a short
Home press begun on LG. A bounded one-shot launch handles that case, suppressed
when native routing has already started Panorama. Returning to LG alone does not
redirect. An installed-manifest check every five seconds restores the previous
mapping and disables Home if the target disappears. This does not guarantee recovery
from every renderer failure or an ungracefully killed daemon: use the controller
through SSH to restore routing.

**Passive mode** is the original fallback: after a short Home release it waits
briefly for LG to become foreground, then launches the target. This leaves a visible
LG transition. Both modes use a read-only input descriptor, never an exclusive grab.
Device identity is resolved by name through sysfs and checked with EVIOCGNAME; no
event index is hardcoded. The input ABI must be measured, not inferred from the
kernel: the tested aarch64 TV has 32-bit Python and 16-byte native input events.

Holds at least 0.65 seconds and repeat events do not create a short-Home request.
Ordinary keys and long-Home behavior stay with LG. Requests coalesce; failures do
not create endless relaunches. An existing app instance can be reused if webOS
retains it; the integration does not force retention in memory. LG remains
installed and accessible with Return or the controller's `lg-home` command.

Native API research: [Galaxy Launcher](https://github.com/guntiss/webos-galaxy-launcher),
revision `6fda86a400ac45832a7dcc52d382fbfd53bbd6b5`. Its documented mechanism was
studied; no source code was copied. These private platform interfaces are verified
only on the firmware in the test record, not guaranteed across LG releases.

## Installation, initially disabled

The host needs Python 3 and an already configured administrator SSH alias. The TV needs its existing Python 3, root Luna access and Homebrew boot hooks. There is no PC HTTP server or ongoing host connection in the final design.

Run the passive probe on the TV while pressing only the requested keys, and review the format, timestamps, device identity and code. Do not copy the measured profile below blindly. The standalone probe source is system_integration/probe.py; it does not activate integration.

```sh
python3 scripts/install-integration.py --ssh-config YOUR_PRIVATE_SSH_CONFIG --host YOUR_ADMIN_ALIAS \
  --input-name YOUR_MEASURED_DEVICE_NAME --key-code YOUR_MEASURED_HOME_CODE
```

Installation stages only the four project Python files (engine, controller, probe and Home routing). It initializes home=false and power=false, starts no daemon and creates no boot hook. For a code update, --update first stops the project daemon and archives the previous project code/config under its own directory; it preserves options and leaves the daemon stopped. Start it explicitly after review.

Before activation, copy the existing launcher, root/SSH startup and any previous integration files to a private recovery location. These are file backups, not a system/firmware image. Keep all credentials and raw observations outside Git.

## Management and rollback

On the TV, use Python 3 and the fixed project controller:

```sh
python3 /var/lib/bnhr-customhome-integration/control.py status
# Choose only after the app category is installed and recognized:
python3 /var/lib/bnhr-customhome-integration/control.py mode native
# Or select the original fallback: control.py mode passive
python3 /var/lib/bnhr-customhome-integration/control.py home on --temporary 900
python3 /var/lib/bnhr-customhome-integration/control.py home off
python3 /var/lib/bnhr-customhome-integration/control.py power on
python3 /var/lib/bnhr-customhome-integration/control.py power off
python3 /var/lib/bnhr-customhome-integration/control.py lg-home
python3 /var/lib/bnhr-customhome-integration/control.py stop
python3 /var/lib/bnhr-customhome-integration/control.py start
```

Run these through your existing administrator SSH connection. home and power are independent flags. The temporary Home lease expires after 900 seconds; test home off and ordinary LG Home before making anything persistent.

Only after physical Home validation:

```sh
python3 /var/lib/bnhr-customhome-integration/control.py persist on
# To remove only the automatic daemon start:
python3 /var/lib/bnhr-customhome-integration/control.py persist off
# To remove all and only this integration, keeping the launcher and root/SSH:
python3 /var/lib/bnhr-customhome-integration/control.py remove
```

Persist on clears the temporary lease and writes only this project's Homebrew hook. It does not independently enable either feature. Stop restores the original Home mapping but leaves feature flags unchanged, so a later start or boot reactivates configured Home. Use home off to retain LG across future boots. Remove stops this process, removes this hook and deletes only the two fixed project directories. It never uninstalls an app or removes webosbrew, its official startup script, or the separate administrator SSH hook.

Files/processes owned by this phase:

| Item | Purpose |
| --- | --- |
| /var/lib/bnhr-customhome-integration | Code and feature flags |
| /tmp/bnhr-customhome-integration | Exclusive lock, PID, handled-boot marker, status, bounded logs |
| /var/lib/webosbrew/init.d/40-bnhr-customhome-integration | Optional boot hook |
| One controller run process | Input and power event handling |
| At most one persistent luna-send power subscription | Present only while power integration is enabled |
| At most one native lifecycle subscription | Present only with native Home enabled |

One-shot Luna queries have deadlines. A file lock prevents duplicate daemons. Stop terminates owned children; it never uses a global pkill. Logs rotate at 64 KiB and repeated errors are rate-limited. They stay local and may reveal installed app IDs; do not publish them unreviewed.

## Boot, wake and session reconnections

Boot is requested only by the Homebrew boot hook and deduplicated with a per-boot marker in /tmp. On this TV boot_id can remain constant and btime can shift across suspend, so neither value is used alone as a boot identity. The boot hook requests at most one opening for that boot, during a bounded startup window. A controlled reboot is verified separately using reset uptime, cleared temporary sentinel and fresh process state together with the boot-time observation. The handled marker prevents a restarted daemon/hook from creating a second boot launch. Enabling power midway through a session records the current boot as handled and does not open the app immediately.

Wake requires an observed transition from standby/suspend to Active. An initial Active snapshot, reconnect with the same Active state and Screen Saver dismissal do not count as wakes. Boot/wake launch retries are bounded; a changed foreground app during delayed retries cancels the pending request. Overlapping triggers coalesce and an already foreground target is not relaunched.

The daemon does not repeatedly enforce a preferred foreground app. Restarting it during an Active session starts by observing a baseline; it does not pull focus back to the launcher. No extra HDMI behavior is added.

## Historical passive-mode test record

These observations predate 0.2.2. References below to unchanged app files/default
Home settings describe that earlier phase only. See the current record linked above.

Target: LG 43UR78006LK, firmware 33.31.75, SDK 10.3.2, webOS 25. The existing manual app and administrator access were previously validated.

- Measured: LGE RCU, event0 at observation time; Home773; Python3.10.13, native @llHHi size16, pointer32bits, aligned events and valid timestamps. Short0.169s, long3.162s. These are observations, not global defaults.
- Owner baseline: short Home opens LG; long Home activates zoom, with the up arrow also tried.
- Installer verification: features initially off, no hook; temporary Home enabled then disabled and process stopped; no daemon remains after stop.
- Local tests cover short/long/repeat filtering, fragmented/multiline JSON, Active baseline/reconnect/screensaver, pending Home cancellation, one launch, failed-launch termination, bounded wake retries, user navigation cancellation and overlapping-trigger coalescing.
- Owner temporary Home trial: short Home from YouTube opens Mon accueil after a brief LG screen and loading indicator; repeated separated presses repeat this visible transition. Return reaches LG and long Home still activates the native zoom, including from Mon accueil.
- Runtime evidence: two closely spaced Home releases were coalesced to one launch; no autonomous redirect followed without another short press. A failed/blocked foreground condition ended its bounded request rather than redirecting another application.
- Owner rollback trial, before persistence: with Home disabled, a short press from YouTube leaves LG Home displayed without redirecting back.
- After this confirmation, the project hook was enrolled and Home/power enabled independently. No launcher files or root/SSH startup files changed.
- A warm daemon restart while YouTube was foreground did not change focus. Its power subscription was then deliberately terminated once and reconnected; YouTube remained foreground. The single expected subscription-close diagnostic is not a recurring spontaneous failure.
- Owner confirms automatic opening after the Power cycle, with LG/loading/custom-home transition. The same daemon and subscription observed Suspend → Active; one wake launch occurred about 1.5 seconds after Active. btime shifted during suspend, so the boot marker was changed to tmpfs without changing wake behavior.
- Controlled true reboot: the pre-reboot temporary sentinel disappeared, uptime reset and fresh daemon/PIDs appeared. The boot hook started the integration about 42.6 seconds after kernel boot; exactly one launch request was accepted at about 43.2 seconds. The combined SSH/foreground check completed at about 141 seconds and showed the custom home in foreground. The exact first visible frame was not timed; do not confuse the launch request time with a guaranteed display time.
- Root SSH returned as UID0; the server still advertised only publickey and rejected an unauthenticated attempt. Homebrew root=true, telnetDisabled=true, failsafe=false, sshdEnabled=true and blockUpdates=false; no Telnet listener observed.
- After boot, there is exactly one integration daemon, one power subscription and no temporary lifecycle probe. The boot event log contains one startup, one boot request and one launch, with no spontaneous error loop.
- Independent disable checks: power off terminates its subscription while Home remains active; home off closes input descriptors while power remains active. Both were restored on at the end.
- All seven application files, the official Homebrew startup and the existing SSH hook remain byte-identical to the baseline. The only added startup hook is 40-bnhr-customhome-integration. The native default-app setting and all 153 retained app IDs are unchanged.
- The native Screen Saver is allowed to appear during inactivity and is not repeatedly dismissed by this integration.
- Owner visual feedback after the true boot: no loading indicator in that final trial, but a few LG Home frames remain visible before Mon accueil. This is not a zero-frame replacement; loading may differ across trials.
