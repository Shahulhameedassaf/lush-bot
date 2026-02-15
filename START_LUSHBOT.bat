@echo off
title Starting LushBot

echo ================================
echo    Starting LushBot Services
echo ================================
echo.

echo [1/3] Starting Qdrant...
docker start qdrant 2>nul
if errorlevel 1 (
    docker run -d -p 6333:6333 -v qdrant_data:/qdrant/storage --name qdrant qdrant/qdrant >nul 2>&1
)
echo      Done!

echo [2/3] Starting Ollama...
start /MIN ollama serve
echo      Done!

echo [3/3] Starting Flask server...
timeout /t 3 /nobreak >nul
cd backend
start /MIN cmd /k "..\\.venv\\Scripts\\activate && python app.py"
echo      Done!

echo.
echo ================================
echo   LushBot Started!
echo ================================
echo.
echo Opening browser in 5 seconds...
timeout /t 5 /nobreak >nul
start http://localhost:5000

exit
