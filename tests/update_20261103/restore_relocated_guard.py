"""Reverse a single relocated rel32 using old FNV, then require old SHA256.

This never authorizes an address from FNV alone. An independent old SHA256
validates that every restored instruction byte equals the original pinned body.
No game process, writes or machine-code execution.
"""
from pathlib import Path
import struct,json,hashlib
script=Path(__file__).with_name('input_relocation_audit.py');namespace={'__file__':str(script)}
exec(script.read_text(encoding='utf-8').split('report=[]')[0],namespace)
read,md,O=namespace['read'],namespace['md'],namespace['O']
P=1099511628211;MASK=(1<<64)-1;INV=pow(P,-1,1<<64)
def fnv(b,h=14695981039346656037):
 for x in b:h=((h^x)*P)&MASK
 return h

def solve4(code,offset,want):
 before=fnv(code[:offset]);after=want
 for x in reversed(code[offset+4:]):after=((after*INV)&MASK)^x
 forwards={}
 for a in range(256):
  h=((before^a)*P)&MASK
  for b in range(256):forwards[((h^b)*P)&MASK]=(a,b)
 for d in range(256):
  h=((after*INV)&MASK)^d
  for c in range(256):
   middle=((h*INV)&MASK)^c
   if middle in forwards:return bytes((*forwards[middle],c,d))
 return None

reports=[]
for olda,newa,size,want,sha in [
 (0x7D689B0,0x7D582D0,0x150,0xC44FEAF1C1B45380,'3ccc03b2d116e540ff747fbb7819fc9a9326668a5f0a3ce3f1e8e75023ece663'),
 (0x7D80850,0x7D6FE10,0x46,0xFB448C543EEA677F,'88120e604ac3e00afd6416b4ae2856a647c074973bd36574aee5ae2fcccb3c89'),
 (0x71E5600,0x71D16E0,0x54,0x5FCEFD0AB2982150,'07927297a3ba595d0d43ccb6090342025ef87c8a62e6e1f245130fba01ac548d')]:
 code=bytearray(read(newa,size));unknown=[];refs=[]
 for i in md.disasm(bytes(code),0x140000000+newa):
  a=i.address-0x140000000;off=a-newa
  if i.mnemonic=='call' and i.operands[0].type==2:unknown.append((off+i.imm_offset,off+i.size,i.operands[0].imm-0x140000000))
  for op in i.operands:
   if op.type==3 and op.mem.base==41:
    target=a+i.size+op.mem.disp;oldtarget=target+0x156e0
    struct.pack_into('<i',code,off+i.disp_offset,oldtarget-(olda+off+i.size));refs.append(dict(new=hex(target),old=hex(oldtarget),kind='RIP_constant'))
 if len(unknown)!=1:raise RuntimeError('expected one unknown')
 offset,end,newtarget=unknown[0];restored=solve4(code,offset,want)
 if restored is None:
  reports.append(dict(old=hex(olda),new=hex(newa),failed='No single-relocation reconstruction'));continue
 code[offset:offset+4]=restored;oldtarget=olda+end+struct.unpack('<i',restored)[0]
 refs.append(dict(new=hex(newtarget),old=hex(oldtarget),kind='direct_call'))
 actual=hashlib.sha256(code).hexdigest();matched=actual==sha
 report=dict(old=hex(olda),new=hex(newa),size=size,old_sha256=sha,reconstructed_sha256=actual,complete_old_body_sha256_match=matched,relocations=refs)
 if matched:
  report['new_sha256']=hashlib.sha256(read(newa,size)).hexdigest();report['new_fnv64']=hex(fnv(read(newa,size)))
 reports.append(report)
(O/'single_relocation_restored_proof.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
for x in reports:print(json.dumps(x))
