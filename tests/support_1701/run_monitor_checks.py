"""Exercise the actual C# and native topology selectors with shared desktop cases.

No display configuration, HWND or installed file is changed. Refresh rate is
recorded in case data but intentionally does not participate in span selection.
"""
from pathlib import Path
import hashlib,json,subprocess,zipfile
H=Path(__file__).resolve().parent;D=H.parents[1];R=D/'runtime'
B=H/'monitor_fixture';B.mkdir(exist_ok=True)
cases=json.loads((H/'monitor_cases.json').read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
launcher=(D/'src/Launcher.cs').read_text(encoding='utf-8-sig')
helper=launcher[launcher.index('internal static class DisplayTopology {'):].split('internal sealed class MonitorLayoutDiagram',1)[0]
prefix='using System;using System.Drawing;using System.Linq;using System.Collections.Generic;using System.Runtime.InteropServices;\n'
cs=[prefix,helper,'\nclass MonitorFixture {static void Main(){']
for i,c in enumerate(cases):
    rows=','.join('new DisplayTopology.Monitor(new Rectangle(%d,%d,%d,%d),%s,"%s")'%(m['x'],m['y'],m['w'],m['h'],str(m['primary']).lower(),m['device']) for m in c['monitors'])
    cs.append('{var r=DisplayTopology.Select(new DisplayTopology.Monitor[]{'+rows+'},new string[]{'+','.join('"'+v+'"' for v in c.get('selection',[]))+'});Console.WriteLine("%d\\t"+(r.CanSpan?1:0)+"\\t"+r.SpanBounds.Width+"\\t"+r.SpanBounds.Height+"\\t"+r.SpanBounds.X+"\\t"+r.SpanBounds.Y+"\\t"+r.Reason);}'%i)
cs.append('}}')
(B/'monitor_cs.cs').write_text(''.join(cs),encoding='utf-8')
cpp=['#include "src/display_window.h"\n#include <cstdio>\nint main(){\n'];baseline_cpp=[]
for i,c in enumerate(cases):
    oldrows=','.join('{{%d,%d,%d,%d},%s}'%(m['x'],m['y'],m['x']+m['w'],m['y']+m['h'],str(m['primary']).lower()) for m in c['monitors'])
    rows=','.join('{{%d,%d,%d,%d},%s,L"%s"}'%(m['x'],m['y'],m['x']+m['w'],m['y']+m['h'],str(m['primary']).lower(),m['device']) for m in c['monitors'])
    selection=c.get('selection',['','','']);setup='ac8display::SpanSelection selected;'+''.join('wcscpy_s(selected.%s.data(),32,L"%s");'%(role,value) for role,value in zip(['left','center','right'],selection))
    oldline='{auto r=ac8display::choose_span({'+oldrows+'});std::printf("%d\\t%%d\\t%%d\\t%%d\\t%%ld\\t%%ld\\t%%s\\n",r.valid?1:0,r.width,r.height,r.bounds.left,r.bounds.top,r.reason);}'%i
    baseline_cpp.append(oldline)
    cpp.append('{'+setup+'auto r=ac8display::choose_span({'+rows+'},selected);std::printf("%d\\t%%d\\t%%d\\t%%d\\t%%ld\\t%%ld\\t%%s\\n",r.valid?1:0,r.width,r.height,r.bounds.left,r.bounds.top,r.reason);}'%i)
cpp.append('}')
(B/'monitor_native.cpp').write_text(''.join(cpp),encoding='utf-8')
with zipfile.ZipFile(H/'monitor_baseline_sources.zip') as z:old=z.read('display_window.h').decode('utf-8-sig')
a=old.index('struct DisplayMonitor');b=old.index('// Only this call\'s coordinate',a)
old_defs=old[a:b]
old_cpp=('#include "src/display_window.h"\n#include <cstdio>\nint main(){\n'+''.join(baseline_cpp)+'}').replace('#include "src/display_window.h"','#define NOMINMAX\n#include <windows.h>\n#include <vector>\n#include <cstdint>\nnamespace ac8display{\n'+old_defs+'\n}')
(B/'monitor_baseline.cpp').write_text(old_cpp,encoding='utf-8')
vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
csc=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
command=[str(csc),'/nologo','/target:exe','/r:System.Drawing.dll','/out:'+str(B/'monitor_cs.exe'),str(B/'monitor_cs.cs')]
compiled=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace');assert compiled.returncode==0,compiled.stdout+compiled.stderr
cmd='@echo off\r\ncall "'+vc+'" >nul\r\nif errorlevel 1 exit /b 1\r\n'
for name in ['monitor_native','monitor_baseline']:
    cmd+='cl /nologo /std:c++20 /EHsc /O2 /I"'+str(R)+'" "'+str(B/(name+'.cpp'))+'" /Fe:"'+str(B/(name+'.exe'))+'" /Fo:"'+str(B/(name+'.obj'))+'" /link user32.lib\r\nif errorlevel 1 exit /b 1\r\n'
cmd+='exit /b 0\r\n'
(B/'build_fixture.cmd').write_text(cmd,encoding='utf-8')
compiled=subprocess.run(['cmd','/c',str(B/'build_fixture.cmd')],capture_output=True,text=True,encoding='utf-8',errors='replace');assert compiled.returncode==0,compiled.stdout+compiled.stderr

def run(name):
    p=subprocess.run([str(B/(name+'.exe'))],capture_output=True,text=True,encoding='utf-8',errors='replace');assert p.returncode==0,p.stdout+p.stderr
    rows=[]
    for line in p.stdout.splitlines():
        parts=line.split('\t');assert len(parts)==7,line
        rows.append([int(v) for v in parts[:6]]+[parts[6]])
    assert len(rows)==len(cases)
    return rows
native,managed,old=map(run,['monitor_native','monitor_cs','monitor_baseline'])
assert native==managed,'Launcher/native topology decision mismatch'
for i,(c,row) in enumerate(zip(cases,native)):
    assert row[:2]==[i,int(c['valid'])],(c['name'],row)
    if c['valid']:assert row[2:6]==[c['width'],c['height'],c['left'],c['top']],(c['name'],row)
negative=[c['name'] for c,o,n in zip(cases,old,native) if c['valid'] and o[1]==0 and n[1]==1]
assert len(negative)>=16,negative
# The old centered triple keeps exactly its former geometry, even with extras.
for c,o,n in zip(cases,old,native):
    if o[1] and 'selection' not in c:assert o[:6]==n[:6],('existing geometry changed',c['name'],o,n)
report=dict(passed=True,cases=len(cases),selector_comparisons=len(cases)*2,baseline_false_negatives_fixed=negative,
    hz='Mixed 60/75/144/180 Hz case metadata is not a geometry constraint.',
    constraints='Three contiguous equal-resolution, top/bottom-aligned displays containing the primary. Prefer primary-centered triple when extra screens exist. Single wide surface is not physical triple span.',
    sources={p.relative_to(D).as_posix():sha(p) for p in [D/'src/Launcher.cs',R/'src/display_window.h',H/'monitor_cases.json',Path(__file__),H/'monitor_baseline_sources.zip']})
(H/'monitor_regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('PASS: %d shared C#/native topology cases; %d exact baseline false negatives fixed; existing centered triples preserved.'%(len(cases),len(negative)))
