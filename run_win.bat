@echo off
REM Conscious Pebble - Windows Launcher (Lite/Text-Only Version)
REM
REM This script starts Conscious Pebble WITHOUT voice services.
REM Voice is disabled on Windows because MLX is Apple Silicon only.
REM
REM Usage:
REM   Double-click this file or run from command prompt:
REM   run_win.bat

setlocal

REM Get script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Virtual environment
set "VENV_DIR=%SCRIPT_DIR%.pebble_env"

REM Check if venv exists
if not exist "%VENV_DIR%" (
    echo [ERROR] Virtual environment not found!
    echo.
    echo Please run setup_win.bat first:
    echo   setup_win.bat
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo          Conscious Pebble - Starting Services
echo                    (Text-Only Mode)
echo ============================================================
echo.

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

echo NOTE: Voice features are NOT available on Windows.
echo       Using text-only mode.
echo.
echo Starting Home Control GUI on port 7860...
echo.

REM Open browser after delay
start "" cmd /c "timeout /t 3 >nul && start http://localhost:7860"

REM Start the GUI
echo ============================================================
echo   Conscious Pebble is running!
echo ============================================================
echo.
echo   GUI:  http://localhost:7860
echo.
echo   Press Ctrl+C to stop
echo.

python home_control.py

call deactivate