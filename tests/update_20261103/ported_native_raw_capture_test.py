"""Check pinned native raw-input capture and relocated mapper instructions.

The installed EXE is opened read-only. All execution uses synthetic Unicorn
memory. The complete native mapper and admission routine run unmodified; the
mapper trampoline relocates only the verified memory MOVSS in its first 19
bytes. Caller ranges establish synchronous call order by their actual machine
instructions. This does not execute the complete flight physics or a game.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import struct
import sys

sys.dont_write_bytecode = True
from ported_native_player_maneuver_test import (  # noqa: E402
    Executable, NativeFixture, OWNER, PROCESSED, DRIFT,
)
from capstone import Cs, CS_ARCH_X86, CS_MODE_64  # noqa: E402
from capstone.x86_const import X86_OP_IMM, X86_OP_MEM, X86_REG_RIP  # noqa: E402
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE  # noqa: E402
from unicorn.x86_const import (  # noqa: E402
    UC_X86_REG_RAX, UC_X86_REG_RBX, UC_X86_REG_RCX, UC_X86_REG_RDX,
    UC_X86_REG_RSI, UC_X86_REG_RDI, UC_X86_REG_RBP, UC_X86_REG_RSP,
    UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_R10, UC_X86_REG_R11,
    UC_X86_REG_R12, UC_X86_REG_R13, UC_X86_REG_R14, UC_X86_REG_R15,
    UC_X86_REG_EFLAGS, UC_X86_REG_RIP, UC_X86_REG_XMM0,
)

MAPPER_RVA = 0x4d22fe0
MAPPER_END = 0x4d2313a
INPUT = 0x2010000
STACK = 0x3000000
STOP = 0x4000000
TRAMPOLINE = 0x5000000
ENTRY_STUB = 0x5010000
CLOBBER_HELPER = 0x5020000
PREFIX = bytes.fromhex("48 83 ec 38 f6 42 18 01 0f 57 c9 f3 0f 10 05 bd c6 2c 07")
PINNED_RANGES = (
    ("mapper", MAPPER_RVA, MAPPER_END,
     "a9dfb52c14597844ffb50e8aa397e82291b7d146a4f2c54ea9e724c3f0b4a807"),
    ("player_packet", 0x7d535e4, 0x7d53605,
     "29fb56393d041bd9adde12abb5ffa3a7d32048013460bfea3a9d91ddda4ac802"),
    ("player_packet_alternate", 0x7d5f32f, 0x7d5f3c6,
     "fd2197648e77b1971a9b39c690b31b9d596f9ace46d0caedcc2ef71b5c2f0316"),
    ("mapper_shared_rcx_caller", 0x7d539aa, 0x7d539b8,
     "781f0bb84c2d42fd8d6e4326e41b44299522ae22251fb6d36d33a9d5909cb602"),
    ("simulation_call", 0x4d23330, 0x4d23343,
     "f037fd800cf43b619f83bece715847be40e79a1e251b00dcced2afa2f3229dcd"),
    ("input_then_physics", 0x4d25368, 0x4d25427,
     "8d67b732e88c83b12b8606efefb99d1f571f199c1a4f1d72a59784cc630976a0"),
    ("physics_to_player_maneuver", 0x4d30932, 0x4d30949,
     "563a1b206f85fe7b36dfeda23ec74c1cc6885a22c9c26759ccc66d3d23396fa0"),
    ("admission", 0x4d2fd60, 0x4d2ff8b,
     "b41a5a8f04bea529e8863c05e544e6bbccaadf1ed71c5c5c51346f98bab9ad4a"),
    ("brake_neutral_gate", 0x7d4ee60, 0x7d4ee73,
     "0dbb1273603ee307bb213c47ae232b7c3d3d79dcf3c4d8473f3183128868d020"),
    ("brake_neutral_timer", 0x7d45bba, 0x7d45bec,
     "d5dd2932d14dd42c402c01b00874ba51f2168b7c13bfa1f2f3be650b0e930f33"),
    ("native_device_packet", 0x7d582d0, 0x7d58420,
     "862c73b63a04e5202ffaf9fe53ebffe480b0f85781380e7c126cac16d10d7c68"),
)
GENERAL_REGISTERS = (
    UC_X86_REG_RAX, UC_X86_REG_RBX, UC_X86_REG_RCX, UC_X86_REG_RDX,
    UC_X86_REG_RSI, UC_X86_REG_RDI, UC_X86_REG_RBP, UC_X86_REG_RSP,
    UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_R10, UC_X86_REG_R11,
    UC_X86_REG_R12, UC_X86_REG_R13, UC_X86_REG_R14, UC_X86_REG_R15,
)
COMPARE_REGISTERS = GENERAL_REGISTERS + (UC_X86_REG_EFLAGS,) + tuple(
    UC_X86_REG_XMM0 + index for index in range(16)
)


class MapperFixture:
    def __init__(self, executable, decoder, *, flags=0, state=0.0,
                 packet_flags=0, preparation=False, pitch=-0.375):
        self.executable = executable
        self.uc = Uc(UC_ARCH_X86, UC_MODE_64)
        self.pages = set(range((executable.base + MAPPER_RVA) & ~0xFFF, (executable.base + MAPPER_END + 0xFFF) & ~0xFFF, 0x1000))
        mapper = executable.read(MAPPER_RVA, MAPPER_END - MAPPER_RVA)
        for instruction in decoder.disasm(mapper, executable.base + MAPPER_RVA):
            for operand in instruction.operands:
                if operand.type == X86_OP_MEM and operand.mem.base == X86_REG_RIP:
                    address = instruction.address + instruction.size + operand.mem.disp
                    self.pages.add(address & ~0xFFF)
        for page in self.pages:
            self.uc.mem_map(page, 0x1000)
            self.uc.mem_write(page, executable.read(page - executable.base, 0x1000))
        for address, size in ((OWNER, 0x4000), (INPUT, 0x1000),
                              (STACK, 0x10000), (STOP, 0x1000),
                              (TRAMPOLINE, 0x1000), (ENTRY_STUB, 0x1000),
                              (CLOBBER_HELPER, 0x1000)):
            self.uc.mem_map(address, size)
        # Preserve test flags, RAX, and legacy memory MOVSS lane semantics.
        self.trampoline = (
            PREFIX[:11] + b"\x50\x48\xb8"
            + struct.pack("<Q", executable.base + 0xbfef6b0)
            + b"\xf3\x0f\x10\x00\x58\xff\x25\0\0\0\0"
            + struct.pack("<Q", executable.base + MAPPER_RVA + len(PREFIX))
        )
        self.uc.mem_write(TRAMPOLINE, self.trampoline)
        # This is the runtime entry marker design, not a replacement native
        # mapper: save caller state, call a synthetic deliberately hostile
        # ABI-conforming helper, restore it, and tail-jump to native mapping.
        self.entry_stub = bytearray(bytes.fromhex("9c 50 51 52 41 50 41 51 41 52 41 53 48 81 ec 88 00 00 00"))
        for index in range(6):
            self.entry_stub += bytes((0xF3, 0x0F, 0x7F, 0x44 + 8 * index, 0x24, 0x20 + 16 * index))
        self.entry_stub += bytes.fromhex("48 8b 8c 24 b0 00 00 00 48 b8")
        self.entry_stub += struct.pack("<Q", CLOBBER_HELPER) + bytes.fromhex("ff d0")
        for index in range(6):
            self.entry_stub += bytes((0xF3, 0x0F, 0x6F, 0x44 + 8 * index, 0x24, 0x20 + 16 * index))
        self.entry_stub += bytes.fromhex("48 81 c4 88 00 00 00 41 5b 41 5a 41 59 41 58 5a 59 58 9d ff 25 00 00 00 00")
        self.entry_stub += struct.pack("<Q", executable.base + MAPPER_RVA)
        self.uc.mem_write(ENTRY_STUB, bytes(self.entry_stub))
        hostile = bytearray()
        for index, opcode in enumerate((b"\x48\xb8", b"\x48\xb9", b"\x48\xba",
                                        b"\x49\xb8", b"\x49\xb9", b"\x49\xba", b"\x49\xbb")):
            hostile += opcode + struct.pack("<Q", 0xBAD0000000000000 + index)
        for index in range(6):
            hostile += bytes((0x66, 0x0F, 0xEF, 0xC0 + 9 * index))
        hostile += bytes.fromhex("31 c0 c3")  # Deliberately alter flags as well.
        self.uc.mem_write(CLOBBER_HELPER, bytes(hostile))
        self.helper_calls = []
        self.uc.hook_add(UC_HOOK_CODE, self.observe_helper)
        self.uc.mem_write(INPUT, struct.pack("<6fB", pitch, -0.625, 0.875,
                                            0.9, 0.7, 0.8, packet_flags))
        self.uc.mem_write(OWNER, struct.pack("<6fB", 1.0, -0.9, 0.6,
                                            0.2, 0.1, 0.3, 0xFF))
        self.float(OWNER + 0x89C, 0.0)
        self.uc.mem_write(OWNER + 0x8B0, struct.pack("<I", flags))
        self.float(OWNER + 0xD4, state)
        self.float(OWNER + 0xD8, 0.4)
        self.uc.mem_write(OWNER + 0xDD, bytes([int(preparation)]))
        self.float(OWNER + 0xB0, 0.5)
        self.float(OWNER + 0x9C8, 1.0)
        self.float(OWNER + 0x68, 0.0)
        for index, register in enumerate(GENERAL_REGISTERS):
            self.uc.reg_write(register, 0x1234567812340000 + 0x80 * index)
        for index in range(16):
            self.uc.reg_write(UC_X86_REG_XMM0 + index,
                              0x9876543210FEDCBA1234567890ABCDEF + index)
        self.uc.reg_write(UC_X86_REG_EFLAGS, 0x246)
        self.prepare_call()

    def float(self, address, value):
        self.uc.mem_write(address, struct.pack("<f", value))

    def observe_helper(self, uc, address, size, _):
        if address == CLOBBER_HELPER:
            assert uc.reg_read(UC_X86_REG_RCX) == OWNER, "Entry stub supplied the wrong raw owner"
            assert uc.reg_read(UC_X86_REG_RSP) & 15 == 8, "Marker helper stack violated x64 alignment"
            self.helper_calls.append(address)

    def prepare_call(self):
        self.uc.reg_write(UC_X86_REG_RSP, STACK + 0xF008)
        self.uc.mem_write(STACK + 0xF008, struct.pack("<Q", STOP))
        self.uc.reg_write(UC_X86_REG_RCX, OWNER)
        self.uc.reg_write(UC_X86_REG_RDX, INPUT)

    def execute(self, *, trampoline=False, prefix_only=False, entry_stub=False, entry_only=False):
        entry = ENTRY_STUB if entry_stub else TRAMPOLINE if trampoline else self.executable.base + MAPPER_RVA
        end = self.executable.base + MAPPER_RVA if entry_only else (
            self.executable.base + MAPPER_RVA + len(PREFIX) if prefix_only else STOP)
        if entry_only and not entry_stub:
            return self.snapshot()
        self.uc.emu_start(entry, end, count=10000)
        assert self.uc.reg_read(UC_X86_REG_RIP) == end
        if entry_stub:
            assert len(self.helper_calls) == 1, "Entry marker helper did not execute exactly once"
        return self.snapshot()

    def snapshot(self):
        return bytes(self.uc.mem_read(OWNER, 25)), tuple(
            self.uc.reg_read(register) for register in COMPARE_REGISTERS)


def run(executable):
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    decoder.detail = True
    tests = []
    fingerprints = {}

    def check(name, condition):
        assert condition, name
        tests.append(name)

    for name, first, end, expected in PINNED_RANGES:
        actual = hashlib.sha256(executable.read(first, end - first)).hexdigest()
        check("pinned_" + name, actual == expected)
        fingerprints[name] = {"rva": f"{first:X}..{end:X}", "sha256": actual}
    check("verified_complete_19_byte_prefix", executable.read(MAPPER_RVA, 19) == PREFIX)
    check("relocated_movss_sign_mask", executable.read(0xbfef6b0, 4) == b"\0\0\0\x80")

    instructions = {}
    for name, first, end, _ in PINNED_RANGES:
        instructions[name] = list(decoder.disasm(executable.read(first, end - first),
                                               executable.base + first))

    def calls(name):
        return [instruction.operands[0].imm - executable.base
                for instruction in instructions[name]
                if instruction.mnemonic == "call"
                and instruction.operands[0].type == X86_OP_IMM]

    check("player_mapper_then_simulation", calls("player_packet") == [0x4d22fe0, 0x4D23140])
    check("alternate_mapper_then_simulation", calls("player_packet_alternate") == [0x4d22fe0, 0x4D23140])
    check("caller_depends_on_preserved_rcx", calls("mapper_shared_rcx_caller") == [0x4d22fe0, 0x4D23140]
          and [instruction.mnemonic for instruction in instructions["mapper_shared_rcx_caller"]]
          == ["call", "movaps", "call"])
    check("simulation_calls_native_frame", calls("simulation_call") == [0x4D25260])
    check("input_processor_precedes_physics", calls("input_then_physics") == [0x4d2c040, 0x4D30370])
    check("physics_calls_player_maneuver", calls("physics_to_player_maneuver") == [0x4d2f960])
    check("native_player_owner_offset", instructions["player_packet"][0].op_str == "rcx, [rsi + 0x2268]")
    check("alternate_native_player_owner_offset", instructions["player_packet_alternate"][0].op_str == "rcx, [rbx + 0x2268]")
    check("native_gate_vtable_target", struct.unpack("<Q", executable.read(0xcbf0200, 8))[0]
          == executable.base + 0x7d4ee60)
    timer_name = b"PostStallManeuverNeutralLengthTime\0"
    check("native_timer_metadata_name", executable.read(0xcbf5bf8, len(timer_name)) == timer_name)
    check("native_timer_metadata_offset", struct.unpack("<I", executable.read(0xcbed2fa, 4))[0]
          == 0x1174)
    packet_instructions = {instruction.address - executable.base: instruction
                           for instruction in instructions["native_device_packet"]}
    check("native_brake_source_and_packet_destination",
          packet_instructions[0x7d58382].op_str == "xmm0, dword ptr [rcx + 0xfe8]"
          and packet_instructions[0x7d58392].op_str == "dword ptr [rdx + 0x10], xmm0")

    gate_fixture = MapperFixture(executable, decoder)
    for page_rva in (0x7d4e000, 0xe510000, 0x7d45000):
        gate_fixture.uc.mem_map(executable.base + page_rva, 0x1000)
        gate_fixture.uc.mem_write(executable.base + page_rva,
                                 executable.read(page_rva, 0x1000))
    check("native_gate_zero_constant", executable.read(0xe51085c, 4) == b"\0" * 4)
    for remaining, expected_gate in ((0.4, 1), (0.0, 0), (-0.4, 0), (float("nan"), 1)):
        gate_fixture.prepare_call()
        gate_fixture.float(OWNER + 0x1178, remaining)
        gate_fixture.uc.reg_write(UC_X86_REG_RCX, OWNER + 0xF48)
        gate_fixture.uc.emu_start(executable.base + 0x7d4ee60, STOP, count=100)
        assert gate_fixture.uc.reg_read(UC_X86_REG_RAX) & 0xFF == expected_gate
    check("native_gate_is_timer_predicate_including_unordered", True)
    for brake, remaining, expected_remaining in ((0.0, 0.4, 1.0), (1.0, 0.4, 0.3),
                                                  (1.0, 0.05, 0.0)):
        gate_fixture.float(OWNER + 0xFE8, brake)
        gate_fixture.float(OWNER + 0x1174, 1.0)
        gate_fixture.float(OWNER + 0x1178, remaining)
        gate_fixture.uc.reg_write(UC_X86_REG_RDI, OWNER)
        gate_fixture.uc.reg_write(UC_X86_REG_XMM0 + 8, 0)
        gate_fixture.uc.reg_write(UC_X86_REG_XMM0 + 7,
                                 struct.unpack("<I", struct.pack("<f", 0.1))[0])
        gate_fixture.uc.emu_start(executable.base + 0x7d45bba,
                                 executable.base + 0x7d45bec, count=100)
        actual_remaining = struct.unpack("<f", gate_fixture.uc.mem_read(OWNER + 0x1178, 4))[0]
        assert abs(actual_remaining - expected_remaining) < 1e-6
    check("native_brake_resets_or_decrements_grace_timer", True)

    # Inspect native stores rather than assuming that raw floats are regenerated.
    stores = []
    for instruction in instructions["mapper"]:
        if instruction.mnemonic != "movss" or not instruction.operands:
            continue
        operand = instruction.operands[0]
        if operand.type == X86_OP_MEM and instruction.op_str.startswith("dword ptr [rcx"):
            stores.append(operand.mem.disp)
    check("native_mapper_stores_every_raw_float", stores == [0, 4, 8, 12, 16, 20])

    cases = 0
    for flags, state, packet_flags, preparation in itertools.product(
            (0, 1 << 19, 1 << 23, 1 << 24),
            (0.0, 1.0, float("nan")), (0, 1), (False, True)):
        arguments = dict(flags=flags, state=state,
                         packet_flags=packet_flags, preparation=preparation)
        for prefix_only in (False, True):
            original = MapperFixture(executable, decoder, **arguments).execute(prefix_only=prefix_only)
            relocated = MapperFixture(executable, decoder, **arguments).execute(
                trampoline=True, prefix_only=prefix_only)
            assert original == relocated, (arguments, prefix_only)
            marked = MapperFixture(executable, decoder, **arguments).execute(
                entry_stub=True, prefix_only=prefix_only)
            assert original == marked, ("entry_stub", arguments, prefix_only)
        untouched_entry = MapperFixture(executable, decoder, **arguments).snapshot()
        marked_entry = MapperFixture(executable, decoder, **arguments).execute(entry_stub=True, entry_only=True)
        assert untouched_entry == marked_entry, ("entry_state", arguments)
        cases += 1
    check("relocated_prefix_and_full_mapper_match_48_cases", cases == 48)
    check("entry_marker_stub_preserves_flags_all_registers_xmm_lanes", cases == 48)
    check("entry_marker_then_native_mapper_matches_native_return_contract", cases == 48)

    fixture = MapperFixture(executable, decoder, pitch=-0.375)
    raw, registers = fixture.execute()
    expected = struct.pack("<6fB", 0.375, 0.625, -0.875, 0.9, 0.7, 0.8, 0)
    check("native_device_replaces_prior_mod_values", raw == expected)
    check("mapper_preserves_native_rcx_rdx_contract",
          registers[COMPARE_REGISTERS.index(UC_X86_REG_RCX)] == OWNER
          and registers[COMPARE_REGISTERS.index(UC_X86_REG_RDX)] == INPUT)
    # A real held or remapped device may legitimately equal the prior mod pitch.
    fixture.uc.mem_write(OWNER, struct.pack("<6f", 0.375, -1.0, 1.0, 0.0, 0.0, 0.0))
    fixture.prepare_call()
    check("fresh_equal_pitch_still_rewrites_other_axes", fixture.execute()[0] == expected)
    fixture.uc.mem_write(OWNER, struct.pack("<3f", 1.0, -0.9, 0.6))
    fixture.float(INPUT, 0.0)
    fixture.prepare_call()
    released = fixture.execute()[0]
    check("native_release_replaces_persisted_mod_pitch", struct.unpack("<f", released[:4])[0] == 0.0)

    # Execute native admission with a mouse-selected pitch still in the raw block.
    # The complete frame/physics is not emulated: its pinned call order above
    # shows why restoring raw immediately after input processing is premature.
    admitted = NativeFixture(executable, previous_pitch=0.0, pitch=0.0,
                             throttle=1.0, brake=1.0)
    native_snapshot = bytes(admitted.uc.mem_read(OWNER, 24))
    admitted.input(0.7, throttle=1.0, brake=1.0, yaw=-0.4, roll=0.25)
    sent = bytes(admitted.uc.mem_read(OWNER, 24))
    q_before = bytes(admitted.uc.mem_read(PROCESSED, 24))
    check("downstream_admission_reads_live_selected_pitch", admitted.admission() == 2)
    check("native_admission_keeps_sent_raw_axes", bytes(admitted.uc.mem_read(OWNER, 24)) == sent)
    check("native_admission_keeps_processed_q", bytes(admitted.uc.mem_read(PROCESSED, 24)) == q_before)
    early_restore = NativeFixture(executable, previous_pitch=0.0, pitch=0.7,
                                 throttle=1.0, brake=1.0)
    early_restore.uc.mem_write(OWNER, native_snapshot)
    check("early_raw_restore_removes_native_admission_edge", early_restore.admission() == 0)

    eligible_press = NativeFixture(executable, previous_pitch=0.7, pitch=0.7,
                                   native_button=True)
    check("positive_automatic_history_blocks_actual_positive_press", eligible_press.admission() == 0)
    eligible_press.input(0.0)
    check("eligible_native_neutral_step_updates_history", eligible_press.admission() == 0
          and eligible_press.read_float(DRIFT + 0x38) == 0.0)
    eligible_press.input(0.7)
    check("subsequent_actual_positive_press_uses_native_admission", eligible_press.admission() == 2)
    expired_press = NativeFixture(executable, previous_pitch=0.7, pitch=0.7,
                                  native_button=False)
    expired_raw = bytes(expired_press.uc.mem_read(OWNER, 24))
    check("expired_native_timer_blocks_admission_preserves_physical_pitch", expired_press.admission() == 0
          and bytes(expired_press.uc.mem_read(OWNER, 24)) == expired_raw)
    # The native timer is an admission gate, not a history-store gate; the
    # runtime repair policy must require it explicitly before selecting zero.
    expired_press.input(0.0)
    check("expired_timer_still_updates_history_and_cannot_enter", expired_press.admission() == 0
          and expired_press.read_float(DRIFT + 0x38) == 0.0)
    expired_press.input(0.7)
    check("expired_timer_blocks_next_positive_edge", expired_press.admission() == 0)
    return {
        "passed": True, "tests": len(tests), "checks": tests,
        "mapper_equivalence_cases": cases, "prefix_and_full_runs": cases * 6,
        "entry_marker_state_checks": cases,
        "fingerprints": fingerprints,
        "prefix_19_bytes": PREFIX.hex(" "),
        "mapper_constant_rva": "C004590",
        "physics_gate": {"source": "owner+860 (pawn+F48) vtable+50",
                         "getter_rva": "7D5F560", "timer_offset": "pawn+1178",
                         "reset_duration_offset": "pawn+1174",
                         "reset_duration_property": "PostStallManeuverNeutralLengthTime",
                         "meaning": "Brake-neutral grace timer predicate, not an extra PSM key."},
        "boundary": "Mark a native mapper generation and capture its mapped floats before the first subsequent mod input write, or capture immediately after mapper while preserving its complete native return register contract. A verified caller reuses RCX without reload. Retain selected raw inputs through subsequent physics; never infer fresh native input from equality with a prior mod write.",
        "scope": "Pinned EXE read-only; exact native mapper, exact relocated prefix, exact full native admission in synthetic memory. Caller fingerprints verify direct synchronous order. No complete flight physics, game process, live device sampling or live Cobra success claim.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, default=Path(
        "E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe"))
    arguments = parser.parse_args()
    executable = Executable(arguments.exe)
    try:
        print(json.dumps(run(executable), separators=(",", ":")))
    finally:
        executable.close()


if __name__ == "__main__":
    main()
