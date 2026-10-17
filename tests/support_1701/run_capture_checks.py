from pathlib import Path
import hashlib,json,subprocess
H=Path(__file__).resolve().parent;D=H.parents[1];R=D/'runtime'
vc='C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat'
cmd=H/'run_capture.cmd'
cmd.write_text('@echo off\ncall "'+vc+'" >nul\ncl /nologo /O2 /EHsc /std:c++20 /I"'+str(R/'src')+'" "'+str(H/'capture_test.cpp')+'" /Fe:"'+str(H/'capture_test.exe')+'" /Fo:"'+str(H/'capture_test.obj')+'"\nif errorlevel 1 exit /b1\n"'+str(H/'capture_test.exe')+'"\n',encoding='utf-8')
run=subprocess.run(['cmd','/c',str(cmd)],capture_output=True,text=True,encoding='utf-8',errors='replace')
(H/'capture.log').write_text(run.stdout+run.stderr,encoding='utf-8');assert run.returncode==0,run.stdout+run.stderr
files=[R/'src/support_capture.h',R/'src/mouse_aim.cpp',H/'capture_test.cpp',Path(__file__)]
r={'passed':True,'source_sha256':{p.relative_to(D).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'scope':'Opt-in capture timing and 4Hz bound, token expiry/rearm/cancellation at35/60/180/360 inputHz; no live gameplay claim.'}
(H/'capture_regression.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(run.stdout.strip())
