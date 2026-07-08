@echo off
REM ============================================================
REM  NutriMind AI - ONE-CLICK launcher
REM  Installs everything (first run) and starts the app.
REM ============================================================
setlocal
cd /d "%~dp0"
call setup.bat quiet
if errorlevel 1 exit /b 1
call run.bat
endlocal
