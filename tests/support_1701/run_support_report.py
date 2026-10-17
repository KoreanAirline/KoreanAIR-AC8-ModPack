"""Exercise the production manual collector with bounded private fixture data."""
from pathlib import Path
import json
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
D = HERE.parent.parent
CSC = Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
with tempfile.TemporaryDirectory(prefix='ac8_report_') as temporary:
    work = Path(temporary)
    binary = work / 'SupportReportTest.exe'
    command = [str(CSC), '/nologo', '/target:exe', '/main:SupportReportTest',
               '/out:' + str(binary), '/r:System.Web.Extensions.dll',
               '/r:System.IO.Compression.dll', '/r:System.IO.Compression.FileSystem.dll',
               str(D / 'src/PackCore.cs'), str(D / 'src/SupportReport.cs'),
               str(HERE / 'SupportReportTest.cs')]
    subprocess.run(command, check=True)
    subprocess.run([str(binary), str(work)], check=True)
    result = json.loads((work / 'results.json').read_text(encoding='utf-8-sig'))
    result['source_files'] = ['src/SupportReport.cs', 'tests/support_1701/SupportReportTest.cs']
    (HERE / 'report_results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
