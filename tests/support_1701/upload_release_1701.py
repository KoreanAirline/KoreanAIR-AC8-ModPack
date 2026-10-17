"""Create a new draft only after exact candidate owner approval. Never overwrite assets."""
from pathlib import Path
import hashlib
import json
import subprocess
from release_authorization_1701 import release_authorized
from prepare_release_1701 import check_source_map

H = Path(__file__).resolve().parent
D = H.parents[1]
W, B, P = D.parents[1], D / 'build', D.parent / 'ac8-github-public'
O, GH = W / 'outputs', W / 'work/tools/gh/gh.exe'
REPO, TAG, BRAND, BUILD = 'KoreanAirline/KoreanAIR-AC8-ModPack', 'v2.3-b2026101701', 'KoreanAIR_AC8_ModPack_2.3', 2026101701
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))


def gh(*args):
    result = subprocess.run([str(GH), *map(str, args)], capture_output=True, text=True, encoding='utf-8', errors='replace')
    assert result.returncode == 0, result.stderr[:1200]
    return result.stdout


def main():
    approval, candidate, packaged = load(D / 'tests/owner_release_approval_1701.json'), load(H / 'candidate.json'), load(H / 'release_assets_1701.json')
    assert approval.get('version') == '2.3' and approval.get('build') == BUILD
    assert release_authorized(approval, candidate['tested_binary_sha256']), 'Exact current binaries need explicit owner release approval.'
    assert approval['approved_binary_sha256'] == candidate['tested_binary_sha256']
    assert candidate['passed'] and candidate['build'] == BUILD and packaged['public_repository_staged'] and packaged['public_release_authorized']
    gate = load(B / 'feature_regression.json')
    assert gate['passed'] and (gate['version'], gate['build']) == ('2.3', BUILD)
    check_source_map(gate['source_sha256'])
    check_source_map(gate['evidence_sha256'])
    regression = load(H / 'regression.json')
    assert regression['passed'] and regression['flight_implementation_unchanged_from1608'] is True
    for key, path in dict(setup=B / (BRAND + '_Setup.exe'), launcher=B / (BRAND + '.exe'), native=D / 'runtime/scripts/ac8_mouse_aim_010.dll', payload=B / 'Payload.zip').items():
        assert sha(path) == approval['approved_binary_sha256'][key], key
    assets = [B / (BRAND + '_Setup.exe'), B / 'Payload.zip', B / 'update.json', O / (BRAND + '.zip'), O / (BRAND + '_Sources.zip'), B / 'SHA256.txt']
    assert len(packaged['assets']) == 6
    for path in assets:
        assert packaged['assets'][path.name] == dict(size=path.stat().st_size, sha256=sha(path)), path.name
    prior = json.loads(gh('api', '--paginate', '--slurp', 'repos/' + REPO + '/releases?per_page=100'))
    assert not any(release['tag_name'] == TAG for page in prior for release in page), 'Do not overwrite an existing release.'
    tag_check = subprocess.run([str(GH), 'api', 'repos/' + REPO + '/git/ref/tags/' + TAG], capture_output=True, text=True, encoding='utf-8', errors='replace')
    assert tag_check.returncode != 0 and '404' in tag_check.stderr, 'Existing tag or unavailable tag check; refuse release creation.'
    assert not subprocess.check_output(['git', '-C', str(P), 'status', '--porcelain'], text=True).strip(), 'Commit the staged public source first.'
    local_commit = subprocess.check_output(['git', '-C', str(P), 'rev-parse', 'HEAD'], text=True).strip()
    commit = json.loads(gh('api', 'repos/' + REPO + '/git/ref/heads/main'))['object']['sha']
    assert local_commit == commit, 'Push the reviewed public source commit first.'
    print(gh('release', 'create', TAG, *assets, '--repo', REPO, '--draft', '--target', commit, '--title', 'KoreanAIR AC8 Mod Pack 2.3', '--notes-file', D / 'RELEASE_NOTES.md').strip(), flush=True)
    pages = json.loads(gh('api', '--paginate', '--slurp', 'repos/' + REPO + '/releases?per_page=100'))
    release = next(r for page in pages for r in page if r['tag_name'] == TAG)
    assert release['draft'] and len(release['assets']) == 6
    local, verified = {p.name: p for p in assets}, []
    assert {a['name'] for a in release['assets']} == set(local)
    for asset in release['assets']:
        path = local[asset['name']]
        assert asset['state'] == 'uploaded' and asset['size'] == path.stat().st_size and asset['digest'] == 'sha256:' + sha(path), path.name
        verified.append(dict(name=asset['name'], size=asset['size'], sha256=sha(path), github_digest=asset['digest'], matched=True))
    proof = dict(passed=True, tag=TAG, version='2.3', build=BUILD, commit=commit, release_id=release['id'], owner_tested_current_build=approval.get('owner_tested_current_build') is True, no_problems_confirmed=approval.get('no_problems_confirmed') is True, owner_explicitly_waived_current_build_test=approval.get('owner_explicitly_waived_current_build_test') is True, release_approved=True, owner_approval_sha256=sha(D / 'tests/owner_release_approval_1701.json'), candidate_sha256=sha(H / 'candidate.json'), assets=verified)
    (H / 'draft_release_verified_1701.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print('PASS draft uploaded; all six GitHub asset digests match exact owner-approved binaries.', flush=True)


if __name__ == '__main__':
    main()
