"""Actual Core install and exact Setup CLI/provider, using inert local fixtures.

The new library is loaded through PowerShell reflection, never launched as an
executable. No old binary, game, native mod or network endpoint is executed.
Only CampaignSubtitles generation and unused UI/update branches are stubbed.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import secrets
import subprocess
import time
import uuid
import zipfile

H = Path(__file__).resolve().parent
D = H.parents[1]
OUT = H / ('installed_setup_cache_' + time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6])
OUT.mkdir()
CSC = Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
core_path = D / 'src/PackCore.cs'
provider_path = D / 'src/UpdateCore.cs'
setup_path = D / 'src/Setup.cs'
core = core_path.read_text(encoding='utf-8')
provider = provider_path.read_text(encoding='utf-8')
setup = setup_path.read_text(encoding='utf-8')


def block(source, marker):
    start = source.index(marker)
    at = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[at] == '{') - (source[at] == '}')
        at += 1
    return source[start:at]


brand = re.search(r'const string Brand="([^"]+)"', core).group(1)
build = int(re.search(r'const long ReleaseBuild\s*=\s*(\d+)', core).group(1))
version = brand.rsplit('_', 1)[1]
tag = f'v{version}-b{build}'
MOD = 'Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/'
files = {
    MOD + 'config.ini': (b'[control]\r\nsensitivity=0.01\r\n', 'runtime', True),
    MOD + 'display.ini': (b'[display]\r\nfov=90\r\n', 'runtime', True),
    MOD + 'subtitle.ini': (b'[subtitles]\r\nposition=native\r\n', 'runtime', True),
    MOD + 'Scripts/main.lua': (b'-- inert fixture, never executed\r\n', 'runtime', False),
    'Game/Binaries/Win64/dinput8.dll': (b'inert synthetic campaign hook; never executable', 'campaign', False),
    'KoreanAIR_AC8_ModPack/Translation/campaign-dialogue.json.gz': (b'inert synthetic dictionary', 'campaign', False),
    'fixture-id.txt': (secrets.token_bytes(512), 'common', False),
}
manifest = {'files': [], 'legacy': {}}
candidate = OUT / 'candidate'
candidate.mkdir()
payload = candidate / 'Payload.zip'
with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path, (data, group, mutable) in files.items():
        source = 'payload/' + path
        manifest['files'].append(dict(path=path, source=source,
                                     hash=hashlib.sha256(data).hexdigest(),
                                     group=group, mutable=mutable))
        archive.writestr(source, data)
    manifest_bytes = json.dumps(manifest, separators=(',', ':')).encode()
    archive.writestr('manifest.json', manifest_bytes)
descriptor = dict(schema=1, version=version, build=build, tag=tag,
                  filename='Payload.zip', sha256=hashlib.sha256(payload.read_bytes()).hexdigest(),
                  size=payload.stat().st_size,
                  url=f'https://github.com/KoreanAirline/KoreanAIR-AC8-ModPack/releases/download/{tag}/Payload.zip',
                  manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest())
(OUT / 'descriptor.json').write_text(json.dumps(descriptor, separators=(',', ':')))
(OUT / 'manifest.json').write_bytes(manifest_bytes)
extracted = {
    'InstallerPayloadDescriptor': block(provider, 'public sealed class InstallerPayloadDescriptor'),
    'ReleasePayload': block(provider, 'public static class ReleasePayload'),
    'Setup.Main': block(setup, '[STAThread]static int Main('),
}
repository = next(line.strip() for line in provider.splitlines()
                  if 'public const string Repository=' in line)
isolated = OUT / 'ExactSetupProvider.cs'
isolated.write_text('''using System;using System.IO;using System.Net;using System.Linq;using System.Reflection;using System.Text;using System.Text.RegularExpressions;using System.Threading;using System.IO.Compression;using System.Security.Cryptography;using System.Windows.Forms;
using KoreanAIR;
namespace KoreanAIR {
''' + extracted['InstallerPayloadDescriptor'] + '\n' + extracted['ReleasePayload'] + '''
public static class UpdateCore {
''' + repository + '''
public static int NetworkAttempts;
internal static HttpWebResponse Response(string url,int timeout){++NetworkAttempts;throw new InvalidOperationException("Network unavailable in isolated fixture.");}
public static void ApplyInstaller(string root,string nonce,string token,Assembly assembly){throw new InvalidOperationException("Updates excluded from fixture.");}
}
public sealed class UiLanguage {public string Error(Exception ex){return ex.Message;}public string T(string en,string ko){return en;}}
public static class CampaignSubtitles {
public sealed class Result {public byte[] Pak;public string Fingerprint,Status;}
public static string Fingerprint(string root,byte[] patch){return "synthetic-current-stock";}
public static Result Build(string root,byte[] patch){return new Result{Pak=Encoding.UTF8.GetBytes("inert generated current-stock dialogue archive"),Fingerprint="synthetic-current-stock",Status="Synthetic fixture only"};}
}
}
class Setup:Form {
static IntPtr SetThreadDpiAwarenessContext(IntPtr context){return IntPtr.Zero;}
public Setup(string root,bool? translation){}
''' + extracted['Setup.Main'] + '\n}\n')
library = candidate / 'Setup.exe'
sources = [core_path, isolated, H / 'InstalledSetupCacheAudit.cs']
refs = ['System.Windows.Forms.dll', 'System.Drawing.dll', 'System.Web.Extensions.dll',
        'System.IO.Compression.dll', 'System.IO.Compression.FileSystem.dll']
subprocess.run([str(CSC), '/nologo', '/target:library', '/platform:x64',
                '/define:FRAME_GENERATION_TEST;ATOMIC_TEST', '/out:' + str(library),
                '/resource:' + str(OUT / 'descriptor.json') + ',PayloadDescriptor.json',
                '/resource:' + str(OUT / 'manifest.json') + ',PayloadManifest.json',
                *['/r:' + reference for reference in refs], *map(str, sources)], check=True)
host = OUT / 'invoke-audit.ps1'
host.write_text('''param([string]$auditPath,[string]$phase,[string]$fixturePath,[string]$reportPath)
$ErrorActionPreference='Stop'
$assembly=[Reflection.Assembly]::LoadFile([IO.Path]::GetFullPath($auditPath))
$method=$assembly.GetType('InstalledSetupCacheAudit',$true).GetMethod('Main',[Reflection.BindingFlags]'Static,NonPublic')
$arguments=New-Object object[] 1
$arguments[0]=[string[]]@($phase,$fixturePath,$reportPath)
exit [int]$method.Invoke($null,$arguments)
''')
root = OUT / 'isolated-game'
cache_base = Path(os.environ['LOCALAPPDATA']) / 'KoreanAIR_AC8_ModPack/Payloads'
owned_cache = cache_base / descriptor['sha256']
assert not owned_cache.exists(), 'Unique synthetic cache unexpectedly exists; refusing to touch it.'
reports = []
try:
    for phase, assembly in [('prepare', library), ('enable', root / 'KoreanAIR_AC8_ModPack/Setup.exe')]:
        report_path = OUT / (phase + '.json')
        result = subprocess.run(['powershell.exe', '-NoProfile', '-File', str(host),
                                 str(assembly), phase, str(root), str(report_path)],
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                capture_output=True, text=True, errors='replace', timeout=60)
        print(result.stdout, end='')
        if result.returncode:
            print(result.stderr)
        reports.append(json.loads(report_path.read_text(encoding='utf-8')))
        result.check_returncode()
finally:
    # Delete only this synthetic payload's newly created SHA cache leaf. No
    # recursive deletion or real release cache modification is performed.
    assert owned_cache.parent.resolve() == cache_base.resolve()
    assert re.fullmatch('[a-f0-9]{64}', owned_cache.name)
    if owned_cache.exists():
        for item in owned_cache.iterdir():
            assert item.is_file() and (item.name == 'Payload.zip' or re.fullmatch(r'download-[a-f0-9]{32}\.part', item.name))
            item.unlink()
        owned_cache.rmdir()
report = dict(
    passed=all(part['passed'] for part in reports),
    checks=[check for part in reports for check in part['checks']],
    build=build,
    source_sha256={path.relative_to(D).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in [core_path, provider_path, setup_path, H / 'InstalledSetupCacheAudit.cs', Path(__file__)]},
    exact_extracted_source_sha256={name: hashlib.sha256(text.encode()).hexdigest()
                                   for name, text in extracted.items()},
    fixture_payload_sha256=descriptor['sha256'],
    scope='Full production Core.Install with FRAME_GENERATION_TEST settings isolation and ATOMIC_TEST observation; exact production Setup.Main and ReleasePayload. Subtitle archive generation is synthetic; UI and unused update branches stubbed.',
    execution_backend='New managed library loaded by ordinary Windows PowerShell reflection, never a custom executable process.',
    game_modified=False, game_executed=False, native_mod_executed=False,
    network_available=False, network_requested=False, temporary_Setup_copy=False,
    synthetic_SHA_cache_removed=True,
)
(OUT / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
(H / 'installed_setup_cache_results.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(passed=report['passed'], checks=len(report['checks']), report=str(OUT / 'results.json'))))
