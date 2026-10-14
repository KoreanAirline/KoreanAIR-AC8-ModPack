"""Read-only released1.0 versus b1302 landing/rotation guard comparison.

The guard classification instructions from both DLLs execute against synthetic
snapshots. This proves their admission behavior, not identical live landings.
"""
from pathlib import Path
import hashlib
import json
import re
import struct
import sys

HERE = Path(__file__).resolve().parent
RESP = HERE.parents[1] / 'ac8-mouseflight' / 'responsive'
sys.path.insert(0, str(RESP / 'tools'))
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RDI, UC_X86_REG_RSI, UC_X86_REG_RDX, UC_X86_REG_XMM8
from native_player_maneuver_test import Executable

paths = {
    'released1.0': HERE / 'compare_v10_payload/payload/Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/Scripts/ac8_mouse_aim_010.dll',
    'b1302_before_landing_fix': HERE / 'fixtures_120206/changed_owned/Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/Scripts/ac8_mouse_aim_010.dll',
}
ranges = {'released1.0': (0x145E0, 0x16D46, 0x1A280, 0x10D79),
          'b1302_before_landing_fix': (0x191A0, 0x1C55C, 0x20300, 0x14859)}
payloads = {label: Executable(path) for label, path in paths.items()}
assert hashlib.sha256(paths['b1302_before_landing_fix'].read_bytes()).hexdigest() == '53be7efe23207feb7af17f1276d7fb587443be79cceaeca1ee840963d5143e04'
rows = {}
ownership_codes = {}
samplers = {}
for label, image in payloads.items():
    processor, processor_end, sampler, classification = ranges[label]
    data = paths[label].read_bytes()
    ownership_codes[label] = image.read(classification, 0x38)
    normalized = bytearray(image.read(sampler, 0x5F))
    normalized[0x1E:0x22] = b'\0' * 4  # The one RIP-relative verified-code bool.
    samplers[label] = bytes(normalized)
    processor_code = image.read(processor, processor_end - processor)
    rows[label] = {
        'sha256': hashlib.sha256(data).hexdigest(),
        'process_input_rva': hex(processor),
        'maneuver_sampler_rva': hex(sampler),
        'maneuver_ownership_classification_rva': hex(classification),
        'landing_field_displacements_in_process_input': {
            hex(field): struct.pack('<I', field) in processor_code for field in [0x58B0, 0x1425, 0x1426]},
        'classification_sha256': hashlib.sha256(ownership_codes[label]).hexdigest(),
        'normalized_sampler_sha256': hashlib.sha256(samplers[label]).hexdigest(),
    }
assert ownership_codes['released1.0'] == ownership_codes['b1302_before_landing_fix']
assert samplers['released1.0'] == samplers['b1302_before_landing_fix']

cases = [(0, -1, 0), (0x40000, -1, 0), (0x40200, -1, 0),
         (1 << 9, -1, 0), ((1 << 17) | (1 << 19), -1, 0),
         ((1 << 17) | (1 << 18) | (1 << 19), -1, 0),
         (1 << 23, -1, 0), (1 << 24, -1, 0), (0, .1, 0),
         (1 << 19, -1, 1)]
results = []
for flags, state, alternate in cases:
    outputs = {}
    for label, image in payloads.items():
        start = ranges[label][3]
        page = start & ~0xFFF
        uc = Uc(UC_ARCH_X86, UC_MODE_64)
        uc.mem_map(image.base + page, 0x1000)
        uc.mem_write(image.base + page, image.read(page, 0x1000))
        snapshot = 0x2000000
        uc.mem_map(snapshot, 0x1000)
        uc.mem_write(snapshot, struct.pack('<IffBB', flags, state, 1.0, 1, alternate))
        uc.reg_write(UC_X86_REG_RDI, snapshot)
        uc.reg_write(UC_X86_REG_RDX, 0)
        uc.reg_write(UC_X86_REG_RSI, 0)
        uc.reg_write(UC_X86_REG_XMM8, 0)
        def stop(engine, address, size, user):
            if address == image.base + start + 0x38:
                engine.emu_stop()
        uc.hook_add(UC_HOOK_CODE, stop)
        uc.emu_start(image.base + start, image.base + start + 0x39, count=30)
        outputs[label] = bool(uc.reg_read(UC_X86_REG_RSI) & 0xFF)
    expected = bool(flags & (3 << 23) or state > 0 or
                    (flags & (7 << 17)) == ((1 << 17) | (1 << 19)) or alternate)
    assert all(value == expected for value in outputs.values()), (flags, state, alternate, outputs)
    results.append({'flags': hex(flags), 'state': state, 'alternate': alternate, 'native_maneuver_owned': outputs})

source = (HERE.parent / 'runtime/src/mouse_aim.cpp').read_text()
guard = (HERE.parent / 'runtime/src/native_landing_guard.h').read_text()
evidence = {
    'scope': 'Released1.0 and b1302 DLL instructions/fields; synthetic branch execution. No same-scenario live1.0 trace is available.',
    'payloads': rows,
    'ownership_classification_byte_identical': True,
    'normalized_maneuver_sampler_byte_identical': True,
    'actual_dll_instruction_cases': results,
    'confirmed_delta': 'b1302 source filters unheld native aggregate rotation to0 and adds mapping provenance/player PSM admission. Original1.0 has no corresponding early unheld-axis-zero sequence before parameter sampling. These differences do not identify the causal landing regression without matching live traces.',
    'new_guard_design': 'GearDown, bit18, and bit9 without a valid transform controller retain ordinary approach. Native bit9/script replace/blend requires the same pawn+ED0 LiveNetworkPlayerPlane class ancestry admitted by71E5600; enabled scripted phases3..7 independently defer flight/camera writes. Release seeds current heading once.',
    'qualification': 'Bit9 alone is insufficient. Guard now additionally checks the native controller getter prerequisites; actual7D70440 entry/getter instruction tests distinguish absent/foreign controller from valid exact/derived class. Current logs do not record phase orED0, so live runway confirmation remains necessary.',
    'current_mouse_aim_source_sha256': hashlib.sha256((HERE.parent / 'runtime/src/mouse_aim.cpp').read_bytes()).hexdigest(),
    'current_landing_guard_sha256': hashlib.sha256((HERE.parent / 'runtime/src/native_landing_guard.h').read_bytes()).hexdigest(),
}
(HERE / 'landing_v10_comparison_evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
for image in payloads.values():
    image.close()
print('PASS: original1.0 and b1302 ownership-classification bytes match; normalized sampler bytes match;10 native snapshot cases match, including no maneuver ownership for landing00040200.')
