@echo off
cd /d "%~dp0\.."
if "%~1"=="" (
  echo Drag a backup .sql file onto restore.bat to restore it.
  pause
  exit /b
)
echo WARNING: this replaces ALL current data with the backup "%~1".
set /p OK=Type YES to continue: 
if not "%OK%"=="YES" exit /b
docker compose exec -T db psql -U library -d library -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose exec -T db psql -U library -d library < "%~1"
docker compose restart backend
echo Restore finished.
pause
