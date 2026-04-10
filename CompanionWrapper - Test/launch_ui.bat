@echo off
echo ============================================
echo   Companion Wrapper UI — Starting Up
echo ============================================
echo.

if not exist "persona\persona_config.json" (
    echo   No persona found. Running setup wizard...
    echo.
    python setup_wizard.py
    echo.
)

if not exist ".env" (
    echo   No .env found. Copying template...
    copy env_template.txt .env
    echo   Edit .env with your API key, then run this again.
    pause
    exit /b 1
)

echo   Launching UI...
python companion_ui.py
pause
