# 🔧 Fix: "Razorpay client not initialized" Error

## 🔴 The Problem

Error message: **"Razorpay client not initialized. Check RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET environment variables."**

This happens when Razorpay client fails to initialize on Render.

## ✅ Solution Steps

### Step 1: Verify Environment Variables in Render

Go to **Render Dashboard → Your Service → Environment Tab**

**Check these variables:**

1. **RAZORPAY_KEY_ID**
   - Value should be: `rzp_live_RrRixqT6TVvpwD`
   - Must start with `rzp_`
   - No extra spaces

2. **RAZORPAY_KEY_SECRET**
   - Value should be: `OIJKIACl354fuecNgdKLwRcF`
   - **IMPORTANT**: Use lowercase "l" not "1" (one)
   - Must be at least 20 characters
   - No extra spaces

### Step 2: Fix Common Issues

#### Issue 1: Wrong Key Secret
❌ Wrong: `OIJKIAC1354fuecNgdKLwRcF` (has "1" instead of "l")
✅ Correct: `OIJKIACl354fuecNgdKLwRcF` (has lowercase "l")

#### Issue 2: Extra Spaces
- Click the eye icon to reveal the value
- Copy the exact value (no leading/trailing spaces)
- Paste it back

#### Issue 3: Missing Variables
- If variable doesn't exist, click "+ Add"
- Add `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`
- Set correct values

### Step 3: Save and Redeploy

1. **Click "Save, rebuild, and deploy"** button
2. **Wait for deployment** (2-5 minutes)
3. **Check Logs** for:
   ```
   ✅ Razorpay client initialized successfully
   Account: [Your Account Name]
   ```

### Step 4: Verify in Logs

After deployment, check **Render → Logs** tab:

**✅ Success looks like:**
```
✅ Razorpay client initialized successfully
   Key ID: rzp_live_RrRixqT6TV...
   Account: [Account Name]
```

**❌ Error looks like:**
```
❌ Razorpay initialization error: [error message]
   RAZORPAY_KEY_ID: Set (XX chars)
   RAZORPAY_KEY_SECRET: Set (XX chars)
```

## 🔍 Debugging Checklist

- [ ] `RAZORPAY_KEY_ID` exists in Render environment
- [ ] `RAZORPAY_KEY_SECRET` exists in Render environment
- [ ] Key ID starts with `rzp_live_`
- [ ] Key Secret has lowercase "l" not "1"
- [ ] No extra spaces in values
- [ ] `razorpay==1.4.2` in requirements.txt
- [ ] Deployment completed successfully
- [ ] Logs show initialization success

## 🚨 Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "Razorpay client not initialized" | Keys missing/wrong | Set correct env vars |
| "Authentication failed" | Wrong key secret | Verify exact key secret |
| "Invalid RAZORPAY_KEY_ID format" | Wrong key ID | Must start with `rzp_` |
| "RAZORPAY_KEY_SECRET seems too short" | Wrong/truncated secret | Copy full secret |
| "razorpay package not installed" | Missing from requirements | Already in requirements.txt ✅ |

## 📝 Quick Fix

1. **Render Dashboard** → Environment
2. **Edit RAZORPAY_KEY_SECRET**
3. **Set to**: `OIJKIACl354fuecNgdKLwRcF` (lowercase "l")
4. **Save, rebuild, and deploy**
5. **Check logs** for success message

## ✅ After Fix

Once fixed, you should see in logs:
```
✅ Razorpay client initialized successfully
```

And payment button will work! 🎉
