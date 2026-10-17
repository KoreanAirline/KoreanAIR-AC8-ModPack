from pathlib import Path
import subprocess,hashlib,json
H=Path(__file__).resolve().parent;D=H.parents[1];B=H/'monitor_fixture';B.mkdir(exist_ok=True)
p=D/'src/Launcher.cs';source=p.read_text(encoding='utf-8-sig');start=source.index(' internal static Layout ReadPhysical(params string[] selection)');body=source.index('{',start);depth=1;end=body+1
while depth:
 if source[end]=='{':depth+=1
 elif source[end]=='}':depth-=1
 end+=1
source=source[:body]+'{return Select(MonitorUiAudit.Monitors,selection);}'+source[end:]
fixture=B/'Launcher_fixture.cs';fixture.write_text(source,encoding='utf-8')
csc='C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe'
command=[csc,'/nologo','/target:exe','/platform:x64','/main:MonitorUiAudit','/out:'+str(B/'MonitorUiAudit.exe')]
command+=['/r:'+r for r in ['System.Windows.Forms.dll','System.Drawing.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll']]
command+=[str(D/'src'/n) for n in ['PackCore.cs','Ui.cs','UpdateCore.cs','Hud.cs','Keys.cs','UpdateUI.cs','MouseInputWorker.cs','SupportReport.cs']]+[str(fixture),str(H/'MonitorUiAudit.cs')]
run=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace');assert run.returncode==0,run.stdout+run.stderr
run=subprocess.run([str(B/'MonitorUiAudit.exe'),str(H)],capture_output=True,text=True,encoding='utf-8',errors='replace');assert run.returncode==0,run.stdout+run.stderr
report=json.loads((H/'monitor_ui_regression.json').read_text(encoding='utf-8-sig'));report['source_sha256']={p.relative_to(D).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [D/'src/Launcher.cs',H/'MonitorUiAudit.cs',Path(__file__)]};(H/'monitor_ui_regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(run.stdout.strip())
