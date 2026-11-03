"""Current-game gate: source-bound ABI, installer, monitor and existing control regressions."""
from pathlib import Path
import hashlib,json,subprocess,sys
H=Path(__file__).resolve().parent;D=H.parents[1];R=D/'runtime';T=D/'tests';B=D/'build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
release=json.loads((D/'release.json').read_text());BUILD=release['build'];assert release['version']=='2.4' and BUILD>=2026110303
tests=['update_20261103/verify_native_guards.py','font_bug_20261103/test_campaign_subtitles_cs.py','font_bug_20261103/test_subtitle_lifecycle.py','font_bug_20261103/test_subtitle_defaults.py','font_bug_20261103/test_installed_setup_cache.py','update_20261103/run_game_build.py','update_20261103/run_shared_loader_inspection.py','update_20261103/run_shared_provider_integration.py','update_20261103/run_update_changes.py','native_headlook_test.py','native_input_axes_test.py','native_launcher_identity_test.py','debrief_1503/validate_replay.py']
results=[]
for test in tests:
    r=subprocess.run([sys.executable,str(T/test)],cwd=D,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (H/(Path(test).stem+'_gate.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
    assert r.returncode==0,(test,(r.stdout+r.stderr)[-2000:])
    print('PASS '+test,flush=True);results.append(dict(test=test,passed=True))
proof_names=['update_20261103/native_guards.json','font_bug_20261103/csharp_current_stock_results.json','font_bug_20261103/subtitle_lifecycle_results.json','font_bug_20261103/subtitle_defaults_results.json','font_bug_20261103/installed_setup_cache_results.json','update_20261103/game_build_results.json','update_20261103/shared_loader_inspection_results.json','update_20261103/shared_provider_integration_results.json','update_20261103/update_changes_results.json',
    'monitor_1103/monitor_regression.json','render_1510/final_pipeline_evidence.json','stretch_1603/ui_projection_query_evidence.json','stretch_1604/widget_guard_evidence.json',
    'alt_manual_1503/evidence.json','alt_manual_1503/handoff_order_evidence.json','alt_manual_1503/worker_epoch_evidence.json','debrief_1503/regression.json','candidate_1504/input_axes/evidence.json',
    'aim_jitter_audit/display_evidence.json','overlay_loop_integration_evidence.json','native_launcher_identity_1503/evidence.json']
evidence={}
for name in proof_names:
    p=T/name;report=json.loads(p.read_text(encoding='utf-8-sig'));assert report['passed'],name
    for relative,h in report.get('source_sha256',{}).items():assert sha(D/relative)==h,('stale evidence',name,relative)
    evidence['tests/'+name]=sha(p)
native=json.loads((R/'build/native_identity.json').read_text());assert(native['version'],native['build'])==('2.4',BUILD)
for relative,h in native['source_sha256'].items():assert sha(D/relative)==h,('native source changed',relative)
assert sha(R/'build/ac8_mouse_aim_010.dll')==sha(R/'scripts/ac8_mouse_aim_010.dll')==native['dll_sha256']
for p in(H/'native_psm_abi_current_build/evidence.json',):
    value=json.loads(p.read_text());assert value['passed'];evidence[p.relative_to(D).as_posix()]=sha(p)
for name in ('map_target_headlook.json','map_native_camera.json','map_native_window.json','final_projection_mapping.json','input_port_mapping.json','war_loader_pattern_audit.json','input_full_restore_proof.json','landing_entry_reverseproof.json'):
    p=H/name;json.loads(p.read_text());evidence[p.relative_to(D).as_posix()]=sha(p)
paths=[D/'release.json',D/'build_pack.py',D/'README_ENG.txt',D/'README_KOR.txt',D/'RELEASE_NOTES.md',D/'campaign-source/campaign-dialogue.json.gz',R/'payload_manifest.json',R/'generate_identity.ps1',T/'feature_regression_gate.py',Path(__file__)]
for folder in('src','runtime/src','runtime/scripts'):
    paths.extend(p for p in(D/folder).rglob('*')if p.is_file())
paths.extend(p for p in R.glob('*')if p.suffix in('.cmd','.cpp','.lua'))
report=dict(passed=True,version='2.4',build=BUILD,source_sha256={p.relative_to(D).as_posix():sha(p)for p in sorted(set(paths))},evidence_sha256=evidence,tests=results,
    native_cpp_lua_build_completed=True,owner_gameplay_tested=False,published=False,
    scope='Current PE exact native guards, independent old-body/caller relocation evidence, private-process native hook/ABI fixtures, real-source controller/camera/UI/installer/monitor regressions, current-stock campaign dialogue remapping with all other current strings preserved. Flight with add-on aircraft and every campaign scene remain unverified.')
(B/'feature_regression.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS exact 2.4 current-source gate; publication requires the separate owner instruction and real startup record.')
