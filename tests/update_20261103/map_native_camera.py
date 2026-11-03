"""Read-only migration of existing camera/window ABI guards; no game writes."""
from pathlib import Path
import hashlib,json,struct,sys,re
D=Path(__file__).resolve().parents[2]; W=D.parent; O=Path(__file__).resolve().parent
sys.path.insert(0,str(D/'campaign-loader'))
from inspect_interop import PE
pe=PE('E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe')
sites=json.loads((O/'runtime_signature_scan.json').read_text())['sites']
mapping={};evidence=[]
def put(old,new,why):
    old=hex(old) if isinstance(old,int) else old.lower();new=hex(new) if isinstance(new,int) else new.lower()
    if old in mapping:assert mapping[old]==new,(old,new,mapping[old])
    mapping[old]=new;evidence.append(dict(old=old,new=new,proof=why))
def hits(b,kind='data'):
    found=[]
    for name,r,vs,raw,size in pe.sections:
        if kind=='code' and name!='.text':continue
        if kind=='data' and not (0xab00000<=r<0xdbec000):continue
        p=raw
        while True:
            p=pe.data.find(b,p,raw+size)
            if p<0:break
            found.append(r+p-raw);p+=1
    return found
def qword(r):return struct.unpack('<Q',pe.read(r,8))[0]-pe.base
def site(name):return next(x for x in sites if x['name']==name and x['file'].endswith('native_camera.h'))
def choose(name,lo,hi,adjust=0):
    s=site(name);raw=pe.read(lo,hi-lo);needle=bytes.fromhex(s['signature']);found=[];at=0
    while (at:=raw.find(needle,at))>=0:found.append(lo+at);at+=1
    assert len(found)==1,(name,[hex(x)for x in found]);put(s['old_rva'],found[0]-adjust,'Original exact guard, unique in independently qualified owning code range')
    return found[0]
for s in sites:
    if s['unique'] and s['old_rva']!='0x78ed1df':put(s['old_rva'],s['exact_hits'][0],'Exact original embedded byte guard is globally unique')
dfm_stop=hits(bytes.fromhex('48c783c807000000000000'),'code')
assert len(dfm_stop)==1,dfm_stop
put(0x78ED1DF,dfm_stop[0],'Exact DFMAllStop clears owned +7C8 pointer; distinct from slow timeline stop')
# The two camera manager tables must contain the same unique current-cache
# getter and both distinct update implementations at their existing ABI slots.
tables=[]
for addr in hits(struct.pack('<Q',pe.base+0x48ef260)):
    table=addr-0x758;update=qword(table+241*8)
    if update in (0x70b4960,0x48ebe00):tables.append((table,update))
assert len(tables)==2,tables
engine=next(t for t,u in tables if u==0x48ebe00);live=next(t for t,u in tables if u==0x70b4960)
put(0xBB926F0,engine,'Unique shared current-cache getter + engine update vtable slot 241')
put(0xC9D3160,live,'Unique shared current-cache getter + live update vtable slot 241')
put(0x48F9250,0x48ebe00,'Engine table update slot and original entry bytes')
put(0x70C8ED0,0x70b4960,'Live table update slot and original entry bytes')
proof=json.loads((D/'tests/camera_manager_native_proof.json').read_text())['native_slice_sha256']
for old,slot,size in [(0x48FC690,0x748,7),(0x48FC6A0,0x750,7),(0x48FC6B0,0x758,8),(0x48FC6C0,0x760,8)]:
    new=qword(engine+slot);assert qword(live+slot)==new
    assert hashlib.sha256(pe.read(new,size)).hexdigest()==proof[f'{hex(old)}:{hex(size)}']
    put(old,new,'Same getter in both typed vtables; exact saved old-body SHA256')
put(0x48F9710,qword(engine+0x828),'Unchanged engine POV consumer ABI slot 0x828')
# Constructor LEA is independently bound to the qualified engine vtable.
constructor=[]
for p in hits(bytes.fromhex('488d05'),'code'):
    target=p+7+struct.unpack('<i',pe.read(p+3,4))[0]
    if target==engine and pe.read(p+7,3)==bytes.fromhex('488903'):constructor.append(p)
assert len(constructor)==1,constructor
put(0x48F65E3,constructor[0],'LEA resolves to qualified engine manager table and stores it to [rbx]')
choose('actor_component_field_store',0x4175800,0x4176000)
cut=choose('sequence_cut_weak_field',0x6c7e000,0x6c7f000)
choose('cinematic_component_read',cut,cut+32)
choose('cinematic_component_compare',cut,cut+40)
choose('fov_load_bytes',0x48eb000,0x48ebe00)
choose('active_camera_getter',0x41ce000,0x41cf000)
choose('force_setter',0x3970000,0x3990000)
pending=choose('pending_target_getter',0x48e9000,0x48ea000)
choose('current_target_getter',pending,pending+64)
mode=choose('projection_mode_read',0x4182000,0x4183300)
choose('orthographic_width_read',mode,mode+128)
# Viewport table is uniquely bound to the existing ResizeFrame signature.
frame=int(mapping['0x4ac0e70'],16)
viewtables=[a-8 for a in hits(struct.pack('<Q',pe.base+frame)) if qword(a-8)>0 and qword(a-8)<0xab00000]
assert len(viewtables)==1,viewtables
put(0xBE7DDC8,viewtables[0],'Unique typed table containing ResizeFrame at slot +8')
# Exact old actor-root/quaternion layout: compare normalized stored disassembly.
oldfile=W/'ac8-mouseflight/responsive/actor_basis_3fd7430.txt'
oldlines={int(m[1],16)-pe.base:(m[2],m[3]) for l in oldfile.read_text().splitlines() if (m:=re.match(r'([\da-fA-F]+)\s+(\w+)\s*(.*)',l))}
def norm(m,o,a,z):
    o=re.sub(r'\[rip\s*[+-]\s*0x[\da-f]+\]','[rip REL]',o)
    if (m.startswith('j')or m=='call') and re.fullmatch(r'0x[\da-f]+',o):
        t=int(o,16)-pe.base;o='internal:'+str(t-a)if a<=t<z else 'external'
    return m,o
actor=[]
prefix=bytes.fromhex('4883ec38488b42204533c9')
for new in hits(prefix,'code'):
    ins=pe.instructions(new,0x79)
    if all((old:=oldlines.get(0x3fd7430+i.address-pe.base-new)) and norm(*old,0x3fd7430,0x3fd74a9)==norm(i.mnemonic,i.op_str,new,new+0x79)for i in ins):actor.append(new)
assert len(actor)==1,actor
put(0x3FD7430,actor[0],'Full actor position getter normalized instructions, stored old disassembly')
# Quaternion getter is the immediately adjacent reflected thunk, with exact
# component/root and quaternion read instructions from the saved old body.
delta=actor[0]-0x3fd7430
for old in (0x3fd751c,):
    new=old+delta;b=pe.read(new,7)
    assert b==bytes.fromhex('0f10b100020000')
    assert pe.read(new+12,7)==bytes.fromhex('0f10b910020000')
    put(old,new,'Adjacent reflected rotation thunk preserves root +1A0, quaternion +200/+210 instruction layout')
# Native slow-motion class factory resolves its own cache (never a fixed delta).
for old_factory,new_factory,old_global,old_body in [(0x70222F0,0x700dd60,0xE520178,0x7021960),(0x701BEC0,0x7007930,0xE51FEC0,0x701B990)]:
    jump=pe.instructions(new_factory,5)[0];assert jump.mnemonic=='jmp'
    body=int(jump.op_str,16)-pe.base;ins=pe.instructions(body,80)
    loads=[i for i in ins if i.mnemonic=='mov'and i.op_str.startswith('rax, qword ptr [rip')]
    assert loads
    load=loads[0];target=load.address-pe.base+load.size+load.disp
    put(old_factory,new_factory,'Generated typed ObjectProperty factory (independent property map)')
    put(old_global,target,'Typed factory RIP-relative cached UClass getter')
    if old_factory==0x70222F0:put(0x7021967,load.address-pe.base,'Typed slow class factory current cache load')
put(0x4920030,int(mapping['0x492003a'],16)-10,'Unique existing input enable bit guard and containing accessor offset')
names=hits('LiveCampaignGameMode\0'.encode('utf-16le'))
assert len(names)==1,names
named=[]
for r in hits(bytes.fromhex('488d15'),'code'):
    if r+7+struct.unpack('<i',pe.read(r+3,4))[0]==names[0]:named.append(r)
assert len(named)==1,named
body=0x70a7290;ins=pe.instructions(body,0xae)
assert any(i.mnemonic=='lea'and i.address-pe.base==named[0]for i in ins)
loads=[i.address-pe.base+i.size+i.disp for i in ins if i.mnemonic=='mov'and i.op_str.startswith('rax, qword ptr [rip')]
assert len(loads)==2 and loads[0]==loads[1]
assert any(i.mnemonic=='mov'and i.op_str=='dword ptr [rsp + 0x20], 0x1f10'for i in ins)
put(0xE525E40,loads[0],'Named LiveCampaignGameMode class factory with repeated cache load and native object size 1F10')
result=dict(exe_sha256=hashlib.sha256(pe.data).hexdigest(),mapping=mapping,evidence=evidence)
(O/'map_native_camera.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'mapped':len(mapping),'tables':[(hex(t),hex(u))for t,u in tables],'output':str(O/'map_native_camera.json')},indent=2))
