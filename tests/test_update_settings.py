"""Exercise the real Setup CLI with a small, isolated synthetic game/payload."""
from pathlib import Path
import hashlib
import json
import os
import re
import struct
import subprocess
import time
import uuid
import zipfile

D = Path(__file__).resolve().parents[1]
OUT = D / 'tests' / ('update_settings_' + time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6])
OUT.mkdir()
CSC = Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
MOD = 'Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/'
core_source = (D / 'src/PackCore.cs').read_text()
brand = re.search(r'const string Brand="([^"]+)"', core_source).group(1)
release_build = int(re.search(r'const long ReleaseBuild\s*=\s*(\d+)', core_source).group(1))
release_version = brand.rsplit('_', 1)[1]
checks = []


def check(name, passed):
    checks.append(dict(name=name, passed=bool(passed)))
    if not passed:
        raise AssertionError(name)


def put(root, relative, content):
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def fake(name):
    root = OUT / 'fixtures' / name
    exe = bytearray(1024)
    for offset, fmt, value in [(0, '<H', 0x5A4D), (0x3C, '<I', 128),
                               (128, '<I', 0x4550), (132, '<H', 0x8664),
                               (136, '<I', 0x6AA0E27D), (208, '<I', 0x2195A000)]:
        struct.pack_into(fmt, exe, offset, value)
    put(root, 'Game/Binaries/Win64/AceCombat8.exe', exe)
    put(root, 'start_protected_game.exe', exe)
    put(root, 'EasyAntiCheat/Settings.json', b'{"executable":"Game/Binaries/Win64/AceCombat8.exe"}')
    return root


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def read_state(root):
    return json.loads((root / 'KoreanAIR_AC8_ModPack/installed.json').read_text())


files = {
    brand + '.exe': (b'synthetic launcher payload', 'common', False),
    'Game/Binaries/Win64/dinput8.dll': (b'campaign loader', 'campaign', False),
    'Game/Content/Paks/pakchunk0-Windows_999_P.pak': (b'campaign pak', 'campaign', False),
    'Game/Binaries/Win64/dwmapi.dll': (b'runtime loader', 'runtime', False),
    'Game/Binaries/Win64/UE4SS/UE4SS-settings.ini': (b'[General]\r\nFixture=1\r\n', 'runtime', True),
    MOD + 'config.ini': (b'[control]\r\nsensitivity=0.03\r\n', 'runtime', True),
    MOD + 'display.ini': (b'[display]\r\nfov=100\r\n', 'runtime', True),
    MOD + 'subtitle.ini': (b'[subtitles]\r\nposition=native\r\n', 'runtime', True),
    MOD + 'Scripts/main.lua': (b'-- fixture only', 'runtime', False),
}
manifest = dict(brand=brand, files=[dict(path=p, source='payload/' + p, hash=hashlib.sha256(v).hexdigest(),
                            group=g, mutable=m) for p, (v, g, m) in files.items()], legacy={})
payload = OUT / 'Payload.zip'
with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('manifest.json', json.dumps(manifest))
    for path, (content, _, _) in files.items():
        z.writestr('payload/' + path, content)

sources = [D / 'src' / name for name in ('PackCore.cs', 'Ui.cs', 'Setup.cs')]
# Setup shares updater protocol code; the Launcher UI partial is excluded.
if (D / 'src/UpdateCore.cs').exists():
    sources.append(D / 'src/UpdateCore.cs')
refs = ['System.Windows.Forms.dll', 'System.Drawing.dll', 'System.Web.Extensions.dll',
        'System.IO.Compression.dll', 'System.IO.Compression.FileSystem.dll', 'System.Net.Http.dll']
setup = OUT / 'SetupFixture.exe'
subprocess.run([str(CSC), '/nologo', '/target:winexe', '/platform:x64', '/main:Setup',
                '/out:' + str(setup), *['/reference:' + r for r in refs],
                '/resource:' + str(payload) + ',Payload.zip', *map(str, sources)], check=True)
update_audit = OUT / 'UpdateSettingsAudit.exe'
subprocess.run([str(CSC), '/nologo', '/target:exe', '/platform:x64', '/main:UpdateSettingsAudit',
                '/out:' + str(update_audit), *['/reference:' + r for r in refs],
                '/resource:' + str(payload) + ',Payload.zip', *map(str, sources),
                str(D / 'tests/UpdateSettingsAudit.cs')], check=True)


def run_install(root, flags, success=True):
    result = subprocess.run([str(setup), '--install', str(root), *map(str, flags)],
                            creationflags=subprocess.CREATE_NO_WINDOW)
    check('install_exit_' + root.name, (result.returncode == 0) == success)


preference = Path(os.environ['LOCALAPPDATA']) / 'KoreanAIR_AC8_ModPack/language.txt'
language_before = preference.read_bytes() if preference.exists() else None
root = fake('upgrade')
mods_path = 'Game/Binaries/Win64/UE4SS/Mods/mods.txt'
put(root, mods_path, b'; keep original comment\r\nOtherMod : 0\r\n')
flags = (1, 0, 1)
run_install(root, flags)
user_settings = {
    MOD + 'config.ini': ('; custom 조종\r\n[control]\r\nsensitivity=0.046\r\n'
                         '[keys]\r\nfree_look=F8\r\n[hud]\r\ncolor=#aabbcc\r\n').encode('utf-16'),
    MOD + 'display.ini': b'; custom\n[display]\nenabled=0\nspan=1\nfov=121\ndistance=3210\nheight=703\n',
    MOD + 'subtitle.ini': b'[subtitles]\r\nposition=bottom\r\n; saved preference\r\n',
    'Game/Binaries/Win64/UE4SS/UE4SS-settings.ini': b'[General]\r\nFixture=99\r\nCustom=keep\r\n',
    'Game/Binaries/Win64/UnrelatedMod/settings.ini': b'[unrelated]\nvalue=keep\n',
}
for path, value in user_settings.items():
    put(root, path, value)
put(root, MOD + 'pack.ini', b'[modules]\r\nmouseFlight=0\r\ndisplay=1\r\nsubtitles=1\r\n'
    b'[diagnostics]\r\nenabled=1\r\n[custom]\r\nfixture=keep\r\n')
put(root, mods_path, b'; keep original comment\r\nOtherMod : 0\r\nAC8MouseAim : 1\r\nLaterMod : 1\r\n')

# Simulate a recorded prior visible version without depending on old production binaries.
record = read_state(root)
old_launcher = 'KoreanAIR_AC8_ModPack_1.0.exe'
(root / (brand + '.exe')).rename(root / old_launcher)
for item in record['files']:
    if item['path'] == brand + '.exe':
        item['path'] = old_launcher
    if item['path'] == MOD + 'pack.ini':
        item['mutable'] = False  # Prior installer versions recorded this as immutable.
record['version'] = '1.0'
state_path = root / 'KoreanAIR_AC8_ModPack/installed.json'
state_path.write_text(json.dumps(record))
selected = tuple(int(record[key]) for key in ('campaign', 'mouse', 'display'))
run_install(root, selected)
after = read_state(root)
check('selected_modules_preserved', tuple(int(after[k]) for k in ('campaign', 'mouse', 'display')) == flags)
check('user_ini_bytes_preserved', all((root / p).read_bytes() == v for p, v in user_settings.items()))
pack_after = (root / (MOD + 'pack.ini')).read_text()
check('pack_non_module_settings_preserved', '[diagnostics]\nenabled=1' in pack_after
      and '[custom]\nfixture=keep' in pack_after)
mod_lines = (root / mods_path).read_text().splitlines()
check('other_mod_rows_preserved', all(line in mod_lines for line in
                                    ('; keep original comment', 'OtherMod : 0', 'LaterMod : 1')))
check('old_owned_launcher_removed', not (root / old_launcher).exists() and (root / (brand + '.exe')).exists())
check('copied_setup_updated', (root / 'KoreanAIR_AC8_ModPack/Setup.exe').read_bytes() == setup.read_bytes())

# Manual installs deliberately refuse a suspended pack before mutating any files.
for path in ('Game/Binaries/Win64/dinput8.dll', 'Game/Binaries/Win64/dwmapi.dll',
             'Game/Content/Paks/pakchunk0-Windows_999_P.pak'):
    parked = root / 'KoreanAIR_AC8_ModPack/Disabled' / path
    parked.parent.mkdir(parents=True, exist_ok=True)
    (root / path).rename(parked)
after['suspended'] = True
after['version'] = '1.0'
after['build'] = 0
state_path.write_text(json.dumps(after))
before_refusal = snapshot(root)
run_install(root, flags, success=False)
check('suspended_manual_update_preserves_every_file', snapshot(root) == before_refusal)

result = subprocess.run([str(update_audit), str(root), str(setup), 'valid'],
                        creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True, text=True, errors='replace')
check('automatic_update_success', result.returncode == 0)
updated = read_state(root)
check('automatic_update_records_release_version_and_build', updated['version'] == release_version
      and updated['build'] == release_build)
check('automatic_update_preserves_suspended_mode', updated['suspended'])
check('automatic_update_preserves_selected_modules',
      tuple(int(updated[k]) for k in ('campaign', 'mouse', 'display')) == flags)
check('automatic_update_preserves_user_ini_bytes', all((root / p).read_bytes() == v
                                                     for p, v in user_settings.items()))
check('automatic_update_preserves_pack_settings', (root / (MOD + 'pack.ini')).read_text() == pack_after)
parkable = ('Game/Binaries/Win64/dinput8.dll', 'Game/Binaries/Win64/dwmapi.dll',
            'Game/Content/Paks/pakchunk0-Windows_999_P.pak')
check('automatic_update_keeps_loaders_parked', all(not (root / p).exists() and
      (root / 'KoreanAIR_AC8_ModPack/Disabled' / p).exists() for p in parkable))
check('automatic_update_hash_inventory_valid', all(hashlib.sha256(
      (root / ('KoreanAIR_AC8_ModPack/Disabled/' + item['path']
       if item['path'] in parkable else item['path'])).read_bytes()).hexdigest() == item['hash']
      for item in updated['files'] if not item['mutable']))
before_failed_update = snapshot(root)
result = subprocess.run([str(update_audit), str(root), str(setup), 'invalid'],
                        creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True, text=True, errors='replace')
check('automatic_update_invalid_payload_refused', result.returncode != 0)
check('failed_automatic_update_restores_suspended_installation', snapshot(root) == before_failed_update)
language_after = preference.read_bytes() if preference.exists() else None
check('language_preference_untouched', language_before == language_after)

report = dict(passed=all(c['passed'] for c in checks), checks=checks,
              tested_source_sha256={p.relative_to(D).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in sources + [D / 'tests/UpdateSettingsAudit.cs']})
(OUT / 'results.json').write_text(json.dumps(report, indent=2))
print(json.dumps(dict(passed=report['passed'], checks=len(checks), report=str(OUT / 'results.json'))))
