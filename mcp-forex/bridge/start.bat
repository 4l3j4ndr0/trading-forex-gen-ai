@echo off
echo ═══════════════════════════════════════════
echo   MT5 Bridge — Starting...
echo ═══════════════════════════════════════════
echo.

:: Load environment variables from .env
if exist .env (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" set "%%a=%%b"
    )
)

:: Start the bridge
python app.py

pause
