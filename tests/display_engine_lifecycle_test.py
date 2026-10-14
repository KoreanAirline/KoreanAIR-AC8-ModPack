"""Compile actual engine-span integration functions against mocked host boundaries.

This verifies request lifecycle and original-engine delegation, not the user's
GPU, Slate implementation, or physical FHD/QHD monitors. No game is started and
no installed game file or HWND is touched.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

RUNTIME = Path(__file__).resolve().parent.parent / "runtime"
engine = (RUNTIME / "src/display_engine.h").read_text(encoding="utf-8")
window = (RUNTIME / "src/display_window.h").read_text(encoding="utf-8")


def function(source, name):
    start = source.rfind("\n", 0, source.index(name + "(")) + 1
    body = source.index("{", start)
    depth, end = 1, body + 1
    while depth:
        if source[end] == "{":
            depth += 1
        elif source[end] == "}":
            depth -= 1
        end += 1
    return source[start:end]


definitions = window[window.index("struct DisplayMonitor"):window.index("// Only this call's coordinate")]
definitions += window[window.index("struct ClientMetrics"):window.index("inline ClientMetrics physical_client_metrics")]
definitions += window[window.index("struct WindowPlan"):window.index("// Invoke poll/apply_due")]
globals_source = engine[engine.index("using EngineResizeFrame"):engine.index("bool current_engine_viewport")]

prefix = r'''
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <array>
#include <vector>
#include <atomic>
#include <mutex>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#define __try try
#define __except(...) catch(...)
unsigned checks=0;
void require(bool ok,const char* why){++checks;if(!ok){std::fprintf(stderr,"FAIL: %s\n",why);std::exit(1);}}
void log_line(const char*,...){}
uint64_t fixture_now=1000;
uint64_t fixture_clock(){return fixture_now;}
#define GetTickCount64 fixture_clock
bool fixture_minimized=false;
BOOL fixture_iconic(HWND){return fixture_minimized;}
#define IsIconic fixture_iconic
std::atomic<bool> running{true};
HWND game_window=reinterpret_cast<HWND>(0x1000);
namespace ac8display {
'''

boundaries = r'''
ClientMetrics fixture_client;
SpanGeometry fixture_geometry;
ClientMetrics physical_client_metrics(HWND window){return window==game_window?fixture_client:ClientMetrics{};}
SpanGeometry physical_span_geometry(){return fixture_geometry;}
}
std::array<std::array<unsigned char,0x300>,3> fixture_viewports{};
std::array<std::array<unsigned char,0x40>,3> fixture_natives{};
std::array<unsigned char,0x510> fixture_scene{};
void* fixture_viewport=fixture_viewports[0].data();
void* fixture_native=fixture_natives[0].data();
HWND fixture_owner=game_window;
int fixture_render_w=1920,fixture_render_h=1080;
bool fixture_owner_valid=true,fixture_render_valid=true;
unsigned engine_calls=0,reshape_calls=0,cache_calls=0,move_calls=0;
int captured_w=0,captured_h=0,captured_mode=-1;
uintptr_t live_engine_viewport(){return reinterpret_cast<uintptr_t>(fixture_viewport);}
bool current_engine_viewport(void* candidate){return fixture_owner_valid&&candidate==fixture_viewport;}
bool current_engine_window(void* candidate){return fixture_owner_valid&&candidate==fixture_native&&fixture_owner==game_window;}
uintptr_t owning_scene_window(uintptr_t viewport){return fixture_owner_valid&&viewport==live_engine_viewport()?reinterpret_cast<uintptr_t>(fixture_scene.data()):0;}
BOOL fixture_iswindow(HWND window){return fixture_owner_valid&&window==fixture_owner;}
DWORD fixture_window_thread(HWND window,DWORD* process){if(process)*process=fixture_iswindow(window)?GetCurrentProcessId():0;return fixture_iswindow(window)?1:0;}
#define IsWindow fixture_iswindow
#define GetWindowThreadProcessId fixture_window_thread
bool read_display_viewport_dimensions(int& w,int& h){w=h=0;if(!fixture_render_valid)return false;w=fixture_render_w;h=fixture_render_h;return true;}
void sync_window_cached_origin(void*,int,int){++cache_calls;}
bool install_engine_span(){return true;}
void __fastcall fixture_move(void*,int x,int y){++move_calls;ac8display::fixture_client.x=x;ac8display::fixture_client.y=y;}
HMODULE fixture_module(const wchar_t*){return reinterpret_cast<HMODULE>(reinterpret_cast<uintptr_t>(&fixture_move)-0x1B44B10);}
#define GetModuleHandleW fixture_module
template<typename T>void put(void* at,T value){std::memcpy(at,&value,sizeof value);}
void bind_owner(){
    const auto base=reinterpret_cast<uintptr_t>(fixture_module(nullptr));
    put(fixture_viewport,base+0xBE7DDC8);
    put(fixture_scene.data()+0x508,reinterpret_cast<uintptr_t>(fixture_native));
    put(fixture_native,base+0xB4CF6E0);
    put(static_cast<unsigned char*>(fixture_native)+0x28,fixture_owner);
}
'''

fixture = r'''
void __fastcall original_reshape_fixture(void* native,int x,int y,int w,int h){
    require(native==fixture_native,"original reshape delegated to current native owner");
    ++reshape_calls;ac8display::fixture_client={x,y,w,h,true};
}
void __fastcall original_resize_fixture(void* viewport,uint32_t w,uint32_t h,int mode){
    require(viewport==fixture_viewport,"original engine resize delegated to current viewport");
    ++engine_calls;captured_w=w;captured_h=h;captured_mode=mode;
    reshape_engine_span(fixture_native,0,0,int(w),int(h));
    fixture_render_w=w;fixture_render_h=h;
}
void reset(int w,int h){
    fixture_now=1000;fixture_minimized=false;fixture_owner_valid=fixture_render_valid=true;
    game_window=fixture_owner=reinterpret_cast<HWND>(0x1000);
    fixture_viewport=fixture_viewports[0].data();fixture_native=fixture_natives[0].data();bind_owner();
    fixture_render_w=w;fixture_render_h=h;
    ac8display::fixture_client={0,0,w,h,true};
    ac8display::fixture_geometry=ac8display::choose_span({{{-w,0,0,h},false},{{0,0,w,h},true},{{w,0,w*2,h},false}});
    engine_span_plan={};engine_span_original={};engine_span_desired=false;
    engine_span_installed=false;engine_span_failed=false;engine_span_sequence=0;engine_span_acknowledged=0;
    engine_span_recovery.reset();engine_span_scope=false;scoped_engine_span={};
    engine_span_last_window=0;engine_span_resize_calls=0;engine_span_slate_calls=0;
    original_engine_resize=&original_resize_fixture;original_window_reshape=&original_reshape_fixture;
    engine_calls=reshape_calls=cache_calls=move_calls=0;
}
ac8display::WindowPlan poll(){bind_owner();return poll_engine_span(game_window,true);}
void mismatch(int w,int h){ac8display::fixture_client={0,0,w,h,true};fixture_render_w=w;fixture_render_h=h;}
void expect_target(int w,int h){
    const auto actual=ac8display::fixture_client;
    require(actual.valid&&actual.width==w*3&&actual.height==h&&actual.x==-w,"original engine path produces planned triple client and origin");
    require(fixture_render_w==w*3&&fixture_render_h==h,"original engine delegation retains render viewport agreement");
    require(captured_mode==2,"span recovery requests engine windowed mode");
    require(!engine_span_scope,"scope restored after original engine resize");
}
void scenario(int w,int h){
    reset(w,h);
    auto plan=poll();require(plan.valid&&plan.serial==1&&plan.width==w*3&&plan.height==h,"initial resolution serial uses detected FHD/QHD dimensions");
    require(engine_calls==0,"polling does not mutate window or engine");
    require(restore_engine_span(plan.serial,plan.width,plan.height,2),"ack recovers same-value UGS no-op through original engine");
    expect_target(w,h);require(engine_calls==1&&reshape_calls==1,"one native engine/reshape request for initial serial");
    require(restore_engine_span(plan.serial,plan.width,plan.height,2)&&engine_calls==1,"duplicate acknowledgement is idempotent");
    fixture_now+=3000;require(poll().serial==plan.serial,"verified span makes no extra resolution command");
    // The hooked ResizeFrame still handles the normal menu -> mission path.
    resize_game_frame(fixture_viewport,w,h,1);expect_target(w,h);
    require(engine_calls==2&&poll().serial==plan.serial,"normal mission ResizeFrame needs no recovery serial");
    // Simulate a menu resize through a path that bypassed ResizeFrame.
    mismatch(w,h);fixture_now+=1000;
    require(poll().serial==plan.serial,"menu reset must first settle");
    fixture_now+=749;require(poll().serial==plan.serial,"750ms mismatch debounce enforced");
    ++fixture_now;auto recovery=poll();require(recovery.serial==plan.serial+1,"stable menu reset receives a new command serial");
    require(engine_calls==2,"observation schedules command without HWND/engine mutation");
    require(restore_engine_span(recovery.serial,w*3,h,2),"menu recovery acknowledgement accepted");expect_target(w,h);
    require(engine_calls==3,"same cached UGS settings still cause one original engine resize");
    // A render-only reset is detected even while the HWND still spans.
    fixture_render_w=w;fixture_now+=2000;require(poll().serial==recovery.serial,"render-only mismatch first settles");
    fixture_now+=750;recovery=poll();require(recovery.serial==3,"render-only reset requests recovery");
    require(restore_engine_span(recovery.serial,w*3,h,2),"render-only acknowledgement accepted");expect_target(w,h);
    // Recreate viewport and window while cached old HWND remains valid.
    fixture_viewport=fixture_viewports[1].data();fixture_native=fixture_natives[1].data();
    fixture_owner=reinterpret_cast<HWND>(0x1100);mismatch(w,h);fixture_now+=2000;
    require(poll().serial==recovery.serial&&game_window==fixture_owner,"guarded live owner rebinds cached HWND and starts recreation settling");
    fixture_now+=750;recovery=poll();require(recovery.serial==4,"new viewport/native window reset requests bounded recovery");
    require(restore_engine_span(recovery.serial,w*3,h,2),"recreated owner recovers through current original engine");expect_target(w,h);
    require(engine_span_original.width==w&&engine_span_original.height==h&&engine_span_original.x==0,"pre-span restore snapshot survives menu/owner recreation");
    // Minimize/alt-tab produces no recovery or resize, even beyond all timers.
    const auto before=engine_calls;fixture_minimized=true;mismatch(0,0);fixture_now+=5000;
    require(poll().serial==recovery.serial&&engine_calls==before,"minimize does not reopen or resize window");
    fixture_minimized=false;mismatch(w,h);fixture_now+=100;
    require(poll().serial==recovery.serial,"restore-from-minimize restarts mismatch settling");
    fixture_now+=750;require(poll().serial==recovery.serial&&engine_span_recovery.exhausted(),"three-per-minute recovery limit stops repeated competing resets");
    fixture_viewport=fixture_viewports[2].data();fixture_native=fixture_natives[2].data();fixture_now+=5000;
    require(poll().serial==recovery.serial&&engine_calls==before,"owner churn cannot bypass exhausted recovery budget");
    // Manual off remains actionable with an exhausted recovery budget.
    auto off=poll_engine_span(game_window,false);require(off.valid&&!off.span,"off transition cancels recovery");
    require(restore_engine_span(off.serial,w,h,1),"off restores original resolution via current native owner");
    require(ac8display::fixture_client.width==w&&ac8display::fixture_client.height==h&&ac8display::fixture_client.x==0,"off preserves original monitor origin and resolution");
    require(engine_calls==before+1&&move_calls==2,"off delegates one original engine resize and original move API");
    // Failed/stale owners and stale acknowledgements cannot call the engine.
    require(!restore_engine_span(recovery.serial,w*3,h,2)&&engine_calls==before+1,"stale span ack after off refused");
    plan=poll();fixture_owner_valid=false;
    require(!restore_engine_span(plan.serial,w*3,h,2)&&engine_calls==before+1,"unverified native owner refuses engine call");
    fixture_now+=10000;require(poll().serial==plan.serial,"unverified owner cannot schedule lifecycle recovery");
    fixture_owner_valid=true;fixture_render_valid=false;
    require(!restore_engine_span(plan.serial,w*3,h,2)&&engine_calls==before+1,"unmeasured render viewport refuses engine call");
}
int main(){
    scenario(1920,1080);scenario(2560,1440);
    reset(1920,1080);uintptr_t native=0;
    require(guarded_engine_window(live_engine_viewport(),native)==fixture_owner&&native==reinterpret_cast<uintptr_t>(fixture_native),"actual live-owner guard validates pinned viewport/native vtables");
    put(fixture_viewport,uintptr_t(0));require(!guarded_engine_window(live_engine_viewport(),native)&&native==0,"actual guard rejects unpinned viewport");bind_owner();
    put(fixture_native,uintptr_t(0));require(!guarded_engine_window(live_engine_viewport(),native)&&native==0,"actual guard rejects unpinned native window");bind_owner();
    put(fixture_scene.data()+0x508,uintptr_t(0));require(!guarded_engine_window(live_engine_viewport(),native),"actual guard rejects incomplete native-owner binding");bind_owner();
    put(static_cast<unsigned char*>(fixture_native)+0x28,reinterpret_cast<HWND>(0x9999));require(!guarded_engine_window(live_engine_viewport(),native),"actual guard rejects foreign/destroyed HWND");
    // Complete verified-span minute replenishes an actually exhausted budget.
    reset(1920,1080);auto plan=poll();require(restore_engine_span(plan.serial,5760,1080,2),"stable-budget fixture enabled");
    for(int i=0;i<3;++i){mismatch(1920,1080);fixture_now+=2000;poll();fixture_now+=750;plan=poll();require(restore_engine_span(plan.serial,5760,1080,2),"stable-budget recovery acknowledged");}
    mismatch(1920,1080);fixture_now+=2000;poll();fixture_now+=750;
    require(poll().serial==plan.serial&&engine_span_recovery.exhausted(),"stable-budget fixture exhausts three-per-minute limit");
    resize_game_frame(fixture_viewport,1920,1080,1);++fixture_now;poll();fixture_now+=59999;poll();
    require(engine_span_recovery.exhausted(),"shorter-than-minute verification cannot replenish commands");
    ++fixture_now;poll();require(!engine_span_recovery.exhausted()&&engine_span_recovery.count()==0,"full verified minute replenishes exhausted budget");
    mismatch(1920,1080);++fixture_now;poll();fixture_now+=750;
    require(poll().serial==plan.serial+1,"later genuine reset recovers after verified span replenishes budget");
    // Five unresolved requests cannot turn into an indefinite low-frequency loop.
    reset(1920,1080);plan=poll();fixture_now+=2000;
    for(int i=0;i<5;++i){poll();fixture_now+=750;plan=poll();fixture_now+=61000;}
    poll();fixture_now+=750;require(poll().serial==plan.serial&&engine_span_recovery.exhausted(),"five unresolved commands stop even across minute boundaries");
    std::printf("PASS: %u actual engine poll/ack/ResizeFrame/reshape lifecycle checks for 5760x1080 and 7680x1440; mocked platform boundaries, no game hardware claim.\n",checks);
}
'''

functions = "\n".join(function(engine, name) for name in (
    "guarded_engine_window", "reshape_engine_span", "resize_game_frame", "restore_engine_span", "poll_engine_span"))
build = RUNTIME / "build/display_engine_lifecycle_fixture"
build.mkdir(parents=True, exist_ok=True)
(build / "display_engine_lifecycle_test.cpp").write_text(
    prefix + definitions + boundaries + globals_source + functions + fixture, encoding="utf-8")
vcvars = Path("C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat")
(build / "run.cmd").write_text(
    f'@echo off\ncall "{vcvars}" >nul\n'
    'cl /nologo /EHsc /std:c++20 /Od display_engine_lifecycle_test.cpp /Fe:display_engine_lifecycle_test.exe >build.log 2>&1\n'
    'if errorlevel 1 exit /b 1\ndisplay_engine_lifecycle_test.exe\n')
result = subprocess.run(["cmd", "/c", str(build / "run.cmd")], cwd=build, capture_output=True, text=True)
print(result.stdout, end="")
if result.returncode:
    print(result.stderr, end="")
    print((build / "build.log").read_text())
    sys.exit(result.returncode)
output = result.stdout.strip()
checks = re.search(r'PASS: (\d+) actual engine', output)
assert checks and int(checks[1]) >= 152, output
evidence = dict(
    passed=True, checks=int(checks[1]), result=output,
    source_sha256={path: hashlib.sha256((RUNTIME.parent / path).read_bytes()).hexdigest() for path in (
        'runtime/src/display_engine.h', 'runtime/src/display_window.h', 'runtime/scripts/display.lua',
        'tests/display_engine_lifecycle_test.py', 'runtime/lua_display_resolution_lifecycle_test.lua')},
    compiled_fixture_sha256=hashlib.sha256((build / 'display_engine_lifecycle_test.cpp').read_bytes()).hexdigest(),
    tested_production_functions=['guarded_engine_window', 'poll_engine_span', 'restore_engine_span', 'resize_game_frame', 'reshape_engine_span', 'EngineSpanRecovery.observe'],
    viewport_cases=['5760x1080', '7680x1440'],
    scope='Actual production engine-span functions compiled/executed with pinned owner memory fixtures and mocked clock, native engine/reshape delegates and physical client measurements; no game process, real HWND or graphics hardware touched.',
    live_fhd_verified=False, live_qhd_after_change_verified=False,
    limitations=['Latest real log observed only the existing QHD path; reported FHD menu reset was not physically reproduced.',
                 'Mocked original engine delegate proves call ownership and dimensions, not internal Slate/RHI same-size behavior or real backbuffer recreation.',
                 'Regression covers bounded settled client/render reset recovery, owner recreation, minimize, idempotent/stale ack, off snapshot and command-budget exhaustion.'])
(RUNTIME.parent / 'tests/display_engine_lifecycle_evidence.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
