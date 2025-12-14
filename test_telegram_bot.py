"""
Test Telegram Bot Configuration
Run this script to verify your bot token and get your Chat ID
"""
import requests
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "7581428285:AAF6qwxQYniDoZnhiwERUP_k0Vlf-k6MVSQ")
CHAT_ID = os.getenv("CHAT_ID", "")

print("=" * 60)
print("Telegram Bot Configuration Test")
print("=" * 60)
print()

# Test 1: Check Bot Token
print("1. Testing Bot Token...")
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
try:
    response = requests.get(url, timeout=10)
    data = response.json()
    if data.get("ok"):
        bot_info = data.get("result", {})
        print(f"   ✅ Bot Token is VALID")
        print(f"   Bot Username: @{bot_info.get('username', 'N/A')}")
        print(f"   Bot Name: {bot_info.get('first_name', 'N/A')}")
    else:
        print(f"   ❌ Bot Token is INVALID")
        print(f"   Error: {data.get('description', 'Unknown error')}")
        exit(1)
except Exception as e:
    print(f"   ❌ Error testing bot token: {e}")
    exit(1)

print()

# Test 2: Check Chat ID
print("2. Checking Chat ID...")
if not CHAT_ID:
    print("   ⚠️  CHAT_ID is NOT SET")
    print()
    print("   To get your Chat ID:")
    print("   1. Open Telegram")
    print("   2. Search for @userinfobot")
    print("   3. Start a conversation")
    print("   4. It will reply with your Chat ID (a number)")
    print("   5. Copy that number and add it to start_server.bat")
    print()
    print("   Or visit this URL (replace YOUR_CHAT_ID with the number):")
    print(f"   https://api.telegram.org/bot{BOT_TOKEN}/getUpdates")
    print()
else:
    print(f"   ✅ CHAT_ID is set: {CHAT_ID}")
    print()
    
    # Test 3: Send Test Message
    print("3. Sending test message...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": "✅ Test message from Stockboy Bot!\n\nIf you see this, your bot is configured correctly! 🎉"
    }
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        if result.get("ok"):
            print(f"   ✅ Test message sent successfully!")
            print(f"   Check your Telegram chat to see the message.")
        else:
            print(f"   ❌ Failed to send test message")
            print(f"   Error: {result.get('description', 'Unknown error')}")
            if "chat not found" in result.get("description", "").lower():
                print()
                print("   💡 TIP: Make sure you have started a conversation with your bot first!")
                print("   1. Search for your bot on Telegram")
                print("   2. Click 'Start' or send /start")
                print("   3. Then run this test again")
    except Exception as e:
        print(f"   ❌ Error sending test message: {e}")

print()
print("=" * 60)
print("Test Complete")
print("=" * 60)


