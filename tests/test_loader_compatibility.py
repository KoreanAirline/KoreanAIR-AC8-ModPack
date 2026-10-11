from pathlib import Path
import argparse,hashlib,json,subprocess,tempfile,time,uuid,zipfile

D=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description='Test the actual Setup assembly through a standalone reflection adapter.')
parser.add_argument('--setup',type=Path,default=D/'build/KoreanAIR_AC8_ModPack_1.2_Setup.exe')
args=parser.parse_args()
setup=args.setup.resolve(strict=True)
setup_hash=hashlib.sha256(setup.read_bytes()).hexdigest()
OUT=D/'tests'/('loader_compatibility_'+time.strftime('%Y%m%d_%H%M%S'))
OUT.mkdir()
CSC=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
files={
 'Game/Binaries/Win64/dinput8.dll':(b'current campaign fixture','campaign'),
 'Game/Content/Paks/pakchunk0-Windows_999_P.pak':(b'campaign resource fixture','campaign'),
 'Game/Binaries/Win64/dwmapi.dll':(b'runtime loader fixture','runtime'),
 'Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/Scripts/main.lua':(b'-- runtime fixture','runtime'),
 'Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/config.ini':(b'[control]\r\nsensitivity=0.03\r\n','runtime'),
 'Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/display.ini':(b'[display]\r\nspan=0\r\n','runtime'),
}
manifest={'files':[{'path':path,'source':'payload/'+path,'hash':hashlib.sha256(content).hexdigest(),'group':group,'mutable':path.endswith('.ini')} for path,(content,group) in files.items()],
          'legacy':{'Game/Binaries/Win64/dinput8.dll':hashlib.sha256(b'legacy campaign fixture').hexdigest()}}
payload=OUT/'fakePayload.zip'
with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('manifest.json',json.dumps(manifest))
 for path,(content,group) in files.items():z.writestr('payload/'+path,content)
exe=OUT/'LoaderCompatibilityAudit.exe'
refs=['System.Windows.Forms.dll','System.Drawing.dll','System.Web.Extensions.dll','Microsoft.CSharp.dll']
subprocess.run([str(CSC),'/nologo','/target:exe','/platform:x64','/main:LoaderCompatibilityAudit','/out:'+str(exe),
                *['/reference:'+r for r in refs],str(D/'tests/LoaderCompatibilityAudit.cs')],check=True)
adapter_hash=hashlib.sha256(exe.read_bytes()).hexdigest()
fixtures=Path(tempfile.gettempdir())/('ac8compat_'+uuid.uuid4().hex[:8])
result=subprocess.run([str(exe),str(fixtures),str(setup),str(payload)],creationflags=subprocess.CREATE_NO_WINDOW)
report=json.loads((fixtures/'results.json').read_text(encoding='utf-8'))
report['fixtures']=str(fixtures)
report['tested_source_sha256']={name:hashlib.sha256((D/name).read_bytes()).hexdigest() for name in ('src/PackCore.cs','src/Ui.cs','src/UpdateCore.cs','src/Setup.cs','tests/LoaderCompatibilityAudit.cs','tests/test_loader_compatibility.py')}
report['target_setup']=str(setup.relative_to(D)) if setup.is_relative_to(D) else setup.name
report['target_setup_sha256']=setup_hash
report['adapter_sha256']=adapter_hash
report['fixture_payload_sha256']=hashlib.sha256(payload.read_bytes()).hexdigest()
report['adapter_source_files']=['tests/LoaderCompatibilityAudit.cs']
report['adapter_embedded_payload']=False
report['architecture']='Reflection-only adapter loads actual Setup assembly. Core cases use external tiny payload; unchanged Setup UI uses its actual embedded payload. Synthetic game directories only; no game launch or network call.'
if hashlib.sha256(setup.read_bytes()).hexdigest()!=setup_hash:
 report['passed']=False
 report['error']='Target Setup changed during test.'
(OUT/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['passed'],'checks':report['checks'],'error':report['error'],'report':str(OUT/'results.json')}))
result.check_returncode()
if not report['passed']:raise RuntimeError(report['error'])
