// Real Windows ABI and unwind execution of production-generated admission code.
// Native admission bytes/settings are fixture memory; no game process is used.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define MH_CreateHook test_CreateHook
#define MH_EnableHook test_EnableHook
#define MH_RemoveHook test_RemoveHook
#include "../runtime/src/native_psm_admission.h"
#undef MH_CreateHook
#undef MH_EnableHook
#undef MH_RemoveHook
#include "native_psm_abi_fixture.h"
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <set>
#include <algorithm>
#include <cmath>
extern "C" MH_STATUS WINAPI MH_CreateHook(LPVOID,LPVOID,LPVOID*);
extern "C" MH_STATUS WINAPI MH_EnableHook(LPVOID);
extern "C" MH_STATUS WINAPI MH_RemoveHook(LPVOID);
static bool force_absolute=false;
static void* last_selector=nullptr;
extern "C" MH_STATUS WINAPI test_CreateHook(LPVOID a,LPVOID b,LPVOID* c){last_selector=b;return force_absolute?MH_ERROR_MEMORY_ALLOC:MH_CreateHook(a,b,c);}
extern "C" MH_STATUS WINAPI test_EnableHook(LPVOID a){return MH_EnableHook(a);}
extern "C" MH_STATUS WINAPI test_RemoveHook(LPVOID a){return MH_RemoveHook(a);}
struct Capture {std::uint64_t gp[7]{},flags{};unsigned char xmm[6][16]{};std::uintptr_t fifth=0;};
static_assert(offsetof(Capture,xmm)==0x40&&offsetof(Capture,fifth)==0xa0);
extern "C" void invoke_psm(void*,const Capture*,Capture*);
extern "C" void clobber_helper();
extern "C" void tail_probe();
extern "C" unsigned char invoke_start,invoke_return,invoke_end;
extern "C" std::uintptr_t invoke_caller_rsp=0;
extern "C" std::uintptr_t expected_nonvolatile[4]{};
extern "C" bool abi_step_mode=false;
static unsigned checks=0,helper_calls=0,helper_unwinds=0;
static bool block_choice=false,step_mode=false;
static unsigned char* current_block=nullptr;
static unsigned current_selector_size=0;
static unsigned char* installed_native_entry=nullptr;
static Capture expected_entry;
static std::set<unsigned> stepped[7];
static void require(bool ok,const char* name){++checks;if(!ok){std::fprintf(stderr,"FAIL %s\n",name);std::exit(1);}}
static void require_context(CONTEXT c,const char* name){
    require(c.Rip==reinterpret_cast<DWORD64>(&invoke_return)&&c.Rsp==invoke_caller_rsp,name);
    require(c.Rbx==expected_nonvolatile[0]&&c.Rsi==expected_nonvolatile[1]&&c.Rdi==expected_nonvolatile[2]&&c.Rbp==expected_nonvolatile[3],"unwind restores native nonvolatile GP registers");
}
static bool unwind_one(CONTEXT& c){
    DWORD64 image=0;auto* fn=RtlLookupFunctionEntry(c.Rip,&image,nullptr);if(!fn)return false;
    PVOID handler=nullptr;DWORD64 establisher=0;
    RtlVirtualUnwind(UNW_FLAG_NHANDLER,image,c.Rip,fn,&c,&handler,&establisher,nullptr);return true;
}
extern "C" bool observe_saved_frame(const player_admission::SavedFrame* frame){
    ++helper_calls;
    const std::uint64_t gp[]={frame->rax,frame->rcx,frame->rdx,frame->r8,frame->r9,frame->r10,frame->r11};
    require(memcmp(gp,expected_entry.gp,sizeof(gp))==0,"helper sees exact entry volatile GP registers");
    require(memcmp(frame->xmm,expected_entry.xmm,sizeof(frame->xmm))==0,"helper sees all 128 bits of entry XMM0..5");
    require(((frame->flags^expected_entry.flags)&0xcd5)==0,"helper sees native entry arithmetic flags");
    if(step_mode){
        CONTEXT c{};RtlCaptureContext(&c);
        require(unwind_one(c),"compiled helper observer has unwind metadata");
        require(unwind_one(c),"intentionally clobbering assembly helper has unwind metadata");
        require(c.Rip>=reinterpret_cast<DWORD64>(current_block+0x600)&&c.Rip<reinterpret_cast<DWORD64>(current_block+0x600+current_selector_size),"helper unwinds into production selector");
        require(unwind_one(c),"production selector has helper-call unwind metadata");
        require_context(c,"helper/selector unwind reaches original caller");++helper_unwinds;
    }
    return block_choice;
}
static LONG CALLBACK step_handler(EXCEPTION_POINTERS* exception){
    if(exception->ExceptionRecord->ExceptionCode!=EXCEPTION_SINGLE_STEP)return EXCEPTION_CONTINUE_SEARCH;
    auto& live=*exception->ContextRecord;const auto ip=live.Rip;
    if(ip==reinterpret_cast<DWORD64>(&invoke_return)){live.EFlags&=~0x100u;return EXCEPTION_CONTINUE_EXECUTION;}
    if(ip==reinterpret_cast<DWORD64>(installed_native_entry)){live.EFlags|=0x100u;return EXCEPTION_CONTINUE_EXECUTION;}
    const auto base=reinterpret_cast<DWORD64>(current_block);
    if(current_block&&ip>=base&&ip<base+0x600+current_selector_size){
        const unsigned offset=unsigned(ip-base);unsigned index=6;
        if(offset<0x22b)index=offset<0x58?0:offset<0x21f?1:2;
        else if(offset>=0x300&&offset<0x52b){const unsigned rel=offset-0x300;index=rel<0x58?3:rel<0x21f?4:5;}
        else if(offset<0x600)return EXCEPTION_CONTINUE_EXECUTION;
        stepped[index].insert(offset);
        auto c=live;
        require(unwind_one(c),"executed dynamic instruction boundary has registered function entry");
        require_context(c,"executed clone/selector boundary unwinds to original caller");
        live.EFlags|=0x100u;
        return EXCEPTION_CONTINUE_EXECUTION;
    }
    if(ip>=reinterpret_cast<DWORD64>(&invoke_start)&&ip<reinterpret_cast<DWORD64>(&invoke_return)){live.EFlags|=0x100u;return EXCEPTION_CONTINUE_EXECUTION;}
    if(ip>=reinterpret_cast<DWORD64>(&clobber_helper)&&ip<reinterpret_cast<DWORD64>(&clobber_helper)+0x100&&abi_step_mode){live.EFlags|=0x100u;return EXCEPTION_CONTINUE_EXECUTION;}
    // The real helper receives a separate live unwind check; restore TF from
    // its entry frame when returning to the production selector.
    live.EFlags&=~0x100u;return EXCEPTION_CONTINUE_EXECUTION;
}
struct NativeMemory {
    alignas(16) std::array<unsigned char,0x4000> owner{};
    alignas(16) std::array<unsigned char,0x100> context{};
    void seed(bool generic=false,bool early=false){
        owner.fill(0);context.fill(0);
        auto put=[&](unsigned offset,float v){memcpy(owner.data()+offset,&v,4);};
        const auto address=reinterpret_cast<std::uintptr_t>(owner.data());
        const std::uintptr_t pointers[]={address,address+0x38,address+0x9c0};memcpy(context.data(),pointers,sizeof(pointers));
        context[0x1a]=1;const float dt=1.f/60;memcpy(context.data()+0x20,&dt,4);
        put(0,.7f);put(0xc,1);put(0x10,1);put(0x14,0);
        put(0x98+0x18,100);put(0x108+0x14,.1f);put(0x108+0x18,.1f);put(0x108+0x38,0);
        put(0x9c0+0x384,0);put(0x9c0+0x380,generic?.0f:.4f);put(0x9c0+0x3d0,200);
        owner[0x9c0+0x3cc]=1;
        if(generic){put(0x14,1);put(0x108+8,.5f);}
        if(early){const std::uint32_t flags=1u<<6;memcpy(owner.data()+0x8b0,&flags,4);}
        for(unsigned i=0;i<24;++i)owner[0x98+0x160+i]=static_cast<unsigned char>(0x30+i);
    }
    Capture entry(bool step=false){
        Capture c;for(unsigned i=0;i<7;++i)c.gp[i]=0x1234000056780000ull+i*0x1111;
        const auto a=reinterpret_cast<std::uintptr_t>(owner.data());
        c.gp[1]=a+0x108;c.gp[2]=a;c.gp[3]=reinterpret_cast<std::uintptr_t>(context.data());c.gp[4]=a+0x98;c.fifth=a+0x8b0;
        c.flags=0x247|(step?0x100:0);
        for(unsigned i=0;i<6;++i)for(unsigned j=0;j<16;++j)c.xmm[i][j]=static_cast<unsigned char>(7+i*29+j);
        return c;
    }
};
static void invoke(void* target,Capture entry,Capture& out,bool step=false){expected_entry=entry;step_mode=abi_step_mode=step;invoke_psm(target,&entry,&out);step_mode=abi_step_mode=false;}
static std::array<std::array<unsigned char,20>,3> unwind_info(){
    std::array<std::array<unsigned char,20>,3> a{};for(unsigned i=0;i<3;++i)memcpy(a[i].data(),native_unwind[i],player_admission::unwind_sizes[i]);return a;
}
static unsigned char* make_block(){
    auto* b=static_cast<unsigned char*>(VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE));require(b!=nullptr,"allocate independent test code");
    player_admission::Constants c{};memcpy(c.data(),native_constants,sizeof(c));
    player_admission::build_clone(b,native_code,c,false);player_admission::build_clone(b+0x300,native_code,c,true);
    current_selector_size=player_admission::build_selector(b+0x600,reinterpret_cast<std::uintptr_t>(&clobber_helper),reinterpret_cast<std::uintptr_t>(b),reinterpret_cast<std::uintptr_t>(b+0x300));
    require(player_admission::register_unwind(b,current_selector_size,unwind_info()),"register all seven production function entries");FlushInstructionCache(GetCurrentProcess(),b,4096);current_block=b;return b;
}
static void check_entries(unsigned char* b){
    for(unsigned copy=0;copy<2;++copy)for(unsigned f=0;f<3;++f){DWORD64 image=0;auto* fn=RtlLookupFunctionEntry(reinterpret_cast<DWORD64>(b+copy*0x300+player_admission::starts[f]),&image,nullptr);
        require(fn&&image==reinterpret_cast<DWORD64>(b)&&fn->BeginAddress==copy*0x300+player_admission::starts[f]&&fn->EndAddress==copy*0x300+player_admission::ends[f],"each native fragment has exact registered boundaries");
        const auto* u=b+fn->UnwindData;require(memcmp(u,native_unwind[f],f?4:16)==0,"native unwind header/codes preserved");
        if(f){const auto* parent=reinterpret_cast<const RUNTIME_FUNCTION*>(u+4+((u[2]+1)&~1u)*2);require(parent->BeginAddress==copy*0x300&&parent->EndAddress==copy*0x300+0x58&&parent->UnwindData==0x900+copy*0x60,"CHAININFO points to matching clone first fragment");}
    }
    DWORD64 image=0;auto* fn=RtlLookupFunctionEntry(reinterpret_cast<DWORD64>(b+0x600),&image,nullptr);require(fn&&fn->BeginAddress==0x600&&fn->EndAddress==0x600+current_selector_size,"selector has exact registered boundaries");
}
static void test_transparency(unsigned char* b){
    const unsigned size=player_admission::build_selector(b+0xc00,reinterpret_cast<std::uintptr_t>(&clobber_helper),reinterpret_cast<std::uintptr_t>(&tail_probe),reinterpret_cast<std::uintptr_t>(&tail_probe));
    FlushInstructionCache(GetCurrentProcess(),b+0xc00,size);
    Capture in;for(unsigned i=0;i<7;++i)in.gp[i]=0xa123456780000000ull+i*0x1234567;
    for(unsigned i=0;i<6;++i)for(unsigned j=0;j<16;++j)in.xmm[i][j]=static_cast<unsigned char>(i*27+j);
    for(bool choice:{false,true})for(std::uint64_t flags:{0x202ull,0x203ull,0x246ull,0xA92ull}){
        block_choice=choice;in.flags=flags;Capture out;invoke(b+0xc00,in,out);
        require(memcmp(in.gp,out.gp,sizeof(in.gp))==0,"selector restores every volatile GP including caller-live RCX");
        require(memcmp(in.xmm,out.xmm,sizeof(in.xmm))==0,"selector restores every bit XMM0..5 including caller-live XMM5");
        require(((in.flags^out.flags)&0xcd5)==0,"selector tail jump preserves all native entry arithmetic flags");
    }
}
static void test_native(unsigned char* b){
    NativeMemory m;
    for(bool choice:{false,true})for(bool generic:{false,true})for(bool early:{false,true}){
        block_choice=choice;Capture ref,out;const auto baseline=choice?b+0x300:b;
        m.seed(generic,early);auto saved=m;invoke(baseline,m.entry(),ref);auto expected=m;
        m=saved;invoke(b+0x600,m.entry(),out);
        require(memcmp(m.owner.data(),expected.owner.data(),m.owner.size())==0,"selector preserves exact chosen native memory side effects");
        require(memcmp(ref.gp,out.gp,sizeof(ref.gp))==0,"selector preserves chosen native volatile GP return effects");
        require(memcmp(ref.xmm,out.xmm,sizeof(ref.xmm))==0,"selector preserves chosen native XMM return effects");
        require(((ref.flags^out.flags)&0xcd5)==0,"selector preserves chosen native return flags");
        m.seed(generic,early);invoke(b+0x600,m.entry(true),out,true);
    }
    std::printf("Windows instruction boundary counts:");for(unsigned i=0;i<7;++i)std::printf(" %zu",stepped[i].size());std::printf("; helper unwinds %u\n",helper_unwinds);
    for(unsigned i=0;i<7;++i)require(!stepped[i].empty(),"Windows unwind exercised every clone fragment and selector");
    require(stepped[6].size()>25&&helper_unwinds==8,"Windows unwind covers selector prologue/body/epilogues and real helper boundary");
}
static void test_origin(){
    player_admission::Origin o;constexpr std::uintptr_t a=0x123400;
    o.publish(a,3,4,.7f,true);for(unsigned substep=0;substep<20;++substep)require(o.matches(a,a+0x98,a+0x108,3,4,.7f),"automatic origin persists through repeated native substeps");
    require(!o.matches(a,a+0x98,a+0x108,4,4,.7f)&&!o.matches(a,a+0x98,a+0x108,3,5,.7f),"fresh mapping and lifecycle epoch reject retained origin");
    require(!o.matches(a+1,a+0x98,a+0x108,3,4,.7f)&&!o.matches(a,a+0x99,a+0x108,3,4,.7f)&&!o.matches(a,a+0x98,a+0x109,3,4,.7f),"different owner/dynamics/drift reject retained origin");
    require(!o.matches(a,a+0x98,a+0x108,3,4,std::nextafter(.7f,1.f)),"same-looking changed pitch bits reject retained origin");
    o.publish(a,3,4,.7f,false);require(!o.matches(a,a+0x98,a+0x108,3,4,.7f),"physical/native packet clears automatic origin");o.clear();require(!o.automatic,"lifecycle clear resets automatic origin");
}
static void commit_page(unsigned char* image,unsigned rva,unsigned length){
    const unsigned start=rva&~0xfffu,size=(rva+length-start+0xfff)&~0xfffu;
    require(VirtualAlloc(image+start,size,MEM_COMMIT,PAGE_EXECUTE_READWRITE)!=nullptr,"commit native-layout fixture page");
}
static void test_install(bool absolute){
    // Reserve the original PE address layout, but commit only read-only native
    // instruction/constant/unwind fixture pages. No executable is loaded.
    auto* image=static_cast<unsigned char*>(VirtualAlloc(nullptr,0xd70d000,MEM_RESERVE,PAGE_NOACCESS));require(image!=nullptr,"reserve native-layout fixture image");
    constexpr unsigned target_rva=0x4d3f3a0;commit_page(image,target_rva,0x22b);memcpy(image+target_rva,native_code,sizeof(native_code));
    for(unsigned i=0;i<6;++i){commit_page(image,native_literal_rvas[i],16);memcpy(image+native_literal_rvas[i],native_constants+i,4);}
    for(unsigned i=0;i<3;++i){commit_page(image,native_pdata[i][2],20);memcpy(image+native_pdata[i][2],native_unwind[i],player_admission::unwind_sizes[i]);}
    commit_page(image,0x1000,sizeof(RUNTIME_FUNCTION)*3);auto* table=reinterpret_cast<RUNTIME_FUNCTION*>(image+0x1000);
    for(unsigned i=0;i<3;++i)table[i]={native_pdata[i][0],native_pdata[i][1],native_pdata[i][2]};
    require(RtlAddFunctionTable(table,3,reinterpret_cast<DWORD64>(image))!=FALSE,"register real native-layout fragment metadata");
    std::array<std::array<unsigned char,20>,3> read{};
    require(player_admission::read_native_unwind(image+target_rva,read)&&read==unwind_info(),"production native metadata reader validates all three original chained fragments");
    bool installed=false;force_absolute=absolute;
    require(player_admission::install(image+target_rva,reinterpret_cast<void*>(&clobber_helper),installed)&&installed,absolute?"install actual absolute fallback admission hook":"install actual MinHook admission hook");
    current_block=static_cast<unsigned char*>(last_selector)-0x600;installed_native_entry=image+target_rva;
    // Both installations use this same generated selector size.
    check_entries(current_block);
    require(player_admission::install(image+target_rva,reinterpret_cast<void*>(&clobber_helper),installed),"installed hook remains idempotent after target bytes change");
    NativeMemory m;
    for(bool choice:{false,true})for(bool generic:{false,true}){
        block_choice=choice;Capture direct,hooked;m.seed(generic,false);auto saved=m;
        invoke(current_block+(choice?0x300:0),m.entry(),direct);auto expected=m;m=saved;
        invoke(image+target_rva,m.entry(),hooked);
        require(memcmp(expected.owner.data(),m.owner.data(),m.owner.size())==0,"installed hook preserves chosen complete native memory effects");
        require(memcmp(direct.gp,hooked.gp,sizeof(direct.gp))==0&&memcmp(direct.xmm,hooked.xmm,sizeof(direct.xmm))==0&&((direct.flags^hooked.flags)&0xcd5)==0,"installed hook preserves complete chosen native GP/XMM/flags return effects");
    }
    auto* veh=AddVectoredExceptionHandler(1,step_handler);m.seed();Capture out;block_choice=absolute;
    invoke(image+target_rva,m.entry(true),out,true);RemoveVectoredExceptionHandler(veh);
    std::printf("PASS actual %s install, three native-layout unwind fragments, chosen clone ABI/side effects and Windows helper/selector unwind.\n",absolute?"absolute fallback":"MinHook");
    installed_native_entry=nullptr;
    // Installed code remains reachable until process exit, matching production.
}
int main(){
    require(player_admission::hash(native_code,sizeof(native_code))==player_admission::native_hash,"native fixture matches production full-function fingerprint");
    auto* b=make_block();check_entries(b);test_transparency(b);
    auto* veh=AddVectoredExceptionHandler(1,step_handler);require(veh!=nullptr,"register real Windows single-step validation");test_native(b);RemoveVectoredExceptionHandler(veh);test_origin();
    require(MH_Initialize()==MH_OK,"initialize actual bundled MinHook");test_install(false);test_install(true);
    std::printf("PASS native PSM ABI/unwind: %u checks; helper calls=%u live helper unwinds=%u; instruction boundaries=",checks,helper_calls,helper_unwinds);for(unsigned i=0;i<7;++i)std::printf("%s%zu",i?"/":"",stepped[i].size());std::printf(". Exact native fixture code, synthetic memory only; no live flight claim.\n");
    RtlDeleteFunctionTable(reinterpret_cast<RUNTIME_FUNCTION*>(b+0xb00));VirtualFree(b,0,MEM_RELEASE);
}
