# ✅ Pre-Deployment Checklist

Use this checklist before deploying to Render:

## 📦 Code Ready
- [ ] All code changes committed to Git
- [ ] All files pushed to GitHub repository
- [ ] No local-only files in repository (check .gitignore)

## 🔧 Configuration Files
- [ ] `Procfile` exists and contains: `web: gunicorn app:app`
- [ ] `requirements.txt` has all dependencies
- [ ] `render.yaml` is configured (optional but recommended)

## 🔐 Environment Variables (Set in Render Dashboard)
- [ ] `SECRET_KEY` - Secure random string
- [ ] `BOT_TOKEN` - Your Telegram bot token
- [ ] `CHAT_ID` - Your Telegram Chat ID
- [ ] `ADMIN_PASSWORD` - Admin password (change from default!)
- [ ] `ADMIN_USERNAME` - Admin username (default: stockboy)
- [ ] `FIREBASE_CREDENTIALS` - If using Firebase (JSON string)
- [ ] `MAINTENANCE_MODE` - Set to `false` for production

## 🧪 Testing
- [ ] App runs locally without errors
- [ ] Telegram bot responds to `/start` command
- [ ] Payment submission works
- [ ] Admin panel accessible

## 🔗 Post-Deployment
- [ ] Set Telegram webhook to Render URL
- [ ] Test website at Render URL
- [ ] Test Telegram bot commands
- [ ] Verify payment notifications work

## 📝 Quick Deploy Commands

```bash
# 1. Commit all changes
git add .
git commit -m "Deploy to Render"

# 2. Push to GitHub
git push origin main

# 3. Render will auto-deploy (if connected)
# Or manually trigger deployment in Render dashboard
```

## 🚨 Important Notes

1. **Change default admin password** before deploying!
2. **Never commit sensitive data** (tokens, passwords) to Git
3. **Use environment variables** for all secrets
4. **Test webhook** after deployment
5. **Monitor logs** in Render dashboard for errors
