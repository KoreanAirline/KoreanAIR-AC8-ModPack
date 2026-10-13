param(
    [string]$adapterPath,
    [string]$fixturePath,
    [string]$setupPath,
    [string]$payloadPath
)
$ErrorActionPreference = 'Stop'
$assembly = [Reflection.Assembly]::LoadFile([IO.Path]::GetFullPath($adapterPath))
$method = $assembly.GetType('LoaderCompatibilityAudit', $true).GetMethod(
    'Main', [Reflection.BindingFlags]'Static,NonPublic')
$arguments = New-Object object[] 1
$arguments[0] = [string[]]@($fixturePath, $setupPath, $payloadPath)
exit [int]$method.Invoke($null, $arguments)
