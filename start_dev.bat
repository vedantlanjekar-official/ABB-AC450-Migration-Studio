@echo off
echo Starting ABB AC450 Converter Services...
echo.
echo Launching FastAPI Backend on http://localhost:8000 ...
start "FastAPI Backend" cmd /k "cd /d %~dp0 && python -m uvicorn backend.main:app --reload --port 8000"

echo Launching Next.js Frontend on http://localhost:5173 ...
start "Next.js Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Services launched! Open http://localhost:5173 in browser.
