"""Verify the exact local candidate; attach installation evidence without inventing an owner playtest."""
from pathlib import Path
import hashlib
import json

H = Path(__file__).resolve().parent
D = H.parents[1]
B = D / 'build'
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
candidate = load(H / 'candidate.json')
gate = load(B / 'feature_regression.json')
installation = load(D / 'tests/local_candidate_1901_installed.json')
support = load(H / 'actual_installed_support.json')
regression = load(H / 'regression.json')
assert all(r['passed'] and (r['version'], r['build']) == ('2.3', 2026101901)
           for r in (candidate, gate, installation, support, regression))
assert regression['only_native_player_maneuver_repress_changed_from1701'] is True
assert regression['cobra_report_root_cause_confirmed'] is False and regression['cobra_gameplay_verified'] is False
assert all(installation[k] for k in ('personal_settings_unchanged',
    'graphics_settings_unchanged', 'ui_language_unchanged',
    'selected_modules_unchanged', 'suspended_state_unchanged'))
for name, expected in {**gate['source_sha256'], **gate['evidence_sha256']}.items():
    assert sha(D / name) == expected, name
binaries = dict(setup=B / 'KoreanAIR_AC8_ModPack_2.3_Setup.exe', launcher=B / 'KoreanAIR_AC8_ModPack_2.3.exe', native=D / 'runtime/scripts/ac8_mouse_aim_010.dll', payload=B / 'Payload.zip')
assert candidate['tested_binary_sha256'] == {k: sha(v) for k, v in binaries.items()}
installed = Path('E:/SteamLibrary/steamapps/common/ACE COMBAT 8')
for source, target in (
    (binaries['launcher'], installed / 'KoreanAIR_AC8_ModPack_2.3.exe'),
    (binaries['native'], installed / 'Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/scripts/ac8_mouse_aim_010.dll'),
):
    assert sha(source) == sha(target), target.name
candidate['local_installation'] = installation
candidate['actual_installed_support_verification'] = support
assert candidate['owner_gameplay_tested'] is False
assert candidate['cobra_report_root_cause_confirmed'] is False and candidate['cobra_gameplay_verified'] is False
(H / 'candidate.json').write_text(json.dumps(candidate, indent=2) + '\n', encoding='utf-8')
print('PASS exact local install, unchanged settings and synthetic regression evidence; no owner playtest claimed. Record the exact-build owner authorization after this step.')
