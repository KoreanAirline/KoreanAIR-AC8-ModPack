param([string]$gameRoot,[string]$destination,[switch]$Enable)
$ErrorActionPreference='Stop'
$dll=Join-Path $PSScriptRoot 'LiveFrameGenerationAudit.dll'
$assembly=[Reflection.Assembly]::LoadFile($dll)
$arguments=New-Object object[] 1
$arguments[0]=[string[]]@($gameRoot,$destination,$(if($Enable){'--enable'}else{'--original'}))
exit [int]$assembly.GetType('LiveFrameGenerationAudit',$true).GetMethod('Run').Invoke($null,$arguments)
