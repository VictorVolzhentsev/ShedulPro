@echo off
chcp 65001 >nul
echo =============================
echo   ShedulPro Bot - Stopping
echo =============================
echo.

:: Find and kill the bot process by window title
taskkill /FI "WINDOWTITLE eq ShedulPro Bot" /F >nul 2>&1

:: Also kill any python running main.py (fallback)
for /f "tokens=2" %%a in ('wmic process where "commandline like '%%main.py%%' and name='python.exe'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo Bot stopped.
timeout /t 2 >nul
