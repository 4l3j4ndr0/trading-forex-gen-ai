@echo off
echo ═══════════════════════════════════════════
echo   MT5 Bridge — Installation
echo ═══════════════════════════════════════════
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Install Python 3.12+ from python.org
    pause
    exit /b 1
)

:: Install dependencies
echo Installing Python packages...
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Failed to install packages
    pause
    exit /b 1
)

echo.
echo ✅ Installation complete!
echo.
echo Next steps:
echo   1. Install MetaTrader 5 from XM: https://www.xm.com/mt5
echo   2. Login with your demo account credentials
echo   3. Copy .env.example to .env and fill in your details
echo   4. Run: start.bat
echo.
pause
