@echo off
setlocal
cd /d "%~dp0\.."
set "VENV_PY=%CD%\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
  echo Creating Python virtual environment...
  py -3 -m venv .venv
  if errorlevel 1 (
    echo Could not create the virtual environment. Install Python 3.11 or newer from https://www.python.org/downloads/windows/
    pause
    exit /b 1
  )
  "%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
  if errorlevel 1 (
    echo ClipGIF requires Python 3.11 or newer. Install it from https://www.python.org/downloads/windows/
    pause
    exit /b 1
  )
)
"%VENV_PY%" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo Could not install Python dependencies. Check your internet connection and try again.
  pause
  exit /b 1
)
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo ffmpeg/ffprobe not found. Install with: winget install Gyan.FFmpeg
  pause
  exit /b 1
)
where ffprobe >nul 2>nul
if errorlevel 1 (
  echo ffprobe not found. Install ffmpeg from https://ffmpeg.org/download.html and add its bin folder to PATH.
  pause
  exit /b 1
)
if "%CLIPGIF_PORT%"=="" set "CLIPGIF_PORT=8000"
echo ClipGIF will be available at http://127.0.0.1:%CLIPGIF_PORT%
start "ClipGIF server" /min "%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port %CLIPGIF_PORT%
"%VENV_PY%" scripts\wait_for_server.py %CLIPGIF_PORT%
if errorlevel 1 goto server_failed
start "" "http://127.0.0.1:%CLIPGIF_PORT%"
echo ClipGIF is running. Close the minimized "ClipGIF server" window to stop it.
endlocal
exit /b 0
:server_failed
echo ClipGIF server did not become ready. Check the server window for errors.
pause
exit /b 1
