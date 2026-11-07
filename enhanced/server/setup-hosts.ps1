$hostsPath = 'C:\Windows\System32\drivers\etc\hosts'
if (-not (Get-Content -LiteralPath $hostsPath | Select-String '^\s*127\.0\.0\.1\s+APSEODESK172(?:\s|$)')) {
 Copy-Item -LiteralPath $hostsPath -Destination 'D:\FO3ID\server\hosts.before-fo3' -Force
 Add-Content -LiteralPath $hostsPath -Value "`r`n127.0.0.1 APSEODESK172 # FO3ID local server"
}
