"""Read-only window ABI/engine global relocation against saved pre-update evidence."""
from pathlib import Path
import sys,json,re,struct,hashlib
O=Path(__file__).resolve().parent;D=O.parents[1];W=D.parent
sys.path.insert(0,str(D/'campaign-loader'))
from inspect_interop import PE
pe=PE('E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe')
mapping={};evidence=[]
def put(old,new,proof):mapping[hex(old)]=hex(new);evidence.append(dict(old=hex(old),new=hex(new),proof=proof))
def hits(b,kind='code'):
    out=[]
    for name,r,vs,raw,size in pe.sections:
        if kind=='code'and name!='.text':continue
        if kind=='data'and not(0xab00000<=r<0xdbec000):continue
        at=raw
        while(at:=pe.data.find(b,at,raw+size))>=0:out.append(r+at-raw);at+=1
    return out
def norm(m,o,a,z):
    o=re.sub(r'\[rip\s*[+-]\s*0x[\da-f]+\]','[rip REL]',o)
    if(m.startswith('j')or m=='call')and re.fullmatch(r'0x[\da-f]+',o):
        t=int(o,16);t=t-pe.base if t>=pe.base else t;o='internal:'+str(t-a)if a<=t<z else 'external'
    return m,o
old=json.loads((W/'ac8-mouseflight/responsive/native_window_move_r434_audit.json').read_text())['move_window_to']
expected={int(m[1],16):(m[2],m[3])for l in old['disassembly']if(m:=re.match(r'0x([\da-f]+) (\w+)\s*(.*)',l))}
qualified=[]
for new in hits(bytes.fromhex('405556574883ec60')):
    ins=pe.instructions(new,0xb4)
    if all((o:=expected.get(i.address-pe.base-new+0x1b44b10))and norm(*o,0x1b44b10,0x1b44bc4)==norm(i.mnemonic,i.op_str,new,new+0xb4)for i in ins):qualified.append(new)
assert len(qualified)==1,qualified
move=qualified[0];put(0x1B44B10,move,'Full old MoveWindowTo instruction body matches normalized new body')
tables=[a-0x18 for a in hits(struct.pack('<Q',pe.base+move),'data')]
assert len(tables)==1,tables
table=tables[0];put(0xB4CF6E0,table,'Unique native window vtable with verified MoveWindowTo at slot18')
for old,slot in [(0x1B44820,8),(0x1B45170,0xf0)]:
    new=struct.unpack('<Q',pe.read(table+slot,8))[0]-pe.base;put(old,new,'Native window vtable ABI slot; same HWND layout used by verified move method')
# Saved original guard for the SWindow cached-position setter, additionally
# requiring exactly one candidate with the known +378/+380 position/cache use.
prefix=bytes.fromhex('48895c240848897424184889542410574883ec30')
candidates=[]
for new in hits(prefix):
    ins=pe.instructions(new,180)
    if any(i.mnemonic=='movss'and i.op_str.startswith('dword ptr [rcx + 0x378]')for i in ins) and any(i.mnemonic=='movss'and i.op_str.startswith('dword ptr [rcx + 0x37c]')for i in ins):candidates.append(new)
assert len(candidates)==1,candidates
put(0x1C66FE0,candidates[0],'Exact original prologue plus cached screen position store at +378')
# IsWindow true is a folded leaf. Its exact old body was only `mov al,1;ret`;
# an engine resize path must reference the exact leaf in the viewport table.
# Resolve from the qualified new FSceneViewport table +0x60.
cam=json.loads((O/'map_native_camera.json').read_text())['mapping'];viewport=int(cam['0xbe7ddc8'],16)
leaf=struct.unpack('<Q',pe.read(viewport+0x60,8))[0]-pe.base
assert pe.read(leaf,3)==bytes.fromhex('b001c3')
put(0x16BACA0,leaf,'Known FSceneViewport IsWindow slot+60 points to exact true leaf')
# Locate saved old instructions that refer to GEngine, preserving the original
# instruction sequence and deriving the new RIP address from that match.
refs=[];parsed={}
paths=list((D/'tests').rglob('*.txt'))+list((W/'ac8-mouseflight/responsive').glob('*.txt'))
for path in paths:
    if path.stat().st_size>15000000:continue
    lines=[]
    for l in path.read_text(encoding='utf-8-sig',errors='replace').splitlines():
        m=re.match(r'\s*(?:0x)?([\da-fA-F]{7,16}):?\s+(\w+)\s*(.*)',l)
        if m:
            a=int(m[1],16);a=a-pe.base if a>=pe.base else a;lines.append((a,m[2],m[3]))
    for j,(a,m,o) in enumerate(lines[:-1]):
        z=re.search(r'\[rip\s*([+-])\s*(0x[\da-f]+)\]',o)
        if z and lines[j+1][0]-a in range(1,16):
            target=lines[j+1][0]+int(z[2],16)*(1 if z[1]=='+'else -1)
            if target==0xE4C50E8:refs.append(dict(path=str(path.relative_to(D.parent)),old=hex(a),sequence=lines[max(0,j-2):j+6]))
global_proofs=[]
for r in refs:
    old=int(r['old'],16)
    anchor=0x4ac0e70 if 0x4ac0e70<=old<0x4ac1370 else 0x468eb00 if 0x468eb00<=old<0x468f400 else None
    if anchor is None:continue
    new_anchor=int(cam[hex(anchor)],16);delta=new_anchor-anchor
    seq=r['sequence'];start=seq[0][0];end=seq[-1][0]+15
    ins=pe.instructions(start+delta,end-start)
    byaddr={i.address-pe.base-delta:i for i in ins}
    if not all(a in byaddr and norm(m,o,start,end)==norm(byaddr[a].mnemonic,byaddr[a].op_str,start+delta,end+delta)for a,m,o in seq):continue
    i=byaddr[old];target=i.address-pe.base+i.size+i.disp
    global_proofs.append(dict(old=hex(old),new=hex(old+delta),target=hex(target),instruction_count=len(seq),source=r['path']))
assert len(global_proofs)>=3,global_proofs
assert len({r['target']for r in global_proofs})==1,global_proofs
put(0xE4C50E8,int(global_proofs[0]['target'],16),'Independent native ResizeFrame/projection old instruction sequences resolve same new GEngine global')
result=dict(mapping=mapping,evidence=evidence,engine_global_proofs=global_proofs)
(O/'map_native_window.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'mapping':mapping,'engine_proofs':len(global_proofs)},indent=2))
