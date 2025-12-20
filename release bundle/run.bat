@echo off
setlocal
echo ===================================================
echo   CardioVoice Backend - One-Click Launcher
echo ===================================================
echo.
:: 1. Check for Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is NOT installed or not running!
    echo Please install Docker Desktop and try again.
    pause
    exit /b 1
)
:: 2. Prompt for Keys (Only if not already set)
if "%GIGACHAT_AUTH_KEY%"=="" (
    set /p GIGACHAT_AUTH_KEY="Enter your GigaChat Auth Key: "
)
if "%GITHUB_REPOSITORY_OWNER%"=="" (
    set /p GITHUB_REPOSITORY_OWNER="Enter the GitHub Username (owner of image): "
)
:: 3. Export variables for this session
set GIGACHAT_AUTH_KEY=%GIGACHAT_AUTH_KEY%
set GITHUB_REPOSITORY_OWNER=%GITHUB_REPOSITORY_OWNER%
echo.
echo [INFO] Pulling latest images...
docker-compose -f docker-compose.deploy.yml pull
echo.
echo [INFO] Starting services...
docker-compose -f docker-compose.deploy.yml up -d
echo.
echo ===================================================
echo   SUCCESS! Services are running.
echo   API Health: http://localhost:5010/health
echo   API Docs:   http://localhost:5010/docs
echo ===================================================
echo.
pause