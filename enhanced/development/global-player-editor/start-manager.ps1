$ErrorActionPreference='Stop'
$editorRoot=Split-Path -Parent $MyInvocation.MyCommand.Path
$editorLog=Join-Path $editorRoot 'manager.out.log'
$editorError=Join-Path $editorRoot 'manager.err.log'
Start-Process -FilePath 'D:\FO3ID\server\.venv\Scripts\python.exe' -ArgumentList @('-B','-u',(Join-Path $editorRoot 'player_database.py')) -WorkingDirectory $editorRoot -WindowStyle Hidden -RedirectStandardOutput $editorLog -RedirectStandardError $editorError
Write-Host 'Global player database manager: http://127.0.0.1:8090/'
