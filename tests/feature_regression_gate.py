"""Validate the local candidate before packaging; never authorizes publication."""
from pathlib import Path
import hashlib,json,subprocess,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")

D=Path(__file__).resolve().parents[1]
R=D/'runtime';B=D/'build';T=D/'tests'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
release=json.loads((D/'release.json').read_text(encoding='utf-8-sig'))
if release['version']=='2.3' and release['build']>=2026101902:
    candidate_commands=[[sys.executable,T/'install_access_1902/validate_candidate.py'],[sys.executable,T/'native_headlook_test.py'],[sys.executable,T/'scene_input_release_test.py'],[sys.executable,T/'candidate_1505/emulate_headlook.py']]
    candidate_proofs=('install_access_1902/regression.json',)
elif release['version']=='2.3' and release['build']>=2026101901:
    candidate_commands=[[sys.executable,T/'cobra_1901/validate_candidate.py'],[sys.executable,T/'native_headlook_test.py'],[sys.executable,T/'scene_input_release_test.py'],[sys.executable,T/'candidate_1505/emulate_headlook.py']]
    candidate_proofs=('cobra_1901/regression.json',)
elif release['version']=='2.3':
    candidate_commands=[[sys.executable,T/'support_1701/validate_candidate.py'],[sys.executable,T/'native_headlook_test.py'],[sys.executable,T/'scene_input_release_test.py'],[sys.executable,T/'candidate_1505/emulate_headlook.py']]
    candidate_proofs=('support_1701/regression.json',)
elif release['version']=='2.2' and release['build']>=2026101608:
    candidate_commands=[
        [sys.executable,T/'transition_1608/validate_changes.py'],
        [sys.executable,T/'native_headlook_test.py'],
        [sys.executable,T/'scene_input_release_test.py'],
        [sys.executable,T/'candidate_1505/emulate_headlook.py'],
    ]
    candidate_proofs=('transition_1608/regression.json',)
elif release['version']=='2.2' and release['build']>=2026101607:
    candidate_commands=[
        [sys.executable,T/'focus_1607/validate_changes.py'],
        [sys.executable,T/'native_headlook_test.py'],
        [sys.executable,T/'scene_input_release_test.py'],
        [sys.executable,T/'candidate_1505/emulate_headlook.py'],
    ]
    candidate_proofs=('focus_1607/regression.json',)
elif release['version']=='2.2' and release['build']>=2026101606:
    candidate_commands=[
        [sys.executable,T/'focus_1606/validate_changes.py'],
        [sys.executable,T/'native_headlook_test.py'],
        [sys.executable,T/'scene_input_release_test.py'],
        [sys.executable,T/'candidate_1505/emulate_headlook.py'],
    ]
    candidate_proofs=('focus_1606/regression.json',)
elif release['version']=='2.2' and release['build']>=2026101604:
    candidate_commands=[
        [sys.executable,T/'stretch_1604/validate_changes.py'],
        [sys.executable,T/'native_headlook_test.py'],
        [sys.executable,T/'scene_input_release_test.py'],
        [sys.executable,T/'candidate_1505/emulate_headlook.py'],
    ]
    candidate_proofs=('stretch_1604/regression.json',)
elif release['version']=='2.2' and release['build']>=2026101603:
    candidate_commands=[
        [sys.executable,T/'stretch_1603/validate_changes.py'],
        [sys.executable,T/'native_headlook_test.py'],
        [sys.executable,T/'scene_input_release_test.py'],
        [sys.executable,T/'candidate_1505/emulate_headlook.py'],
    ]
    candidate_proofs=('stretch_1603/regression.json',)
elif release['version']=='2.2' and release['build']>=2026101601:
    candidate_commands=[
        [sys.executable,T/'render_1511/validate_changes.py'],
        [sys.executable,T/'native_headlook_test.py'],
        [sys.executable,T/'scene_input_release_test.py'],
        [sys.executable,T/'candidate_1505/emulate_headlook.py'],
    ]
    candidate_proofs=('render_1511/regression.json',)
elif release['version']=='2.2' and release['build']>=2026101510:
    candidate_commands=[
        [sys.executable,T/'render_1510/validate_changes.py'],
        [sys.executable,T/'native_headlook_test.py'],
        [sys.executable,T/'scene_input_release_test.py'],
        [sys.executable,T/'candidate_1505/emulate_headlook.py'],
    ]
    candidate_proofs=('render_1510/regression.json',)
elif release['version']=='2.2' and release['build']>=2026101509:
    candidate_commands=[
        [sys.executable,T/'scene_1509/validate_changes.py'],
        [sys.executable,T/'native_headlook_test.py'],
        [sys.executable,T/'scene_input_release_test.py'],
        [sys.executable,T/'candidate_1505/emulate_headlook.py'],
    ]
    candidate_proofs=('scene_1509/regression.json',)
elif release['version']=='2.2':
    candidate_commands=[
        [sys.executable,T/'focus_1508/validate_changes.py'],
        [sys.executable,T/'native_headlook_test.py'],
        [sys.executable,T/'scene_input_release_test.py'],
        [sys.executable,T/'candidate_1505/emulate_headlook.py'],
    ]
    candidate_proofs=('focus_1508/regression.json',)
elif release['version']=='2.1':
    candidate_commands=[
        [sys.executable,T/'ultrawide_1507/validate_changes.py'],
        [sys.executable,T/'native_headlook_test.py'],
        [sys.executable,T/'scene_input_release_test.py'],
        [sys.executable,T/'candidate_1505/emulate_headlook.py'],
    ]
    candidate_proofs=('ultrawide_1507/regression.json',)
else:
    candidate_commands=[
        [sys.executable,T/'candidate_1506/validate_changes.py'],
        [sys.executable,T/'candidate_1505/validate_changes.py'],
    ]
    candidate_proofs=('candidate_1505/regression.json','candidate_1506/regression.json')
commands=candidate_commands+[
    [sys.executable,T/'native_input_axes_test.py'],
    [sys.executable,T/'display_camera_audit.py'],
    [sys.executable,T/'overlay_loop_integration_test.py'],
    [sys.executable,T/'alt_manual_takeover_test.py'],
    [sys.executable,T/'alt_handoff_order_test.py'],
    [sys.executable,T/'alt_worker_epoch_test.py'],
    [sys.executable,T/'debrief_1503/validate_replay.py'],
    [R/'tools/lua.exe',R/'lua_reticle_target_test.lua'],
    [sys.executable,T/'native_launcher_identity_test.py'],
]
results=[]
for command in commands:
    result=subprocess.run(list(map(str,command)),cwd=D,capture_output=True,text=True,
                          encoding='utf-8',errors='replace')
    print(result.stdout[-1000:],flush=True)
    if result.returncode:
        print(result.stderr[-2000:]);raise SystemExit(result.returncode)
    results.append(dict(test=Path(command[1]).name,passed=True,result=result.stdout.strip()))

proofs={}
for name in ('alt_manual_1503/evidence.json','alt_manual_1503/handoff_order_evidence.json',
             'alt_manual_1503/worker_epoch_evidence.json','debrief_1503/regression.json',
             'native_launcher_identity_1503/evidence.json','candidate_1504/input_axes/evidence.json',
             'aim_jitter_audit/display_evidence.json','overlay_loop_integration_evidence.json',
             *candidate_proofs):
    path=T/name;proof=json.loads(path.read_text(encoding='utf-8-sig'))
    assert proof['passed'],name
    for source,expected in proof['source_sha256'].items():
        assert sha(D/source)==expected,(name,source,'stale evidence')
    proofs['tests/'+name]=sha(path)
native=json.loads((R/'build/native_identity.json').read_text())
assert (native['version'],native['build'])==(release['version'],release['build'])
assert sha(R/'scripts/ac8_mouse_aim_010.dll')==native['dll_sha256']
for source,expected in native['source_sha256'].items():assert sha(D/source)==expected,source

# Bind the successful tests to the exact sources and shipped Lua scripts. A
# later patch cannot package using an earlier candidate's pass/fail record.
paths=[D/'release.json',R/'generate_identity.ps1',D/'build_pack.py',R/'payload_manifest.json',
       D/'README_ENG.txt',D/'README_KOR.txt',D/'assets/launcher.ico',D/'assets/launcher.png']
for folder in ('runtime/src','runtime/scripts','src'):
    paths.extend(p for p in (D/folder).rglob('*') if p.is_file())
paths.extend(p for p in R.glob('*') if p.is_file() and p.suffix in ('.cpp','.lua','.cmd'))
paths.extend([T/'feature_regression_gate.py',T/'alt_manual_takeover_test.py',
              T/'alt_handoff_order_test.py',T/'alt_worker_epoch_test.py',
              T/'input_free_look_gate_test.py',T/'debrief_1503/validate_replay.py',
              T/'native_input_axes_test.py',T/'display_camera_audit.py',T/'overlay_loop_integration_test.py',
              T/'native_launcher_identity_test.py'])
report=dict(passed=True,version=release['version'],build=release['build'],
    source_sha256={p.relative_to(D).as_posix():sha(p) for p in sorted(set(paths))},
    evidence_sha256=proofs,tests=results,published=False,
    owner_gameplay_tested=False,
    scope='Current candidate source identity, extracted production input gates and scheduling regressions, replay scene proof, existing target selection and actual private input-worker startup. No live combat/debrief display certification.')
(B/'feature_regression.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PASS exact candidate regression gate; local packaging only; owner test and release approval remain required.')
