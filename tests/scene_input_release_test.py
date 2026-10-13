"""Exercise actual mouse capture and scene bridge before flight/free-look input.

Uses the shipped scene lease, FreeLook, and extracted production functions.
The game's raw-input API and Lua numeric transport are controlled fixtures.
"""
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
runtime = here.parent / "runtime"
source = (runtime / "src/mouse_aim.cpp").read_text(encoding="utf-8")
main = (runtime / "scripts/main.lua").read_text(encoding="utf-8")
headlook = (runtime / "scripts/headlook.lua").read_text(encoding="utf-8")
assert main.index("local headlooking=headlook.update()") < main.index("frame_native(address,")
assert "function M.release() native(0,0) end" in headlook
assert "if count~=1 then M.release();return false end" in headlook

def function(name):
    start = source.index(name + "(")
    start = source.rfind("\n", 0, start) + 1
    end = source.index("{", start) + 1
    depth = 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]

prefix = r'''
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <atomic>
#include <array>
#include <mutex>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "scene_mouse.h"
#include "free_look.h"
#include "geometric_guidance.h"
#include "aim_zoom.h"
struct Features {bool mouse_flight=true,diagnostics=false;} pack_features;
std::atomic<bool> running{true},enabled{true},active{true},game_paused{false},gaze_active{false};
std::atomic<long> mouse_dx{0},mouse_dy{0};ac8scene::Mouse scene_mouse;
struct Config {float look_sensitivity=.03f,sensitivity=.1f;} config;
std::atomic<bool> zoom_requested{false},manual_free_look{false},native_maneuver_active{false},recenter_requested{false},resume_center_requested{false};
std::atomic<float> zoom_magnification{1};
std::atomic<float> command_pitch{0},command_roll{0},command_yaw{0},pose_pitch{0},pose_yaw{0},pose_roll{0},camera_pitch{0},camera_yaw{0},camera_roll{0},target_pitch{0},target_yaw{0},look_pitch{0},look_yaw{0};
std::atomic<uint64_t> maneuver_pitch_motion{0};std::atomic<unsigned> keyboard_mask{0};
flight::FreeLook free_look;flight::GeometricGuidance guidance;
bool free_look_key_pressed=false;
float previous_pitch=0,previous_yaw=0,previous_roll=0,filtered_pitch_rate=0,filtered_yaw_rate=0,filtered_roll_rate=0;
unsigned long long previous_pose_tick=0,telemetry_tick=0;double previous_pose_seconds=0;
std::mutex target_vector_mutex;flight::V live_target{1,0,0};uint64_t live_target_revision=1;
bool focused=true,head_eligible=true;ULONGLONG clock_tick=100;
ULONGLONG fixture_clock(){return clock_tick;}
#define GetTickCount64 fixture_clock
double precise_seconds(){return double(clock_tick)/1000;}
SHORT fixture_keys(int){return 0;}
#define GetAsyncKeyState fixture_keys
bool foreground_is_game(){return focused;}bool on_bridge_thread(){return true;}
bool live_pointer_number(double n){return n>=65536&&n<1e12;}
void log_line(const char*,...){}
struct lua_State {double args[2]{};std::array<double,3> result{};unsigned count=0;};
struct LuaView {
    lua_State* state;
    explicit LuaView(lua_State* s):state(s){}
    void set_number(double n){state->result[state->count++]=n;}
};
bool read_numbers(LuaView& lua,double(&out)[2]) {memcpy(out,lua.state->args,sizeof(out));return true;}
namespace ac8headlook {
bool native_headlook_active(uintptr_t){return head_eligible;}
bool apply_native_headlook(uintptr_t,float,float){return true;}
}
UINT WINAPI raw_original(HRAWINPUT input,UINT command,LPVOID data,PUINT,UINT){if(command!=RID_INPUT)return UINT(-1);memcpy(data,input,sizeof(RAWINPUT));return sizeof(RAWINPUT);}
using GetRawInputDataFn=UINT(WINAPI*)(HRAWINPUT,UINT,LPVOID,PUINT,UINT);
GetRawInputDataFn original_get_raw_input_data=raw_original;
unsigned checks=0;
void require(bool ok,const char* message){++checks;if(!ok){std::fprintf(stderr,"FAIL: %s\n",message);std::exit(1);}}
'''
fixture = r'''
lua_State scene(uintptr_t owner=0,bool paused=false){lua_State state;state.args[0]=double(owner);state.args[1]=paused?1:0;require(ac8_mouseaim_scenelook(&state)==3,"actual scene numeric bridge accepted");return state;}
void capture(long x,long y){RAWINPUT packet{},out{};packet.header.dwType=RIM_TYPEMOUSE;packet.data.mouse.lLastX=x;packet.data.mouse.lLastY=y;UINT bytes=sizeof(out);require(capture_get_raw_input_data(reinterpret_cast<HRAWINPUT>(&packet),RID_INPUT,&out,&bytes,sizeof(RAWINPUTHEADER))==sizeof(out),"actual raw capture preserves native packet result");}
int main(){
    using namespace flight;const auto view=basis(0,0,0);
    auto goal=[] {return basis(target_pitch.load(),target_yaw.load(),0).f;};
    auto camera=[] {return basis(look_pitch.load(),look_yaw.load(),0).f;};
    for(int frame=0;frame<40;++frame){
        clock_tick+=16;capture(7,-3);scene();
        require(mouse_dx.load()==7&&mouse_dy.load()==-3,"idle headlook release preserves captured flight deltas");
        const auto prior=goal();update_commands();
        require(dot(goal(),prior)<.99999f&&dot(live_target,goal())>.99999f,"actual update_commands advances and publishes ordinary aim after idle scene release");
    }
    const auto flight_goal=goal();free_look_key_pressed=true;capture(30,-20);scene();update_commands();
    require(free_look.held&&manual_free_look.load()&&dot(camera(),view.f)>.99999f&&dot(goal(),flight_goal)>.99999f,"actual ALT update discards exactly its boundary deltas");
    const auto initial_camera=camera();
    for(int frame=0;frame<40;++frame){clock_tick+=16;capture(9,-4);scene();update_commands();}
    require(dot(camera(),initial_camera)<.99f&&dot(goal(),flight_goal)>.99999f,"actual ALT update advances camera while preserving flight goal");
    capture(50,20);scene(0x10000);require(mouse_dx.load()==0&&mouse_dy.load()==0,"real scene entry discards flight boundary once");
    capture(10,-20);const auto moved=scene(0x10000);
    require(std::abs(moved.result[0]-.3)<1e-6&&std::abs(moved.result[1]-.6)<1e-6,"actual scene receives separate mouse deltas");
    mouse_dx.store(8);mouse_dy.store(6);scene(0x10000);
    require(mouse_dx.load()==8&&mouse_dy.load()==6,"unchanged live scene binding is idempotent");
    scene(0x10000,true);require(mouse_dx.load()==0&&mouse_dy.load()==0,"scene pause transition discards once");
    mouse_dx.store(8);scene(0x10000,true);require(mouse_dx.load()==8,"repeated paused scene binding does not discard again");
    scene(0x10000,false);require(mouse_dx.load()==0,"scene unpause boundary discards once");
    clock_tick+=251;capture(8,-5);require(mouse_dx.load()==8,"expired scene routes fresh delta back to flight");
    scene(0x10000);require(mouse_dx.load()==0&&mouse_dy.load()==0,"stale scene reactivation discards boundary once");
    mouse_dx.store(9);scene();require(mouse_dx.load()==0,"actual scene exit discards boundary once");
    free_look.reset();free_look_key_pressed=false;target_pitch.store(0);target_yaw.store(0);
    for(int frame=0;frame<40;++frame){clock_tick+=16;capture(7,-3);scene();require(mouse_dx.load()==7&&mouse_dy.load()==-3,"fresh flight deltas survive repeated idle release after real scene exit");update_commands();}
    require(dot(goal(),view.f)<.9f,"actual ordinary aim resumes after scene exit and repeated idle releases");
    for(float ratio:{1.f,2.f,8.f})for(float amount:{0.f,.25f,.5f,1.f})for(bool vertical:{false,true}) {
        free_look.reset();free_look_key_pressed=false;target_pitch.store(0);target_yaw.store(0);
        camera_pitch.store(0);camera_yaw.store(0);camera_roll.store(0);
        const float baseline_fov=100,rendered_fov=ac8zoom::lens(baseline_fov,std::pow(ratio,amount));
        zoom_magnification.store(ac8zoom::magnification(baseline_fov,rendered_fov));
        clock_tick+=16;capture(vertical?0:10,vertical?10:0);scene();update_commands();
        const float world_angle=vertical?std::abs(pitch(goal())):std::abs(yaw(goal()));
        const float original_pixels=960*std::tan(10*config.sensitivity*rad)/std::tan(baseline_fov*.5f*rad);
        const float zoom_pixels=960*std::tan(world_angle*rad)/std::tan(rendered_fov*.5f*rad);
        require(std::abs(original_pixels-zoom_pixels)<.001f,"actual update_commands retains original x/y pixel response at each current optical transition");
    }
    for(float ratio:{1.f,2.f,8.f})for(float amount:{0.f,.25f,.5f,1.f})for(bool vertical:{false,true}) {
        free_look.reset();free_look_key_pressed=true;target_pitch.store(17);target_yaw.store(30);
        camera_pitch.store(0);camera_yaw.store(0);camera_roll.store(0);zoom_requested.store(true);
        const auto held_goal=goal();const float rendered_fov=ac8zoom::lens(100,std::pow(ratio,amount));
        zoom_magnification.store(ac8zoom::magnification(100,rendered_fov));
        capture(100,-100);update_commands();
        require(dot(camera(),view.f)>.999999f&&dot(goal(),held_goal)>.999999f,"zoomed ALT entry discards boundary packet without moving aim");
        clock_tick+=16;capture(vertical?0:10,vertical?10:0);update_commands();
        const float world_angle=vertical?std::abs(pitch(camera())):std::abs(yaw(camera()));
        const float ordinary_pixels=960*std::tan(10*config.look_sensitivity*rad)/std::tan(50*rad);
        const float zoom_pixels=960*std::tan(world_angle*rad)/std::tan(rendered_fov*.5f*rad);
        require(std::abs(ordinary_pixels-zoom_pixels)<.001f,"actual ALT uses configured look sensitivity with matching current-lens pixel response");
        require(dot(goal(),held_goal)>.999999f&&zoom_requested.load(),"zoomed ALT movement leaves clicked zoom and flight goal intact");
        free_look_key_pressed=false;clock_tick+=16;capture(100,-100);update_commands();
        require(dot(goal(),held_goal)>.999999f&&zoom_requested.load()&&!manual_free_look.load(),"ALT release discards boundary packet and retains zoom/flight goal");
        clock_tick+=16;capture(10,0);update_commands();
        require(dot(goal(),held_goal)<.999999f&&zoom_requested.load(),"ordinary aim movement resumes after ALT while zoom remains requested");
    }
    std::printf("PASS scene input release pipeline: %u checks; actual raw capture/scene bridge/update_commands/FreeLook; 40 ordinary, 40 ALT and 40 post-scene frames; real entry/pause/stale/reactivation/exit boundaries discard once; flight and ALT current-lens mouse displacement at 1x/2x/8x; ALT enter/move/release preserves clicked zoom and flight goal; main.lua idle headlook release precedes flight frame.\n",checks);
}
'''
build = here / "input_zoom_build"
build.mkdir(exist_ok=True)
(build / "scene_input_release_test.cpp").write_text(prefix + function("publish_target") + function("capture_get_raw_input_data") + function("ac8_mouseaim_scenelook") + function("update_commands") + fixture, encoding="utf-8")
vcvars = Path("C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat")
(build / "run_scene_input_release.cmd").write_text(f'@echo off\ncall "{vcvars}" >nul\ncl /nologo /O2 /EHsc /std:c++20 /I"{runtime / "src"}" scene_input_release_test.cpp /Fe:scene_input_release_test.exe >scene_input_release_build.log 2>&1\nif errorlevel 1 exit /b 1\nscene_input_release_test.exe\n')
result = subprocess.run(["cmd", "/c", str(build / "run_scene_input_release.cmd")], cwd=build, capture_output=True, text=True)
print(result.stdout, end="")
if result.returncode:
    print(result.stderr, end="")
    print((build / "scene_input_release_build.log").read_text(encoding="utf-8", errors="replace"))
sys.exit(result.returncode)
