#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace player_maneuver {
// 4D3FF84 passes dynamics+70 to 4D3EFA0. Its mode/phase are +1D/+1E;
// 4D3F55B enters mode 2 for every supported PostStall maneuver. The native
// 4D3F54F..559 throttle/brake threshold is exactly the float at D2A912C.
inline constexpr float request_threshold=0.8999999761581421f;
inline bool can_prepare_edge(std::uint8_t mode,std::uint32_t flags,std::uint8_t capability,
                             float speed,float generic_minimum,float maneuver_maximum) {
    // Verified native gates that can bypass the history store at 4D3F56A.
    // COMISS minimum,speed/JBE permits unordered values at the generic gate.
    return mode==0&&capability!=0&&!(flags&((3u<<18)|(1u<<6)))&&
        !((flags&(1u<<5))&&generic_minimum>speed)&&
        std::isfinite(speed)&&std::isfinite(maneuver_maximum)&&speed<=maneuver_maximum;
}
struct Snapshot {
    bool sampled=false;
    std::uint8_t mode=0,phase=0;
    // Caller filters aggregate game rotations with ManualRotation before
    // sampling. raw_pitch is claimed keyboard input, not a device classifier.
    float previous_pitch=0,throttle=0,brake=0,raw_pitch=0;
    bool prepare_edge_allowed=false;
    std::uint64_t native_mapping=0;
    // Read-only native gate observations for bounded admission diagnostics.
    float speed=0,generic_minimum=0,maneuver_maximum=0,brake_grace=0;
    std::uint8_t capability=0;
    float generic_elapsed=0,generic_duration=0;
    bool generic_latched=false;
    // Read-only dispatcher observations distinguish the native special
    // branch used by the original release from generic mode1/high-G.
    float dispatch_state=0,dispatch_scale=1;
    std::uint8_t dispatch_alternate_state=0;
    bool valid() const {
        return sampled&&mode<=2&&phase<=3&&std::isfinite(previous_pitch)&&
            std::isfinite(throttle)&&std::isfinite(brake)&&std::isfinite(raw_pitch);
    }
    bool requested() const {return valid()&&throttle>request_threshold&&brake>request_threshold;}
    const char* admission_reason(std::uint32_t flags) const {
        if(!valid())return "sample-unavailable";
        if(mode!=0)return "native-mode-active";
        if(!capability)return "capability-off";
        if(flags&((3u<<18)|(1u<<6)))return "native-flags";
        if((flags&(1u<<5))&&generic_minimum>speed)return "generic-speed";
        if(!std::isfinite(speed)||!std::isfinite(maneuver_maximum))return "speed-invalid";
        if(speed>maneuver_maximum)return "above-psm-speed";
        if(!(flags&(1u<<8))&&!(brake_grace>0))return "grace-closed";
        if(!requested())return "combo-below-threshold";
        if(previous_pitch>0)return "pitch-history-positive";
        if(raw_pitch<=0)return "pull-not-positive";
        return "native-edge-ready";
    }
};
struct Control {
    bool active=false,native_active=false,new_keyboard=false,new_native_pitch=false;
    bool entered=false,exited=false,released=false,write_pitch=false,neutral_edge=false;
    float pitch_raw=0;

    bool owns_rotation() const {return native_active;}

    void reset() {*this=Control{};}
    void observe(const Snapshot& s,std::uint64_t motion,float automatic_pitch,
                 bool keyboard_pitch,float up_pitch=1.f) {
        const bool was_active=active,was_native=native_active;
        const bool moved=have_motion_&&motion!=previous_motion_;
        const bool new_key=keyboard_pitch&&!previous_keyboard_;
        new_keyboard=new_key;
        const bool had_native=have_native_;
        const bool fresh_native=s.native_mapping&&s.native_mapping!=previous_mapping_;
        new_native_pitch=fresh_native&&have_native_&&s.raw_pitch>0&&previous_native_pitch_<=0;
        if(fresh_native) {
            previous_mapping_=s.native_mapping;previous_native_pitch_=s.raw_pitch;have_native_=true;
        }
        previous_motion_=motion;have_motion_=true;
        previous_keyboard_=keyboard_pitch;
        entered=exited=released=write_pitch=neutral_edge=false;
        pitch_raw=s.raw_pitch;
        // RawOwnership removes prior mod writes and ManualRotation excludes
        // unclaimed base-game mouse axes before this snapshot. Only
        // actual native mode 2 identifies PSM; mode 1 is generic high-G drift.
        // Throttle/brake and nonzero pitch cannot suppress mouse pursuit.
        native_active=s.sampled?s.mode==2:was_native;
        active=native_active;
        entered=active&&!was_active;exited=was_active&&!active;released=exited;
        if(!s.valid()) {edge_wait_=false;return;}
        if(!native_active) {
            mouse_valid_=false;mouse_pitch_=0;
            // An automatic positive pitch can pollute native rising-edge
            // history. A NEW claimed keyboard positive press on the verified eligible
            // path may prepare zero; native physics must observe that zero
            // before we return the held native pitch. Automatic mouse input
            // and continuing holds cannot synthesize admission edges. The
            // mapper sequence proves a fresh packet, not its input device.
            // A new keyboard press can follow an already-positive claimed
            // packet. Require a fresh mapped positive packet, rather than
            // losing that genuine press merely because its sign did not cross.
            const bool new_positive_keyboard=had_native&&fresh_native&&new_key&&s.raw_pitch>0;
            if((new_native_pitch||new_positive_keyboard)&&s.requested()&&s.previous_pitch>0&&s.prepare_edge_allowed)
                edge_wait_=true;
            if(!s.requested()||!s.prepare_edge_allowed||s.raw_pitch<=0||s.previous_pitch<=0)
                edge_wait_=false;
            neutral_edge=edge_wait_;
            write_pitch=neutral_edge;pitch_raw=neutral_edge?0:s.raw_pitch;
            return;
        }
        edge_wait_=false;
        if(keyboard_pitch||s.raw_pitch!=0) {
            // Claimed keyboard input and its release take priority.
            // An old mouse pull must not reappear on native key release.
            mouse_valid_=false;mouse_pitch_=0;
        } else {
            if(!was_native&&std::isfinite(automatic_pitch)) {
                mouse_pitch_=std::clamp(automatic_pitch,-1.f,1.f);mouse_valid_=true;
            }
            if(moved) {
                if((motion&3u)==1&&std::isfinite(up_pitch)) {
                    mouse_pitch_=std::clamp(up_pitch,-1.f,1.f);mouse_valid_=true;
                } else if((motion&3u)==2) {mouse_pitch_=0;mouse_valid_=true;}
            }
        }
        write_pitch=mouse_valid_;pitch_raw=mouse_valid_?mouse_pitch_:s.raw_pitch;
    }
    // Caller has already excluded unclaimed aggregate rotations. Held
    // keyboard yaw/roll retain their exact native values.
    float raw(int axis,float native_raw) const {
        return active&&axis==0&&write_pitch?pitch_raw:native_raw;
    }
private:
    bool have_motion_=false,previous_keyboard_=false,mouse_valid_=false,edge_wait_=false;
    bool have_native_=false;
    std::uint64_t previous_motion_=0,previous_mapping_=0;
    float mouse_pitch_=0,previous_native_pitch_=0;
};
}
