@echo off
REM Quick start script for PHP API server on Windows

echo.
echo ====================================
echo  Mathison Database API - Windows
echo ====================================
echo.

REM Check if PHP is in PATH
where php >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PHP_CMD=php
    echo Using PHP from PATH
) else (
    REM Try common PHP locations
    if exist "C:\php\php.exe" (
        set PHP_CMD=C:\php\php.exe
        echo Using PHP from C:\php\
    ) else if exist "C:\Program Files\PHP\php.exe" (
        set PHP_CMD="C:\Program Files\PHP\php.exe"
        echo Using PHP from C:\Program Files\PHP\
    ) else (
        echo ERROR: PHP not found!
        echo Please install PHP or update this script with your PHP path
        echo See WINDOWS_SETUP.md for installation instructions
        pause
        exit /b 1
    )
)

REM Check if config.php exists
if not exist "%~dp0config.php" (
    echo.
    echo WARNING: config.php not found!
    echo Please copy config.example.php to config.php and configure it
    echo.
    echo Running: copy config.example.php config.php
    copy "%~dp0config.example.php" "%~dp0config.php"
    echo.
    echo Please edit api-server\config.php with your database credentials
    pause
)

REM Check if vendor directory exists
if not exist "%~dp0vendor" (
    echo.
    echo ERROR: Dependencies not installed!
    echo Please run: composer install
    echo Or: php composer.phar install
    echo.
    pause
    exit /b 1
)

REM Default port
set PORT=8000

REM Check if port argument was provided
if not "%1"=="" set PORT=%1

echo.
echo Starting PHP Development Server...
echo URL: http://localhost:%PORT%
echo Press Ctrl+C to stop
echo.

cd /d "%~dp0public"
%PHP_CMD% -S localhost:%PORT%

