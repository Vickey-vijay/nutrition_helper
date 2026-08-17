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

REM If port 8000 is taken, work out WHAT is on it before assuming it is us.
REM Something else occupying the port would otherwise send the user's browser
REM to an unrelated application under our name.
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul 2>nul
if not errorlevel 1 (
  ".venv\Scripts\python.exe" -c "import json,urllib.request,sys; sys.exit(0 if json.loads(urllib.request.urlopen('http://localhost:8000/api/health',timeout=4).read()).get('status')=='ok' else 1)" >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Port 8000 is already in use by another program, so NutriMind
    echo         cannot start. Close whatever is using port 8000 and try again.
    echo.
    echo         To see what is using it, run:
    echo             netstat -ano ^| findstr :8000
    echo.
    pause
    exit /b 1
  )
  echo NutriMind AI is already running on port 8000.
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
