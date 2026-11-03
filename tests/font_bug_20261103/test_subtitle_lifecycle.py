from pathlib import Path
import hashlib,json,subprocess,tempfile
H=Path(__file__).resolve().parent;D=H.parents[1]
exe=H/'SubtitleLifecycleTests.exe'
sources=[D/'src/PackCore.cs',D/'src/CampaignSubtitles.cs',D/'src/GameInputCompatibility.cs',H/'SubtitleLifecycleTests.cs']
refs=['System.Windows.Forms.dll','System.Drawing.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll']
subprocess.run(['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/target:exe','/define:CAMPAIGN_SUBTITLES_TEST','/platform:x64','/out:'+str(exe),*['/r:'+x for x in refs],*map(str,sources)],check=True)
r=subprocess.run([str(exe),tempfile.gettempdir()],capture_output=True,text=True)
report=dict(passed=r.returncode==0,output=r.stdout,error=r.stderr,source_sha256={p.relative_to(D).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[Path(__file__)]},game_modified=False)
(H/'subtitle_lifecycle_results.json').write_text(json.dumps(report,indent=2)+'\n')
print(r.stdout);assert r.returncode==0,r.stderr
