param([string]$TargetScript)
$ErrorActionPreference='Stop'
$scriptPath=if($TargetScript){$TargetScript}else{Join-Path $PSScriptRoot 'stop-server.ps1'}
$global:FO3TestStopped=@()
$global:FO3TestRunning=$true
$global:FO3TestChecks=0
$global:FO3TestAppears=$false
function Get-Process { param($Name,$ErrorAction) $global:FO3TestChecks++; if($global:FO3TestRunning -or ($global:FO3TestAppears -and $global:FO3TestChecks -gt 1)){[pscustomobject]@{Id=123;ProcessName='fifazf'}} }
function Get-CimInstance { param($ClassName) @([pscustomobject]@{Name='python.exe';CommandLine='python D:\FO3ID\server\http_config.py 443 --tls';ProcessId=111},[pscustomobject]@{Name='python.exe';CommandLine='python D:\FO3ID\server\messenger.py';ProcessId=222},[pscustomobject]@{Name='python.exe';CommandLine='python D:\other\server.py';ProcessId=333}) }
function Stop-Process { param($Id,$ErrorAction) $global:FO3TestStopped+=$Id }
$results=@()
try { & $scriptPath; throw 'Active game was not protected' } catch { if($_.Exception.Message -notlike '*更新已延后*'){throw} }
if($global:FO3TestStopped.Count -ne 0){throw 'Service stopped while playing'}
$results+='active game: no service stopped'
$global:FO3TestRunning=$false;$global:FO3TestChecks=0
& $scriptPath
if(($global:FO3TestStopped -join ',') -ne '111,222'){throw 'Idle target filter failed'}
$results+='idle: only official services selected (mocked stop)'
$global:FO3TestStopped=@();$global:FO3TestChecks=0;$global:FO3TestAppears=$true
try { & $scriptPath; throw 'Late game was not protected' } catch { if($_.Exception.Message -notlike '*更新已延后*'){throw} }
if($global:FO3TestStopped.Count -ne 0){throw 'Service stopped after game appeared'}
$results+='game appears after target discovery: stop deferred'
@{status='PASS';powershell=$PSVersionTable.PSVersion.ToString();tests=$results;actual_processes_stopped=0} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'tests.json') -Encoding UTF8
Write-Output 'NONINTERRUPT_STOP_TESTS_PASS'
