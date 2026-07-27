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
  echo [1/4] Creating virtual environment...
  %PYEXE% -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Could not create the virtual environment.
    if not "%~1"=="quiet" pause
    exit /b 1
  )
) else (
  echo [1/4] Virtual environment already exists.
)

REM --- 4. Install dependencies ---
REM     llama-cpp-python ships no wheel on PyPI for many Windows/Python combos,
REM     so pip tries to compile it and fails on any machine without CMake and a
REM     C++ toolchain. The project's own wheel index carries pre-built CPU
REM     wheels, so we point pip at it first - that is what makes the local AI
REM     tier install on a plain client machine with no build tools.
REM     If it still fails we retry WITHOUT it: the app runs on the Groq /
REM     rule-based tiers regardless.
set "LOCALAI=1"
set "LLAMA_WHEELS=https://abetlen.github.io/llama-cpp-python/whl/cpu"
echo [2/4] Installing dependencies (this can take a minute or two)...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt --extra-index-url %LLAMA_WHEELS%
if errorlevel 1 (
  echo.
  echo [WARN] The full install failed - usually this is llama-cpp-python,
  echo        which needs build tools on some machines.
  echo        Retrying without the local-AI package...
  echo.
  set "LOCALAI=0"
  ".venv\Scripts\python.exe" -c "open('.core-requirements.tmp','w').write(''.join(l for l in open('requirements.txt') if 'llama-cpp-python' not in l))"
  ".venv\Scripts\python.exe" -m pip install -r .core-requirements.tmp
  set "CORERC=!errorlevel!"
  if exist ".core-requirements.tmp" del ".core-requirements.tmp" >nul 2>nul
  if not "!CORERC!"=="0" (
    echo.
    echo [ERROR] Dependency installation failed.
    echo         Check your internet connection and try running setup.bat again.
    echo         If it keeps failing, send the text above to your developer.
    if not "%~1"=="quiet" pause
    exit /b 1
  )
)

REM --- 5. Create .env from template (never overwrite an existing one) ---
if not exist ".env" (
  echo [3/4] Creating .env from template...
  copy ".env.example" ".env" >nul
) else (
  echo [3/4] .env already present - leaving it untouched.
)

REM --- 6. Download the local quantised AI model (best effort, never fatal) ---
REM     A failure here is fine: app/ai.py falls back to Groq and then to the
REM     built-in rule-based generator, so setup must warn and carry on.
set "MODELOK=0"
echo.
echo [4/4] Downloading local AI model, this is a one-time ~4GB download...
echo       (a smaller ~2.4GB model is chosen automatically on low-RAM machines)
echo       You can skip this now and run "python -m app.setup_model" later.
echo.
if "!LOCALAI!"=="0" (
  echo       Skipped: llama-cpp-python is not installed, so the local model
  echo       could not be used even if it were downloaded.
) else (
  ".venv\Scripts\python.exe" -m app.setup_model
  if errorlevel 1 (
    echo.
    echo       [WARN] The local AI model could not be downloaded.
    echo              This is NOT fatal - setup will continue.
    echo              The app will use the Groq cloud tier if you set a
    echo              GROQ_API_KEY in .env, otherwise the built-in
    echo              rule-based generator. Both work fine.
    echo              To retry later:  python -m app.setup_model
  ) else (
    set "MODELOK=1"
  )
)

echo.
echo ==================================================
echo    Setup complete!
echo.
if "!MODELOK!"=="1" (
  echo    Local AI is ready - the app runs a quantised model on
  echo    this computer. No API key needed, works offline, free.
) else (
  echo    Local AI is NOT installed. The app still works:
  echo      - open ".env" with Notepad and paste a GROQ_API_KEY
  echo        to use the free Groq cloud tier, or
  echo      - use it as-is with the built-in rule-based generator.
  echo    To try the local model again:  python -m app.setup_model
)
echo.
echo    Next step: double-click  run.bat
echo ==================================================
if not "%~1"=="quiet" pause
endlocal
