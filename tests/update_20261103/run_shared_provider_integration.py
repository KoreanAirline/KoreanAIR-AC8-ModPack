"""Installer provider migration fixtures. Does not touch or launch the game."""
from pathlib import Path
import hashlib,json,subprocess,zipfile,tempfile
from datetime import datetime,timezone
H=Path(__file__).resolve().parent;D=H.parents[1]
CSC=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
B=Path('C:/Users/USER/Downloads/ACE8 Mod Loader 1.3.1 (Windows Version) 64 1.3.1 2026-10-23T22-20Z pZViQ1V4u')
bin=next(B.rglob('UE4SS.dll')).parent.parent
payload=H/'shared_provider_fixture_payload.zip';files={}
for name in ('dwmapi.dll','ue4ss/UE4SS.dll'):
    files['Game/Binaries/Win64/'+name]=(bin/name).read_bytes()
files.update({'Game/Binaries/Win64/dinput8.dll':b'inert campaign loader fixture',
    'Game/Content/Paks/pakchunk0-Windows_999_P.pak':b'inert approved pak fixture',
    'Game/Binaries/Win64/UE4SS/UE4SS-settings.ini':b'[fixture]\r\nexternal=preserved\r\n'})
mod='Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/'
for name in ('Scripts/main.lua','config.ini','display.ini','subtitle.ini'):files[mod+name]=b'-- inert fixture\r\n'
manifest=dict(brand='fixture',legacy={},files=[])
with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as z:
    for path,value in files.items():
        group='campaign' if path in ('Game/Binaries/Win64/dinput8.dll','Game/Content/Paks/pakchunk0-Windows_999_P.pak') else 'runtime'
        manifest['files'].append(dict(path=path,source='payload/'+path,hash=hashlib.sha256(value).hexdigest(),group=group,mutable=path.endswith('.ini')))
        z.writestr('payload/'+path,value)
    z.writestr('manifest.json',json.dumps(manifest))
refs=['System.Windows.Forms.dll','System.Drawing.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll']
exe=H/'SharedProviderIntegrationTests.exe'
build=subprocess.run([str(CSC),'/nologo','/target:exe','/platform:x64','/optimize+','/out:'+str(exe)]+['/r:'+x for x in refs]+[str(D/'src/PackCore.cs'),str(H/'SharedProviderIntegrationTests.cs')],capture_output=True,text=True)
if build.returncode:raise RuntimeError(build.stdout+build.stderr)
destination=Path(tempfile.gettempdir())/('ac8sp_'+datetime.now(timezone.utc).strftime('%H%M%S_%f'))
result=subprocess.run([str(exe),str(destination),str(bin),str(payload)],capture_output=True,text=True,encoding='utf-8',errors='replace')
report=dict(passed=result.returncode==0,output=result.stdout,error=result.stderr,fixture=str(destination),game_modified=False,downloaded_code_executed=False,
    core_sha256=hashlib.sha256((D/'src/PackCore.cs').read_bytes()).hexdigest())
(H/'shared_provider_integration_results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(result.stdout)
if result.returncode:raise RuntimeError(result.stderr)
