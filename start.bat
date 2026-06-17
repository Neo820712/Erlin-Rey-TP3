@echo off
REM start.bat - Levanta el entorno completo para la demo del TP3.
REM   - Ventana 1: backend FastAPI en http://localhost:8000 (con PYTHONPATH=.)
REM   - Ventana 2: frontend (dashboard) en http://localhost:3000
REM   - Abre el dashboard en el navegador por defecto.
REM Doble click sobre este archivo arranca todo.

cd /d "%~dp0"

start "Backend API :8000" cmd /k "set PYTHONPATH=. && uv run uvicorn backend.main:app --reload --port 8000"
start "Frontend :3000" cmd /k "cd frontend && python -m http.server 3000"

timeout /t 2 /nobreak >nul
start "" "http://localhost:3000"
