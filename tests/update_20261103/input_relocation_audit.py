"""Read-only native input/response instruction relocation audit for updated game."""
from pathlib import Path
import re,sys,mmap,struct,json,hashlib
D=Path(__file__).resolve().parents[2];W=D.parent
sys.path.insert(0,str(W/'libs'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
O=Path(__file__).resolve().parent
old={}
files=list((W/'ac8-mouseflight/responsive').glob('*.txt'))
files+=list((D/'tests').glob('landing*disassembly*txt'))
files+=[D/'runtime/build/native_maneuver_disassembly.txt']
files+=list((D/'tests/focus_1607').glob('input*txt'))
for p in files:
 for line in p.read_text(encoding='utf-8-sig',errors='replace').splitlines():
  m=re.match(r'\s*(?:0x)?([\da-fA-F]{7,16}):?\s+([a-zA-Z][\w.]*)\s*(.*)',line)
  if m:
   a=int(m[1],16);a=a-0x140000000 if a>=0x140000000 else a
   old[a]=(m[2].lower(),m[3].lower(),str(p.relative_to(W)))
p=Path('E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe');f=p.open('rb');data=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ);pe=struct.unpack_from('<I',data,0x3c)[0];n=struct.unpack_from('<H',data,pe+6)[0];o=struct.unpack_from('<H',data,pe+20)[0];secs=[]
for i in range(n):
 at=pe+24+o+40*i;v,r,s,b=struct.unpack_from('<IIII',data,at+8);secs.append((r,max(v,s),b))
def read(r,n):
 s=next(s for s in secs if s[0]<=r<s[0]+s[1]);off=s[2]+r-s[0];return data[off:off+n]
md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True
ranges=[(0x4D32580,0x4D326DA),(0x4D3B680,0x4D3BF93),(0x4D3EFA0,0x4D3F294),(0x4D3F3A0,0x4D3F5CB),(0x4D3F5D0,0x4D3F94C),(0x4D3FF72,0x4D3FF89),(0x4D3FB68,0x4D3FCDA),(0x4D325DC,0x4D326C7),(0x4D456F0,0x4D45B78),(0x4D40AD0,0x4D41212),(0x4D3C250,0x4D3C500),(0x4D42780,0x4D43540),(0x7D63CE4,0x7D63D05),(0x7D6FA0F,0x7D6FAA6),(0x7D640AA,0x7D640B8),(0x4D328D0,0x4D328E3),(0x4D34908,0x4D349C7),(0x7D5F560,0x7D5F573),(0x7D562BA,0x7D562EC),(0x7D689B0,0x7D68B00)]
ranges +=[(0x7D594C0,0x7D595AE),(0x7D63F56,0x7D63FB4),(0x7D7EAB0,0x7D7EB15),(0x7D80850,0x7D80896),(0x7D80930,0x7D8096A),(0x7D70440,0x7D70544),(0x7D70C1E,0x7D70C43),(0x7D70D27,0x7D70D3D)]
def norm(m,o,start,end):
 o=o.strip()
 o=re.sub(r'\s+[0-9a-f]{9,}\s+f=.*$','',o)
 o=re.sub(r'\[rip\s*[+-]\s*0x[0-9a-f]+\]','[rip REL]',o)
 if m.startswith('j')or m=='call':
  if re.fullmatch('0x[0-9a-f]+',o):
   a=int(o,16);a=a-0x140000000 if a>=0x140000000 else a
   o='internal:'+str(a-start) if start<=a<end else 'external'
 return m,o
report=[]
for a,z in ranges:
 delta=0xF640 if a<0x5000000 else 0x10E20;guess=a-delta
 expected=[(r,*old[r][:2]) for r in sorted(old) if a<=r<z]
 if not expected or expected[0][0]!=a:
  report.append(dict(old=hex(a),end=hex(z),error='old instructions unavailable'));continue
 prefix=expected[:min(10,len(expected))];candidates=[]
 # Search independently by instruction identity in a bounded neighborhood;
 # the approximate code delta never authorizes any production address.
 for new in range(guess-4000,guess+4001):
  ins=list(md.disasm(read(new,100),0x140000000+new,count=len(prefix)))
  if len(ins)!=len(prefix):continue
  if all(i.address-0x140000000-new==r-a and norm(m,op,a,z)==norm(i.mnemonic,i.op_str,new,new+z-a)for (r,m,op),i in zip(prefix,ins)):
   candidates.append(new)
 if len(candidates)!=1:
  report.append(dict(old=hex(a),end=hex(z),error='prefix not unique',candidates=[hex(n)for n in candidates]));continue
 new=candidates[0];b=read(new,z-a);ins=list(md.disasm(b,0x140000000+new));mismatches=[];missing=[];refs=[];rips=[]
 for i in ins:
  addr=i.address-0x140000000;orig=a+addr-new
  if orig not in old:missing.append(hex(orig));continue
  om,oo,file=old[orig];lhs=norm(om,oo,a,z);rhs=norm(i.mnemonic,i.op_str,new,new+z-a)
  if lhs!=rhs:mismatches.append(dict(offset=hex(orig-a),old=' '.join((om,oo)),new=i.mnemonic+' '+i.op_str))
  if i.mnemonic=='call' and re.fullmatch('0x[0-9a-f]+',i.op_str) and re.fullmatch('0x[0-9a-f]+',oo):
   refs.append(dict(old_target=hex(int(oo,16)-(0x140000000 if int(oo,16)>=0x140000000 else 0)),new_target=hex(int(i.op_str,16)-0x140000000),old_call=hex(orig),new_call=hex(addr)))
  if 'rip' in oo:
   m=re.search(r'\[rip\s*([+-])\s*(0x[0-9a-f]+)\]',oo)
   if m:
    disp=int(m[2],16)*(1 if m[1]=='+'else -1);oldtarget=orig+i.size+disp
    # Capstone disp is the actual updated RIP operand.
    op=next((o for o in i.operands if o.type==3 and o.mem.base==41),None)
    if op:
     target=addr+i.size+op.mem.disp
     rips.append(dict(old_target=hex(oldtarget),new_target=hex(target),bytes16=read(target,16).hex() if any(s[0]<=target<s[0]+s[1] for s in secs) else None))
 h=14695981039346656037
 for x in b:h=((h^x)*1099511628211)&0xffffffffffffffff
 report.append(dict(old=hex(a),end=hex(z),candidate=hex(new),size=z-a,instructions=len(ins),old_missing=len(missing),mismatches=len(mismatches),verified_instruction_shape=not missing and not mismatches,first_differences=mismatches[:8],fnv64=hex(h),sha256=hashlib.sha256(b).hexdigest(),references=refs,rip_relocations=rips))
(O/'input_relocation_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for r in report:print(r['old'],r.get('candidate'),'instructions',r.get('instructions'),'missing',r.get('old_missing'),'mismatch',r.get('mismatches'),r.get('error',''))
