"""Package the current verified candidate; optional local public staging, no publication."""
from pathlib import Path,PurePosixPath
import argparse,ast,hashlib,io,json,re,subprocess,zipfile

H=Path(__file__).resolve().parent;D=H.parents[1];B=D/'build';P=D.parent/'ac8-github-public'
VERSION,BUILD='2.4',2026110301
BRAND='KoreanAIR_AC8_ModPack_'+VERSION;TAG='v'+VERSION+'-b'+str(BUILD)
TEXT_EXT={'.py','.cpp','.c','.h','.hpp','.cs','.json','.md','.txt','.ini','.cmd','.ps1','.lua','.asm','.def','.yml','.yaml','.xml','.inc','.cmake'}
BINARY_EXT={'.pak','.ucas','.utoc','.pyc','.dll','.exe','.obj','.pdb','.lib','.dmp','.etl','.zip','.bin'}
OWNER_INSTRUCTION='Owner explicitly authorized this build for agent startup verification and publication without owner gameplay testing on 2026-11-03.'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def source_map(mapping):
    for relative,wanted in mapping.items():
        path=PurePosixPath(relative)
        assert not path.is_absolute()and'..'not in path.parts and':'not in relative and'\\'not in relative,relative
        assert sha(D/relative)==wanted,'Stale verification: '+relative

def public(data,name):
    path=PurePosixPath(name)
    assert not path.is_absolute()and'..'not in path.parts and':'not in name and'\\'not in name,name
    assert path.name.lower()not in{'acecombat8.exe','start_protected_game.exe'},name
    assert not any(part.lower()in{'source_before','private','capture','captures','replay_capture','fixture','fixtures'}or part.startswith('fixtures_')for part in path.parts),name
    if path.suffix.lower()not in TEXT_EXT:return data
    encoding='utf-16'if data.startswith((b'\xff\xfe',b'\xfe\xff'))else'utf-8-sig'
    text=data.decode(encoding)
    text=text.replace(OWNER_INSTRUCTION,'Owner explicitly authorized this build for agent startup verification and publication without owner gameplay testing on 2026-11-03.')
    text=re.sub(r'(?i)([A-Z]:[/\\]+Users[/\\]+)[^/\\\r\n"<>]+(?=[/\\])',lambda m:m[1]+'USER',text)
    text=text.replace('USER','USER').replace('USER','USER').replace('USER','USER')
    assert not re.search(r'(?i)(github_pat_[a-z0-9_]+|gh[pousr]_[a-z0-9]{20,}|sk-[a-zA-Z0-9]{24,})',text),name
    return text.encode('utf-16'if encoding=='utf-16'else'utf-8')

def exact_record(path,hashes,check_sources=False):
    record=load(path)
    assert(record['version'],record['build'])==(VERSION,BUILD),path.name
    assert record['passed']is True,path.name
    assert record['tested_binary_sha256']==hashes,'Different tested binaries: '+path.name
    if check_sources:
        for field in('source_sha256','evidence_sha256'):
            if field in record:source_map(record[field])
    return record

def public_build_script():
    # Keep configurable public paths and payload-only rebuilds. Full prepared-
    # source builds use the same campaign freshness check as the owner build.
    text=(P/'build_pack.py').read_text(encoding='utf-8-sig')
    current=(D/'build_pack.py').read_text(encoding='utf-8-sig');tree=ast.parse(current)
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='verified_campaign_loader')
    helper=ast.get_source_segment(current,function)
    if'def verified_campaign_loader('not in text:
        text=text.replace('files=[];data={}\n',"native_sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()\n"+helper+"\ncampaign_loader=verified_campaign_loader(D,release)\nfiles=[];data={}\n",1)
        old="loader=D/'campaign-loader/build/dinput8.dll'\nif not loader.exists():loader=D/'campaign-loader/dinput8.dll'\nadd('Game/Binaries/Win64/dinput8.dll',loader,'campaign')"
        assert old in text
        text=text.replace(old,"add('Game/Binaries/Win64/dinput8.dll',campaign_loader,'campaign')")
    else:
        previous=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name=='verified_campaign_loader')
        text=text.replace(ast.get_source_segment(text,previous),helper)
    assert'--payload-zip'in text and'--game-root'in text and'--launcher-only'in text
    assert "'SupportReport.cs'"in text
    return public(text.encode(),'build_pack.py')

def notes():
    return{
      'notes_en':'2.4 · build2026110301\nGame-update compatibility and exact native-code guards were refreshed. Untested game builds show a warning. Recognized IoStoreLoaderMod1.3.1 uses one archive loader, preserving other mod files. Manual triple selection can include gaps and different display sizes. Settings and disabled state are preserved. Update using this Setup over the existing game folder; if the old updater fails, download Setup from this release. External loader is a separate author download. FALKEN combined flight remains unverified.',
      'notes_ko':'2.4 · 빌드2026110301\n게임 업데이트 대응 정보와 실제 코드 검사를 갱신했습니다. 미검증 게임 빌드에는 경고를 표시합니다. 확인된 IoStoreLoaderMod1.3.1과 로더를 하나로 공유하며 다른 모드 파일을 보존합니다. 모니터 직접 선택은 간격·해상도 차이를 포함할 수 있습니다. 설정과 모드가 꺼진 상태는 유지합니다. 기존 게임 폴더에 이 Setup을 실행하세요. 구버전 자동 업데이트가 실패하면 이 릴리즈의 Setup을 직접 받으세요. 외부 로더는 제작자에게 별도로 받아야 하며 FALKEN 병용 비행은 아직 검증하지 못했습니다.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage-public',action='store_true',help='Also stage sanitized current source locally; never pushes, tags or creates a release.')
    args=parser.parse_args();release=load(D/'release.json')
    assert(release['version'],release['build'])==(VERSION,BUILD)
    binaries={'setup':B/(BRAND+'_Setup.exe'),'launcher':B/(BRAND+'.exe'),'native':D/'runtime/scripts/ac8_mouse_aim_010.dll','payload':B/'Payload.zip'}
    hashes={key:sha(path)for key,path in binaries.items()}
    gate=load(B/'feature_regression.json')
    assert gate['passed']and(gate['version'],gate['build'])==(VERSION,BUILD)
    for field in('source_sha256','evidence_sha256'):source_map(gate[field])
    records={name:exact_record(H/(name+'.json'),hashes,True)for name in('candidate','local_install','smoke_launch')}
    native=load(D/'runtime/build/native_identity.json');loader=load(D/'campaign-loader/build/loader_identity.json')
    assert(native['version'],native['build'])==(VERSION,BUILD)and native['dll_sha256']==hashes['native']
    assert(loader['version'],loader['build'])==(VERSION,BUILD)and loader['passed']
    source_map(native['source_sha256']);source_map(loader['source_sha256'])
    assert loader['dll_sha256']==sha(D/'campaign-loader/build/dinput8.dll')
    assert loader['abi_sha256']==sha(D/'campaign-loader/ABI_AND_GUARDS.json')
    for name,wanted in loader['test_sha256'].items():assert sha(D/'campaign-loader/build'/name)==wanted,name
    with zipfile.ZipFile(binaries['payload'])as z:
        manifest=json.loads(z.read('manifest.json'))
        assert manifest['brand']==BRAND
        for item in manifest['files']:
            path=PurePosixPath(item['path']);assert not path.is_absolute()and'..'not in path.parts and':'not in item['path']and'\\'not in item['path']
            assert path.name.lower()not in{'acecombat8.exe','start_protected_game.exe'}
            assert'iostoreloadermod'not in item['path'].lower()and'falken'not in item['path'].lower(),item['path']
            assert hashlib.sha256(z.read(item['source'])).hexdigest()==item['hash'],item['path']
    update=dict(schema=1,version=VERSION,build=BUILD,tag=TAG,installer=binaries['setup'].name,sha256=hashes['setup'],size=binaries['setup'].stat().st_size,**notes())
    assert all(len(update[k])<=8000 for k in('notes_en','notes_ko'))
    (B/'update.json').write_text(json.dumps(update,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    waiver={'version':VERSION,'build':BUILD,'owner_tested_current_build':False,'owner_explicitly_waived_current_build_test':True,'owner_authorized_agent_smoke_test_then_publish':True,'instruction':OWNER_INSTRUCTION,'tested_binary_sha256':hashes,'scope':'Exact current candidate only. Agent smoke launch and current automatic checks are required. This record is not owner gameplay certification.'}
    (H/'owner_release_waiver.json').write_text(json.dumps(waiver,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    validation={'version':VERSION,'build':BUILD,'passed':True,'owner_tested_current_build':False,'owner_explicitly_waived_current_build_test':True,'public_release_authorized':True,'tested_binary_sha256':hashes,'records':records,'feature_gate':gate,'native_identity':native,'campaign_loader_identity':loader,'limitations':'Current automated checks, settings-preserving local installation and agent smoke launch. No claim of all missions tested, crash-free gameplay, or actual FALKEN combined flight.'}
    (H/'release_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sources={}
    def add(path,name=None):
        if path.is_file():
            name=name or path.relative_to(D).as_posix();sources[name]=public(path.read_bytes(),name)
    for folder in('src','licenses','assets','campaign-source','runtime/src','runtime/include','runtime/scripts','runtime/test_fixtures'):
        for path in(D/folder).rglob('*'):
            if not path.is_file()or path.suffix.lower()in BINARY_EXT:continue
            if path.name in{'SharedLoader.cs','Quality.cs','performance.lua'}:continue
            add(path)
    for folder in('runtime','campaign-loader'):
        for path in(D/folder).glob('*'):
            if path.is_file()and path.suffix.lower()in TEXT_EXT and not path.name.startswith(('perf_','performance')):add(path)
    # Keep current validation source, never generated fixtures or private captures.
    for path in H.glob('*'):
        if path.is_file()and path.suffix.lower()in{'.py','.cs','.cpp','.h'}:add(path)
    safe_proofs=('final_projection_mapping.json','map_target_headlook.json','map_native_camera.json','map_native_window.json','war_loader_pattern_audit.json','native_source_port.json','shared_loader_inspection_results.json','shared_provider_integration_results.json','update_changes_results.json','campaign_build_gate_results.json','documentation_identity.json')
    for name in safe_proofs:add(H/name,'validation/'+name)
    for name in('candidate','local_install','smoke_launch'):add(H/(name+'.json'),'validation/'+name+'.json')
    for name in('AGENTS.md','release.json','RELEASE_NOTES.md','README_ENG.txt','README_KOR.txt'):add(D/name)
    add(D/'runtime/build/native_identity.json');add(D/'campaign-loader/build/loader_identity.json')
    public_waiver={k:v for k,v in waiver.items()if k!='instruction'}
    sources['validation/owner_release_waiver.json']=public(json.dumps(public_waiver,indent=2).encode(),'validation/owner_release_waiver.json')
    add(H/'release_validation.json','VALIDATION.json')
    for name in('BUILDING.md','LICENSE'):
        data=(P/name).read_bytes()
        if name=='BUILDING.md':
            data=data.replace(b'KoreanAIR_AC8_ModPack_2.2',BRAND.encode()).replace(b'KoreanAIR_AC8_ModPack_2.3',BRAND.encode())
            data+=b'\nNative campaign verification requires the Python capstone package and the installed game executable for read-only ABI checks. Rebuild with python campaign-loader/build_campaign.py <AceCombat8.exe>. The external IoStoreLoaderMod is a separate author download and is not included in this source archive.\n'
        sources[name]=public(data,name)
    sources['README.md']=public((D/'RELEASE_NOTES.md').read_bytes(),'README.md')
    sources['build_pack.py']=public_build_script()
    sources['Payload.zip']=binaries['payload'].read_bytes()
    sources['BUILDING.txt']=b'Windows: python build_pack.py --payload-zip Payload.zip. See BUILDING.md.\nOnly redistributable mod payload is supplied; game executables and private captures are excluded.\nNative rebuild: runtime sources require Visual Studio C++ tools. Campaign rebuild: python campaign-loader/build_campaign.py <AceCombat8.exe>.\nValidation records describe local source-bound checks; source paths are anonymized for publication.\n'
    sources['PUBLIC_SOURCE_SHA256.json']=json.dumps({name:hashlib.sha256(data).hexdigest()for name,data in sorted(sources.items())},indent=2).encode()+b'\n'
    with zipfile.ZipFile(B/(BRAND+'_Sources.zip'),'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
        for name,data in sorted(sources.items()):z.writestr(name,data)
    with zipfile.ZipFile(B/(BRAND+'.zip'),'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
        for path in(binaries['setup'],binaries['payload'],D/'README_ENG.txt',D/'README_KOR.txt',D/'RELEASE_NOTES.md',B/'update.json'):z.write(path,path.name)
        z.writestr('SHA256.txt',hashes['setup']+'  '+binaries['setup'].name+'\n'+hashes['payload']+'  Payload.zip\n')
    assets=[binaries['setup'],binaries['payload'],B/'update.json',B/(BRAND+'.zip'),B/(BRAND+'_Sources.zip')]
    (B/'SHA256.txt').write_text(''.join(sha(path)+'  '+path.name+'\n'for path in assets),encoding='utf-8')
    if args.stage_public:
        assert(P/'.git').is_dir(),'Expected existing public checkout.'
        allowed=('src/','licenses/','assets/','runtime/src/','runtime/include/','runtime/scripts/','campaign-loader/','campaign-source/','tests/update_20261103/')
        for name,data in sources.items():
            if name.startswith(allowed)or name in{'AGENTS.md','release.json','RELEASE_NOTES.md','README.md','README_ENG.txt','README_KOR.txt','build_pack.py','BUILDING.md'}:
                target=P/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    report={'version':VERSION,'build':BUILD,'tag':TAG,'passed':True,'public_repository_staged':args.stage_public,'public_release_authorized':True,'owner_explicitly_waived_current_build_test':True,'source_entries':len(sources),'tested_binary_sha256':hashes,'assets':{path.name:{'size':path.stat().st_size,'sha256':sha(path)}for path in assets+[B/'SHA256.txt']},'published':False}
    (H/'release_assets.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
