param([string]$Client='D:\FO3ID\32795')
$ErrorActionPreference='Stop'
if(Get-Process fifazf -ErrorAction SilentlyContinue){throw '请先退出 FIFA Online 3，再安装强化显示资源。'}
$root=(Resolve-Path -LiteralPath $Client).Path.TrimEnd('\')
$backup='D:\FO3ID\backup\enhancement20'
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$files=@(
 @{Name='TeamManagementPlayerEnhancementTabPage.big';Relative='data\ui\TeamManagementPlayerEnhancementTabPage.big'},
 @{Name='TileList.big';Relative='data\ui\components\TileList.big'},
 @{Name='PlayerInfoNew.big';Relative='data\ui\components\PlayerInfoNew.big'},
 @{Name='Label.big';Relative='data\ui\components\Label.big'},
 @{Name='ScrollingList.big';Relative='data\ui\components\ScrollingList.big'},
 @{Name='SmoothList.big';Relative='data\ui\components\SmoothList.big'},
 @{Name='TeamManagementTeamInfoTabPage.big';Relative='data\ui\TeamManagementTeamInfoTabPage.big'}
)
$manifestPath=Join-Path $backup 'manifest.json'
$manifest=@()
if(Test-Path -LiteralPath $manifestPath){
 $parsed=Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
 $manifest=@($parsed | ForEach-Object { $_ })
}
$plans=@()
foreach($file in $files){
 $source=Join-Path $PSScriptRoot $file.Name
 $target=Join-Path $root $file.Relative
 if(-not(Test-Path -LiteralPath $source) -or -not(Test-Path -LiteralPath $target)){throw "缺少文件：$($file.Name)"}
 $wanted=(Get-FileHash -LiteralPath $source).Hash
 $current=(Get-FileHash -LiteralPath $target).Hash
 $record=$manifest | Where-Object Name -eq $file.Name
 if($record){
  if($current -notin @($record.OriginalSHA256,$record.InstalledSHA256,$wanted)){throw "资源存在未审查修改：$($file.Name)"}
  if((Get-FileHash -LiteralPath (Join-Path $backup $file.Name)).Hash -ne $record.OriginalSHA256){throw "原始备份校验失败：$($file.Name)"}
 }else{
  $saved=Join-Path $backup $file.Name
  if(Test-Path -LiteralPath $saved){
   if((Get-FileHash -LiteralPath $saved).Hash -ne $current){throw "现有未登记备份不同：$($file.Name)"}
  }else{Copy-Item -LiteralPath $target -Destination $saved}
  $record=[pscustomobject]@{Name=$file.Name;Relative=$file.Relative;OriginalSHA256=$current;InstalledSHA256=$wanted}
  $manifest+= $record
 }
 $plans+= [pscustomobject]@{Source=$source;Target=$target;Wanted=$wanted;Record=$record;Name=$file.Name}
}
if(-not ($plans | Where-Object { (Get-FileHash -LiteralPath $_.Target).Hash -ne $_.Wanted })){
 Write-Output '全部7项强化界面资源已是当前版本，无需安装。'
 return
}
$run=Join-Path $backup ('display-run-'+(Get-Date -Format 'yyyyMMdd-HHmmss-ffff'))
New-Item -ItemType Directory -Path $run | Out-Null
foreach($plan in $plans){Copy-Item -LiteralPath $plan.Target -Destination (Join-Path $run $plan.Name)}
if(Test-Path -LiteralPath $manifestPath){Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $run 'manifest-before.json')}
try{
 foreach($plan in $plans){
  Copy-Item -LiteralPath $plan.Source -Destination $plan.Target -Force
  if((Get-FileHash -LiteralPath $plan.Target).Hash -ne $plan.Wanted){throw "安装校验失败：$($plan.Name)"}
  $plan.Record.InstalledSHA256=$plan.Wanted
 }
 $temporary=Join-Path $run 'manifest-next.json'
 $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $temporary -Encoding UTF8
 if(Test-Path -LiteralPath $manifestPath){[IO.File]::Replace($temporary,$manifestPath,(Join-Path $run 'manifest-replaced.json'))}else{[IO.File]::Move($temporary,$manifestPath)}
}catch{
 foreach($plan in $plans){Copy-Item -LiteralPath (Join-Path $run $plan.Name) -Destination $plan.Target -Force}
 throw
}
Write-Output '已安装7项强化界面资源；原始低阶图标与新增高阶列表显示待实机核对。'
Write-Output ('本次回退副本：'+$run)
