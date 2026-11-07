$ErrorActionPreference = 'Stop'
$package = Join-Path $PSScriptRoot 'language_chi.big'
$check = Get-Content -LiteralPath (Join-Path $PSScriptRoot '验证结果.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash.ToLowerInvariant() -ne $check.sha256) {
    throw 'Chinese package SHA256 mismatch.'
}
$client = 'D:\FO3ID\32795'
if (-not (Test-Path -LiteralPath (Join-Path $client 'fifazf.exe'))) { throw 'FO3ID client missing.' }
$backup = 'D:\FO3ID\backup\localization-zh'
New-Item -ItemType Directory -Force -Path $backup | Out-Null
$manifestPath = Join-Path $backup 'resource-manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath)) {
    $entries = @()
    foreach ($relative in @('_cache\games\fo3id\externalAssets\language_chi.big', '_cache\cdn\externalAssets\language_chi.big')) {
        $target = Join-Path $client $relative
        $original = Test-Path -LiteralPath $target
        $saved = Join-Path $backup ($entries.Count.ToString() + '-language_chi.big')
        if ($original) { Copy-Item -LiteralPath $target -Destination $saved }
        $entries += [pscustomobject]@{ target = $target; original = $original; backup = $saved }
    }
    $entries | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding UTF8
}
$resourceEntries = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
# Preflight all existing targets before changing either copy.
foreach ($entry in $resourceEntries) {
    if (Test-Path -LiteralPath $entry.target) {
        try {
            $probe = [System.IO.File]::Open($entry.target, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
            $probe.Dispose()
        } catch {
            throw 'The game is using its language cache. Exit FIFA Online 3, then run this installer again. No resource copies were changed in this run.'
        }
    }
}
foreach ($entry in $resourceEntries) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $entry.target) | Out-Null
    Copy-Item -LiteralPath $package -Destination $entry.target -Force
}
Write-Output 'Chinese resources installed. Original Indonesian files are unchanged.'
Write-Output 'For the next server launch set FO3_LANGUAGE=chi, then restart the server and game.'
