@echo off
echo ============================================
echo   Companion Wrapper — Starting Up
echo ============================================
echo.

:: Check for persona config
if not exist "persona\persona_config.json" (
    echo  No persona found. Running setup wizard...
    echo.
    python setup_wizard.py
    echo.
)

:: Check for .env
if not exist ".env" (
    echo  No .env found. Copying template...
    copy env_template.txt .env
    echo  Edit .env with your API key, then run this again.
    pause
    exit /b
)

echo  Loading persona...
python main.py
pause
