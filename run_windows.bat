@echo off
cd /d "%~dp0"
title NandN International Web Server
echo ========================================================
echo   NandN INTERNATIONAL - STARTING LOCAL WEB SERVER
echo ========================================================
echo.
echo Checking dependencies...
python -m pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    py -m pip install -r requirements.txt >nul 2>&1
)

echo.
echo Starting Flask web application...
echo Open your browser at: http://127.0.0.1:5000
echo.
python app.py
if errorlevel 1 (
    py app.py
)
pause
