@echo off
echo.
echo ====================================
echo  Testing PHP API Setup
echo ====================================
echo.

REM Set PHP path
set PHP_CMD=C:\php\php.exe

echo [1/4] Checking PHP installation...
%PHP_CMD% -v 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PHP not found at C:\php\php.exe
    pause
    exit /b 1
)
echo OK: PHP is installed
echo.

echo [2/4] Checking pdo_mysql extension...
%PHP_CMD% -m | findstr /C:"pdo_mysql" >nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: pdo_mysql extension not enabled
    echo.
    echo Fix: Edit C:\php\php.ini and uncomment: extension=pdo_mysql
    pause
    exit /b 1
)
echo OK: pdo_mysql extension is enabled
echo.

echo [3/4] Checking MySQL connection...
%PHP_CMD% -r "try { new PDO('mysql:host=localhost', 'test', 'password'); echo 'OK: MySQL is running and accessible'; } catch (Exception $e) { echo 'ERROR: Cannot connect to MySQL - ' . $e->getMessage(); exit(1); }"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Fix: Start your MySQL server
    pause
    exit /b 1
)
echo.

echo [4/4] Testing API health endpoint...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing; if ($r.StatusCode -eq 200) { Write-Host 'OK: API is responding' -ForegroundColor Green; Write-Host $r.Content } else { Write-Host 'ERROR: API returned status' $r.StatusCode -ForegroundColor Red; exit 1 } } catch { Write-Host 'ERROR: API not responding -' $_.Exception.Message -ForegroundColor Red; Write-Host 'Make sure PHP server is running (start-server.bat)' -ForegroundColor Yellow; exit 1 }"
if %ERRORLEVEL% NEQ 0 (
    pause
    exit /b 1
)

echo.
echo ====================================
echo  All tests PASSED!
echo ====================================
echo.
pause

