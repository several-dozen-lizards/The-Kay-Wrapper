@echo off
title Je Ne Sais Quoi
cd /d "%~dp0"

echo ============================================
echo   JE NE SAIS QUOI
echo   The indefinable quality.
echo ============================================
echo.

:: Check for .env file
if not exist ".env" (
    echo   No .env found. Copying template...
    if exist "env_template.txt" (
        copy env_template.txt .env >nul
    )
    echo   Edit .env with your API key, then run this again.
    pause
    exit /b 1
)

:: Check for persona config
if not exist "persona\persona_config.json" (
    echo   No persona configured. Running setup wizard...
    echo.
    python setup_wizard.py
    echo.
    if not exist "persona\persona_config.json" (
        echo   Setup cancelled. Run this again when ready.
        pause
        exit /b 1
    )
)

echo   Choose mode:
echo     1. Terminal only (text in this window)
echo     2. Godot UI (start backend + open UI)
echo.
set /p MODE="  Mode [1]: "
if not defined MODE set MODE=1
if "%MODE%"=="2" goto :ui_mode

:terminal_mode
echo.
echo   Starting in terminal mode...
echo   Type 'quit' or 'exit' to end session.
echo   ============================================
echo.
python main.py
goto :end

:ui_mode
echo.
echo   Starting Python backend on port 8780...
start /B python main.py --ui --room-port 8780
echo   Waiting for backend to initialize...
timeout /t 5 /nobreak > nul
echo.

if exist "godot-ui\JNSQ.exe" (
    echo   Launching Godot UI...
    start "" "godot-ui\JNSQ.exe"
) else if exist "godot-ui\Companion.exe" (
    echo   Launching Godot UI...
    start "" "godot-ui\Companion.exe"
) else (
    echo   ============================================
    echo   Backend is RUNNING on ws://localhost:8780
    echo   ============================================
    echo.
    echo   Open godot-ui/project.godot in Godot Engine
    echo   and press F5 to connect.
)

echo.
echo   Backend running in background.
echo   Press Ctrl+C or close this window to stop.
echo.

:wait_loop
timeout /t 60 /nobreak >nul
goto :wait_loop

:end
echo.
echo   Session ended.
pause
