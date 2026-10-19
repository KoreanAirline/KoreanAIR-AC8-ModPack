param([Parameter(Mandatory=$true)][string]$Workspace)
$ErrorActionPreference='Stop'
$auditRoot=Join-Path $Workspace 'work/ac8-distribution/tests/install_access_1902'
$fixtureRoot=Join-Path $auditRoot ('preflight_fixture_'+[Guid]::NewGuid().ToString('N'))
Add-Type -Path (Join-Path $auditRoot 'PreflightAudit.cs') -ReferencedAssemblies System.Web.Extensions
[PreflightAudit1902]::Execute($fixtureRoot,(Join-Path $auditRoot 'preflight_results.json'))
Get-Content -LiteralPath (Join-Path $auditRoot 'preflight_results.json')
