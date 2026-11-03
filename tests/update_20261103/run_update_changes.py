"""Headless WinForms fixture of the actual updater source, no network fetch."""
from pathlib import Path
import hashlib,json,subprocess
H=Path(__file__).resolve().parent;D=H.parents[1]
CSC=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe');exe=H/'UpdateChangesTests.exe'
refs=['System.Windows.Forms.dll','System.Drawing.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll']
names=['PackCore.cs','CampaignSubtitles.cs','Ui.cs','UpdateCore.cs','Launcher.cs','Hud.cs','Keys.cs','UpdateUI.cs','MouseInputWorker.cs','SupportReport.cs']
args=[str(CSC),'/nologo','/target:exe','/main:UpdateChangesTests','/platform:x64','/optimize+','/out:'+str(exe)]+['/r:'+x for x in refs]+[str(D/'src'/x)for x in names]+[str(H/'UpdateChangesTests.cs')]
result=subprocess.run(args,capture_output=True,text=True)
if result.returncode:raise RuntimeError(result.stdout+result.stderr)
result=subprocess.run([str(exe),str(H)],capture_output=True,text=True,encoding='utf-8',errors='replace')
print(result.stdout)
report=json.loads((H/'update_changes_results.json').read_text(encoding='utf-8-sig'))
report['source_sha256']={'src/'+x:hashlib.sha256((D/'src'/x).read_bytes()).hexdigest()for x in names}
(H/'update_changes_results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
if result.returncode:raise RuntimeError(result.stderr or report['error'])
