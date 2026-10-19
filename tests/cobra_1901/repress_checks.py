"""Pin a same-mapping S release/repress loss against the previous header.

The fixture compiles the actual production ownership, PSM sampler, Control and
axis selector into two separate DLLs. Only Control's header differs. The real
EXE admission instructions execute in synthetic memory, never a live process.
"""
from pathlib import Path
import ast
import ctypes
import hashlib
import json
import math
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
TESTS = HERE.parent
DIST = TESTS.parent
RUNTIME = DIST / "runtime"
sys.path.insert(0, str(TESTS))
from native_player_maneuver_test import Executable, NativeFixture, DRIFT  # noqa: E402

BASELINE = HERE / "repress_baseline_native_player_maneuver.h"
BASELINE_SHA = "d9f93362a85930c5adc15d8a26ec81576e547fe6e2aea4658210b75848ee8394"
VCVARS = Path("C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat")
BUILD = HERE / "repress_build"
BUILD.mkdir(exist_ok=True)
checks = 0


def require(condition, label):
    global checks
    checks += 1
    assert condition, label


def function(text, signature):
    start = text.index(signature)
    end = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def fixture_source(header):
    production = (RUNTIME / "src/mouse_aim.cpp").read_text(encoding="utf-8")
    test_text = (TESTS / "native_psm_input_pipeline_test.py").read_text(encoding="utf-8")
    constants = {}
    for statement in ast.parse(test_text).body:
        if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Constant):
            for target in statement.targets:
                if isinstance(target, ast.Name) and target.id in ("prefix", "fixture"):
                    constants[target.id] = statement.value.value
    start = production.index("for(int i=0;i<3;++i)trace.raw_before[i]=axes[i];")
    ownership = production[start:production.index("const auto* settings=", start)]
    start = production.index("for(int i=0;i<3;++i) {", production.index("const bool held_axis[]={held_pitch,held_yaw,held_roll};"))
    selector = function(production[start:], "for(int i=0;i<3;++i) {")
    fixture = constants["fixture"].replace("/* ACTUAL_PRODUCTION_OWNERSHIP */", ownership)
    fixture = fixture.replace("/* ACTUAL_PRODUCTION_SELECTOR */", selector)
    fixture = fixture.replace("/* ACTUAL_PRODUCTION_SYNC_GATE */", next(line.strip() for line in production.splitlines() if "commit_response_sync(pawn,context,trace);" in line))
    fixture = fixture.replace("/* ACTUAL_PRODUCTION_GUIDANCE_GATE */", next(line.strip() for line in production.splitlines() if "const bool apply_guidance=" in line))
    prefix = constants["prefix"].replace('#include "native_player_maneuver.h"', '#include "' + header.as_posix() + '"')
    return prefix + function(production, "player_maneuver::Snapshot sample_player_maneuver(") + function(production, "native_maneuver::Snapshot sample_native_maneuver(") + fixture


class Pipeline:
    def __init__(self, name, header):
        self.directory = BUILD / name
        self.directory.mkdir(exist_ok=True)
        source = self.directory / "repress_fixture.cpp"
        source.write_text(fixture_source(header), encoding="utf-8")
        command = self.directory / "repress_build.cmd"
        command.write_text(f'@echo off\ncall "{VCVARS}" >nul\ncl /nologo /O2 /EHsc /std:c++20 /LD /I"{RUNTIME / "src"}" repress_fixture.cpp /Fe:repress_fixture.dll >repress_build.log 2>&1\n', encoding="utf-8")
        result = subprocess.run(["cmd", "/c", str(command)], cwd=self.directory, capture_output=True)
        require(result.returncode == 0, (self.directory / "repress_build.log").read_text(encoding="utf-8", errors="replace"))
        self.dll = ctypes.CDLL(str(self.directory / "repress_fixture.dll"))
        self.dll.packet.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_int, ctypes.c_int,
            ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_uint,
            ctypes.c_int, ctypes.c_ulonglong, ctypes.c_float, ctypes.c_float,
            ctypes.POINTER(ctypes.c_float)]
        self.dll.packet.restype = ctypes.c_uint

    def reset(self):
        self.dll.reset_control()

    def packet(self, pitch=1, previous=1, mapping=3, key=True, mode=0,
               capability=1, speed=100, maximum=200, minimum=0, grace=.4,
               flags=0, yaw=0, roll=0):
        sent = (ctypes.c_float * 6)()
        state = self.dll.packet(pitch, previous, mode, capability, speed, maximum,
            minimum, grace, flags, key, mapping, yaw, roll, sent)
        require(list(sent)[3:] == [1, 1, 1], "all auxiliary input remains exact")
        return state, list(sent)

    def setup(self, **pending):
        self.reset()
        self.packet(0, key=False, mapping=1)
        self.packet(mapping=2, speed=201)
        # Continuing S becomes eligible, without inventing a new physical edge.
        state, _ = self.packet(mapping=3)
        require(not state & 2, "crossing speed cap with S held does not prepare PSM")
        self.packet(0, key=False, mapping=3)
        state, sent = self.packet(**pending)
        expected = pending.get("pitch", 1)
        require(not state & 2 and (sent[0] == expected or math.isnan(sent[0]) and math.isnan(expected)), "same-mapping press never writes a guessed packet")


require(hashlib.sha256(BASELINE.read_bytes()).hexdigest() == BASELINE_SHA, "previous published header pinned")
baseline = Pipeline("baseline", BASELINE)
current = Pipeline("current", RUNTIME / "src/native_player_maneuver.h")
exe = Executable(Path("E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe"))
try:
    replay = {}
    for name, pipeline in (("baseline", baseline), ("current", current)):
        pipeline.setup()
        state, first = pipeline.packet(mapping=4)
        native = NativeFixture(exe, previous_pitch=1, pitch=first[0],
            speed=100, high_g=1, yaw=first[1], roll=first[2])
        first_mode = native.admission()
        previous = native.read_float(DRIFT + 0x38)
        _, second = pipeline.packet(mapping=5, previous=previous)
        native.input(second[0], high_g=1, yaw=second[1], roll=second[2])
        second_mode = native.admission()
        replay[name] = {"neutral_preparation": bool(state & 2), "sent": [first[0], second[0]], "native_modes": [first_mode, second_mode]}
    require(replay["baseline"] == {"neutral_preparation": False, "sent": [1, 1], "native_modes": [0, 0]}, "previous header reproduces lost real S re-press")
    require(replay["current"] == {"neutral_preparation": True, "sent": [0, 1], "native_modes": [0, 2]}, "fixed production pipeline permits unchanged native admission to mode2")

    # Same-packet callbacks do not consume the transition. Only the immediately
    # following mapping can consume it, and a successful consume is one-shot.
    for repeated in (0, 1, 8, 120):
        current.setup()
        for _ in range(repeated):
            state, sent = current.packet(mapping=3)
            require(not state & 2 and sent[0] == 1, "same mapping leaves actual pitch unchanged")
        state, _ = current.packet(mapping=4)
        require(state & 2, "next contiguous packet consumes eligible event")
        current.packet(mapping=4, previous=0)
        for mapping in range(5, 20):
            state, sent = current.packet(mapping=mapping)
            require(not state & 2 and sent[0] == 1, "continued hold does not repeat consumed event")

    bad = [dict(speed=201), dict(capability=0), dict(grace=0), dict(flags=1 << 18),
           dict(flags=1 << 6), dict(flags=1 << 5, minimum=150), dict(mode=1),
           dict(previous=0), dict(pitch=0), dict(pitch=-1), dict(pitch=float("nan"))]
    # Gate must be open BOTH at observation and consumption, and an intervening
    # bad callback cancels it even when no new mapper packet has arrived.
    for parameters in bad:
        for when in ("observe", "consume", "intervene"):
            current.setup(**(parameters if when == "observe" else {}))
            if when == "intervene":
                current.packet(mapping=3, **parameters)
            state, _ = current.packet(mapping=4, **(parameters if when == "consume" else {}))
            require(not state & 2, f"{when} invalidates eligible re-press: {parameters}")
            next_mapping = 5
            # A zero/negative FRESH raw packet creates its own genuine rising
            # input next time. Consume that ordinary edge's zero history before
            # checking steady holds; it is independent of the expired event.
            if when == "consume" and parameters.get("pitch", 1) <= 0:
                state, _ = current.packet(mapping=5)
                require(state & 2, "later genuine native pitch sign edge retains existing behavior")
                current.packet(mapping=6, previous=0)
                next_mapping = 7
            for mapping in range(next_mapping, 12):
                state, _ = current.packet(mapping=mapping)
                require(not state & 2, f"ineligible event cannot revive on steady held S: {when} {parameters}")

    for skip in (5, 6, 100):
        current.setup()
        for mapping in (skip, skip + 1):
            state, _ = current.packet(mapping=mapping)
            require(not state & 2, "missing immediate mapping expires deferred press")

    for mode in (1, 2):
        current.setup()
        current.packet(mapping=3, mode=mode)
        state, _ = current.packet(mapping=4)
        require(not state & 2, "native mode ownership discards deferred press")
    current.setup()
    current.reset()
    for mapping in (4, 5, 6):
        state, _ = current.packet(mapping=mapping)
        require(not state & 2, "reset does not guess an existing held key was freshly pressed")
    current.setup()
    current.packet(0, key=False, mapping=3)
    for mapping in (4, 5):
        state, _ = current.packet(key=False, mapping=mapping)
        require(not state & 2, "released key cancels event")

    # Ineligible press, then many eligible frames at different update rates.
    for rate in (35, 60, 180, 360):
        current.setup(speed=201)
        for mapping in range(4, 4 + rate):
            state, sent = current.packet(mapping=mapping)
            require(not state & 2 and sent[0] == 1, "held S across falling speed never synthesizes PSM")

    unit_source = RUNTIME / "native_player_maneuver_test.cpp"
    command = BUILD / "repress_unit.cmd"
    command.write_text(f'@echo off\ncall "{VCVARS}" >nul\ncl /nologo /O2 /EHsc /std:c++20 "{unit_source}" /Fe:repress_unit.exe >repress_unit_build.log 2>&1\nif errorlevel 1 exit /b 1\nrepress_unit.exe\n', encoding="utf-8")
    result = subprocess.run(["cmd", "/c", str(command)], cwd=BUILD, capture_output=True)
    require(result.returncode == 0, result.stdout.decode("utf-8", errors="replace") + result.stderr.decode("utf-8", errors="replace") + (BUILD / "repress_unit_build.log").read_text(encoding="utf-8", errors="replace"))
    report = {"passed": True, "checks": checks, "native_replay": replay,
        "baseline_sha256": BASELINE_SHA,
        "current_header_sha256": hashlib.sha256((RUNTIME / "src/native_player_maneuver.h").read_bytes()).hexdigest(),
        "production_pipeline_sha256": hashlib.sha256((RUNTIME / "src/mouse_aim.cpp").read_bytes()).hexdigest(),
        "scope": "Synthetic actual production fragments plus unmodified full native EXE admission. No live flight, speed/settings/history game edits, or remote report root-cause claim."}
    (HERE / "repress_evidence.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS S re-press regression: {checks} checks; previous header loses edge/mode0, fix emits neutral once then native mode2; no speed-triggered held-S admission.")
finally:
    exe.close()
