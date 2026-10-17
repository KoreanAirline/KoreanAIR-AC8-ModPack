"""Count rejected-topology work in actual extracted engine poll functions."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
H=Path(__file__).resolve().parent;D=H.parents[1];R=D/'runtime';B=H/'monitor_fixture';B.mkdir(exist_ok=True)
base=(D/'tests/display_engine_lifecycle_test.py').read_text(encoding='utf-8-sig')
values={}
for node in ast.parse(base).body:
 if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ['prefix','boundaries','fixture']:
  values[node.targets[0].id]=ast.literal_eval(node.value)
window=(R/'src/display_window.h').read_text(encoding='utf-8')
definitions=window[window.index('struct DisplayMonitor'):window.index("// Only this call's coordinate")]+window[window.index('struct ClientMetrics'):window.index('inline ClientMetrics physical_client_metrics')]+window[window.index('struct WindowPlan'):window.index('// Invoke poll/apply_due')]
def extract(s,name):
 start=s.rfind('\n',0,s.index(name+'('))+1;body=s.index('{',start);depth=1;end=body+1
 while depth:
  if s[end]=='{':depth+=1
  elif s[end]=='}':depth-=1
  end+=1
 return s[start:end]
results={}
for variant,path in [('baseline',H/'baseline_display_engine.h'),('current',R/'src/display_engine.h')]:
 engine=path.read_text(encoding='utf-8-sig')
 prefix=values['prefix'].replace('void log_line(const char*,...){}','unsigned refused_logs=0;void log_line(const char* format,...){if(std::strstr(format,"DISPLAY span refused:"))++refused_logs;}')
 boundaries=values['boundaries'].replace('SpanGeometry fixture_geometry;','SpanGeometry fixture_geometry;unsigned fixture_geometry_calls=0;std::vector<DisplayMonitor> fixture_monitors;').replace('SpanGeometry physical_span_geometry(const SpanSelection& selection={}){return fixture_geometry;}','SpanGeometry physical_span_geometry(const SpanSelection& selection={}){++fixture_geometry_calls;return fixture_monitors.empty()?fixture_geometry:choose_span(fixture_monitors,selection);}')
 globals_source=engine[engine.index('using EngineResizeFrame'):engine.index('bool current_engine_viewport')]
 functions='\n'.join(extract(engine,n) for n in ['guarded_engine_window','reshape_engine_span','resize_game_frame','restore_engine_span','poll_engine_span'])
 fixture=values['fixture'].replace('fixture_now=1000;fixture_minimized=false;','fixture_now=1000;ac8display::fixture_geometry_calls=0;ac8display::fixture_monitors.clear();refused_logs=0;fixture_minimized=false;')
 if variant=='current':fixture=fixture.replace('engine_span_plan={};','engine_span_geometry_retry=0;engine_span_geometry_reason=nullptr;engine_span_selection={};engine_span_selection_changed=false;engine_span_topology_revision=0;engine_span_seen_topology=0;engine_span_plan={};')
 required_checks=r'''
    reset(1920,1080);ac8display::fixture_geometry={{},0,0,false,"three_aligned_adjacent_monitors_required"};
    for(unsigned i=0;i<5000;++i){fixture_now=1000+i;require(!poll().valid,"invalid topology does not issue a resize plan");}
    require(engine_calls==0,"refused topology never invokes the renderer");
    std::printf("REJECTED_ENUM=%u REJECTED_LOG=%u\\n",ac8display::fixture_geometry_calls,refused_logs);
'''
 if variant=='current':required_checks+=r'''
    require(ac8display::fixture_geometry_calls==5&&refused_logs==1,"five-second invalid desktop bounded to five enumerations and one explanation");
    fixture_now=6000;ac8display::fixture_geometry.reason="duplicate_monitor_bounds";poll();
    require(ac8display::fixture_geometry_calls==6&&refused_logs==2,"changed rejection reason produces one new explanation");
    for(unsigned i=0;i<999;++i){++fixture_now;poll();}
    require(ac8display::fixture_geometry_calls==6&&refused_logs==2,"same reason cannot spam enumeration or logs between deadlines");
    reset(1920,1080);auto supported=ac8display::fixture_geometry;ac8display::fixture_geometry={{},0,0,false,"three_aligned_adjacent_monitors_required"};
    require(!poll().valid,"hotplug scenario initially unsupported");ac8display::fixture_geometry=supported;++fixture_now;
    require(!poll().valid&&ac8display::fixture_geometry_calls==1,"automatic retry is bounded while waiting for reconnection deadline");
    fixture_now=2000;require(poll().valid&&ac8display::fixture_geometry_calls==2,"valid reconnected triple is discovered within one second");
    reset(1920,1080);supported=ac8display::fixture_geometry;ac8display::fixture_geometry={{},0,0,false,"three_aligned_adjacent_monitors_required"};poll();
    ++fixture_now;poll_engine_span(game_window,false);ac8display::fixture_geometry=supported;++fixture_now;
    require(poll().valid&&ac8display::fixture_geometry_calls==2,"manual off-on retries immediately and does not preserve stale rejection state");
'''
 if variant=='current':required_checks+=r'''
    reset(1920,1080);
    ac8display::fixture_monitors={{{0,-900,1600,0},true,L"A"},{{-1920,0,0,1080},false,L"L"},{{0,0,1920,1080},false,L"C"},{{1920,0,3840,1080},false,L"R"},{{3840,0,5760,1080},false,L"E"}};
    ac8display::SpanSelection chosen;wcscpy_s(chosen.left.data(),32,L"L");wcscpy_s(chosen.center.data(),32,L"C");wcscpy_s(chosen.right.data(),32,L"R");
    auto manual_plan=poll_engine_span(game_window,true,chosen);
    require(manual_plan.valid&&manual_plan.width==5760&&manual_plan.rectangle.left==-1920,"manual triple excludes unrelated primary and extra display");
    require(restore_engine_span(manual_plan.serial,5760,1080,2),"manual plan applies through original engine");
    const auto enum_before=ac8display::fixture_geometry_calls,resize_before=engine_calls;auto full_monitors=ac8display::fixture_monitors;
    engine_span_topology_revision.fetch_add(1,std::memory_order_relaxed);
    require(poll_engine_span(game_window,true,chosen).serial==manual_plan.serial&&ac8display::fixture_geometry_calls==enum_before+1&&engine_calls==resize_before,"display-change event revalidates once without resizing identical geometry");
    require(poll_engine_span(game_window,true,chosen).serial==manual_plan.serial&&ac8display::fixture_geometry_calls==enum_before+1,"unchanged event generation does not query monitors again");
    ++chosen.revision;
    require(poll_engine_span(game_window,true,chosen).serial==manual_plan.serial&&ac8display::fixture_geometry_calls==enum_before+2&&engine_calls==resize_before,"explicit INI Save revalidates screen-only mode without resizing unchanged geometry");
    ac8display::fixture_monitors.erase(ac8display::fixture_monitors.begin()+3);engine_span_topology_revision.fetch_add(1,std::memory_order_relaxed);
    require(!poll_engine_span(game_window,true,chosen).valid&&!engine_span_plan.valid&&engine_calls==resize_before,"unplug event invalidates missing selected device without fallback or resize");
    ac8display::fixture_monitors=full_monitors;engine_span_topology_revision.fetch_add(1,std::memory_order_relaxed);
    manual_plan=poll_engine_span(game_window,true,chosen);
    require(manual_plan.valid&&manual_plan.width==5760&&engine_span_original.width==1920,"reconnect event immediately rebuilds exact roles while preserving original snapshot");
    require(restore_engine_span(manual_plan.serial,5760,1080,2),"reconnect span restores through original engine");
    wcscpy_s(chosen.left.data(),32,L"C");wcscpy_s(chosen.center.data(),32,L"R");wcscpy_s(chosen.right.data(),32,L"E");
    auto changed_plan=poll_engine_span(game_window,true,chosen);
    require(changed_plan.valid&&changed_plan.serial==manual_plan.serial+1&&changed_plan.rectangle.left==0,"changed role selection rebuilds active span exactly once");
    require(engine_span_original.width==1920&&engine_span_original.x==0,"changing roles preserves first pre-span restore snapshot");
    require(restore_engine_span(changed_plan.serial,5760,1080,2),"reselected span applies through original engine");
    require(poll_engine_span(game_window,true,chosen).serial==changed_plan.serial,"unchanged selected devices do not re-enumerate or resize");
    wcscpy_s(chosen.right.data(),32,L"MISSING");
    require(!poll_engine_span(game_window,true,chosen).valid&&!engine_span_plan.valid,"missing changed device invalidates old active expansion plan without fallback");
    auto off_manual=poll_engine_span(game_window,false,chosen);
    require(off_manual.valid&&!off_manual.span&&restore_engine_span(off_manual.serial,1920,1080,1),"off after invalid selection restores original window");
    require(ac8display::fixture_client.width==1920&&ac8display::fixture_client.x==0,"manual selection off restores initial resolution and monitor origin");
'''
 fixture=fixture.replace('int main(){','int main(){'+required_checks)
 source=prefix+definitions+boundaries+globals_source+functions+fixture
 cpp=B/('retry_'+variant+'.cpp');cpp.write_text(source,encoding='utf-8')
 vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
 command=B/('retry_'+variant+'.cmd')
 command.write_text('@echo off\ncall "'+vc+'" >nul\ncl /nologo /EHsc /std:c++20 /Od "'+str(cpp)+'" /Fe:"'+str(B/('retry_'+variant+'.exe'))+'" /Fo:"'+str(B/('retry_'+variant+'.obj'))+'" /link user32.lib\nif errorlevel 1 exit /b 1\n"'+str(B/('retry_'+variant+'.exe'))+'"\nexit /b %errorlevel%\n',encoding='utf-8')
 run=subprocess.run(['cmd','/c',str(command)],capture_output=True,text=True,encoding='utf-8',errors='replace');assert run.returncode==0,run.stdout+run.stderr
 found=re.search(r'REJECTED_ENUM=(\d+) REJECTED_LOG=(\d+)',run.stdout);assert found,run.stdout
 results[variant]=dict(enumerations=int(found[1]),logs=int(found[2]),result=run.stdout.strip(),compiled_source_sha256=hashlib.sha256(cpp.read_bytes()).hexdigest())
assert results['baseline']['enumerations']==5000 and results['baseline']['logs']==5000
assert results['current']['enumerations']==5 and results['current']['logs']==1
report=dict(passed=True,duration_ms=5000,polls=5000,results=results,sources={p.relative_to(D).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'src/display_engine.h',R/'src/display_window.h',H/'baseline_display_engine.h',Path(__file__)]},scope='Extracted production poll, lifecycle and resize/restore functions against mocked platform and clock. This counts avoided calls, not FPS gains or live-hardware certification.')
(H/'display_retry_regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('PASS: unsupported desktop over 5000 polls: baseline5000 enumerations/5000 logs; current5 enumerations/1 log. Automatic reconnect <=1s, immediate manual retry and existing lifecycle checks pass.')
