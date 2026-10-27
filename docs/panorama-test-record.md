# Panorama 0.2.0 — test record, 2026-10-27

Device: LG 43UR78006LK, firmware 33.31.75, webOS 25 / SDK 10.3.2,
aarch64 kernel. Application: `com.bnhr.customhome`, 1920×1080, default trust tier.
This is a UI update, not another root or system-integration procedure.

## Technically checked

- Previous installed files, configuration and resources saved privately; recovery
  IPK 0.1.0 rebuilt and validated offline for application ID and SHA-256. Browser
  storage export also saved. This is a file backup, not a full system backup.
- Normal appInstallService update reports `state: installed`; normal launch succeeds.
  Version 0.2.0 and twelve configured apps are visible in the running page.
  Eight entertainment shortcuts remain on the home row, four tools in Settings.
- TV capture examined directly at 1920×1080. No missing image or recorded JavaScript
  exception. The initial installed-package icons were rejected by the user, then
  replaced by the four monochrome service icons from approved proposal B. Other
  entertainment shortcuts use that proposal's text treatment. Private icons and
  captures are not redistributed in Git.
- TV preference persistence verified by closing and reopening the application:
  Twitch moved before YouTube, Netflix shortcut hidden, Dunes background and 20%
  extra darkening retained. These test changes were then restored to default order,
  all shortcuts visible, Horizon / 15%. This did not uninstall Netflix or any app.
- YouTube AdFree was opened through the new UI; foreground API confirmed its real
  application ID. An instrumented visibility event recorded `hidden: true` and
  `clockRunning: false`. The launcher was then reopened; its foreground clock resumed.
  The temporary measurement listener and storage key were removed.
- Four protected system files compare byte-for-byte with the pre-update backup:
  official startup.sh, administrator SSH hook, project integration hook and its
  config. Integration process PID and independent Home/power controls remained active.
  No root, SSH or power mechanism was edited. No reboot or HDMI launch was added.

## Performance measurement and limits

A five-second idle foreground sample via Chromium Performance domain reports
0.007135 seconds TaskDuration, 0.000319 seconds ScriptDuration and 952,464 bytes
JSHeapUsedSize (about 0.91 MiB). These are renderer diagnostics, **not total TV CPU,
GPU, native renderer memory or whole-system RAM**. A short sample does not prove
absence of long-term leaks.

A deliberately aggressive sequence dispatching one arrow at each animation frame
(56 frames) averaged 85.38 ms between frames, maximum 133.3 ms. An earlier sample
before focus/paint isolation changes averaged 91.19 ms, maximum 166.6 ms. These
single samples are not a controlled benchmark or proof of an improvement ratio.
An idle rAF sample averaged about 16 ms. Rapid navigation therefore still has a
render cost; this is not certified 60 fps scrolling. Physical navigation comfort
is pending user confirmation. No unnecessary continuous render loop runs normally.

## Local browser checks

Playwright 1.64.1 / Chromium 148, mocked webOS APIs, no TV transport and a local
server with `connect-src 'none'`. Captures at 1920×1080 and 1280×720 were opened
and examined: home/focus, fully visible last tile, settings, organisation bottom,
loading, missing app and refusal. Navigation by arrows/OK/Return, pointer clicks,
background/darkening persistence, ordering/hiding/reset and duplicate-launch guard
pass. No JavaScript exception in the local suite. Three Node preference tests pass
for unavailable/corrupt storage, absent/new shortcut ordering and validation.

## User confirmation versus pending checks

Confirmed: B — Panorama selected as visual reference; service logos requested in
place of installed package icons, keeping AdFree in application titles.

The user then completed the short physical test and replied: “Tout fonctionne et
c’est lisible”. This confirms readability from the bed, remote navigation to the
last app, opening YouTube or Twitch and returning with Home, changing background /
darkening, and hiding/showing a shortcut. It does not separately confirm pointer
comfort or playback inside every service. Earlier YouTube/Twitch tests remain
historical results; the new request allowed either application.

Pending: long-session performance, pointer use on the physical remote, a fresh
reboot/wake cycle and execution of the recovery IPK. Those system events were not
retested in this UI-only phase. Home's possible LG flash/latency is unchanged and
explicitly deferred to a separate phase. No new HDMI test was performed.
