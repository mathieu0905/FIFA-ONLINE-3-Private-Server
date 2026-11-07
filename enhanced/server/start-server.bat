@echo off
cd /d D:\FO3ID\server
set FO3_GAME=D:\FO3ID\32795
set FO3_LANGUAGE=chi
set FO3_MAX_GRADE=20
if not exist gamedata\fifadb.sqlite (
 echo Missing player database. Complete client setup first.
 pause
 exit /b 1
)
.venv\Scripts\python.exe start_all.py
if errorlevel 1 (
 echo Server startup failed. See the error above.
 pause
 exit /b 1
)


