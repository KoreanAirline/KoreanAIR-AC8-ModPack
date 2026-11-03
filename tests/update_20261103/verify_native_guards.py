"""Independently read exact production byte/FNV guards from the current game file."""
from pathlib import Path
import re,json,sys,hashlib
O=Path(__file__).resolve().parent;D=O.parents[1]
sys.path.insert(0,str(D/'campaign-loader'));from inspect_interop import PE
pe=PE('E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe')
rows=[];errors=[]
for p in (D/'runtime/src').glob('*'):
    if p.suffix not in('.cpp','.h'):continue
    text=p.read_text(encoding='utf-8-sig')
    pattern=r'(?:std::)?memcmp\([^,\n]*?base\+(0x[\da-fA-F]+)(?:\+(0x[\da-fA-F]+))?[^,\n]*,\s*(\w+),\s*sizeof(?:\((\w+)\)|\s+(\w+))'
    for m in re.finditer(pattern,text):
        addr=int(m[1],16)+(int(m[2],16)if m[2]else 0);name=m[3]
        definitions=list(re.finditer(r'const unsigned char\s+'+name+r'\[\]\s*=\s*\{([^}]+)\}',text[:m.start()]))
        if not definitions:errors.append((p.name,hex(addr),name,'missing prior declaration'));continue
        literal=definitions[-1][1];wanted=bytes(int(n.strip(),0)for n in literal.split(',')if n.strip())
        actual=pe.read(addr,len(wanted));ok=actual==wanted
        rows.append(dict(file=p.name,address=hex(addr),name=name,size=len(wanted),passed=ok))
        if not ok:errors.append((p.name,hex(addr),name,'byte mismatch',wanted.hex(),actual.hex()))
    for m in re.finditer(r'\{0x([\dA-F]+)u,0x([\dA-F]+)u,0x([\dA-F]+)ull\}',text):
        a,n,h=(int(v,16)for v in m.groups());v=14695981039346656037
        for b in pe.read(a,n):v=((v^b)*1099511628211)&0xffffffffffffffff
        ok=v==h;rows.append(dict(file=p.name,address=hex(a),name='full-body FNV64',size=n,passed=ok))
        if not ok:errors.append((p.name,hex(a),'FNV mismatch',hex(h),hex(v)))
    for m in re.finditer(r'const uintptr_t starts\[\]=\{([^}]+)\};\s*const uintptr_t ends\[\]=\{([^}]+)\};\s*const uint64_t expected\[\]=\{([^}]+)\}',text):
        groups=[[int(v,16)for v in re.findall(r'0x([\da-fA-F]+)',g)]for g in m.groups()]
        assert len(groups[0])==len(groups[1])==len(groups[2])
        for a,z,h in zip(*groups):
            v=14695981039346656037
            for b in pe.read(a,z-a):v=((v^b)*1099511628211)&0xffffffffffffffff
            ok=v==h;rows.append(dict(file=p.name,address=hex(a),name='full-range FNV64',size=z-a,passed=ok))
            if not ok:errors.append((p.name,hex(a),'range FNV mismatch',hex(h),hex(v)))
assert len(rows)>=65,len(rows)
report=dict(passed=not errors,exe_sha256=hashlib.sha256(pe.data).hexdigest(),timestamp=hex(pe.timestamp),image_size=hex(pe.image_size),guards=rows,errors=errors,
    source_sha256={p.relative_to(D).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in(D/'runtime/src').glob('*')if p.suffix in('.cpp','.h')},
    scope='Exact bytes/FNV read from current PE, prior declaration scoped by source order. Not a live flight or graphics test.')
(O/'native_guards.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'guards':len(rows),'errors':errors},indent=2))
if errors:raise SystemExit(1)
