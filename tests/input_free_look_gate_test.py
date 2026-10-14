"""Run shipped free-look ownership and flight-pursuit gates with controlled keys.

The extracted function is production code. No game is launched or modified.
Camera/mouse ownership must be independent of retained-goal RAW pursuit and
response-state writes. Optional source argument provides the old-build negative
control. No game flight or target-convergence claim.
"""
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
runtime = here.parent / "runtime"
source_path = Path(sys.argv[1]) if len(sys.argv)>1 else runtime / "src/mouse_aim.cpp"
source = source_path.read_text(encoding="utf-8")

def function(name):
    start = source.index(name + "(")
    start = source.rfind("\n", 0, start) + 1
    end = source.index("{", start) + 1
    depth = 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]

processor = function("process_input")
guidance_gate = next(line.strip() for line in processor.splitlines() if "const bool apply_guidance=" in line)
response_gate = next(line.strip() for line in function("commit_response_sync").splitlines() if "bool same=" in line)
assert processor.index("native_raw.begin(") < processor.index("const bool apply_guidance=")
assert "manual_free_look.store(looking);" in function("update_commands")
assert "manual_free_look.store(looking && free_look.manual)" not in source

prefix = r'''
#include <atomic>
#include <array>
#include <cstdio>
#include <cstdlib>
#include "free_look.h"
#include "native_raw_input.h"
std::atomic<bool> manual_free_look{false},free_look_binding_blocked{false};
std::atomic<int> free_look_binding{18};
std::atomic<bool> enabled{true},active{true},game_paused{false},gaze_active{false};
std::atomic<uintptr_t> aircraft{100};
std::array<bool,256> physical{};
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
'''.replace("/* ACTUAL_PRODUCTION_GUIDANCE_GATE */",guidance_gate).replace("/* ACTUAL_PRODUCTION_RESPONSE_GATE */",response_gate)
fixture = r'''
int main() {
    using namespace flight;
    const auto start=basis(0,0,0),plane=basis(25,65,80);
    FreeLook look;V goal=start.f;
    native_input::RawOwnership raw;
    for(int key:{18,164,165,int('F')}) {
        free_look_binding.store(key);manual_free_look.store(false);physical.fill(false);
        require(!free_look_suspends_guidance()&&pursue()&&sync_allowed(),"ordinary input integrates");
        float axes[3]={.25f,-.4f,.5f};raw.reset();raw.mapping(100);raw.begin(100,axes);
        // A retained mod axis must be removed before entering native ownership.
        raw.wrote(100,0,.75f);axes[0]=.75f;raw.begin(100,axes);
        require(axes[0]==.25f,"retained automatic raw write restored before ALT gate");
        physical[key]=true;
        require(free_look_suspends_guidance(),"physical free-look owns mouse and camera before Lua poll without flight keys");
        require(pursue()&&sync_allowed(),"physical ALT before Lua poll keeps last-goal RAW pursuit and coherent response commit");
        require(axes[0]==.25f&&axes[1]==-.4f&&axes[2]==.5f,"actual native axes survive held ALT");
        look.reset();goal=start.f;look.step(true,goal,start,0,0,&plane,false);
        require(look.held&&!look.manual&&dot(goal,start.f)>.99999f,"ALT alone retains mouse world goal without keyboard flag");
        for(int frame=0;frame<100;++frame) {
            const V fixed=goal;look.step(true,goal,plane,9,-7,&plane,false);
            require(dot(goal,fixed)>.99999f&&pursue()&&sync_allowed(),"free-look camera movement keeps same last world goal and automatic tracking throughout hold");
        }
        look.step(false,goal,start,500,500,&plane,false);physical[key]=false;
        require(!free_look_suspends_guidance()&&!look.handed_off&&dot(goal,start.f)>.99999f,"ALT-only release preserves world target and resumes");
        physical[key]=true;look.step(true,goal,start,0,0,&plane,false);look.step(true,goal,start,20,10,&plane,true);
        manual_free_look.store(true);physical[key]=false;
        require(free_look_suspends_guidance()&&pursue()&&sync_allowed(),"latched camera hold before Lua release does not stop retained-goal tracking");
        look.step(false,goal,start,500,-500,&plane,false);manual_free_look.store(false);
        require(look.handed_off&&dot(goal,plane.f)>.99999f&&!free_look_suspends_guidance(),"manual keyboard nose handoff resumes after release");
        physical[key]=true;free_look_binding_blocked.store(true);
        require(!free_look_suspends_guidance(),"held key at reload/refocus waits for release");
        free_look_binding_blocked.store(false);
    }
    free_look_binding.store(0);physical.fill(true);
    require(!free_look_suspends_guidance(),"unbound free-look gate stays off");
    require(!pursue(false)&&!pursue(true,false),"disabled or unmatched native input refuses automatic pursuit");
    enabled=false;require(!sync_allowed(),"disabled response commit refused");enabled=true;
    active=false;require(!sync_allowed(),"inactive response commit refused");active=true;
    game_paused=true;require(!sync_allowed(),"paused response commit refused");game_paused=false;
    gaze_active=true;require(!sync_allowed(),"cinematic gaze response commit refused");gaze_active=false;
    require(!sync_allowed(200),"foreign aircraft response commit refused");
    std::printf("PASS free-look input gate: %u checks; actual production mouse/camera ownership, RAW-pursuit and response-commit gates; physical ALT-before-Lua; 400 held camera movements preserve last world goal; manual nose handoff; rebind/refocus blocked hold; disabled/inactive/pause/gaze/foreign input safeguards. No live flight claim.\n",checks);
}
'''
build = here / "input_zoom_build"
build.mkdir(exist_ok=True)
(build / "input_free_look_gate_test.cpp").write_text(prefix + function("free_look_suspends_guidance") + gates + fixture, encoding="utf-8")
vcvars = Path("C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat")
(build / "run_free_look.cmd").write_text(f'@echo off\ncall "{vcvars}" >nul\ncl /nologo /O2 /EHsc /std:c++20 /I"{runtime / "src"}" input_free_look_gate_test.cpp /Fe:input_free_look_gate_test.exe >input_free_look_build.log 2>&1\nif errorlevel 1 exit /b 1\ninput_free_look_gate_test.exe\n')
result = subprocess.run(["cmd", "/c", str(build / "run_free_look.cmd")], cwd=build, capture_output=True, text=True)
print(result.stdout, end="")
if result.returncode:
    print(result.stderr, end="")
    print((build / "input_free_look_build.log").read_text(encoding="utf-8", errors="replace"))
sys.exit(result.returncode)
