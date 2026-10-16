"""Run the built updater handoff locally with synthetic game files only."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import time
import uuid

D = Path(__file__).resolve().parents[1]
OUT = D / 'tests' / ('update_handoff_' + time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6])
OUT.mkdir()
FIXTURES = Path(tempfile.gettempdir()) / ('ac8handoff_' + uuid.uuid4().hex[:8]) / 'tests/fixtures'
source = (D / 'src/PackCore.cs').read_text(encoding='utf-8-sig')
BRAND = re.search(r'const string Brand="([^"]+)"', source).group(1)
BUILD = int(re.search(r'const long ReleaseBuild\s*=\s*(\d+)', source).group(1))
VERSION = BRAND.rsplit('_', 1)[1]
MOD = 'Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/'
SETUP = OUT / 'ReleaseSetup.exe'
shutil.copy2(D / 'build' / (BRAND + '_Setup.exe'), SETUP)
shutil.copy2(D / 'build/Payload.zip', OUT / 'Payload.zip')
expected_launcher_hash = hashlib.sha256((D / 'build' / (BRAND + '.exe')).read_bytes()).hexdigest()
helper = OUT / 'UpdateHandoffProcess.exe'
subprocess.run(['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe', '/nologo',
                '/target:exe', '/platform:x64', '/reference:System.Web.Extensions.dll',
                '/out:' + str(helper), str(D / 'tests/UpdateHandoffProcess.cs')], check=True)
checks = []
case_reports = []
source_hashes = {str(p.relative_to(D)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (D / 'src').glob('*.cs')}
binary_hashes = dict(setup=hashlib.sha256(SETUP.read_bytes()).hexdigest(),
                     launcher=expected_launcher_hash, helper=hashlib.sha256(helper.read_bytes()).hexdigest())


def check(name, passed):
    checks.append(dict(name=name, passed=bool(passed)))
    if not passed:
        raise AssertionError(name)


def put(root, relative, content):
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def execute(*args, capture=True):
    result = subprocess.run(list(map(str, args)), creationflags=subprocess.CREATE_NO_WINDOW,
                            stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                            stderr=subprocess.PIPE if capture else subprocess.DEVNULL,
                            text=True, errors='replace')
    if result.returncode:
        raise AssertionError('Process failed: ' + str(args) + '\n' + (result.stdout or '') + (result.stderr or ''))
    return result


def state(root):
    return json.loads((root / 'KoreanAIR_AC8_ModPack/installed.json').read_text(encoding='utf-8-sig'))


preference = Path(os.environ['LOCALAPPDATA']) / 'KoreanAIR_AC8_ModPack/language.txt'
language_before = preference.read_bytes() if preference.exists() else None
for name, delay_ms, suspended, flags in [('immediate', 0, False, (1, 0, 1)),
                                       ('delayed_suspended', 750, True, (0, 1, 0))]:
    root = FIXTURES / name
    exe = bytearray(1024)
    for offset, fmt, value in [(0, '<H', 0x5A4D), (0x3C, '<I', 128), (128, '<I', 0x4550),
                               (132, '<H', 0x8664), (136, '<I', 0x6AA0E27D), (208, '<I', 0x2195A000)]:
        struct.pack_into(fmt, exe, offset, value)
    put(root, 'Game/Binaries/Win64/AceCombat8.exe', exe)
    put(root, 'start_protected_game.exe', exe)
    put(root, 'EasyAntiCheat/Settings.json', b'{"executable":"Game/Binaries/Win64/AceCombat8.exe","title":"fixture"}')
    put(root, 'Game/Binaries/Win64/UE4SS/Mods/mods.txt', b'OtherMod : 0\r\n; external comment\r\n')
    execute(SETUP, '--install', root, *flags)
    if suspended:
        execute(root / (BRAND + '.exe'), '--suspend')
    saved = {
        MOD + 'config.ini': ('; custom saved config\r\n[control]\r\nsensitivity=0.043\r\nlook_sensitivity=0.019\r\n'
                             '[keys]\r\nfree_look=F8\r\n[hud]\r\nfixture=keep\r\n').encode('utf-16'),
        MOD + 'display.ini': b'[display]\r\nenabled=1\r\nspan=0\r\nfov=119\r\ndistance=3300\r\nheight=701\r\n',
        MOD + 'subtitle.ini': b'[subtitles]\r\nposition=bottom\r\n',
        'Game/Binaries/Win64/UE4SS/UE4SS-settings.ini': b'[General]\r\nFixture=99\r\n',
        'Game/Binaries/Win64/UnrelatedMod/settings.ini': b'[fixture]\r\nkeep=yes\r\n',
    }
    for path, value in saved.items():
        put(root, path, value)
    put(root, MOD + 'pack.ini', b'[modules]\r\nmouseFlight=1\r\ndisplay=0\r\nsubtitles=1\r\n'
        b'[diagnostics]\r\nenabled=1\r\n[custom]\r\nfixture=keep\r\n')
    mods = root / 'Game/Binaries/Win64/UE4SS/Mods/mods.txt'
    mods.write_bytes(mods.read_bytes() + b'LaterMod : 1\r\n')
    # Scope the real launcher's automatic network check to a closed loopback port.
    put(root, BRAND + '.exe.config', b'<?xml version="1.0"?><configuration><system.net>'
        b'<defaultProxy enabled="true"><proxy usesystemdefault="false" autoDetect="false" '
        b'proxyaddress="http://127.0.0.1:1" bypassonlocal="false"/></defaultProxy>'
        b'</system.net></configuration>')
    old_brand = 'KoreanAIR_AC8_ModPack_1.2'
    shutil.copy2(helper, root / (BRAND + '.exe'))
    (root / (BRAND + '.exe')).rename(root / (old_brand + '.exe'))
    record = state(root)
    for item in record['files']:
        if item['path'] == BRAND + '.exe':
            item['hash'] = binary_hashes['helper']
            item['path'] = old_brand + '.exe'
    record['version'] = '1.2'
    record['build'] = 0
    state_path = root / 'KoreanAIR_AC8_ModPack/installed.json'
    state_path.write_text(json.dumps(record), encoding='utf-8')
    start = time.monotonic()
    monitor_report = OUT / (name + '_launcher.json')
    observer = subprocess.Popen([str(helper), 'monitor', str(root / (BRAND + '.exe')), str(monitor_report)],
                                creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, errors='replace')
    execute(root / (old_brand + '.exe'), 'parent', root, SETUP, delay_ms, capture=False)
    monitor_stdout, monitor_stderr = observer.communicate(timeout=45)
    if observer.returncode:
        raise AssertionError('Fixture launcher monitor failed: ' + monitor_stdout + monitor_stderr)
    monitor = json.loads(monitor_report.read_text(encoding='utf-8-sig'))
    updated = state(root)
    check(name + '_reopened_fixture_launcher_closed', monitor['visible'] and monitor['closeRequested'] and monitor['exited'])
    check(name + '_release_version_and_build', updated['version'] == VERSION and updated['build'] == BUILD)
    check(name + '_previous_launcher_removed', not (root / (old_brand + '.exe')).exists())
    check(name + '_new_launcher_binary', hashlib.sha256((root / (BRAND + '.exe')).read_bytes()).hexdigest() == expected_launcher_hash)
    check(name + '_module_choices', tuple(int(updated[k]) for k in ('campaign', 'mouse', 'display')) == flags)
    check(name + '_suspended_state', updated['suspended'] == suspended)
    check(name + '_saved_ini_bytes', all((root / path).read_bytes() == value for path, value in saved.items()))
    pack = (root / (MOD + 'pack.ini')).read_text(encoding='utf-8-sig')
    check(name + '_pack_extra_settings', '[diagnostics]\nenabled=1' in pack and '[custom]\nfixture=keep' in pack)
    check(name + '_other_mod_rows', all(line in mods.read_text(encoding='utf-8-sig')
                                      for line in ('OtherMod : 0', '; external comment', 'LaterMod : 1')))
    parkable = ('Game/Binaries/Win64/dinput8.dll', 'Game/Binaries/Win64/dwmapi.dll',
                'Game/Content/Paks/pakchunk0-Windows_999_P.pak')
    check(name + '_installed_hash_inventory', all(hashlib.sha256(
        (root / ('KoreanAIR_AC8_ModPack/Disabled/' + item['path']
         if suspended and item['path'] in parkable else item['path'])).read_bytes()).hexdigest() == item['hash']
        for item in updated['files'] if not item['mutable']))
    check(name + '_copied_setup_hash', hashlib.sha256((root / 'KoreanAIR_AC8_ModPack/Setup.exe').read_bytes()).hexdigest() == binary_hashes['setup'])
    case_reports.append(dict(name=name, fixture=str(root), parent=json.loads((root / 'handoff-parent.json').read_text()),
                             launcher=monitor, duration_seconds=round(time.monotonic() - start, 3)))
language_after = preference.read_bytes() if preference.exists() else None
check('language_preference_untouched', language_before == language_after)
report = dict(passed=all(c['passed'] for c in checks), checks=checks, cases=case_reports,
              tested_source_sha256=source_hashes, tested_binary_sha256=binary_hashes,
              test_source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (D / 'tests/UpdateHandoffProcess.cs', Path(__file__))})
(OUT / 'results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(dict(passed=report['passed'], checks=len(checks), report=str(OUT / 'results.json'))))
