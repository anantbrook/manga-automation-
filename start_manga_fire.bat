@echo off
echo ===================================================
echo   Starting MangaFire PRO Stack...
echo ===================================================

echo.
echo NOTE: Ensure Redis is running (e.g., WSL, Docker, or native Windows port)
echo.

cd backend
if exist "venv\" (
    call venv\Scripts\activate.bat
)

echo Starting Celery Worker...
start "Celery Worker" cmd /c "celery -A tasks.celery worker --loglevel=info"

echo Starting Celery Beat...
start "Celery Beat" cmd /c "celery -A tasks.celery beat --loglevel=info"

echo Starting Python Backend + Telegram Bot...
start "MangaFire Backend" cmd /k "python run.py"
cd ..

echo Starting React Frontend...
cd frontend
start "MangaFire Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ===================================================
echo All services started in separate windows!
echo    - Frontend: http://localhost:5173
echo    - Backend API: http://localhost:5000
echo ===================================================
echo Close the individual windows to stop the services.
pause
