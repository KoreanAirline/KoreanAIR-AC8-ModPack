"""Actual runtime sampler/Control -> unmodified pinned native PSM admission.

Synthetic memory and settings only; no game process, model/flag edits or live
flight claim. The EXE admission executes without replacing any native helper.
"""
from pathlib import Path
import ctypes
import hashlib
import json
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
start = source.index("native_maneuver::Snapshot sample_native_maneuver(")
end = source.index("{", start) + 1
depth = 1
while depth:
    depth += (source[end] == "{") - (source[end] == "}")
    end += 1
native_sampler = source[start:end]
start = source.index("for(int i=0;i<3;++i)trace.raw_before[i]=axes[i];")
end = source.index("const auto* settings=", start)
ownership = source[start:end]
assert source.index("manual_rotation.retain_keyboard(axes,user_enabled);") < source.index("player_maneuver_sample=sample_player_maneuver(pawn,axes,settings,flags);")
start = source.index("for(int i=0;i<3;++i) {", source.index("const bool held_axis[]={held_pitch,held_yaw,held_roll};"))
end = source.index("{", start) + 1
depth = 1
while depth:
    depth += (source[end] == "{") - (source[end] == "}")
    end += 1
selector = source[start:end]
guidance_gate = next(line.strip() for line in source.splitlines() if "const bool apply_guidance=" in line)
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
#include "manual_rotation_input.h"
native_input::RawOwnership native_raw;
bool free_look_manual_control(){return false;}
bool player_maneuver_code_verified=true;
bool maneuver_code_verified=true;
player_maneuver::Control control;
auto& player_maneuver_control=control;
native_maneuver::Guard maneuver_guard;
struct Trace {double before[3]{};float raw_before[3]{},raw_sent[3]{},predicted[3]{};unsigned mode=1u<<17;};
'''
fixture = r'''
extern "C" __declspec(dllexport) void reset_control(){control.reset();maneuver_guard.reset();native_raw.reset();}
extern "C" __declspec(dllexport) unsigned packet(float pitch,float previous,int mode,int capability,
    float speed,float maximum,float minimum,float grace,unsigned flags,int keyboard,unsigned long long mapping,float native_yaw,float native_roll,float* sent){
    std::array<unsigned char,0x2600> pawn_storage{};std::array<unsigned char,0x500> settings{};
    const auto pawn=reinterpret_cast<uintptr_t>(pawn_storage.data());
    auto* dynamics=pawn_storage.data()+0x2300;dynamics[0x8d]=static_cast<unsigned char>(mode);
    memcpy(dynamics+0xa8,&previous,4);memcpy(dynamics+0x18,&speed,4);memcpy(pawn_storage.data()+0x1178,&grace,4);
    settings[0x3cc]=static_cast<unsigned char>(capability);memcpy(settings.data()+0x3d0,&maximum,4);memcpy(settings.data()+0x384,&minimum,4);
    float axes[6]={pitch,native_yaw,native_roll,1,1,1};native_raw.mappings=mapping;
    const bool keyboard_pitch=(keyboard&1)!=0,keyboard_yaw=(keyboard&4)!=0,keyboard_roll=(keyboard&2)!=0,user_enabled=true;
    Trace trace;
    /* ACTUAL_PRODUCTION_OWNERSHIP */
    const auto sample=sample_player_maneuver(pawn,axes,settings.data(),flags);
    control.observe(sample,0,1,keyboard_pitch);
    const bool apply_guidance=true,native_ownership=control.owns_rotation(),valid=true;
    const bool held_axis[]={held_pitch,held_yaw,held_roll};
    const float requested[]={1,-1,1};
    native_input::Params params{.016f,0,10,10,10,10,10,10};
    /* ACTUAL_PRODUCTION_SELECTOR */
    unsigned sync_commits=0;unsigned char* context=nullptr;
    auto commit_response_sync=[&](uintptr_t,unsigned char*,Trace&){++sync_commits;};
    /* ACTUAL_PRODUCTION_SYNC_GATE */
    memcpy(sent,axes,sizeof(axes));
    return (sample.prepare_edge_allowed?1u:0u)|(control.neutral_edge?2u:0u)|(control.active?4u:0u)|(sync_commits?8u:0u);
}
// Ordinary/Alt/F8 path executes the identical ownership and writeback blocks.
extern "C" __declspec(dllexport) void rotation_packet(float* axes,const double* before,const float* requested,
    int keyboard,int enabled,int looking,int fresh_mapping,float dt,float modifier,float* predicted){
    control.reset();maneuver_guard.reset();
    const auto pawn=reinterpret_cast<uintptr_t>(axes)-0x2268;
    if(fresh_mapping)native_raw.mapping(pawn+0x2268);
    native_raw.begin(pawn+0x2268,axes);
    const bool keyboard_pitch=(keyboard&1)!=0,keyboard_yaw=(keyboard&4)!=0,keyboard_roll=(keyboard&2)!=0,user_enabled=enabled!=0;
    Trace trace;for(int i=0;i<3;++i)trace.before[i]=before[i];
    /* ACTUAL_PRODUCTION_OWNERSHIP */
    const bool override_input=true;
    /* ACTUAL_PRODUCTION_GUIDANCE_GATE */
    const bool native_ownership=false,valid=true;
    const bool held_axis[]={held_pitch,held_yaw,held_roll};
    native_input::Params params{dt,modifier,15,8,10,4,6,5};
    /* ACTUAL_PRODUCTION_SELECTOR */
    for(int i=0;i<3;++i)predicted[i]=trace.predicted[i];
}
extern "C" __declspec(dllexport) void legacy_packet(float* axes,int keyboard,float input_scale){
    control.reset();maneuver_guard.reset();native_raw.reset();
    const auto pawn=reinterpret_cast<uintptr_t>(axes)-0x2268;
    native_raw.mapping(pawn+0x2268);native_raw.begin(pawn+0x2268,axes);
    const bool keyboard_pitch=(keyboard&1)!=0,keyboard_yaw=(keyboard&4)!=0,keyboard_roll=(keyboard&2)!=0,user_enabled=true;
    Trace trace;
    /* ACTUAL_PRODUCTION_OWNERSHIP */
    maneuver_guard.observe({1u<<23,0,input_scale,true},0,1);
    const bool apply_guidance=true,native_ownership=maneuver_guard.active,valid=true;
    const bool held_axis[]={held_pitch,held_yaw,held_roll};
    const float requested[]={1,-1,1};
    native_input::Params params{.016f,0,10,10,10,10,10,10};
    /* ACTUAL_PRODUCTION_SELECTOR */
}
extern "C" __declspec(dllexport) unsigned recovery_packet(int mode,unsigned flags,float state,float scale,int ready,
    int keyboard,float pitch,float yaw,float roll,float* sent){
    std::array<unsigned char,0x2600> pawn_storage{};std::array<unsigned char,0x500> settings{};
    const auto pawn=reinterpret_cast<uintptr_t>(pawn_storage.data());
    auto* dynamics=pawn_storage.data()+0x2300;dynamics[0x8d]=static_cast<unsigned char>(mode);
    memcpy(dynamics+0x3c,&state,4);memcpy(dynamics+0x40,&scale,4);dynamics[0x45]=static_cast<unsigned char>(ready);
    float axes[6]={pitch,yaw,roll,1,1,1};
    const bool keyboard_pitch=(keyboard&1)!=0,keyboard_yaw=(keyboard&4)!=0,keyboard_roll=(keyboard&2)!=0,user_enabled=true;
    Trace trace;
    /* ACTUAL_PRODUCTION_OWNERSHIP */
    control.observe(sample_player_maneuver(pawn,axes,settings.data(),flags),0,1,keyboard_pitch);
    const auto native_sample=sample_native_maneuver(pawn,flags);
    maneuver_guard.observe(native_sample,0,1);
    const bool apply_guidance=true,native_ownership=maneuver_guard.active||control.owns_rotation(),valid=true;
    const bool held_axis[]={held_pitch,held_yaw,held_roll};
    const float requested[]={1,-1,1};
    native_input::Params params{.016f,0,10,10,10,10,10,10};
    /* ACTUAL_PRODUCTION_SELECTOR */
    unsigned sync_commits=0;unsigned char* context=nullptr;
    auto commit_response_sync=[&](uintptr_t,unsigned char*,Trace&){++sync_commits;};
    /* ACTUAL_PRODUCTION_SYNC_GATE */
    memcpy(sent,axes,sizeof(axes));
    return (native_sample.native_alternate?1u:0u)|(control.active?2u:0u)|(native_ownership?4u:0u)|(sync_commits?8u:0u);
}
'''
fixture = fixture.replace("/* ACTUAL_PRODUCTION_OWNERSHIP */", ownership).replace("/* ACTUAL_PRODUCTION_SELECTOR */", selector).replace("/* ACTUAL_PRODUCTION_SYNC_GATE */", sync_line).replace("/* ACTUAL_PRODUCTION_GUIDANCE_GATE */", guidance_gate)
build = here / "input_zoom_build"
build.mkdir(exist_ok=True)
(build / "native_psm_pipeline.cpp").write_text(prefix + sampler + native_sampler + fixture, encoding="utf-8")
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
dll.legacy_packet.argtypes = [ctypes.POINTER(ctypes.c_float),ctypes.c_int,ctypes.c_float]
dll.legacy_packet.restype = None
dll.recovery_packet.argtypes = [ctypes.c_int,ctypes.c_uint,ctypes.c_float,ctypes.c_float,ctypes.c_int,
    ctypes.c_int,ctypes.c_float,ctypes.c_float,ctypes.c_float,ctypes.POINTER(ctypes.c_float)]
dll.recovery_packet.restype = ctypes.c_uint
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
    if state&6:
        require(list(sent)[1:3] == [yaw if keyboard&4 else 0,roll if keyboard&2 else 0], "claimed keyboard lateral axes retained; unclaimed base mouse excluded during preparation/native ownership")
    return (state,float(sent[0]),list(sent)) if full else (state,float(sent[0]))

executable = Executable(Path("E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe"))
try:
    for _, first, last, expected in PINNED_RANGES:
        require(hashlib.sha256(executable.read(first,last-first)).hexdigest() == expected, "pinned native instruction fingerprint")
    # Aggregate game mouse axes are not physical press provenance, even when
    # freshly mapped, positive, full-scale, or paired with throttle/brake.
    for pitch in [.1,.2,.8,1,-1]:
        dll.reset_control();packet(0,1,keyboard=False,mapping=1)
        state,sent,axes=packet(pitch,1,keyboard=False,mapping=2,yaw=.2,roll=.8,full=True)
        require(not state&6 and state&8 and sent==1 and axes[1]!=0 and axes[2]!=0,"base mouse cannot create PSM neutral edge or reserve pursuit axes")
    for keys in [0,2,4,6,7]:
        dll.reset_control()
        state,sent,axes=packet(.1,1,mode=2,keyboard=keys,mapping=1,yaw=.3125,roll=-.4375,full=True)
        require(state&4 and not state&2 and abs(sent-(.1 if keys&1 else 1))<1e-7,"observed native mode2 retains keyboard pull or existing mouse elevator intent")
    for keys in range(8):
        for scale in [0,.4,1]:
            raw=(ctypes.c_float*6)(.1,.3125,-.4375,1,1,1)
            expected=[raw[0] if keys&1 else float(ctypes.c_float(scale).value),raw[1] if keys&4 else 0,raw[2] if keys&2 else 0,1,1,1]
            dll.legacy_packet(raw,keys,scale)
            require(list(raw)==expected,"legacy dispatcher retains held keyboard axes, native-scaled mouse elevator and neutral unheld lateral axes")
    for keys in range(8):
        dll.reset_control()
        sent=(ctypes.c_float*6)()
        require(dll.recovery_packet(2,0,0,.2,0,keys,.625,.3125,-.4375,sent)&6==6,
            "actual mode2 owns accepted PSM before its native recovery tail")
        state=dll.recovery_packet(0,1<<19,0,.2,1,keys,.625,.3125,-.4375,sent)
        expected=[.625 if keys&1 else 1,.3125 if keys&4 else 0,-.4375 if keys&2 else 0,1,1,1]
        require(state&5==5 and not state&10 and list(sent)==expected,
            "actual native recovery sampler/selector retains ownership after mode2 ends, preserving all eight keyboard combinations, full mouse elevator and auxiliary input without response sync")
        state=dll.recovery_packet(0,1<<19,0,.2,0,keys,.625,.3125,-.4375,sent)
        require(not state&7 and state&8,"native recovery clearing restores ordinary input immediately even when pitch key is held")
    for flags,ready in [(0,1),(1<<19,0),(0x80,1),(0x88,1)]:
        dll.reset_control();sent=(ctypes.c_float*6)()
        state=dll.recovery_packet(0,flags,0,.2,ready,0,0,.3125,-.4375,sent)
        require(not state&7 and state&8,"native byte without flag19, flag19 without byte, or generic highG cannot claim recovery ownership")
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
    report={"passed":True,"checks":checks,"production_fragments":["ManualRotation boundary before PSM sampler","sample_player_maneuver","sample_native_maneuver","Control","raw selector","response sync gate"],"source_sha256":hashlib.sha256((runtime/'src/mouse_aim.cpp').read_bytes()).hexdigest(),"ownership_sha256":hashlib.sha256((runtime/'src/manual_rotation_input.h').read_bytes()).hexdigest(),"scope":"Synthetic memory; exact native PSM admission and observed dispatcher/recovery handoff; base mouse excluded before snapshots; no live-flight claim."}
    (here/'native_psm_input_pipeline_evidence.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f"PASS native PSM input pipeline: {checks} checks; actual ownership boundary/sampler/Control/raw selector/sync gate and unmodified native admission; aggregate mouse cannot fake native press; new S -> neutral once -> held mode2; keyboard/mouse mode2 elevator; generic-highG race prevented; auxiliary inputs retained. Synthetic memory only, no live-flight claim.")
finally:
    executable.close()
