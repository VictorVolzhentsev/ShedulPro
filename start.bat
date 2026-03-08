@echo off
chcp 65001 >nul
echo =============================
echo   ShedulPro Bot - Starting
echo =============================
echo.

:: Check if already running
tasklist /FI "WINDOWTITLE eq ShedulPro Bot" 2>NUL | find /I "python" >NUL
if not errorlevel 1 (
    echo Bot is already running!
    pause
    exit /b
)

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not found. Downloading Python 3.12 installer...
    curl -o python-installer.exe "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    if exist python-installer.exe (
        echo Installing Python 3.12 silently... This may take a few minutes.
        start /wait python-installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
        echo Python installed successfully!
        del python-installer.exe
        echo.
        echo ========================================================
        echo IMPORTANT: Please CLOSE this window and run start.bat again!
        echo ^(This is required to update the system PATH variables^)
        echo ========================================================
        pause
        exit /b
    ) else (
        echo Failed to download Python installer. Please install it manually.
        pause
        exit /b
    )
)

:: Check for virtual environment and create if missing
if not exist ".venv" (
    echo Virtual environment not found. Creating one...
    python -m venv ".venv"
    echo Installing dependencies...
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)

:: Start the bot
echo Starting bot...
title ShedulPro Bot
.venv\Scripts\python.exe main.py

:: If bot exits
echo.
echo Bot stopped.
pause