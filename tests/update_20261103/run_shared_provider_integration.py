"""Installer provider migration fixtures. Does not touch or launch the game."""
from pathlib import Path
import gzip,hashlib,json,subprocess,zipfile,tempfile
from datetime import datetime,timezone
H=Path(__file__).resolve().parent;D=H.parents[1]
CSC=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
B=Path('<USER_HOME>/Downloads/ACE8 Mod Loader 1.3.1 (Windows Version) 64 1.3.1 2026-10-23T22-20Z pZViQ1V4u')
bin=next(B.rglob('UE4SS.dll')).parent.parent
payload=H/'shared_provider_fixture_payload.zip';files={}
for name in ('dwmapi.dll','ue4ss/UE4SS.dll'):
    files['Game/Binaries/Win64/'+name]=(bin/name).read_bytes()
files.update({'Game/Binaries/Win64/dinput8.dll':b'inert campaign loader fixture',
    'KoreanAIR_AC8_ModPack/Translation/campaign-dialogue.json.gz':gzip.compress(json.dumps({'schema':1,'rows':[{'key':'FixtureDialogue','en':'Fixture English','ko':'시험 대사'}]}).encode('utf-8'),mtime=0),
    'Game/Binaries/Win64/UE4SS/UE4SS-settings.ini':b'[fixture]\r\nexternal=preserved\r\n'})
mod='Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/'
for name in ('Scripts/main.lua','config.ini','display.ini','subtitle.ini'):files[mod+name]=b'-- inert fixture\r\n'
manifest=dict(brand='fixture',legacy={},files=[])
with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as z:
    for path,value in files.items():
        group='campaign' if path=='Game/Binaries/Win64/dinput8.dll' or path.startswith('KoreanAIR_AC8_ModPack/Translation/') else 'runtime'
        manifest['files'].append(dict(path=path,source='payload/'+path,hash=hashlib.sha256(value).hexdigest(),group=group,mutable=path.endswith('.ini')))
        z.writestr('payload/'+path,value)
    z.writestr('manifest.json',json.dumps(manifest))
refs=['System.Windows.Forms.dll','System.Drawing.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll']
exe=H/'SharedProviderIntegrationTests.exe'
sources=[D/'src/PackCore.cs',D/'src/CampaignSubtitles.cs',D/'src/GameInputCompatibility.cs',H/'SharedProviderIntegrationTests.cs',Path(__file__)]
build=subprocess.run([str(CSC),'/nologo','/target:exe','/platform:x64','/optimize+','/define:CAMPAIGN_SUBTITLES_TEST','/out:'+str(exe)]+['/r:'+x for x in refs]+[str(p)for p in sources if p.suffix=='.cs'],capture_output=True,text=True)
if build.returncode:raise RuntimeError(build.stdout+build.stderr)
destination=Path(tempfile.gettempdir())/('ac8sp_'+datetime.now(timezone.utc).strftime('%H%M%S_%f'))
result=subprocess.run([str(exe),str(destination),str(bin),str(payload)],capture_output=True,text=True,encoding='utf-8',errors='replace')
report=dict(passed=result.returncode==0,output=result.stdout,error=result.stderr,fixture=str(destination),game_modified=False,downloaded_code_executed=False,
    core_sha256=hashlib.sha256((D/'src/PackCore.cs').read_bytes()).hexdigest(),
    source_sha256={p.relative_to(D).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in sources},
    test_only_generator_injection=True,production_generator_tested_separately=True)
(H/'shared_provider_integration_results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(result.stdout)
if result.returncode:raise RuntimeError(result.stderr)
