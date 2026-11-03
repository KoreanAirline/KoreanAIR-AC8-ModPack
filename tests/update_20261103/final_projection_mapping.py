"""Read-only relocation of final-projection ABI guards, with call/table checks."""
from pathlib import Path
import hashlib,json,mmap,re,struct,sys
D=Path(__file__).resolve().parents[2];W=D.parent;H=Path(__file__).resolve().parent
sys.path.insert(0,str(W/'libs'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
P=Path('E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe')
f=P.open('rb');data=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ);pe=struct.unpack_from('<I',data,0x3c)[0];n=struct.unpack_from('<H',data,pe+6)[0];op=pe+24;ss=op+struct.unpack_from('<H',data,pe+20)[0];base=struct.unpack_from('<Q',data,op+24)[0];sections=[]
for i in range(n):
 p=ss+i*40;v,va,size,raw=struct.unpack_from('<IIII',data,p+8);flags=struct.unpack_from('<I',data,p+36)[0];sections.append((va,max(v,size),raw,size,flags))
def read(r,size):
 for va,v,raw,rs,flags in sections:
  if va<=r and r+size<=va+rs:return data[raw+r-va:raw+r-va+size]
 raise ValueError(hex(r))
def pointer(r):return struct.unpack('<Q',read(r,8))[0]-base
md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True
text=(D/'runtime/src/final_projection.h').read_text(encoding='utf-8-sig')
old={'local_bytes':0x468eb00,'matrix_bytes':0x418fba0,'call_bytes':0x468f2ba,'viewport_size_bytes':0x449eaf0,'viewport_base_constructor':0x4ab5ca9,'ui_layer_query':0x4ac8f44,'ui_size_query':0x7b9d27f,'widget_extents_bytes':0x4bb2050,'widget_extents_call':0x7301370}
report={'exe_sha256':hashlib.sha256(data).hexdigest(),'scope':__doc__,'guards':{},'mapping':{}}
def norm(mnemonic,operands,start,end):
 operands=re.sub(r'\[rip\s*[+-]\s*0x[0-9a-f]+\]','[rip REL]',operands.strip().lower())
 if mnemonic.startswith('j')or mnemonic=='call':
  if re.fullmatch('0x[0-9a-f]+',operands):
   target=int(operands,16);target=target-base if target>=base else target
   operands='internal:'+str(target-start)if start<=target<end else'external'
 return mnemonic.lower(),operands
old_instructions={}
for p in [D/'tests/stretch_1604/converter_renderlayer.txt',D/'tests/render_1511/render_callers_disasm.txt',D/'tests/render_1510/local_projection_disasm.txt']:
 for line in p.read_text(encoding='utf-8-sig',errors='replace').splitlines():
  m=re.match(r'(0x[0-9a-f]+):\s+(\w+)\s*(.*)',line)
  if m:old_instructions[int(m[1],16)]=(m[2],m[3])
for name,rva in old.items():
 body=re.search(r'const unsigned char '+name+r'\[\]\s*=\s*\{(.*?)\};',text,re.S)[1]
 code=bytes(int(x.strip(),0)for x in body.split(',')if x.strip());masked=set()
 decoded=list(md.disasm(code,base+rva))
 for ins in decoded:
  offset=ins.address-base-rva
  if 'rip' in ins.op_str:masked.update(range(offset+ins.disp_offset,offset+ins.disp_offset+ins.disp_size))
  if ins.mnemonic in ('call','jmp') and ins.operands and ins.operands[0].type==2:masked.update(range(offset+ins.imm_offset,offset+ins.imm_offset+ins.imm_size))
 pattern=b''.join(b'.' if i in masked else re.escape(bytes([b]))for i,b in enumerate(code));hits=[]
 for va,v,raw,rs,flags in sections:
  if flags&0x20000000:
   hits += [va+m.start()for m in re.finditer(pattern,data[raw:raw+rs],re.S)]
 if name=='viewport_base_constructor':
  qualified=[]
  for at in hits:
   ins=next(md.disasm(read(at,11),base+at));target=at+ins.size+ins.disp
   try:
    if pointer(target+0x28)==0x4491c60:qualified.append(at)
   except ValueError:pass
  all_hits=hits;hits=qualified
 elif name=='widget_extents_call':
  all_hits=hits;qualified=[];context=[];old_start=0x7301260;old_end=0x730143c
  expected=[(r,*old_instructions[r])for r in sorted(old_instructions)if old_start<=r<old_end]
  for at in hits:
   start=at-(rva-old_start);instructions=list(md.disasm(read(start,old_end-old_start),base+start));differences=[]
   for instruction in instructions:
    offset=instruction.address-base-start;old_address=old_start+offset
    if old_address not in old_instructions:differences.append({'offset':hex(offset),'error':'missing old instruction'});continue
    mn,op=old_instructions[old_address]
    if norm(mn,op,old_start,old_end)!=norm(instruction.mnemonic,instruction.op_str,start,start+old_end-old_start):differences.append({'offset':hex(offset),'old':mn+' '+op,'new':instruction.mnemonic+' '+instruction.op_str})
   context.append({'candidate':hex(at),'old_parent':hex(old_start),'new_parent':hex(start),'instructions':len(instructions),'mismatches':len(differences),'first_differences':differences[:4]})
   if len(instructions)==len(expected)and not differences:qualified.append(at)
  hits=qualified;report['widget_parent_context']=context
 else:all_hits=hits
 item={'old':hex(rva),'length':len(code),'masked_offsets':sorted(masked),'candidate_count':len(all_hits),'qualified_hits':[hex(x)for x in hits]}
 if len(hits)==1:
  at=hits[0];item['new']=hex(at);item['new_bytes']=read(at,len(code)).hex();refs=[]
  for ins in md.disasm(read(at,len(code)),base+at):
   if ins.mnemonic=='call' and ins.operands and ins.operands[0].type==2:refs.append({'kind':'call','instruction':hex(ins.address-base),'target':hex(ins.operands[0].imm-base)})
   if 'rip' in ins.op_str:refs.append({'kind':'rip','instruction':hex(ins.address-base),'target':hex(ins.address-base+ins.size+ins.disp)})
  item['references']=refs;report['mapping'][hex(rva)]=hex(at)
 report['guards'][name]=item

# Explicit return addresses used to distinguish UI branches from real render
# projection. These are within their independently matched guard sequences.
for old_return,name,offset in ((0x4ac8f58,'ui_layer_query',20),(0x7b9d286,'ui_size_query',7),(0x7301381,'widget_extents_call',17)):
 item=report['guards'][name]
 if 'new'in item:report['mapping'][hex(old_return)]=hex(int(item['new'],16)+offset)

# Check the real typed FViewport base table from its constructor RIP reference.
ctor=report['guards']['viewport_base_constructor']
if ctor.get('references'):
 target=int(ctor['references'][0]['target'],16)
 report['viewport_base_table']={'old':'0xbe7dbd8','new':hex(target),'size_slot_0x28':hex(pointer(target+0x28)),'verified_size_slot':pointer(target+0x28)==0x4491c60}
 report['mapping']['0xbe7dbd8']=hex(target)

# The LiveLocalPlayer vtable must have exactly this GetProjectionData override
# at slot0x368. UE builds omit MSVC RTTI, so prove the class through its
# generated class getter -> registration descriptor -> named factory graph.
needle=struct.pack('<Q',base+0x4681d00);tables=[]
for va,v,raw,rs,flags in sections:
 if not flags&0x20000000:
  for m in re.finditer(re.escape(needle),data[raw:raw+rs]):
   table=va+m.start()-0x368
   if table<0:continue
   name=None
   try:
    locator=pointer(table-8);type_rva=struct.unpack('<I',read(locator+12,4))[0]
    raw_name=read(type_rva+16,256).split(b'\0',1)[0];name=raw_name.decode('ascii')
   except (ValueError,UnicodeError):pass
   item={'table':hex(table),'RTTI_name':name,'slot_0x368':hex(pointer(table+0x368))}
   try:
    getter=pointer(table+0x378);factory=pointer(table+0x380)
    descriptors=[]
    for ins in md.disasm(read(getter,0x30),base+getter):
     if ins.mnemonic=='lea' and ins.op_str.startswith('rdx, [rip'):
      descriptor=ins.address-base+ins.size+ins.disp
      if pointer(descriptor)==factory:descriptors.append(descriptor)
    factory_names=[]
    for ins in md.disasm(read(factory,0xb0),base+factory):
     if ins.mnemonic=='lea' and ins.op_str.startswith('rdx, [rip'):
      address=ins.address-base+ins.size+ins.disp
      value=read(address,64).decode('utf-16-le',errors='replace').split('\0',1)[0]
      if value=='LiveLocalPlayer':factory_names.append({'address':hex(address),'value':value})
    destructor=pointer(table);self_stores=[]
    for ins in md.disasm(read(destructor,0x90),base+destructor):
     if ins.mnemonic=='lea' and 'rip' in ins.op_str and ins.address-base+ins.size+ins.disp==table:self_stores.append(hex(ins.address-base))
    item['class_identity']={'getter_slot_0x378':hex(getter),'factory_slot_0x380':hex(factory),'descriptor_to_same_factory':[hex(x)for x in descriptors],'factory_class_names':factory_names,'destructor_slot_0':hex(destructor),'destructor_self_table_references':self_stores,'verified':len(descriptors)==1 and len(factory_names)==1 and len(self_stores)==1}
   except(ValueError,UnicodeError)as error:item['class_identity']={'verified':False,'error':str(error)}
   tables.append(item)
report['local_player_tables']=tables
matched=[t for t in tables if t.get('class_identity',{}).get('verified')]
if len(matched)==1:report['mapping']['0xc7bf8d8']=matched[0]['table']

report['verified_direct_relations']={
 'local_to_matrix':any(r['target']=='0x4183260'for r in report['guards']['call_bytes'].get('references',[])),
 'widget_caller_to_extents':any(r['target']=='0x4ba2af0'for r in report['guards']['widget_extents_call'].get('references',[])),
 'typed_viewport_size_slot':report.get('viewport_base_table',{}).get('verified_size_slot',False)}
(H/'final_projection_mapping.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
