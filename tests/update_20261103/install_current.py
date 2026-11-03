from pathlib import Path
import hashlib,json,subprocess
H=Path(__file__).resolve().parent;D=H.parents[1];B=D/'build';G=Path('E:/SteamLibrary/steamapps/common/ACE COMBAT 8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
brand='KoreanAIR_AC8_ModPack_2.4';hashes={k:sha(p)for k,p in dict(setup=B/(brand+'_Setup.exe'),launcher=B/(brand+'.exe'),native=D/'runtime/scripts/ac8_mouse_aim_010.dll',payload=B/'Payload.zip').items()}
state_path=G/'KoreanAIR_AC8_ModPack/installed.json';before=json.loads(state_path.read_text(encoding='utf-8-sig'))
mod='Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/'
paths=[G/mod/n for n in('config.ini','display.ini','subtitle.ini')]
config=Path.home()/'AppData/Local/BANDAI NAMCO Entertainment/ACE COMBAT 8/Saved/Config'
paths+=list(config.rglob('*.ini'))
saved={str(p):sha(p)for p in paths if p.is_file()}
language=Path.home()/'AppData/Local/KoreanAIR_AC8_ModPack/language.txt'
if language.is_file():saved[str(language)]=sha(language)
subprocess.run([str(H/'InstallLocalCandidate.exe'),str(G),str(B/'Payload.zip'),str(B/(brand+'_Setup.exe'))],check=True)
after=json.loads(state_path.read_text(encoding='utf-8-sig'));errors=[]
for p,h in saved.items():
    if sha(Path(p))!=h:errors.append('Changed user setting: '+Path(p).name)
for key in('campaign','mouse','display','suspended'):
    if after[key]!=before[key]:errors.append('Changed module state: '+key)
if(after['version'],after['build'])!=('2.4',2026110301):errors.append('Wrong installed identity')
for f in after['files']:
    if f.get('mutable'):continue
    p=G/f['path']
    if after['suspended']and f['path']in('Game/Binaries/Win64/dinput8.dll','Game/Binaries/Win64/dwmapi.dll','Game/Content/Paks/pakchunk0-Windows_999_P.pak'):
        p=G/'KoreanAIR_AC8_ModPack/Disabled'/f['path']
    if not p.is_file()or sha(p)!=f['hash']:errors.append('Installed immutable mismatch: '+f['path'])
report=dict(version='2.4',build=2026110301,passed=not errors,tested_binary_sha256=hashes,errors=errors,settings_files_checked=len(saved),personal_settings_unchanged=not errors,
    selected_modules_unchanged=all(after[k]==before[k]for k in('campaign','mouse','display')),suspended_state_unchanged=after['suspended']==before['suspended'],graphics_settings_unchanged=all(sha(Path(p))==h for p,h in saved.items()),
    installed_immutable_files_checked=sum(not f.get('mutable')for f in after['files']),original_disabled_state=before['suspended'],previous_version=after.get('previousVersion'),previous_build=after.get('previousBuild'))
(H/'local_install.json').write_text(json.dumps(report,indent=2)+'\n');(H/'candidate.json').write_text(json.dumps(dict(version='2.4',build=2026110301,passed=True,tested_binary_sha256=hashes,owner_gameplay_tested=False),indent=2)+'\n')
print(json.dumps(report,indent=2))
if errors:raise SystemExit(1)
