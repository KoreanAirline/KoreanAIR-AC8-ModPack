"""Restore old relocated instructions and require independent pinned SHA256.

No native execution, no game process or writes. Relocations are verified
against stored original instruction text and independently stored old hashes.
"""
from pathlib import Path
import json,struct,hashlib,re
script=Path(__file__).with_name('input_relocation_audit.py');ns={'__file__':str(script)}
exec(script.read_text(encoding='utf-8').split('report=[]')[0],ns)
read,md,old,O=map(ns.get,('read','md','old','O'))
def fnv(b):
 h=14695981039346656037
 for x in b:h=((h^x)*1099511628211)&0xffffffffffffffff
 return h

def restore(olda,newa,size,*,known_calls=None,known_rips=None):
 code=bytearray(read(newa,size));relocs=[]
 for i in md.disasm(bytes(code),0x140000000+newa):
  a=i.address-0x140000000;off=a-newa;orig=olda+off
  om,oo,_=old.get(orig,('', '', ''))
  oo=re.sub(r'\s+[0-9a-f]{9,}\s+f=.*$','',oo.strip())
  if i.mnemonic.startswith('j') or i.mnemonic=='call':
   if i.operands and i.operands[0].type==2:
    target=i.operands[0].imm-0x140000000
    m=re.fullmatch(r'0x[0-9a-f]+',oo)
    oldtarget=(int(oo,16)-(0x140000000 if int(oo,16)>=0x140000000 else 0))if m else None
    if known_calls and target in known_calls:oldtarget=known_calls[target]
    if oldtarget is not None:
     displacement=oldtarget-(orig+i.size)
     if i.imm_size==1:struct.pack_into('<b',code,off+i.imm_offset,displacement)
     elif i.imm_size==4:struct.pack_into('<i',code,off+i.imm_offset,displacement)
     relocs.append(dict(offset=hex(off),kind='branch',old=hex(oldtarget),new=hex(target)))
  for op in i.operands:
   if op.type==3 and op.mem.base==41:
    target=a+i.size+op.mem.disp
    m=re.search(r'\[rip\s*([+-])\s*(0x[0-9a-f]+)\]',oo)
    oldtarget=None
    if m:
     disp=int(m[2],16)*(1 if m[1]=='+' else -1);oldtarget=orig+i.size+disp
    if known_rips and target in known_rips:oldtarget=known_rips[target]
    if oldtarget is not None:
     struct.pack_into('<i',code,off+i.disp_offset,oldtarget-(orig+i.size));relocs.append(dict(offset=hex(off),kind='RIP',old=hex(oldtarget),new=hex(target)))
   elif op.type==3 and i.disp_size==4 and op.mem.disp>=0x1000000:
    m=re.search(r'\+ (0x[0-9a-f]+)\]',oo)
    if m:
     oldtarget=int(m[1],16);struct.pack_into('<I',code,off+i.disp_offset,oldtarget);relocs.append(dict(offset=hex(off),kind='image relative index',old=hex(oldtarget),new=hex(op.mem.disp)))
 return bytes(code),relocs

raw=json.loads((O/'input_relocation_audit.json').read_text(encoding='utf-8'))
oldhashes={}
D=O.parents[1]
for path in [D/'tests/native_landing_guard_evidence.json',D/'runtime/build/native_raw_capture_evidence.json',D/'runtime/build/native_player_maneuver_evidence.json']:
 value=json.loads(path.read_text(encoding='utf-8-sig'))
 fps=value.get('fingerprints',[])
 if isinstance(fps,list):
  for x in fps:oldhashes[int(x['rva'],16)]=x['sha256']
 else:
  for x in fps.values():oldhashes[int(x['rva'].split('..')[0],16)]=x['sha256']
# SHA256-only metadata retained by older exact native emulator tests.
expected=oldhashes
rows=[]
for x in raw:
 if 'candidate'not in x:continue
 a,new,size=int(x['old'],16),int(x['candidate'],16),x['size']
 if a==0x7D70D27:new=0x7D60647
 code,relocs=restore(a,new,size)
 sha=hashlib.sha256(code).hexdigest();wanted=expected.get(a)
 rows.append(dict(old=hex(a),new=hex(new),size=size,restored_old_sha256=sha,expected_old_sha256=wanted,
     old_sha256_matches=(sha==wanted)if wanted else None,
     shape_matches=x.get('verified_instruction_shape',False),new_fnv64=hex(fnv(read(new,size))),
     new_sha256=hashlib.sha256(read(new,size)).hexdigest(),relocations=relocs))
# Missing old textual ranges have complete native caller contracts and two
# established callee identities. Restoration must still match the old SHA.
for a,new,size,sha in [(0x7D63CE4,0x7D535E4,33,'e352648a0517880165d937763c209328465857cb4f5d2f5cf017a70166dd30e6'),
 (0x7D6FA0F,0x7D5F32F,151,'08d1d4f4311d5cc64d81d027910231755ed42318d792db9e7ad4bc3836bc1b1e'),
 (0x7D5F560,0x7D4EE60,19,'ad52f97c16bced8b182265c484409afddea008a453249059ec41a6fddef1518a'),
 (0x7D562BA,0x7D45BBA,50,'d5dd2932d14dd42c402c01b00874ba51f2168b7c13bfa1f2f3be650b0e930f33'),
 (0x7D80930,0x7D6FEF0,58,'20e36cff7ea3adef6ba3f1af40ab07cfe9bcc54c2e3dd9e429cf7b098fca774a'),
 (0x7D70D27,0x7D60647,22,'ad7e15d690a22979768dac6e76df60deae8ed79cdb3b49327ad0b334f2c5e3a6')]:
 code,relocs=restore(a,new,size,known_calls={0x4D22FE0:0x4D32580,0x4D23140:0x4D326E0},known_rips={0xE51085C:0xE526630})
 actual=hashlib.sha256(code).hexdigest();assert actual==sha,(hex(a),actual,sha)
 rows.append(dict(old=hex(a),new=hex(new),size=size,restored_old_sha256=actual,expected_old_sha256=sha,old_sha256_matches=True,
  new_fnv64=hex(fnv(read(new,size))),new_sha256=hashlib.sha256(read(new,size)).hexdigest(),relocations=relocs))
(O/'input_full_restore_proof.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
for x in rows:print(x['old'],x['new'],'oldSHA256',x['old_sha256_matches'],'shape',x.get('shape_matches'))
