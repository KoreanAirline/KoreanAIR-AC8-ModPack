"""Actual runtime sampler/Control -> unmodified pinned native PSM admission.

Synthetic memory and settings only; no game process, model/flag edits or live
flight claim. The EXE admission executes without replacing any native helper.
"""
from pathlib import Path
import ctypes
import hashlib
import subprocess
import sys

from native_player_maneuver_test import Executable, NativeFixture, DRIFT, SETTINGS, PINNED_RANGES

here = Path(__file__).resolve().parent
runtime = here.parent / "runtime"
source = (runtime / "src/mouse_aim.cpp").read_text(encoding="utf-8")
start = source.index("player_maneuver::Snapshot sample_player_maneuver(")
end = source.index("{", start) + 1
depth = 1
while depth:
    depth += (source[end] == "{") - (source[end] == "}")
    end += 1
sampler = source[start:end]
start = source.index("for(int i=0;i<3;++i) {", source.index("const bool held_axis[]={held_pitch,held_yaw,held_roll};"))
end = source.index("{", start) + 1
depth = 1
while depth:
    depth += (source[end] == "{") - (source[end] == "}")
    end += 1
selector = source[start:end]
sync_line = next(line.strip() for line in source.splitlines() if "commit_response_sync(pawn,context,trace);" in line)
assert "!player_maneuver_control.neutral_edge" in sync_line
assert "const bool automatic_tracking=apply_guidance&&!native_ownership&&!player_maneuver_control.neutral_edge;" in source
prefix = r'''
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <array>
#include <cstring>
#include "native_player_maneuver.h"
#include "native_raw_input.h"
#include "native_actuator.h"
#include "native_maneuver_guard.h"
native_input::RawOwnership native_raw;
bool player_maneuver_code_verified=true;
player_maneuver::Control control;
auto& player_maneuver_control=control;
native_maneuver::Guard maneuver_guard;
struct Trace {double before[3]{};float raw_sent[3]{},predicted[3]{};unsigned mode=1u<<17;};
'''
fixture = r'''
extern "C" __declspec(dllexport) void reset_control(){control.reset();native_raw.reset();}
extern "C" __declspec(dllexport) unsigned packet(float pitch,float previous,int mode,int capability,
    float speed,float maximum,float minimum,float grace,unsigned flags,int keyboard,unsigned long long mapping,float native_yaw,float native_roll,float* sent){
    std::array<unsigned char,0x2600> pawn_storage{};std::array<unsigned char,0x500> settings{};
    const auto pawn=reinterpret_cast<uintptr_t>(pawn_storage.data());
    auto* dynamics=pawn_storage.data()+0x2300;dynamics[0x8d]=static_cast<unsigned char>(mode);
    memcpy(dynamics+0xa8,&previous,4);memcpy(dynamics+0x18,&speed,4);memcpy(pawn_storage.data()+0x1178,&grace,4);
    settings[0x3cc]=static_cast<unsigned char>(capability);memcpy(settings.data()+0x3d0,&maximum,4);memcpy(settings.data()+0x384,&minimum,4);
    float axes[6]={pitch,native_yaw,native_roll,1,1,1};native_raw.mappings=mapping;
    const auto sample=sample_player_maneuver(pawn,axes,settings.data(),flags);
    control.observe(sample,0,1,keyboard!=0);
    const bool apply_guidance=true,native_ownership=control.owns_rotation(),valid=true;
    const bool held_axis[]={keyboard!=0||axes[0]!=0,axes[1]!=0,axes[2]!=0};
    const float requested[]={1,-1,1};Trace trace;
    native_input::Params params{.016f,0,10,10,10,10,10,10};
    /* ACTUAL_PRODUCTION_SELECTOR */
    unsigned sync_commits=0;unsigned char* context=nullptr;
    auto commit_response_sync=[&](uintptr_t,unsigned char*,Trace&){++sync_commits;};
    /* ACTUAL_PRODUCTION_SYNC_GATE */
    memcpy(sent,axes,sizeof(axes));
    return (sample.prepare_edge_allowed?1u:0u)|(control.neutral_edge?2u:0u)|(control.active?4u:0u)|(sync_commits?8u:0u);
}
'''
fixture = fixture.replace("/* ACTUAL_PRODUCTION_SELECTOR */", selector).replace("/* ACTUAL_PRODUCTION_SYNC_GATE */", sync_line)
build = here / "input_zoom_build"
build.mkdir(exist_ok=True)
(build / "native_psm_pipeline.cpp").write_text(prefix + sampler + fixture, encoding="utf-8")
vcvars = Path("C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat")
(build / "run_psm_pipeline.cmd").write_text(f'@echo off\ncall "{vcvars}" >nul\ncl /nologo /O2 /EHsc /std:c++20 /LD /I"{runtime / "src"}" native_psm_pipeline.cpp /Fe:native_psm_pipeline.dll >native_psm_pipeline_build.log 2>&1\n')
compiled = subprocess.run(["cmd", "/c", str(build / "run_psm_pipeline.cmd")], cwd=build, capture_output=True, text=True)
if compiled.returncode:
    print((build / "native_psm_pipeline_build.log").read_text(encoding="utf-8", errors="replace"))
    sys.exit(compiled.returncode)
dll = ctypes.CDLL(str(build / "native_psm_pipeline.dll"))
dll.packet.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_int, ctypes.c_int,
                      ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                      ctypes.c_uint, ctypes.c_int, ctypes.c_ulonglong, ctypes.c_float, ctypes.c_float, ctypes.POINTER(ctypes.c_float)]
dll.packet.restype = ctypes.c_uint
checks = 0

def require(ok, label):
    global checks
    checks += 1
    assert ok, label

def packet(pitch, previous, *, mode=0, capability=1, speed=100, maximum=200,
           minimum=0, grace=.4, flags=0, keyboard=True, mapping=2,yaw=.3125,roll=-.4375,full=False):
    sent = (ctypes.c_float * 6)()
    state = dll.packet(pitch, previous, mode, capability, speed, maximum, minimum,
                       grace, flags, keyboard, mapping, yaw, roll, sent)
    require(list(sent)[3:] == [1,1,1], "throttle/brake/highG retained exactly")
    if state&6 or (yaw!=0 and roll!=0):require(list(sent)[1:3] == [yaw,roll], "actual native yaw/roll retained on preparation/native ownership")
    return (state,float(sent[0]),list(sent)) if full else (state,float(sent[0]))

executable = Executable(Path("E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe"))
try:
    for _, first, last, expected in PINNED_RANGES:
        require(hashlib.sha256(executable.read(first,last-first)).hexdigest() == expected, "pinned native instruction fingerprint")
    for capability, flags, grace in [(1,0,.4),(2,0,.4),(1,1<<8,0),(2,1<<8,0)]:
        dll.reset_control()
        packet(.1,1,capability=capability,flags=flags,grace=grace,keyboard=False,mapping=1)
        state, sent = packet(1,1,capability=capability,flags=flags,grace=grace)
        require(state&3 == 3 and not state&12 and sent == 0, "new S after positive mouse repairs eligible history without claiming mode2 or response sync")
        native = NativeFixture(executable,previous_pitch=1,pitch=sent,capability=capability,
                               flags=flags,native_button=grace>0,high_g=1,yaw=.3125,roll=-.4375)
        require(native.admission()==0 and native.read_float(DRIFT+0x38)==0, "unmodified native admission consumes neutral and stores zero history")
        state, sent = packet(1,native.read_float(DRIFT+0x38),capability=capability,flags=flags,grace=grace,mapping=3)
        require(not state&2 and sent==1, "continuing physical hold returns actual positive pitch after neutral")
        native.input(sent,high_g=1,yaw=.3125,roll=-.4375)
        require(native.admission()==2 and native.phase==1, "actual native Cobra/Kulbit admission succeeds on held physical pull")
        state, sent = packet(1,1,mode=2,capability=capability,flags=flags,grace=grace,mapping=4)
        require(state&4 and not state&2 and sent==1, "genuine observed mode2 retains exact physical pull")
    for kind in ["down", "speed", "grace", "capability", "generic-speed", "excluded-flags"]:
        params = dict(capability=1,speed=100,maximum=200,minimum=0,grace=.4,flags=0)
        if kind=="speed": params["speed"]=201
        if kind=="grace": params["grace"]=0
        if kind=="capability": params["capability"]=0
        if kind=="generic-speed": params.update(flags=1<<5,minimum=150)
        if kind=="excluded-flags": params["flags"]=1<<18
        dll.reset_control();packet(.1,1,keyboard=False,mapping=1,**params)
        physical = -1 if kind=="down" else 1
        state,sent=packet(physical,1,**params)
        require(not state&6 and sent==physical, kind+": no synthetic neutral/mode ownership; physical input retained")
        native=NativeFixture(executable,previous_pitch=1,pitch=sent,capability=params["capability"],
                             speed=params["speed"],flags=params["flags"],native_button=params["grace"]>0,high_g=1)
        native.float(SETTINGS+0x384,params["minimum"])
        require(native.admission()!=2,kind+": actual native gate remains authoritative")
    # Reproduce native generic-mode admission during the old preparation packet.
    raced=NativeFixture(executable,previous_pitch=1,pitch=0,high_g=1,roll=1)
    raced.float(SETTINGS+0x380,.4);raced.float(DRIFT+8,.4)
    require(raced.admission()==1,"automatic roll on neutral preparation wrongly admits actual generic highG mode1")
    raced.input(1,high_g=1,roll=1);require(raced.admission()==1,"generic mode1 prevents next actual PSM admission")
    for capability in [1,2]:
        dll.reset_control();packet(.1,1,keyboard=False,mapping=1,yaw=0,roll=0)
        state,sent,axes=packet(1,1,capability=capability,yaw=0,roll=0,full=True)
        require(state&3==3 and not state&12 and axes[:3]==[0,0,0],"actual production selector suppresses automatic yaw/roll and sync only on preparation callback")
        native=NativeFixture(executable,previous_pitch=1,pitch=sent,capability=capability,high_g=1,roll=axes[2])
        native.float(SETTINGS+0x380,.4);native.float(DRIFT+8,.4)
        require(native.admission()==0 and native.read_float(DRIFT+0x38)==0,"exact native yaw/roll avoids generic highG race while native stores zero")
        state,sent,axes=packet(1,0,capability=capability,mapping=3,yaw=0,roll=0,full=True)
        require(not state&6 and axes[1]!=0 and axes[2]!=0,"automatic outputs resume after single preparation callback")
        native.input(sent,high_g=1,yaw=axes[1],roll=axes[2]);require(native.admission()==2,"held physical S admits actual Cobra/Kulbit after coherent native preparation")
    print(f"PASS native PSM input pipeline: {checks} checks; actual runtime sampler/Control/process selector/sync gate and unmodified native admission; positive mouse -> new S -> neutral once -> held mode2; generic-highG roll race prevented; Cobra/Kulbit/flag8; W/down and ineligible gates retain physical axes/auxiliary flags. Synthetic memory only, no live-flight claim.")
finally:
    executable.close()
