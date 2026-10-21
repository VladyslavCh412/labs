@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Setting up local Python environment...
  py -m venv .venv
  if errorlevel 1 goto failed
  ".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" launch.py
if errorlevel 1 goto failed
goto end
:failed
echo.
echo Please check the error above. Python 3.12+ is required.
pause
:end
