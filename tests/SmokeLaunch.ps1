$ErrorActionPreference = 'Stop'
$distributionRoot = Split-Path $PSScriptRoot -Parent
$gameRoot = 'E:/SteamLibrary/steamapps/common/ACE COMBAT 8'
$nativeRoot = Join-Path $gameRoot 'Game/Binaries/Win64'
$reportFolder = Join-Path $PSScriptRoot 'live_crosshair'
if (Get-Process -Name AceCombat8 -ErrorAction SilentlyContinue) { throw 'Game must be closed before this startup check.' }
$campaignPath = Join-Path $nativeRoot 'KoreanAIR_AC8_Campaign.log'
$campaignBefore = if (Test-Path -LiteralPath $campaignPath) { (Get-Item -LiteralPath $campaignPath).Length } else { 0 }
$launchedAt = Get-Date
& (Join-Path $PSScriptRoot 'LiveLaunch.exe') $gameRoot
if ($LASTEXITCODE -ne 0) { throw 'Installed launcher did not start the game.' }
$gameProcess = $null
$deadline = (Get-Date).AddSeconds(45)
do {
    Start-Sleep -Milliseconds 500
    $gameProcess = Get-Process -Name AceCombat8 -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($gameProcess -and $gameProcess.MainWindowHandle -ne 0) { break }
} while ((Get-Date) -lt $deadline)
if (-not $gameProcess) { throw 'No game process after launch.' }
Start-Sleep -Seconds 10
$gameProcess.Refresh()
$modulePaths = @(
    (Join-Path $nativeRoot 'dinput8.dll'),
    (Join-Path $nativeRoot 'dwmapi.dll'),
    (Join-Path $nativeRoot 'UE4SS/UE4SS.dll'),
    (Join-Path $nativeRoot 'UE4SS/Mods/AC8MouseAim/Scripts/ac8_mouse_aim_010.dll')
) | ForEach-Object { [IO.Path]::GetFullPath($_) }
# The forwarding DLLs also load Windows' own namesakes. Verify the installed
# paths rather than counting both system and mod copies as separate modules.
$modules = @($gameProcess.Modules | Where-Object { [IO.Path]::GetFullPath($_.FileName) -in $modulePaths } | ForEach-Object {
    @{name=$_.ModuleName;path=$_.FileName;sha256=(Get-FileHash -LiteralPath $_.FileName -Algorithm SHA256).Hash.ToLowerInvariant()}
})
$windowTitle = $gameProcess.MainWindowTitle
$closeRequested = $gameProcess.CloseMainWindow()
$closeDeadline = (Get-Date).AddSeconds(45)
do {
    Start-Sleep -Milliseconds 500
    $stillRunning = Get-Process -Id $gameProcess.Id -ErrorAction SilentlyContinue
} while ($stillRunning -and (Get-Date) -lt $closeDeadline)
$campaignLog = Get-Item -LiteralPath $campaignPath
$campaignBytes = [IO.File]::ReadAllBytes($campaignPath)
$campaignOffset = if ($campaignBytes.Length -ge $campaignBefore) { [int]$campaignBefore } else { 0 }
$campaignText = [Text.Encoding]::UTF8.GetString($campaignBytes,$campaignOffset,$campaignBytes.Length-$campaignOffset)
$ueText = Get-Content -LiteralPath (Join-Path $nativeRoot 'UE4SS/UE4SS.log') -Raw
$mouseLog = Get-ChildItem -LiteralPath (Join-Path $nativeRoot 'UE4SS/Mods/AC8MouseAim/Logs') -Filter 'MouseAim*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$mouseText = Get-Content -LiteralPath $mouseLog.FullName -Raw
$expectedNativeHash = (Get-FileHash -LiteralPath (Join-Path $distributionRoot 'runtime/scripts/ac8_mouse_aim_010.dll')).Hash.ToLowerInvariant()
$freshNative = $mouseLog.LastWriteTime -ge $launchedAt
$renderSamples = @([regex]::Matches($mouseText,'DISPLAY native render viewport: (\d+)x(\d+)') | ForEach-Object { @{width=[int]$_.Groups[1].Value;height=[int]$_.Groups[2].Value} })
$wideRenderSamples = @($renderSamples | Where-Object { $_.width -gt 2*$_.height })
$errors = 'Recovering after runtime error|native camera refused|native camera disabled|bridge refused|input processor signature missing|error native raw input|direct bridge unavailable|Failed to execute main script|DISPLAY camera disabled|Unhandled Exception|Fatal error'
$report = @{
    started_at=$launchedAt.ToString('o');checked_at=(Get-Date).ToString('o')
    running=($modules.Count -eq 4);pid=$gameProcess.Id;window=$windowTitle
    campaign_log_fresh=($campaignLog.LastWriteTime -ge $launchedAt)
    campaign_pak_mounted=($campaignText.Contains('Campaign loader armed:') -and $campaignText.Contains('Approved KoreanAIR campaign PAK selected.'))
    campaign_pak_sha256=(Get-FileHash -LiteralPath (Join-Path $gameRoot 'Game/Content/Paks/pakchunk0-Windows_999_P.pak')).Hash.ToLowerInvariant()
    lua_modules_loaded=$ueText.Contains('Loaded modules: MouseFlight, TripleDisplay.')
    new_runtime_errors=($ueText -match $errors -or $mouseText -match $errors)
    modules=$modules;native_dll_matches=(@($modules | Where-Object { $_.name -eq 'ac8_mouse_aim_010.dll' -and $_.sha256 -eq $expectedNativeHash }).Count -eq 1)
    native_log_fresh=$freshNative
    native_camera_registered=$mouseText.Contains('native camera post-update registered;')
    native_maneuver_guard_verified=$mouseText.Contains('native maneuver input build guard: verified')
    native_player_maneuver_guard_verified=$mouseText.Contains('native player maneuver build guard: verified')
    native_raw_provenance_verified=$mouseText.Contains('native raw input provenance hook: verified mapper and synchronous physics order')
    native_render_viewport_samples=$renderSamples
    native_render_viewport_observed=($renderSamples.Count -gt 0)
    native_wide_render_viewport_observed=($wideRenderSamples.Count -gt 0)
    graphics_override_log_present=$ueText.Contains('[AC8Performance]')
    close_request_accepted=$closeRequested
    mission_piloted=$false;game_closed_normally=($closeRequested -and -not $stillRunning)
}
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $reportFolder 'live_game_launch.json') -Encoding utf8
if (-not $report.running -or -not $report.campaign_log_fresh -or -not $report.campaign_pak_mounted -or -not $report.lua_modules_loaded -or $report.new_runtime_errors -or -not $report.native_dll_matches -or -not $report.native_log_fresh -or -not $report.native_camera_registered -or -not $report.native_maneuver_guard_verified -or -not $report.native_player_maneuver_guard_verified -or -not $report.native_raw_provenance_verified -or -not $report.game_closed_normally) {
    throw 'Startup verification failed; see live_game_launch.json.'
}
Write-Output 'PASS: installed launcher startup, current native camera/maneuver guards, revised campaign PAK mount and normal exit. No mission piloting.'
