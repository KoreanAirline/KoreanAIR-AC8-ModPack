"""Read-only name + generated offset descriptor bindings for the updated PE."""
from pathlib import Path
import json,struct,sys
D=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(D/'campaign-loader'))
from inspect_interop import PE
pe=PE('E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe')


def locations(needle):
    result=[]
    # Reflected strings and generated records live in the original read-only
    # data range, called .tls in this protected executable's file layout.
    for _,rva,vs,raw,size in pe.sections:
        if rva<0xab00000 or rva>=0xdbec000:continue
        at=raw;end=raw+size
        while True:
            at=pe.data.find(needle,at,end)
            if at<0:break
            result.append(rva+at-raw);at+=1
    return result


specs=[
    (0xCC03620,0xCC0A858,'CameraViewComponent',0x18c8),
    (0xC5E77E0,0xC5E4410,'CachedFirstPersonCamera',0xb0),
    (0xC5E7760,0xC5E4338,'CachedCockpitCamera',0xc0),
    (0xC5E78E0,0xC5E4370,'CachedThirdPersonCamera',0xd0),
    (0xC5E7860,0xC5E4458,'CachedFocusTarget',0xe0),
    (0xC5E7960,0xC5E4FC8,'CachedImpactCamera',0x100),
    (0xCB376D0,0xCB35CC0,'FocusInputHoldDuration',0xf8),
    (0xCBC6BD0,0xCBC8760,'DFMGameObject',0x7c8),
    (0xCBC6B10,0xCBC87B8,'SlowMotionGameObject',0x848),
]
mapping={};evidence=[]
for old_record,old_name,name,offset in specs:
    hits=[]
    field=struct.pack('<HHI',1,offset,0)
    for string in locations((name+'\0').encode('ascii')):
        for row in locations(struct.pack('<Q',pe.base+string)):
            if pe.read(row+0x30,8)==field:hits.append(dict(record=row,name=string))
    evidence.append(dict(old_record=hex(old_record),old_name=hex(old_name),name=name,
        offset=hex(offset),matches=hits))
    if len(hits)==1:
        mapping[hex(old_record)]=hex(hits[0]['record']);mapping[hex(old_name)]=hex(hits[0]['name'])
        if name in ('DFMGameObject','SlowMotionGameObject'):
            mapping[hex(0x701bec0 if name=='DFMGameObject' else 0x70222f0)]=hex(struct.unpack('<Q',pe.read(hits[0]['record']+0x38,8))[0]-pe.base)
report=dict(scope=__doc__,mapping=mapping,evidence=evidence)
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
