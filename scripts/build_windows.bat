@echo off
setlocal
cd /d "%~dp0.."
echo ==================================================
echo LanShare Build Script for Windows
echo ==================================================

echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo Starting build process...
python scripts/build.py

if %errorlevel% neq 0 (
    echo.
    echo BUILD FAILED!
    pause
    exit /b 1
)

echo.
echo Build successful! Check the 'dist' folder for LanShare.exe
pause
endlocal
