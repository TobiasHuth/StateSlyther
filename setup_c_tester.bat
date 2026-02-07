@echo off
REM Interactive C State Machine Tester - Windows Setup Installer
REM This batch file helps with compiler setup and validation

setlocal enabledelayedexpansion

echo ========================================
echo C State Machine Tester Setup (Windows)
echo ========================================
echo.

REM Check for compiler
echo Checking for C compiler...
echo.

where gcc >nul 2>nul
if !ERRORLEVEL! equ 0 (
    for /f "tokens=*" %%i in ('gcc --version ^| findstr /R "gcc"') do (
        echo ✓ Found: %%i
    )
    set COMPILER=gcc
    goto compiler_found
)

where clang >nul 2>nul
if !ERRORLEVEL! equ 0 (
    for /f "tokens=*" %%i in ('clang --version ^| findstr /R "clang"') do (
        echo ✓ Found: %%i
    )
    set COMPILER=clang
    goto compiler_found
)

where cl >nul 2>nul
if !ERRORLEVEL! equ 0 (
    echo ✓ Found: Microsoft Visual C++
    set COMPILER=cl
    goto compiler_found
)

echo ✗ No C compiler found
echo.
echo Install a C compiler on Windows:
echo.
echo Option 1: MinGW (Recommended)
echo   • Download from: https://www.mingw-w64.org/
echo   • Or via Chocolatey: choco install mingw
echo.
echo Option 2: MSVC (Visual Studio)
echo   • Download from: https://visualstudio.microsoft.com/
echo   • Community edition is free
echo.
echo Option 3: LLVM/Clang
echo   • Download from: https://releases.llvm.org/
echo.
pause
exit /b 1

:compiler_found
echo.
echo Compiler: !COMPILER!
echo.

REM Check for Python
where python >nul 2>nul
if !ERRORLEVEL! equ 0 (
    for /f "tokens=*" %%i in ('python --version') do (
        echo ✓ Found: %%i
    )
) else (
    echo ✗ Python not found
    echo Install Python 3 from: https://www.python.org/
    pause
    exit /b 1
)

REM Check for Tkinter
python -c "import tkinter" >nul 2>nul
if !ERRORLEVEL! equ 0 (
    echo ✓ Tkinter available
) else (
    echo ✗ Tkinter not available
    echo Tkinter is usually included with Python
    echo If missing, reinstall Python and select "tcl/tk and IDLE"
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To test C code:
echo 1. Generate C code in StateSlyther
echo 2. Click "Test C Code (Compile)" button
echo 3. Use the interactive tester
echo.
echo To compile manually:
echo   gcc your_file.c -o state_machine -Wall -Wextra
echo   state_machine.exe
echo.
pause
