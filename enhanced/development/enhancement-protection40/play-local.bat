@echo off
setlocal
set "PSModulePath=%SystemRoot%\System32\WindowsPowerShell\v1.0\Modules;%ProgramFiles%\WindowsPowerShell\Modules"
cd /d D:\FO3ID\server
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -Command "if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 1}"
if errorlevel 1 (
 echo Please close FIFA Online 3 before starting the updated client.
 pause
 exit /b 1
)
.venv\Scripts\python.exe patches\protection40_preflight.py
if errorlevel 1 (
 pause
 exit /b 1
)
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File patches\install-zh.ps1
if errorlevel 1 (
 pause
 exit /b 1
)
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File patches\install-grade20.ps1
if errorlevel 1 (
 pause
 exit /b 1
)
rem The game is closed: restart our managed services to load installed updates.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File stop-server.ps1
if errorlevel 1 (
 pause
 exit /b 1
)
.venv\Scripts\python.exe -c "import time; time.sleep(1)"
start "FO3ID server" cmd /c start-server.bat
.venv\Scripts\python.exe wait_services.py
if errorlevel 1 (
 pause
 exit /b 1
)
set __COMPAT_LAYER=RunAsInvoker
start "" launcher\fifalauncher.exe

