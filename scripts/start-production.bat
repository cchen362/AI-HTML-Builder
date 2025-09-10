@echo off
REM AI HTML Builder - Windows Production Startup Script

echo.
echo ======================================
echo   AI HTML Builder - Production Start
echo ======================================
echo.

REM Check if Podman is installed
podman --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Podman is not installed or not in PATH
    echo Please install Podman and try again
    pause
    exit /b 1
)

REM Check if .env.prod exists
if not exist ".env.prod" (
    echo [ERROR] .env.prod file not found
    echo Please create .env.prod with your production configuration
    pause
    exit /b 1
)

REM Check if docker-compose.prod.yml exists
if not exist "docker-compose.prod.yml" (
    echo [ERROR] docker-compose.prod.yml file not found
    pause
    exit /b 1
)

echo [INFO] Starting AI HTML Builder production deployment...
echo.

REM Stop any existing containers
echo [STEP 1/4] Stopping existing containers...
podman-compose -f docker-compose.prod.yml down

REM Build the application
echo.
echo [STEP 2/4] Building application image...
podman build -t ai-html-builder:latest .

if %errorlevel% neq 0 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

REM Start services
echo.
echo [STEP 3/4] Starting services...
podman-compose -f docker-compose.prod.yml up -d

if %errorlevel% neq 0 (
    echo [ERROR] Failed to start services
    pause
    exit /b 1
)

REM Wait for services to be ready
echo.
echo [STEP 4/4] Waiting for services to be ready...
timeout /t 30 /nobreak

REM Display service status
echo.
echo [INFO] Checking service status...
podman-compose -f docker-compose.prod.yml ps

echo.
echo ======================================
echo   Deployment Complete!
echo ======================================
echo.
echo Application URL: http://localhost:8080
echo Admin Panel:     http://localhost:8080/admin
echo API Documentation: http://localhost:8080/docs
echo.
echo Management Commands:
echo   View logs: podman logs -f ai-html-builder-app
echo   Stop services: podman-compose -f docker-compose.prod.yml down
echo.
echo Press any key to exit...
pause >nul