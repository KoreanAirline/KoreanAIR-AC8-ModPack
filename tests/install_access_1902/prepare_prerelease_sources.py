"""Prepare an anonymous local diagnostic source branch/archive; never push or publish."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import zipfile

H = Path(__file__).resolve().parent
D = H.parent.parent
P = D.parent / 'ac8-github-public'
W = D.parent.parent
B = D / 'build'
BRANCH = 'install-test-b2026101902'
BUILD = 2026101902
SOURCE_NAME = 'KoreanAIR_AC8_ModPack_2.3_INSTALL_TEST_b2026101902_Sources.zip'
CODE = {'.cs', '.py', '.ps1', '.cpp', '.h', '.hpp', '.lua', '.asm', '.inc'}
BLOCKED = {'.exe', '.dll', '.etl', '.dmp', '.pdb', '.obj', '.lib', '.pak', '.ucas', '.utoc', '.pyc', '.bin'}
ASSETS = {'assets/launcher.ico', 'assets/launcher.png'}
sha = lambda data: hashlib.sha256(data).hexdigest()
load = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))

def git(*args, env=None):
    return subprocess.check_output(['git', '-C', str(P), *args], text=True, encoding='utf-8', env=env).strip()

profile_name = Path.home().name
private_names = [profile_name + '109-star', profile_name + '109', profile_name]
path_variants = []
for path in (W, Path.home()):
    for value in (str(path), path.as_posix()):
        path_variants += [(value, '<WORKSPACE>' if path == W else '<USERPROFILE>'), (json.dumps(value)[1:-1], '<WORKSPACE>' if path == W else '<USERPROFILE>')]

def public(data, name):
    if name in ASSETS:
        return data
    encoding = 'utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    text = data.decode(encoding)
    for value, replacement in sorted(path_variants, key=lambda x: -len(x[0])):
        text = re.sub(re.escape(value), lambda _: replacement, text, flags=re.I)
    text = re.sub(r'(?i)([A-Z]:[/\\]+Users[/\\]+)[^/\\\r\n"<>]+(?=[/\\])', lambda m: m[1] + 'USER', text)
    for name_part in private_names:
        text = re.sub(re.escape(name_part), 'USER', text, flags=re.I)
    assert not re.search(r'(?i)(github_pat_[a-z0-9_]+|gh[pousr]_[a-z0-9]{20,}|sk-[a-zA-Z0-9]{24,})', text), name
    return text.encode('utf-16' if encoding == 'utf-16' else 'utf-8')

def safe_name(name):
    path = Path(name)
    assert not path.is_absolute() and '..' not in path.parts and ':' not in name and '\\' not in name, name
    return name

release = load(D / 'release.json')
candidate = load(H / 'candidate.json')
gate = load(B / 'feature_regression.json')
assert release['build'] == candidate['build'] == gate['build'] == BUILD
assert candidate['passed'] and gate['passed']
for category in ('source_sha256', 'evidence_sha256'):
    for name, digest in gate[category].items():
        assert sha((D / name).read_bytes()) == digest, name
for name, digest in candidate['binaries'].items():
    source = B / name if name not in {'README_ENG.txt', 'README_KOR.txt'} else D / name
    assert sha(source.read_bytes()) == digest, name
resuming = git('branch', '--show-current') == BRANCH
if not resuming:
    assert git('status', '--porcelain') == '', 'Public checkout must start clean.'
    assert git('branch', '--show-current') == 'main'
main_before = git('rev-parse', 'main')
assert load(P / 'release.json')['build'] == (BUILD if resuming else 2026101901)

sources = {}
excluded = []
with zipfile.ZipFile(H / 'baseline_1901_sources.zip') as baseline:
    assert len(baseline.infolist()) == 716
    for item in baseline.infolist():
        name = safe_name(item.filename)
        if item.is_dir():
            continue
        if name in {'VALIDATION.json', 'PUBLIC_SOURCE_SHA256.json'} or name.startswith('validation/') or (name.endswith('.zip') and name != 'Payload.zip'):
            excluded.append(name)
            continue
        assert Path(name).suffix.lower() not in BLOCKED, name
        sources[name] = baseline.read(item)

def add(path, name=None):
    name = safe_name(name or path.relative_to(D).as_posix())
    assert path.is_file(), str(path)
    assert Path(name).suffix.lower() not in BLOCKED, name
    sources[name] = public(path.read_bytes(), name)

# Only the reviewed installer-only changes and their build identity differ
# from the published baseline. All other native flight/render sources stay pinned.
override = [
    'src/PackCore.cs', 'src/Ui.cs', 'src/Setup.cs', 'release.json',
    'runtime/src/pack_identity.h', 'runtime/payload_manifest.json',
    'runtime/build/native_identity.json', 'tests/feature_regression_gate.py',
    'tests/debrief_1503/validate_replay.py',
]
for name in override:
    add(D / name)
for path in sorted(H.iterdir()):
    if path.is_file() and (path.suffix.lower() in CODE or path.name in {'READOUT.md', 'PREFLIGHT_DESIGN.md', 'PRERELEASE_NOTES.md'}):
        if path.name != 'publish_prerelease.py':
            add(path)
add(H / 'PRERELEASE_NOTES.md', 'RELEASE_NOTES.md')
# Retain the portable public builder rather than the private workspace builder.
add(P / 'build_pack.py', 'build_pack.py')
building = (P / 'BUILDING.md').read_bytes().replace(b'KoreanAIR_AC8_ModPack_2.2', b'KoreanAIR_AC8_ModPack_2.3')
sources['BUILDING.md'] = public(building, 'BUILDING.md')
sources['Payload.zip'] = (B / 'Payload.zip').read_bytes()
assert sha(sources['Payload.zip']) == candidate['binaries']['Payload.zip']

guide = '''# Diagnostic source snapshot: 2.3 b2026101902

This snapshot belongs to the installation-diagnostic prerelease, not the stable update channel. The owner authorized sharing it with an installation reporter. The reporter's underlying Windows restriction and installation success have not been confirmed; no personal gameplay test of this build is claimed.

The installer adds bounded create/write/rename preflight checks and failure diagnostics. It does not change user ACLs, security software, gameplay control calculations, graphics settings or rendering logic. The native source differs from stable b2026101901 only in its build identity; the supplied native binary and payload use b2026101902.

Use this archive's Payload.zip when rebuilding this snapshot. It is the exact verified redistributable payload associated with b2026101902 and contains the installable mod binaries. No game executable, individual test executable/DLL, private capture or nested historical source ZIP is included. Launcher/installer rebuilds may have different hashes because compilation is not guaranteed deterministic; the build metadata must remain consistent.

Run `python build_pack.py --payload-zip Payload.zip` on Windows with the documented compiler. See BUILDING.md. Native builds require the Visual Studio tools and included vendor source/dependencies. Owner-specific validation that requires a game executable or private capture is not fully reproducible from public materials.

Current installation tests are in tests/install_access_1902. The source-scope test reads a separate stable b2026101901 Sources.zip; download that release asset and place it at tests/install_access_1902/baseline_1901_sources.zip before running that comparison. Historical baseline ZIPs are intentionally not nested in this archive. Tests that require the owner-supplied HOTAS distribution need that separately obtained package.

Only fresh b2026101902 validation is included under validation/. Historical release approvals and old aggregate VALIDATION.json were removed. The new VALIDATION.json states the diagnostic scope and limits. Original validation source/binary hashes identify the private tested files; some public source or report text is anonymized, so its byte hash can differ. PUBLIC_SOURCE_SHA256.json hashes the public archive entries (excluding itself); PUBLIC_REPOSITORY_SHA256.json hashes the public Git snapshot entries (excluding itself). The original-local/public-critical source map appears in validation/public_source_map.json.

No stable promotion or automatic-update change is authorized by the preparation of this diagnostic snapshot. The stable b2026101901 release assets remain separate. A future stable replacement needs the owner's release instruction and a new internal build.
'''
sources['SOURCEGUIDE.md'] = guide.encode('utf-8')
fresh_reports = [
    'candidate.json', 'regression.json', 'diagnostic_gate.json', 'diagnostic_results.json',
    'atomic_write_results.json', 'product_access_validation.json', 'product_atomic_results.json',
    'product_preflight_results.json', 'final_setup_validation.json', 'final_setup_atomic_results.json',
    'local_installation.json', 'installed_verification.json',
]
for name in fresh_reports:
    add(H / name, 'validation/' + name)
add(B / 'feature_regression.json', 'validation/feature_regression.json')
reports = {}
stale_reports = []
for pattern, label in [('update_settings_*/results.json', 'settings'), ('update_handoff_*/results.json', 'handoff'), ('release_payload_*/results.json', 'payload')]:
    path = max((D / 'tests').glob(pattern), key=lambda p: p.stat().st_mtime_ns)
    report = load(path)
    assert report['passed'] and all(row['passed'] for row in report['checks']), label
    if any(sha((D / name).read_bytes()) != digest for name, digest in report['tested_source_sha256'].items()):
        stale_reports.append(label)
        continue
    if label == 'handoff':
        assert report['tested_binary_sha256']['setup'] == candidate['binaries']['KoreanAIR_AC8_ModPack_2.3_Setup.exe']
        assert report['tested_binary_sha256']['launcher'] == candidate['launcher_sha256']
    add(path, 'validation/' + label + '.json')
    reports[label] = len(report['checks'])

critical = override + ['src/Launcher.cs', 'src/UpdateCore.cs', 'src/SupportReport.cs']
source_map = {name: dict(original_local_sha256=sha((D / name).read_bytes()), public_sha256=sha(sources[name]), public_text_anonymized=sources[name] != (D / name).read_bytes()) for name in critical}
native_names = sorted(name for name in sources if name.startswith(('runtime/src/', 'runtime/scripts/')) and Path(name).suffix.lower() in CODE)
for name in native_names:
    assert sources[name] == public((D / name).read_bytes(), name), name
identity = load(D / 'runtime/build/native_identity.json')
assert identity['build'] == BUILD
validation = dict(passed=True, version='2.3', build=BUILD, scope='Owner-authorized diagnostic prerelease sharing only; not stable release approval.', owner_gameplay_tested=False, remote_installation_fixed_confirmed=False, stable_update_feed_changed=False, original_validated_candidate=candidate, installer_only_gameplay_calculation_unchanged=True, native_source_entries_verified=len(native_names), reports=reports, stale_reports_excluded=stale_reports, validation_limit='Synthetic and local settings-preserving installation checks. The remote Windows file restriction is not yet diagnosed. No anti-cheat bypass or security-permission override is added.')
sources['VALIDATION.json'] = public((json.dumps(validation, indent=2) + '\n').encode(), 'VALIDATION.json')
sources['validation/public_source_map.json'] = (json.dumps(source_map, indent=2) + '\n').encode()

# A second pass sanitizes inherited public-baseline text as well.
for name in list(sources):
    if name != 'Payload.zip':
        sources[name] = public(sources[name], name)

token = re.compile(r'(?i)(github_pat_[a-z0-9_]+|gh[pousr]_[a-z0-9]{20,}|sk-[a-zA-Z0-9]{24,})')
scan = dict(passed=True, text_entries_scanned=0, known_redistributable_payload_sha256=sha(sources['Payload.zip']), excluded_historical_entries=excluded, private_name_hits=[], token_hits=[], binary_or_capture_hits=[])
for name, data in sources.items():
    assert safe_name(name) == name
    if name == 'Payload.zip' or name in ASSETS:
        continue
    assert not name.endswith('.zip') and Path(name).suffix.lower() not in BLOCKED, name
    assert not any(part.startswith(('fixture_', 'diagnostic_fixture_', 'diagnostic_build_')) or part in {'fixtures', 'repress_build'} for part in Path(name).parts), name
    text = data.decode('utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    scan['text_entries_scanned'] += 1
    for identifier in private_names:
        if identifier.lower() in text.lower():
            scan['private_name_hits'].append(name)
    if token.search(text):
        scan['token_hits'].append(name)
assert not scan['private_name_hits'] and not scan['token_hits']
scan['public_critical_sources'] = source_map
sources['validation/privacy_scan.json'] = (json.dumps(scan, indent=2) + '\n').encode()
sources['PUBLIC_SOURCE_SHA256.json'] = (json.dumps({name: sha(data) for name, data in sorted(sources.items())}, indent=2) + '\n').encode()
source_zip = H / SOURCE_NAME
with zipfile.ZipFile(source_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name, data in sorted(sources.items()):
        archive.writestr(name, data)
with zipfile.ZipFile(source_zip) as archive:
    assert archive.testzip() is None
    checksums = json.loads(archive.read('PUBLIC_SOURCE_SHA256.json'))
    assert len(checksums) + 1 == len(archive.infolist())
    for name, digest in checksums.items():
        assert sha(archive.read(name)) == digest, name

if not resuming:
    git('switch', '-c', BRANCH)
tracked = set(git('ls-files').splitlines())
repo_names = set(override) | {'SOURCEGUIDE.md', 'RELEASE_NOTES.md', 'BUILDING.md'}
repo_names |= {name for name in sources if name.startswith('tests/install_access_1902/') and Path(name).suffix.lower() in CODE}
# Keep the source commit reviewable: no reports, archives, assets or binaries.
for name in sorted(repo_names):
    target = P / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(sources[name])
forced = {name for name in repo_names if name.startswith('runtime/')}
git('add', '--', *sorted(repo_names - forced))
git('add', '-f', '--', *sorted(forced))
# Hash the Git index bytes, since this Windows checkout may normalize CRLF.
index_rows = [line.split(None, 3) for line in git('ls-files', '--stage').splitlines()]
repo_map = {}
for _, object_id, _, name in index_rows:
    if name == 'PUBLIC_REPOSITORY_SHA256.json':
        continue
    data = subprocess.check_output(['git', '-C', str(P), 'cat-file', 'blob', object_id])
    repo_map[name] = sha(data)
(P / 'PUBLIC_REPOSITORY_SHA256.json').write_text(json.dumps(repo_map, indent=2) + '\n', encoding='utf-8')
repo_names.add('PUBLIC_REPOSITORY_SHA256.json')
git('add', '--', 'PUBLIC_REPOSITORY_SHA256.json')
git('diff', '--cached', '--check')
diff_stat = git('diff', '--cached', '--stat')
diff_names = git('diff', '--cached', '--name-only').splitlines()
for name in diff_names:
    assert Path(name).suffix.lower() not in BLOCKED and not name.endswith('.zip'), name
    data = (P / name).read_bytes()
    text = data.decode('utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    assert not token.search(text) and not any(identifier.lower() in text.lower() for identifier in private_names), name
environment = os.environ.copy()
for role in ('AUTHOR', 'COMMITTER'):
    environment['GIT_' + role + '_NAME'] = 'KoreanAIR'
    environment['GIT_' + role + '_EMAIL'] = '290084614+KoreanAirline@users.noreply.github.com'
git('commit', '-m', 'Prepare installation diagnostic prerelease 2.3 b2026101902', env=environment)
commit = git('rev-parse', 'HEAD')
assert git('rev-parse', 'main') == main_before
assert git('status', '--porcelain') == ''
proof = dict(passed=True, version='2.3', build=BUILD, branch=BRANCH, commit=commit, main_commit_unchanged=main_before, source_zip=SOURCE_NAME, source_zip_sha256=sha(source_zip.read_bytes()), source_entries=len(sources), source_archive_crc_verified=True, public_source_checksums_verified=True, native_source_entries_verified=len(native_names), payload_sha256=sha(sources['Payload.zip']), public_critical_source_map=source_map, privacy_scan_passed=True, private_name_hits=[], token_hits=[], staged_files=diff_names, local_diff_stat=diff_stat, anonymous_author=git('log', '-1', '--format=%an <%ae>'), anonymous_committer=git('log', '-1', '--format=%cn <%ce>'), pushed=False, published=False)
(H / 'prerelease_source_prepared.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
(H / 'prerelease_source_scan.json').write_text(json.dumps(scan, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: proof[key] for key in ('passed', 'build', 'branch', 'commit', 'main_commit_unchanged', 'source_zip', 'source_zip_sha256', 'source_entries', 'native_source_entries_verified', 'pushed', 'published')}, indent=2))
print(diff_stat)
