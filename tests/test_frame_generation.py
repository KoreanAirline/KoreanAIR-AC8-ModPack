from pathlib import Path
import subprocess,json,time,hashlib
D=Path(__file__).resolve().parents[1]
out=D/'tests'/('frame_generation_'+time.strftime('%Y%m%d_%H%M%S'));out.mkdir()
dll=out/'FrameGenerationAudit.dll'
refs=['System.Windows.Forms.dll','System.Drawing.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll']
sources=['src/PackCore.cs','src/Ui.cs','src/UpdateCore.cs','src/Launcher.cs','src/Hud.cs','src/Keys.cs','src/UpdateUI.cs','tests/FrameGenerationAudit.cs']
subprocess.run(['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/target:library','/platform:x64','/define:FRAME_GENERATION_TEST','/out:'+str(dll),*['/reference:'+r for r in refs],*[str(D/p) for p in sources]],check=True)
run=subprocess.run(['powershell.exe','-NoProfile','-STA','-File',str(D/'tests/InvokeFrameGenerationAudit.ps1'),str(dll),str(out)],creationflags=subprocess.CREATE_NO_WINDOW)
report=json.loads((out/'results.json').read_text(encoding='utf-8-sig'))
report['source_sha256']={name:hashlib.sha256((D/name).read_bytes()).hexdigest() for name in sources+['tests/test_frame_generation.py','tests/InvokeFrameGenerationAudit.ps1']}
report['library_sha256']=hashlib.sha256(dll.read_bytes()).hexdigest()
report['tested_artifact']=str(dll.relative_to(D))
report['execution_backend']='DLL-hosted exact current sources with FRAME_GENERATION_TEST synthetic profile-path override; actual package binary not tested here'
report['live_game_started']=False
report['real_profile_modified']=False
(D/'tests/frame_generation_evidence.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'passed':report['passed'],'checks':report['checks'],'report':str(out/'results.json')}))
if not report['passed']:raise RuntimeError(report['error'])
run.check_returncode()
