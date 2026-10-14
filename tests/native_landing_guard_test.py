"""Pinned EXE landing evidence and isolated ownership/lifecycle regression.

No game process is started or modified. Native gate instructions execute only
against synthetic memory; full aircraft landing behavior remains a live check.
"""
from pathlib import Path
import hashlib
import json
import re
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parent / 'runtime'
RESP = HERE.parents[1] / 'ac8-mouseflight' / 'responsive'
sys.path.insert(0, str(RESP / 'tools'))
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSI, UC_X86_REG_RSP, UC_X86_REG_RCX, UC_X86_REG_RAX
from native_player_maneuver_test import Executable

BUILD = HERE / 'native_landing_guard_build'
BUILD.mkdir(exist_ok=True)
vcvars = Path('C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat')
command = ('@echo off\ncall "' + str(vcvars) + '" >nul\n'
           'cl /nologo /EHsc /std:c++20 /O2 "' + str(RUNTIME / 'native_landing_guard_test.cpp') +
           '" /Fe:native_landing_guard_test.exe >build.log 2>&1\n'
           'if errorlevel 1 exit /b 1\nnative_landing_guard_test.exe\n')
(BUILD / 'run.cmd').write_text(command)
result = subprocess.run(['cmd', '/c', str(BUILD / 'run.cmd')], cwd=BUILD, capture_output=True, text=True)
if result.returncode:
    print(result.stdout, result.stderr, (BUILD / 'build.log').read_text(encoding='utf-8', errors='replace'))
    raise SystemExit(result.returncode)
print(result.stdout.strip())

source = (RUNTIME / 'src/native_landing_guard.h').read_text()
guards = re.findall(r'\{0x([\dA-F]+)u,0x([\dA-F]+)u,0x([\dA-F]+)ull\}', source)
game = Executable(Path('E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe'))
verified = []
for rva, size, wanted in guards:
    rva, size, wanted = int(rva, 16), int(size, 16), int(wanted, 16)
    value = 14695981039346656037
    code = game.read(rva, size)
    for byte in code:
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    assert value == wanted, hex(rva)
    verified.append({'rva': hex(rva), 'size': size, 'fnv64': hex(value), 'sha256': hashlib.sha256(code).hexdigest()})

phase_names = ['None', 'Fly', 'GearDown', 'StopPlane', 'RespawnWait', 'FadeOut', 'Catapult', 'Runway']
for index, name in enumerate(phase_names):
    pointer, value = struct.unpack('<QQ', game.read(0xC9E09B0 + 16 * index, 16))
    actual = game.read(pointer - game.base, 100).split(b'\0', 1)[0].decode()
    assert value == index and actual == 'ELiveTakeoffAndLandingState::' + name, (index, value, actual)
assert struct.unpack('<Q', game.read(0xC9E0FE0 + 0x4A8, 8))[0] == game.base + 0x7D7EAB0
assert struct.unpack('<7I', game.read(0x7D7FC34, 28)) == (
    0x7D7EB15, 0x7D7EBA2, 0x7D7F021, 0x7D7F0ED, 0x7D7F18B, 0x7D7F3F4, 0x7D7F8E6)

# Execute the real native branch after component and actor-type admission.
# Stop before its native helper; no helper's behavior is replaced or claimed.
gate_cases = []
for flags in [0, 1 << 18, 1 << 9, 0x40200]:
    for replace, blend in [(0, 0), (1, 0), (0, 1)]:
        uc = Uc(UC_ARCH_X86, UC_MODE_64)
        code_page = game.base + 0x7D63000
        uc.mem_map(code_page, 0x2000)
        uc.mem_write(code_page, game.read(0x7D63000, 0x2000))
        pawn = 0x2000000
        uc.mem_map(pawn, 0x6000)
        uc.mem_write(pawn + 0x2B18, struct.pack('<I', flags))
        uc.mem_write(pawn + 0x1425, bytes([replace, blend]))
        uc.reg_write(UC_X86_REG_RSI, pawn)
        uc.mem_map(0x3000000, 0x10000)
        uc.reg_write(UC_X86_REG_RSP, 0x300F000)
        destinations = []
        def stop(engine, address, size, user):
            if address in (game.base + 0x7D63FAA, game.base + 0x7D63FB4, game.base + 0x7D646D5):
                destinations.append(address - game.base)
                engine.emu_stop()
        uc.hook_add(UC_HOOK_CODE, stop)
        uc.emu_start(game.base + 0x7D63F74, game.base + 0x7D646D6, count=30)
        expected = 0x7D646D5 if not flags & (1 << 9) else (0x7D63FB4 if replace or blend else 0x7D63FAA)
        assert destinations == [expected], (flags, replace, blend, destinations)
        gate_cases.append({'flags': hex(flags), 'replace': replace, 'blend': blend, 'destination': hex(expected)})

# Execute the actual landing entry AND its complete native controller getter.
# The native StaticClass accessor reads its populated cache, just as it does
# during play. No game helper is stubbed; stop before cloned controller copy.
controller_cases = []
for kind in ['absent-component', 'dead-component', 'absent-controller', 'null-class',
             'short-ancestry', 'wrong-ancestor', 'exact-class', 'derived-class']:
    uc = Uc(UC_ARCH_X86, UC_MODE_64)
    for rva, size in [(0x7D70000, 0x1000), (0x71E5000, 0x1000), (0x6F0D000, 0x1000), (0xE515000, 0x1000)]:
        uc.mem_map(game.base + rva, size)
        uc.mem_write(game.base + rva, game.read(rva, size))
    pawn, component, controller, wanted, actual, ancestors = (0x2000000, 0x2010000, 0x2011000, 0x2012000, 0x2013000, 0x2014000)
    uc.mem_map(pawn, 0x20000)
    uc.mem_map(0x3000000, 0x10000)
    uc.mem_map(0x4000000, 0x1000)
    stack = 0x300F000
    uc.mem_write(stack, struct.pack('<Q', 0x4000000))
    uc.reg_write(UC_X86_REG_RSP, stack)
    uc.reg_write(UC_X86_REG_RCX, pawn)
    uc.mem_write(game.base + 0xE515A30, struct.pack('<Q', wanted))
    uc.mem_write(pawn + 0x58B0, struct.pack('<Q', 0 if kind == 'absent-component' else component))
    uc.mem_write(component + 8, struct.pack('<I', 0x40000000 if kind == 'dead-component' else 0))
    uc.mem_write(pawn + 0xED0, struct.pack('<Q', 0 if kind == 'absent-controller' else controller))
    uc.mem_write(controller + 0x10, struct.pack('<Q', 0 if kind == 'null-class' else actual))
    uc.mem_write(wanted + 0x38, struct.pack('<i', 1))
    uc.mem_write(actual + 0x38, struct.pack('<i', 0 if kind == 'short-ancestry' else (2 if kind == 'derived-class' else 1)))
    uc.mem_write(actual + 0x30, struct.pack('<Q', ancestors))
    uc.mem_write(ancestors + 8, struct.pack('<Q', 0 if kind == 'wrong-ancestor' else wanted + 0x30))
    observed = []
    def stop_controller(engine, address, size, user):
        if address in (game.base + 0x7D704FC, 0x4000000):
            observed.append(address == game.base + 0x7D704FC)
            engine.emu_stop()
    uc.hook_add(UC_HOOK_CODE, stop_controller)
    uc.emu_start(game.base + 0x7D70440, 0x4000001, count=140)
    expected = kind in ['exact-class', 'derived-class']
    assert observed == [expected], (kind, observed)
    controller_cases.append({'case': kind, 'native_transform_path_entered': expected})

log = Path('E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/Logs/MouseAim-00028.log')
rows = log.read_text().splitlines()
landing = next((index, line) for index, line in enumerate(rows, 1) if 'flags=00040200' in line)
seeds = []
for index, line in enumerate(rows, 1):
    match = re.match(r'(\d+) native mission seed: heading=\(([-\d.]+),([-\d.]+)\)', line)
    if match and int(match[1]) >= 288250000:
        seeds.append((index, int(match[1]), float(match[2]), float(match[3])))
flips = sum(abs(abs(b[3] - a[3]) - 180) < .005 for a, b in zip(seeds, seeds[1:]))
assert landing and flips > 50
evidence = {
    'scope': 'Read-only pinned executable derivation plus synthetic ownership/gate/lifecycle checks; live landing fix not yet verified.',
    'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
    'fingerprints': verified,
    'component': {'pawn_pointer': '0x58B0', 'vtable_rva': '0xC9E0FE0', 'owner': '0x90', 'phase': '0x118', 'disabled': '0x12E'},
    'phase_values': dict(enumerate(phase_names)),
    'native_gate': {'raw_flags': 'pawn+0x2B18 bit9', 'replace': 'pawn+0x1425', 'blend': 'pawn+0x1426', 'synthetic_cases': gate_cases,
                    'controller': 'pawn+ED0 IsA cached LiveNetworkPlayerPlane class at module+E515A30; native71E5600 class ancestry test',
                    'actual_entry_and_controller_getter_cases': controller_cases},
    'native_transform': '7D70440 uses cloned controller pawn+3C60; 7D70D38 calls native4D33880 on real pawn+2268 after input/physics.',
    'live_00028': {'landing_flags_line': landing[0], 'landing_flags_tick': 288242125, 'yaw_sent': 1.0,
                   'seed_samples': len(seeds), 'opposite_heading_transitions': flips,
                   'first_seed_line': seeds[0][0], 'last_seed_line': seeds[-1][0]},
    'crash_limitation': "Reporter provided only UE4 '01'. Saved contexts dated Oct4/Oct10 and UE4SS dumps Oct13 cannot identify that reported event or establish that it is fixed. Latest Oct13 UE4SS log ends normally.",
}
(HERE / 'native_landing_guard_evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
game.close()
print(f'PASS: {len(verified)} independent pinned fingerprints, phase enum/vtable/switch derivation, {len(gate_cases)} native gate branches, {len(controller_cases)} actual entry/controller getter cases; log shows {flips} opposite-heading transitions.')
