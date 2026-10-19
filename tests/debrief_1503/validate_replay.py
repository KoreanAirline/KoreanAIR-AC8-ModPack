"""Real Lua observers, pre-fix negative control, and captured replay provenance."""
from pathlib import Path
import hashlib, json, shutil, subprocess, tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RUNTIME=ROOT/'runtime'
LUA=RUNTIME/'tools/lua.exe'
tests={}
for name in ['lua_display_cinematic_test','lua_scene_projection_test','lua_display_resolution_lifecycle_test']:
    run=subprocess.run([str(LUA),str(RUNTIME/(name+'.lua')),str(RUNTIME)],capture_output=True,text=True)
    assert run.returncode==0,run.stdout+run.stderr
    output=run.stdout+run.stderr
    (HERE/(name+'.log')).write_text(output)
    tests[name]={'passed':True,'summary':output.splitlines()[-1]}

prior=HERE/'prior_scene.lua'
assert hashlib.sha256(prior.read_bytes()).hexdigest()=='0f4e3bb365e3cc725200f411e4f7be3b1f0604f73bee8b54942bcdac1390bb04'
release=json.loads((ROOT/'release.json').read_text(encoding='utf-8-sig'))
native_policy=release['build']>=2026101509
if release['build']>=2026101510:
    proof_path=ROOT/('tests/install_access_1902/regression.json' if release['version']=='2.3' and release['build']>=2026101902 else 'tests/cobra_1901/regression.json' if release['version']=='2.3' and release['build']>=2026101901 else 'tests/support_1701/regression.json' if release['version']=='2.3' else 'tests/transition_1608/regression.json' if release['build']>=2026101608 else 'tests/focus_1607/regression.json' if release['build']>=2026101607 else 'tests/focus_1606/regression.json' if release['build']>=2026101606 else 'tests/stretch_1604/regression.json' if release['build']>=2026101604 else 'tests/stretch_1603/regression.json' if release['build']>=2026101603 else 'tests/render_1511/regression.json' if release['build']>=2026101601 else 'tests/render_1510/regression.json')
    proof=json.loads(proof_path.read_text(encoding='utf-8-sig'))
    assert proof['passed']
    for name,expected in proof['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,'stale final projection evidence: '+name
    negative={'passed':True,'result':proof['negative_control']}
elif native_policy:
    # The captured1509 failure passed the historical ReplayPawn class test but
    # still published Observe. Test the actual native final-POV pipeline now,
    # rather than treating another Lua class admission as a rendering fix.
    proof_path=ROOT/'tests/scene_1509/native_scene_evidence.json'
    proof=json.loads(proof_path.read_text(encoding='utf-8-sig'))
    assert proof['passed']
    for name,expected in proof['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected, 'stale native scene evidence: '+name
    assert proof['actual_failure']['mode']==4
    assert proof['tests']['baseline_1508']['expected_negative']
    negative={'passed':True,'result':'Captured fresh Observe command reproduces the real cropped replay in exact1508 native source; current final-POV pipeline passes the same assertion.'}
else:
 with tempfile.TemporaryDirectory(prefix='ac8-replay-proof-') as temporary:
    fixture=Path(temporary);scripts=fixture/'scripts';scripts.mkdir()
    for name in ['display.lua','gaze.lua','main.lua']:
        shutil.copyfile(RUNTIME/'scripts'/name,scripts/name)
    shutil.copyfile(prior,scripts/'scene.lua')
    run=subprocess.run([str(LUA),str(RUNTIME/'lua_display_cinematic_test.lua'),str(fixture)],capture_output=True,text=True)
    output=(run.stdout+run.stderr).replace(str(fixture),'<prior-scene-fixture>')
    assert run.returncode!=0 and 'actual ReplayPawn with owned active replay component widens mode: expected 3, received 4' in output,output
    (HERE/'prior_scene_failure.log').write_text(output)
    negative={'passed':True,'result':'The exact prior installed scene.lua fails the new ReplayPawn regression with expected SceneActor(3), actual Observe(4).'}

capture=json.loads((HERE/'debrief_active_components.json').read_text())
owner=capture['local_players'][0];target=owner['current_target']
assert 'LiveReplayPawn' in target['class_chain'] and owner['local_owner_backlink_matches']
assert capture['render_size']==[7680,1440] and owner['normalized_viewport_origin_size']==[0,0,1,1]
active=[camera for camera in target['camera_components'] if camera.get('active')]
assert len(active)==1 and 'LiveReplayAce8CameraComponent' in active[0]['class_chain']
assert active[0]['outer']==target['address'] and owner['pov']['aspect']<7680/1440
files=[RUNTIME/'scripts/scene.lua',RUNTIME/'lua_display_cinematic_test.lua',Path(__file__)]
report={'passed':True,'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    'tests':tests,'negative_control':negative,
    'confirmed_live_failure':{'target_class_chain':target['class_chain'],'render_size':capture['render_size'],
        'normalized_viewport':owner['normalized_viewport_origin_size'],'native_aspect':owner['pov']['aspect'],
        'camera_components':len(target['camera_components']),'active_component_class':active[0]['class'],
        'owned_active_replay_component':True},
    'runtime_policy':('Successful final LocalPlayer projection after native view extensions owns the full 3D output rectangle, independent of scene classes and retained camera cache.' if release['build']>=2026101510 else 'Native final render POV of the verified current LocalPlayer camera manager owns projection; target/controller class names and Lua component discovery do not admit or reject scenes.' if native_policy else 'Only the confirmed ReplayPawn and an active valid owned replay-camera witness gain SceneActor permission. Stable scenes check that one witness; camera invalidation rechecks a bounded current-target array immediately. Failed proof retries at most once per second.'),
    'validation_limit':'The pre-fix failure was captured in the actual user-confirmed debrief. Candidate visible rendering remains for owner testing after installation; no live code injection or settings changes were performed.'}
(HERE/'regression.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: real replay/hangar/cinematic/resolution regressions; '+('native final-output proof, zero-lens admission negative control; visible candidate gameplay unverified.' if release['build']>=2026101510 else 'captured native1508 Observe negative control; final-POV ownership.' if native_policy else 'exact prior-scene negative control; confirmed debrief failure provenance.'))
