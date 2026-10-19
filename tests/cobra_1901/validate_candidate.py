"""Source-bound scope and feature regression for the explicit S re-press fix."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
H=Path(__file__).resolve().parent;D=H.parents[1];T=D/'tests';R=D/'runtime'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
norm=lambda b:b.decode('utf-8-sig').replace('\r\n','\n')
release=json.loads((D/'release.json').read_text());assert (release['version'],release['build'])==('2.3',2026101901)
changed=[]
with zipfile.ZipFile(H/'baseline_1701_sources.zip') as z:
 for n in z.namelist():
  if not n.startswith(('runtime/src/','runtime/scripts/','src/')):continue
  p=D/n
  assert p.is_file(),n
  old=norm(z.read(n));now=p.read_text(encoding='utf-8-sig')
  if now==old:continue
  changed.append(n)
  assert n in {'runtime/src/native_player_maneuver.h','runtime/src/pack_identity.h','src/PackCore.cs'},n
  if n=='src/PackCore.cs':assert now.replace('2026101901','2026101701')==old,'Installer logic changed'
 assert (R/'src/mouse_aim.cpp').read_text(encoding='utf-8-sig')==norm(z.read('runtime/src/mouse_aim.cpp')),'Main flight callback changed'
 assert 'runtime/src/native_player_maneuver.h' in changed
commands=[T/'hotas_1701/run_core_checks.py',T/'support_1701/run_monitor_checks.py',T/'support_1701/run_monitor_ui.py',T/'support_1701/run_display_retry_checks.py',T/'support_1701/run_capture_checks.py',T/'support_1701/run_support_report.py',T/'native_player_maneuver_test.py',T/'native_psm_input_pipeline_test.py',T/'native_psm_admission_test.py',H/'repress_checks.py',T/'focus_1607/run_slow_lens_checks.py',T/'focus_1607/run_interactive_checks.py',T/'focus_1607/run_seed_mode_checks.py',T/'focus_1508/focus_camera_audit.py',T/'focus_1508/hud_display_audit.py',T/'stretch_1604/widget_guard_test.py',T/'render_1511/typed_viewport_scope_audit.py',T/'first_person_camera_test.py',T/'native_landing_integration_test.py',T/'focus_1607/run_translation_ui.py']
results=[]
for j,test in enumerate(commands):
 run=subprocess.run([sys.executable,str(test)],cwd=D,capture_output=True,text=True,encoding='utf-8',errors='replace')
 (H/f'validation_{j}.log').write_text(run.stdout+run.stderr,encoding='utf-8')
 assert run.returncode==0,run.stdout+run.stderr
 print(run.stdout[-500:].strip(),flush=True);results.append({'test':test.relative_to(D).as_posix(),'passed':True})
proof=json.loads((H/'repress_evidence.json').read_text(encoding='utf-8-sig'))
assert proof['passed']
files=[D/n for n in changed]+[R/'src/mouse_aim.cpp',R/'native_player_maneuver_test.cpp',D/'src/Launcher.cs',D/'src/SupportReport.cs',D/'src/Setup.cs',D/'src/PackCore.cs',D/'build_pack.py',Path(__file__),H/'repress_checks.py']
files += list(H.glob('repress_*.cpp'))
report={'passed':True,'version':'2.3','build':2026101901,'tests':results,'source_sha256':{p.relative_to(D).as_posix():sha(p) for p in files},'negative_control':'Published1701 Control loses a genuine S release/re-press observed inside one native mapping. The bounded next-packet fix passes the same native admission sequence; no eligible-speed crossing, throttle/brake hold, invalid state or reset may invent a press. See repress_evidence.json.','only_native_player_maneuver_repress_changed_from1701':True,'flight_math_and_main_callback_unchanged':True,'cobra_report_root_cause_confirmed':False,'cobra_gameplay_verified':False,'owner_gameplay_tested':False,'published':False,'validation_limit':'Exact production helper, native admission and feature regressions against synthetic memory. The remote report has no mission/input log and is not claimed reproduced in live gameplay.'}
(H/'regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('PASS source-bound1901 regression; only bounded physical S re-press recognition changed.')
