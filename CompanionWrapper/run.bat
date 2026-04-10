@echo off
title Companion Wrapper
echo.
echo  ============================================
echo   Companion Wrapper
echo  ============================================
echo.

:: Navigate to script directory
cd /d "%~dp0"

:: Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found. Install Python 3.10+ first.
    echo  https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check for persona config — run wizard if missing
if not exist "persona\persona_config.json" (
    echo  No companion configured yet. Let's set one up!
    echo.
    python setup_wizard.py
    echo.
    if not exist "persona\persona_config.json" (
        echo  Setup cancelled. Run this again when ready.
        pause
        exit /b 1
    )
)

:: Check for .env — copy template if missing
if not exist ".env" (
    echo  No .env file found. Creating from template...
    if exist "env_template.txt" (
        copy env_template.txt .env >nul
        echo.
        echo  ================================================
        echo   IMPORTANT: Edit .env with your API key!
        echo   Open .env in any text editor and paste your key.
        echo  ================================================
        echo.
        echo  Get an API key from:
        echo    Anthropic: https://console.anthropic.com/
        echo    OpenAI:    https://platform.openai.com/api-keys
        echo.
        echo  After adding your key, run this script again.
        pause
        exit /b 1
    ) else (
        echo  ERROR: env_template.txt not found.
        pause
        exit /b 1
    )
)

:: Check for dependencies
echo  Checking dependencies...
pip show anthropic >nul 2>&1
if errorlevel 1 (
    echo  Installing dependencies...
    pip install -r requirements.txt --break-system-packages -q
    echo  Done.
)

:: Read companion name from persona config (best-effort)
for /f "tokens=2 delims=:," %%a in ('findstr "display_name" persona\persona_config.json 2^>nul') do (
    set "COMP_NAME=%%~a"
)
if defined COMP_NAME (
    set "COMP_NAME=%COMP_NAME: =%"
    set "COMP_NAME=%COMP_NAME:"=%"
    title %COMP_NAME% - Companion Wrapper
    echo  Companion: %COMP_NAME%
) else (
    echo  Companion: [configured]
)
echo.

:: Detect available modes
set HAS_GODOT=0
if exist "godot-ui\Companion.exe" set HAS_GODOT=1

if %HAS_GODOT%==1 (
    echo  Choose mode:
    echo    1. Terminal mode (text only)
    echo    2. Godot UI (graphical)
    echo.
    set /p MODE="  Mode [2]: "
    if not defined MODE set MODE=2
) else (
    set MODE=1
)

if "%MODE%"=="2" goto :godot_mode

:terminal_mode
echo.
echo  Starting in terminal mode...
echo  Type 'quit' or 'exit' to end session.
echo  ============================================
echo.
python main.py
goto :end

:godot_mode
echo.
echo  Starting backend + Godot UI...
echo  (Close this window to stop the backend)
echo.

:: Start Python backend with private room server in background
start /b python main.py --ui --room-port 8780

:: Wait for backend to start
echo  Waiting for backend...
timeout /t 3 /nobreak >nul

:: Launch Godot UI
start "" "godot-ui\Companion.exe"

:: Keep this window open (backend runs here)
echo.
echo  Backend running on ws://localhost:8780
echo  Press Ctrl+C or close this window to stop.
echo.

:: Wait indefinitely (backend is running in background)
:wait_loop
timeout /t 60 /nobreak >nul
goto :wait_loop

:end
echo.
echo  Session ended.
pause
