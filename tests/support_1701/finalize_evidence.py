"""Bind the latest explicit one-build owner waiver to the verified local files."""
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
installation = load(D / 'tests/local_candidate_1701_installed.json')
support = load(H / 'actual_installed_support.json')
assert all(r['passed'] and (r['version'], r['build']) == ('2.3', 2026101701)
           for r in (candidate, gate, installation, support))
assert all(installation[k] for k in ('personal_settings_unchanged',
    'graphics_settings_unchanged', 'ui_language_unchanged',
    'selected_modules_unchanged', 'suspended_state_unchanged'))
for name, expected in {**gate['source_sha256'], **gate['evidence_sha256']}.items():
    assert sha(D / name) == expected, name
installed = Path('E:/SteamLibrary/steamapps/common/ACE COMBAT 8')
for source, target in (
    (B / 'KoreanAIR_AC8_ModPack_2.3.exe', installed / 'KoreanAIR_AC8_ModPack_2.3.exe'),
    (D / 'runtime/scripts/ac8_mouse_aim_010.dll', installed / 'Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/scripts/ac8_mouse_aim_010.dll'),
):
    assert sha(source) == sha(target), target.name
candidate['local_installation'] = installation
candidate['actual_installed_support_verification'] = support
(H / 'candidate.json').write_text(json.dumps(candidate, indent=2) + '\n', encoding='utf-8')
approval = dict(
    version='2.3', build=2026101701,
    release_approved=True, owner_tested_current_build=False,
    no_problems_confirmed=False,
    owner_explicitly_waived_current_build_test=True,
    exception_applies_to_build=2026101701,
    regression_review_passed=True,
    regression_condition='No detected regression from published2.2 b2026101608; flight implementation preserved.',
    latest_owner_authorization='그냥 깃허브 올려줘 적어도 전 버전보다 악화되는거 아니면',
    authorization_scope='This build only. The owner explicitly requested publication without another personal playtest, conditional on regression validation. The standing owner-test policy remains unchanged for later builds.',
    approved_binary_sha256=candidate['tested_binary_sha256'],
    regression_gate_sha256=sha(B / 'feature_regression.json'),
    candidate_sha256=sha(H / 'candidate.json'),
    no_regression_evidence='Current automated feature gate passed; production flight calculations remain identical to published 2.2 b2026101608 after removal of passive support capture and display-topology notifications. Settings-preserving installation verified on owner PC.',
    validation_limits='No new owner flight test; remote weaving root cause and combined HOTAS gameplay remain unconfirmed. No blanket crash-free or FPS claim.',
)
(D / 'tests/owner_release_approval_1701.json').write_text(json.dumps(approval, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('PASS exact local install, unchanged settings and one-build owner release waiver recorded.')
