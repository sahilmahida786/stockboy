# 🚀 Render Deployment Guide

This guide will help you deploy your Stockboy application to Render.

## 📋 Prerequisites

1. **GitHub Account** - Your code should be in a GitHub repository
2. **Render Account** - Sign up at https://render.com
3. **Environment Variables** - You'll need to configure these in Render

## 🔧 Step 1: Prepare Your Repository

1. Make sure all your changes are committed:
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

## 🌐 Step 2: Deploy to Render

### Option A: Using render.yaml (Recommended)

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Click "New +"** → **"Web Service"**
3. **Connect your GitHub repository**
4. **Render will automatically detect `render.yaml`** and use those settings
5. **Configure Environment Variables** (see Step 3 below)

### Option B: Manual Configuration

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Click "New +"** → **"Web Service"**
3. **Connect your GitHub repository**
4. **Configure the service**:
   - **Name**: `stockboy` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Choose Free or Paid plan

## 🔐 Step 3: Set Environment Variables

In your Render service dashboard, go to **Environment** tab and add:

### Required Variables:

1. **SECRET_KEY**
   - Generate a secure random string
   - You can use: `python -c "import secrets; print(secrets.token_hex(32))"`
   - Or use Render's auto-generated value

2. **BOT_TOKEN**
   - Your Telegram bot token
   - Example: `7581428285:AAF6qwxQYniDoZnhiwERUP_k0Vlf-k6MVSQ`

3. **CHAT_ID**
   - Your Telegram Chat ID (get it from @userinfobot)
   - Example: `1924050423`

4. **ADMIN_PASSWORD**
   - Your admin password (default: `stockboy@123`)
   - **Change this for security!**

5. **FIREBASE_CREDENTIALS** (if using Firebase)
   - Paste your Firebase service account JSON as a string
   - Or upload the JSON file and reference the path

### Optional Variables:

- **MAINTENANCE_MODE**: Set to `true` to enable maintenance mode
- **ADMIN_USERNAME**: Default is `stockboy`

## 🔗 Step 4: Set Up Telegram Webhook

Once your app is deployed and running:

1. **Get your Render URL**: 
   - It will be something like: `https://stockboy.onrender.com`

2. **Set the webhook** by visiting this URL in your browser:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<your-render-url>/telegram-update
   ```
   
   Replace:
   - `<YOUR_BOT_TOKEN>` with your actual bot token
   - `<your-render-url>` with your Render service URL

3. **Verify webhook**:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
   ```

## ✅ Step 5: Verify Deployment

1. **Check Build Logs**: Make sure the build completed successfully
2. **Check Runtime Logs**: Look for any errors
3. **Test Your Website**: Visit your Render URL
4. **Test Telegram Bot**: Send `/start` to your bot

## 📁 File Structure for Render

Your repository should have:
```
stockboy/
├── app.py                 # Main Flask application
├── Procfile              # Process file (web: gunicorn app:app)
├── requirements.txt      # Python dependencies
├── render.yaml          # Render configuration (optional)
├── static/              # Static files (CSS, images, etc.)
├── templates/           # HTML templates
└── payment_ss/          # Payment screenshots (will be created)
```

## 🔄 Updating Your Deployment

To update your live website:

1. **Make changes locally**
2. **Commit and push to GitHub**:
   ```bash
   git add .
   git commit -m "Update description"
   git push origin main
   ```
3. **Render will automatically detect the push and redeploy**
4. **Wait for deployment to complete** (check Render dashboard)

## 🐛 Troubleshooting

### Build Fails

- Check that all dependencies are in `requirements.txt`
- Verify Python version compatibility
- Check build logs in Render dashboard

### App Crashes on Startup

- Check runtime logs in Render dashboard
- Verify all environment variables are set
- Make sure `BOT_TOKEN` and `CHAT_ID` are correct

### Telegram Bot Not Working

- Verify webhook is set correctly
- Check that `BOT_TOKEN` environment variable is set
- Test webhook URL: `https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

### Static Files Not Loading

- Make sure `static/` folder is in your repository
- Check file paths in templates

### Payment Screenshots Not Saving

- Render's filesystem is ephemeral (files reset on restart)
- Consider using a cloud storage service (S3, Cloudinary) for production
- For now, files will persist until the service restarts

## 📝 Notes

- **Free Tier Limitations**: 
  - Services spin down after 15 minutes of inactivity
  - First request after spin-down may be slow
  - Consider upgrading to paid plan for always-on service

- **File Storage**: 
  - Render's filesystem is not persistent
  - Payment screenshots and uploads will be lost on restart
  - For production, use cloud storage (AWS S3, Cloudinary, etc.)

- **Database**: 
  - Currently using JSON files (not persistent on Render)
  - Consider using Render PostgreSQL for production

## 🎉 Success!

Once deployed, your website will be live at:
`https://<your-service-name>.onrender.com`

Your Telegram bot will automatically:
- ✅ Receive and respond to messages
- ✅ Send payment notifications
- ✅ Handle approve/reject buttons (if webhook is set)



