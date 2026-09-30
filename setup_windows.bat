@echo off
rem Yumizoo: installs everything and makes Episode 1. Just double-click this file.
cd /d "%~dp0"
set PY=python
python --version >nul 2>nul || set PY=py -3
echo Using:
%PY% --version
echo.
echo [1/3] Installing the Python libraries (a few minutes)...
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto error
echo.
echo [2/3] Downloading the voice and the font (only the first time)...
%PY% get_assets.py
if errorlevel 1 goto error
echo.
echo [3/3] Making Episode 1. This can take 20-40 minutes, keep this window open...
%PY% make_episode1.py
if errorlevel 1 goto error
echo.
echo Done! The video is in the "output" folder.
start "" "%~dp0output"
pause
exit /b 0

:error
echo.
echo Something went wrong. Take a photo of this window and send it to Claude.
pause
exit /b 1
