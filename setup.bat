@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==================================================
echo    NutriMind AI  -  Setup
echo ==================================================
echo.

REM --- 1. Find a Python interpreter (python, then the py launcher) ---
set "PYEXE="
where python >nul 2>nul
if not errorlevel 1 set "PYEXE=python"

if not defined PYEXE (
  where py >nul 2>nul
  if not errorlevel 1 set "PYEXE=py -3"
)

if not defined PYEXE (
  echo [ERROR] Python was not found on this computer.
  echo.
  echo         1. Install Python 3.10 or newer from https://www.python.org/downloads/
  echo         2. During install, TICK the box "Add python.exe to PATH"
  echo         3. Restart this setup.bat after installing.
  echo.
  if not "%~1"=="quiet" pause
  exit /b 1
)

REM --- 2. Check the Python version is new enough ---
%PYEXE% -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] A Python installation was found, but it is older than 3.9.
  echo         Please install Python 3.10+ from https://www.python.org/downloads/
  echo         and make sure it is first on PATH, then run setup.bat again.
  echo.
  if not "%~1"=="quiet" pause
  exit /b 1
)
for /f "delims=" %%v in ('%PYEXE% -c "import sys; print(sys.version.split()[0])"') do set "PYVER=%%v"
echo Using Python %PYVER%
echo.

REM --- 3. Create virtual environment ---
if not exist ".venv" (
  echo [1/3] Creating virtual environment...
  %PYEXE% -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Could not create the virtual environment.
    if not "%~1"=="quiet" pause
    exit /b 1
  )
) else (
  echo [1/3] Virtual environment already exists.
)

REM --- 4. Install dependencies ---
echo [2/3] Installing dependencies (this can take a minute or two)...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [ERROR] Dependency installation failed.
  echo         Check your internet connection and try running setup.bat again.
  echo         If it keeps failing, send the text above to your developer.
  if not "%~1"=="quiet" pause
  exit /b 1
)

REM --- 5. Create .env from template (never overwrite an existing one) ---
if not exist ".env" (
  echo [3/3] Creating .env from template...
  copy ".env.example" ".env" >nul
) else (
  echo [3/3] .env already present - leaving it untouched.
)

echo.
echo ==================================================
echo    Setup complete!
echo.
echo    Optional: open the ".env" file with Notepad and paste
echo    your GROQ_API_KEY to enable live AI features.
echo    The app also works with NO key (a built-in fallback is used).
echo.
echo    Next step: double-click  run.bat
echo ==================================================
if not "%~1"=="quiet" pause
endlocal
