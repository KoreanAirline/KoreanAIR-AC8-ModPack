"""Offline proof of descriptor/sibling and old embedded payload providers.

Compiles tiny resources and exact isolated provider source; no full pack build,
installation, scan configuration or game process interaction is performed.
"""
from pathlib import Path
import hashlib,json,os,re,secrets,subprocess,time,uuid,zipfile

D=Path(__file__).resolve().parents[1]
OUT=D/'tests'/('release_payload_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6])
OUT.mkdir()
CSC=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
core=(D/'src/PackCore.cs').read_text()
brand=re.search(r'const string Brand="([^"]+)"',core).group(1)
build=int(re.search(r'const long ReleaseBuild\s*=\s*(\d+)',core).group(1))
version=brand.rsplit('_',1)[1]
tag=f'v{version}-b{build}'
files={'Game/Binaries/Win64/dinput8.dll':b'benign synthetic campaign loader text',
       'fixture.txt':('\n'.join(secrets.token_hex(64) for _ in range(128))+'\n').encode()}
manifest={'files':[dict(path=p,source='payload/'+p,hash=hashlib.sha256(v).hexdigest(),group='campaign' if p.endswith('.dll') else 'common',mutable=False) for p,v in files.items()],'legacy':{}}
manifest_bytes=json.dumps(manifest,separators=(',',':')).encode()
(OUT/'manifest.expected.json').write_bytes(manifest_bytes)
payload=OUT/'payload.expected.zip'
with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('manifest.json',manifest_bytes)
    for path,data in files.items():z.writestr('payload/'+path,data)
payload_bytes=payload.read_bytes()
descriptor=dict(schema=1,version=version,build=build,tag=tag,filename='Payload.zip',sha256=hashlib.sha256(payload_bytes).hexdigest(),size=len(payload_bytes),url=f'https://github.com/KoreanAirline/KoreanAIR-AC8-ModPack/releases/download/{tag}/Payload.zip',manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest())
mutations={'bad_schema':{'schema':2},'bad_version':{'version':'1.2'},'bad_build':{'build':build-1},'bad_tag':{'tag':'latest'},'bad_filename':{'filename':'Other.zip'},'bad_path':{'filename':'../Payload.zip'},'bad_hash':{'sha256':'bad'},'bad_size':{'size':0},'bad_manifest_hash':{'manifest_sha256':'bad'},'bad_url':{'url':'http://github.com/KoreanAirline/KoreanAIR-AC8-ModPack/releases/download/'+tag+'/Payload.zip'},'foreign_repo':{'url':'https://github.com/Other/Repo/releases/download/'+tag+'/Payload.zip'},'unpinned_url':{'url':'https://github.com/KoreanAirline/KoreanAIR-AC8-ModPack/releases/latest/download/Payload.zip'}}
fixture_source=OUT/'Fixture.cs'
fixture_source.write_text('public static class BenignPayloadFixture { public static int Marker=1; }\n')
for kind in ['valid','cached','tampered','truncated','oversized','missing','mismatched_manifest','legacy','empty',*mutations]:
    folder=OUT/kind;folder.mkdir();resources=[]
    if kind=='legacy':
        embedded=folder/'legacy.zip';embedded.write_bytes(payload_bytes);resources=['/resource:'+str(embedded)+',Payload.zip']
    elif kind!='empty':
        desc=dict(descriptor);desc.update(mutations.get(kind,{}))
        if kind=='missing':desc['sha256']=hashlib.sha256(payload_bytes+b'unavailable unique fixture').hexdigest()
        pd=folder/'descriptor.json';pd.write_text(json.dumps(desc,separators=(',',':')))
        pm=folder/'manifest.json';pm.write_bytes(manifest_bytes if kind!='mismatched_manifest' else b'{"files":[],"legacy":{}}')
        resources=['/resource:'+str(pd)+',PayloadDescriptor.json','/resource:'+str(pm)+',PayloadManifest.json']
    if kind in ['valid','tampered','truncated','oversized']:
        data=payload_bytes
        if kind=='tampered':data=data[:-1]+bytes([data[-1]^1])
        elif kind=='truncated':data=data[:-1]
        elif kind=='oversized':data=data+b'X'
        (folder/'Payload.zip').write_bytes(data)
    subprocess.run([str(CSC),'/nologo','/target:library','/platform:x64','/out:'+str(folder/(kind+'.dll')),*resources,str(fixture_source)],check=True)
provider_source=(D/'src/UpdateCore.cs').read_text()
def block(source,marker):
    start=source.index(marker);opened=source.index('{',start);at=opened+1;depth=1
    while depth:
        depth+=(source[at]=='{')-(source[at]=='}');at+=1
    return source[start:at]
extracted={'InstallerPayloadDescriptor':block(provider_source,'public sealed class InstallerPayloadDescriptor'),
           'ReleasePayload':block(provider_source,'public static class ReleasePayload'),
           'Core.Safe':block(core,'public static string Safe('),
           'Core.Hash':block(core,'public static string Hash(byte[]')}
fields=[next(line.strip() for line in core.splitlines() if marker in line) for marker in ('public const string Brand=','public const long ReleaseBuild=','public const string Folder=','public static JavaScriptSerializer Json=')]
repository=next(line.strip() for line in provider_source.splitlines() if 'public const string Repository=' in line)
isolated=OUT/'ProviderOnly.cs'
isolated.write_text('''using System;using System.IO;using System.Net;using System.Linq;using System.Reflection;using System.Text;using System.Text.RegularExpressions;using System.Threading;using System.IO.Compression;using System.Security.Cryptography;using System.Web.Script.Serialization;
namespace KoreanAIR {
'''+extracted['InstallerPayloadDescriptor']+'\n'+extracted['ReleasePayload']+'\npublic static class Core {\n'+'\n'.join(fields)+'\n'+extracted['Core.Safe']+'\n'+extracted['Core.Hash']+'\n}\npublic static class UpdateCore {\n'+repository+'''
public static int NetworkAttempts=0;
internal static HttpWebResponse Response(string url,int timeout){++NetworkAttempts;throw new InvalidOperationException("Network calls are excluded from provider-only fixtures.");}
}
}
''')
sources=[isolated,D/'tests/ReleasePayloadAudit.cs']
refs=['System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll']
audit=OUT/'ProviderOnlyAudit.dll'
subprocess.run([str(CSC),'/nologo','/target:library','/platform:x64','/out:'+str(audit),*['/reference:'+r for r in refs],*map(str,sources)],check=True)
host=OUT/'invoke-provider.ps1'
host.write_text('''param([string]$auditPath,[string]$fixturePath,[string]$reportPath)
$ErrorActionPreference='Stop'
$assembly=[Reflection.Assembly]::LoadFile([IO.Path]::GetFullPath($auditPath))
$method=$assembly.GetType('ReleasePayloadAudit',$true).GetMethod('Main',[Reflection.BindingFlags]'Static,NonPublic')
$arguments=New-Object object[] 1
$arguments[0]=[string[]]@($fixturePath,$reportPath)
exit [int]$method.Invoke($null,$arguments)
''')
cache_base=Path(os.environ['LOCALAPPDATA'])/'KoreanAIR_AC8_ModPack/Payloads'
owned_cache=cache_base/descriptor['sha256']
assert not owned_cache.exists(),'Unique synthetic cache folder unexpectedly exists; refusing to touch it.'
try:
    result=subprocess.run(['powershell.exe','-NoProfile','-File',str(host),str(audit),str(OUT),str(OUT/'results.json')],creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True,text=True,errors='replace')
finally:
    # Remove only this run's newly created SHA folder, without recursive removal
    # or touching any real release cache. Payload provider closes its handles.
    assert owned_cache.parent.resolve()==cache_base.resolve() and re.fullmatch('[a-f0-9]{64}',owned_cache.name)
    if owned_cache.exists():
        for item in owned_cache.iterdir():
            assert item.is_file() and (item.name=='Payload.zip' or re.fullmatch('download-[a-f0-9]{32}\\.part',item.name))
            item.unlink()
        owned_cache.rmdir()
print(result.stdout)
if result.returncode:print(result.stderr)
report=json.loads((OUT/'results.json').read_text())
report['tested_source_sha256']={p.relative_to(D).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [D/'src/PackCore.cs',D/'src/UpdateCore.cs',D/'tests/ReleasePayloadAudit.cs',Path(__file__)]}
report['exact_extracted_source_sha256']={name:hashlib.sha256(text.encode()).hexdigest() for name,text in extracted.items()}
report['isolated_fixture_source_sha256']=hashlib.sha256(isolated.read_bytes()).hexdigest()
report['prior_adapter_block']={'error':'WinError 225','observation':'An earlier adapter containing the full PackCore/Ui/UpdateCore was blocked at process launch. This provider-only fixture excludes unrelated installer/game-file code. No quarantine restore, protection changes or exclusions were used.'}
report['fixture_payload_sha256']=descriptor['sha256']
report['fixture_manifest_sha256']=descriptor['manifest_sha256']
report['provider_binary_sha256']=hashlib.sha256(audit.read_bytes()).hexdigest()
report['execution_backend']='Isolated provider-only library invoked by ordinary Windows PowerShell reflection host; no custom executable launched.'
report['download_allowed']=False
(OUT/'results.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(passed=report['passed'],checks=len(report['checks']),report=str(OUT/'results.json'))))
result.check_returncode()
if not report['passed']:raise RuntimeError(report['error'])
