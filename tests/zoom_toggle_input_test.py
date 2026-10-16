"""Run actual shipped key polling/rebinding with controlled input and INI reads."""
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
runtime = here.parent / "runtime"
source = (runtime / "src/mouse_aim.cpp").read_text(encoding="utf-8")

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
#include <atomic>
#include <array>
#include <mutex>
#include <cwchar>
#include <cstdio>
#include <cstdlib>
#include "mod_keys.h"
#include "hud_render.h"
#include "aim_zoom.h"
#include "free_look.h"
flight::FreeLook free_look;flight::FreeLookManualControl free_look_manual;
void reset_look_mouse_input(){}
struct Features {bool mouse_flight=true;} pack_features;
std::atomic<bool> zoom_enabled{true},zoom_requested{false},zoom_binding_blocked{false},free_look_binding_blocked{false},manual_free_look{false};
std::atomic<int> free_look_binding{18},zoom_binding{2};
std::atomic<float> zoom_magnification{1};
std::atomic<bool> active{true},enabled{true},game_paused{false},gaze_active{false},hud_enabled{true},recenter_requested{false},reload_requested{false};
std::atomic<bool> native_landing_owned{false};
ac8keys::Bindings key_bindings;ac8keys::Edges key_edges;
bool key_bindings_initialized=false,free_look_key_blocked=false,free_look_key_pressed=false,focused=true;
std::array<bool,256> physical{};int configured_zoom=2;wchar_t config_path[1]{};
std::mutex hud_settings_mutex;ac8hud::Settings hud_settings;
short GetAsyncKeyState(int key){return physical[key]?short(0x8000):0;}
bool foreground_is_game(){return focused;}
void log_line(const char*,...){}
int GetPrivateProfileIntW(const wchar_t*,const wchar_t*,int fallback,const wchar_t*){return fallback;}
float section_number(const wchar_t* section,const wchar_t* key,float fallback){return !wcscmp(section,L"keys")&&!wcscmp(key,L"zoom")?float(configured_zoom):fallback;}
uint32_t hud_color(const wchar_t*,uint32_t fallback){return fallback;}
unsigned checks=0;
void require(bool ok,const char* text){++checks;if(!ok){std::fprintf(stderr,"FAIL: %s\n",text);std::exit(1);}}
'''
fixture = r'''
int main(){
    load_hud_keys();poll_mod_keys();physical[2]=true;poll_mod_keys();
    require(zoom_requested.load(),"first right-button click requests zoom");
    for(int i=0;i<100;++i)poll_mod_keys();
    require(zoom_requested.load(),"long held button cannot toggle repeatedly");
    physical[2]=false;poll_mod_keys();require(zoom_requested.load(),"release after first click keeps zoom active");
    ac8zoom::Transition blend;blend.step(zoom_requested.load(),.05f);const float first=blend.amount;
    physical[2]=true;poll_mod_keys();require(!zoom_requested.load(),"second press requests unzoom");
    const float second=blend.step(zoom_requested.load(),.001f);
    require(second<=first&&first-second<.001f,"second click begins continuous smooth return");
    physical[2]=false;poll_mod_keys();physical[2]=true;poll_mod_keys();
    require(zoom_requested.load(),"rapid third click requests zoom again");
    const float third=blend.step(zoom_requested.load(),.001f);
    require(third>=second&&third-second<.001f,"rapid reclick remains continuous");
    zoom_magnification.store(2);focused=false;poll_mod_keys();require(!zoom_requested.load()&&zoom_magnification.load()==1,"focus loss cancels toggle and optical input");
    focused=true;poll_mod_keys();require(!zoom_requested.load(),"held button on refocus cannot restore old toggle");
    physical[2]=false;poll_mod_keys();physical[2]=true;poll_mod_keys();require(zoom_requested.load(),"fresh focused click activates zoom");
    configured_zoom=int('Z');physical['Z']=true;load_hud_keys();
    require(!zoom_requested.load()&&zoom_binding.load()=='Z',"actual live keyboard rebind cancels old toggle");
    poll_mod_keys();require(!zoom_requested.load(),"held rebound key requires release");
    physical['Z']=false;poll_mod_keys();physical[2]=false;poll_mod_keys();physical[2]=true;poll_mod_keys();
    require(!zoom_requested.load(),"old mouse binding no longer toggles");
    physical['Z']=true;poll_mod_keys();require(zoom_requested.load(),"fresh remapped keyboard click toggles");
    physical['Z']=false;poll_mod_keys();require(zoom_requested.load(),"remapped key release preserves toggle");
    zoom_magnification.store(8);physical[18]=true;poll_mod_keys();
    require(zoom_requested.load()&&zoom_magnification.load()==8&&manual_free_look.load(),"ALT keeps clicked zoom and actual optical input while owning free look");
    physical['Z']=true;poll_mod_keys();require(!zoom_requested.load()&&manual_free_look.load(),"rebound keyboard zoom can toggle off while ALT stays held");
    physical['Z']=false;poll_mod_keys();physical['Z']=true;poll_mod_keys();require(zoom_requested.load(),"rebound keyboard zoom can toggle on while ALT stays held");
    physical['Z']=false;physical[18]=false;poll_mod_keys();require(zoom_requested.load()&&zoom_magnification.load()==8&&!manual_free_look.load(),"ALT release keeps clicked zoom and measured magnification");
    configured_zoom=2;physical[2]=false;load_hud_keys();poll_mod_keys();
    physical[18]=true;poll_mod_keys();physical[2]=true;poll_mod_keys();
    require(zoom_requested.load()&&manual_free_look.load(),"default RMB click activates zoom during held ALT");
    for(int i=0;i<50;++i)poll_mod_keys();require(zoom_requested.load(),"holding RMB with ALT cannot repeat toggle");
    physical[2]=false;poll_mod_keys();require(zoom_requested.load(),"RMB release during ALT keeps clicked zoom");
    physical[2]=true;poll_mod_keys();require(!zoom_requested.load()&&manual_free_look.load(),"default RMB second click turns zoom off during held ALT");
    physical[18]=false;poll_mod_keys();require(!zoom_requested.load(),"ALT release after RMB toggle-off cannot resurrect zoom");
    configured_zoom=int('Z');physical['Z']=false;load_hud_keys();poll_mod_keys();physical['Z']=true;poll_mod_keys();
    require(zoom_requested.load(),"fresh keyboard click still activates after default binding regression");
    zoom_enabled.store(false);poll_mod_keys();require(!zoom_requested.load(),"live disable cancels toggle");zoom_enabled.store(true);
    physical['Z']=false;poll_mod_keys();physical['Z']=true;poll_mod_keys();game_paused.store(true);poll_mod_keys();require(!zoom_requested.load(),"pause cancels toggle");game_paused.store(false);
    physical['Z']=false;poll_mod_keys();physical['Z']=true;poll_mod_keys();gaze_active.store(true);poll_mod_keys();require(!zoom_requested.load(),"native scene cancels toggle");gaze_active.store(false);
    physical['Z']=false;poll_mod_keys();physical['Z']=true;poll_mod_keys();active.store(false);poll_mod_keys();require(!zoom_requested.load(),"menu/inactive state cancels toggle");
    std::printf("PASS zoom toggle input: %u checks; actual production key poll and INI rebind; first-click/release persists, hold no repeat, second-click smooth out, rapid reclick continuity, keyboard remap, ALT keeps zoom and optical input, RMB/keyboard toggle during ALT, focus/disable/pause/scene/menu guards.\n",checks);
}
'''
build = here / "input_zoom_build"
build.mkdir(exist_ok=True)
(build / "zoom_toggle_input_test.cpp").write_text(prefix + function("key_states") + function("load_hud_keys") + function("poll_mod_keys") + fixture, encoding="utf-8")
vcvars = Path("C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat")
(build / "run_zoom_toggle.cmd").write_text(f'@echo off\ncall "{vcvars}" >nul\ncl /nologo /O2 /EHsc /std:c++20 /I"{runtime / "src"}" zoom_toggle_input_test.cpp /Fe:zoom_toggle_input_test.exe >zoom_toggle_build.log 2>&1\nif errorlevel 1 exit /b 1\nzoom_toggle_input_test.exe\n')
result = subprocess.run(["cmd", "/c", str(build / "run_zoom_toggle.cmd")], cwd=build, capture_output=True, text=True)
print(result.stdout, end="")
if result.returncode:
    print(result.stderr, end="")
    print((build / "zoom_toggle_build.log").read_text(encoding="utf-8", errors="replace"))
sys.exit(result.returncode)
