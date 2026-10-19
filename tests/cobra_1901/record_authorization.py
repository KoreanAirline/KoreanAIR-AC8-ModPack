"""Record the owner's current conditional fix-and-reupload request honestly."""
from pathlib import Path
import hashlib,json
from release_authorization_1901 import REGRESSION_CONDITION,release_authorized
H=Path(__file__).resolve().parent;D=H.parents[1]
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
c=load(H/'candidate.json');g=load(D/'build/feature_regression.json')
r=load(H/'regression.json');p=load(H/'repress_evidence.json')
assert all(x['passed'] for x in (c,g,r,p))
assert p['native_replay']['baseline']['native_modes']==[0,0]
assert p['native_replay']['current']['native_modes']==[0,2]
assert r['only_native_player_maneuver_repress_changed_from1701'] is True
assert all(c['local_installation'][k] for k in ('personal_settings_unchanged','graphics_settings_unchanged','ui_language_unchanged','selected_modules_unchanged','suspended_state_unchanged'))
approval=dict(version='2.3',build=2026101901,release_approved=True,
 owner_tested_current_build=False,no_problems_confirmed=False,
 owner_authorized_conditional_bugfix_release=True,
 authorization_mode='conditional_fix_and_reupload',exception_applies_to_build=2026101901,
 reproduced_input_edge_confirmed=True,regression_review_passed=True,
 regression_condition=REGRESSION_CONDITION,
 latest_owner_authorization='코브라 기동 발동이 안된다는(shift ctrl 누르고 s키가 안먹힌다는)제보가 있는데 진짜인지 설마 버그가 회귀한건지 검사해줘 문제가 맞다면 수정해서 재업로드해',
 latest_owner_clarification='그냥 안된다고 해서 너가 보기에 모드 수정하다가 회귀시킨게 없는지를 봐봐',
 authorization_scope='Current conditional bug-fix request only. A distinct existing input timing defect was reproduced and corrected. The reporter-specific cause is not known and no personal owner playtest is claimed. Standing approval rules remain unchanged for later builds.',
 approved_binary_sha256=c['tested_binary_sha256'],candidate_sha256=sha(H/'candidate.json'),
 regression_gate_sha256=sha(D/'build/feature_regression.json'),
 reproduced_edge_evidence_sha256=sha(H/'repress_evidence.json'),
 cobra_report_root_cause_confirmed=False,cobra_gameplay_verified=False)
assert release_authorized(approval,c['tested_binary_sha256'])
(D/'tests/owner_release_approval_1901.json').write_text(json.dumps(approval,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('PASS exact-build conditional bug-fix authorization recorded; no personal playtest claimed.')
