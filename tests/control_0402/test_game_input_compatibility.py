"""Compile and run read-only input compatibility tests; no private fixtures copied."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
DISTRIBUTION = HERE.parents[1]
COMPILER = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
SOURCES = [DISTRIBUTION / 'src/GameInputCompatibility.cs', HERE / 'GameInputCompatibilityTests.cs']
EXECUTABLE = HERE / 'GameInputCompatibilityTests.exe'


def main():
    command = [str(COMPILER), '/nologo', '/target:exe', '/platform:x64', '/optimize+',
               '/define:GAME_INPUT_COMPATIBILITY_TEST', '/r:System.Web.Extensions.dll',
               '/out:' + str(EXECUTABLE)] + [str(path) for path in SOURCES]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise RuntimeError(compiled.stdout + compiled.stderr)
    saves = Path(os.environ['LOCALAPPDATA']) / 'BANDAI NAMCO Entertainment/ACE COMBAT 8/Saved/SaveGames'
    fixtures = []  # Public tests use generated fixtures only.
    executed = subprocess.run([str(EXECUTABLE)] + [str(path) for path in fixtures],
                              capture_output=True, text=True, encoding='utf-8', errors='replace')
    lines = [line for line in executed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError('Input compatibility tests produced no JSON result.')
    report = json.loads(lines[-1])
    report['source_sha256'] = {path.relative_to(DISTRIBUTION).as_posix():
                              hashlib.sha256(path.read_bytes()).hexdigest() for path in SOURCES}
    report['private_fixture_paths_recorded'] = False
    (HERE / 'game_input_compatibility_results.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if executed.returncode or not report['passed']:
        raise RuntimeError(report.get('error') or 'Input compatibility tests failed.')


if __name__ == '__main__':
    main()
