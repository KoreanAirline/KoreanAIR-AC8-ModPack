from pathlib import Path
import json, shutil
H=Path(__file__).resolve().parent;D=H.parents[1]
baseline=H/'baseline_1701_sources.zip'
if not baseline.exists():
    shutil.copy2(D.parents[1]/'outputs/KoreanAIR_AC8_ModPack_2.3_Sources.zip',baseline)
release=json.loads((D/'release.json').read_text(encoding='utf-8-sig'))
assert release['version']=='2.3' and release['build'] in (2026101701,2026101901)
release.update(build=2026101901,change_type='bugfix')
(D/'release.json').write_text(json.dumps(release,indent=2)+'\n',encoding='utf-8')
p=D/'src/PackCore.cs';s=p.read_text(encoding='utf-8-sig')
s=s.replace('AssemblyInformationalVersion("2.3+b2026101701")','AssemblyInformationalVersion("2.3+b2026101901")')
s=s.replace('ReleaseBuild=2026101701;','ReleaseBuild=2026101901;')
p.write_text(s,encoding='utf-8')
print('Prepared2.3 b2026101901; published1701 baseline retained.')
