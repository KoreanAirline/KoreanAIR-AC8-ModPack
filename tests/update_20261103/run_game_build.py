from pathlib import Path
import subprocess,json,hashlib
H=Path(__file__).resolve().parent;D=H.parents[1]
refs=['System.Windows.Forms.dll','System.Drawing.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll'];exe=H/'GameBuildTests.exe'
sources=[D/'src/PackCore.cs',D/'src/CampaignSubtitles.cs',D/'src/GameInputCompatibility.cs',H/'GameBuildTests.cs',Path(__file__)]
cmd=['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/target:exe','/platform:x64','/out:'+str(exe)]+['/r:'+x for x in refs]+[str(p)for p in sources if p.suffix=='.cs']
subprocess.run(cmd,check=True)
r=subprocess.run([str(exe),'E:/SteamLibrary/steamapps/common/ACE COMBAT 8'],capture_output=True,text=True)
(H/'game_build_results.json').write_text(json.dumps(dict(passed=r.returncode==0,output=r.stdout,error=r.stderr,source_sha256={str(p.relative_to(D)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources}),indent=2)+'\n')
print(r.stdout)
if r.returncode:raise RuntimeError(r.stderr)
