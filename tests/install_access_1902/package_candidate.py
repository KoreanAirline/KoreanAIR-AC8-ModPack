from pathlib import Path
import hashlib,json,zipfile
H=Path(__file__).resolve().parent;D=H.parents[1];B=D/'build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
gate=json.loads((B/'feature_regression.json').read_text(encoding='utf-8-sig'))
assert gate['passed'] and (gate['version'],gate['build'])==('2.3',2026101902)
for f,h in {**gate['source_sha256'],**gate['evidence_sha256']}.items():assert sha(D/f)==h,f
brand='KoreanAIR_AC8_ModPack_2.3'
files=[B/(brand+'_Setup.exe'),B/'Payload.zip',D/'README_ENG.txt',D/'README_KOR.txt']
candidate=H/(brand+'_INSTALL_TEST_b2026101902.zip')
guide='''KoreanAIR AC8 Mod Pack 2.3 b2026101902 — installation test candidate

Extract every file into one folder. Leave Payload.zip beside Setup and run Setup.
Select the existing ACE COMBAT 8 folder; do not uninstall your existing pack first.
Existing module choices/settings can be retained. The flight and rendering code has not changed.
If installation fails, send this file created by the test installer:
%TEMP%\\KoreanAIR_AC8_Setup_error.txt
Press Windows+R, paste that path and press Enter to open it after the error.
The log records local paths, Windows file errors and permission-rule summaries.
Security settings and permissions are not changed by this installer.
This test has not yet confirmed the cause or fixed installation on the reporter's PC.
This is an installation-diagnostic prerelease. It is not offered by stable automatic updates.

설치 확인용 테스트본입니다. 압축을 모두 풀고 Payload.zip 옆의 Setup을 실행하세요.
기존 모드를 먼저 제거하지 말고, 기존 게임 폴더에 설치하세요.
조종·렌더링 코드는 변경하지 않았습니다.
실패하면 오류 발생 직후 위 경로의 새 오류 로그를 보내 주세요.
보안 설정·파일 권한을 자동으로 변경하지 않습니다. 설치 진단용 사전 릴리즈이며 정식 자동 업데이트 대상이 아닙니다.
'''
with zipfile.ZipFile(candidate,'w',zipfile.ZIP_DEFLATED) as z:
    for f in files:z.write(f,f.name)
    z.writestr('INSTALL_TEST.txt',guide)
    z.writestr('SHA256.txt',''.join(sha(f)+'  '+f.name+'\n' for f in files))
with zipfile.ZipFile(candidate) as z:assert z.testzip() is None
report={'passed':True,'version':'2.3','build':2026101902,'zip':candidate.name,'sha256':sha(candidate),
    'binaries':{f.name:sha(f) for f in files},'launcher_sha256':sha(B/(brand+'.exe')),
    'gameplay_sources_unchanged_from_published1901':True,'remote_installation_fixed_confirmed':False,'owner_tested':False,'published':False}
(H/'candidate.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'candidate':candidate.name,'sha256':sha(candidate),'published':False}))
