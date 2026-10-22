# Persistence via Homebrew Channel's init.d

Once [Homebrew Channel](https://www.webosbrew.org/) is installed (via a root
exploit like [SlopBro](https://github.com/throwaway96/slopbro)), it runs any
executable script dropped in `/var/lib/webosbrew/init.d/` on every boot,
before the rest of the system finishes starting. That's the hook that makes
everything in this repo survive a reboot.

Drop these in as `/var/lib/webosbrew/init.d/<NN>-<name>.sh`, `chmod +x` them.
Numeric prefix controls run order; it didn't end up mattering much here, but
lower numbers run first.

- `10-disable-ads.sh` - runs [`ads/disable_ads.sh`](../ads/disable_ads.sh)
- `20-homekey-watcher.sh` - starts [`watchers/homekey_watcher.py`](../watchers/homekey_watcher.py) in the background
- `30-powerstate-watcher.sh` - starts [`watchers/powerstate_watcher.py`](../watchers/powerstate_watcher.py) in the background

Each one is a one-liner, for example:

```sh
#!/bin/sh
nohup python3 /media/developer/custom_home/homekey_watcher.py > /tmp/homekey_watcher.log 2>&1 &
```

(Copy the actual watcher `.py` files to `/media/developer/custom_home/` on
the TV first - `/var/lib/webosbrew` itself isn't a great place to keep
long-lived app files.)
