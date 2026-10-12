"""Execute pinned AC8 player PSM instructions against synthetic memory only.

The complete 4D3F3A0 admission routine runs unmodified. Phase checks execute
4D3F5D0 through 4D3F6ED, stopping before the separate orientation helpers.
No native helper is stubbed, no game process is accessed, and no file is written.
Synthetic settings prove native branch behavior, not live aircraft performance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
from pathlib import Path
import struct
import sys


HERE = Path(__file__).resolve().parent
RESPONSIVE = HERE.parents[1] / "ac8-mouseflight" / "responsive"
sys.path.insert(0, str(RESPONSIVE / "tools"))
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE  # noqa: E402
from unicorn.x86_const import (  # noqa: E402
    UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9,
    UC_X86_REG_RSP, UC_X86_REG_RIP,
)


PINNED_RANGES = (
    ("admission", 0x4D3F3A0, 0x4D3F5CB,
     "89236b998877e58ad79646c27015f58f339be799222ed7cd5536d61694d321b8"),
    ("phase", 0x4D3F5D0, 0x4D3F94C,
     "f8087d28c073de5462ace0749ffff810472eba8557c3881ebcfec64bc2181f0e"),
)
OWNER = 0x2000000
DYNAMICS = OWNER + 0x98
DRIFT = DYNAMICS + 0x70
PROCESSED = OWNER + 0x38
SETTINGS = OWNER + 0x9C0
FLAGS = OWNER + 0x8B0
CONTEXT = 0x2010000
STACK = 0x3000000
STOP = 0x4000000
PHASE_STOP_RVA = 0x4D3F6ED
PROCESSED_SENTINEL = struct.pack("<3d", 0.3125, -0.271, 0.19)


class Executable:
    """Parse the EXE's own section table instead of trusting a saved PE layout."""

    def __init__(self, path: Path):
        self.file = path.open("rb")
        self.bytes = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
        if self.bytes[:2] != b"MZ":
            raise ValueError("Expected a PE executable")
        pe = struct.unpack_from("<I", self.bytes, 0x3C)[0]
        if self.bytes[pe:pe + 4] != b"PE\0\0":
            raise ValueError("Invalid PE signature")
        count = struct.unpack_from("<H", self.bytes, pe + 6)[0]
        optional_size = struct.unpack_from("<H", self.bytes, pe + 20)[0]
        if struct.unpack_from("<H", self.bytes, pe + 24)[0] != 0x20B:
            raise ValueError("Expected a 64-bit PE executable")
        self.base = struct.unpack_from("<Q", self.bytes, pe + 24 + 24)[0]
        self.sections = []
        for index in range(count):
            offset = pe + 24 + optional_size + 40 * index
            virtual, rva, raw_size, raw = struct.unpack_from("<4I", self.bytes, offset + 8)
            self.sections.append((rva, max(virtual, raw_size), raw_size, raw))

    def read(self, rva: int, size: int) -> bytes:
        for start, virtual_size, raw_size, raw in self.sections:
            if start <= rva < start + virtual_size:
                relative = rva - start
                available = max(0, min(size, raw_size - relative))
                return self.bytes[raw + relative:raw + relative + available].ljust(size, b"\0")
        raise ValueError(f"RVA outside executable sections: {rva:x}")

    def close(self):
        self.bytes.close()
        self.file.close()


class NativeFixture:
    def __init__(self, executable: Executable, *, capability=1, previous_pitch=0.0,
                 pitch=0.7, throttle=1.0, brake=1.0, high_g=0.0,
                 speed=100.0, flags=0, native_button=True, yaw=0.0, roll=0.0):
        self.executable = executable
        self.uc = Uc(UC_ARCH_X86, UC_MODE_64)
        self.phase_stop = False
        self.visited = set()
        # Only code and constant pages read by these native instructions.
        self._native_pages(0x4D3F000, 0x4D40000)
        self._native_pages(0xD2A8000, 0xD2B4000)
        for address, size in ((OWNER, 0x4000), (CONTEXT, 0x1000),
                              (STACK, 0x10000), (STOP, 0x1000)):
            self.uc.mem_map(address, size)
        self.uc.hook_add(UC_HOOK_CODE, self._instruction)
        self.uc.mem_write(PROCESSED, PROCESSED_SENTINEL)
        self.uc.mem_write(CONTEXT, struct.pack("<QQQ", OWNER, PROCESSED, SETTINGS))
        self.uc.mem_write(CONTEXT + 0x1A, bytes([int(native_button)]))
        self.float(CONTEXT + 0x20, 1.0 / 60.0)
        self.float(DYNAMICS + 0x18, speed)
        self.float(DRIFT + 0x14, 0.1)  # Native drift deadzone, disclosed synthetic setting.
        self.float(DRIFT + 0x18, 0.1)
        self.float(DRIFT + 0x38, previous_pitch)
        self.float(SETTINGS + 0x380, 1.0)
        self.float(SETTINGS + 0x38C, 1.0)
        self.float(SETTINGS + 0x3D0, 200.0)  # Synthetic PSM admission speed limit.
        self.float(SETTINGS + 0x444, 10.0)
        self.uc.mem_write(SETTINGS + 0x3CC, bytes([capability]))
        self.uc.mem_write(FLAGS, struct.pack("<I", flags))
        self.input(pitch, throttle=throttle, brake=brake, high_g=high_g, yaw=yaw, roll=roll)

    def _native_pages(self, first: int, end: int):
        for rva in range(first, end, 0x1000):
            self.uc.mem_map(self.executable.base + rva, 0x1000)
            self.uc.mem_write(self.executable.base + rva, self.executable.read(rva, 0x1000))

    def _instruction(self, uc, address, size, _):
        self.visited.add(address - self.executable.base)
        if self.phase_stop and address == self.executable.base + PHASE_STOP_RVA:
            uc.emu_stop()

    def float(self, address: int, value: float):
        self.uc.mem_write(address, struct.pack("<f", value))

    def input(self, pitch: float, *, throttle=1.0, brake=1.0, high_g=0.0, yaw=0.0, roll=0.0):
        self.uc.mem_write(OWNER, struct.pack("<6f", pitch, yaw, roll, throttle, brake, high_g))

    def read_float(self, address: int) -> float:
        return struct.unpack("<f", self.uc.mem_read(address, 4))[0]

    @property
    def mode(self):
        return self.uc.mem_read(DRIFT + 0x1D, 1)[0]

    @property
    def phase(self):
        return self.uc.mem_read(DRIFT + 0x1E, 1)[0]

    def execute(self, start: int, *, phase_prefix=False):
        self.phase_stop = phase_prefix
        self.visited.clear()
        sp = STACK + 0xFF00 - 8
        self.uc.mem_write(sp, struct.pack("<Q", STOP))
        self.uc.mem_write(sp + 0x28, struct.pack("<Q", FLAGS))
        self.uc.reg_write(UC_X86_REG_RSP, sp)
        self.uc.reg_write(UC_X86_REG_RCX, DRIFT)
        self.uc.reg_write(UC_X86_REG_RDX, OWNER)
        self.uc.reg_write(UC_X86_REG_R8, CONTEXT)
        self.uc.reg_write(UC_X86_REG_R9, DYNAMICS)
        before = bytes(self.uc.mem_read(PROCESSED, 24))
        raw_before = bytes(self.uc.mem_read(OWNER, 24))
        self.uc.emu_start(self.executable.base + start, STOP, count=2000)
        expected_end = self.executable.base + PHASE_STOP_RVA if phase_prefix else STOP
        assert self.uc.reg_read(UC_X86_REG_RIP) == expected_end, "Native execution did not reach the declared stop"
        assert bytes(self.uc.mem_read(PROCESSED, 24)) == before, "Native admission/phase changed processed q"
        assert bytes(self.uc.mem_read(OWNER, 24)) == raw_before, "Native admission/phase changed raw axes"

    def admission(self):
        self.execute(0x4D3F3A0)
        return self.mode

    def phase_prefix(self, *, phase, pitch, angle, total_angle=0.0):
        self.uc.mem_write(DRIFT + 0x1D, bytes([2, phase]))
        self.input(pitch)
        self.float(DRIFT + 0x44, angle)
        self.float(DRIFT + 0x48, total_angle)
        self.float(DRIFT + 0x50, 0.0)
        self.execute(0x4D3F5D0, phase_prefix=True)
        assert self.mode == 2, "Phase prefix unexpectedly changed PSM mode"
        return self.phase


def run(executable: Executable):
    tests = []

    def check(name: str, condition: bool):
        assert condition, name
        tests.append(name)

    # This path proves the genuine history-store instruction between inputs,
    # rather than resetting previous_pitch in the Python test implementation.
    fixture = NativeFixture(executable, previous_pitch=0.4)
    check("positive_history_blocks_entry", fixture.admission() == 0)
    fixture.input(0.0)
    check("native_neutral_stores_pitch_history", fixture.admission() == 0
          and 0x4D3F56A in fixture.visited and fixture.read_float(DRIFT + 0x38) == 0.0)
    fixture.input(0.7)
    check("next_positive_input_enters_psm", fixture.admission() == 2 and fixture.phase == 1)
    check("admission_does_not_need_special_dispatch_flags", struct.unpack("<I", fixture.uc.mem_read(FLAGS, 4))[0] == 0)
    check("direct_psm_does_not_need_raw_high_g", NativeFixture(executable, high_g=0.0).admission() == 2)
    check("admission_preserves_nonzero_raw_yaw_roll", NativeFixture(executable, yaw=-0.33, roll=0.25).admission() == 2)
    check("native_button_false_blocks_entry", NativeFixture(executable, native_button=False).admission() == 0)
    check("pitch_zero_blocks_entry", NativeFixture(executable, pitch=0.0).admission() == 0)
    check("throttle_below_native_gate_blocks_entry", NativeFixture(executable, throttle=0.8).admission() == 0)
    check("brake_below_native_gate_blocks_entry", NativeFixture(executable, brake=0.8).admission() == 0)
    check("capability_disabled_blocks_entry", NativeFixture(executable, capability=0).admission() == 0)
    check("native_speed_gate_blocks_entry", NativeFixture(executable, speed=201.0).admission() == 0)
    for bit in (18, 19):
        check(f"flag_{bit}_blocks_entry", NativeFixture(executable, flags=1 << bit).admission() == 0)
    excluded = NativeFixture(executable, flags=1 << 6, previous_pitch=0.4, pitch=0.0)
    history = bytes(excluded.uc.mem_read(DRIFT + 0x38, 4))
    check("flag_6_skips_history_update", excluded.admission() == 0
          and 0x4D3F56A not in excluded.visited
          and bytes(excluded.uc.mem_read(DRIFT + 0x38, 4)) == history)
    excluded = NativeFixture(executable, flags=1 << 5, previous_pitch=0.4, pitch=0.0)
    excluded.float(SETTINGS + 0x384, 150.0)
    history = bytes(excluded.uc.mem_read(DRIFT + 0x38, 4))
    check("flag_5_below_generic_speed_gate_skips_history_update", excluded.admission() == 0
          and 0x4D3F56A not in excluded.visited
          and bytes(excluded.uc.mem_read(DRIFT + 0x38, 4)) == history)
    for label, capability, flags in (("capability_zero", 0, 0), ("flag_18", 1, 1 << 18), ("flag_19", 1, 1 << 19)):
        excluded = NativeFixture(executable, capability=capability, flags=flags, previous_pitch=0.4, pitch=0.0)
        history = bytes(excluded.uc.mem_read(DRIFT + 0x38, 4))
        check(label + "_skips_history_update", excluded.admission() == 0
              and 0x4D3F56A not in excluded.visited
              and bytes(excluded.uc.mem_read(DRIFT + 0x38, 4)) == history)
    equal_gate = NativeFixture(executable, flags=1 << 5, previous_pitch=0.4, pitch=0.0)
    equal_gate.float(SETTINGS + 0x384, 100.0)
    check("generic_speed_equality_updates_history", equal_gate.admission() == 0
          and 0x4D3F56A in equal_gate.visited and equal_gate.read_float(DRIFT + 0x38) == 0.0)
    unordered_gate = NativeFixture(executable, flags=1 << 5, previous_pitch=0.4, pitch=0.0)
    unordered_gate.float(SETTINGS + 0x384, float("nan"))
    check("unordered_generic_minimum_updates_history", unordered_gate.admission() == 0
          and 0x4D3F56A in unordered_gate.visited and unordered_gate.read_float(DRIFT + 0x38) == 0.0)

    cobra = NativeFixture(executable, capability=1)
    kulbit = NativeFixture(executable, capability=2)
    check("cobra_and_kulbit_share_mode_2", cobra.admission() == kulbit.admission() == 2)
    check("zero_release_does_not_reverse_or_cancel_early_pull", cobra.phase_prefix(phase=1, pitch=0.0, angle=80.0) == 1)
    check("positive_input_finishes_phase_2", cobra.phase_prefix(phase=2, pitch=0.7, angle=100.0) == 0)
    check("zero_s_release_retains_phase_2_before_native_angle_gate", cobra.phase_prefix(phase=2, pitch=0.0, angle=100.0) == 2)
    check("zero_s_release_advances_phase_2_at_native_angle_gate", cobra.phase_prefix(phase=2, pitch=0.0, angle=200.0) == 0)
    check("native_negative_cancel_enters_phase_2", cobra.phase_prefix(phase=1, pitch=-0.7, angle=80.0) == 2)
    check("cobra_profile_finishes_after_pull", cobra.phase_prefix(phase=1, pitch=0.0, angle=110.0) == 0)
    check("kulbit_profile_continues_rotation", kulbit.phase_prefix(phase=1, pitch=0.0, angle=110.0) == 3)
    check("kulbit_zero_release_retains_phase_3_before_full_rotation", kulbit.phase_prefix(phase=3, pitch=0.0, angle=110.0, total_angle=180.0) == 3)
    check("kulbit_phase_3_finishes_at_full_rotation", kulbit.phase_prefix(phase=3, pitch=0.0, angle=110.0, total_angle=250.0) == 0)
    return tests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=Path(
        "E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe"))
    args = parser.parse_args()
    executable = Executable(args.exe)
    try:
        fingerprints = {}
        for name, first, end, expected in PINNED_RANGES:
            code = executable.read(first, end - first)
            actual = hashlib.sha256(code).hexdigest()
            assert actual == expected, f"Unpinned native {name} instructions; test refused"
            fnv = 14695981039346656037
            for byte in code:
                fnv = ((fnv ^ byte) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
            fingerprints[name] = {"rva": f"{first:X}..{end:X}", "sha256": actual, "fnv1a64": f"{fnv:016x}"}
        tests = run(executable)
        print(json.dumps({
            "passed": True, "tests": len(tests), "checks": tests,
            "fingerprints": fingerprints,
            "processed_q_unchanged_in_every_native_run": True,
            "raw_axes_unchanged_in_every_native_run": True,
            "scope": "Unmodified full native admission and native phase prefix; synthetic memory/settings, no orientation helpers or live flight. EXE opened read-only; no game process or file writes.",
        }, separators=(",", ":")))
    finally:
        executable.close()


if __name__ == "__main__":
    main()
