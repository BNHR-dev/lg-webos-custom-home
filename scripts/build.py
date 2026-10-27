#!/usr/bin/env python3
"""Stage only the launcher and validated configuration; package on the PC."""
import argparse, json, pathlib, shutil, subprocess
root = pathlib.Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--config', type=pathlib.Path, default=root/'developer_home/config.example.json')
p.add_argument('--packager', default='ares-package')
p.add_argument('--private-assets-dir', type=pathlib.Path, help='Explicit local-only image folder; never included by a generic build')
a = p.parse_args()
config = json.loads(a.config.read_text())
assert isinstance(config.get('apps'), list), 'apps must be an array'
for item in config['apps'] + config.get('inputs', []):
    assert isinstance(item.get('id'), str) and item['id'], 'Each shortcut needs an id'
    assert isinstance(item.get('name'), str) and item['name'], 'Each shortcut needs a name'
stage = root/'dist/app'
if stage.exists():
    shutil.rmtree(stage)  # Generated output only; never package stale files.
stage.mkdir(parents=True, exist_ok=True)
for name in ['index.html', 'style.css', 'app.js', 'preferences.js', 'appinfo.json', 'icon.png', 'largeIcon.png']:
    shutil.copyfile(root/'developer_home'/name, stage/name)
shutil.copytree(root/'developer_home/assets', stage/'assets')
if a.private_assets_dir:
    target = stage/'assets/private'
    target.mkdir()
    for image in a.private_assets_dir.iterdir():
        if image.is_file() and not image.is_symlink() and image.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.svg']:
            shutil.copyfile(image, target/image.name)
(stage/'config.js').write_text('window.HOME_CONFIG = ' + json.dumps(config, ensure_ascii=True) + ';\n')
subprocess.run([a.packager, str(stage), '-o', str(root/'dist')], check=True)
