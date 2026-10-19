$ErrorActionPreference='Stop'
$taskGameRoot='E:/SteamLibrary/steamapps/common/ACE COMBAT 8'
$taskLauncher=Join-Path $taskGameRoot 'KoreanAIR_AC8_ModPack_2.3.exe'
$taskBefore=@{}
foreach($taskName in @('config.ini','display.ini','subtitle.ini','pack.ini')){
 $taskPath=Join-Path $taskGameRoot ('Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/'+$taskName)
 $taskBefore[$taskPath]=[Convert]::ToBase64String([IO.File]::ReadAllBytes($taskPath))
}
$taskAssembly=[Reflection.Assembly]::LoadFile([IO.Path]::GetFullPath($taskLauncher))
$taskArgs=New-Object object[] 2
$taskArgs[0]=[string]$taskGameRoot
$taskArgs[1]=[string]'en'
$taskMethod=$taskAssembly.GetType('KoreanAIR.SupportReport').GetMethod('Create',[Type[]]@([string],[string]))
$taskReport=[string]$taskMethod.Invoke($null,$taskArgs)
$taskText=[IO.File]::ReadAllText($taskReport,[Text.Encoding]::UTF8)
if($taskText -notmatch 'KoreanAIR_AC8_ModPack_2.3 build 2026101902'){throw 'Report identity mismatch.'}
if($taskText -notmatch 'Active monitor count: 3'){throw 'Physical monitor evidence missing.'}
if($taskText -match 'status=MISMATCH'){throw 'Installed critical file differs from candidate.'}
if($taskText -match 'USER' -or $taskText.Contains($taskGameRoot) -or $taskText.Contains($taskGameRoot.Replace('/','\'))){throw 'Private path redaction failed.'}
if((Get-Item -LiteralPath $taskReport).Length -gt 921600){throw 'Report exceeded byte budget.'}
foreach($taskPath in $taskBefore.Keys){if($taskBefore[$taskPath] -ne [Convert]::ToBase64String([IO.File]::ReadAllBytes($taskPath))){throw 'Collector modified settings.'}}
$taskEvidence=@{passed=$true;version='2.3';build=2026101902;actual_installed_launcher=$true;physical_monitor_count=3;critical_files_match=$true;private_path_redaction=$true;settings_unchanged=$true;report_bytes=(Get-Item -LiteralPath $taskReport).Length;game_launched=$false;published=$false}
$taskEvidence|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'installed_verification.json') -Encoding UTF8
'PASS actual installed launcher integrity/report export; settings unchanged.'
