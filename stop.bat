@echo off
setlocal
chcp 65001 >nul

echo =============================
echo   ShedulPro Bot - Stopping
echo =============================
echo.

powershell -NoProfile -Command "& { $processes = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*main.py*' }; foreach ($process in $processes) { Stop-Process -Id $process.ProcessId -Force } }"

echo Bot stopped.
