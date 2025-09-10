@echo off
REM AI HTML Builder - Windows Production Stop Script

echo.
echo ======================================
echo   AI HTML Builder - Production Stop
echo ======================================
echo.

REM Check if Podman is installed
podman --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Podman is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if docker-compose.prod.yml exists
if not exist "docker-compose.prod.yml" (
    echo [ERROR] docker-compose.prod.yml file not found
    pause
    exit /b 1
)

echo [INFO] Stopping AI HTML Builder production services...
echo.

REM Stop services
podman-compose -f docker-compose.prod.yml down

if %errorlevel% neq 0 (
    echo [ERROR] Failed to stop services
    pause
    exit /b 1
)

echo.
echo [INFO] Services stopped successfully
echo.
echo To restart: run start-production.bat
echo To view remaining containers: podman ps -a
echo To remove all containers: podman-compose -f docker-compose.prod.yml down -v
echo.
echo Press any key to exit...
pause >nul