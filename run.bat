@echo off
setlocal
cd /d "%~dp0"

REM Ensure the environment is set up (silent if already done).
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found - running setup first...
  echo.
  call setup.bat quiet
  if errorlevel 1 exit /b 1
)

REM If something is already listening on port 8000, don't start a second
REM copy - just reopen the browser on the instance that's already running.
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul 2>nul
if not errorlevel 1 (
  echo NutriMind AI already appears to be running on port 8000.
  echo Opening your browser...
  start "" http://localhost:8000
  timeout /t 3 >nul
  exit /b 0
)

echo.
echo ==================================================
echo    NutriMind AI is starting...
echo    Open  http://localhost:8000  in your browser.
echo    Press Ctrl+C in this window to stop.
echo ==================================================
echo.

REM Open the browser a few seconds after the server starts.
start "" cmd /c "timeout /t 4 >nul & start http://localhost:8000"

REM Launch the server (foreground).
".venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000

endlocal
