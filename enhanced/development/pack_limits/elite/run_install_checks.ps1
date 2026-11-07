$ErrorActionPreference='Stop'
& 'D:\FO3ID\server\.venv\Scripts\python.exe' 'D:\fifaol3\pack_limits\elite\test_server_boundary.py'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& 'D:\FO3ID\server\.venv\Scripts\python.exe' 'D:\fifaol3\pack_limits\elite\test_install.py'
exit $LASTEXITCODE
