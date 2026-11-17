@echo off
cd /d "%~dp0"
if not exist .env (
  echo Missing .env. Run scripts/bootstrap_env.py first as described in README.md.
  pause
  exit /b 1
)
docker compose up -d --build --wait
if errorlevel 1 (
  echo Docker startup failed. See the messages above.
  docker compose logs --tail=50
) else (
  echo Foodgram is available at http://localhost:8080
  start "" "http://localhost:8080"
)
pause
