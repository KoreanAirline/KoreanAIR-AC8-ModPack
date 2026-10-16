"""Compile actual Alt pursuit, response, PSM and current-nose handoff gates.

Controlled keyboard/native-pose fixtures only. No game process or flight-quality
claim. Optional source argument supplies the published Alt-only negative control.
"""
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
runtime = here.parent / "runtime"
current_source = (runtime / "src/mouse_aim.cpp").read_text(encoding="utf-8")
source_path = Path(sys.argv[1]) if len(sys.argv)>1 else runtime / "src/mouse_aim.cpp"
source = source_path.read_text(encoding="utf-8")

def function(name, text=None):
    text = source if text is None else text
    start = text.index(name + "(")
    start = text.rfind("\n", 0, start) + 1
    end = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]

def block(text, marker):
    start=text.index(marker)
    end=text.index("{",start)+1
    depth=1
    while depth:
        depth+=(text[end]=="{")-(text[end]=="}")
        end+=1
    return text[start:end]

processor = function("process_input")
guidance_gate = next(line.strip() for line in processor.splitlines() if "const bool apply_guidance=" in line)
response_gate = next(line.strip() for line in function("commit_response_sync").splitlines() if "bool same=" in line)
psm_gate = next(line.strip() for line in function("block_automatic_psm").splitlines() if "if(!enabled.load()" in line)
assert processor.index("native_raw.begin(") < processor.index("const bool apply_guidance=")
assert "manual_free_look.store(looking);" in function("update_commands")
if "free_look_manual_control" in processor:
    assert function("update_commands").index("free_look.synchronize(free_look_manual);") < function("update_commands").index("const bool look_boundary=")
assert "manual_free_look.store(looking && free_look.manual)" not in source
# Old-source negative controls use their actual gates and the current latch
# fixture; Alt-only must fail before any new handoff block is required.
modern="free_look_manual_control" in processor
nose_handoff="if(live_pose_valid)align_free_look_target(input_basis);" if modern else ""
if modern:
    assert processor.index("free_look_manual_control();") < processor.index("input_target=read_target")
    assert processor.index("align_free_look_target(input_basis);") < processor.index("const bool apply_guidance=")
    assert "free_look_manual_control()" in guidance_gate+response_gate+psm_gate

prefix = r'''
#include <atomic>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include "free_look.h"
#include "native_raw_input.h"
#include "manual_rotation_input.h"
using namespace flight;
std::atomic<bool> manual_free_look{false},free_look_binding_blocked{false};
std::atomic<int> free_look_binding{18};
std::atomic<bool> enabled{true},active{true},game_paused{false},gaze_active{false},native_landing_owned{false};
std::atomic<uintptr_t> aircraft{100};
std::array<bool,256> physical{};
std::recursive_mutex pointing_mutex;
FreeLookManualControl free_look_manual;
std::atomic<long> mouse_dx{0},mouse_dy{0};
long look_mouse_dx=0,look_mouse_dy=0;
bool mouse_capture_look=false,mouse_flight_after_look=false;
V input_target{1,0,0};uint64_t input_target_revision=0;
std::atomic<float> target_pitch{0},target_yaw{0};
uint64_t publish_target(V aim){input_target=aim;return input_target_revision+1;}
struct Controller {unsigned resets=0;void reset(){++resets;}}live_guidance,native_rudder;
bool focused=true;
bool foreground_is_game(){return focused;}
short GetAsyncKeyState(int key) {return physical[key]?short(0x8000):0;}
unsigned checks=0;
void require(bool ok,const char* label) {++checks;if(!ok){std::fprintf(stderr,"FAIL: %s\n",label);std::exit(1);}}
'''
gates = r'''
bool pursue(bool user_enabled=true,bool override_input=true) {
    /* ACTUAL_PRODUCTION_GUIDANCE_GATE */
    return apply_guidance;
}
bool sync_allowed(uintptr_t pawn=100) {
    /* ACTUAL_PRODUCTION_RESPONSE_GATE */
    return same;
}
bool automatic_psm_provenance_allowed() {
    /* ACTUAL_PRODUCTION_PSM_GATE */
    return true;
}
bool native_frame(const Basis& input_basis,bool live_pose_valid=true,bool user_enabled=true,bool override_input=true) {
    free_look_manual_control();
    /* ACTUAL_PRODUCTION_NOSE_HANDOFF */
    /* ACTUAL_PRODUCTION_GUIDANCE_GATE */
    return apply_guidance;
}
'''.replace("/* ACTUAL_PRODUCTION_GUIDANCE_GATE */",guidance_gate).replace("/* ACTUAL_PRODUCTION_RESPONSE_GATE */",response_gate).replace("/* ACTUAL_PRODUCTION_PSM_GATE */",psm_gate).replace("/* ACTUAL_PRODUCTION_NOSE_HANDOFF */",nose_handoff)
fixture = r'''
int main() {
    const auto start=basis(0,0,0),plane=basis(25,65,80),moved=basis(-21,-70,-120);
    native_input::RawOwnership raw;
    for(int key:{18,164,165,int('F')}) {
        free_look_binding.store(key);manual_free_look.store(false);physical.fill(false);free_look_manual.reset();
        require(!free_look_suspends_guidance()&&pursue()&&sync_allowed()&&automatic_psm_provenance_allowed(),"ordinary input integrates");
        float axes[3]={.25f,-.4f,.5f};raw.reset();raw.mapping(100);raw.begin(100,axes);
        raw.wrote(100,0,.75f);axes[0]=.75f;raw.begin(100,axes);
        require(axes[0]==.25f,"retained automatic raw write restored before ALT gate");
        physical[key]=true;
        require(free_look_suspends_guidance(),"physical free-look owns mouse and camera before Lua poll without flight keys");
        require(pursue()&&sync_allowed()&&automatic_psm_provenance_allowed(),"physical ALT before Lua poll keeps last-goal RAW pursuit and coherent response commit");
        FreeLook look;V goal=start.f;
        look.step(true,goal,start,0,0,&plane,false);
        for(int frame=0;frame<100;++frame) {
            const V fixed=goal;look.step(true,goal,plane,9,-7,&plane,false);
            require(dot(goal,fixed)>.99999f&&pursue()&&sync_allowed()&&automatic_psm_provenance_allowed(),"Alt-only camera movement preserves goal and all ordinary automatic gates");
        }
        physical[key]=false;look.step(false,goal,start,500,500,&plane,false);
        require(!look.handed_off&&dot(goal,start.f)>.99999f&&native_frame(plane)&&dot(input_target,start.f)>.99999f,"Alt-only release retains previous world goal");
        for(int direction:{int('W'),int('S'),int('A'),int('D'),int('Q'),int('E')})for(bool already_held:{false,true}) {
            physical.fill(false);free_look_manual.reset();look.reset();goal=start.f;input_target=start.f;
            if(already_held)physical[direction]=true;
            physical[key]=true;
            if(!already_held) {
                require(pursue()&&sync_allowed()&&automatic_psm_provenance_allowed(),"Alt initially follows before explicit flight input");
                physical[direction]=true;
            }
            require(!pursue()&&!sync_allowed()&&!automatic_psm_provenance_allowed(),"each explicit flight key immediately stops pursuit response writes and automatic PSM provenance before Lua poll");
            require(!native_frame(plane)&&dot(input_target,plane.f)>.99999f,"manual native callback publishes current nose before any automatic input");
            look.step(true,goal,start,500,-500,&plane,free_look_manual.manual);
            require(look.manual&&dot(goal,plane.f)>.99999f&&dot(look.direction,start.f)>.99999f,"manual entry aligns circle with nose and discards camera boundary packet");
            const V camera_before=look.direction;
            physical[direction]=false;
            require(!pursue()&&!sync_allowed()&&!automatic_psm_provenance_allowed(),"flight key release never re-enables automation while Alt remains held");
            require(!native_frame(moved)&&dot(input_target,moved.f)>.99999f,"latched hold follows moving native aircraft nose after direction-key release");
            look.step(true,goal,start,20,-10,&moved,free_look_manual.manual);
            require(dot(goal,moved.f)>.99999f&&dot(camera_before,look.direction)<.99999f,"free camera keeps moving independently while circle stays at moving nose");
            // Run exact production keyboard filter: every claimed native axis
            // and all auxiliaries survive while unclaimed base mouse is removed.
            float manual_axes[6]={.25f,-.4f,.5f,.8f,.7f,.6f};
            const native_input::ManualRotation claimed{direction=='W'||direction=='S',direction=='Q'||direction=='E',direction=='A'||direction=='D'};
            claimed.retain_keyboard(manual_axes,true);
            require(manual_axes[0]==(claimed.pitch?.25f:0)&&manual_axes[1]==(claimed.yaw?-.4f:0)&&manual_axes[2]==(claimed.roll?.5f:0)&&manual_axes[3]==.8f&&manual_axes[4]==.7f&&manual_axes[5]==.6f,"manual takeover preserves exact claimed native flight and auxiliary values");
            physical[key]=false;
            require(!native_frame(plane,false)&&free_look_manual.pending_handoff,"release with invalid live pose defers automatic pursuit and retains handoff");
            require(!sync_allowed()&&!automatic_psm_provenance_allowed(),"deferred handoff cannot write response or claim automatic PSM provenance");
            require(native_frame(plane)&&dot(input_target,plane.f)>.99999f&&!free_look_manual.pending_handoff,"release publishes current live nose before resuming ordinary mouse pursuit");
            look.step(false,goal,start,500,-500,&plane,false);
            require(look.handed_off&&dot(goal,plane.f)>.99999f&&sync_allowed()&&automatic_psm_provenance_allowed(),"manual release cannot restore old goal or use boundary mouse deltas");
            look.step(true,goal,start,0,0,&plane,false);physical[key]=true;
            require(pursue()&&sync_allowed(),"next Alt-only hold starts without stale manual latch");
            physical[key]=false;look.reset();free_look_manual.reset();input_target=start.f;
        }
        physical[key]=true;physical['W']=true;free_look_binding_blocked=true;
        require(!free_look_binding_down()&&!free_look_manual_control()&&pursue(),"rebound/refocused held binding is blocked until released");
        free_look_binding_blocked=false;physical.fill(false);
    }
    // Native release/repress before a Lua camera update starts a new hold;
    // the prior FreeLook.manual must never resurrect nose-following.
    free_look_binding=18;physical.fill(false);free_look_manual.reset();
    physical[18]=true;physical['W']=true;require(!native_frame(plane),"rapid-hold fixture enters manual ownership");
    FreeLook rapid;V rapid_goal=plane.f;
    rapid.synchronize(free_look_manual);rapid.step(true,rapid_goal,start,0,0,&plane,free_look_manual.manual);
    require(rapid.manual&&rapid.held,"Lua observes the first manual hold");
    physical['W']=false;physical[18]=false;
    require(native_frame(moved)&&dot(input_target,moved.f)>.99999f,"native release hands off before next Lua update");
    physical[18]=true;
    require(native_frame(moved)&&!free_look_manual.manual,"native repress without flight key starts ordinary follow hold");
    const V new_world_goal=input_target;rapid_goal=new_world_goal;
    rapid.synchronize(free_look_manual);rapid.step(true,rapid_goal,start,500,-500,&plane,free_look_manual.manual);
    require(!rapid.manual&&dot(rapid_goal,new_world_goal)>.99999f&&dot(rapid.direction,start.f)>.99999f,"new physical hold clears stale local manual latch and discards its camera boundary deltas");
    rapid.step(true,rapid_goal,start,20,-10,&plane,free_look_manual.manual);
    require(dot(rapid_goal,new_world_goal)>.99999f&&pursue()&&sync_allowed(),"rapid new Alt-only hold preserves its world target while camera moves");
    physical.fill(false);free_look_manual.reset();
    for(unsigned lifecycle=0;lifecycle<6;++lifecycle) {
        physical.fill(false);physical[18]=true;physical['W']=true;
        require(free_look_manual_control(),"lifecycle fixture owns a manual Alt hold");
        if(lifecycle==0)enabled=false;if(lifecycle==1)active=false;if(lifecycle==2)game_paused=true;
        if(lifecycle==3)gaze_active=true;if(lifecycle==4)native_landing_owned=true;if(lifecycle==5)focused=false;
        require(!free_look_manual_control()&&!free_look_manual.held&&!free_look_manual.pending_handoff,"disable pawn pause gaze landing and focus reset stale manual latch");
        enabled=true;active=true;game_paused=false;gaze_active=false;native_landing_owned=false;focused=true;
        physical.fill(false);require(pursue(),"ordinary input resumes without stale manual ownership");
    }
    free_look_binding=0;physical.fill(true);free_look_manual.reset();
    require(!free_look_binding_down()&&!free_look_manual_control(),"unbound free-look stays off");physical.fill(false);
    require(!pursue(false)&&!pursue(true,false),"disabled or unmatched native input refuses automatic pursuit");
    enabled=false;require(!sync_allowed(),"disabled response commit refused");enabled=true;
    active=false;require(!sync_allowed(),"inactive response commit refused");active=true;
    game_paused=true;require(!sync_allowed(),"paused response commit refused");game_paused=false;
    gaze_active=true;require(!sync_allowed(),"cinematic gaze response commit refused");gaze_active=false;
    require(!sync_allowed(200),"foreign aircraft response commit refused");
    std::printf("PASS free-look input gate: %u checks; actual production RAW-pursuit response-commit PSM gates and live-nose handoff; Alt-only follows; six flight keys before/after Alt entry latch whole hold; key release keeps nose alignment; valid-pose release precedes ordinary pursuit; independent camera, native axes and lifecycle gates. No live flight claim.\n",checks);
}
'''
helper_source=source if modern else current_source
helpers=function("reset_look_mouse_input",current_source)+function("free_look_binding_down",helper_source)+function("observe_mouse_mode",current_source)+function("free_look_manual_control",helper_source)+function("free_look_suspends_guidance")+function("align_free_look_target",current_source)
build = here / "input_zoom_build"
build.mkdir(exist_ok=True)
(build / "input_free_look_gate_test.cpp").write_text(prefix+helpers+gates+fixture, encoding="utf-8")
vcvars = Path("C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat")
(build / "run_free_look.cmd").write_text(f'@echo off\ncall "{vcvars}" >nul\ncl /nologo /O2 /EHsc /std:c++20 /I"{runtime / "src"}" input_free_look_gate_test.cpp /Fe:input_free_look_gate_test.exe >input_free_look_build.log 2>&1\nif errorlevel 1 exit /b 1\ninput_free_look_gate_test.exe\n')
result = subprocess.run(["cmd", "/c", str(build / "run_free_look.cmd")], cwd=build, capture_output=True, text=True)
print(result.stdout, end="")
if result.returncode:
    print(result.stderr, end="")
    print((build / "input_free_look_build.log").read_text(encoding="utf-8", errors="replace"))
sys.exit(result.returncode)
