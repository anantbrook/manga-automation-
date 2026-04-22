#!/bin/bash
echo "🔥 Starting MangaFire PRO Stack..."

# Set trap to kill all background processes on exit
trap 'kill $(jobs -p) 2>/dev/null; exit' SIGINT SIGTERM EXIT

# 1. Start Redis (if redis-server exists locally, otherwise assume Docker/remote)
if command -v redis-server &> /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes
else
    echo "⚠️ Redis server not found locally. Ensure Redis is running (e.g. via Docker)."
fi

# 2. Start Celery Worker & Beat
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
fi
echo "Starting Celery Worker..."
celery -A tasks.celery worker --loglevel=info > /tmp/celery_worker.log 2>&1 &
echo "Starting Celery Beat..."
celery -A tasks.celery beat --loglevel=info > /tmp/celery_beat.log 2>&1 &

# 3. Start Backend Orchestrator (Flask + Bot)
echo "Starting Python Backend + Bot..."
python3 run.py > /tmp/flask_bot.log 2>&1 &
cd ..

# 4. Start Frontend
echo "Starting React Frontend..."
cd frontend
npm run dev > /tmp/vite.log 2>&1 &
cd ..

echo ""
echo "✅ All services started!"
echo "   - Frontend: http://localhost:5173"
echo "   - Backend API: http://localhost:5000"
echo "   - Logs: tail -f /tmp/flask_bot.log /tmp/vite.log /tmp/celery_worker.log"
echo "Press Ctrl+C to stop all services."

# Wait indefinitely, letting the trap catch the exit
wait
