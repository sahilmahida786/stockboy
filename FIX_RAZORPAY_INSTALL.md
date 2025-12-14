# 🔧 Fix: "razorpay package not installed" Error

## 🔴 The Problem

Render logs show:
```
⚠️ razorpay package not installed - install with: pip install razorpay
```

Even though `razorpay==1.4.2` is in `requirements.txt`, it's not being installed during the build.

## ✅ Solution: Force Fresh Rebuild

### Step 1: Verify requirements.txt

Your `requirements.txt` should have:
```
razorpay==1.4.2
```

✅ **Already correct!** (Line 7)

### Step 2: Trigger Manual Rebuild in Render

1. **Go to Render Dashboard**
   - Navigate to: https://dashboard.render.com/
   - Select your **stockboy** service

2. **Manual Deploy**
   - Click **"Manual Deploy"** button (top right)
   - Select **"Deploy latest commit"**
   - This forces a fresh build

3. **Watch Build Logs**
   - Click **"Logs"** tab
   - Watch for: `Installing collected packages: razorpay`
   - Should see: `Successfully installed razorpay-1.4.2`

### Step 3: Verify Installation

After deployment, check logs for:
```
📦 Razorpay package imported successfully
✅ Razorpay client initialized successfully
   Key ID: rzp_live_RrVTwgfzN5B...
   Account: [Your Account Name]
```

## 🔍 Alternative: Check Build Command

If rebuild doesn't work, verify build command:

1. **Render Dashboard** → **Settings** tab
2. **Build Command** should be:
   ```
   pip install -r requirements.txt
   ```
3. If different, change it to above
4. **Save** and redeploy

## 🚨 If Still Not Working

### Option 1: Clear Build Cache
1. Render Dashboard → **Settings**
2. Scroll to **"Clear build cache"**
3. Click **"Clear cache"**
4. Redeploy

### Option 2: Verify requirements.txt Format
Make sure `requirements.txt` has:
- No extra spaces
- Correct line endings
- Exact version: `razorpay==1.4.2`

### Option 3: Check Build Logs
Look for errors like:
- `ERROR: Could not find a version that satisfies the requirement razorpay`
- `WARNING: Ignoring invalid distribution`
- Any pip installation errors

## 📝 Quick Fix Steps

1. ✅ Verify `requirements.txt` has `razorpay==1.4.2` (already done)
2. ✅ Go to Render Dashboard
3. ✅ Click **"Manual Deploy"** → **"Deploy latest commit"**
4. ✅ Watch build logs for razorpay installation
5. ✅ Verify success in runtime logs

## ✅ Expected Success Logs

After successful deployment:
```
Installing collected packages: razorpay
Successfully installed razorpay-1.4.2
...
📦 Razorpay package imported successfully
✅ Razorpay client initialized successfully
```

## 🎯 Root Cause

The package wasn't installed because:
- Build happened before `razorpay` was added to requirements.txt, OR
- Build cache is stale, OR
- Build command didn't run properly

**Solution**: Force a fresh rebuild by manual deploy.

