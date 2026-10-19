param([Parameter(Mandatory=$true)][string]$Workspace,[string]$AssemblyPath)
$ErrorActionPreference='Stop'
$auditRoot=Join-Path $Workspace 'work/ac8-distribution/tests/install_access_1902'
$source=Join-Path $Workspace 'work/ac8-distribution/src/PackCore.cs'
$fixtureRoot=Join-Path $auditRoot ('product_preflight_fixture_'+[Guid]::NewGuid().ToString('N'))
if(!$AssemblyPath){
 $AssemblyPath=Join-Path $auditRoot 'Core_Preflight.dll'
 & 'C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe' /nologo /target:library /platform:x64 ('/out:'+$AssemblyPath) /reference:System.Web.Extensions.dll /reference:System.IO.Compression.dll /reference:System.IO.Compression.FileSystem.dll $source
 if($LASTEXITCODE -ne 0){throw 'Production Core compilation failed'}
}
Add-Type -Path (Join-Path $auditRoot 'ProductPreflightAudit.cs') -ReferencedAssemblies System.Web.Extensions
[ProductPreflightAudit1902]::Execute($AssemblyPath,$fixtureRoot,(Join-Path $auditRoot 'product_preflight_results.json'),$source)
$result=Get-Content -LiteralPath (Join-Path $auditRoot 'product_preflight_results.json') -Raw | ConvertFrom-Json
$result | Select-Object passed,checkCount,failedChecks,assemblySha256,productionSourceSha256
if(!$result.passed){$result.checks | Where-Object {-not $_.passed};throw 'Production preflight checks failed'}
