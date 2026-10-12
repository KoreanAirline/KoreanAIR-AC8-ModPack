from pathlib import Path
import hashlib,json,subprocess,struct,time,zipfile
D=Path(__file__).resolve().parents[1]
BASE=D/'tests'/('fixtures_'+time.strftime('%H%M%S'));BASE.mkdir()
SETUP=D/'build/KoreanAIR_AC8_ModPack_1.3_Setup.exe'
results=[]
def check(name,condition):
    results.append(dict(name=name,passed=bool(condition)))
    if not condition:raise AssertionError(name)
def fake(name,bad=False):
    root=BASE/name; win=root/'Game/Binaries/Win64';win.mkdir(parents=True)
    b=bytearray(1024);struct.pack_into('<H',b,0,0x5a4d);struct.pack_into('<I',b,0x3c,128);struct.pack_into('<I',b,128,0x4550);struct.pack_into('<H',b,132,0x8664);struct.pack_into('<I',b,136,0 if bad else 0x6AA0E27D);struct.pack_into('<I',b,208,0x2195A000)
    (win/'AceCombat8.exe').write_bytes(b);(root/'start_protected_game.exe').write_bytes(b)
    eac=root/'EasyAntiCheat';eac.mkdir();(eac/'Settings.json').write_text(json.dumps({'executable':'Game/Binaries/Win64/AceCombat8.exe','productid':'fixture','title':'fixture'}))
    (root/'unrelated.txt').write_text('keep me');return root
def run(*args,ok=True):
    result=subprocess.run([str(SETUP),*map(str,args)],creationflags=subprocess.CREATE_NO_WINDOW)
    if (result.returncode==0)!=ok:raise AssertionError(f'Unexpected exit {result.returncode} {args}: '+(Path.home()/'AppData/Local/Temp/KoreanAIR_AC8_Setup_error.txt').read_text())
def state(root):return json.loads((root/'KoreanAIR_AC8_ModPack/installed.json').read_text())
for cp in range(2):
 for m in range(2):
  for d in range(2):
   root=fake(f'combo_{cp}{m}{d}');run('--install',root,cp,m,d)
   check(f'combo_{cp}{m}{d}_campaign', (root/'Game/Binaries/Win64/dinput8.dll').exists()==bool(cp))
   check(f'combo_{cp}{m}{d}_runtime',(root/'Game/Binaries/Win64/UE4SS/UE4SS.dll').exists()==bool(cp or m or d))
   if cp or m or d:
    record=state(root);check('hash_inventory_'+root.name,all(hashlib.sha256((root/f['path']).read_bytes()).hexdigest()==f['hash'] for f in record['files']))
    if cp or m or d:
     pack=(root/'Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/pack.ini').read_text();check('flags_'+root.name,f'mouseFlight={m}' in pack and f'display={d}' in pack and 'subtitles=1' in pack)
    run('--install',root,cp,m,d);run('--uninstall',root)
    check('uninstall_'+root.name,not(root/'KoreanAIR_AC8_ModPack/installed.json').exists() and not(root/'Game/Binaries/Win64/dinput8.dll').exists() and not(root/'Game/Binaries/Win64/dwmapi.dll').exists())
   check('unrelated_'+root.name,(root/'unrelated.txt').read_text()=='keep me')
root=fake('upgrade');mods=root/'Game/Binaries/Win64/UE4SS/Mods/mods.txt';mods.parent.mkdir(parents=True);mods.write_text('OtherMod : 1\n');run('--install',root,0,1,0)
config=root/'Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/config.ini';config.write_text('[control]\nsensitivity=0.04\nlook_sensitivity=0.03\n');mods.write_text(mods.read_text()+'LaterMod : 1\n');run('--install',root,1,0,1)
check('upgrade_preserves_sensitivity','sensitivity=0.04' in config.read_text());run('--install',root,1,0,0)
check('campaign_only_keeps_subtitle_runtime','OtherMod : 1' in mods.read_text() and 'LaterMod : 1' in mods.read_text() and 'AC8MouseAim : 1' in mods.read_text());run('--uninstall',root)
check('removal_preserves_other_mod_rows','OtherMod : 1' in mods.read_text() and 'LaterMod : 1' in mods.read_text() and 'AC8MouseAim' not in mods.read_text())
root=fake('conflict');dll=root/'Game/Binaries/Win64/dinput8.dll';dll.write_bytes(b'unknown mod');run('--install',root,1,1,1,ok=False)
check('conflict_no_changes',dll.read_bytes()==b'unknown mod' and not(root/'KoreanAIR_AC8_ModPack').exists())
root=fake('foreign_loader_runtime');external={
 'Game/Binaries/Win64/dinput8.dll':b'foreign loader\x00\xff',
 'Game/Binaries/Win64/WeaponPack/config.ini':b'[weapon]\r\nvalue=18.5\r\n',
 'Game/Binaries/Win64/WeaponPack/Resource/weapon.bin':bytes(range(256)),
 'Game/Binaries/Win64/WeaponPack.log':b'original log\r\n',
 'Game/Content/Paks/WeaponPack_v18.5_P.pak':b'unrelated weapon resources',
}
for name,content in external.items():
 p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
run('--install',root,1,1,1,ok=False)
check('foreign_campaign_preflight_no_mutations',before=={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()})
for m,d in [(1,0),(0,1),(1,1)]:
 run('--install',root,0,m,d)
 check(f'foreign_runtime_install_{m}{d}',all((root/p).read_bytes()==content for p,content in external.items()) and not state(root)['campaign'])
 launcher=root/'KoreanAIR_AC8_ModPack_1.3.exe'
 for action in ['--suspend','--verify','--resume','--verify']:
  p=subprocess.run([str(launcher),action],creationflags=subprocess.CREATE_NO_WINDOW);check(f'foreign_{m}{d}_{action}',p.returncode==0 and all((root/name).read_bytes()==content for name,content in external.items()))
 run('--uninstall',root)
 check(f'foreign_runtime_removal_{m}{d}',all((root/p).read_bytes()==content for p,content in external.items()) and not(root/'KoreanAIR_AC8_ModPack/installed.json').exists())
check('foreign_originals_fully_restored',before=={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()})
root=fake('unsupported',bad=True);run('--install',root,1,1,1,ok=False);check('unsupported_no_changes',not(root/'KoreanAIR_AC8_ModPack').exists())
root=fake('changed_owned');run('--install',root,1,0,0);dll=root/'Game/Binaries/Win64/dinput8.dll';dll.write_bytes(b'changed');run('--uninstall',root,ok=False);check('changed_preserved',dll.read_bytes()==b'changed' and (root/'KoreanAIR_AC8_ModPack/installed.json').exists())
root=fake('suspend');run('--install',root,1,1,1);launcher=root/'KoreanAIR_AC8_ModPack_1.3.exe'
for action in ['--verify','--suspend','--verify','--resume','--verify']:
 p=subprocess.run([str(launcher),action],creationflags=subprocess.CREATE_NO_WINDOW);check('launcher'+action,p.returncode==0)
run('--uninstall',root)
with zipfile.ZipFile(D/'build/Payload.zip') as z:
 names=z.namelist();check('no_closed_thai_payload',not any('thai' in n.lower() for n in names));check('no_game_executable_in_payload',not any(n.endswith('/AceCombat8.exe') or n.endswith('/start_protected_game.exe') for n in names))
(BASE/'results.json').write_text(json.dumps(results,indent=2))
print(json.dumps({'checks':len(results),'passed':all(r['passed'] for r in results),'report':str(BASE/'results.json')}))
