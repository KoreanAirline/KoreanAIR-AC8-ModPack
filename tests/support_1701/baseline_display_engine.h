// AC8 build 6AA0E27D. Entry points were resolved from the setres sink and the
// live GameViewport's vtable, then checked against this executable's code.
// Keep window, Slate cached geometry, render viewport and backbuffer on the
// original engine resize path. Never resize its HWND independently.
using EngineResizeFrame=void(__fastcall*)(void*,uint32_t,uint32_t,int);
using NativeWindowReshape=void(__fastcall*)(void*,int32_t,int32_t,int32_t,int32_t);
using NativeWindowMove=void(__fastcall*)(void*,int32_t,int32_t);
using CachedWindowPosition=void(__fastcall*)(void*,uint64_t);
EngineResizeFrame original_engine_resize=nullptr;
NativeWindowReshape original_window_reshape=nullptr;
std::mutex engine_span_mutex;
ac8display::WindowPlan engine_span_plan;
ac8display::ClientMetrics engine_span_original;
bool engine_span_desired=false,engine_span_installed=false,engine_span_failed=false;
uint64_t engine_span_sequence=0;
uint64_t engine_span_acknowledged=0;
ac8display::EngineSpanRecovery engine_span_recovery;
thread_local bool engine_span_scope=false;
thread_local ac8display::WindowPlan scoped_engine_span;
std::atomic<unsigned> engine_span_resize_calls{0},engine_span_slate_calls{0};
std::atomic<uintptr_t> engine_span_last_window{0};
thread_local bool correcting_span_cache=false;
bool current_engine_viewport(void* candidate) {
    __try {
        const auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        const auto engine=*reinterpret_cast<uintptr_t*>(base+0xE4C50E8);
        if(!engine)return false;
        const auto client=*reinterpret_cast<uintptr_t*>(engine+0xA80);
        return client&&*reinterpret_cast<uintptr_t*>(client+0xF0)==reinterpret_cast<uintptr_t>(candidate);
    } __except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
uintptr_t live_engine_viewport() {
    __try {
        const auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        const auto engine=*reinterpret_cast<uintptr_t*>(base+0xE4C50E8);
        if(!engine)return 0;
        const auto client=*reinterpret_cast<uintptr_t*>(engine+0xA80);
        return client?*reinterpret_cast<uintptr_t*>(client+0xF0):0;
    } __except(EXCEPTION_EXECUTE_HANDLER){return 0;}
}
bool read_display_viewport_dimensions(int& width,int& height) {
    width=height=0;
    // Reading the engine's actual render size does not require installing the
    // optional multi-monitor resize hooks. Unspanned ultrawide windows use the
    // same pinned viewport identity, owner chain and dimension range guards.
    __try {
        const auto viewport=live_engine_viewport();
        const auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        if(!viewport||!current_engine_viewport(reinterpret_cast<void*>(viewport))||
           *reinterpret_cast<uintptr_t*>(viewport)!=base+0xBE7DDC8)return false;
        const int w=*reinterpret_cast<int*>(viewport+0xA8),h=*reinterpret_cast<int*>(viewport+0xAC);
        if(w<640||h<360||w>16384||h>16384)return false;
        width=w;height=h;
        static int previous_w=0,previous_h=0;
        if(w!=previous_w||h!=previous_h){previous_w=w;previous_h=h;log_line("DISPLAY native render viewport: %dx%d (guarded live GameViewport)",w,h);}
        return true;
    } __except(EXCEPTION_EXECUTE_HANDLER) {return false;}
}
bool current_engine_window(void* native) {
    __try {
        if(!native)return false;
        const auto hwnd=*reinterpret_cast<HWND*>(static_cast<unsigned char*>(native)+0x28);
        const auto table=*reinterpret_cast<uintptr_t*>(native);
        const auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        if(table!=base+0xB4CF6E0)return false;
        DWORD process=0;GetWindowThreadProcessId(hwnd,&process);
        return hwnd==game_window&&process==GetCurrentProcessId();
    } __except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
uintptr_t owning_scene_window(uintptr_t viewport) {
    __try {
        if(!viewport)return 0;
        const auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        auto widget=*reinterpret_cast<uintptr_t*>(viewport+0x250);
        for(unsigned count=0;widget&&count<16;++count) {
            const auto table=*reinterpret_cast<uintptr_t*>(widget);
            if(*reinterpret_cast<uintptr_t*>(table+0x208)==base+0x16BACA0)return widget;
            widget=*reinterpret_cast<uintptr_t*>(widget+0x1E0);
        }
        return 0;
    } __except(EXCEPTION_EXECUTE_HANDLER){return 0;}
}
HWND guarded_engine_window(uintptr_t viewport,uintptr_t& native) {
    native=0;
    __try {
        const auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        if(!viewport||!current_engine_viewport(reinterpret_cast<void*>(viewport))||
           *reinterpret_cast<uintptr_t*>(viewport)!=base+0xBE7DDC8)return nullptr;
        const auto scene=owning_scene_window(viewport);
        if(!scene)return nullptr;
        const auto owner=*reinterpret_cast<uintptr_t*>(scene+0x508);
        if(!owner||*reinterpret_cast<uintptr_t*>(owner)!=base+0xB4CF6E0)return nullptr;
        const auto hwnd=*reinterpret_cast<HWND*>(owner+0x28);
        DWORD process=0;
        if(!IsWindow(hwnd)||!GetWindowThreadProcessId(hwnd,&process)||process!=GetCurrentProcessId())return nullptr;
        native=owner;return hwnd;
    } __except(EXCEPTION_EXECUTE_HANDLER){return nullptr;}
}
void sync_window_cached_origin(void* native,int expected_width,int expected_height) {
    if(correcting_span_cache)return;
    const auto window=owning_scene_window(live_engine_viewport());
    if(!window||*reinterpret_cast<uintptr_t*>(window+0x508)!=reinterpret_cast<uintptr_t>(native))return;
    const auto actual=ac8display::physical_client_metrics(game_window);
    if(!actual.valid||actual.width!=expected_width||actual.height!=expected_height)return;
    const float desired[2]={float(actual.x),float(actual.y)};
    const auto cached=reinterpret_cast<float*>(window+0x378);
    if(cached[0]==desired[0]&&cached[1]==desired[1])return;
    uint64_t packed=0;memcpy(&packed,desired,sizeof(packed));
    const auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
    auto setter=reinterpret_cast<CachedWindowPosition>(base+0x1C66FE0);
    correcting_span_cache=true;
    setter(reinterpret_cast<void*>(window),packed);
    correcting_span_cache=false;
    log_line("DISPLAY engine cached origin synchronized: (%d,%d)",actual.x,actual.y);
}
void __fastcall reshape_engine_span(void* window,int32_t x,int32_t y,int32_t width,int32_t height) {
    const bool apply=engine_span_scope&&current_engine_window(window);
    if(apply) {
        x=scoped_engine_span.rectangle.left;y=scoped_engine_span.rectangle.top;
        width=scoped_engine_span.width;height=scoped_engine_span.height;
        engine_span_last_window.store(reinterpret_cast<uintptr_t>(window));
        engine_span_slate_calls.fetch_add(1);
    }
    // This original function owns HWND, requested-size and virtual-size caches.
    // SWindow::SetCachedSize next calls native AdjustCachedSize (vtable +0xF0),
    // which returns actual client/requested dimensions, not the clamped input.
    // Original ResizeFrame subsequently updates the backbuffer and viewport.
    original_window_reshape(window,x,y,width,height);
    // SWindow records the caller's position before this virtual call. A no-op
    // native move emits no WM_MOVE, so reconcile with the original cache API.
    // Its remaining caller code updates cached size only.
    if(apply)sync_window_cached_origin(window,scoped_engine_span.width,scoped_engine_span.height);
}
void __fastcall resize_game_frame(void* viewport,uint32_t width,uint32_t height,int mode) {
    ac8display::WindowPlan plan;
    {std::lock_guard<std::mutex> lock(engine_span_mutex);plan=engine_span_plan;}
    const bool apply=running.load()&&plan.valid&&plan.span&&width&&height&&current_engine_viewport(viewport);
    const bool old_scope=engine_span_scope;
    const auto old_plan=scoped_engine_span;
    if(apply) {
        engine_span_scope=true;scoped_engine_span=plan;
        const auto count=engine_span_resize_calls.fetch_add(1)+1;
        if(count<=12)log_line("DISPLAY engine ResizeFrame: source=%ux%u mode=%d target=%dx%d mode=2 origin=(%ld,%ld) thread=%lu",width,height,mode,plan.width,plan.height,plan.rectangle.left,plan.rectangle.top,GetCurrentThreadId());
        width=plan.width;height=plan.height;mode=2;
    }
    original_engine_resize(viewport,width,height,mode);
    engine_span_scope=old_scope;scoped_engine_span=old_plan;
}
bool install_engine_span() {
    const auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
    const auto dos=reinterpret_cast<IMAGE_DOS_HEADER*>(base);
    const auto nt=reinterpret_cast<IMAGE_NT_HEADERS64*>(base+dos->e_lfanew);
    const unsigned char frame[]={0x40,0x55,0x56,0x57,0x41,0x54,0x41,0x56,0x41,0x57,0x48,0x8D,0xAC,0x24,0xB8,0xFD,0xFF,0xFF};
    const unsigned char position[]={0x48,0x89,0x5C,0x24,0x08,0x48,0x89,0x74,0x24,0x18,0x48,0x89,0x54,0x24,0x10,0x57,0x48,0x83,0xEC,0x30};
    auto slot=reinterpret_cast<void**>(base+0xBE7DDC8+8);
    auto window_slot=reinterpret_cast<void**>(base+0xB4CF6E0+8);
    auto adjust_slot=reinterpret_cast<void**>(base+0xB4CF6E0+0xF0);
    auto move_slot=reinterpret_cast<void**>(base+0xB4CF6E0+0x18);
    if(nt->FileHeader.TimeDateStamp!=0x6AA0E27D||nt->OptionalHeader.SizeOfImage!=0x2195A000||
       *slot!=reinterpret_cast<void*>(base+0x4AC0E70)||
       *window_slot!=reinterpret_cast<void*>(base+0x1B44820)||
       *adjust_slot!=reinterpret_cast<void*>(base+0x1B45170)||
       *move_slot!=reinterpret_cast<void*>(base+0x1B44B10)||
       memcmp(reinterpret_cast<void*>(base+0x4AC0E70),frame,sizeof(frame))||
       memcmp(reinterpret_cast<void*>(base+0x1C66FE0),position,sizeof(position))) {
        log_line("DISPLAY engine integration refused: executable/function/vtable signature mismatch");return false;
    }
    DWORD window_protection=0,frame_protection=0;
    if(!VirtualProtect(window_slot,sizeof(void*),PAGE_READWRITE,&window_protection))return false;
    if(!VirtualProtect(slot,sizeof(void*),PAGE_READWRITE,&frame_protection)) {
        DWORD ignored=0;VirtualProtect(window_slot,sizeof(void*),window_protection,&ignored);return false;
    }
    original_engine_resize=reinterpret_cast<EngineResizeFrame>(*slot);
    original_window_reshape=reinterpret_cast<NativeWindowReshape>(*window_slot);
    InterlockedExchangePointer(window_slot,reinterpret_cast<void*>(&reshape_engine_span));
    InterlockedExchangePointer(slot,reinterpret_cast<void*>(&resize_game_frame));
    DWORD ignored=0;VirtualProtect(slot,sizeof(void*),frame_protection,&ignored);
    VirtualProtect(window_slot,sizeof(void*),window_protection,&ignored);
    log_line("DISPLAY engine integration registered: two guarded vtable slots; live GameViewport ResizeFrame and native reshape; original AdjustCachedSize/RHI/backbuffer; no HWND resize loop");
    return true;
}
bool restore_engine_span(uint64_t serial,int width,int height,int mode) {
    ac8display::WindowPlan plan;
    {std::lock_guard<std::mutex> lock(engine_span_mutex);plan=engine_span_plan;}
    if(!engine_span_installed||!plan.valid||plan.serial!=serial)return false;
    const auto viewport=live_engine_viewport();
    uintptr_t native=0;
    const auto window=guarded_engine_window(viewport,native);
    if(!window||window!=game_window||!current_engine_window(reinterpret_cast<void*>(native)))return false;
    engine_span_last_window.store(native);
    if(engine_span_acknowledged==serial)return true;
    if(plan.span) {
        int render_width=0,render_height=0;
        const auto actual=ac8display::physical_client_metrics(window);
        if(!actual.valid||IsIconic(window)||!read_display_viewport_dimensions(render_width,render_height))return false;
        if(actual.width!=plan.width||actual.height!=plan.height||
           actual.x!=plan.rectangle.left||actual.y!=plan.rectangle.top||
           render_width!=plan.width||render_height!=plan.height) {
            // ApplyResolutionSettings may skip its cached same-value request
            // after a menu reset. Execute the guarded original engine path
            // once for this serial, retaining the existing reshape scope.
            log_line("DISPLAY engine span recovery apply: serial=%llu client=%dx%d render=%dx%d target=%dx%d",serial,actual.width,actual.height,render_width,render_height,plan.width,plan.height);
            resize_game_frame(reinterpret_cast<void*>(viewport),plan.width,plan.height,2);
        }
        engine_span_acknowledged=serial;engine_span_recovery.issued(GetTickCount64());
        return true;
    }
    if(!viewport||!current_engine_window(reinterpret_cast<void*>(native)))return false;
    // Move through the original window API before borderless/exclusive mode
    // chooses its monitor. A 3-monitor window must not restore to the left one.
    const auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
    auto move=reinterpret_cast<NativeWindowMove>(base+0x1B44B10);
    log_line("DISPLAY engine restore requested: resolution=%dx%d mode=%d thread=%lu",width,height,mode,GetCurrentThreadId());
    const auto current=ac8display::physical_client_metrics(game_window);
    if(!current.valid)return false;
    // MonitorFromWindow chooses intersecting area; a wide window can tie.
    // Center it over the original monitor first, then restore its known
    // origin after resizing. Final placement does not depend on that tie.
    const int center_x=engine_span_original.x+engine_span_original.width/2;
    const int center_y=engine_span_original.y+engine_span_original.height/2;
    move(reinterpret_cast<void*>(native),center_x-current.width/2,center_y-current.height/2);
    // UGS may skip a same-value request after a game-menu reset. Explicitly
    // execute its original resize path once for this manual off transition.
    original_engine_resize(reinterpret_cast<void*>(viewport),width,height,mode);
    move(reinterpret_cast<void*>(native),engine_span_original.x,engine_span_original.y);
    const auto restored=ac8display::physical_client_metrics(game_window);
    if(restored.valid)sync_window_cached_origin(reinterpret_cast<void*>(native),restored.width,restored.height);
    log_line("DISPLAY engine restore: resolution=%dx%d mode=%d originalOrigin=(%d,%d)",width,height,mode,engine_span_original.x,engine_span_original.y);
    engine_span_acknowledged=serial;
    return true;
}
ac8display::WindowPlan poll_engine_span(HWND window,bool requested) {
    if(requested&&!engine_span_installed&&!engine_span_failed) {
        engine_span_installed=install_engine_span();engine_span_failed=!engine_span_installed;
    }
    requested=requested&&engine_span_installed;
    int render_width=0,render_height=0;
    uintptr_t viewport=0,native=0;
    if(engine_span_installed) {
        viewport=live_engine_viewport();
        const auto owner=guarded_engine_window(viewport,native);
        if(owner) {
            // During recreation a still-valid old HWND can remain cached by
            // input/overlay discovery. The guarded live viewport owns this one.
            if(owner!=game_window)log_line("DISPLAY live viewport window rebound: viewport=%p native=%p",reinterpret_cast<void*>(viewport),reinterpret_cast<void*>(native));
            game_window=window=owner;engine_span_last_window.store(native);
        }
        read_display_viewport_dimensions(render_width,render_height);
    }
    if(requested!=engine_span_desired) {
        if(requested) {
            const auto geometry=ac8display::physical_span_geometry();
            if(!geometry.valid){log_line("DISPLAY span refused: %s",geometry.reason);return {};}
            engine_span_original=ac8display::physical_client_metrics(window);
            if(!engine_span_original.valid||engine_span_original.width<640||engine_span_original.height<360||IsIconic(window))return {};
            ac8display::WindowPlan next{++engine_span_sequence,geometry.width,geometry.height,true,true,geometry.bounds};
            {std::lock_guard<std::mutex> lock(engine_span_mutex);engine_span_plan=next;}
        } else {
            ac8display::WindowPlan next{++engine_span_sequence,engine_span_original.width,engine_span_original.height,false,true,{}};
            {std::lock_guard<std::mutex> lock(engine_span_mutex);engine_span_plan=next;}
        }
        engine_span_desired=requested;
        engine_span_recovery.reset();
        if(requested)engine_span_recovery.issued(GetTickCount64());
    }
    ac8display::WindowPlan result;
    {std::lock_guard<std::mutex> lock(engine_span_mutex);result=engine_span_plan;}
    const auto actual=ac8display::physical_client_metrics(window);
    const bool was_exhausted=engine_span_recovery.exhausted();
    if(requested&&engine_span_recovery.observe(result,actual,render_width,render_height,
        reinterpret_cast<uintptr_t>(window),viewport,native,IsIconic(window)!=0,GetTickCount64())) {
        result.serial=++engine_span_sequence;
        {std::lock_guard<std::mutex> lock(engine_span_mutex);engine_span_plan=result;}
        log_line("DISPLAY settled span reset: serial=%llu recovery=%u client=%dx%d origin=(%d,%d) render=%dx%d target=%dx%d",result.serial,engine_span_recovery.count(),actual.width,actual.height,actual.x,actual.y,render_width,render_height,result.width,result.height);
    }
    if(!was_exhausted&&engine_span_recovery.exhausted())log_line("DISPLAY span recovery stopped: bounded command budget exhausted; disable/re-enable or retain verified span for one minute");
    static int old_width=0,old_height=0,old_x=0,old_y=0;
    if(actual.valid&&(actual.width!=old_width||actual.height!=old_height||actual.x!=old_x||actual.y!=old_y)) {
        old_width=actual.width;old_height=actual.height;old_x=actual.x;old_y=actual.y;
        log_line("DISPLAY engine observation: client=%dx%d origin=(%d,%d) reshapeCalls=%u frameCalls=%u",actual.width,actual.height,actual.x,actual.y,engine_span_slate_calls.load(),engine_span_resize_calls.load());
    }
    return result;
}
