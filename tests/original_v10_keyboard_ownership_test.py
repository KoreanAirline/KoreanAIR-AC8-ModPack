"""Execute the exact released 1.0 DLL's keyboard ownership instructions.

No DLL is loaded into a process. Its input callback's key classifier and raw
selector mask construction run unmodified in synthetic Unicorn memory. Only
GetAsyncKeyState is represented by supplied physical key states.
"""
from pathlib import Path
import hashlib
import itertools
import json
import struct
import sys

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parents[1]/'libs'))
sys.path.insert(0,str(here.parents[1]/'ac8-mouseflight/responsive/tools'))
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RSP
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RCX,UC_X86_REG_RAX,UC_X86_REG_RSP,UC_X86_REG_R14

path=here/'compare_v10_payload/payload/Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/Scripts/ac8_mouse_aim_010.dll'
raw=path.read_bytes()
sha=hashlib.sha256(raw).hexdigest()
assert sha=='8a55cb69ea205570475840129033a25ceeda4c16924090af32d74369bb009b2c'
pe=pefile.PE(data=raw)
base=pe.OPTIONAL_HEADER.ImageBase
function=next(entry.struct for entry in pe.DIRECTORY_ENTRY_EXCEPTION if entry.struct.BeginAddress<=0x14709<entry.struct.EndAddress)
assert (function.BeginAddress,function.EndAddress)==(0x145E0,0x16D46)
cs=Cs(CS_ARCH_X86,CS_MODE_64)
cs.detail=True
instructions=list(cs.disasm(pe.get_data(function.BeginAddress,function.EndAddress-function.BeginAddress),base+function.BeginAddress))
# Stack slots later copied into the actual native raw selector's held-axis
# array have exactly one writer each: the GetAsyncKeyState classifier.
stores=[]
for ins in instructions:
    if not ins.operands:continue
    operand=ins.operands[0]
    if ins.mnemonic=='mov' and operand.type==X86_OP_MEM and operand.mem.base==X86_REG_RSP and operand.mem.disp in [0x50,0x55,0x57]:
        stores.append((ins.address-base,operand.mem.disp))
assert stores==[(0x14733,0x50),(0x14763,0x57),(0x14792,0x55)]

uc=Uc(UC_ARCH_X86,UC_MODE_64)
uc.mem_map(base+0x14000,0x3000)
uc.mem_write(base+0x14000,pe.get_data(0x14000,0x3000))
uc.mem_map(base+0x29000,0x1000)
stub,stack,pawn=0x500000,0x1000000,0x2000000
uc.mem_map(stub,0x1000)
uc.mem_write(stub,b'\xC3')
uc.mem_write(base+0x29328,struct.pack('<Q',stub))
uc.mem_map(stack,0x10000)
uc.mem_map(pawn,0x4000)
pressed=set()
calls=[]

def keyboard(uc,address,size,_):
    if address==stub:
        key=uc.reg_read(UC_X86_REG_RCX)
        calls.append(key)
        uc.reg_write(UC_X86_REG_RAX,0x8000 if key in pressed else 0)

uc.hook_add(UC_HOOK_CODE,keyboard)
checks=0
for states,axis_values in itertools.product(itertools.product([False,True],repeat=6),[(.1,.2,.8),(1.,-1.,1.),(0.,0.,0.)]):
    pressed={key for key,down in zip(map(ord,'WSADQE'),states) if down}
    calls.clear()
    sp=stack+0x8000
    uc.mem_write(sp,b'\xA5'*0x100)
    uc.mem_write(pawn+0x2268,struct.pack('<3f',*axis_values))
    uc.reg_write(UC_X86_REG_RSP,sp)
    uc.reg_write(UC_X86_REG_R14,pawn)
    uc.emu_start(base+0x14709,base+0x14796,count=200)
    # Exact released callback's mask-array construction, with no substituted
    # condition or source-family header.
    uc.emu_start(base+0x1633E,base+0x16359,count=20)
    actual=bytes(uc.mem_read(sp+0x5C,3))
    expected=bytes([states[0] or states[1],states[4] or states[5],states[2] or states[3]])
    assert actual==expected,(states,axis_values,actual,expected)
    assert set(calls)<=set(map(ord,'WSADQE'))
    checks+=1

def disassembly(first,end):
    return [f'{ins.address-base:08X} {ins.mnemonic} {ins.op_str}' for ins in cs.disasm(pe.get_data(first,end-first),base+first)]

report={'passed':True,'cases':checks,'original_dll_sha256':sha,'function_rva':'145E0..16D46','function_sha256':hashlib.sha256(pe.get_data(function.BeginAddress,function.EndAddress-function.BeginAddress)).hexdigest(),'classifier_rva':'14709..14796','selector_mask_rva':'1633E..16359','classifier':disassembly(0x14709,0x14796),'selector_mask':disassembly(0x1633E,0x16359),'mask_writers':stores,'finding':'Exact released 1.0 raw selector held-axis array is only W/S, Q/E, A/D physical key state; arbitrary native raw values never reserve an unheld axis.','scope':'Exact 1.0 DLL instruction subsets in synthetic memory; GetAsyncKeyState supplied by fixture. No complete DLL callback, guidance function or live flight execution.'}
(here/'original_v10_keyboard_ownership_evidence.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(f'PASS exact released 1.0 keyboard ownership: {checks} cases; all 64 physical key combinations × 3 aggregate raw packets; original DLL SHA256 {sha}; original selector masks contain no native-axis-nonzero condition.')
