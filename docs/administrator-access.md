# Administrator access verification — separate from launcher integration

Test date: 2026-10-27. One LG **43UR78006LK**, firmware **33.31.75**, SDK **10.3.2**, marketed as webOS 25. Kernel architecture: aarch64. These observations do not certify other models or firmware.

This phase obtained and verified root access. It did not alter the launcher source, Home handling, automatic launch of the custom home, advertising apps or firmware. The manual launcher remains an ordinary app. Root infrastructure starting at boot is distinct from launching a home screen at boot.

## Sources reviewed and applicability

- [Official SlopBro at 21023d56ca424607bb03d2939609cc658c655fc7](https://github.com/throwaway96/slopbro/tree/21023d56ca424607bb03d2939609cc658c655fc7): README, PC launcher, page, JS service entry point and autoroot script reviewed; 16 upstream tests passed locally. This was the upstream HEAD checked for this phase.
- [Homebrew Channel 0.7.3 at 92fcf9fef7ce08dbeae3b0616df8d0c75c11f0b3](https://github.com/webosbrew/webos-homebrew-channel/tree/92fcf9fef7ce08dbeae3b0616df8d0c75c11f0b3): elevation code, service methods, startup and SSH behavior reviewed. Installed service.js, elevate-service, startup.sh and jumpstart.sh matched the official release bytes.
- [SlopBro issue 49](https://github.com/throwaway96/slopbro/issues/49): same firmware on another model, with success after fixing network routing. This was supporting evidence, not a model certification.
- [Issue 29](https://github.com/throwaway96/slopbro/issues/29): another report of success on firmware 33.31.75 using voiceweb.
- [Issue 61](https://github.com/throwaway96/slopbro/issues/61): illustrates why a success message alone is insufficient evidence of usable root.
- [Issue 14](https://github.com/throwaway96/slopbro/issues/14): unroot/cleanup feature request; no documented --unroot entry point was found in the reviewed revision.

Homebrew re-elevation requires existing administrator authority. The installed Updater's exec endpoint runs under its own UID and was not treated as an independent privilege escalation mechanism.

Preflight confirmed that voiceweb existed. The standard SlopBro candidate order selected it without pretending that the SDK was a different version. Python 3 and the existing developer connection were used. The TV-to-PC HTTP route was checked before the attempt. A temporary firewall allowance was limited to the TV and the required TCP port; the global firewall was never disabled.

## Developer Mode and preservation of applications

The official autoroot script converts devmode_enabled from a file into a directory, installs Homebrew 0.7.3 and elevates its Luna service. It checks LG's signed start-devmode.sh and warns that the LG Developer Mode app must be removed before reboot. Keeping that app would conflict with the documented procedure and could endanger developer apps.

The owner initially excluded application removal. Work stopped before the exploit to explain this conflict. The owner then explicitly authorized removal of **only LG Developer Mode**, after root and authenticated SSH had been verified. No exception was inferred for any other app.

Recovery copies were made first: all developer app files visible to prisoner, actual deployed launcher files and configuration, PC source and private configuration, a rebuilt launcher recovery IPK, the original connection, and integrity hashes. After root, a further private archive captured LG Developer Mode, its signed startup script/signature/verifier, preferences and accessible service definitions before removal.

These are file-level recovery copies, **not** a firmware dump, complete system image or guaranteed backup of every app's login/storage. The launcher recovery IPK was rebuilt from deployed files; it is not claimed to be the original byte-identical package.

## Intervention and evidence before reboot

One standard SlopBro execution was performed with the pinned filesystem assets. No --telnet or --curl-insecure option was used. The page ran through voiceweb, downloaded the expected four files, and the autoroot result was retained privately. No alternative exploit was tried.

The official HBC 0.7.3 package had been saved on the PC and checked against the release digest:

`sha256:d10bf3c753551d7c72fb7a92b20fcd2317e502a220ac668ba8e76f6ea78b363c`

Separate checks then established:

| Context | Evidence before reboot |
| --- | --- |
| Homebrew status | checkRoot returned true. |
| Homebrew execution | exec running id returned uid=0(root), gid=0(root). |
| Administrator SSH | Dedicated Ed25519 key authenticated as root; id returned uid=0(root). |

A dedicated public key was appended to authorized_keys, with directory mode 700 and file mode 600. Existing key content was not replaced. Telnet startup was disabled. Homebrew's unmodified startup and persistent activity were used for root infrastructure.

A small project-owned SSH hook under Homebrew init.d starts the bundled Dropbear with password authentication disabled (-s), a dedicated PID file, and a bounded local status log. It also handles the builtin listener when the Homebrew SSH switch is enabled: it checks the executable identity before replacing that listener, so there is a single key-only listener. The stock Homebrew startup file was not patched. No home-screen script was enrolled.

The owner enabled the Homebrew SSH switch during verification; it remains enabled. The hardening hook continues to enforce key-only SSH. The updater service was not used to obtain root.

## Removal and reboot checks

The first removal request through Homebrew's uninstall endpoint returned FAILED_REMOVE. Its implementation uses the developer-only dev/remove route, while LG Developer Mode was installed in the store partition. The failure was retained and the two API routes were inspected before changing the approach. The normal appInstallService/remove route then reported state removed, progress 100 for this exact package.

Full app inventories before and after removal showed **only com.palmdts.devmode removed**: 154 app IDs before, 153 after. The other IDs remained present after reboot.

The first reboot request through the platform API was accepted. The initial monitoring script incorrectly required a changed boot_id, even when SSH connected successfully. That value stayed constant on this TV; the monitor therefore gave a false failure result. Kernel boot time, uptime, startup marker and listener start time showed that the SSH daemon had started during boot, before later Homebrew UI interaction. Do not infer a particular snapshot mechanism solely from this behavior.

A second controlled reboot using the normal system reboot command was performed to remove this ambiguity. No exploit was rerun and Homebrew was not opened manually to recover access.

| Check after the second reboot | Observed result |
| --- | --- |
| Genuine reboot evidence | Kernel btime changed; uptime reset; a pre-reboot /tmp sentinel disappeared. |
| Automatic SSH availability | Returned in about 42 seconds. |
| SSH privilege | Dedicated-key session returned uid=0(root). |
| SSH authentication | Server advertised only publickey; a connection with public-key authentication disabled was rejected. |
| Listener | One Dropbear listener using -s; IPv4/IPv6 port 22. |
| Homebrew | checkRoot=true, configuration root=true, exec id returned UID 0. |
| Homebrew flags | telnetDisabled=true, sshdEnabled=true, failsafe=false, blockUpdates=false. |
| Telnet | No telnetd process or TCP port 23 listener observed. |
| Other applications | All 153 retained IDs present; LG Developer Mode absent. |
| Existing launcher | All seven deployed app files, including private config.js, byte-identical to the pre-root copy. |
| Launcher operation | Ordinary launch accepted; DOM complete, ten tiles, no pending request, JavaScript error or API failure observed. |

A comparison initially included a packageinfo.json from the sibling package directory. Restricting it to the actual application directory confirmed the seven application files were unchanged. No launcher correction or reinstall was required.

## Ongoing access and rollback limits

Use the administrator SSH connection with the dedicated key. The old prisoner/Developer Mode connection is no longer the management path after removing LG Developer Mode. Keep the private key, pinned host key and private connection configuration outside public Git. The host key was first recorded on the local network, not independently certified by an external authority.

HBC can now execute arbitrary commands as root. That capability is not a reason to run the legacy launcher watchers or ad scripts: those remain unvalidated for this firmware. Do not reinstall LG Developer Mode casually while the rooted developer marker and startup infrastructure are in place.

Rollback options are limited and distinct:

- To remove only the manual launcher, use its exact package ID with the authenticated root connection. The generic uninstall script requires a CLI device alias configured for that root connection; the old prisoner alias will not work after this migration.
- SSH hardening is project-owned and its hook is removable/revisable through an existing administrator session. Removing the active access mechanism before establishing an alternative would risk lockout; it does not itself unroot the TV.
- Restoring the stock Developer Mode workflow requires a coordinated restoration of the relevant marker, LG app and root startup/registration state. The saved files help recovery but do not provide a tested full unroot procedure. No factory reset or automatic cleanup was performed or authorized.
- Homebrew's stock failsafe behavior was not rewritten. A future failed startup must be diagnosed separately; the absence of Telnet is an observed result of this successful boot, not a claim about every future failure mode.

PC-side HTTP and inspector forwarding processes were stopped. The temporary firewall rule has an expiry and serves no running HTTP listener. No private logs, app inventory, key material, pairing token, connection address or recovery archive is part of this document.

## License boundary and scope stop

SlopBro is AGPL-3.0-or-later. Its source remains in a separate local checkout; no SlopBro code was copied into this MIT fork. This document links the exact reviewed revision and describes the observations. Homebrew's official package was downloaded for local use, not redistributed here.

This phase stops with administrator access and persistence verified. Home-button integration and automatic custom-home startup remain a separate, unimplemented phase.
