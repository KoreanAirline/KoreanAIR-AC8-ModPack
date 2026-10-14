param([string]$assemblyPath,[string]$destination)
$ErrorActionPreference='Stop'
$assembly=[Reflection.Assembly]::LoadFile([IO.Path]::GetFullPath($assemblyPath))
$method=$assembly.GetType('FrameGenerationAudit',$true).GetMethod('Run')
$arguments=New-Object object[] 1
$arguments[0]=[string[]]@($destination)
exit [int]$method.Invoke($null,$arguments)
