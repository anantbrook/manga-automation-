@echo off
echo ===================================================
echo   Setting up MangaFire PRO local environment...
echo ===================================================

echo.
echo [1/3] Setting up Python Backend...
cd backend
if not exist "venv\" (
    python -m venv venv
    echo Created virtual environment.
)
call venv\Scripts\activate.bat
pip install -r requirements.txt
echo Installed backend dependencies.

echo.
echo Initializing database...
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"
echo Database initialized.
call deactivate
cd ..

echo.
echo [2/3] Setting up React Frontend...
cd frontend
call npm install
echo Installed frontend dependencies.
cd ..

echo.
echo [3/3] Setting up Environment Variables...
if not exist ".env" (
    copy .env.example .env
    echo Created .env file. Please edit it to add your Telegram Bot Token!
)

echo.
echo ===================================================
echo Setup Complete! You can now run start_manga_fire.bat
echo ===================================================
pause
