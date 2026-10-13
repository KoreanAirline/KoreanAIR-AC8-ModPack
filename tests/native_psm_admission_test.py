"""Actual origin helper and native admission clones, synthetic memory only.

Runs complete pinned native instructions. Automatic-packet blocking must
preserve generic high-G admission, history and existing mode1/mode2 state;
the untouched clone must match every native register and memory result.
"""
from pathlib import Path
import ctypes
import hashlib
import itertools
import json
import struct
import subprocess
import sys

from native_player_maneuver_test import Executable, NativeFixture, DRIFT, SETTINGS, FLAGS
from unicorn.x86_const import (
    UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8,
    UC_X86_REG_R9, UC_X86_REG_R10, UC_X86_REG_R11, UC_X86_REG_EFLAGS,
    UC_X86_REG_XMM0, UC_X86_REG_XMM1, UC_X86_REG_XMM2, UC_X86_REG_XMM3,
    UC_X86_REG_XMM4, UC_X86_REG_XMM5,
)

HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parent / "runtime"
SOURCE = (RUNTIME / "src/mouse_aim.cpp").read_text(encoding="utf-8")


def function(name):
    first = SOURCE.index(name + "(")
    first = SOURCE.rfind("\n", 0, first) + 1
    end = SOURCE.index("{", first) + 1
    depth = 1
    while depth:
        depth += (SOURCE[end] == "{") - (SOURCE[end] == "}")
        end += 1
    return SOURCE[first:end]


first = SOURCE.index("player_admission_origin.publish(")
last = SOURCE.index(");", first) + 2
publication = SOURCE[first:last]
assert "apply_guidance&&valid&&!held_pitch&&!native_ownership&&!player_maneuver_control.neutral_edge" in publication
assert SOURCE.index("player_admission_origin.clear();", SOURCE.index("uintptr_t __fastcall process_input(")) < SOURCE.index("if(!active.load()", SOURCE.index("uintptr_t __fastcall process_input("))
PREFIX = r'''
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <atomic>
#include "native_psm_admission.h"
#include "native_raw_input.h"
thread_local native_input::RawOwnership native_raw;
thread_local player_admission::Origin player_admission_origin;
std::atomic<bool> enabled{true},active{true},game_paused{false},gaze_active{false};
std::atomic<uintptr_t> aircraft{0x2000000-0x2268};
std::atomic<uint64_t> input_generation{1};
bool looking=false;
bool free_look_suspends_guidance(){return looking;}
struct Control{bool neutral_edge=false;}player_maneuver_control;
'''
FIXTURE = r'''
extern "C" __declspec(dllexport) void build(const unsigned char* code,const unsigned* constants,int blocked,unsigned char* out){
    player_admission::Constants values{};memcpy(values.data(),constants,sizeof(values));
    player_admission::build_clone(out,code,values,blocked!=0);
}
extern "C" __declspec(dllexport) void reset(){
    native_raw.reset();player_admission_origin.clear();enabled=true;active=true;game_paused=false;gaze_active=false;
    looking=false;input_generation=1;aircraft=0x2000000-0x2268;
}
extern "C" __declspec(dllexport) void mapped(uintptr_t owner){mark_native_mapping(reinterpret_cast<unsigned char*>(owner));}
extern "C" __declspec(dllexport) void publish(float pitch,int keys,int automatic,int valid_input,int owned,int neutral){
    const uintptr_t pawn=aircraft.load();const bool apply_guidance=automatic!=0,valid=valid_input!=0,held_pitch=(keys&1)!=0,native_ownership=owned!=0;
    player_maneuver_control.neutral_edge=neutral!=0;float axes[3]={pitch,0,0};
    /* ACTUAL_PRODUCTION_PUBLICATION */
}
extern "C" __declspec(dllexport) int route(uintptr_t owner,uintptr_t dynamics,uintptr_t drift,float raw){
    uintptr_t context[5]={owner};player_admission::SavedFrame frame{};
    frame.r8=reinterpret_cast<uintptr_t>(context);frame.r9=dynamics;frame.rcx=drift;frame.rdx=reinterpret_cast<uintptr_t>(&raw);
    return block_automatic_psm(&frame);
}
extern "C" __declspec(dllexport) void gates(int on,int is_active,int paused,int gaze,int alt,int next_epoch){
    enabled=on!=0;active=is_active!=0;game_paused=paused!=0;gaze_active=gaze!=0;looking=alt!=0;
    if(next_epoch)input_generation.fetch_add(1);
}
'''.replace("/* ACTUAL_PRODUCTION_PUBLICATION */", publication)
BUILD = HERE / "native_psm_admission_build"
BUILD.mkdir(exist_ok=True)
(BUILD / "fixture.cpp").write_text(PREFIX + function("mark_native_mapping") + function("block_automatic_psm") + FIXTURE, encoding="utf-8")
vcvars = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
(BUILD / "run.cmd").write_text(f'@echo off\ncall "{vcvars}" >nul\ncl /nologo /O2 /EHsc /std:c++20 /LD /I"{RUNTIME / "src"}" fixture.cpp /Fe:fixture.dll >build.log 2>&1\n', encoding="utf-8")
result = subprocess.run(["cmd", "/c", str(BUILD / "run.cmd")], cwd=BUILD, capture_output=True, text=True)
if result.returncode:
    print((BUILD / "build.log").read_text(encoding="utf-8", errors="replace"))
    sys.exit(result.returncode)
dll = ctypes.CDLL(str(BUILD / "fixture.dll"))
dll.build.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_uint), ctypes.c_int, ctypes.POINTER(ctypes.c_ubyte)]
dll.publish.argtypes = [ctypes.c_float, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
dll.route.argtypes = [ctypes.c_ulonglong, ctypes.c_ulonglong, ctypes.c_ulonglong, ctypes.c_float]
dll.route.restype = ctypes.c_int
dll.mapped.argtypes = [ctypes.c_ulonglong]
OWNER = 0x2000000
checks = 0


def require(ok, message):
    global checks
    checks += 1
    assert ok, message


def route(raw=1, owner=OWNER, dynamics=OWNER + 0x98, drift=OWNER + 0x108):
    return bool(dll.route(owner, dynamics, drift, raw))


for keys, raw in itertools.product(range(8), [-1, 0, .9152, 1]):
    dll.reset();dll.mapped(OWNER)
    dll.publish(raw, keys, True, True, False, False)
    expected = not bool(keys & 1)
    require(route(raw) == expected, "actual automatic publication/helper excludes only unheld automatically selected pitch")
    require(route(raw) == expected, "same retained packet remains protected across repeated native physics substeps")
    require(not route(raw, owner=OWNER + 0x4000), "unrelated native actor defaults to untouched admission")
    require(route(raw) == expected, "unrelated actor cannot consume the player's retained origin")
    require(not route(raw, dynamics=OWNER + 0x90) and not route(raw, drift=OWNER + 0x100), "unmatched native dynamics/drift defaults native")
    if raw != 0:
        require(not route(0), "a changed raw packet defaults native")
    dll.mapped(OWNER)
    require(not route(raw), "new native mapping clears stale automatic origin")
for automatic, valid, owned, neutral in [(False, True, False, False), (True, False, False, False), (True, True, True, False), (True, True, False, True)]:
    dll.reset();dll.mapped(OWNER);dll.publish(1, 0, automatic, valid, owned, neutral)
    require(not route(), "native/disabled/invalid/accepted maneuver/physical neutral preparation retains untouched admission")
for gates in [(0,1,0,0,0,0), (1,0,0,0,0,0), (1,1,1,0,0,0), (1,1,0,1,0,0), (1,1,0,0,1,0), (1,1,0,0,0,1)]:
    dll.reset();dll.mapped(OWNER);dll.publish(1, 0, True, True, False, False);dll.gates(*gates)
    require(not route(), "off/inactive/pause/gaze/Alt/lifecycle epoch defaults native without stale automatic authority")

EXE = Executable(Path("E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe"))
CLONE = 0x6000000
try:
    code = EXE.read(0x4D3F3A0, 0x22B)
    require(hashlib.sha256(code).hexdigest() == "89236b998877e58ad79646c27015f58f339be799222ed7cd5536d61694d321b8", "complete native admission instruction fingerprint")
    constants = []
    for offset in [0x4E, 0x70, 0x9D, 0xAD, 0xB9, 0xE3]:
        displacement = struct.unpack_from("<i", code, offset + 4)[0]
        constants.append(struct.unpack("<I", EXE.read(0x4D3F3A0 + offset + 8 + displacement, 4))[0])
    input_code = (ctypes.c_ubyte * len(code)).from_buffer_copy(code)
    input_constants = (ctypes.c_uint * 6)(*constants)
    clones = []
    for blocked in [False, True]:
        output = (ctypes.c_ubyte * 0x300)()
        dll.build(input_code, input_constants, blocked, output)
        clones.append(bytes(output))
    registers = [UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9,
        UC_X86_REG_R10, UC_X86_REG_R11, UC_X86_REG_EFLAGS, UC_X86_REG_XMM0, UC_X86_REG_XMM1,
        UC_X86_REG_XMM2, UC_X86_REG_XMM3, UC_X86_REG_XMM4, UC_X86_REG_XMM5]

    def run(pitch, previous, mode, speed, flags, high_g, clone=None, native_button=True, roll=-.4375):
        fixture = NativeFixture(EXE, pitch=pitch, previous_pitch=previous, speed=speed, flags=flags,
            high_g=high_g, native_button=native_button, yaw=.3125, roll=roll)
        fixture.uc.mem_write(DRIFT + 0x1D, bytes([mode, 1 if mode == 2 else 0]))
        fixture.float(SETTINGS + 0x3D0, 138.889)
        fixture.float(SETTINGS + 0x380, .4)
        fixture.float(DRIFT + 8, .39)
        fixture.uc.reg_write(UC_X86_REG_XMM5, 0x123456789ABCDEF0123456789ABCDEF0)
        if clone is None:
            fixture.admission()
        else:
            fixture.uc.mem_map(CLONE, 4096);fixture.uc.mem_write(CLONE, clone)
            fixture.execute(CLONE - EXE.base)
        require(struct.unpack("<I", fixture.uc.mem_read(FLAGS, 4))[0] == flags, "native flags remain byte-exact")
        return bytes(fixture.uc.mem_read(DRIFT, 0x60)), [fixture.uc.reg_read(reg) for reg in registers], fixture

    cases = 0
    for pitch, previous, mode, speed, flags, high_g in itertools.product(
        [-1, 0, 1], [-1, 0, 1], [0, 1, 2], [130, 155.023], [0, 0x100, 0x180, 1 << 6, 1 << 18], [0, 1]):
        native_memory, native_registers, _ = run(pitch, previous, mode, speed, flags, high_g)
        copied_memory, copied_registers, _ = run(pitch, previous, mode, speed, flags, high_g, clones[0])
        require(copied_memory == native_memory and copied_registers == native_registers,
            "complete unmodified clone matches native memory and every volatile/flags/XMM0..5 result")
        expected_memory, _, _ = run(pitch, previous, mode, speed, flags & ~0x100, high_g, native_button=False)
        blocked_memory, _, fixture = run(pitch, previous, mode, speed, flags, high_g, clones[1])
        require(blocked_memory == expected_memory,
            "candidate-only skip preserves exact native generic highG, history and existing mode1/mode2 state")
        require(mode == 2 or fixture.mode != 2, "automatic low-speed combo and flag8 never synthesize native PSM admission")
        cases += 1
    # Real log 00026 has key0 mode2 at these speeds, with flag8 forcing the
    # button gate. Reproduce its causal raw-auto rise without any game edits.
    for speed in [126.726, 135.152]:
        _, _, original = run(1, 0, 0, speed, 0x180, 1)
        _, _, automatic = run(1, 0, 0, speed, 0x180, 1, clones[1])
        require(original.mode == 2 and automatic.mode == 1,
            "logged Ctrl+Shift-only automatic rise loses only PSM entry while retaining genuine generic highG")
    # The native history store still receives zero then actual held S. No
    # velocity/capability/native pitch-history or raw axis edits are made.
    _, _, physical = run(0, 1, 0, 130, 0x100, 1, clones[0], roll=0)
    require(physical.mode == 0 and physical.read_float(DRIFT + 0x38) == 0, "native neutral preparation stores its own zero")
    physical.input(1, high_g=1)
    physical.execute(CLONE - EXE.base)
    require(physical.mode == 2 and physical.phase == 1, "genuine subsequent held S retains exact native PSM entry")
    report = {"passed": True, "checks": checks, "native_cases": cases,
        "production_fragments": ["mark_native_mapping", "block_automatic_psm", "actual selected raw origin publication", "Origin", "build_clone"],
        "source_sha256": {"runtime/src/mouse_aim.cpp": hashlib.sha256((RUNTIME / "src/mouse_aim.cpp").read_bytes()).hexdigest(), "runtime/src/native_psm_admission.h": hashlib.sha256((RUNTIME / "src/native_psm_admission.h").read_bytes()).hexdigest()},
        "finding": "Automatic packets skip only native PSM candidate evaluation, including flag8 forced eligibility, while ordinary raw pursuit, generic highG, native history and accepted native modes retain their own behavior. Physical S/neutral preparation and unknown/native/off/Alt paths retain unchanged admission.",
        "scope": "Complete native instructions and extracted production provenance in synthetic memory; no game process, trajectory or live-flight claim."}
    (HERE / "native_psm_admission_evidence.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS native PSM admission provenance: {checks} checks; {cases} complete native cases; automatic candidate-only skip, repeated substeps, native/generic/history/physical-S parity.")
finally:
    EXE.close()
