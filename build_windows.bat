@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo     Building CDC Excel Matcher for Windows (.exe)
echo ===================================================
echo.

rem Check if Python is installed and accessible
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in your PATH!
    echo Please install Python 3.10, 3.11, or 3.12 from python.org or via:
    echo     winget install Python.Python.3.11
    echo (Make sure to check "Add Python to PATH" during installation)
    pause
    exit /b 1
)

echo [1/3] Checking and installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller pywebview

echo.
echo [2/3] Building Windows Executable with PyInstaller...
python -m PyInstaller desktop.spec --noconfirm --clean

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Build failed! Check the output messages above.
    pause
    exit /b 1
)

echo.
echo [3/3] Build Succeeded!
echo ===================================================
echo Your Windows executable is ready at:
echo %~dp0dist\CDC_Excel_Matcher\CDC_Excel_Matcher.exe
echo ===================================================
echo.
echo You can run it directly by double-clicking CDC_Excel_Matcher.exe
echo or copy the 'dist\CDC_Excel_Matcher' folder anywhere!
echo.
pause
