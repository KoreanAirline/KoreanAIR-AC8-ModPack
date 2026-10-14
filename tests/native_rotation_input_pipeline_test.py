"""Production input ownership/writeback -> pinned native raw-to-q processor.

Imports the PSM fixture to build the same production ownership and selector
blocks once. Native input instructions run in synthetic Unicorn memory only;
the unrelated throttle helper and finite import are stubbed as in the existing
native adapter validation. No aircraft dynamics or live-flight claim.
"""
from pathlib import Path
import ctypes
import hashlib
import itertools
import json
import struct

import native_psm_input_pipeline_test as pipeline
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_OP_MEM
from capstone.x86_const import X86_REG_RIP
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP, UC_X86_REG_RBP

here = Path(__file__).resolve().parent
runtime = here.parent / 'runtime'
ex = pipeline.Executable(Path('E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe'))
base = ex.base
start, end = base + 0x4D3B680, base + 0x4D3BF93
code = ex.read(start-base, end-start)
prior = json.loads((here.parents[1]/'ac8-mouseflight/responsive/build/native_processor_validation.json').read_text())
assert hashlib.sha256(code).hexdigest() == prior['native_code_sha256']
uc = Uc(UC_ARCH_X86, UC_MODE_64)
pages = set()

def page(address):
    address &= ~4095
    if address not in pages:
        uc.mem_map(address,4096)
        uc.mem_write(address,ex.read(address-base,4096))
        pages.add(address)

md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = True
for address in range(start & ~4095,end,4096):
    page(address)
for ins in md.disasm(code,start):
    for operand in ins.operands:
        if operand.type == CS_OP_MEM and operand.mem.base == X86_REG_RIP:
            address = ins.address+ins.size+operand.mem.disp
            page(address)
            page(address+15)
uc.mem_write(base+0x4D3BFA0,b'\xC3')
STOP,STUB,STACK,STATE,RAW,SET,CTX = 0x500000,0x600000,0x1000000,0x2000000,0x2001000,0x2002000,0x2003000
for address,size in [(STOP,4096),(STUB,4096),(STACK,65536),(STATE,16384)]:
    uc.mem_map(address,size)
uc.mem_write(STUB,b'\xB8\x01\0\0\0\xC3')
uc.mem_write(base+0xAB19CE0,struct.pack('<Q',STUB))

def execute(raw,before,dt,modifier):
    uc.mem_write(STATE,b'\0'*16384)
    uc.mem_write(STATE,struct.pack('<3d',*before))
    uc.mem_write(RAW,struct.pack('<6f',*raw))
    uc.mem_write(SET,struct.pack('<f',1.)*(0x500//4))
    for offset,value in zip([0xE8,0xF0,0xF8,0x100,0x108,0x110],[15,8,10,4,6,5]):
        uc.mem_write(SET+offset,struct.pack('<d',value))
    uc.mem_write(CTX,struct.pack('<QQBB2xIfff',RAW,SET,0,0,0,modifier,0.,dt))
    sp=STACK+65536-4096-8
    uc.mem_write(sp,struct.pack('<Q',STOP))
    for register,value in [(UC_X86_REG_RSP,sp),(UC_X86_REG_RBP,0),(UC_X86_REG_RCX,STATE),(UC_X86_REG_RDX,CTX)]:
        uc.reg_write(register,value)
    uc.emu_start(start,STOP,count=2000)
    return struct.unpack('<3d',uc.mem_read(STATE,24))

dll = pipeline.dll
dll.rotation_packet.argtypes = [ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_float),ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_float,ctypes.c_float,ctypes.POINTER(ctypes.c_float)]
dll.rotation_packet.restype = None
checks=0
worst=0.

def require(ok,label):
    global checks
    checks+=1
    assert ok,label

def select(raw,before,requested,keys=0,enabled=True,looking=False,dt=1/60,modifier=0):
    packet=(ctypes.c_float*6)(*raw)
    q=(ctypes.c_double*3)(*before)
    want=(ctypes.c_float*3)(*requested)
    predicted=(ctypes.c_float*3)()
    dll.rotation_packet(packet,q,want,keys,enabled,looking,True,dt,modifier,predicted)
    sent=list(packet)
    actual=execute(sent,before,dt,modifier)
    global worst
    worst=max(worst,max(abs(actual[i]-predicted[i]) for i in range(3)))
    require(sent[3:]==list((ctypes.c_float*3)(*raw[3:])),'throttle/brake/highG bit-preserved')
    require(max(abs(actual[i]-predicted[i]) for i in range(3))<2e-6,'production selected raw matches exact native q')
    return sent,actual

try:
    # In 1.0's keyboard-only ownership, unheld native rotation never reserved
    # the automatic output. Clean input is an independent equivalent baseline.
    cases=0
    for before,requested,dt,modifier,roll in itertools.product(
        [(0.,0.,0.),(.7,-.3,.4),(-.7,.3,-.4)],
        [(1.,-1.,1.),(-1.,1.,-1.),(0.,0.,0.),(.3,-.2,.4)],
        [1/60,1/120],[0.,.65],[.2,.8,1.]):
        noisy=[.1,0.,roll,.9,.7,.8]
        baseline,qbaseline=select([0.,0.,0.,.9,.7,.8],before,requested,dt=dt,modifier=modifier)
        actual,qactual=select(noisy,before,requested,dt=dt,modifier=modifier)
        require(actual==baseline and qactual==qbaseline,'keys0 .1/.2/.8/fullscale matches 1.0 keyboard-only ownership raw and native q')
        cases+=1
    # Every keyboard-axis combination retains precisely that aggregate axis,
    # including native opposing-key zero, while the other axes keep guidance.
    for keys,rawpitch in itertools.product(range(8),[-1.,0.,1.]):
        raw=[rawpitch,.3125,-.4375,1.,1.,1.]
        sent,_=select(raw,(.3,-.2,.4),(1.,-1.,1.),keys)
        for axis,bit in enumerate([1,4,2]):
            require(sent[axis]==raw[axis] if keys&bit else True,'held WASD/QE axis retains native value')
        looked,qlook=select(raw,(.3,-.2,.4),(1.,-1.,1.),keys,looking=True)
        require(looked==sent,'Alt keeps identical automatic pursuit on unheld axes, with exact native held-axis values')
        off,_=select(raw,(.3,-.2,.4),(1.,-1.,1.),keys,enabled=False,looking=True)
        require(off==raw,'F8 off retains all native controls even during Alt')
    packet=(ctypes.c_float*6)(.1,.2,.8,1,1,1)
    before=(ctypes.c_double*3)(.3,-.2,.4)
    want=(ctypes.c_float*3)(1,-1,1)
    prediction=(ctypes.c_float*3)()
    def retained(enabled,looking,fresh):
        dll.rotation_packet(packet,before,want,0,enabled,looking,fresh,1/60,0,prediction)
        actual=execute(list(packet),list(before),1/60,0)
        require(max(abs(actual[i]-prediction[i]) for i in range(3))<2e-6,'retained packet transitions remain native raw-to-q coherent')
    retained(True,False,True)
    require(packet[0]==1 and packet[1]==-1,'initial automatic outputs retained for downstream physics')
    retained(True,True,False)
    require(packet[0]==1 and packet[1]==-1,'Alt cleans retained RAW then reapplies the same last-goal pursuit without fresh mapping')
    retained(False,True,False)
    require(list(packet)[:3]==list((ctypes.c_float*3)(.1,.2,.8)),'F8 restores original native aggregate after consumed Alt filtering')
    retained(True,False,True)
    require(packet[0]==1 and packet[1]==-1,'Alt release immediately resumes automatic axes without mouse contamination')
    # Fresh release, Alt and resumed guidance consume the same stale-write
    # cleanup and keyboard policy, rather than retaining prior mouse flight.
    source=(runtime/'src/mouse_aim.cpp').read_text(encoding='utf-8')
    processor=source[source.index('uintptr_t __fastcall process_input('):source.index('bool prepare_hook()')]
    require(processor.index('native_raw.begin(')<processor.index('game_paused.load()'),'retained mod writes removed before native-camera/lifecycle early gates')
    require(processor.index('gaze_active.load()')<processor.index('manual_rotation.retain_keyboard('),'native camera scenes return before enabled ownership filter')
    require(processor.index('manual_rotation.retain_keyboard(')<processor.index('sample_player_maneuver(pawn,axes'),'aggregate excluded before PSM snapshot')
    report={'passed':True,'checks':checks,'keys0_baseline_cases':cases,'native_input_runs':cases*2+24*3+4,'max_raw_to_q_error':worst,'source_sha256':hashlib.sha256((runtime/'src/mouse_aim.cpp').read_bytes()).hexdigest(),'ownership_sha256':hashlib.sha256((runtime/'src/manual_rotation_input.h').read_bytes()).hexdigest(),'native_code_sha256':hashlib.sha256(code).hexdigest(),'scope':'Actual production ownership/selector and pinned native input instructions in synthetic memory. Throttle auxiliary helper and finite import stubbed; no dynamics or live-flight claim.'}
    (here/'native_rotation_input_pipeline_evidence.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,separators=(',',':')))
finally:
    ex.close()
