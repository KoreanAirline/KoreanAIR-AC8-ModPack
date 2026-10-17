"""Read-only PE and text review of the owner-supplied HOTAS full package.

No downloaded native library is loaded or executed. This is not a gameplay or
ABI compatibility certification.
"""
from pathlib import Path
import hashlib, json, sys, difflib

D = Path(__file__).resolve().parents[2]
W = D.parents[1]
H = Path(__file__).resolve().parent
sys.path.insert(0, str(W / 'work/libs'))
import pefile

download = Path(sys.argv[1])
game = Path(sys.argv[2])
out = {'read_only': True, 'download_executed': False, 'files': {}}
symbols = [
    '??0Lua@LuaMadeSimple@RC@@QEAA@PEAUlua_State@@@Z',
    '??1Lua@LuaMadeSimple@RC@@QEAA@XZ',
    '?get_stack_size@Lua@LuaMadeSimple@RC@@QEBAHXZ',
    '?is_number@Lua@LuaMadeSimple@RC@@QEBA_NH@Z',
    '?get_number@Lua@LuaMadeSimple@RC@@QEBANH@Z',
    '?set_number@Lua@LuaMadeSimple@RC@@QEBAXN@Z',
]
def sha(b): return hashlib.sha256(b).hexdigest()
def pe_info(p):
    b = p.read_bytes()
    pe = pefile.PE(data=b)
    exports = {s.name.decode('ascii', 'replace'): s for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name} if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT') else {}
    imports = {x.dll.decode('ascii', 'replace'): [i.name.decode('ascii', 'replace') if i.name else '#'+str(i.ordinal) for i in x.imports] for x in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])}
    section_sha = {s.Name.rstrip(b'\0').decode():sha(s.get_data()) for s in pe.sections}
    info = {'sha256': sha(b), 'size':len(b), 'machine':hex(pe.FILE_HEADER.Machine), 'sections_sha256':section_sha,
            'exports':sorted(exports), 'imports':imports, 'lua_api':{}}
    for sym in symbols:
        e = exports.get(sym)
        info['lua_api'][sym] = {'rva':hex(e.address), 'first_128':pe.get_data(e.address,128).hex()} if e else None
    return info
for name in ['Game/Binaries/Win64/dwmapi.dll', 'Game/Binaries/Win64/UE4SS/UE4SS.dll']:
    hotas, ours = pe_info(download/name), pe_info(game/name)
    out['files'][name] = {'hotas':hotas, 'ours':ours,
        'same_bytes':hotas['sha256']==ours['sha256'],
        'same_export_names':hotas['exports']==ours['exports'],
        'missing_lua_symbols':[s for s in symbols if not hotas['lua_api'][s]]}
mods = 'Game/Binaries/Win64/UE4SS/Mods/'
out['native_mods']={}
ours_exports=set(out['files']['Game/Binaries/Win64/UE4SS/UE4SS.dll']['ours']['exports'])
for rel in ['AC8HOTAS/Scripts/ac8_hotas_devices_001.dll', 'AC8AnalogYaw/Scripts/ac8_analog_yaw_013.dll']:
    info=pe_info(download/(mods+rel))
    needs=[sym for lib,syms in info['imports'].items() if lib.lower()=='ue4ss.dll' for sym in syms]
    info['missing_imports_from_our_runtime']=[sym for sym in needs if sym not in ours_exports]
    out['native_mods'][rel]=info
out['mod_lists']={name:(download/(mods+name)).read_text(encoding='utf-8-sig') for name in ['mods.txt','mods.json']}
out['hotas_readme_sha256'] = sha((download/(mods+'AC8HOTAS/README.md')).read_bytes())
out['analog_yaw_readme_sha256'] = sha((download/(mods+'AC8AnalogYaw/README.md')).read_bytes())
out['override'] = (download/'Game/Binaries/Win64/override.txt').read_text().strip()
out['settings_diff'] = list(difflib.unified_diff(
    (game/'Game/Binaries/Win64/UE4SS/UE4SS-settings.ini').read_text(encoding='utf-8-sig').splitlines(),
    (download/'Game/Binaries/Win64/UE4SS/UE4SS-settings.ini').read_text(encoding='utf-8-sig').splitlines(),
    fromfile='our-tested-settings',tofile='download-settings'))
out['conclusions'] = [
    'The supplied full-install loader and UE4SS differ from the pinned KoreanAIR runtime. Same exported names do not certify C++ Lua wrapper ABI compatibility.',
    'lua_bridge.h pins the tested UE4SS digest before constructing a size0xA8 LuaMadeSimple wrapper; accepting only a foreign proxy without the matching tested UE4SS is insufficient.',
    'HOTAS binds native flight-stick profiles, but enabled MouseFlight clears aggregate pitch/yaw/roll unless WASD/QE physically owns the axis. Simultaneous HOTAS rotation is intentionally not a supported blend.',
    'AC8AnalogYaw alters the yaw accumulator modeled by MouseFlight. Its README warns of another hook on the same target. Both enabled cannot be treated as equivalent native yaw processing.',
    'Preserving HOTAS while enabling Screen/translation/subtitle layout and disabling MouseFlight is the narrow compatible architecture, subject to actual integration validation of the shared runtime.',
    'The supported deployment should merge mod-only HOTAS folders into one verified UE4SS runtime and preserve other mod lists/bindings; never blanket-allow every conflicting DLL hash.',
]
(H/'download_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name,item in out['files'].items():
    print(name, 'same_bytes',item['same_bytes'],'same_exports',item['same_export_names'],'hotas_sha',item['hotas']['sha256'],'ours_sha',item['ours']['sha256'])
    print('missing_lua_symbols',item['missing_lua_symbols'])
print('Read-only PE review complete. No downloaded DLL was executed.')
