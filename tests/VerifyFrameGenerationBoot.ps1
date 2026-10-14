param([ValidateSet('On','Off')][string]$Mode='On',[switch]$SaveRequest)
$ErrorActionPreference='Stop'
$root='E:/SteamLibrary/steamapps/common/ACE COMBAT 8'
$distributionRoot=Split-Path $PSScriptRoot -Parent
$release=Get-Content -LiteralPath (Join-Path $distributionRoot 'release.json') -Raw | ConvertFrom-Json
$exe=Join-Path $root ('KoreanAIR_AC8_ModPack_'+$release.version+'.exe')
$assembly=[Reflection.Assembly]::LoadFrom($exe)
$core=$assembly.GetType('KoreanAIR.Core',$true)
if($core.GetMethod('Running').Invoke($null,[object[]]@($root))){throw 'Close the game before this verification.'}
if($SaveRequest){$core.GetMethod('SetFrameGeneration').Invoke($null,[object[]]@($root,($Mode -eq 'On'))) | Out-Null;Write-Output ('Saved '+$Mode);exit 0}
$launch=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'live_crosshair/live_game_launch.json') -Raw | ConvertFrom-Json
$state=$core.GetMethod('ReadState').Invoke($null,[object[]]@($root))
$core.GetMethod('ValidateFrameGeneration').Invoke($null,[object[]]@($root,$state)) | Out-Null
$engine=Join-Path $env:LOCALAPPDATA 'BANDAI NAMCO Entertainment/ACE COMBAT 8/Saved/Config/Windows/Engine.ini'
$status=Join-Path $root 'Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/upscaler_status.ini'
$data=@{}
foreach($line in [IO.File]::ReadAllLines($status)){if($line -match '^([^=]+)=(.*)$'){$data[$matches[1]]=$matches[2]}}
$expected=if($Mode -eq 'On'){'2x'}else{'off'}
if($data['fg_mode'] -ne $expected){throw ('Requested '+$Mode+' but native mode was '+$data['fg_mode'])}
$protected=(Test-Path -LiteralPath $engine) -and (([IO.File]::GetAttributes($engine) -band [IO.FileAttributes]::ReadOnly) -ne 0)
if(-not $launch.game_closed_normally -or -not $launch.native_landing_guard_verified -or -not $protected){throw 'Post-exit startup preservation failed.'}
$report=@{passed=$true;requested=$Mode.ToLowerInvariant();tested_launcher_sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant();native_status=$data;engine_sha256=(Get-FileHash -LiteralPath $engine -Algorithm SHA256).Hash.ToLowerInvariant();engine_protected_after_game_exit=$protected;normal_game_exit=$launch.game_closed_normally;mission_piloted=$false;actual_generated_frames_in_flight_verified=$false;scope='Real startup and normal shutdown; native support/mode and last presentation cache. No flight FPS or generated-frame-in-flight assertion.'}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $PSScriptRoot ('live_crosshair/frame_generation_'+$Mode.ToLowerInvariant()+'_boot.json')) -Encoding utf8
if($Mode -eq 'On'){$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'live_crosshair/frame_generation_startup_evidence.json') -Encoding utf8}
Write-Output ('PASS '+$Mode+' native mode and post-exit managed configuration')
