"""Real WinForms and Core subtitle defaults, using only inert temporary fixtures."""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile
import zipfile

H = Path(__file__).resolve().parent
D = H.parents[1]
CSC = Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
MOD = 'Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/'
sources = [D / 'src' / name for name in (
    'PackCore.cs', 'CampaignSubtitles.cs', 'Setup.cs', 'Launcher.cs', 'Ui.cs',
    'UpdateCore.cs', 'Hud.cs', 'Keys.cs', 'UpdateUI.cs', 'MouseInputWorker.cs',
    'SupportReport.cs',
)] + [H / 'SubtitleDefaultsTests.cs']
refs = ['System.Windows.Forms.dll', 'System.Drawing.dll', 'System.Web.Extensions.dll',
        'System.IO.Compression.dll', 'System.IO.Compression.FileSystem.dll']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

with tempfile.TemporaryDirectory(prefix='ac8_subtitle_defaults_') as temporary:
    folder = Path(temporary)
    exe = folder / 'SubtitleDefaultsTests.exe'
    payload = folder / 'inert_payload.zip'
    # Use the current shipped position file, not a duplicate test-only default.
    files = {
        MOD + 'subtitle.ini': ((D / 'runtime/subtitle.ini').read_bytes(), 'runtime', True),
        MOD + 'config.ini': (b'[control]\r\nsensitivity=0.01\r\n', 'runtime', True),
        MOD + 'Scripts/main.lua': (b'-- inert fixture, never executed\r\n', 'runtime', False),
        'Game/Binaries/Win64/dinput8.dll': (b'inert campaign hook fixture', 'campaign', False),
        'KoreanAIR_AC8_ModPack/Translation/campaign-dialogue.json.gz': (b'inert dictionary fixture', 'campaign', False),
        # A deliberately misclassified old archive exercises unconditional rejection.
        'Game/Content/Paks/pakchunk0-Windows_999_P.pak': (b'inert historical whole-table archive', 'common', False),
    }
    manifest = dict(files=[], legacy={})
    with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path, (data, group, mutable) in files.items():
            source = 'payload/' + path
            manifest['files'].append(dict(path=path, source=source,
                                         hash=hashlib.sha256(data).hexdigest(),
                                         group=group, mutable=mutable))
            archive.writestr(source, data)
        archive.writestr('manifest.json', json.dumps(manifest))
    command = [str(CSC), '/nologo', '/target:exe', '/platform:x64', '/optimize+',
               '/main:SubtitleDefaultsTests', '/define:FRAME_GENERATION_TEST',
               '/out:' + str(exe), '/resource:' + str(payload) + ',Payload.zip',
               *['/r:' + name for name in refs], *map(str, sources)]
    built = subprocess.run(command, capture_output=True, text=True, errors='replace')
    if built.returncode:
        raise RuntimeError(built.stdout + built.stderr)
    result = subprocess.run([str(exe), str(folder / 'fixtures'), str(payload)],
                            capture_output=True, text=True, encoding='utf-8',
                            errors='replace', timeout=60)

report = dict(
    passed=result.returncode == 0,
    output=result.stdout,
    error=result.stderr,
    source_sha256={path.relative_to(D).as_posix(): sha(path)
                   for path in sources + [Path(__file__), D / 'runtime/subtitle.ini']},
    production_setup_and_launcher_compiled=True,
    entry_point='SubtitleDefaultsTests',
    only_test_define='FRAME_GENERATION_TEST (redirects user settings to temporary fixtures)',
    game_modified=False,
    game_executed=False,
    native_mod_executed=False,
    network_requested=False,
    temporary_fixtures_removed=True,
)
(H / 'subtitle_defaults_results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(result.stdout, end='')
if result.returncode:
    raise RuntimeError(result.stderr)
