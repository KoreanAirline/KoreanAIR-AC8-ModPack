"""Package a local candidate. Public staging separately requires exact-build approval."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import zipfile
from release_authorization_1701 import release_authorized

H = Path(__file__).resolve().parent
D = H.parents[1]
B, T, P, O = D / 'build', D / 'tests', D.parent / 'ac8-github-public', D.parents[1] / 'outputs'
VERSION, BUILD = '2.3', 2026101701
BRAND, TAG = 'KoreanAIR_AC8_ModPack_2.3', 'v2.3-b2026101701'
TEXT_EXT = {'.py', '.cpp', '.c', '.h', '.hpp', '.cs', '.json', '.md', '.txt', '.ini', '.cmd', '.ps1', '.lua', '.asm', '.def', '.yml', '.yaml', '.xml', '.inc'}
BINARY_EXT = {'.pak', '.ucas', '.utoc', '.pyc', '.dll', '.exe', '.obj', '.pdb', '.lib', '.dmp', '.etl'}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))


def exact_approval(approval, hashes):
    assert release_authorized(approval, hashes), 'Exact current binaries need owner approval, with a playtest or an explicit one-time test waiver.'


def public(data, name):
    if name.lower().endswith('.zip'):
        buf = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as out:
            for entry in src.infolist():
                n = entry.filename
                assert not Path(n).is_absolute() and '..' not in Path(n).parts, n
                assert Path(n).name.lower() not in {'acecombat8.exe', 'start_protected_game.exe'}, n
                if entry.is_dir() or Path(n).suffix.lower() in BINARY_EXT:
                    continue
                out.writestr(n, public(src.read(entry), n))
        return buf.getvalue()
    if Path(name).suffix.lower() not in TEXT_EXT:
        return data
    encoding = 'utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    text = data.decode(encoding)
    text = re.sub(r'(?i)([A-Z]:[/\\]+Users[/\\]+)[^/\\\r\n"<>]+(?=[/\\])', lambda m: m[1] + 'USER', text)
    text = text.replace('USER', 'USER').replace('USER', 'USER').replace('USER', 'USER')
    assert not re.search(r'(?i)(github_pat_[a-z0-9_]+|gh[pousr]_[a-z0-9]{20,}|sk-[a-zA-Z0-9]{24,})', text), name
    return text.encode('utf-16' if encoding == 'utf-16' else 'utf-8')


def check_source_map(mapping):
    for rel, expected in mapping.items():
        assert sha(D / rel) == expected, rel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage-public', action='store_true', help='Also stage public source; requires exact current-build owner approval or explicit conditional test waiver.')
    args = parser.parse_args()
    release, approval = load(D / 'release.json'), load(T / 'owner_release_approval_1701.json')
    candidate, gate, installed = load(H / 'candidate.json'), load(B / 'feature_regression.json'), load(T / 'local_candidate_1701_installed.json')
    for record in (release, candidate, gate, installed, approval):
        assert (record['version'], record['build']) == (VERSION, BUILD)
    assert candidate['passed'] and gate['passed'] and installed['passed']
    regression = load(H / 'regression.json')
    assert regression['passed'] and regression['flight_implementation_unchanged_from1608'] is True
    assert regression['remote_weave_fixed_confirmed'] is False
    assert candidate['remote_weave_fixed_confirmed'] is False and candidate['hotas_gameplay_verified'] is False
    for field in ('graphics_settings_unchanged', 'ui_language_unchanged', 'personal_settings_unchanged', 'selected_modules_unchanged', 'suspended_state_unchanged'):
        assert installed[field] is True, field
    check_source_map(gate['source_sha256'])
    check_source_map(gate['evidence_sha256'])
    binaries = dict(setup=B / (BRAND + '_Setup.exe'), launcher=B / (BRAND + '.exe'), native=D / 'runtime/scripts/ac8_mouse_aim_010.dll', payload=B / 'Payload.zip')
    hashes = {key: sha(path) for key, path in binaries.items()}
    assert candidate['tested_binary_sha256'] == hashes
    if args.stage_public:
        exact_approval(approval, hashes)
    reports = {}
    for pattern, key in [('update_settings_*/results.json', 'settings'), ('update_handoff_*/results.json', 'handoff'), ('release_payload_*/results.json', 'payload')]:
        path = max(T.glob(pattern), key=lambda p: p.stat().st_mtime_ns)
        report = load(path)
        assert report['passed'] and all(c['passed'] for c in report['checks']), key
        check_source_map(report['tested_source_sha256'])
        reports[key] = path, report
    for key in ('setup', 'launcher'):
        assert reports['handoff'][1]['tested_binary_sha256'][key] == hashes[key], key
    update = dict(schema=1, version=VERSION, build=BUILD, tag=TAG, installer=BRAND + '_Setup.exe', sha256=hashes['setup'], size=binaries['setup'].stat().st_size)
    (B / 'update.json').write_text(json.dumps(update, indent=2) + '\n', encoding='utf-8')
    actual_report = load(H / 'actual_installed_support.json')
    assert actual_report['passed'] and actual_report['settings_unchanged'] and actual_report['critical_files_match']
    assert (actual_report['version'], actual_report['build']) == (VERSION, BUILD)
    validation = dict(version=VERSION, build=BUILD, passed=True, owner_tested_current_build=approval.get('owner_tested_current_build') is True, public_release_authorized=release_authorized(approval, hashes), owner_explicitly_waived_current_build_test=approval.get('owner_explicitly_waived_current_build_test') is True, tested_binary_sha256=hashes, checks={k: len(r['checks']) for k, (_, r) in reports.items()}, settings_preservation=installed, feature_gate=gate, candidate=candidate, actual_installed_report=actual_report, monitor_retry=load(H / 'display_retry_regression.json'), remote_weave_fixed_confirmed=False, hotas_gameplay_verified=False, validation_limit='Automated source-bound regression and settings-preserving local installation. The owner explicitly waived a new playtest for this exact build, conditional on no detected regression. Existing1608 flight calculation is unchanged. Remote stationary-target weaving and combined in-game HOTAS operation remain unverified. No FPS improvement or scene-stall cure is claimed. Graphics, DLSS Quality and frame-generation preferences remain unchanged. The source-bound release.json change_type retains feature_local_candidate because approved binaries are never rebuilt for publication.')
    (H / 'release_validation_1701.json').write_text(json.dumps(validation, indent=2) + '\n', encoding='utf-8')
    sources = {}

    def add(path, name=None):
        if path.is_file():
            name = name or path.relative_to(D).as_posix()
            sources[name] = public(path.read_bytes(), name)

    for folder in ('src', 'licenses', 'assets', 'campaign-source', 'runtime/src', 'runtime/include', 'runtime/scripts', 'runtime/test_fixtures'):
        for path in (D / folder).rglob('*'):
            if path.is_file() and path.suffix.lower() not in BINARY_EXT and path.name not in {'Quality.cs', 'performance.lua'}:
                add(path)
    for path in (D / 'runtime').glob('*'):
        if path.is_file() and path.suffix.lower() in TEXT_EXT and path.name not in {'performance.ini', 'performance_test.lua', 'perf_readonly_audit.py', 'perf_readonly_audit.json'}:
            add(path)
    for path in (D / 'campaign-loader').glob('*'):
        if path.is_file() and path.suffix.lower() in TEXT_EXT:
            add(path)
            if path.name == 'build.cmd':
                sources['campaign-loader/build.cmd'] = sources['campaign-loader/build.cmd'].replace(b'..\\..\\ac8-mouseflight\\package\\src\\vendor\\minhook', b'..\\runtime\\src\\vendor\\minhook')
    for path in T.glob('*'):
        if path.is_file() and path.suffix.lower() in {'.py', '.cs', '.ps1', '.asm', '.cpp', '.h'} and not path.name.startswith(('prepare_1204', 'refresh_1204', 'InstallCandidate')):
            add(path)
    folders = ['target_selection_1502', 'alt_manual_1503', 'debrief_1503', 'overlay_cadence_1503', 'candidate_1504', 'candidate_1505', 'candidate_1506', 'ultrawide_1507', 'aim_jitter_audit', 'native_launcher_identity_1503', 'focus_1508', 'scene_1509', 'render_1510', 'render_1511', 'stretch_1603', 'stretch_1604', 'focus_1606', 'focus_1607', 'transition_1608', 'support_1701', 'hotas_1701']
    for folder in folders:
        for path in (T / folder).rglob('*'):
            if path.is_file() and path.suffix.lower() in {'.py', '.cpp', '.cs', '.h', '.asm', '.lua', '.inc'} and path.stat().st_size < 2000000 and not any(part.endswith('_fixture') or part == 'fixtures' or part.startswith('fixtures_') for part in path.relative_to(T / folder).parts):
                add(path)
        for path in (T / folder).glob('*sources.zip'):
            add(path)
    add(H / 'monitor_cases.json')
    # Tiny pinned code signatures are test inputs, not private live captures.
    add(T / 'focus_1607/input_pins.json')
    for name in ('AGENTS.md', 'release.json', 'RELEASE_NOTES.md', 'README_ENG.txt', 'README_KOR.txt'):
        add(D / name)
    # The owner's feature descriptions are preserved verbatim apart from path redaction.
    for name in ('BUILDING.md', 'LICENSE', 'README.md'):
        add(P / name, name)
    sources['README.md'] = public((H / 'public_README_1701.md').read_bytes(), 'README.md')
    add(P / 'build_pack.py', 'build_pack.py')
    public_build = sources['build_pack.py'].decode('utf-8')
    if "'SupportReport.cs'" not in public_build:
        public_build = public_build.replace("'MouseInputWorker.cs'))", "'MouseInputWorker.cs','SupportReport.cs'))")
    assert "'SupportReport.cs'" in public_build, 'Public installer rebuild must include the report collector.'
    sources['build_pack.py'] = public_build.encode('utf-8')
    for key, (path, _) in reports.items():
        add(path, 'validation/' + key + '.json')
    add(T / 'owner_release_approval_1701.json', 'validation/owner_release_approval.json')
    add(H / 'release_validation_1701.json', 'VALIDATION.json')
    add(D / 'runtime/build/native_identity.json')
    for name in ('regression.json', 'monitor_regression.json', 'monitor_ui_regression.json', 'display_retry_regression.json', 'capture_regression.json', 'report_results.json', 'candidate.json', 'actual_installed_support.json'):
        add(H / name, 'validation/' + name)
    add(T / 'hotas_1701/core_regression.json', 'validation/hotas_core_regression.json')
    # This is the unchanged redistributable mod payload, not a private game/capture archive.
    sources['Payload.zip'] = binaries['payload'].read_bytes()
    sources['BUILDING.txt'] = b'Build launcher/installer: python build_pack.py --payload-zip Payload.zip. See BUILDING.md.\nNative runtime source, Lua, campaign loader and translation inputs are included.\nFull owner validation requires a pinned game executable and private live captures, which are not redistributed.\nPublic source entries are anonymized; private validation hashes refer to original local inputs.\n'
    sources['PUBLIC_SOURCE_SHA256.json'] = json.dumps({n: hashlib.sha256(data).hexdigest() for n, data in sorted(sources.items())}, indent=2).encode() + b'\n'
    with zipfile.ZipFile(B / (BRAND + '_Sources.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(sources.items()):
            z.writestr(name, data)
    with zipfile.ZipFile(B / (BRAND + '.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for path in (binaries['setup'], binaries['payload'], D / 'README_ENG.txt', D / 'README_KOR.txt', B / 'update.json'):
            z.write(path, path.name)
        z.writestr('SHA256.txt', hashes['setup'] + '  ' + BRAND + '_Setup.exe\n' + hashes['payload'] + '  Payload.zip\n')
    O.mkdir(exist_ok=True)
    for path in (B / (BRAND + '.zip'), B / (BRAND + '_Sources.zip')):
        shutil.copy2(path, O / path.name)
    assets = [binaries['setup'], binaries['payload'], B / 'update.json', O / (BRAND + '.zip'), O / (BRAND + '_Sources.zip')]
    (B / 'SHA256.txt').write_text(''.join(sha(path) + '  ' + path.name + '\n' for path in assets), encoding='utf-8')
    report = dict(tag=TAG, version=VERSION, build=BUILD, source_entries=len(sources), exact_validated_binaries_preserved=True, public_repository_staged=args.stage_public, public_release_authorized=validation['public_release_authorized'], assets={p.name: dict(size=p.stat().st_size, sha256=sha(p)) for p in assets + [B / 'SHA256.txt']})
    (H / 'release_assets_1701.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if args.stage_public:
        tracked = set(subprocess.check_output(['git', '-C', str(P), 'ls-files'], text=True).splitlines())
        added = {'SideButtonUiAudit.cs', 'test_side_buttons_ui.py', 'InvokeSideButtonUiAudit.ps1', 'UpdateHandoffProcess.cs', 'UpdateSettingsAudit.cs', 'test_update_settings.py', 'test_update_handoff.py'}
        for name, data in sources.items():
            if name.startswith(('src/', 'licenses/', 'assets/', 'runtime/src/', 'runtime/include/', 'runtime/scripts/')) or name in {'AGENTS.md', 'release.json', 'RELEASE_NOTES.md', 'README.md', 'README_ENG.txt', 'README_KOR.txt', 'build_pack.py'} or (name.startswith('tests/') and (name in tracked or Path(name).name in added or name.startswith(('tests/support_1701/', 'tests/hotas_1701/')))):
                target = P / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
    print(json.dumps(dict(tag=TAG, source_entries=len(sources), assets=list(report['assets']), checks=validation['checks'], public_repository_staged=args.stage_public, public_release_authorized=validation['public_release_authorized'])))


if __name__ == '__main__':
    main()
