@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 (
  echo Install Python 3.12 for Windows from python.org, then run Setup.cmd again.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Installation failed. Check your network and try again.
  pause
  exit /b 1
)
echo Floaty is ready. Double-click Floaty.cmd to launch.
pause
