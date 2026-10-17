"""Publish a hash-verified draft only after current-candidate owner approval."""
from pathlib import Path
import hashlib
import json
import subprocess
import urllib.request
from release_authorization_1701 import release_authorized
from prepare_release_1701 import check_source_map

H = Path(__file__).resolve().parent
D = H.parents[1]
GH = D.parents[1] / 'work/tools/gh/gh.exe'
REPO, TAG, BUILD = 'KoreanAirline/KoreanAIR-AC8-ModPack', 'v2.3-b2026101701', 2026101701
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))


def gh(*args):
    result = subprocess.run([str(GH), *map(str, args)], capture_output=True, text=True, encoding='utf-8', errors='replace')
    assert result.returncode == 0, result.stderr[:1200]
    return result.stdout


def read_public(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'KoreanAIR-ReleaseVerification'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def verify_assets(release, expected):
    assert len(release['assets']) == 6 and {a['name'] for a in release['assets']} == set(expected)
    for asset in release['assets']:
        proof = expected[asset['name']]
        assert asset['state'] == 'uploaded' and asset['size'] == proof['size'] and asset['digest'] == 'sha256:' + proof['sha256'], asset['name']


def main():
    proof = load(H / 'draft_release_verified_1701.json')
    approval, candidate = load(D / 'tests/owner_release_approval_1701.json'), load(H / 'candidate.json')
    assert proof['passed'] and proof['tag'] == TAG and proof['build'] == BUILD
    assert release_authorized(approval, candidate['tested_binary_sha256'])
    assert approval['build'] == BUILD and approval['version'] == '2.3' and approval['approved_binary_sha256'] == candidate['tested_binary_sha256']
    assert sha(D / 'tests/owner_release_approval_1701.json') == proof['owner_approval_sha256'] and sha(H / 'candidate.json') == proof['candidate_sha256']
    gate = load(D / 'build/feature_regression.json')
    assert gate['passed'] and (gate['version'], gate['build']) == ('2.3', BUILD)
    check_source_map(gate['source_sha256'])
    check_source_map(gate['evidence_sha256'])
    expected = {a['name']: a for a in proof['assets']}
    draft = json.loads(gh('api', 'repos/' + REPO + '/releases/' + str(proof['release_id'])))
    assert draft['tag_name'] == TAG and draft['draft'] and not draft['prerelease'], 'Only the verified unpublished draft may be published.'
    verify_assets(draft, expected)
    request = H / 'publish_request_1701.json'
    request.write_text(json.dumps(dict(draft=False, make_latest='true')), encoding='utf-8')
    released = json.loads(gh('api', 'repos/' + REPO + '/releases/' + str(proof['release_id']), '-X', 'PATCH', '--input', request))
    assert released['tag_name'] == TAG and not released['draft'] and not released['prerelease']
    latest = json.loads(gh('api', 'repos/' + REPO + '/releases/latest'))
    assert latest['tag_name'] == TAG
    verify_assets(latest, expected)
    update_asset = next(a for a in latest['assets'] if a['name'] == 'update.json')
    setup_asset = next(a for a in latest['assets'] if a['name'] == 'KoreanAIR_AC8_ModPack_2.3_Setup.exe')
    body = read_public(update_asset['browser_download_url'])
    assert hashlib.sha256(body).hexdigest() == expected['update.json']['sha256']
    feed = json.loads(body)
    assert feed['tag'] == TAG and feed['version'] == '2.3' and feed['build'] == BUILD and feed['sha256'] == expected[setup_asset['name']]['sha256']
    downloaded = read_public(setup_asset['browser_download_url'])
    assert hashlib.sha256(downloaded).hexdigest() == feed['sha256'] and len(downloaded) == feed['size']
    report = dict(published=True, version='2.3', build=BUILD, url=latest['html_url'], tag=TAG, commit=proof['commit'], release_id=latest['id'], assets=proof['assets'], owner_tested_current_build=approval.get('owner_tested_current_build') is True, owner_no_problems_confirmed=approval.get('no_problems_confirmed') is True, owner_explicitly_waived_current_build_test=approval.get('owner_explicitly_waived_current_build_test') is True, owner_release_approved=True, exact_validated_binaries_preserved=True, latest_verified=True, public_update_feed_download_verified=True, public_standalone_setup_download_verified=True, settings_preserved=True, remote_weave_fixed_confirmed=False, hotas_gameplay_verified=False)
    (D / 'tests/release_1701_complete.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (H / 'public_update_feed_1701.json').write_text(json.dumps(feed, indent=2) + '\n', encoding='utf-8')
    candidate['published'], candidate['release_url'] = True, latest['html_url']
    (H / 'candidate.json').write_text(json.dumps(candidate, indent=2) + '\n', encoding='utf-8')
    print('PASS published latest; verified public update feed and standalone Setup: ' + latest['html_url'])


if __name__ == '__main__':
    main()
