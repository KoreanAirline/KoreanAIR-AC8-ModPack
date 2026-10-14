"""Execute the extracted production overlay loop against counted OS boundaries.

No native window is created. Geometry, clock, timer failure and publications
are deterministic; production refresh scheduling, dirty policy and wait/control
flow are unchanged. This is a lifecycle/cadence test, not measured game FPS.
"""
from pathlib import Path
import hashlib,json,subprocess

T=Path(__file__).resolve().parent;R=T.parent/'runtime';B=R/'build'
source=(R/'src/mouse_aim.cpp').read_text()
start=source.index('void overlay_loop() {');end=source.index('{',start)+1;depth=1
while depth:
    depth+=(source[end]=='{')-(source[end]=='}');end+=1
loop=source[start:end]
assert loop.count('schedule.consume(')==2 and 'schedule.active()&&timer.arm(remaining)' in loop
assert 'flush()' not in loop and 'Sleep(16)' not in loop
production_loop=loop
for native,fake in [('ac8display::PhysicalPixelScope physical_pixels;','FakePhysicalPixels physical_pixels;'),
                    ('ac8overlay::MonitorRefresh refresh;','FakeMonitorRefresh refresh;'),
                    ('ac8overlay::RefreshTimer timer;','FakeRefreshTimer timer;')]:
    assert loop.count(native)==1;loop=loop.replace(native,fake)

prelude=r'''
#include "overlay_refresh.h"
#include "overlay_update_policy.h"
#include <atomic>
#include <mutex>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <vector>
unsigned checks=0;
void require(bool value,const char* label){++checks;if(!value){std::fprintf(stderr,"FAIL: %s\n",label);std::exit(1);}}
uint64_t qpc=0,revision=1,frame_index=0;
unsigned iterations=0,limit=500,rate=180,draws=0,hides=0,arms=0,cancels=0,display_invalidations=0;
unsigned period_poll=0,failed_waits=0,positive_waits=0;
bool input=true,present_ok=true,placement_ok=true,timer_ok=true,clock_ok=true,
     visible=true,showing=false,armed=false,hide_midway=false,message_pending=false,wait_ok=true;
uint64_t timer_deadline=0;
std::vector<uint64_t> draw_times;
std::vector<uint32_t> backing;
std::atomic<bool> running{true},hud_enabled{true},game_paused{false},gaze_active{false},
    active{true},enabled{true},perf_enabled{false};
std::atomic<uintptr_t> aircraft{2};
std::atomic<float> target_pitch{},target_yaw{},camera_pitch{},camera_yaw{};
HWND game_window=reinterpret_cast<HWND>(2),overlay_window=nullptr;
HINSTANCE self_module=reinterpret_cast<HINSTANCE>(3);
std::mutex hud_frame_mutex,hud_settings_mutex;
HANDLE hud_overlay_wake=nullptr;
ac8hud::Settings hud_settings;
namespace flight {
struct V{float x=1,y=0,z=0;};struct Basis{V f;};struct Point{int x=300,y=300;bool visible=true;};
Point project_marker(V,Basis,V,float,int,int){return {};}
}
struct HudFrame {uintptr_t pawn=2;int width=5760,height=1080;uint64_t tick=1000,publication=1;flight::V aim,offset;flight::Basis pose,view;float fov=90;};
HudFrame hud_frame;
namespace ac8pack {const char* version="fixture";}
namespace ac8profile {std::atomic<bool> enabled{false};}
std::atomic<uint64_t> overlay_uploads{0};
struct Features {bool diagnostics=false;} pack_features;
struct FakePhysicalPixels {};
struct FakeMonitorRefresh {
    unsigned update(HWND,const RECT&,uint64_t){++period_poll;return rate;}
    void invalidate(){++display_invalidations;}
};
struct FakeRefreshTimer {
    HANDLE handle()const{return reinterpret_cast<HANDLE>(12);}
    bool arm(uint64_t remaining){++arms;if(!timer_ok)return false;armed=true;timer_deadline=qpc+std::max<uint64_t>(1,remaining);return true;}
    void cancel(){++cancels;armed=false;}
};
namespace ac8overlay {
struct GlyphPoint{int x,y;bool visible;};struct GlyphResult{bool success,changed,uploaded;};
class GlyphOverlay {
 bool own_shown=false;unsigned id;
 inline static unsigned created=0;
public:
 explicit GlyphOverlay(HINSTANCE):id(++created){}
 HWND handle()const{return reinterpret_cast<HWND>(uintptr_t(100+id));}
 bool needs_restore()const{return false;}
 size_t backing_bytes()const{return 5000;}
 GlyphResult present(HWND,const RECT&,GlyphPoint,const ac8hud::Glyph&,HWND=HWND_TOPMOST,bool=true){
  if(id%2==0){++draws;draw_times.push_back(qpc);}own_shown=present_ok&&placement_ok;showing=own_shown;
  return {present_ok&&placement_ok,true,true};
 }
 bool hide(){if(own_shown){++hides;own_shown=false;showing=false;return true;}return false;}
 void close(){hide();}
};
}
flight::V read_target(flight::V fallback,uint64_t* out){*out=revision;return fallback;}
RECT draw_overlay(HDC,RECT,uint32_t*,const ac8overlay::Observation&,const HudFrame&){++draws;draw_times.push_back(qpc);return {0,0,1,1};}
void log_line(const char*,...){}
LRESULT CALLBACK overlay_proc(HWND,UINT,WPARAM,LPARAM){return 0;}
HWND locate_game_window(){return game_window;}
template<class... T> BOOL yes(T...){return TRUE;}
template<class... T> ATOM register_class(T...){return 1;}
template<class... T> HWND create_window(T...){return reinterpret_cast<HWND>(4);}
template<class... T> HCURSOR cursor(T...){return reinterpret_cast<HCURSOR>(5);}
template<class... T> HANDLE create_event(T...){return reinterpret_cast<HANDLE>(11);}
template<class... T> HDC dc(T...){return reinterpret_cast<HDC>(6);}
template<class... T> HGDIOBJ select(T...){return reinterpret_cast<HGDIOBJ>(7);}
template<class... T> LONG_PTR style(T...){return 1;}
template<class... T> BOOL present(T...){return present_ok;}
template<class... T> BOOL place(T...){if(placement_ok)showing=true;return placement_ok;}
BOOL show(HWND,int command){if(command==SW_HIDE){++hides;showing=false;}return TRUE;}
template<class... T> BOOL window_visible(T...){return perf_enabled.load()&&showing;}
template<class... T> BOOL window_valid(T...){return TRUE;}
template<class... T> BOOL minimized(T...){return FALSE;}
HWND foreground(){return visible?game_window:nullptr;}
uint64_t tick(){return 1000+qpc/10000;}
BOOL frequency(LARGE_INTEGER* value){value->QuadPart=clock_ok?10000000:0;return clock_ok;}
BOOL counter(LARGE_INTEGER* value){value->QuadPart=qpc;return TRUE;}
BOOL fake_client(HWND,RECT* rect){*rect={0,0,5760,1080};return TRUE;}
BOOL fake_origin(HWND,POINT* point){*point={-1920,0};return TRUE;}
int fake_title(HWND,wchar_t* out,int){*out=0;return 0;}
HBITMAP dib(HDC,const BITMAPINFO* info,UINT,void** out,HANDLE,DWORD){
    backing.resize(size_t(info->bmiHeader.biWidth)*size_t(-info->bmiHeader.biHeight));
    *out=backing.data();return reinterpret_cast<HBITMAP>(8);
}
BOOL peek(MSG* message,HWND,UINT,UINT,UINT){
    if(message_pending){message_pending=false;message->message=WM_DISPLAYCHANGE;return TRUE;}return FALSE;
}
DWORD fake_error(){return 5;}
void advance(uint64_t delta){
    require(delta>0,"native wait makes positive temporal progress");++positive_waits;qpc+=delta;
    const auto current=qpc/285714;
    if(current!=frame_index){frame_index=current;hud_frame.publication=current+1;hud_frame.tick=tick();}
}
DWORD wait(DWORD count,const HANDLE* handles,DWORD timeout,DWORD,DWORD){
    ++iterations;
    if(iterations==100){message_pending=true;}
    if(hide_midway&&iterations==250){game_paused=true;}
    if(iterations>=limit)running=false;
    if(!wait_ok){++failed_waits;return WAIT_FAILED;}
    uint64_t delta=uint64_t(timeout)*10000;
    DWORD result=WAIT_TIMEOUT;
    if(input){delta=std::min<uint64_t>(delta,40000);++revision;result=WAIT_OBJECT_0;}
    for(DWORD i=0;i<count;++i)if(handles[i]==reinterpret_cast<HANDLE>(12)&&armed){
        const auto timer_delay=timer_deadline>qpc?timer_deadline-qpc:1;
        if(timer_delay<delta){delta=timer_delay;result=WAIT_OBJECT_0+i;}
    }
    require(timeout>0,"loop never uses zero polling timeout");
    advance(delta);return result;
}
void sleep(DWORD ms){require(ms>=1,"failed wait has bounded positive fallback");advance(uint64_t(ms)*10000);}
void reset(){
    qpc=0;revision=1;frame_index=0;iterations=draws=hides=arms=cancels=display_invalidations=period_poll=failed_waits=positive_waits=0;
    input=present_ok=placement_ok=timer_ok=clock_ok=visible=wait_ok=true;showing=armed=hide_midway=message_pending=false;
    running=true;hud_enabled=active=enabled=true;game_paused=gaze_active=perf_enabled=false;
    hud_frame={};draw_times.clear();rate=180;limit=500;
}
'''
aliases=dict(RegisterClassW='register_class',CreateWindowExW='create_window',LoadCursorW='cursor',CreateEventW='create_event',
             QueryPerformanceFrequency='frequency',QueryPerformanceCounter='counter',GetDC='dc',CreateCompatibleDC='dc',
             GetTickCount64='tick',IsWindow='window_valid',GetForegroundWindow='foreground',IsIconic='minimized',
             GetClientRect='fake_client',GetWindowTextW='fake_title',ClientToScreen='fake_origin',SetWindowLongPtrW='style',
             GdiFlush='yes',SelectObject='select',DeleteObject='yes',CreateDIBSection='dib',IsWindowVisible='window_visible',
             UpdateLayeredWindow='present',GetLastError='fake_error',SetWindowPos='place',ShowWindow='show',PeekMessageW='peek',
             TranslateMessage='yes',DispatchMessageW='yes',MsgWaitForMultipleObjectsEx='wait',Sleep='sleep',
             CloseHandle='yes',DeleteDC='yes',ReleaseDC='yes',DestroyWindow='yes',UnregisterClassW='yes')
prelude+='\n'.join(f'#define {native} {fake}' for native,fake in aliases.items())+'\n'
tests=r'''
int main(){
    for(const auto hz:{60u,75u,144u,165u,180u,240u}){
        reset();rate=hz;overlay_loop();
        require(draws>10,"continuous actual goal input remains responsive");
        const auto minimum=10000000/hz;
        for(size_t i=1;i<draw_times.size();++i)
            require(draw_times[i]-draw_times[i-1]>=minimum,"continuous input wakes cannot exceed covered refresh");
        require(display_invalidations==1,"production message pump invalidates rate after display change");
    }
    for(int failure=0;failure<2;++failure){
        reset();present_ok=failure!=0;placement_ok=failure==0;overlay_loop();
        require(draws<=qpc*rate/10000000+1,"failed upload/placement retry remains display-paced");
        for(size_t i=1;i<draw_times.size();++i)
            require(draw_times[i]-draw_times[i-1]>=10000000/rate,"failed submits never spin on zero timer");
    }
    reset();timer_ok=false;overlay_loop();
    require(draws>10&&arms>0,"failed timer uses timeout fallback while goal still updates");
    require(draws<=qpc*rate/10000000+1,"failed timer fallback remains paced");
    reset();clock_ok=false;present_ok=false;overlay_loop();
    require(arms==0,"unavailable QPC does not arm a zero-delay timer");
    require(qpc>=uint64_t(iterations)*10000,"unavailable scheduler cannot busy-spin failed submits");
    reset();input=false;limit=120;hud_frame.pawn=0;overlay_loop();
    require(draws==0,"idle blank state submits no glyph image");
    require(arms==0&&cancels>0,"clean idle does not schedule repeated uploads");
    reset();hide_midway=true;overlay_loop();
    require(hides==2&&!showing,"pause immediately hides both glyphs once and keeps them hidden");
    reset();visible=false;overlay_loop();
    require(draws==0&&arms==0,"unfocused overlay neither draws nor schedules high-rate timer");
    reset();wait_ok=false;limit=10;overlay_loop();
    require(failed_waits==limit&&positive_waits==limit,"failed native wait uses sleep fallback");
    std::printf("PASS: %u production overlay-loop lifecycle/cadence checks; no native window or game launched.\n",checks);
}
'''
cpp=B/'overlay_loop_integration_generated.cpp';cpp.write_text(prelude+loop+tests)
vcvars=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
def run(text,name):
    cpp.write_text(text)
    batch=B/'overlay_loop_integration_build.cmd'
    batch.write_text(f'@echo off\ncall "{vcvars}" >nul\nif errorlevel 1 exit /b 1\n'
                     f'cl /nologo /O2 /std:c++20 /EHsc /I..\\src {cpp.name} /Fe:{name}.exe /link user32.lib\n'
                     f'if errorlevel 1 exit /b 1\n{name}.exe\n')
    return subprocess.run(['cmd','/d','/c',str(batch)],cwd=B,capture_output=True,text=True,encoding='utf-8',errors='replace')
result=run(prelude+loop+tests,'overlay_loop_integration_test')
assert result.returncode==0,result.stdout+result.stderr
print(result.stdout.strip());(B/'overlay_loop_integration_test.txt').write_text(result.stdout)
# A reverted unconditional zero-delay timer must fail the unavailable-QPC case.
negative=loop.replace('schedule.active()&&timer.arm(remaining)','timer.arm(remaining)')
bad=run(prelude+negative+tests,'overlay_loop_integration_negative')
assert bad.returncode!=0 and 'unavailable QPC' in bad.stderr,bad.stdout+bad.stderr
cpp.write_text(prelude+loop+tests)
evidence=dict(passed=True,scope='Production extracted overlay loop with counted native boundaries; no game FPS claim.',
              production_loop_sha256=hashlib.sha256(production_loop.encode()).hexdigest(),
              runtime_source_sha256=hashlib.sha256((R/'src/mouse_aim.cpp').read_bytes()).hexdigest(),
              negative_control='Removing inactive-schedule timer guard fails unavailable-QPC regression.')
(T/'overlay_loop_integration_evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
