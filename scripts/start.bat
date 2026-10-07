@echo off
cd /d "%~dp0\.."
if not exist .env copy .env.example .env
echo Starting the library system... (the first start can take several minutes)
docker compose up -d --build
echo.
echo Open http://localhost:8080 in your browser.
pause
