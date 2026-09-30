@echo off
rem Yumizoo Shorts: drag a video (or a few videos) onto this file. You get 2-3 Shorts from each video.
cd /d "%~dp0"
set PY=python
python --version >nul 2>nul || set PY=py -3
if "%~1"=="" (
    echo Drag a video file onto make_short.bat. The Shorts are saved next to the video.
    pause
    exit /b 1
)
%PY% -c "import PIL, numpy, imageio_ffmpeg" >nul 2>nul || %PY% -m pip install pillow numpy imageio-ffmpeg
set FAILED=
for %%V in (%*) do (
    %PY% make_short.py "%%~V" || set FAILED=1
)
if defined FAILED (
    echo.
    echo Something went wrong. Take a photo of this window and send it to Claude.
) else (
    start "" "%~dp1"
)
pause
