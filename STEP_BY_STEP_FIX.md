# 🔧 Step-by-Step: Fix Razorpay Package Installation

## 🎯 The Problem

Render is NOT installing the `razorpay` package during build, causing payment errors.

## ✅ SOLUTION (Follow These Steps Exactly)

### Step 1: Go to Render Dashboard
1. Open: https://dashboard.render.com/
2. Click on your **stockboy** service

### Step 2: Clear Build Cache
1. Click **"Settings"** tab (left sidebar)
2. Scroll down to find **"Clear build cache"** section
3. Click **"Clear build cache"** button
4. Confirm when prompted

### Step 3: Check Build Command
1. Still in **Settings** tab
2. Find **"Build Command"** field
3. Make sure it says:
   ```
   pip install --upgrade pip && pip install -r requirements.txt
   ```
4. If different, change it to above
5. Click **"Save Changes"**

### Step 4: Manual Deploy
1. Go back to main service page
2. Click **"Manual Deploy"** button (top right, blue button)
3. Select **"Deploy latest commit"**
4. Wait for deployment to start

### Step 5: Watch Build Logs
1. Click **"Logs"** tab
2. Make sure you're viewing **"Build Logs"** (not Runtime Logs)
3. Look for these lines:
   ```
   Collecting razorpay==1.4.2
   Installing collected packages: razorpay
   Successfully installed razorpay-1.4.2
   ```

### Step 6: Verify Runtime Logs
After build completes, switch to **Runtime Logs** and look for:
```
📦 Razorpay package imported successfully
✅ Razorpay client initialized successfully
   Key ID: rzp_live_RrVTwgfzN5B...
   Account: [Your Account Name]
```

### Step 7: Test Payment
1. Go to: https://stockboy.works/product/product1
2. Click the payment button
3. Should open Razorpay checkout (no error!)

## 🚨 If Build Logs Show Errors

If you see errors in build logs:

### Error: "Could not find a version"
- Check internet connection during build
- Try changing build command to:
  ```
  pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
  ```

### Error: "Permission denied"
- This shouldn't happen, but contact Render support if it does

### No razorpay in build logs
- Make sure `requirements.txt` is in the root directory
- Verify it has `razorpay==1.4.2` on line 7
- Check that you're looking at Build Logs, not Runtime Logs

## ✅ Success Checklist

After following all steps:
- [ ] Build cache cleared
- [ ] Build command updated
- [ ] Manual deploy triggered
- [ ] Build logs show "Successfully installed razorpay-1.4.2"
- [ ] Runtime logs show "✅ Razorpay client initialized successfully"
- [ ] Payment button works on live site
- [ ] No error popup when clicking payment

## 🎯 Why This Works

1. **Clearing cache** removes stale build state
2. **Upgrading pip** ensures latest package installer
3. **Manual deploy** forces fresh build
4. **Watching logs** confirms installation

---

**Follow these steps in order and payment will work!** 🚀
