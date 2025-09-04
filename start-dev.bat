@echo off
echo Starting AI HTML Builder Development Environment...

REM Check if Python virtual environment exists
if not exist "backend\venv" (
    echo Creating Python virtual environment...
    cd backend
    python -m venv venv
    cd ..
)

REM Start backend in new terminal
echo Starting FastAPI backend...
start cmd /k "cd backend && venv\Scripts\activate && pip install -r requirements.txt && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a moment then start frontend
timeout /t 3 /nobreak >nul
echo Starting React frontend...
start cmd /k "cd frontend && npm install && npm run dev"

echo Both services starting in separate terminals...
echo Frontend: http://localhost:5173
echo Backend: http://localhost:8000
pause