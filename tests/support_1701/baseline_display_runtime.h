// All Unreal/window mutations are requested by the existing game-thread bridge.
// Camera consumers copy a small immutable command; no game calls under locks.
#include "display_math.h"
#include "display_window.h"
#include "scene_render_owner.h"
struct DisplaySettings { bool enabled=true,span=true;float fov=100,distance=3000,height=600; };
struct DisplayCommand { uintptr_t manager=0,pawn=0;ULONGLONG tick=0;ac8display::ViewMode mode=ac8display::ViewMode::Released;int viewport_width=0,viewport_height=0;uintptr_t actor_class=0,cinematic_class=0; };
int read_native_display_scene_state(uintptr_t pawn);
bool read_display_viewport_dimensions(int& width,int& height);
struct DisplayPerspectiveLease {uintptr_t manager=0;ac8display::Perspective native{},written{};};
bool final_projection_installed=false;
bool native_projection_gameplay(void* manager);
unsigned native_display_manager_kind(void* manager) {
    __try {
        if(!manager)return 0;
        const auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        const auto table=*reinterpret_cast<uintptr_t*>(manager);
        if(table==base+0xC9D3160)return 1;
        if(table==base+0xBB926F0)return 2;
    } __except(EXCEPTION_EXECUTE_HANDLER) {}
    return 0;
}
bool native_display_local_manager(void* manager) {
    __try {
        if(!native_display_manager_kind(manager))return false;
        const auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        const auto engine=*reinterpret_cast<uintptr_t*>(base+0xE4C50E8);
        return ac8display::local_render_owner(engine,reinterpret_cast<uintptr_t>(manager),base+0xBE7DDC8);
    } __except(EXCEPTION_EXECUTE_HANDLER) {return false;}
}
bool native_display_valid_target(uintptr_t target) {
    __try {return ac8headlook::valid_object(target);}
    __except(EXCEPTION_EXECUTE_HANDLER) {return false;}
}
uintptr_t native_display_view_target(void* manager) {
    __try {
        if(!native_display_manager_kind(manager))return 0;
        const auto pending=*reinterpret_cast<uintptr_t*>(static_cast<unsigned char*>(manager)+0xBC0);
        return pending?pending:*reinterpret_cast<uintptr_t*>(static_cast<unsigned char*>(manager)+0x320);
    } __except(EXCEPTION_EXECUTE_HANDLER) {return 0;}
}
bool native_display_class_is_a(uintptr_t target,uintptr_t wanted) {
    __try {
        if(!target||!wanted)return false;
        if((*reinterpret_cast<unsigned*>(target+8)&0x40000000u)!=0)return false;
        // Bundled runtime resolves UObject::ClassPrivate +10 and
        // UStruct::SuperStruct +40 from the active executable. Lua supplies
        // StaticFindObject('/Script/Engine.CameraActor'), never a guessed class.
        auto type=*reinterpret_cast<uintptr_t*>(target+0x10);
        for(unsigned depth=0;type&&depth<32;++depth) {
            if(type==wanted)return true;
            type=*reinterpret_cast<uintptr_t*>(type+0x40);
        }
    } __except(EXCEPTION_EXECUTE_HANDLER) {}
    return false;
}
bool native_rendered_camera_actor(uintptr_t target,uintptr_t camera_actor_class) {
    if(!native_display_class_is_a(target,camera_actor_class))return false;
    __try {
        // Pinned CameraActor constructor RVA 4182459 stores +298.
        // Its exact Outer proves the component belongs to this actor.
        const auto component=*reinterpret_cast<uintptr_t*>(target+0x298);
        return ac8headlook::valid_object(component)&&*reinterpret_cast<uintptr_t*>(component+0x20)==target;
    } __except(EXCEPTION_EXECUTE_HANDLER) {return false;}
}
bool native_rendered_camera_pawn(uintptr_t target,uintptr_t cinematic_class) {
    if(!native_display_class_is_a(target,cinematic_class))return false;
    __try {
        const auto component=*reinterpret_cast<uintptr_t*>(target+0x318);
        if(!ac8headlook::valid_object(component)||*reinterpret_cast<uintptr_t*>(component+0x20)!=target)return false;
        // Positive branch of native IsUsingAsCameraCut at RVA 6C90D80.
        // api() independently validates its native functions even when this
        // installation enables triple display without mouse flight/head look.
        const auto* calls=ac8headlook::api();
        if(!calls)return false;
        const auto registry=calls->registry(target);
        if(!ac8headlook::valid_object(registry))return false;
        const auto player=calls->player(registry);
        if(!ac8headlook::valid_object(player))return false;
        return calls->weak(player+0x494)==component;
    } __except(EXCEPTION_EXECUTE_HANDLER) {return false;}
}
// Camera updates use their existing game thread. Retain a few manager owners
// across transitions; restoration only touches the manager currently updating.
thread_local std::array<DisplayPerspectiveLease,4> display_perspective_leases{};
void restore_native_display(void* manager) {
    const auto address=reinterpret_cast<uintptr_t>(manager);
    for(auto& lease:display_perspective_leases) {
        if(lease.manager!=address)continue;
        __try {
            if(native_display_manager_kind(manager))
                ac8display::restore_matching_perspective(static_cast<unsigned char*>(manager)+0x14A0,lease.native,lease.written);
        } __except(EXCEPTION_EXECUTE_HANDLER) {}
        lease.manager=0;
    }
}
std::mutex display_mutex;
DisplaySettings display_settings;
DisplayCommand display_command;
wchar_t display_path[MAX_PATH]{};
ULONGLONG display_check_tick=0;
FILETIME display_file_time{};
bool display_file_seen=false;
std::atomic<bool> display_camera_fault{false};
ac8display::WindowSpan display_window_span;

// Optional fixed counters distinguish rejected native frames from successful
// camera updates. Disabled during normal play; at most one log every 5 seconds.
bool display_profile_decision(ac8display::Decision reason,void* manager=nullptr,uintptr_t expected=0,uintptr_t actual=0) {
    if(ac8profile::enabled.load(std::memory_order_relaxed)) {
        thread_local std::array<uint64_t,unsigned(ac8display::Decision::Count)> counts{};
        thread_local ULONGLONG previous_report=0;
        ++counts[unsigned(reason)];
        const auto now=GetTickCount64();
        if(now-previous_report>=5000) {
            previous_report=now;
            log_line("PROFILE display frames: applied=%llu released=%llu otherManager=%llu expired=%llu lockBusy=%llu targetChanged=%llu invalidLens=%llu viewport=%llu alreadyWide=%llu unsupported=%llu cutRecovered=%llu last=%u manager=%p expected=%p actual=%p",
                counts[0],counts[1],counts[2],counts[3],counts[4],counts[5],counts[6],counts[7],counts[8],counts[9],counts[10],unsigned(reason),manager,reinterpret_cast<void*>(expected),reinterpret_cast<void*>(actual));
            counts.fill(0);
        }
    }
    return reason==ac8display::Decision::Applied;
}

float display_number(const wchar_t* key,float fallback) {
    wchar_t value[64]{},fallback_text[64]{};
    swprintf_s(fallback_text,L"%.6f",fallback);
    GetPrivateProfileStringW(L"display",key,fallback_text,value,64,display_path);
    wchar_t* end=nullptr;const float parsed=wcstof(value,&end);
    return end!=value&&std::isfinite(parsed)?parsed:fallback;
}
void load_display(bool force=false) {
    init_paths();
    if(!display_path[0])swprintf_s(display_path,L"%s\\..\\display.ini",module_folder);
    const auto now=GetTickCount64();
    if(!force&&now-display_check_tick<1000)return;
    display_check_tick=now;
    WIN32_FILE_ATTRIBUTE_DATA data{};
    const bool seen=GetFileAttributesExW(display_path,GetFileExInfoStandard,&data)!=0;
    if(!force&&seen==display_file_seen&&(!seen||CompareFileTime(&display_file_time,&data.ftLastWriteTime)==0))return;
    display_file_seen=seen;display_file_time=seen?data.ftLastWriteTime:FILETIME{};
    // New display features require their explicit configuration file. A copied
    // DLL alone retains the previous controller/camera behavior.
    DisplaySettings next;
    next.enabled=pack_features.display&&seen&&GetPrivateProfileIntW(L"display",L"enabled",1,display_path)!=0;
    next.span=GetPrivateProfileIntW(L"display",L"span",1,display_path)!=0;
    next.fov=std::clamp(display_number(L"fov",100),60.f,120.f);
    next.distance=std::clamp(display_number(L"distance",3000),1500.f,6000.f);
    next.height=std::clamp(display_number(L"height",600),0.f,1500.f);
    {std::lock_guard<std::mutex> lock(display_mutex);display_settings=next;}
    log_line("DISPLAY configuration: enabled=%d triple=%d reference16:9FOV=%.1f distance=%.0f height=%.0f",next.enabled,next.span,next.fov,next.distance,next.height);
}
DisplaySettings current_display_settings() {
    std::lock_guard<std::mutex> lock(display_mutex);return display_settings;
}
void receive_display_camera(uintptr_t manager,uintptr_t pawn,ac8display::ViewMode mode,int width,int height,uintptr_t actor_class=0,uintptr_t cinematic_class=0) {
    std::lock_guard<std::mutex> lock(display_mutex);
    display_command={manager,pawn,GetTickCount64(),mode,width,height,actor_class,cinematic_class};
}
bool apply_native_display(void* manager,const DisplaySettings& settings,const DisplayCommand& cmd,int width,int height) {
    // A repeated post-update callback must not adopt our widened lens as native.
    restore_native_display(manager);
    if(!settings.enabled)return display_profile_decision(ac8display::Decision::Released,manager);
    __try {
        if(!native_display_manager_kind(manager))return display_profile_decision(ac8display::Decision::OtherManager,manager);
        // Pinned native GetViewTarget prefers the pending camera while blending.
        const auto target=native_display_view_target(manager);
        if(target!=cmd.pawn)return display_profile_decision(ac8display::Decision::TargetChanged,manager,cmd.pawn,target);
        unsigned char* pov=static_cast<unsigned char*>(manager)+0x14A0;
        const auto native=ac8display::read_perspective(pov);
        auto mode=cmd.mode;
        if(mode==ac8display::ViewMode::Gameplay) {
            const auto scene=read_native_display_scene_state(cmd.pawn);
            if(scene<0)return false;
            if(scene>0)mode=ac8display::ViewMode::ScenePawn;
        }
        ac8display::Perspective written=native;
        if(mode==ac8display::ViewMode::Gameplay) {
            if(native.projection_mode!=0)return display_profile_decision(ac8display::Decision::InvalidLens,manager);
            flight::Basis pose;if(!read_live_basis(cmd.pawn,pose))return false;
            written.fov=written.desired_fov=ac8display::horizontal_fov(settings.fov,width,height);
            written.aspect=float(width)/height;written.flags|=1u;
            if(!ac8display::valid_perspective(written.fov,written.aspect))return false;
        } else if(mode==ac8display::ViewMode::ScenePawn || mode==ac8display::ViewMode::SceneActor) {
            if(!ac8display::valid_projection(native))return display_profile_decision(ac8display::Decision::InvalidLens,manager);
            if(cmd.viewport_width!=width||cmd.viewport_height!=height)
                return display_profile_decision(ac8display::Decision::Viewport,manager);
            if(float(width)/height<=native.aspect+0.0001f) {
                // The scene already renders this width (or a wider authored
                // lens). This is a usable projection, requiring no override.
                display_profile_decision(ac8display::Decision::AlreadyWide,manager);return true;
            }
            if(!ac8display::scene_perspective(native,width,height,written))
                return display_profile_decision(ac8display::Decision::InvalidLens,manager);
        } else return false;
        // An explicit viewport-matching aspect avoids both letterboxing and
        // MaintainY/legacy axis conversion. Preserve all other packed flags.
        auto* lease=&display_perspective_leases.front();
        for(auto& entry:display_perspective_leases)if(!entry.manager || entry.manager==reinterpret_cast<uintptr_t>(manager)){lease=&entry;break;}
        // Skip rather than evict a live manager's unrecovered native lens.
        if(lease->manager && lease->manager!=reinterpret_cast<uintptr_t>(manager))return false;
        *lease={reinterpret_cast<uintptr_t>(manager),native,written};
        ac8display::write_perspective(pov,written);
        return display_profile_decision(ac8display::Decision::Applied,manager);
    } __except(EXCEPTION_EXECUTE_HANDLER) {return display_profile_decision(ac8display::Decision::Unsupported,manager);}
}
bool update_native_display(void* manager) {
    if(!running.load())return true;
    DisplaySettings settings;DisplayCommand cmd;
    {std::unique_lock<std::mutex> lock(display_mutex,std::try_to_lock);if(!lock.owns_lock())return display_profile_decision(ac8display::Decision::LockBusy,manager);
        settings=display_settings;cmd=display_command;}
    if(!settings.enabled) {
        display_profile_decision(ac8display::Decision::Released,manager);return true;
    }
    if(final_projection_installed) {
        // Scene expansion belongs to the final LocalPlayer projection, after
        // locked FOV, local overrides and view extensions. The retained cache
        // only receives the gameplay slider here so the existing zoom computes
        // from its unzoomed lens. No scene admission or camera class list.
        if(!native_projection_gameplay(manager))return true;
        int w=0,h=0;
        if(!read_display_viewport_dimensions(w,h))return false;
        cmd={reinterpret_cast<uintptr_t>(manager),native_display_view_target(manager),
             GetTickCount64(),ac8display::ViewMode::Gameplay,w,h};
        return apply_native_display(manager,settings,cmd,w,h);
    }
    // The current LocalPlayer/controller/manager backlink is this frame's
    // ownership evidence. A previous Lua publication cannot authorize an old
    // manager, and a new native briefing/menu controller needs no class list.
    if(!native_display_local_manager(manager)) {
        display_profile_decision(ac8display::Decision::OtherManager,manager);return true;
    }
    // The exact native manager has just finished calculating this frame's
    // render POV. Lua proves the local controller/manager association only;
    // reflected camera-component discovery is not the renderer's authority.
    // This covers custom CalcCamera targets and same-frame native camera cuts
    // without selecting a camera, invoking target functions or scanning actors.
    const auto target=native_display_view_target(manager);
    if(!native_display_valid_target(target))return display_profile_decision(ac8display::Decision::Unsupported,manager);
    const bool matching_lua=cmd.manager==reinterpret_cast<uintptr_t>(manager)&&cmd.pawn==target&&
        cmd.tick&&GetTickCount64()>=cmd.tick&&GetTickCount64()-cmd.tick<=250;
    if(!matching_lua)cmd.viewport_width=cmd.viewport_height=0;
    if(!matching_lua||cmd.mode==ac8display::ViewMode::Released||cmd.mode==ac8display::ViewMode::Observe) {
        if(target!=cmd.pawn)display_profile_decision(ac8display::Decision::CutRecovered,manager,cmd.pawn,target);
        cmd.mode=ac8display::ViewMode::SceneActor;
    }
    cmd.manager=reinterpret_cast<uintptr_t>(manager);cmd.pawn=target;cmd.tick=GetTickCount64();
    if(display_camera_fault)return false;
    const auto client=ac8display::physical_client_metrics(game_window);
    if(!client.valid||client.width<=0||client.height<=0)return false;
    // UE4SS's out-parameter representation is not a reliable renderer-size
    // observation on this host. Read the guarded live engine viewport that
    // already owns the successful triple backbuffer resize, every camera frame.
    int render_width=0,render_height=0;
    if(read_display_viewport_dimensions(render_width,render_height)) {
        cmd.viewport_width=render_width;cmd.viewport_height=render_height;
    }
    // The engine's render viewport must have followed the window resize.
    // Out-parameter representations differ across UE4SS builds; zero means
    // no usable engine observation rather than pretending it was measured.
    if(cmd.viewport_width>0&&cmd.viewport_height>0&&
       (cmd.viewport_width!=client.width||cmd.viewport_height!=client.height))return false;
    if(cmd.mode!=ac8display::ViewMode::Gameplay &&
       (cmd.viewport_width<=0||cmd.viewport_height<=0))return false;
    // Invalid/transient cinematic lens data is a skipped frame, not a sticky
    // session failure. Before this update, any matching previous write was
    // restored, so skipped/disabled/unsupported scenes retain the native POV.
    if(!apply_native_display(manager,settings,cmd,client.width,client.height))return false;
    static int previous_w=0,previous_h=0;static float previous_fov=0;
    static auto previous_mode=ac8display::ViewMode::Released;
    static ULONGLONG previous_report_tick=0;
    const float fov=ac8display::read_perspective(static_cast<unsigned char*>(manager)+0x14A0).fov;
    const auto now=GetTickCount64();
    const bool geometry_changed=previous_w!=client.width||previous_h!=client.height||previous_mode!=cmd.mode;
    if(geometry_changed||(std::abs(previous_fov-fov)>.01f&&now-previous_report_tick>=1000)) {
        previous_w=client.width;previous_h=client.height;previous_fov=fov;
        previous_mode=cmd.mode;previous_report_tick=now;
        log_line("DISPLAY final POV: client=%dx%d engineViewport=%dx%d aspect=%.6f horizontalFOV=%.3f mode=%u constraint=viewport-matched",client.width,client.height,cmd.viewport_width,cmd.viewport_height,float(client.width)/client.height,fov,unsigned(cmd.mode));
    }
    return true;
}
