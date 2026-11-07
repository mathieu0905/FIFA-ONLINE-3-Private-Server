$ErrorActionPreference='Stop'
# Never interrupt an active game for a background installation.
function Assert-FO3GameIdle {
    if (Get-Process -Name fifazf -ErrorAction SilentlyContinue) {
        throw '更新已延后，当前游戏继续运行。游戏运行期间禁止停止或重启服务。'
    }
}
Assert-FO3GameIdle
$pattern='(?i)D:\\FO3ID\\server\\(?:http_config|messenger)\.py'
$targets=Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match $pattern }
foreach($item in $targets){ Assert-FO3GameIdle; Stop-Process -Id $item.ProcessId -ErrorAction SilentlyContinue }
Write-Host 'FO3ID local services stopped.'
