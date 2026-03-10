@echo off
setlocal
chcp 65001 >nul

echo =============================
echo   ShedulPro Bot - Starting
echo =============================
echo.

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
pushd "%PROJECT_DIR%" >nul

set "MAIN_PY=%PROJECT_DIR%\main.py"
set "REQUIREMENTS=%PROJECT_DIR%\requirements.txt"
set "VENV_DIR=%PROJECT_DIR%\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "BOOTSTRAP_PYTHON="
set "RUNNING_COUNT=0"

for /f %%a in ('powershell -NoProfile -Command "(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*main.py*' }).Count"') do set "RUNNING_COUNT=%%a"
if not "%RUNNING_COUNT%"=="0" (
    echo Bot is already running!
    goto :done
)

call :python
if errorlevel 1 goto :fail

call :venv
if errorlevel 1 goto :fail

call :deps
if errorlevel 1 goto :fail

echo Starting bot...
title ShedulPro Bot
"%VENV_PYTHON%" "%MAIN_PY%"
goto :shutdown

:python
for /f "delims=" %%p in ('where python 2^>nul') do (
    if not defined BOOTSTRAP_PYTHON set "BOOTSTRAP_PYTHON=%%p"
)

if not defined BOOTSTRAP_PYTHON (
    for %%p in (
        "%LocalAppData%\Programs\Python\Python313\python.exe"
        "%LocalAppData%\Programs\Python\Python312\python.exe"
    ) do (
        if not defined BOOTSTRAP_PYTHON if exist %%~p set "BOOTSTRAP_PYTHON=%%~p"
    )
)

if defined BOOTSTRAP_PYTHON goto :eof

echo Python is not found. Downloading Python 3.13 installer...
set "PYTHON_INSTALLER=%TEMP%\python-installer.exe"
curl -L -o "%PYTHON_INSTALLER%" "https://www.python.org/ftp/python/3.13.2/python-3.13.2-amd64.exe"
if not exist "%PYTHON_INSTALLER%" (
    echo Failed to download Python installer.
    exit /b 1
)

echo Installing Python 3.13 silently... This may take a few minutes.
start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
del "%PYTHON_INSTALLER%" >nul 2>&1

for %%p in (
    "%LocalAppData%\Programs\Python\Python313\python.exe"
    "%LocalAppData%\Programs\Python\Python312\python.exe"
) do (
    if not defined BOOTSTRAP_PYTHON if exist %%~p set "BOOTSTRAP_PYTHON=%%~p"
)

if not defined BOOTSTRAP_PYTHON (
    echo Python installation finished, but python.exe was not found automatically.
    echo Install Python manually and run start.bat again.
    exit /b 1
)
goto :eof

:venv
set "REBUILD_VENV=0"

if not exist "%VENV_PYTHON%" set "REBUILD_VENV=1"
if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" -V >nul 2>&1
    if errorlevel 1 set "REBUILD_VENV=1"
)

if "%REBUILD_VENV%"=="1" (
    echo Recreating local virtual environment...
    if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%"
    "%BOOTSTRAP_PYTHON%" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Failed to create local virtual environment.
        exit /b 1
    )
)
goto :eof

:deps
"%VENV_PYTHON%" -c "import aiogram, aiohttp, aiosqlite, apscheduler, dotenv" >nul 2>&1
if errorlevel 1 (
    echo Installing project dependencies...
    "%VENV_PYTHON%" -m pip install --upgrade pip
    if errorlevel 1 (
        echo Failed to upgrade pip in the local environment.
        exit /b 1
    )
    "%VENV_PYTHON%" -m pip install -r "%REQUIREMENTS%"
    if errorlevel 1 (
        echo Failed to install project dependencies.
        exit /b 1
    )
)
goto :eof

:fail
echo.
echo Bot failed to start.
goto :done

:shutdown
echo.
echo Bot stopped.

:done
popd >nul
pause
