param([string]$Assembly, [string]$Destination)
$ErrorActionPreference = 'Stop'
Add-Type -Path $Assembly
exit [SideButtonUiAudit]::Run([string[]]@($Destination))
