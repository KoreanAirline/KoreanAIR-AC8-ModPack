"""Build independent Windows ABI/unwind execution against the production header.

Reads pinned game code, immutable constants and actual PE exception metadata.
Executes copied admission in synthetic memory only. Does not access the game.
"""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
from native_player_maneuver_test import Executable

HERE=Path(__file__).resolve().parent
RUNTIME=HERE.parent/'runtime'
BUILD=HERE/'native_psm_abi_build'
BUILD.mkdir(exist_ok=True)
exe=Executable(Path('E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe'))
first=0x4d3f3a0
code=exe.read(first,0x22b)
assert hashlib.sha256(code).hexdigest()=='89236b998877e58ad79646c27015f58f339be799222ed7cd5536d61694d321b8'
pe=struct.unpack_from('<I',exe.bytes,0x3c)[0]
pdata_rva,pdata_size=struct.unpack_from('<II',exe.bytes,pe+24+112+3*8)
pdata=exe.read(pdata_rva,pdata_size)
entries=[struct.unpack_from('<III',pdata,n) for n in range(0,len(pdata)-11,12)]
native_entries=[]
for start,end in ((first,first+0x58),(first+0x58,first+0x21f),(first+0x21f,first+0x22b)):
    native_entries.append(next(e for e in entries if e[:2]==(start,end)))
infos=[exe.read(entry[2],size) for entry,size in zip(native_entries,(16,20,16))]
constants=[]
literal_rvas=[]
for offset in (0x4e,0x70,0x9d,0xad,0xb9,0xe3):
    displacement=struct.unpack_from('<i',code,offset+4)[0]
    literal_rvas.append(first+offset+8+displacement)
    constants.append(struct.unpack('<I',exe.read(literal_rvas[-1],4))[0])
def arr(data):return ','.join(f'0x{x:02x}' for x in data)
fixture='#pragma once\nstatic constexpr unsigned char native_code[]={'+arr(code)+'};\n'
fixture+='static constexpr unsigned char native_unwind[3][20]={'+','.join('{'+arr(i)+'}' for i in infos)+'};\n'
fixture+='static constexpr unsigned native_constants[]={'+','.join(hex(c) for c in constants)+'};\n'
fixture+='static constexpr unsigned native_literal_rvas[]={'+','.join(hex(c) for c in literal_rvas)+'};\n'
fixture+='static constexpr unsigned native_pdata[3][3]={'+','.join('{'+','.join(hex(c) for c in e)+'}' for e in native_entries)+'};\n'
(BUILD/'native_psm_abi_fixture.h').write_text(fixture)
vcvars=Path('C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat')
sources=' '.join('"'+str(RUNTIME/'src/vendor/minhook/src'/s)+'"' for s in ('buffer.c','hook.c','trampoline.c','hde/hde64.c'))
script=f'''@echo off
call "{vcvars}" >nul
cd /d "%~dp0"
ml64 /nologo /c /Foharness.obj "{HERE/'native_psm_abi_harness.asm'}" >build.log 2>&1
if errorlevel 1 exit /b 1
cl /nologo /O2 /EHsc /std:c++20 /I"{BUILD}" "{HERE/'native_psm_abi_unwind_test.cpp'}" harness.obj {sources} /Fe:native_psm_abi_unwind_test.exe >>build.log 2>&1
if errorlevel 1 exit /b 1
native_psm_abi_unwind_test.exe >result.txt 2>&1
if errorlevel 1 exit /b 1
type result.txt
'''
(BUILD/'run.cmd').write_text(script)
result=subprocess.run(['cmd','/c',str(BUILD/'run.cmd')],cwd=BUILD,capture_output=True,text=True)
print(result.stdout)
if result.returncode:
    print((BUILD/'build.log').read_text(errors='replace'))
    if (BUILD/'result.txt').exists():print((BUILD/'result.txt').read_text(errors='replace'))
    sys.exit(result.returncode)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'passed':True,'result':(BUILD/'result.txt').read_text().strip(),'native_code_sha256':hashlib.sha256(code).hexdigest(),'native_pdata_entries':[[hex(v) for v in e] for e in native_entries],'native_unwind_hex':[i.hex() for i in infos],'source_sha256':{str(p.relative_to(HERE.parent)).replace('\\','/'):sha(p) for p in [RUNTIME/'src/native_psm_admission.h',HERE/'native_psm_abi_unwind_test.cpp',HERE/'native_psm_abi_harness.asm',Path(__file__)]},'scope':'Real Windows GP/XMM/flags/helper/cloned-admission execution and RtlVirtualUnwind of actual single-step contexts; pinned native bytes and synthetic memory. No game process or live-flight quality claim.'}
(BUILD/'evidence.json').write_text(json.dumps(report,indent=2)+'\n')
exe.close()
