"""Apply independently audited build-specific address migrations, without guidance changes."""
from pathlib import Path
import json,re,shutil,sys
O=Path(__file__).resolve().parent;D=O.parents[1]
sys.path.insert(0,str(D/'campaign-loader'));from inspect_interop import PE
pe=PE('E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe')
mapping={}
for name in ('native_data_mapping','map_camera_properties','map_native_camera','map_native_window','final_projection_mapping','input_port_mapping'):
    for a,b in json.loads((O/(name+'.json')).read_text())['mapping'].items():
        a=int(a,16);b=int(b,16)
        assert a not in mapping or mapping[a]==b,(hex(a),hex(mapping[a]),hex(b))
        mapping[a]=b
backup=O/'runtime_source_before';backup.mkdir(exist_ok=True)
changed=[]
for p in (D/'runtime/src').glob('*'):
    if p.suffix not in ('.h','.cpp')or p.name in ('native_headlook.h','target_point.h'):continue
    original=p.read_text(encoding='utf-8-sig');text=original
    text=re.sub(r'0x[\da-fA-F]+',lambda m:'0x'+format(mapping[int(m[0],16)],'X')if int(m[0],16)in mapping else m[0],text)
    text=text.replace('0x6AA0E27D','0x6AD2D0A7').replace('0x2195A000','0x215A2000')
    if p.name=='display_engine.h':text=text.replace('build 6AA0E27D','build 6AD2D0A7')
    # These original guard arrays include RIP/relative-call bytes. Keep exact
    # guards, updating only already independently qualified instruction sites.
    sites={}
    if p.name=='native_camera.h':sites={'engine_constructor_bytes':(mapping[0x48F65E3],10)}
    if p.name=='native_focus_scene.h':sites={'cache':(mapping[0x7021967],7)}
    if p.name=='final_projection.h':
        report=json.loads((O/'final_projection_mapping.json').read_text())
        sites={name:(int(row['new'],16),row['length'])for name,row in report['guards'].items()}
    for name,(address,count)in sites.items():
        pattern=r'(const unsigned char '+re.escape(name)+r'\[\]\s*=\s*\{)[^}]+(\};)'
        actual=pe.read(address,count);replacement=','.join('0x'+format(b,'02X')for b in actual)
        text,n=re.subn(pattern,lambda m:m[1]+replacement+m[2],text)
        assert n==1,(p,name,n)
    if text!=original:
        target=backup/p.name
        if not target.exists():shutil.copy2(p,target)
        p.write_text(text,encoding='utf-8',newline='\n');changed.append(p.name)
report=dict(mapped_addresses={hex(a):hex(b)for a,b in mapping.items()},changed_files=changed,
    scope='Build-specific addresses and exact guard relocation only; guidance, pointer/camera algorithms and object field offsets are preserved.')
(O/'native_source_port.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'mapped':len(mapping),'changed':changed},indent=2))
