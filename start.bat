@echo off
title NetCoop AI — Multi-Agent NOC Platform
echo ========================================================
echo   NetCoop AI: Multi-Agent Network Fault Diagnosis
echo   IIT Bhubaneswar Agentic AI Grand Finale
echo ========================================================
echo.

echo [1/3] Running automated verification test suite...
python -m pytest backend/tests -v
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Automated tests failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Launching FastAPI Backend Server on port 8000...
start "NetCoop AI - FastAPI Backend" cmd /k "cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo.
echo [3/3] Launching React + Vite Frontend on port 5173...
start "NetCoop AI - Vite Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================================
echo   NetCoop AI is now ONLINE!
echo   Dashboard: http://localhost:5173
echo   FastAPI Docs: http://127.0.0.1:8000/docs
echo ========================================================
pause
