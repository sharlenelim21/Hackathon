@echo off
REM RAKAN - set up and run the Streamlit app (Windows)
setlocal EnableDelayedExpansion
cd /d "%~dp0"

REM 1. Create the virtual environment if it doesn't exist yet
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3.12 -m venv .venv 2>nul || python -m venv .venv
)

REM 2. Use the shared requirements.txt after merging, otherwise the frontend one
if exist "requirements.txt" (
    set "REQ=requirements.txt"
) else (
    set "REQ=requirements-frontend.txt"
)

REM 3. Install or update packages (fast when already installed)
echo Installing packages from !REQ!...
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -r "!REQ!"

REM 4. Start the app
".venv\Scripts\python.exe" --version
".venv\Scripts\python.exe" -m streamlit run app.py

pause
