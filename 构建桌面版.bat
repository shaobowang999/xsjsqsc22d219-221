@echo off
setlocal
cd /d "%~dp0"

set "PYEXE=%~dp0python\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

echo Building SQSC Canvas desktop application...
"%PYEXE%" -m PyInstaller --noconfirm --clean "三千思创无线画布.spec"
if errorlevel 1 (
  echo.
  echo Build failed.
  pause
  exit /b 1
)

echo.
echo Build complete: dist\三千思创无线画布\三千思创无线画布.exe
pause
