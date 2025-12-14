@echo off
echo Starting Flask Server...
echo.

REM Set Telegram Bot Configuration
set BOT_TOKEN=7581428285:AAF6qwxQYniDoZnhiwERUP_k0Vlf-k6MVSQ
REM Set your Telegram Chat ID (get it from @userinfobot on Telegram)
REM IMPORTANT: Replace the number below with your actual Chat ID
set CHAT_ID=

echo Checking Telegram Bot Configuration...
echo.

cd /d "%~dp0"

REM Check if CHAT_ID is set
if "%CHAT_ID%"=="" (
    echo ⚠️  WARNING: CHAT_ID is not set!
    echo.
    echo To get your Chat ID:
    echo 1. Open Telegram
    echo 2. Search for @userinfobot
    echo 3. Start conversation - it will show your Chat ID
    echo 4. Edit this file and set CHAT_ID=YOUR_CHAT_ID
    echo.
    echo Or run: python test_telegram_bot.py
    echo.
    pause
)

python app.py
pause

