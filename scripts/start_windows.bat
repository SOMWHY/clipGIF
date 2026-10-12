@echo off
setlocal
cd /d "%~dp0\.."
set "VENV_PY=%CD%\.venv\Scripts\python.exe"
set "BASE_PY="

if exist "%VENV_PY%" goto check_existing_venv
goto check_system_python

:check_existing_venv
"%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if errorlevel 1 goto unsupported_venv
goto check_ffmpeg

:check_system_python
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 set "BASE_PY=py -3"
if defined BASE_PY goto check_ffmpeg
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 set "BASE_PY=python"
if defined BASE_PY goto check_ffmpeg
goto install_python

:install_python
where winget >nul 2>nul
if errorlevel 1 goto python_no_winget
echo ClipGIF requires Python 3.11 or newer, but no supported Python was found.
choice /C YN /M "Install Python 3.13 with winget now?"
if errorlevel 2 goto python_declined
winget install --id Python.Python.3.13 -e
if errorlevel 1 goto python_install_failed
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 set "BASE_PY=py -3"
if defined BASE_PY goto check_ffmpeg
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 set "BASE_PY=python"
if defined BASE_PY goto check_ffmpeg
goto python_not_visible

:check_ffmpeg
where ffmpeg >nul 2>nul
if errorlevel 1 goto install_ffmpeg
where ffprobe >nul 2>nul
if errorlevel 1 goto install_ffmpeg
goto prerequisites_ready

:install_ffmpeg
where winget >nul 2>nul
if errorlevel 1 goto ffmpeg_no_winget
echo ClipGIF requires both ffmpeg and ffprobe, but one or both were not found on PATH.
choice /C YN /M "Install FFmpeg with winget now?"
if errorlevel 2 goto ffmpeg_declined
winget install --id Gyan.FFmpeg.Shared -e
if errorlevel 1 goto ffmpeg_install_failed
where ffmpeg >nul 2>nul
if errorlevel 1 goto ffmpeg_not_visible
where ffprobe >nul 2>nul
if errorlevel 1 goto ffmpeg_not_visible
goto prerequisites_ready

:prerequisites_ready
if exist "%VENV_PY%" goto install_python_dependencies
if not defined BASE_PY goto python_not_visible
echo Creating Python virtual environment...
%BASE_PY% -m venv .venv
if errorlevel 1 goto venv_failed
"%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if errorlevel 1 goto venv_failed

:install_python_dependencies
"%VENV_PY%" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto dependencies_failed
if "%CLIPGIF_PORT%"=="" set "CLIPGIF_PORT=8000"
echo ClipGIF will be available at http://127.0.0.1:%CLIPGIF_PORT%
start "ClipGIF server" /min "%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port %CLIPGIF_PORT%
"%VENV_PY%" scripts\wait_for_server.py %CLIPGIF_PORT%
if errorlevel 1 goto server_failed
start "" "http://127.0.0.1:%CLIPGIF_PORT%"
echo ClipGIF is running. Close the minimized "ClipGIF server" window to stop it.
endlocal
exit /b 0

:unsupported_venv
echo The existing .venv uses Python older than 3.11 and cannot run ClipGIF.
echo Rename or remove the project .venv folder, then run start.bat again to recreate it.
goto startup_failed

:python_no_winget
echo winget is not available, so Python cannot be installed automatically.
echo Install Python 3.11 or newer from https://www.python.org/downloads/windows/
echo Ensure the Python launcher or python command is available, then run start.bat again.
goto startup_failed

:python_declined
echo Python installation was declined. Install Python 3.11 or newer from https://www.python.org/downloads/windows/
goto startup_failed

:python_install_failed
echo winget could not install Python. Check the output above or install it manually from https://www.python.org/downloads/windows/
goto startup_failed

:python_not_visible
echo Python installation completed, but Python is not available in this process yet.
echo Restart start.bat or open a new terminal and try again. If needed, install from https://www.python.org/downloads/windows/
goto startup_failed

:ffmpeg_no_winget
echo winget is not available, so FFmpeg cannot be installed automatically.
echo Download a Windows build from https://ffmpeg.org/download.html and add its bin folder to PATH.
echo The bin folder must contain both ffmpeg.exe and ffprobe.exe. Then run start.bat again.
goto startup_failed

:ffmpeg_declined
echo FFmpeg installation was declined. Install both ffmpeg and ffprobe, then run start.bat again.
goto startup_failed

:ffmpeg_install_failed
echo winget could not install FFmpeg. Check the output above or install it manually from https://ffmpeg.org/download.html
goto startup_failed

:ffmpeg_not_visible
echo FFmpeg installation completed, but ffmpeg or ffprobe is not available in this process yet.
echo Restart start.bat or open a new terminal and try again.
echo If needed, add the folder containing both executables to PATH.
goto startup_failed

:venv_failed
echo Could not create a Python virtual environment. Verify Python 3.11 or newer is available and try again.
goto startup_failed

:dependencies_failed
echo Could not install Python dependencies. Check your internet connection and try again.
goto startup_failed

:server_failed
echo ClipGIF server did not become ready. Check the server window for errors.
goto startup_failed

:startup_failed
pause
endlocal
exit /b 1
