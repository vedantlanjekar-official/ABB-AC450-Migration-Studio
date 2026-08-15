@echo off
setlocal
cd /d "%~dp0"

set "PY=%~dp0.tools\python\python.exe"
if not exist "%PY%" set "PY=python"

echo Starting ABB AC450 Converter Services...
echo.
echo Launching FastAPI Backend on http://127.0.0.1:8002 ...
start "FastAPI Backend" cmd /k "cd /d "%~dp0" && "%PY%" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8002"

echo Launching Next.js Frontend on http://localhost:5180 ...
start "Next.js Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Services launched!
echo   Frontend: http://localhost:5180
echo   Backend:  http://127.0.0.1:8002/api/health
echo.
echo Open http://localhost:5180 in Google Chrome.
endlocal
