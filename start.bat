@echo off
title VoiceSQL

:: Load GROQ_API_KEY from .env file
if exist .env (
    for /f "tokens=1,2 delims==" %%a in (.env) do (
        if "%%a"=="GROQ_API_KEY" set GROQ_API_KEY=%%b
    )
)

if "%GROQ_API_KEY%"=="" (
    echo ERROR: GROQ_API_KEY not set.
    echo Please copy .env.example to .env and add your key.
    echo Get a free key at https://console.groq.com
    pause
    exit /b 1
)

echo Starting VoiceSQL...
echo Open your browser at: http://localhost:5000
echo.

python backend\app.py
