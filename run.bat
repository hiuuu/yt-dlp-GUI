@echo off
title YouTube Downloader Server
color 0A

echo ====================================
echo   YouTube Downloader GUI Launcher
echo ====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python from https://python.org
    echo and make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Check if app.py exists
if not exist "app.py" (
    echo [ERROR] app.py not found in current directory!
    echo Please make sure you're running this from the correct folder.
    echo.
    pause
    exit /b 1
)

REM Check if yt-dlp.exe exists
if not exist "yt-dlp.exe" (
    echo [WARNING] yt-dlp.exe not found in current directory!
    echo Please download yt-dlp.exe from https://github.com/yt-dlp/yt-dlp/releases
    echo and place it in the same folder as app.py
    echo.
)

REM Check if index.html exists
if not exist "index.html" (
    echo [ERROR] index.html not found in current directory!
    echo Please make sure all files are in the same folder.
    echo.
    pause
    exit /b 1
)

echo [INFO] Starting YouTube Downloader server...
echo.

REM Start the Python app
echo [INFO] Running: python app.py
echo.

REM Try to find and open Firefox
set FIREFOX_FOUND=0
for %%P in ("%ProgramFiles%\Mozilla Firefox\firefox.exe" "%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe" "%LocalAppData%\Mozilla Firefox\firefox.exe") do (
    if exist "%%~P" (
        echo [INFO] Firefox found at: %%~P
        echo [INFO] Opening Firefox...
        start "" "%%~P" "http://localhost:5000"
        set FIREFOX_FOUND=1
        goto :firefox_found
    )
)

:firefox_found
if %FIREFOX_FOUND%==0 (
    echo [WARNING] Firefox not found, opening default browser...
    start http://localhost:5000
)

echo.
echo ====================================
echo   Server is running at:
echo   http://localhost:5000
echo ====================================
echo.
echo [INFO] You can close this window to stop the server.
echo [INFO] The browser should open automatically.
echo.

REM Run the app and keep the window open
python app.py

echo.
echo [INFO] Server stopped.
pause