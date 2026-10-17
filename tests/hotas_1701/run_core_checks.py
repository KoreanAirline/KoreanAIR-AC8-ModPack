from pathlib import Path
import datetime, hashlib, json, subprocess, sys, tempfile
D=Path(__file__).resolve().parents[2]
H=Path(__file__).resolve().parent
CSC=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
args=[str(CSC),'/nologo','/target:exe','/optimize+','/platform:x64','/define:FRAME_GENERATION_TEST',
      '/out:'+str(H/'HotasCoreAudit.exe')]
args+=['/reference:'+x for x in ['System.Windows.Forms.dll','System.Drawing.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll']]
args+=[str(D/'src/PackCore.cs'),str(H/'HotasCoreAudit.cs')]
r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace')
(H/'compile.log').write_text(r.stdout+r.stderr,encoding='utf-8');r.check_returncode()
fixture=Path(tempfile.gettempdir())/'tests'/('ka_hotas_'+datetime.datetime.now().strftime('%H%M%S_%f'))
extra=sys.argv[1:]
if not extra:
 candidates=[p for p in (Path.home()/'Downloads').glob('AC8HOTAS 0.2.0 (with UE4SS and AnalogueYaw Mod)*') if p.is_dir() and (p/'Game').is_dir()]
 assert len(candidates)==1,'Supply the unpacked owner-provided HOTAS folder and canonical game root as arguments.'
 extra=[str(candidates[0]),'E:/SteamLibrary/steamapps/common/ACE COMBAT 8']
r=subprocess.run([str(H/'HotasCoreAudit.exe'),str(fixture),*extra],capture_output=True,text=True,encoding='utf-8',errors='replace')
(H/'checks.log').write_text(r.stdout+r.stderr,encoding='utf-8')
report={'passed':r.returncode==0,'checks':r.stdout.count('PASS ')-1,
        'source_sha256':{p.relative_to(D).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [D/'src/PackCore.cs',H/'HotasCoreAudit.cs']},
        'game_executed':False,'downloaded_native_libraries_executed':False,
        'limit':'Production install/preflight/backup logic tested on isolated fake-game folders using exact supplied shared runtime files; actual simultaneous in-game HOTAS/Screen/subtitle compatibility was not tested.'}
(H/'core_regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(r.stdout[-2200:]);r.check_returncode()
