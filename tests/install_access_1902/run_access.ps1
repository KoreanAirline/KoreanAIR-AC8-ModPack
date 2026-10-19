param([Parameter(Mandatory=$true)][string]$Workspace,[string]$AssemblyPath,[string]$ResultName='results.json')
$ErrorActionPreference='Stop'
$auditRoot=Join-Path $Workspace 'work/ac8-distribution/tests/install_access_1902'
$fixtureRoot=Join-Path $auditRoot ('fixture_'+[Guid]::NewGuid().ToString('N'))
$setup=if($AssemblyPath){$AssemblyPath}else{Join-Path $Workspace 'work/ac8-distribution/build/KoreanAIR_AC8_ModPack_2.3_Setup.exe'}
Add-Type -Path (Join-Path $auditRoot 'AccessAudit.cs') -ReferencedAssemblies System.Web.Extensions
[AccessAudit1902]::Execute($setup,$fixtureRoot,(Join-Path $auditRoot $ResultName))
Get-Content -LiteralPath (Join-Path $auditRoot $ResultName)
