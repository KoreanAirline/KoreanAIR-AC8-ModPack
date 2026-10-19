"""Compile real installer/UI sources and run isolated diagnostics and atomic audits."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import uuid

H = Path(__file__).resolve().parent
D = H.parent.parent
CSC = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
PS = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(args):
    result = subprocess.run([str(a) for a in args], cwd=D, capture_output=True)
    output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
    if output.strip():
        print(output.strip(), flush=True)
    if result.returncode:
        raise RuntimeError('Diagnostic command failed: ' + str(result.returncode))

refs = ['System.Web.Extensions.dll', 'System.IO.Compression.dll', 'System.IO.Compression.FileSystem.dll', 'System.Drawing.dll', 'System.Windows.Forms.dll']
diagnostic_dll = H / 'DiagnosticAudit.dll'
run([CSC, '/nologo', '/target:library', '/define:ATOMIC_TEST', '/out:' + str(diagnostic_dll), *['/r:' + x for x in refs], D / 'src/PackCore.cs', D / 'src/Ui.cs', H / 'DiagnosticAudit.cs'])

# The unchanged older audit resolves ../src/PackCore.cs beside its result.
# Give it a private source/result layout rather than editing that audit.
work = H / ('diagnostic_build_' + uuid.uuid4().hex)
(work / 'src').mkdir(parents=True)
(work / 'tests').mkdir()
shutil.copyfile(D / 'src/PackCore.cs', work / 'src/PackCore.cs')
atomic_dll = work / 'AtomicWriteAudit.dll'
run([CSC, '/nologo', '/target:library', '/define:ATOMIC_TEST', '/out:' + str(atomic_dll), *['/r:' + x for x in refs], D / 'src/PackCore.cs', D / 'tests/AtomicWriteAudit.cs'])
diagnostic_report = H / 'diagnostic_results.json'
atomic_report = work / 'tests/atomic_write_results.json'
script = work / 'Run.ps1'
script.write_text("""param([string]$DiagnosticDll,[string]$DiagnosticReport,[string]$AtomicDll,[string]$AtomicReport)
$ErrorActionPreference='Stop'
$assembly=[Reflection.Assembly]::LoadFrom($DiagnosticDll)
$arguments=New-Object object[] 1
$arguments[0]=$DiagnosticReport
$result=$assembly.GetType('DiagnosticAudit1902').GetMethod('Execute').Invoke($null,$arguments)
if([int]$result -ne 0){exit 1}
$atomic=[Reflection.Assembly]::LoadFrom($AtomicDll)
$arguments=New-Object object[] 1
$arguments[0]=[string[]]@($AtomicReport)
$flags=[Reflection.BindingFlags]::Static -bor [Reflection.BindingFlags]::NonPublic
$result=$atomic.GetType('AtomicWriteAudit').GetMethod('Main',$flags).Invoke($null,$arguments)
exit [int]$result
""", encoding='utf-8-sig')
run([PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script, str(diagnostic_dll), str(diagnostic_report), str(atomic_dll), str(atomic_report)])
diagnostics = json.loads(diagnostic_report.read_text(encoding='utf-8-sig'))
atomic = json.loads(atomic_report.read_text(encoding='utf-8-sig'))
assert diagnostics['passed'] and atomic['passed']
assert diagnostics['coreSha256'] == atomic['tested_core_sha256'] == sha(D / 'src/PackCore.cs')
shutil.copyfile(atomic_report, H / 'atomic_write_results.json')
proof = dict(passed=True, diagnostic_checks=len(diagnostics['checks']), atomic_checks=len(atomic['checks']), core_sha256=sha(D / 'src/PackCore.cs'), ui_sha256=sha(D / 'src/Ui.cs'), audit_sha256=sha(H / 'DiagnosticAudit.cs'), audit_dll_sha256=sha(diagnostic_dll), diagnostic_results_sha256=sha(diagnostic_report), atomic_results_sha256=sha(H / 'atomic_write_results.json'))
(H / 'diagnostic_gate.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
print('Installer diagnostics: ' + str(proof['diagnostic_checks']) + ' PASS; atomic regression: ' + str(proof['atomic_checks']) + ' PASS', flush=True)
