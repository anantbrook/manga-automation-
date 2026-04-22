#!/bin/bash
echo "🚀 Setting up MangaFire PRO local environment..."

# 1. Backend Setup
echo "📦 Setting up Python Backend..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Created virtual environment."
fi
source venv/bin/activate
pip install -r requirements.txt
echo "✅ Installed backend dependencies."

# Setup Database
echo "🗄️ Initializing database..."
python3 -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"
echo "✅ Database initialized."
deactivate
cd ..

# 2. Frontend Setup
echo "🎨 Setting up React Frontend..."
cd frontend
npm install
echo "✅ Installed frontend dependencies."
cd ..

# 3. Environment Variables
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️ Created .env file. Please edit it to add your Telegram Bot Token!"
fi

echo "🎉 Setup Complete! You can now run the app using ./start_manga_fire.sh"
