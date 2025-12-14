# 🔧 Fix: "Firebase authentication not configured"

## ✅ Quick Fix Steps

### Step 1: Download Service Account JSON

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: **stockboy**
3. Click **⚙️ Project Settings** (gear icon)
4. Go to **Service accounts** tab
5. Click **Generate new private key**
6. Click **Generate key** in the confirmation dialog
7. A JSON file will download (e.g., `stockboy-5e03a-firebase-adminsdk-xxxxx.json`)

### Step 2: Save the JSON File

1. Move the downloaded JSON file to your project folder:
   ```
   C:\Users\sahil\stockboy\firebase-service-account.json
   ```

2. **IMPORTANT:** Add this file to `.gitignore` to keep it secure:
   ```
   firebase-service-account.json
   ```

### Step 3: Set Environment Variable (Windows PowerShell)

**Option A: For Current Session Only**
```powershell
$env:FIREBASE_CREDENTIALS="C:\Users\sahil\stockboy\firebase-service-account.json"
```

**Option B: Permanent (Recommended)**
```powershell
[System.Environment]::SetEnvironmentVariable('FIREBASE_CREDENTIALS', 'C:\Users\sahil\stockboy\firebase-service-account.json', 'User')
```

After setting permanently, **restart your terminal/IDE** for changes to take effect.

### Step 4: Verify Setup

1. Restart your Flask app:
   ```bash
   python app.py
   ```

2. Check the console output - you should see:
   ```
   ✅ Firebase Admin SDK initialized successfully
   ```

3. If you see this, you're done! ✅

### Step 5: Test Registration

1. Visit `http://127.0.0.1:5000`
2. Try registering a new user
3. The error should be gone! 🎉

## 🔍 Troubleshooting

### Still seeing "Firebase authentication not configured"?

1. **Check file path:**
   ```powershell
   Test-Path "C:\Users\sahil\stockboy\firebase-service-account.json"
   ```
   Should return `True`

2. **Check environment variable:**
   ```powershell
   $env:FIREBASE_CREDENTIALS
   ```
   Should show the file path

3. **Restart Flask app** after setting environment variable

4. **Check Flask console** for initialization messages

### File not found error?

- Make sure the JSON file is in the correct location
- Check the file path in the environment variable matches exactly
- Use forward slashes or escaped backslashes: `C:\\Users\\sahil\\stockboy\\firebase-service-account.json`


