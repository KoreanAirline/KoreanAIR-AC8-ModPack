from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2]/'runtime'
p=R/'payload_manifest.json';data=json.loads(p.read_text(encoding='utf-8-sig'))
data['distribution_native_sha256']=hashlib.sha256((R/'scripts/ac8_mouse_aim_010.dll').read_bytes()).hexdigest()
for entry in data['ship_files']:
 raw=(R/entry['path']).read_bytes()
 entry['size']=len(raw);entry['sha256']=hashlib.sha256(raw).hexdigest()
p.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print('Native manifest updated to exact current build.')
