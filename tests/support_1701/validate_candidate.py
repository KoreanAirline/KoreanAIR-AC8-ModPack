from pathlib import Path
import hashlib,json,re,subprocess,sys,zipfile
H=Path(__file__).resolve().parent;D=H.parents[1];T=D/'tests';R=D/'runtime'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((D/'release.json').read_text());assert (r['version'],r['build'])==('2.3',2026101701)
changed=[]
with zipfile.ZipFile(H/'baseline_1608_sources.zip') as z:
 old=z.read('runtime/src/mouse_aim.cpp').decode('utf-8-sig').replace('\r\n','\n')
 now=(R/'src/mouse_aim.cpp').read_text(encoding='utf-8-sig')
 stripped=now.replace('update_policy.invalidate();engine_span_topology_revision.fetch_add(1,std::memory_order_relaxed);','update_policy.invalidate();')
 stripped=stripped.replace('poll_engine_span(game_window,settings.enabled&&settings.span,settings.monitors)','poll_engine_span(game_window,settings.enabled&&settings.span)')
 stripped=stripped.replace('#include "support_capture.h"\n','').replace('ac8support::Capture support_capture;\n','')
 a=stripped.index('    wchar_t support_token[32]{};');b=stripped.index('    config_file_seen=',a);stripped=stripped[:a]+stripped[b:]
 stripped=stripped.replace('    support_capture.mouse(trace_dx,trace_dy);\n','')
 a=stripped.index('        int64_t support_x=0,support_y=0;');b=stripped.index('        queue_input_trace(trace);',a);stripped=stripped[:a]+stripped[b:]
 assert stripped==old,'Flight implementation changed beyond passive optional diagnostics'
 allowed={'runtime/src/pack_identity.h','runtime/src/mouse_aim.cpp','runtime/src/display_engine.h','runtime/src/display_window.h','runtime/src/display_runtime.h','runtime/scripts/main.lua'}
 for n in z.namelist():
  if not n.startswith(('runtime/src/','runtime/scripts/')):continue
  if z.read(n).decode('utf-8-sig').replace('\r\n','\n')==(D/n).read_text(encoding='utf-8-sig'):continue
  changed.append(n);assert n in allowed,n
 # This new version marker is the only Lua change; subtitles, targeting and
 # the full native camera/final-output/HUD implementation remain identical.
 assert (R/'scripts/main.lua').read_text(encoding='utf-8-sig').replace('KoreanAIR_AC8_ModPack_2.3','KoreanAIR_AC8_ModPack_2.2')==z.read('runtime/scripts/main.lua').decode('utf-8-sig').replace('\r\n','\n')
commands=[T/'hotas_1701/run_core_checks.py',H/'run_monitor_checks.py',H/'run_monitor_ui.py',H/'run_display_retry_checks.py',H/'run_capture_checks.py',H/'run_support_report.py',T/'focus_1607/run_slow_lens_checks.py',T/'focus_1607/run_interactive_checks.py',T/'focus_1607/run_seed_mode_checks.py',T/'focus_1508/focus_camera_audit.py',T/'focus_1508/hud_display_audit.py',T/'stretch_1604/widget_guard_test.py',T/'render_1511/typed_viewport_scope_audit.py',T/'first_person_camera_test.py',T/'native_landing_integration_test.py',T/'focus_1607/run_translation_ui.py']
results=[]
for j,test in enumerate(commands):
 run=subprocess.run([sys.executable,str(test)],cwd=D,capture_output=True,text=True,encoding='utf-8',errors='replace')
 (H/f'validation_{j}.log').write_text(run.stdout+run.stderr,encoding='utf-8')
 assert run.returncode==0,run.stdout+run.stderr
 print(run.stdout[-400:].strip(),flush=True);results.append({'test':test.relative_to(D).as_posix(),'passed':True})
files=[D/n for n in changed]+[R/'src/support_capture.h',D/'src/SupportReport.cs',D/'src/Launcher.cs',D/'src/Setup.cs',D/'src/PackCore.cs',D/'build_pack.py',Path(__file__)]+[p for p in H.glob('*') if p.suffix in ['.py','.cpp','.cs','.json'] and p.name not in ['regression.json','candidate.json']]
r={'passed':True,'version':'2.3','build':2026101701,'tests':results,'source_sha256':{p.relative_to(D).as_posix():sha(p) for p in files},'negative_control':'61 shared monitor layouts include27 valid layouts rejected by exact1608 selector. Unsupported topology5000 polls previously enumerated/logged5000times, now5enumerations and1log. Existing centered layouts unchanged. Optional diagnostics have bounded fresh-request and expiry negative cases.','flight_implementation_unchanged_from1608':True,'remote_weave_fixed_confirmed':False,'owner_gameplay_tested':False,'published':False,'validation_limit':'Automated source-bound regression and mocked-host tests; remote reporter monitor layout/flight behavior not observed directly.'}
(H/'regression.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print('PASS source-bound candidate1701 feature regression.')
