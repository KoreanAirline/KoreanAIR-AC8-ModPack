"""Execute the real numeric target update path; no game flight is simulated."""
from pathlib import Path
import hashlib,json,subprocess
T=Path(__file__).resolve().parent;R=T.parent/'runtime'
template=(T/'scene_input_release_test.py').read_text()
context={'__file__':str(T/'scene_input_release_test.py'),'__name__':'fixture_prefix'}
exec(compile(template[:template.index('build = here /')],str(T/'scene_input_release_test.py'),'exec'),context)
function=context['function'];prefix=context['prefix']
fixture=r'''
namespace ac8profile {std::atomic<bool> enabled{false};}
std::atomic<uint64_t> pointer_integrations{0};
bool free_look_suspends_guidance(){return manual_free_look.load()||free_look_key_pressed;}
unsigned wakes=0;void wake_overlay(){++wakes;}
'''
fixture+=function('publish_target')+function('read_target')+function('advance_pointer')+function('capture_get_raw_input_data')+function('update_commands')
fixture+=r'''
int main(){
 using namespace flight;update_commands();independent_mouse_capture.store(true);
 auto goal=[] {return read_target({1,0,0});};const auto view=basis(0,0,0);
 // Five real coordinate changes per 36-Hz frame, while keeping the exact
 // existing ordinary lens/axis math. No interpolation/smoothing is used.
 for(unsigned frame=0;frame<36;++frame){
  for(unsigned sample=0;sample<5;++sample){
   ++clock_tick;const auto previous=goal();
   require(advance_pointer(1,0),"fresh true mouse goal can advance between engine frames");
   require(dot(goal()-previous,goal()-previous)>0,"each accepted physical sample immediately moves actual goal");
  }
  const auto previous=goal();update_commands();
  require(dot(goal()-previous,goal()-previous)<2e-12f,"base update cannot replay independently consumed mouse input");
 }
 require(wakes==180&&std::abs(yaw(goal())-18)<.002f,"exact count preservation with 180 target publications during36 frames");
 RAWINPUT packet{},out{};packet.header.dwType=RIM_TYPEMOUSE;packet.data.mouse.lLastX=100;packet.data.mouse.lLastY=-100;
 UINT bytes=sizeof(out);capture_get_raw_input_data(reinterpret_cast<HRAWINPUT>(&packet),RID_INPUT,&out,&bytes,sizeof(RAWINPUTHEADER));
 require(mouse_dx.load()==0&&mouse_dy.load()==0,"same physical input from game RAW feed is never counted twice");
 independent_mouse_capture.store(false);capture_get_raw_input_data(reinterpret_cast<HRAWINPUT>(&packet),RID_INPUT,&out,&bytes,sizeof(RAWINPUTHEADER));
 require(mouse_dx.load()==100&&mouse_dy.load()==-100,"missing helper retains original native RAW capture");mouse_dx.store(0);mouse_dy.store(0);
 for(unsigned boundary=0;boundary<8;++boundary){
  const auto previous=goal();const auto epoch=input_generation.load();
  if(boundary==0)game_paused.store(true);if(boundary==1)gaze_active.store(true);
  if(boundary==2)native_landing_owned.store(true);if(boundary==3)enabled.store(false);
  if(boundary==4)active.store(false);if(boundary==5)recenter_requested.store(true);
  if(boundary==6)resume_center_requested.store(true);if(boundary==7)input_generation.fetch_add(1);
  require(!advance_pointer(20,-20)&&dot(goal()-previous,goal()-previous)==0,"pause/gaze/landing/disable/lifecycle boundary blocks stale asynchronous goal");
  game_paused.store(false);gaze_active.store(false);native_landing_owned.store(false);enabled.store(true);active.store(true);
  recenter_requested.store(false);resume_center_requested.store(false);input_generation.store(epoch);
 }
 const auto previous=goal();free_look_key_pressed=true;
 require(!advance_pointer(100,-100)&&dot(goal()-previous,goal()-previous)==0,"ALT key pauses flight goal before next engine frame");
 queue_mouse_input(100,-100);update_commands();
 require(free_look.held&&!pointing_snapshot.ready&&dot(goal()-previous,goal()-previous)<2e-12f,"ALT enter discards boundary packet");
 queue_mouse_input(20,-20);++clock_tick;update_commands();
 require(std::abs(look_yaw.load()-.6f)<.001f&&dot(goal()-previous,goal()-previous)<2e-12f,"ALT keeps its existing sensitivity and separate flight aim");
 free_look_key_pressed=false;manual_free_look.store(false);
 require(!advance_pointer(10,-10),"ALT release waits for serialized native boundary, never applies old look movement as flight input");
 queue_mouse_input(100,-100);++clock_tick;update_commands();
 const auto release_expected=ac8pointing::move(previous,view,100,-100,config.sensitivity,zoom_magnification.load());
 require(!free_look.held&&pointing_snapshot.ready&&dot(goal()-release_expected,goal()-release_expected)<2e-12f,"ALT release preserves known fresh flight packet and restores real pointing");
 command_pitch.store(.75f);command_roll.store(-.4f);command_yaw.store(.2f);native_maneuver_active.store(true);
 require(advance_pointer(3,-3)&&command_pitch.load()==.75f&&command_roll.load()==-.4f&&command_yaw.load()==.2f,"native maneuver mouse intent accepted without writing any aircraft command or pose");
 native_maneuver_active.store(false);
 scene_mouse.bind(999,false,clock_tick);
 require(!advance_pointer(10,-10),"interactive cinematic lease never changes flight goal");scene_mouse.clear();
 clock_tick+=251;require(!advance_pointer(10,-10),"stale game lens cannot generate target updates");
 std::printf("PASS actual independent target pipeline: %u checks; true 180/36 updates, exact count conservation, exclusive capture, ALT/mission/pause/landing/scene gates, unchanged native maneuver commands. No live flight claim.\n",checks);
}
'''
B=T/'independent_pointing_build';B.mkdir(exist_ok=True)
(B/'fixture.cpp').write_text(prefix+fixture)
vcvars=Path('C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat')
(B/'run.cmd').write_text(f'@echo off\ncall "{vcvars}" >nul\ncl /nologo /O2 /EHsc /std:c++20 /I"{R/"src"}" fixture.cpp /Fe:fixture.exe >build.log 2>&1\nif errorlevel 1 exit /b 1\nfixture.exe\n')
result=subprocess.run(['cmd','/c',str(B/'run.cmd')],cwd=B,capture_output=True,text=True)
if result.returncode:raise RuntimeError(result.stdout+result.stderr+(B/'build.log').read_text(errors='replace'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
evidence={'passed':True,'scope':'Actual extracted production pointing pipeline, synthetic numeric/OS inputs only; no live flight or monitor FPS claim.','result':result.stdout.strip(),'source_sha256':{str(p.relative_to(T.parent)):sha(p) for p in (R/'src/mouse_aim.cpp',R/'src/aim_input_state.h',Path(__file__))}}
(T/'independent_pointing_pipeline_evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
print(result.stdout.strip())
