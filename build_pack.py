from pathlib import Path
import argparse,hashlib,json,os,subprocess,zipfile,shutil
D=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description='Build the KoreanAIR AC8 launcher or installer on Windows.')
parser.add_argument('--launcher-only',action='store_true',help='Build the launcher without runtime or campaign payloads.')
parser.add_argument('--payload-zip',type=Path,help='Use Payload.zip from the matching release Sources.zip to rebuild the installer.')
parser.add_argument('--game-root',type=Path,default=os.environ.get('AC8_GAME_ROOT'),help='Game folder for rebuilding a payload from prepared runtime/campaign sources (or AC8_GAME_ROOT).')
parser.add_argument('--csc',type=Path,default=os.environ.get('CSC'),help='Override the .NET Framework C# compiler location (or CSC).')
options=parser.parse_args()
G=options.game_root
BIN=D/'build';BIN.mkdir(exist_ok=True)
CSC=options.csc or Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
if not CSC.is_file():parser.error('The .NET Framework C# compiler was not found. Supply --csc or set CSC.')
release=json.loads((D/'release.json').read_text(encoding='utf-8'))
BRAND='KoreanAIR_AC8_ModPack_'+release['version']
core=(D/'src/PackCore.cs').read_text(encoding='utf-8')
assert f'Brand="KoreanAIR_AC8_ModPack_{release["version"]}"' in core
assert f'ReleaseBuild={release["build"]};' in core
assert f'AssemblyInformationalVersion("{release["version"]}+b{release["build"]}")' in core
assert release['repository'] in (D/'src/UpdateCore.cs').read_text(encoding='utf-8')
refs=['System.Windows.Forms.dll','System.Drawing.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll']
def compile(name,source,resources=[]):
    args=[str(CSC),'/nologo','/target:winexe','/optimize+','/platform:x64','/out:'+str(BIN/name)]+['/reference:'+r for r in refs]+resources+[str(D/'src/PackCore.cs'),str(D/'src/Ui.cs'),str(D/'src/UpdateCore.cs'),str(D/'src'/source)]
    if source=='Launcher.cs':args.extend(str(D/'src'/p) for p in ('Hud.cs','Keys.cs','UpdateUI.cs'))
    subprocess.run(args,check=True)

def installer_resources():
    payload=BIN/'Payload.zip'
    with zipfile.ZipFile(payload) as z:
        manifest_bytes=z.read('manifest.json')
    descriptor=dict(schema=1,version=release['version'],build=release['build'],
                    tag=f'v{release["version"]}-b{release["build"]}',filename='Payload.zip',
                    sha256=hashlib.sha256(payload.read_bytes()).hexdigest(),size=payload.stat().st_size,
                    url=f'https://github.com/{release["repository"]}/releases/download/v{release["version"]}-b{release["build"]}/Payload.zip',
                    manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest())
    (BIN/'PayloadDescriptor.json').write_text(json.dumps(descriptor,indent=2)+'\n',encoding='utf-8')
    (BIN/'PayloadManifest.json').write_bytes(manifest_bytes)
    return ['/resource:'+str(BIN/name)+','+name for name in ('PayloadDescriptor.json','PayloadManifest.json')]
compile(BRAND+'.exe','Launcher.cs')
if options.launcher_only:
    print(json.dumps({'launcher':str(BIN/(BRAND+'.exe'))}))
    raise SystemExit(0)
if options.payload_zip:
    # The release source archive supplies redistributable payloads without game executables.
    with zipfile.ZipFile(options.payload_zip) as z:
        manifest=json.loads(z.read('manifest.json'))
        data={f['source']:z.read(f['source']) for f in manifest['files']}
    for f in manifest['files']:
        if hashlib.sha256(data[f['source']]).hexdigest()!=f['hash']:
            raise ValueError('Source payload hash mismatch: '+f['path'])
    replacements={BRAND+'.exe':(BIN/(BRAND+'.exe')).read_bytes()}
    replacements.update({'KoreanAIR_AC8_ModPack/'+name:(D/name).read_bytes() for name in ('README_ENG.txt','README_KOR.txt')})
    for f in manifest['files']:
        if f['path'] in replacements:
            data[f['source']]=replacements.pop(f['path'])
            f['hash']=hashlib.sha256(data[f['source']]).hexdigest()
    if replacements:raise ValueError('Use Payload.zip from the matching release: missing '+', '.join(replacements))
    with zipfile.ZipFile(BIN/'Payload.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False).encode())
        for name,content in data.items():z.writestr(name,content)
    compile(BRAND+'_Setup.exe','Setup.cs',installer_resources())
    print(json.dumps({'files':len(manifest['files']),'payload_size':(BIN/'Payload.zip').stat().st_size,'setup_size':(BIN/(BRAND+'_Setup.exe')).stat().st_size}))
    raise SystemExit(0)
if G is None:parser.error('Full payload rebuild requires --game-root or AC8_GAME_ROOT. Use --launcher-only or --payload-zip with release sources.')
if not (D/'runtime/payload_manifest.json').is_file():parser.error('Prepared runtime and campaign payloads are required. See BUILDING.md or use --payload-zip.')
files=[];data={}
def add(path,content,group='common',mutable=False):
    if isinstance(content,Path):content=content.read_bytes()
    key='payload/'+path
    files.append(dict(path=path,source=key,hash=hashlib.sha256(content).hexdigest(),group=group,mutable=mutable));data[key]=content
add(BRAND+'.exe',BIN/(BRAND+'.exe'))
for p in sorted((D/'licenses').rglob('*')):
    if p.is_file():add('KoreanAIR_AC8_ModPack/Licenses/'+p.relative_to(D/'licenses').as_posix(),p)
runtime=json.loads((D/'runtime/payload_manifest.json').read_text())
mod='Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/'
for f in runtime['ship_files']:
    path=f['path']; content=(D/'runtime'/path).read_bytes()
    if path in ('performance.ini','scripts/performance.lua'):continue
    if path=='display.ini':content=b'[display]\r\nenabled=1\r\nspan=0\r\nfov=100\r\ndistance=3000\r\nheight=600\r\n'
    add(mod+('Scripts/'+path[8:] if path.startswith('scripts/') else path),content,'runtime',path in ('config.ini','display.ini','subtitle.ini'))
for path in ['Game/Binaries/Win64/dwmapi.dll','Game/Binaries/Win64/override.txt','Game/Binaries/Win64/UE4SS/UE4SS.dll','Game/Binaries/Win64/UE4SS/UE4SS-settings.ini','Game/Binaries/Win64/UE4SS/UE4SS_SDK_Backends/UE4SS.json']:
    add(path,G/path,'runtime',path.endswith('UE4SS-settings.ini'))
loader=D/'campaign-loader/build/dinput8.dll'
if not loader.exists():loader=D/'campaign-loader/dinput8.dll'
add('Game/Binaries/Win64/dinput8.dll',loader,'campaign')
campaign_pak=D/'campaign-source/rebuilt.pak'
campaign_source=json.loads((D/'campaign-source/release_source_manifest.json').read_text(encoding='utf-8'))
assert campaign_pak.stat().st_size==campaign_source['release_pak_size']
assert hashlib.sha256(campaign_pak.read_bytes()).hexdigest()==campaign_source['release_pak_sha256']
add('Game/Content/Paks/pakchunk0-Windows_999_P.pak',campaign_pak,'campaign')
for name in ('README_ENG.txt','README_KOR.txt'):
    readme=(D/name).read_bytes()
    readme.decode('utf-8')
    add('KoreanAIR_AC8_ModPack/'+name,readme)
    (BIN/name).write_bytes(readme)
legacy={}
roots=['AC8MouseFlight_Licenses','ACE8Thai_Licenses','Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim']
oldnames=['마우스조종_사용법.txt','마우스조종_실행.cmd','마우스조종_응답개선.txt','트리플화면_FOV_안내.txt','한국어_캠페인_모드_설명.txt','한국어모드_설치.cmd','한국어모드_제거.cmd','화면_카메라_설정.cmd','AC8DisplaySettings.ps1','ACE8KoreanLauncher.exe','ACE8KoreanModFiles.json','ACE8KoreanModManage.ps1','ACE8Thai_Launcher.log','EasyAntiCheat/ACE8Thai_Offline.json','Game/Binaries/Win64/ACE8Thai_PakProbe.log','Game/Binaries/Win64/dinput8.dll','Game/Binaries/Win64/dwmapi.dll','Game/Binaries/Win64/override.txt','Game/Binaries/Win64/UE4SS/UE4SS.dll','Game/Binaries/Win64/UE4SS/UE4SS-settings.ini','Game/Binaries/Win64/UE4SS/UE4SS_SDK_Backends/UE4SS.json','Game/Binaries/Win64/UE4SS/Mods/mods.txt','Game/Binaries/Win64/UE4SS/LICENSE','Game/Content/Paks/pakchunk0-Windows_999_P.pak']
for rel in roots:
    oldnames.extend(p.relative_to(G).as_posix() for p in (G/rel).rglob('*') if p.is_file() and not p.is_symlink())
for rel in oldnames:
    p=G/rel
    if p.is_file():legacy[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
if (D/'legacy_inventory.json').exists():legacy=json.loads((D/'legacy_inventory.json').read_text(encoding='utf-8-sig'))
manifest=dict(brand=BRAND,files=files,legacy=legacy)
(BIN/'payload_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
with zipfile.ZipFile(BIN/'Payload.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False).encode())
    for name,content in data.items():z.writestr(name,content)
compile(BRAND+'_Setup.exe','Setup.cs',installer_resources())
print(json.dumps({'files':len(files),'legacy_files':len(legacy),'payload_size':(BIN/'Payload.zip').stat().st_size,'setup_size':(BIN/(BRAND+'_Setup.exe')).stat().st_size}))
