from pathlib import Path
import hashlib,json,zipfile
H=Path(__file__).resolve().parent;D=H.parents[1];B=D/'build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
gate=json.loads((B/'feature_regression.json').read_text(encoding='utf-8-sig'))
assert gate['passed'] and (gate['version'],gate['build'])==('2.3',2026101701)
for f,h in {**gate['source_sha256'],**gate['evidence_sha256']}.items():assert sha(D/f)==h,f
brand='KoreanAIR_AC8_ModPack_2.3'
files=[B/(brand+'_Setup.exe'),B/'Payload.zip',D/'README_ENG.txt',D/'README_KOR.txt']
path=H/(brand+'_LOCAL_b2026101701.zip')
with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
 for f in files:z.write(f,f.name)
 z.writestr('CANDIDATE.txt','Local test candidate2.3 b2026101701. Extract all files and run Setup. Keep Payload.zip beside Setup. Existing settings are retained. Not published to GitHub.\n로컬 테스트 후보입니다. 압축을 모두 풀고 Payload.zip 옆의 Setup을 실행하세요. 기존 설정을 유지합니다. GitHub에는 공개하지 않았습니다.\n')
 z.writestr('SHA256.txt',''.join(sha(f)+'  '+f.name+'\n' for f in files))
with zipfile.ZipFile(path) as z:assert z.testzip() is None
r={'passed':True,'version':'2.3','build':2026101701,'zip':str(path),'zip_sha256':sha(path),'tested_binary_sha256':{k:sha(p) for k,p in {'setup':files[0],'payload':files[1],'launcher':B/(brand+'.exe'),'native':D/'runtime/scripts/ac8_mouse_aim_010.dll'}.items()},'owner_gameplay_tested':False,'remote_weave_fixed_confirmed':False,'hotas_gameplay_verified':False,'published':False}
(H/'candidate.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'candidate':path.name,'sha256':sha(path),'published':False}))
