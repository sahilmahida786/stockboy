# Telegram Bot Setup Guide

## ✅ Bot Token Configured
Your bot token has been added to `start_server.bat`:
```
BOT_TOKEN=7581428285:AAF6qwxQYniDoZnhiwERUP_k0Vlf-k6MVSQ
```

## 📱 Get Your Chat ID

To receive payment notifications, you need to set your Telegram Chat ID:

### Method 1: Using @userinfobot
1. Open Telegram and search for `@userinfobot`
2. Start a conversation with the bot
3. It will reply with your Chat ID (a number like `123456789`)
4. Copy that number

### Method 2: Using @getidsbot
1. Open Telegram and search for `@getidsbot`
2. Start a conversation
3. It will show your Chat ID

### Method 3: From Bot Messages
1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot7581428285:AAF6qwxQYniDoZnhiwERUP_k0Vlf-k6MVSQ/getUpdates`
3. Look for `"chat":{"id":123456789}` in the response
4. Copy the number after `"id":`

## 🔧 Update Chat ID

Once you have your Chat ID:

1. Open `start_server.bat`
2. Replace the empty `CHAT_ID=` with your actual ID:
   ```batch
   set CHAT_ID=123456789
   ```
3. Save the file

## 🚀 Start the Server

1. Double-click `start_server.bat` to start the server
2. The bot will automatically send payment notifications to your Telegram chat

## 🔗 Set Up Webhook (For Approve/Reject Buttons)

For the approve/reject buttons to work, you need to set up a webhook:

### For Local Development (using ngrok):

1. **Install ngrok**: Download from https://ngrok.com/
2. **Start your Flask server**: Run `start_server.bat`
3. **Start ngrok**: Open a new terminal and run:
   ```bash
   ngrok http 5000
   ```
4. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)
5. **Set webhook** by visiting this URL in your browser:
   ```
   https://api.telegram.org/bot7581428285:AAF6qwxQYniDoZnhiwERUP_k0Vlf-k6MVSQ/setWebhook?url=https://abc123.ngrok.io/telegram-update
   ```
   (Replace `abc123.ngrok.io` with your actual ngrok URL)

### For Production (Render/VPS/Server):

#### Render Deployment:

1. **Deploy your app to Render** (see `RENDER_DEPLOYMENT.md`)
2. **Get your Render URL**: `https://your-app.onrender.com`
3. **Set webhook** by visiting this URL in your browser:
   ```
   https://api.telegram.org/bot7581428285:AAF6qwxQYniDoZnhiwERUP_k0Vlf-k6MVSQ/setWebhook?url=https://your-app.onrender.com/telegram-update
   ```
   (Replace `your-app.onrender.com` with your actual Render URL)

#### VPS/Server:

1. Make sure your server is accessible via HTTPS
2. Set webhook:
   ```
   https://api.telegram.org/bot7581428285:AAF6qwxQYniDoZnhiwERUP_k0Vlf-k6MVSQ/setWebhook?url=https://yourdomain.com/telegram-update
   ```

### Check Webhook Status:

Visit this URL to verify:
```
https://api.telegram.org/bot7581428285:AAF6qwxQYniDoZnhiwERUP_k0Vlf-k6MVSQ/getWebhookInfo
```

**Note**: Even without webhook, payment notifications will still be sent. The webhook is only needed for the approve/reject buttons to work automatically.

## 📋 How It Works

1. User submits payment → Bot sends notification to your Telegram
2. Notification includes:
   - Payment screenshot
   - User name
   - Transaction ID
   - Course name
   - Amount
   - ✅ Approve / ❌ Reject buttons
3. Click buttons in Telegram → Payment status updates automatically
4. User gets access when approved

## 🔒 Security Note

- Never share your bot token publicly
- Keep `start_server.bat` private
- Consider using environment variables for production

