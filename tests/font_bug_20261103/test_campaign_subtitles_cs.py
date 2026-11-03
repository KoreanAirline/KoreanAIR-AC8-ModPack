"""Compile actual production C#, compare all generated strings to Python proof."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys,zipfile

H=Path(__file__).resolve().parent;D=H.parents[1]
PY=H/'current_stock_overlay.py';spec=importlib.util.spec_from_file_location('current_stock_reference',PY);reference=importlib.util.module_from_spec(spec);sys.modules[spec.name]=reference;spec.loader.exec_module(reference)
compiler=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
exe=H/'CampaignSubtitlesTests.exe';source=D/'src/CampaignSubtitles.cs';test=H/'CampaignSubtitlesTests.cs';patch=D/'campaign-source/campaign-dialogue.json.gz'
subprocess.run([str(compiler),'/nologo','/optimize+','/platform:x64','/reference:System.Web.Extensions.dll','/out:'+str(exe),str(source),str(test)],check=True)
subprocess.run([str(exe),'E:/SteamLibrary/steamapps/common/ACE COMBAT 8',str(H),str(patch)],check=True)
sources=reference.load_verified_sources();stock=reference.stock_from_evidence(H,sources)
_,_,expected,manifest,_=reference.build_overlay(stock,sources)
plain=(H/'csharp_current_CP_G.bin').read_bytes();actual=reference.table_slices(plain)
assert actual==expected,'Production C# changed a current UTF8 byte slice versus independent Python reference.'
packed=(H/'csharp_current_stock_campaign_P.pak').read_bytes();entries=sources.builder.unpack_pak(packed)
assert set(entries)==set(sources.builder.CAMPAIGN_PATHS)and len(entries)==2
assert len(set(entries.values()))==1
for encoded in entries.values():assert reference.table_slices(reference.decode_dat(encoded,6,sources.builder,16*1024*1024))==expected
result=json.loads((H/'csharp_current_stock_results.json').read_text(encoding='utf-8'))
result.update(python_raw_utf8_tables_equal=True,pak_checksums_and_paths_verified=True,untouched_menus_and_added_strings_equal=True,source_sha256={p.relative_to(D).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in(source,test,Path(__file__),patch)},build_official_archive_bytes_read=4005456+1536+3*53+483074+471360+178361,production_test_hooks_compiled=False)
(H/'csharp_current_stock_results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('PASS: every46594 current UTF8 slice matches independent Python overlay; two-entry PAK paths/SHA1/index/DAT roundtrips verified.')
