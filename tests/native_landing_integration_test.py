"""Compile actual landing helper, pose/camera receivers and processor entry.

Heavy ordinary steering is replaced by a counted boundary after the actual
production entry gate. The real RAW ownership, landing sampler and input
lifecycle run against synthetic pawn/component memory. No game is launched.
"""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parent / 'runtime'
source = (RUNTIME / 'src/mouse_aim.cpp').read_text()
camera = (RUNTIME / 'src/native_camera.h').read_text()

def function(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

helper = function(source, 'bool observe_native_landing(uintptr_t pawn) {')
pose = function(source, 'void receive_pose(const double (&v)[13]) {')
camera_receiver = function(camera, 'bool receive_camera(uintptr_t manager,uintptr_t pawn,double p,double y,double r) {')
camera_update = function(camera, 'void __fastcall update_native_camera(void* manager,float dt) {')
camera_update_gate = camera_update[:camera_update.index('    HudFrame frame;')]
processor = function(source, 'uintptr_t __fastcall process_input(unsigned char* state, unsigned char* context) {')
entry = processor[:processor.index('    if(!active.load()')]
worker = function(source, 'void update_commands() {')
worker_gate = worker[:worker.index('    const auto now')]

# Verify the extracted boundary actually precedes all flight writes, and fail
# if a source edit changes the tested entry arrangement.
assert processor.index('native_raw.begin(') < processor.index('if(observe_native_landing(pawn))')
assert processor.index('if(observe_native_landing(pawn))') < processor.index('manual_rotation.retain_keyboard(')
assert processor.index('if(observe_native_landing(pawn))') < processor.index('commit_response_sync(')
assert pose.index('observe_native_landing(address);') < pose.index('update_commands();')
assert 'native_landing_owned.load()' in worker_gate
assert camera_update_gate.index('observe_native_landing(cmd.pawn)') < camera_update_gate.index('apply_native_camera(')
prepare = function(source, 'bool prepare_hook() {')
assert prepare.index('if(!landing_code_verified)return false;') < prepare.index('MH_Initialize()')

prelude = r'''
#define NOMINMAX
#include <windows.h>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include "native_landing_guard.h"
#include "native_raw_input.h"
#include "input_lifecycle.h"
struct Resettable {unsigned resets=0;void reset(){++resets;}};
Resettable native_rudder,live_guidance,maneuver_guard,player_maneuver_control,free_look,guidance;
struct Origin {bool automatic=false;unsigned clears=0;void clear(){automatic=false;++clears;}};
Origin player_admission_origin;
native_input::RawOwnership native_raw;
flight::InputLifecycle input_lifecycle;
std::atomic<bool> active{true},enabled{true},game_paused{false},gaze_active{false},native_landing_owned{false};
std::atomic<bool> running{true};
std::atomic<bool> native_maneuver_active{false},zoom_requested{false},manual_free_look{false};
std::atomic<bool> recenter_requested{false},resume_center_requested{false},perf_enabled{false};
std::atomic<float> command_pitch{},command_yaw{},command_roll{},zoom_magnification{1};
std::atomic<float> pose_pitch{},pose_yaw{},pose_roll{},camera_pitch{},camera_yaw{},camera_roll{};
std::atomic<float> view_offset_x{},view_offset_y{},view_offset_z{},view_fov{100},roll_reference{};
std::atomic<unsigned long long> applied_tick{},pose_tick{},input_generation{1};
std::atomic<uintptr_t> aircraft{};
std::atomic<long> mouse_dx{},mouse_dy{};
unsigned long long previous_pose_tick=0,telemetry_tick=0,perf_player_inputs=0,perf_other_inputs=0;
bool landing_code_verified=true;
std::mutex camera_command_mutex,target_vector_mutex;
flight::V live_target{1,0,0};
struct CameraCommand {uintptr_t manager=0,pawn=0;double p=0,y=0,r=0;flight::V aim{1,0,0};ULONGLONG tick=0;};
CameraCommand camera_command;
unsigned hud_invalidations=0,normal_updates=0,normal_inputs=0,native_inputs=0,seed_count=0;
unsigned native_camera_calls=0,camera_applies=0,zoom_resets=0;
bool native_camera_starts_landing=false,native_camera_fault=false;
struct Features {bool mouse_flight=true;} pack_features;
int perf_camera=0;
struct PerfSpan {explicit PerfSpan(int){}};
enum class CameraViewMode {Unavailable,FirstPerson,Cockpit,ThirdPerson};
float received_raw[3]{};
double fixture_time=0;
flight::Basis fixture_basis=flight::basis(-2.907f,-35.666f,0);
void invalidate_hud_frame(){++hud_invalidations;}
void log_line(const char*,...){}
unsigned long long fixture_tick(){return 4000;}
HMODULE fixture_module(const wchar_t*){return reinterpret_cast<HMODULE>(0x140000000ull);}
#define GetModuleHandleW fixture_module
#define GetTickCount64 fixture_tick
void restore_native_zoom(void*){}
void restore_native_display(void*){}
void original_camera_update(void*,float){
    ++native_camera_calls;
    if(native_camera_starts_landing)*reinterpret_cast<std::uint32_t*>(aircraft.load()+0x2B18)=0x40200;
}
bool update_native_display(void*){return true;}
void reset_native_zoom_state(void*,bool=true){++zoom_resets;}
uintptr_t native_display_view_target(void*){return aircraft.load();}
bool foreground_is_game(){return true;}
CameraViewMode read_native_camera_mode(uintptr_t){return CameraViewMode::ThirdPerson;}
bool apply_native_camera(void*,const CameraCommand&,CameraViewMode){++camera_applies;return true;}
void require(bool value,const char* label){if(!value){std::fprintf(stderr,"FAIL: %s\n",label);std::exit(1);}}
uintptr_t original(unsigned char*,unsigned char*) {
    ++native_inputs;
    auto* raw=reinterpret_cast<const float*>(aircraft.load()+0x2268);
    std::memcpy(received_raw,raw,sizeof(received_raw));
    return 0xAC8;
}
uintptr_t normal_entry() {
    ++normal_inputs;
    if(input_lifecycle.observe(fixture_time,.016f,input_generation.load(),aircraft.load(),fixture_basis,true,true))++seed_count;
    applied_tick.store(fixture_tick());
    return 0xBEEF;
}
bool receive_camera(uintptr_t,uintptr_t,double,double,double);
bool observe_native_landing(uintptr_t);
void update_commands();
template<class T,std::size_t N>void put(std::array<unsigned char,N>& memory,unsigned offset,T value){std::memcpy(memory.data()+offset,&value,sizeof(value));}
'''
body = prelude + '\n' + camera_receiver + '\n' + helper + '\n'
body += worker_gate + '    ++normal_updates;\n}\n'
body += pose + '\n' + entry + '    return normal_entry();\n}\n'
body += camera_update_gate + '}\n'
body += r'''
int main() {
    std::array<unsigned char,0x5900> plane{};
    std::array<unsigned char,0x1A0> component{};
    std::array<unsigned char,0x40> controller{},wanted_class{},actual_class{};
    std::array<std::uintptr_t,2> ancestors{};
    const auto pawn=reinterpret_cast<uintptr_t>(plane.data());
    const auto comp=reinterpret_cast<uintptr_t>(component.data());
    const auto wanted=reinterpret_cast<std::uintptr_t>(wanted_class.data());
    auto* class_cache=VirtualAlloc(reinterpret_cast<void*>(0x14E510000ull),0x10000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    require(class_cache==reinterpret_cast<void*>(0x14E510000ull),"synthetic module class cache allocation");
    *reinterpret_cast<std::uintptr_t*>(0x14E515A30ull)=wanted;
    put(controller,0x10,reinterpret_cast<std::uintptr_t>(actual_class.data()));
    put(wanted_class,0x38,int(1));put(actual_class,0x38,int(1));
    ancestors[1]=wanted+0x30;put(actual_class,0x30,reinterpret_cast<std::uintptr_t>(ancestors.data()));
    put(plane,0x58B0,comp);put(component,0,std::uintptr_t(0x140000000ull+0xC9E0FE0));
    put(component,0x20,pawn);put(component,0x90,pawn);put(component,0x118,unsigned(2));
    put(plane,0x2B18,std::uint32_t(1u<<18));aircraft.store(pawn);
    std::array<unsigned char,0x30> context{};put(context,0,pawn+0x2268);
    auto* state=plane.data()+0x22A0;
    auto* raw=reinterpret_cast<float*>(plane.data()+0x2268);
    const double frame[13]={double(pawn),-2.907,-35.666,0,-2.907,-35.666,0,100,0,0,0,0,0};
    receive_pose(frame);
    require(normal_updates==1&&!native_landing_owned,"ordinary gear-down approach still updates mouse aim");
    require(receive_camera(0x1234,pawn,1,2,3)&&camera_command.manager==0x1234,"ordinary approach retains requested camera");
    require(process_input(state,context.data())==0xBEEF&&normal_inputs==1&&seed_count==1,"ordinary approach enters steering boundary");
    update_native_camera(reinterpret_cast<void*>(0x1234),.016f);
    require(camera_applies==1,"ordinary gear-down approach applies requested flight camera");
    input_lifecycle.pending_seed=false;
    put(plane,0x2B18,std::uint32_t(0x40200));
    require(!observe_native_landing(pawn)&&!native_landing_owned,"bit9 alone without native transform controller retains approach");
    put(plane,0xED0,reinterpret_cast<std::uintptr_t>(controller.data()));

    // Simulate a retained prior automatic packet, followed by native ownership.
    raw[0]=.25f;raw[1]=-.125f;raw[2]=.5f;native_raw.begin(pawn+0x2268,raw);
    for(int axis=0;axis<3;++axis){raw[axis]=1;native_raw.wrote(pawn+0x2268,axis,1);}
    player_admission_origin.automatic=true;mouse_dx.store(500);mouse_dy.store(-500);
    put(plane,0x2B18,std::uint32_t(0x40200));
    require(process_input(state,context.data())==0xAC8,"actual processor entry yields to native landing");
    require(received_raw[0]==.25f&&received_raw[1]==-.125f&&received_raw[2]==.5f,"RAW cleanup runs before native ownership gate");
    require(normal_inputs==1&&native_inputs==1&&!player_admission_origin.automatic,"landing bypasses ordinary writes and clears automatic PSM provenance");
    require(input_lifecycle.pending_seed&&!input_lifecycle.have_forward,"landing entry arms one live heading seed");
    require(!camera_command.manager&&hud_invalidations,"landing transition invalidates old camera/HUD");
    require(receive_camera(0x1234,pawn,90,180,0)&&!camera_command.manager,"late Lua camera command cannot reacquire scripted landing");

    // Fresh game mapping must win even when its bits equal the prior mod output.
    native_raw.begin(pawn+0x2268,raw);
    for(int axis=0;axis<3;++axis){raw[axis]=1;native_raw.wrote(pawn+0x2268,axis,1);}
    native_raw.mapping(pawn+0x2268);
    require(process_input(state,context.data())==0xAC8&&received_raw[0]==1&&received_raw[1]==1&&received_raw[2]==1,"fresh native packet survives ownership gate");
    const auto updates=normal_updates;
    for(unsigned i=0;i<20;++i){mouse_dx.store(123);receive_pose(frame);require(!camera_command.manager,"scripted camera stays released");}
    require(normal_updates==updates&&normal_inputs==1,"actual pose receiver blocks worker target updates while owned");

    put(component,0x90,std::uintptr_t(0));
    require(process_input(state,context.data())==0xAC8&&native_landing_owned,"transient foreign/unreadable component does not revive steering");
    put(component,0x90,pawn);
    put(plane,0x2B18,std::uint32_t(1u<<18));fixture_time=.5;
    receive_pose(frame);
    require(!native_landing_owned&&input_lifecycle.pending_seed&&mouse_dx==0,"normal approach resumes and discards queued landing mouse movement");
    require(process_input(state,context.data())==0xBEEF&&seed_count==2,"first resumed ordinary input seeds current heading once");
    fixture_time=.516;process_input(state,context.data());require(seed_count==2,"later ordinary approach preserves aim target");
    receive_camera(0x1234,pawn,4,5,6);require(camera_command.manager==0x1234,"ordinary approach can reacquire camera");
    // Native landing can start inside camera processing after the last input
    // or Lua pose callback. The actual post-update gate must re-sample it.
    const auto applied_before=camera_applies;
    native_camera_starts_landing=true;
    update_native_camera(reinterpret_cast<void*>(0x1234),.016f);
    require(native_landing_owned&&!camera_command.manager&&camera_applies==applied_before,"camera post-update re-samples same-frame native landing before mod application");
    native_camera_starts_landing=false;put(plane,0x2B18,std::uint32_t(1u<<18));
    observe_native_landing(pawn);
    const auto cleared=player_admission_origin.clears;
    require(process_input(plane.data(),context.data())==0xAC8&&player_admission_origin.clears==cleared,"non-player invocation bypasses all player ownership work");

    // Native PSM dispatch and its recovery do not become landing ownership.
    put(plane,0x2B18,std::uint32_t((1u<<17)|(1u<<19)));fixture_time=.532;
    require(process_input(state,context.data())==0xBEEF&&!native_landing_owned,"PSM flags alone retain existing maneuver path");
    put(plane,0x2B18,std::uint32_t(0x40200));observe_native_landing(pawn);
    input_generation.fetch_add(1);put(plane,0x2B18,std::uint32_t(0));observe_native_landing(pawn);
    require(!native_landing_owned&&input_lifecycle.pending_seed,"new generation resets stale native ownership");
    put(plane,0x2B18,std::uint32_t(0x40200));observe_native_landing(pawn);observe_native_landing(0);
    require(!native_landing_owned&&input_lifecycle.pending_seed,"release clears published ownership and retains reseed");
    VirtualFree(class_cache,0,MEM_RELEASE);
    std::puts("PASS: extracted production helper/pose/camera/processor gates; ordinary gear-down approach, native RAW cleanup/fresh mapping, PSM provenance, late camera release, same-frame camera post-update landing acquisition, transient unavailable ownership, worker freeze, single resumed seed, epoch and release.");
}
'''
build = HERE / 'native_landing_integration_build'
build.mkdir(exist_ok=True)
(build / 'extracted_landing_integration.cpp').write_text(body)
vcvars = Path('C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat')
command = ('@echo off\ncall "' + str(vcvars) + '" >nul\n'
           'cl /nologo /EHsc /std:c++20 /O2 /I"' + str(RUNTIME / 'src') +
           '" extracted_landing_integration.cpp /Fe:landing_integration_test.exe >build.log 2>&1\n'
           'if errorlevel 1 exit /b 1\nlanding_integration_test.exe\n')
(build / 'run.cmd').write_text(command)
result = subprocess.run(['cmd', '/c', str(build / 'run.cmd')], cwd=build, capture_output=True, text=True)
if result.returncode:
    print(result.stdout, result.stderr, (build / 'build.log').read_text(encoding='utf-8', errors='replace'))
    raise SystemExit(result.returncode)
print(result.stdout.strip())
evidence = {'scope': 'Actual extracted production entry/helper/pose/camera gates against synthetic actors; ordinary flight physics tail is outside this harness.',
            'mouse_aim_sha256': hashlib.sha256((RUNTIME / 'src/mouse_aim.cpp').read_bytes()).hexdigest(),
            'native_camera_sha256': hashlib.sha256((RUNTIME / 'src/native_camera.h').read_bytes()).hexdigest(),
            'extracted_sha256': hashlib.sha256(body.encode()).hexdigest(), 'result': result.stdout.strip(),
            'ordering': 'native_raw.begin before observe_native_landing before manual rotation filtering or response sync; receive_pose observes ownership before update_commands; camera post-update re-samples after original native camera and before mod application'}
(HERE / 'native_landing_integration_evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
