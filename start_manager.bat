@echo off
setlocal

:: Set title
title PDFLibrary Server Manager

:: Check for Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python not found! Please install Python 3.11+
    pause
    exit /b 1
)

:: Activate Virtual Environment if exists (assuming vendor or typical venv)
if exist "vendor\python\python.exe" (
    set "PYTHON_EXEC=vendor\python\python.exe"
) else (
    set "PYTHON_EXEC=python"
)

:: Run Manager
echo Starting Server Manager...
%PYTHON_EXEC% -m manager.main
if %errorlevel% neq 0 (
    echo Manager crashed or closed with error.
    pause
)
endlocal
