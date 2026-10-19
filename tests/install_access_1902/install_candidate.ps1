$ErrorActionPreference='Stop'
$taskDistributionRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$taskGameRoot='E:/SteamLibrary/steamapps/common/ACE COMBAT 8'
if(Get-Process -Name AceCombat8 -ErrorAction SilentlyContinue){throw 'Game is running.'}
$taskBefore=@{}
foreach($taskName in @('config.ini','display.ini','subtitle.ini','pack.ini')){
 $taskPath=Join-Path $taskGameRoot ('Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/'+$taskName)
 $taskBefore[$taskPath]=[Convert]::ToBase64String([IO.File]::ReadAllBytes($taskPath))
}
$taskConfigRoot=Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'BANDAI NAMCO Entertainment/ACE COMBAT 8/Saved/Config/Windows'
foreach($taskName in @('GameUserSettings.ini','Engine.ini')){
 $taskPath=Join-Path $taskConfigRoot $taskName
 $taskBefore[$taskPath]=[Convert]::ToBase64String([IO.File]::ReadAllBytes($taskPath))
}
$taskPreference=Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'KoreanAIR_AC8_ModPack/language.txt'
$taskPreferenceExisted=Test-Path -LiteralPath $taskPreference
if($taskPreferenceExisted){$taskBefore[$taskPreference]=[Convert]::ToBase64String([IO.File]::ReadAllBytes($taskPreference))}
$taskStatePath=Join-Path $taskGameRoot 'KoreanAIR_AC8_ModPack/installed.json'
$taskOldState=Get-Content -LiteralPath $taskStatePath -Raw | ConvertFrom-Json
$taskSetup=Join-Path $taskDistributionRoot 'build/KoreanAIR_AC8_ModPack_2.3_Setup.exe'
$taskAssembly=[Reflection.Assembly]::LoadFile((Join-Path $taskDistributionRoot 'build/KoreanAIR_AC8_ModPack_2.3.exe'))
$taskInstallerAssembly=[Reflection.Assembly]::LoadFile($taskSetup)
$taskPayloadArgs=New-Object object[] 4
$taskPayloadArgs[0]=$taskInstallerAssembly
$taskPayloadArgs[1]=$null
$taskPayloadArgs[2]=[System.Threading.CancellationToken]::None
$taskPayloadArgs[3]=$false
$taskPayload=$taskAssembly.GetType('KoreanAIR.ReleasePayload').GetMethod('OpenPayload').Invoke($null,$taskPayloadArgs)
try {
 $taskUpdateArgs=New-Object object[] 3
 $taskUpdateArgs[0]=[string]$taskGameRoot
 $taskUpdateArgs[1]=[IO.Stream]$taskPayload
 $taskUpdateArgs[2]=[string]$taskSetup
 $null=$taskAssembly.GetType('KoreanAIR.Core').GetMethod('UpdatePreservingState').Invoke($null,$taskUpdateArgs)
} finally {$taskPayload.Dispose()}
foreach($taskPath in $taskBefore.Keys){if($taskBefore[$taskPath] -ne [Convert]::ToBase64String([IO.File]::ReadAllBytes($taskPath))){throw ('Settings changed: '+[IO.Path]::GetFileName($taskPath))}}
if($taskPreferenceExisted -ne (Test-Path -LiteralPath $taskPreference)){throw 'UI language preference changed.'}
$taskState=Get-Content -LiteralPath $taskStatePath -Raw | ConvertFrom-Json
if($taskState.version -ne '2.3' -or $taskState.build -ne 2026101902){throw 'Candidate not installed.'}
foreach($taskField in @('campaign','mouse','display','suspended')){if($taskState.$taskField -ne $taskOldState.$taskField){throw ('Module/suspended state changed: '+$taskField)}}
if(($taskState.frameGeneration|ConvertTo-Json -Compress) -ne ($taskOldState.frameGeneration|ConvertTo-Json -Compress)){throw 'Frame generation lease changed.'}
foreach($taskName in @('KoreanAIR_AC8_ModPack_2.3.exe','Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/Scripts/ac8_mouse_aim_010.dll')){
 $taskSource=if($taskName -like '*.dll'){Join-Path $taskDistributionRoot 'runtime/scripts/ac8_mouse_aim_010.dll'}else{Join-Path $taskDistributionRoot ('build/'+$taskName)}
 if((Get-FileHash -LiteralPath $taskSource -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath (Join-Path $taskGameRoot $taskName) -Algorithm SHA256).Hash){throw 'Installed candidate hash mismatch.'}
}
$taskReport=@{passed=$true;version='2.3';build=2026101902;settings_unchanged=$true;graphics_unchanged=$true;ui_language_unchanged=$true;modules_unchanged=$true;suspended_unchanged=$true;frame_generation_lease_unchanged=$true;production_update_preserving_state=$true;installed_hashes_match=$true;game_launched=$false;published=$false}
$taskReport|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'local_installation.json') -Encoding UTF8
'PASS local candidate1902 installation; settings, graphics, language, modules and suspension preserved.'
