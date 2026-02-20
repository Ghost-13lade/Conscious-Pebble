@echo off
REM Conscious Pebble - Windows Installer (Lite/Text-Only Version)
REM
REM This script sets up Conscious Pebble on Windows WITHOUT voice services.
REM MLX (Apple Silicon) is not available on Windows.
REM
REM Usage:
REM   Double-click this file or run from command prompt:
REM   setup_win.bat

setlocal enabledelayedexpansion

echo ============================================================
echo        Conscious Pebble - Windows Installer
echo           Lite Version (Text-Only, No Voice)
echo ============================================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM =============================================================================
REM STEP 1: Check Prerequisites
REM =============================================================================
echo [Step 1/4] Checking prerequisites...

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.10+ from:
    echo   https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VER=%%i
echo [OK] Python found: %PYTHON_VER%

REM =============================================================================
REM STEP 2: Create Virtual Environment
REM =============================================================================
echo.
echo [Step 2/4] Creating virtual environment...

set "VENV_DIR=%SCRIPT_DIR%.pebble_env"

if exist "%VENV_DIR%" (
    echo   Virtual environment already exists. Removing old one...
    rmdir /s /q "%VENV_DIR%"
)

python -m venv "%VENV_DIR%"
echo [OK] Virtual environment created at: %VENV_DIR%

REM Activate venv
call "%VENV_DIR%\Scripts\activate.bat"

REM Upgrade pip
echo   Upgrading pip...
python -m pip install --upgrade pip --quiet

REM =============================================================================
REM STEP 3: Install Dependencies
REM =============================================================================
echo.
echo [Step 3/4] Installing Python dependencies...

set "REQUIREMENTS_FILE=%SCRIPT_DIR%requirements_win.txt"

if not exist "%REQUIREMENTS_FILE%" (
    echo [ERROR] requirements_win.txt not found!
    call deactivate
    pause
    exit /b 1
)

echo   Installing from requirements_win.txt...
pip install -r "%REQUIREMENTS_FILE%" --quiet

echo [OK] Dependencies installed

REM =============================================================================
REM STEP 4: Create Data Directory and Configuration
REM =============================================================================
echo.
echo [Step 4/4] Setting up data directory...

set "DATA_DIR=%SCRIPT_DIR%data"
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

REM Create .env file with voice disabled
set "ENV_FILE=%DATA_DIR%\.env"
if not exist "%ENV_FILE%" (
    echo   Creating initial .env file...
    (
        echo # Conscious Pebble Configuration - Windows
        echo # Voice services are DISABLED on Windows (MLX not available)
        echo.
        echo LLM_PROVIDER=OpenRouter
        echo OPENAI_BASE_URL=https://openrouter.ai/api/v1
        echo OPENAI_API_KEY=YOUR_API_KEY_HERE
        echo OPENAI_MODEL=openrouter/optimus-alpha
        echo.
        echo TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
        echo ALLOWED_USER_ID=
        echo.
        echo # Voice disabled on Windows
        echo VOICE_ENABLED=false
        echo SENSES_BASE_URL=http://localhost:8081
    ) > "%ENV_FILE%"
    echo [OK] Created .env file at: %ENV_FILE%
) else (
    echo [OK] .env file already exists
)

call deactivate

REM =============================================================================
REM COMPLETE
REM =============================================================================
echo.
echo ============================================================
echo               Installation Complete!
echo ============================================================
echo.
echo NOTE: Voice features are NOT available on Windows.
echo       This is a text-only version.
echo.
echo To start Conscious Pebble:
echo   run_win.bat
echo.
echo Or manually:
echo   1. .pebble_env\Scripts\activate.bat
echo   2. python home_control.py
echo.
echo Then open: http://localhost:7860
echo.
echo IMPORTANT: Configure your LLM provider in the Settings tab!
echo   For OpenRouter, get your API key from: https://openrouter.ai/keys
echo.
pause