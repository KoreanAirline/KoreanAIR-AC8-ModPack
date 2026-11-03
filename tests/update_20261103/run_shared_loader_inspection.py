"""Compile/read-only provider detection tests; never execute downloaded code."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;D=HERE.parents[1]
CSC=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
DOWNLOAD=Path('<USER_HOME>/Downloads/ACE8 Mod Loader 1.3.1 (Windows Version) 64 1.3.1 2026-10-23T22-20Z pZViQ1V4u')
source=next(DOWNLOAD.rglob('UE4SS.dll')).parent.parent
fixture=HERE/('shared_loader_inspection_'+datetime.now(timezone.utc).strftime('%H%M%S_%f'))
exe=HERE/'SharedLoaderInspectionTests.exe'
refs=['System.Windows.Forms.dll','System.Drawing.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll']
sources=(D/'src/PackCore.cs',D/'src/CampaignSubtitles.cs',HERE/'SharedLoaderInspectionTests.cs',Path(__file__))
command=[str(CSC),'/nologo','/target:exe','/platform:x64','/optimize+','/out:'+str(exe)]+['/r:'+x for x in refs]+[str(p)for p in sources if p.suffix=='.cs']
build=subprocess.run(command,capture_output=True,text=True)
if build.returncode:raise RuntimeError(build.stdout+build.stderr)
test=subprocess.run([str(exe),str(fixture),str(source)],capture_output=True,text=True)
report=dict(passed=test.returncode==0,output=test.stdout,error=test.stderr,
    source_sha256={str(p.relative_to(D)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    downloaded_code_executed=False,game_modified=False)
(HERE/'shared_loader_inspection_results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(test.stdout)
if test.returncode:raise RuntimeError(test.stderr)
