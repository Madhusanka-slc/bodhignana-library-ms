@echo off
cd /d "%~dp0\.."
if not exist backups mkdir backups
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set STAMP=%%i
docker compose exec -T db pg_dump -U library -d library > backups\library_%STAMP%.sql
echo Backup saved to backups\library_%STAMP%.sql
echo Copy this file to a USB drive or Google Drive to keep it safe.
pause
