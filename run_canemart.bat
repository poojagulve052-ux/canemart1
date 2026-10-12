@echo off
title CaneMart - Sugarcane Management System
cd /d "%~dp0"
echo ========================================================
echo        CaneMart - Sugarcane Management Platform
echo ========================================================
echo.
echo Starting CaneMart Web Server on port 5000...
echo Opening browser at http://127.0.0.1:5000 ...
echo.
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:5000"
python app.py
pause
