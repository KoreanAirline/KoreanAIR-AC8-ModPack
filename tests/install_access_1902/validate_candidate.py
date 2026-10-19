"""Installer-only scope against the published1901 source; no release approval."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
H=Path(__file__).resolve().parent;D=H.parents[1];T=D/'tests';R=D/'runtime'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
norm=lambda b:b.decode('utf-8-sig').replace('\r\n','\n')
release=json.loads((D/'release.json').read_text(encoding='utf-8-sig'))
assert (release['version'],release['build'])==('2.3',2026101902)
changed=[]
with zipfile.ZipFile(H/'baseline_1901_sources.zip') as z:
    for n in z.namelist():
        if not n.startswith(('runtime/src/','runtime/scripts/','src/')):continue
        p=D/n;assert p.is_file(),n
        if p.read_text(encoding='utf-8-sig')!=norm(z.read(n)):
            changed.append(n)
            assert n in {'src/PackCore.cs','src/Ui.cs','src/Setup.cs','runtime/src/pack_identity.h'},n
        if n=='runtime/src/pack_identity.h':
            assert p.read_text(encoding='utf-8-sig').replace('2026101902','2026101901')==norm(z.read(n))
    for name in ('README_ENG.txt','README_KOR.txt'):
        assert (D/name).read_bytes()==z.read(name),'Owner manual changed'
assert 'src/PackCore.cs' in changed and 'src/Ui.cs' in changed
commands=[
    [sys.executable,H/'run_diagnostics.py'],
    [sys.executable,T/'hotas_1701/run_core_checks.py'],
    [sys.executable,T/'support_1701/run_support_report.py'],
    [sys.executable,T/'focus_1607/run_translation_ui.py'],
]
results=[]
for i,command in enumerate(commands):
    run=subprocess.run(list(map(str,command)),cwd=D,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (H/f'validation_{i}.log').write_text(run.stdout+run.stderr,encoding='utf-8')
    assert run.returncode==0,run.stdout+run.stderr
    print(run.stdout[-800:].strip(),flush=True)
    results.append({'test':Path(command[1]).relative_to(D).as_posix(),'passed':True})
paths=[D/n for n in changed]+[D/'src/Setup.cs',D/'src/Launcher.cs',D/'src/UpdateCore.cs',D/'src/SupportReport.cs',D/'build_pack.py',D/'release.json',Path(__file__),H/'run_diagnostics.py',H/'DiagnosticAudit.cs',H/'DiagnosticAudit.dll']
report={'passed':True,'version':'2.3','build':2026101902,'tests':results,
    'source_sha256':{p.relative_to(D).as_posix():sha(p) for p in paths},
    'negative_control':'The published1901 installer reproduces File.InternalMove UnauthorizedAccessException 0x80070005 when file creation is permitted but rename/delete is denied. The candidate detects that folder limitation before replacing or removing package files; its diagnostic captures stage, HRESULT and path state. This reproduces the symptom, not the unobserved cause on the reporter PC.',
    'gameplay_sources_unchanged_from_published1901':True,'owner_manuals_unchanged':True,
    'remote_installation_fixed_confirmed':False,'owner_gameplay_tested':False,'published':False,
    'validation_limit':'No access to the remote PC. Per-file policies, antivirus filters and access changes after preflight can still reject installation. No ACL/security settings are changed, and no unsafe overwrite fallback is added.'}
(H/'regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('PASS installer-only candidate1902 source scope and diagnostics; remote installation cause remains unconfirmed.')
