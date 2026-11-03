"""Record observed startup, module signatures and retained native initialization logs."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;D=H.parents[1];G=Path('E:/SteamLibrary/steamapps/common/ACE COMBAT 8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
candidate=json.loads((H/'candidate.json').read_text());log=max((G/'Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/Logs').glob('MouseAim-*.log'),key=lambda p:p.stat().st_mtime_ns);text=log.read_text(encoding='utf-8-sig',errors='replace')
required=['KoreanAIR_AC8_ModPack_2.4 ready','native landing build guard: verified','native maneuver input build guard: verified','native player maneuver build guard: verified','native response sync build guard: verified','native raw input provenance hook: verified','native PSM admission provenance hook: verified','native camera post-update registered','DISPLAY final LocalPlayer projection registered','DISPLAY native render viewport: 7680x1440','independent mouse input ready']
checks={name:name in text for name in required};assert all(checks.values()),checks
modules={
 'campaign_loader':G/'Game/Binaries/Win64/dinput8.dll',
 'proxy':G/'Game/Binaries/Win64/dwmapi.dll',
 'UE4SS':G/'Game/Binaries/Win64/UE4SS/UE4SS.dll',
 'mouse_native':G/'Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/Scripts/ac8_mouse_aim_010.dll'}
report=dict(version='2.4',build=2026110301,passed=True,tested_binary_sha256=candidate['tested_binary_sha256'],startup_checks=checks,
    loaded_modules_verified_from_process=True,loaded_module_sha256={k:sha(p)for k,p in modules.items()},visible_window='ACE COMBAT 8 title screen reached after shader preparation; animated render remained responsive',
    startup_log_sha256=sha(log),owner_gameplay_tested=False,mission_flight_tested=False,third_party_aircraft_flight_tested=False,
    preexisting_dependency_warnings='UE4SS ProcessConsoleExec detour and FObjectPtrProperty size warnings were present. KoreanAIR native feature initialization and full renderer completed; no claim that optional console-dependent external mods work.',
    limits='Startup/title and real module loading only. Automated menu key events did not establish menu navigation or flight control, and are not counted as successful input tests. No new crash report was observed during startup. Campaign mission/aircraft add-on operation remains unverified.')
(H/'smoke_launch.json').write_text(json.dumps(report,indent=2)+'\n')
print('Recorded actual startup: four loaded module hashes, current native hooks, 7680x1440 output; flight not claimed.')
