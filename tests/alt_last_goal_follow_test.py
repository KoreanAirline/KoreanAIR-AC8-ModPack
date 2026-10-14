"""Real production gates: last-world-goal pursuit and independent ALT camera.

Executes the extracted ownership/pursuit/response-commit functions and the
unchanged FreeLook implementation. Published 1403 is an expected-failure
negative control. This is not game flight or a convergence simulation.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

here=Path(__file__).resolve().parent
distribution=here.parent
runtime=distribution/'runtime'
baseline=here/'alt_1403_negative_control/mouse_aim.cpp'
assert baseline.is_file(), 'Pinned published 1403 negative-control source required'
assert 'const bool apply_guidance=user_enabled && override_input && !free_look_suspends_guidance();' in baseline.read_text(encoding='utf-8')
runner=here/'input_free_look_gate_test.py'
old=subprocess.run([sys.executable,str(runner),str(baseline)],capture_output=True,text=True)
reason='FAIL: physical ALT before Lua poll keeps last-goal RAW pursuit and coherent response commit'
assert old.returncode!=0 and reason in old.stderr+old.stdout, old.stdout+old.stderr
current=subprocess.run([sys.executable,str(runner)],capture_output=True,text=True)
assert current.returncode==0,current.stdout+current.stderr
assert '447 checks' in current.stdout,current.stdout

source=(runtime/'src/mouse_aim.cpp').read_text(encoding='utf-8')
process=source[source.index('uintptr_t __fastcall process_input('):source.index('bool prepare_hook()')]
assert 'const bool apply_guidance=user_enabled && override_input;' in process
assert 'game_paused.load() || gaze_active.load() || !foreground_is_game()' in process
assert process.index('if(observe_native_landing(pawn))')<process.index('const bool apply_guidance=')
assert 'const bool held_axis[]={held_pitch,held_yaw,held_roll};' in process
assert 'else if(apply_guidance&&valid&&!held_axis[i])' in process
assert 'if(!enabled.load()||!active.load()||game_paused.load()||gaze_active.load())return false;' in source

files=['runtime/src/mouse_aim.cpp','runtime/src/free_look.h',
       'runtime/src/manual_rotation_input.h','tests/input_free_look_gate_test.py',
       'tests/native_psm_input_pipeline_test.py',
       'tests/native_rotation_input_pipeline_test.py',
       'tests/native_psm_admission_test.py',
       'tests/alt_last_goal_follow_test.py']
report={
    'passed':True,'checks':447,
    'scope':'Extracted production ownership/pursuit/response gates plus actual FreeLook, controlled physical keys. No actual game flight, target convergence or handling-quality claim.',
    'source_sha256':{name:hashlib.sha256((distribution/name).read_bytes()).hexdigest() for name in files},
    'negative_control':{'tag':'v1.4-b2026101403','source_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),
        'expected_failure':reason,'returncode':old.returncode},
    'result':current.stdout.strip(),
    'policy':'ALT holds the existing world-space aim goal. Automatic pursuit and response commit continue on unheld flight axes; explicit WASD/QE axes retain native input. ALT mouse movement controls only camera. Manual keyboard flight during ALT recenters the goal at the actual nose when ALT is released. Existing pause/gaze/landing/lifecycle/disabled/matched-native-input gates remain.',
    'automatic_psm':'The unchanged provenance guard now also protects automatic elevator commands while ALT is held; native held W/S preparation and accepted native maneuvers keep their existing ownership.',
}
(here/'alt_last_goal_follow_evidence.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(current.stdout.strip())
print('PASS published 1403 negative control: retained-goal pursuit stops at physical ALT hold; current build continues it.')
