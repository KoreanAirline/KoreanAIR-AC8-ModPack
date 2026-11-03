"""Exercise the production loader freshness gate using isolated file copies."""
from pathlib import Path
import ast,hashlib,json,shutil,tempfile

D=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tree=ast.parse((D/'build_pack.py').read_text(encoding='utf-8-sig'))
function=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='verified_campaign_loader')
scope={'json':json,'native_sha':sha}
exec(compile(ast.Module(body=[function],type_ignores=[]),str(D/'build_pack.py'),'exec'),scope)
check=scope['verified_campaign_loader']
identity=json.loads((D/'campaign-loader/build/loader_identity.json').read_text(encoding='utf-8'))
release=json.loads((D/'release.json').read_text(encoding='utf-8-sig'))
results=[]
def passed(name):results.append({'test':name,'passed':True})
def rejected(name,callback):
    try:callback()
    except(AssertionError,FileNotFoundError):passed(name)
    else:raise AssertionError('Did not reject: '+name)

with tempfile.TemporaryDirectory(prefix='ac8_campaign_gate_')as temporary:
    F=Path(temporary)
    files=list(identity['source_sha256'])+['campaign-loader/build/loader_identity.json','campaign-loader/build/dinput8.dll','campaign-loader/ABI_AND_GUARDS.json','campaign-source/rebuilt.pak']
    files+=['campaign-loader/build/'+name for name in identity['test_sha256']]
    for rel in files:
        target=F/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(D/rel,target)
    assert check(F,release)==F/'campaign-loader/build/dinput8.dll';passed('current verified loader accepted')
    for rel,name in [('campaign-loader/campaign_policy.h','changed guard source rejected'),
                     ('runtime/src/vendor/minhook/include/MinHook.h','changed dependency source rejected'),
                     ('campaign-loader/build/dinput8.dll','changed loader DLL rejected'),
                     ('campaign-loader/ABI_AND_GUARDS.json','changed ABI evidence rejected'),
                     ('campaign-source/rebuilt.pak','changed approved PAK rejected'),
                     ('campaign-loader/build/policy_tests.txt','changed policy test evidence rejected')]:
        target=F/rel;original=target.read_bytes();target.write_bytes(original+b'\n')
        rejected(name,lambda:check(F,release));target.write_bytes(original)
    rejected('wrong release build rejected',lambda:check(F,dict(release,build=release['build']+1)))
    manifest=F/'campaign-loader/build/loader_identity.json';original=manifest.read_bytes()
    altered=dict(identity);altered['test_sha256']=dict(identity['test_sha256']);del altered['test_sha256']['detour_tests.txt']
    manifest.write_text(json.dumps(altered),encoding='utf-8')
    rejected('incomplete test set rejected',lambda:check(F,release));manifest.write_bytes(original)
    manifest.unlink();shutil.copy2(F/'campaign-loader/build/dinput8.dll',F/'campaign-loader/dinput8.dll')
    rejected('missing build record rejects legacy DLL fallback',lambda:check(F,release))

report={'passed':True,'tests':results,'source_sha256':sha(D/'build_pack.py'),'loader_identity_sha256':sha(D/'campaign-loader/build/loader_identity.json'),'execution':'File copies and production Python gate only. No DLL or game code executed.'}
(H/'campaign_build_gate_results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('PASS:',len(results),'campaign packaging freshness cases.')
