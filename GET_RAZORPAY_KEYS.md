# 🔑 How to Get Your Correct Razorpay Keys

## ✅ Your Current Keys (from code)

- **Key ID**: `rzp_live_RrRixqT6TVvpwD`
- **Key Secret**: `OIJKIACl354fuecNgdKLwRcF` (lowercase "l" not "1")

## 📋 Step-by-Step: Verify Keys from Razorpay Dashboard

### Step 1: Login to Razorpay Dashboard
1. Go to: https://dashboard.razorpay.com/
2. Login with your account

### Step 2: Navigate to API Keys
1. Click **"Settings"** (gear icon) in left sidebar
2. Click **"API Keys"** under "Developer Options"

### Step 3: View Live Keys
1. Make sure you're on **"Live Mode"** (not Test Mode)
2. Click **"Reveal Live API Keys"** button
3. You'll see:
   - **Key ID**: `rzp_live_xxxxx`
   - **Key Secret**: `xxxxxxxxxxxxx`

### Step 4: Copy Exact Values
1. **Key ID**: Should be `rzp_live_RrRixqT6TVvpwD`
2. **Key Secret**: Copy the ENTIRE secret (usually 32+ characters)
   - Make sure it's `OIJKIACl354fuecNgdKLwRcF` (lowercase "l")
   - NOT `OIJKIAC1354fuecNgdKLwRcF` (number "1")

### Step 5: Verify in Render
1. Go to **Render Dashboard** → Your Service → **Environment**
2. Check `RAZORPAY_KEY_ID` = `rzp_live_RrRixqT6TVvpwD`
3. Check `RAZORPAY_KEY_SECRET` = `OIJKIACl354fuecNgdKLwRcF`
   - Click eye icon to reveal
   - Make sure no extra spaces
   - Make sure lowercase "l" not "1"

## ⚠️ Common Mistakes

| Wrong | Correct |
|-------|---------|
| `OIJKIAC1354fuecNgdKLwRcF` (has "1") | `OIJKIACl354fuecNgdKLwRcF` (has "l") |
| ` OIJKIACl354fuecNgdKLwRcF` (leading space) | `OIJKIACl354fuecNgdKLwRcF` (no spaces) |
| `OIJKIACl354fuecNgdKLwRcF ` (trailing space) | `OIJKIACl354fuecNgdKLwRcF` (no spaces) |
| Truncated key (too short) | Full key (32+ characters) |

## 🔍 Quick Verification

After setting keys in Render:

1. **Save and Redeploy**
2. **Check Logs** - Should see:
   ```
   ✅ Razorpay client initialized successfully
   Account: [Your Account Name]
   ```

3. **If you see error**, check:
   - Key format (must start with `rzp_live_` for Key ID)
   - Key Secret length (should be 32+ characters)
   - No extra spaces
   - Correct character: lowercase "l" not "1"

## ✅ Correct Keys Format

**Key ID:**
- Starts with: `rzp_live_`
- Example: `rzp_live_RrRixqT6TVvpwD`

**Key Secret:**
- Usually 32+ characters
- Alphanumeric (letters and numbers)
- Example: `OIJKIACl354fuecNgdKLwRcF`

## 🚨 If Keys Don't Match

If the keys in Razorpay dashboard are DIFFERENT from what's in your code:

1. **Update Render Environment Variables** with the NEW keys from Razorpay
2. **Update app.py** (lines 203, 207) with new keys as fallback
3. **Redeploy**

## 📝 Next Steps

1. ✅ Verify keys in Razorpay dashboard
2. ✅ Copy exact values (no spaces)
3. ✅ Set in Render environment variables
4. ✅ Save and redeploy
5. ✅ Check logs for success message

