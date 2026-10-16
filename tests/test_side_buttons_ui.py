"""Compile and exercise current launcher side-button binding/settings/capture UI."""
from pathlib import Path
import json
import subprocess
import time
import uuid

root = Path(__file__).resolve().parents[1]
out = root / "tests" / ("side_buttons_" + time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6])
out.mkdir()
library = out / "SideButtonUiAudit.dll"
refs = ["System.Windows.Forms.dll", "System.Drawing.dll", "System.Web.Extensions.dll",
        "System.IO.Compression.dll", "System.IO.Compression.FileSystem.dll", "System.Net.Http.dll"]
sources = ["PackCore.cs", "Ui.cs", "UpdateCore.cs", "Launcher.cs", "Hud.cs", "Keys.cs",
           "UpdateUI.cs", "MouseInputWorker.cs"]
subprocess.run(["C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe", "/nologo",
                "/target:library", "/platform:x64", "/out:" + str(library),
                *["/reference:" + ref for ref in refs],
                *[str(root / "src" / name) for name in sources],
                str(root / "tests/SideButtonUiAudit.cs")], check=True)
run = subprocess.run(["powershell.exe", "-NoProfile", "-STA", "-File",
                      str(root / "tests/InvokeSideButtonUiAudit.ps1"), str(library), str(out)],
                     creationflags=subprocess.CREATE_NO_WINDOW, timeout=90)
report = json.loads((out / "results.json").read_text(encoding="utf-8-sig"))
print(json.dumps({"passed": report["passed"], "checks": report["checks"],
                  "report": str(out / "results.json")}))
run.check_returncode()
if not report["passed"]:
    raise AssertionError(report["error"])
