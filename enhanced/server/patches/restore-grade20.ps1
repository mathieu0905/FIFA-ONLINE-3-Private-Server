param([string]$Client='D:\FO3ID\32795')
$ErrorActionPreference='Stop'
if(Get-Process fifazf -ErrorAction SilentlyContinue){throw '请先退出 FIFA Online 3，再恢复原版资源。'}
$root=(Resolve-Path -LiteralPath $Client).Path.TrimEnd('\')
$backup='D:\FO3ID\backup\enhancement20'
$manifest=Get-Content -LiteralPath (Join-Path $backup 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$allowed=@{
 'TeamManagementPlayerEnhancementTabPage.big'='data\ui\TeamManagementPlayerEnhancementTabPage.big'
 'TeamManagementTeamInfoTabPage.big'='data\ui\TeamManagementTeamInfoTabPage.big'
 'TileList.big'='data\ui\components\TileList.big'
 'PlayerInfoNew.big'='data\ui\components\PlayerInfoNew.big'
 'Label.big'='data\ui\components\Label.big'
 'ScrollingList.big'='data\ui\components\ScrollingList.big'
 'SmoothList.big'='data\ui\components\SmoothList.big'
}
foreach($entry in $manifest){
 if(-not $allowed.ContainsKey($entry.Name)){throw '未知备份文件'}
 $source=Join-Path $backup $entry.Name
 if((Get-FileHash -LiteralPath $source).Hash -ne $entry.OriginalSHA256){throw '原版备份校验失败'}
}
foreach($entry in $manifest){
 Copy-Item -LiteralPath (Join-Path $backup $entry.Name) -Destination (Join-Path $root $allowed[$entry.Name]) -Force
}
Write-Host '客户端资源已恢复。高于 +10 的存档不应直接降回旧服务端；请先备份存档并保留 +20 属性表。'
