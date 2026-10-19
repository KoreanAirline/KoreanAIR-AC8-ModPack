"""Read-only historical admission audit of released 2.3/2.2 and exact 1.0.

No game process is read or started. Copied released instructions operate on
synthetic memory. Admission alone does not model mode1 physics or trajectories,
and cannot identify an unlogged user's current issue.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
TESTS = HERE.parent
ROOT = TESTS.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(ROOT.parent / "libs"))
from native_player_maneuver_test import Executable, NativeFixture, DRIFT, SETTINGS
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R12, UC_X86_REG_R14, UC_X86_REG_RSI, UC_X86_REG_RSP

checks = 0


def require(condition, label):
    global checks
    checks += 1
    assert condition, label


baseline = TESTS / "support_1701/baseline_1608_sources.zip"
published = HERE / "baseline_1701_sources.zip"
unchanged = []
with ZipFile(baseline) as archive, ZipFile(published) as release:
    identity = json.loads(release.read("release.json"))
    require(identity["version"] == "2.3" and identity["build"] == 2026101701,
            "historical comparison is the published 2.3 b1701 archive")
    for relative in ("runtime/src/native_psm_admission.h", "runtime/src/native_player_maneuver.h", "runtime/src/native_raw_input.h", "runtime/src/manual_rotation_input.h"):
        normalize = lambda data: data.decode("utf-8-sig").replace("\r\n", "\n")
        require(normalize(archive.read(relative)) == normalize(release.read(relative)),
                relative + " in published 2.3 b1701 unchanged from released 2.2 b1608")
        unchanged.append(relative)

# Execute the same complete first pitch-selection iteration as the existing
# exact 1.0 audit. The ordinary pitch branch does not call any native helper.
dll = TESTS / "compare_v10_payload/payload/Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/Scripts/ac8_mouse_aim_010.dll"
raw = dll.read_bytes()
require(hashlib.sha256(raw).hexdigest() == "8a55cb69ea205570475840129033a25ceeda4c16924090af32d74369bb009b2c", "exact released 1.0 DLL")
image = pefile.PE(data=raw)
base = image.OPTIONAL_HEADER.ImageBase
machine = Uc(UC_ARCH_X86, UC_MODE_64)
machine.mem_map(base + 0x16000, 0x1000)
machine.mem_write(base + 0x16000, image.get_data(0x16000, 0x1000))
machine.mem_map(base + 0x2C000, 0x1000)
machine.mem_write(base + 0x2C000, image.get_data(0x2C000, 0x1000))
stack, pawn = 0x1000000, 0x2000000
machine.mem_map(stack, 0x10000)
machine.mem_map(pawn, 0x4000)


def original_pitch(held, native, wanted):
    sp = stack + 0x8000
    machine.mem_write(sp, b"\0" * 0x800)
    machine.mem_write(sp + 0x5C, bytes([held]))
    machine.mem_write(sp + 0x61, b"\1")
    machine.mem_write(sp + 0xE0, struct.pack("<f", wanted))
    machine.mem_write(pawn + 0x2268, struct.pack("<f", native))
    machine.reg_write(UC_X86_REG_RSP, sp)
    machine.reg_write(UC_X86_REG_RSI, 1)
    machine.reg_write(UC_X86_REG_R12, 0)
    machine.reg_write(UC_X86_REG_R14, pawn)
    machine.reg_write(UC_X86_REG_R8, 1)
    machine.emu_start(base + 0x16359, base + 0x1647B, count=100)
    return struct.unpack("<f", machine.mem_read(pawn + 0x2268, 4))[0]


require(original_pitch(False, 0, 1) == 1, "1.0 supplies an automatic positive pitch when S is not held")
require(original_pitch(True, 1, -1) == 1, "1.0 preserves physical S despite an opposite automatic target")
exe = Executable(Path("E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe"))
cases = []
try:
    # A positive history means candidate-only PSM blocking has no additional
    # effect. This native sequence therefore applies with and without that
    # later safety guard. Throttle/brake/highG are synthetic full-scale inputs.
    automatic = original_pitch(False, 0, 1)
    f = NativeFixture(exe, previous_pitch=1, pitch=automatic, speed=100, high_g=1, roll=0)
    f.float(SETTINGS + 0x380, .4)
    onset = None
    for frame in range(1, 41):
        f.input(automatic, high_g=1)
        if f.admission():
            onset = frame
            break
    require(f.mode == 1 and onset == 24, "native generic highG admits mode1 after 24 synthetic 60Hz positive-pitch frames")
    f.input(original_pitch(True, 1, -1), high_g=1)
    require(f.admission() == 1, "already admitted native mode1 does not enter mode2 merely because the pitch now belongs to S")
    require(0x4D3F530 not in f.visited, "native mode1 skips the PSM candidate itself")
    cases.append({"case": "positive_auto_then_S", "generic_mode1_frame": onset, "after_S_mode": f.mode})

    f = NativeFixture(exe, previous_pitch=0, pitch=0, speed=100, high_g=1)
    f.float(SETTINGS + 0x380, .4)
    for frame in range(40):
        f.input(0, high_g=1)
        require(f.admission() == 0, "neutral pitch combo alone remains native mode0")
    f.input(original_pitch(True, 1, -1), high_g=1)
    require(f.admission() == 2, "same native eligible speed and fresh positive S enter mode2 after neutral combo")
    cases.append({"case": "neutral_combo_then_S", "after_S_mode": f.mode})
finally:
    exe.close()

report = {
    "passed": True,
    "checks": checks,
    "published_2_3_b1701_unchanged_from_2_2_b1608": unchanged,
    "historical_archive_sha256": {
        "2.2_b1608": hashlib.sha256(baseline.read_bytes()).hexdigest(),
        "2.3_b1701": hashlib.sha256(published.read_bytes()).hexdigest(),
    },
    "original_1_0_dll_sha256": hashlib.sha256(raw).hexdigest(),
    "original_instruction_range": "16359..1647B pitch-selection iteration",
    "native_sequences": cases,
    "finding": "Existing positive-pitch generic highG can own native mode1 before a subsequent S press. The released 1.0 pitch selector can supply that automatic pitch too; the published 2.2 b1608 and 2.3 b1701 admission and physical-input headers are identical. This sequence is not evidence of a newly introduced 2.3 b1701 regression.",
    "scope": "Historical released source comparison, complete native admission and exact 1.0 pitch iteration in synthetic memory. Does not assert current candidate headers unchanged. No mode1 physics/trajectory simulation, full callback, live key query or current reporter reproduction; no production or game settings changed.",
}
(HERE / "admission_mode1_evidence.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
