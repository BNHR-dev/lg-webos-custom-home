"""Reversible SAM Home routing. No key capture, system file edits or launch loops."""
import pathlib
import json

GET_SETTINGS = 'luna://com.webos.settingsservice/getSystemSettings'
SET_SETTINGS = 'luna://com.webos.settingsservice/setSystemSettings'
SET_HOME = 'luna://com.webos.applicationManager/setDefaultApp'


def mapping(bus):
    reply = bus(GET_SETTINGS, {'category':'general','keys':['defaultApps']})
    value = reply.get('settings', {}).get('defaultApps')
    if not reply.get('returnValue') or not isinstance(value, dict):
        raise RuntimeError('Cannot read original Home routing; no change made')
    return value


def remember(config, bus):
    if 'home_original' not in config:
        value = mapping(bus)
        config['home_original'] = {'present':'home' in value, 'app_id':value.get('home')}


def registered(config, bus):
    reply = bus('luna://com.webos.applicationManager/getAppInfo', {'id':config['app_id']})
    info = reply.get('appInfo', {})
    if not reply.get('returnValue') or info.get('id') != config['app_id'] or 'home' not in (info.get('appCategory') or []):
        raise RuntimeError('Install and verify appCategory [home] before enabling native Home')


def installed(config):
    try:
        path = pathlib.Path('/media/developer/apps/usr/palm/applications') / config['app_id'] / 'appinfo.json'
        info = json.loads(path.read_text())
        return info.get('id') == config['app_id'] and 'home' in (info.get('appCategory') or [])
    except (OSError, ValueError, TypeError):
        return False


def activate(config, bus):
    registered(config, bus)  # SAM must recognise the category, not just a file on disk.
    if 'home_original' not in config:
        raise RuntimeError('Save original Home routing before activation')
    reply = bus(SET_HOME, {'category':'home','appId':config['app_id']})
    if not reply.get('returnValue'):
        restore(config, bus)
        raise RuntimeError('Native Home rejected; original routing restored')
    if mapping(bus).get('home') != config['app_id']:
        restore(config, bus)
        raise RuntimeError('Native Home routing was not confirmed')


def restore(config, bus):
    original = config.get('home_original')
    if not original:
        return
    value = mapping(bus)
    current = value.get('home')
    expected = original.get('app_id') if original.get('present') else None
    if current == expected and ('home' in value) == original.get('present'):
        return
    if current not in [config['app_id'], config['stock_home']]:
        return  # Preserve a third-party/user routing change made independently.
    if original.get('present'):
        reply = bus(SET_HOME, {'category':'home','appId':expected})
    else:
        value.pop('home', None)  # Preserve all other current default-app categories.
        reply = bus(SET_SETTINGS, {'category':'general','settings':{'defaultApps':value}})
    if not reply.get('returnValue'):
        raise RuntimeError('Original Home routing could not be restored; inspect SSH diagnostics')
