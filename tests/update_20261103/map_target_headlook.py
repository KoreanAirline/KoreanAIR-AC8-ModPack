"""Updated target getter and cinematic headlook relocation, read-only PE evidence."""
from pathlib import Path
import hashlib,json,re,struct,sys
D=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent
sys.path.insert(0,str(D/'campaign-loader'))
from inspect_interop import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
pe=PE('E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe');md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True
report=dict(scope=__doc__,exe_sha256=hashlib.sha256(pe.data).hexdigest(),mapping={},evidence=[])
def hits(blob):
 out=[]
 for _,rva,vs,raw,size in pe.sections:
  at=raw;end=raw+size
  while True:
   at=pe.data.find(blob,at,end)
   if at<0:break
   out.append(rva+at-raw);at+=1
 return out
def masked_match(code,start):
 masked=set()
 for i in md.disasm(code,pe.base+start):
  off=i.address-pe.base-start
  if 'rip'in i.op_str:masked.update(range(off+i.disp_offset,off+i.disp_offset+i.disp_size))
  if i.mnemonic in('call','jmp')and i.operands and i.operands[0].type==2 and not pe.base+start<=i.operands[0].imm<pe.base+start+len(code):masked.update(range(off+i.imm_offset,off+i.imm_offset+i.imm_size))
 needle=b''.join(b'.'if n in masked else re.escape(bytes([b]))for n,b in enumerate(code));result=[]
 for _,rva,vs,raw,size in pe.sections:
  if rva>0xab00000:continue
  result += [rva+m.start()for m in re.finditer(needle,pe.data[raw:raw+size],re.S)]
 return result,masked
getter=json.loads((D/'tests/target_selection_1502/native_target_point_evidence.json').read_text(encoding='utf-8'))
old=int(getter['native_getter_rva'],16);code=bytes.fromhex(getter['native_getter_hex']);candidates,masked=masked_match(code,old)
assert len(candidates)==1,candidates
new=candidates[0];newcode=pe.read(new,len(code));restored=bytearray(newcode)
for pos in masked:restored[pos]=code[pos]
assert hashlib.sha256(restored).hexdigest()==getter['native_getter_sha256']
refs=[]
for a,b in zip(md.disasm(code,pe.base+old),md.disasm(newcode,pe.base+new)):
 if 'rip'in a.op_str:
  oa=a.address-pe.base+a.size+a.disp;nb=b.address-pe.base+b.size+b.disp
  refs.append(dict(old=hex(oa),new=hex(nb),new_bytes=pe.read(nb,16).hex()))
report['mapping'][hex(old)]=hex(new)
slots=hits(struct.pack('<Q',pe.base+new))
# A50 virtual is part of a larger inherited table; prove primary table install
# by target class's destructor and exact cached-offset semantic body.
report['evidence'].append(dict(kind='target_point',old=hex(old),new=hex(new),length=len(code),masked_only_rip_offsets=sorted(masked),original_sha256=getter['native_getter_sha256'],restored_old_sha256=hashlib.sha256(restored).hexdigest(),new_sha256=hashlib.sha256(newcode).hexdigest(),new_fnv64=hex(__import__('functools').reduce(lambda a,b:((a^b)*1099511628211)&0xffffffffffffffff,newcode,14695981039346656037)),pointer_slots=[hex(x)for x in slots],constants=refs))
# Primary LiveGameObject vtable destructor pattern from original independent proof.
oldinstall=0x7d197c4;install=bytes.fromhex('48 8d 05 ed 3f ee 04 48 8b f9 48 89 01');cands,_=masked_match(install,oldinstall)
qualified=[]
for a in cands:
 i=next(md.disasm(pe.read(a,7),pe.base+a));table=a+i.size+i.disp
 if table+0xa50 in slots:qualified.append((a,table))
qualified=[(a,t)for a,t in qualified if bytes.fromhex('ba500f0000') in pe.read(struct.unpack('<Q',pe.read(t,8))[0]-pe.base,128)]; assert len(qualified)==1,qualified
at,table=qualified[0];report['mapping']['0xcbfe208']=hex(table+0xa50)
report['evidence'].append(dict(kind='target_vtable',old_slot='0xcbfe208',new_slot=hex(table+0xa50),new_table=hex(table),old_destructor_install=hex(oldinstall),new_destructor_install=hex(at),verified_table_slot_A50=hex(new)))

head=json.loads((D/'tests/headlook_evidence.json').read_text(encoding='utf-8'))
for name in ('yaw','pitch','controller_target','move_interface_get','move_interface_set','native_interpolation'):
 item=head['guards'][name];olda=int(item['rva'],16);body=bytes.fromhex(item['bytes']);cands,mask=masked_match(body,olda)
 ev=dict(kind='headlook_saved_bytes',name=name,old=hex(olda),length=len(body),candidates=[hex(x)for x in cands])
 if len(cands)==1:
  newa=cands[0];newbody=pe.read(newa,len(body));restored=bytearray(newbody)
  for pos in mask:restored[pos]=body[pos]
  assert bytes(restored)==body
  report['mapping'][hex(olda)]=hex(newa);ev.update(new=hex(newa),restored_byte_exact=True,new_fnv64=hex(__import__('functools').reduce(lambda a,b:((a^b)*1099511628211)&0xffffffffffffffff,newbody,14695981039346656037)))
  refs=[]
  for oldi,newi in zip(md.disasm(body,pe.base+olda),md.disasm(newbody,pe.base+newa)):
   if oldi.mnemonic=='call'and oldi.operands and oldi.operands[0].type==2:
    oa=oldi.operands[0].imm-pe.base;na=newi.operands[0].imm-pe.base;refs.append(dict(old=hex(oa),new=hex(na)));report['mapping'][hex(oa)]=hex(na)
   if 'rip'in oldi.op_str:
    oa=oldi.address-pe.base+oldi.size+oldi.disp;na=newi.address-pe.base+newi.size+newi.disp;refs.append(dict(old=hex(oa),new=hex(na),kind='rip'))
  ev['references']=refs
 report['evidence'].append(ev)

# Solve the single moved call/RIP operand against the independently retained
# whole old function FNV. No unmasked opcode/field/branch bytes are changed.
namespace={'__file__':str(H/'restore_relocated_guard.py')}
exec((H/'restore_relocated_guard.py').read_text(encoding='utf-8').split('reports=[]')[0],namespace)
solve4,fnv=namespace['solve4'],namespace['fnv']
for olda,newa,size,wanted in ((0x6cac150,0x6c99d10,0x7f,0x4733A3A10A01B07B),(0x6cabfd0,0x6c99b90,0x7f,0x9180A2ECA608741D),(0x6cba420,0x6ca7fe0,0x81,0x58D1AEF4DF19D54D)):
 body=pe.read(newa,size);ops=[]
 for ins in md.disasm(body,pe.base+newa):
  off=ins.address-pe.base-newa
  if ins.mnemonic=='call'and ins.operands[0].type==2:ops.append((off+ins.imm_offset,off+ins.size,ins.operands[0].imm-pe.base,'call'))
  if 'rip'in ins.op_str:ops.append((off+ins.disp_offset,off+ins.size,ins.address-pe.base+ins.size+ins.disp,'rip'))
 ev=dict(kind='headlook_single_relocation_fnv',old=hex(olda),candidate=hex(newa),size=size,relocations=len(ops))
 if len(ops)==1:
  pos,end,newtarget,kind=ops[0];restored=solve4(body,pos,wanted)
  if restored is not None:
   oldtarget=olda+end+struct.unpack('<i',restored)[0];test=bytearray(body);test[pos:pos+4]=restored;assert fnv(test)==wanted
   ev.update(new=hex(newa),old_fnv=hex(wanted),new_fnv=hex(fnv(body)),old_target=hex(oldtarget),new_target=hex(newtarget),relocation_kind=kind,unchanged_nonrelocation_bytes=True)
   report['mapping'][hex(olda)]=hex(newa);report['mapping'][hex(oldtarget)]=hex(newtarget)
 report['evidence'].append(ev)
# Exact unchanged guarded helper (no image-relative operands).
assert fnv(pe.read(0x6ca6fe0,0xb3))==0xAFA482AE6A248758
report['evidence'].append(dict(kind='headlook_unchanged_function',old='0x6cb9420',new='0x6ca6fe0',size=0xb3,fnv64='0xafa482ae6a248758'))
assert fnv(pe.read(0x6c83c70,0x40))==0x6B9FE18528D13948
# Aspect computation prefix before saved bytes has one additional RIP constant.
oldguard=0x6c93dec;newguard=0x6c81a3c;body=bytearray(pe.read(newguard,0xb6))
for ins in md.disasm(bytes(body),pe.base+newguard):
 if 'rip'in ins.op_str:
  newtarget=ins.address-pe.base+ins.size+ins.disp
  oldtarget={0xdc452f0:0xdc5b2f0,0xdc452f8:0xdc5b2f8,0xd29e100:0xd2b37e0}[newtarget]
  struct.pack_into('<i',body,ins.address-pe.base-newguard+ins.disp_offset,oldtarget-(oldguard+ins.address-pe.base-newguard+ins.size))
assert fnv(body)==0x49A3C7A53B8C6C31
report['mapping'][hex(oldguard)]=hex(newguard)
report['evidence'].append(dict(kind='headlook_aspect_guard',old=hex(oldguard),new=hex(newguard),size=0xb6,old_fnv='0x49a3c7a53b8c6c31',new_fnv=hex(fnv(pe.read(newguard,0xb6))),only_verified_constant_relocations=True))

# The old and new world-registry utility occupy the same unwind fragments
# (2B + remaining7C) and are shared by both typed registry getters. Recover
# the remaining class-getter rel32 independently against each whole old guard.
for olda,newa,size,wanted in ((0x6cb65f0,0x6ca41b0,0x8d,0x7A16C9AE2F6028ED),(0x6cb87f0,0x6ca63b0,0x8d,0x07460302C27F410F),(0x4912910,0x49054c0,0xe4,0x556C558207D40DC0)):
 body=bytearray(pe.read(newa,size));calls=[]
 for ins in md.disasm(bytes(body),pe.base+newa):
  if ins.mnemonic=='call'and ins.operands[0].type==2:calls.append((ins.address-pe.base-newa+ins.imm_offset,ins.address-pe.base-newa+ins.size,ins.operands[0].imm-pe.base))
 ev=dict(kind='headlook_typed_helper_fnv',old=hex(olda),candidate=hex(newa),size=size)
 if len(calls)==2:
  pos,end,target=calls[0];assert target==0x6ca71a0
  struct.pack_into('<i',body,pos,0x6cb95e0-(olda+end));ev['shared_world_utility']={'old':'0x6cb95e0','new':'0x6ca71a0'}
  unknown=calls[1]
 elif len(calls)==1:unknown=calls[0]
 else:raise AssertionError(calls)
 pos,end,target=unknown;original=solve4(body,pos,wanted)
 assert original is not None,(hex(olda),'no valid single class-call restoration')
 body[pos:pos+4]=original;oldtarget=olda+end+struct.unpack('<i',original)[0];assert fnv(body)==wanted
 old_layout=json.loads((D.parent/'ac8-mouseflight/responsive/pe_layout.json').read_text(encoding='utf-8'))
 assert any(row[0]==oldtarget for row in old_layout['pdata']),hex(oldtarget)
 report['mapping'][hex(olda)]=hex(newa);report['mapping'][hex(oldtarget)]=hex(target)
 ev.update(new=hex(newa),old_fnv=hex(wanted),new_fnv=hex(fnv(pe.read(newa,size))),restored_call_old=hex(oldtarget),restored_call_new=hex(target),old_callee_boundary_verified=True)
 report['evidence'].append(ev)
# FWeakObjectPtr resolver is independently reached by the reflected camera-cut
# native function and the current-sequence-player getter.
olda,newa,size=0x1ad7cb0,0x1ad95e0,0x40;body=bytearray(pe.read(newa,size));refs=[]
for ins in md.disasm(bytes(body),pe.base+newa):
 if 'rip'in ins.op_str:
  target=ins.address-pe.base+ins.size+ins.disp;oldtarget=target+0x16000;off=ins.address-pe.base-newa
  struct.pack_into('<i',body,off+ins.disp_offset,oldtarget-(olda+off+ins.size));refs.append({'old':hex(oldtarget),'new':hex(target)})
assert fnv(body)==0xB560438BE9B19589
report['mapping'][hex(olda)]=hex(newa)
report['evidence'].append(dict(kind='headlook_weak_resolver',old=hex(olda),new=hex(newa),size=size,old_fnv='0xb560438be9b19589',new_fnv=hex(fnv(pe.read(newa,size))),only_same_objectarray_relocation=True,references=refs))

# Same-pose engine object array and weak helper above independently establish
# the relocated sequence-player lookup's global and weak-resolver operands.
olda,newa,size=0x6cb7ce0,0x6ca58a0,0xb2;body=bytearray(pe.read(newa,size));unknown=[];refs=[]
for ins in md.disasm(bytes(body),pe.base+newa):
 off=ins.address-pe.base-newa
 if 'rip'in ins.op_str:
  target=ins.address-pe.base+ins.size+ins.disp;oldtarget=target+0x16000
  struct.pack_into('<i',body,off+ins.disp_offset,oldtarget-(olda+off+ins.size));refs.append({'old':hex(oldtarget),'new':hex(target),'kind':'object_array'})
 if ins.mnemonic=='call'and ins.operands[0].type==2:
  target=ins.operands[0].imm-pe.base
  if target==0x1ad95e0:
   struct.pack_into('<i',body,off+ins.imm_offset,0x1ad7cb0-(olda+off+ins.size))
  else:unknown.append((off+ins.imm_offset,off+ins.size,target))
assert len(unknown)==1;pos,end,target=unknown[0];restored=solve4(body,pos,0xCFBB0C8C5D9808B1);assert restored is not None
body[pos:pos+4]=restored;oldtarget=olda+end+struct.unpack('<i',restored)[0];assert fnv(body)==0xCFBB0C8C5D9808B1
assert any(row[0]==oldtarget for row in old_layout['pdata'])
report['mapping'][hex(olda)]=hex(newa);report['mapping'][hex(oldtarget)]=hex(target)
report['evidence'].append(dict(kind='headlook_sequence_player',old=hex(olda),new=hex(newa),size=size,old_fnv='0xcfbb0c8c5d9808b1',new_fnv=hex(fnv(pe.read(newa,size))),typed_factory_old=hex(oldtarget),typed_factory_new=hex(target),references=refs))
# Typed factory identity proof uses the generated registration's literal name,
# sizeof, class flags and the actual cache. It is NOT a constant-delta guess.
for olda,newa,size,name in ((0x6c79370,0x6c67210,0xb0,'LiveCinematicsCameraPawn'),):
 decoded=list(md.disasm(pe.read(newa,size),pe.base+newa));names=[];cache=[]
 for ins in decoded:
  if ins.mnemonic=='lea'and ins.op_str.startswith('rdx, [rip'):
   target=ins.address-pe.base+ins.size+ins.disp
   names.append((target,pe.read(target,2*(len(name)+1)).decode('utf-16le').split('\0')[0]))
  if ins.mnemonic=='mov'and ins.op_str.startswith('rax, qword ptr [rip'):
   cache.append(ins.address-pe.base+ins.size+ins.disp)
 assert len(names)==1 and names[0][1]==name and len(set(cache))==1
 assert bytes.fromhex('c744242060040000')in pe.read(newa,size)
 report['mapping'][hex(olda)]=hex(newa)
 report['evidence'].append(dict(kind='headlook_named_class_factory',old=hex(olda),new=hex(newa),size=size,name=name,name_rva=hex(names[0][0]),cache_rva=hex(cache[0]),sizeof='0x460',new_fnv=hex(fnv(pe.read(newa,size))),proof='Unique literal class-name RIP and generated sizeof0x460 registration, actual cached UClass return; semantic identity not complete old factory byte reconstruction.'))

# Playing-state helper: restore shared native allocator/validity helpers and
# the two typed state factories. Their old function boundaries are retained in
# the independent original .pdata map. Recover the remaining array-value helper.
olda,newa,size=0x6cabe60,0x6c99a20,0x170;body=bytearray(pe.read(newa,size));unknown=[];refs=[]
known={0x6c72100:0x6c84410,0x6c711d0:0x6c834e0,0x19ca240:0x19c8e20,0x1725640:0x1724980}
for ins in md.disasm(bytes(body),pe.base+newa):
 off=ins.address-pe.base-newa
 if 'rip'in ins.op_str:
  target=ins.address-pe.base+ins.size+ins.disp;oldtarget=target+0x16000
  struct.pack_into('<i',body,off+ins.disp_offset,oldtarget-(olda+off+ins.size));refs.append({'old':hex(oldtarget),'new':hex(target),'kind':'shared_global'})
 if ins.mnemonic=='call'and ins.operands[0].type==2:
  target=ins.operands[0].imm-pe.base
  if target in known:
   oldtarget=known[target]
   # Leaf helper 19C8E20 has no unwind entry; retained old native disassembly
   # independently calls it. Whole-function old FNV restoration below still
   # verifies this exact rel32 along with every unmasked opcode/member offset.
   assert any(row[0]==oldtarget for row in old_layout['pdata'])or oldtarget==0x19c8e20
   struct.pack_into('<i',body,off+ins.imm_offset,oldtarget-(olda+off+ins.size));refs.append({'old':hex(oldtarget),'new':hex(target),'kind':'typed_class_or_shared_helper'})
  else:unknown.append((off+ins.imm_offset,off+ins.size,target))
assert len(unknown)==1;pos,end,target=unknown[0];restored=solve4(body,pos,0x7689ACB0FD64DA34)
old_start,new_start,old_end=0x6cb5b70,0x6ca3730,0x6cb5c33
expected=[]
for line in(D/'tests/candidate_1505/input.asm').read_text().splitlines():
 match=re.match(r'([\dA-F]+)\s+(\w+)\s*(.*)',line)
 if match and old_start<=int(match[1],16)<old_end:expected.append((int(match[1],16),match[2],match[3].strip()))
actual=list(md.disasm(pe.read(new_start,old_end-old_start),pe.base+new_start))
def normalize(mnemonic,operands,start,end):
 if mnemonic.startswith('j')or mnemonic=='call':
  if re.fullmatch('0x[0-9a-f]+',operands):
   target=int(operands,16)-pe.base
   operands='internal:'+str(target-start)if start<=target<end else'external'
 return mnemonic,operands
assert len(expected)==len(actual)
for (old_address,mnemonic,operands),ins in zip(expected,actual):
 assert old_address-old_start==ins.address-pe.base-new_start
 assert normalize(mnemonic,operands,old_start,old_end)==normalize(ins.mnemonic,ins.op_str,new_start,new_start+old_end-old_start)
# Independently pinned upstream calls and downstream controller offset prove
# which helper the original caller uses, without a constant-delta inference.
calls=[(oa,int(op,16)-pe.base,ins.operands[0].imm-pe.base)for(oa,mn,op),ins in zip(expected,actual)if mn=='call']
assert calls[:3]==[(0x6cb5b79,0x6cb65f0,0x6ca41b0),(0x6cb5b8a,0x6cb7ce0,0x6ca58a0),(0x6cb5b9b,0x6cabe60,0x6c99a20)]
named=[]
for address,name in((0x6c72100,'LiveCinematicsLevelSequencePlayerPlayingState'),(0x6c711d0,'LiveCinematicsLevelSequencePlayerState')):
 found=[]
 for ins in md.disasm(pe.read(address,0xb0),pe.base+address):
  if ins.mnemonic=='lea'and ins.op_str.startswith('rdx, [rip'):
   string=ins.address-pe.base+ins.size+ins.disp
   if pe.read(string,2*(len(name)+1)).decode('utf-16-le').split('\0')[0]==name:found.append(string)
 assert len(found)==1;named.append(dict(factory=hex(address),name=name,name_rva=hex(found[0])))
report['mapping'][hex(olda)]=hex(newa)
report['mapping']['0x6cb9420']='0x6ca6fe0'
report['mapping']['0xdd5c998']='0xdd46998';report['mapping']['0xdd5c9a0']='0xdd469a0'
assert pe.instructions(0x6c81894,7)[0].op_str=='rdx, qword ptr [rip + 0x70c50fd]'
assert pe.instructions(0x6c8189e,7)[0].op_str=='rax, dword ptr [rip + 0x70c50fb]'
report['evidence'].append(dict(kind='headlook_playing_state',old=hex(olda),new=hex(newa),size=size,new_fnv=hex(fnv(pe.read(newa,size))),whole_old_body_restored=restored is not None,identity_proof='All caller instruction offsets/registers/member offsets/internal branches match the retained original. Its independently verified registry/player calls feed this helper and controller+0x30. Named PlayingState/State factories confirm returned object type.',caller_old=hex(old_start),caller_new=hex(new_start),caller_instruction_count=len(actual),caller_mismatches=0,state_factories=named))
report['evidence'].append(dict(kind='native_viewport_array',old=['0xdd5c998','0xdd5c9a0'],new=['0xdd46998','0xdd469a0'],rip_reads=['0x6c81894','0x6c8189e'],proof='Adjacent native pointer/count RIP reads in aspect selection code; retained TArray pointer/count layout.'))
report['removed_guards']=[dict(old='0xc47b080',bytes='0100600000000000'),dict(old='0xc46e7b0',bytes='0100100000000000')]
report['removed_guard_reason']='Nonunique generated property flags without retained property names cannot identify a member. Remove these redundant guards rather than guess metadata addresses.13 complete code fingerprints remain, including exact native member offsets and aspect math.'
original_source=H/'source_before/runtime/src/native_headlook.h'
source=(original_source if original_source.exists()else D/'runtime/src/native_headlook.h').read_text()
report['ported_guards']=[]
for old_address,size,old_hash in re.findall(r'\{0x([\dA-F]+)u,0x([\dA-F]+)u,0x([\dA-F]+)ull\}',source):
 old_address,size=int(old_address,16),int(size,16)
 if size==8:continue
 relocated=int(report['mapping'].get(hex(old_address),hex(old_address)),16)
 report['ported_guards'].append(dict(old=hex(old_address),new=hex(relocated),size=size,new_fnv=hex(fnv(pe.read(relocated,size)))))
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
