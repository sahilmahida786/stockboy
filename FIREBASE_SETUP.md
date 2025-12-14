# Firebase Setup Instructions

## Step 1: Get Firebase Web Configuration

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: **stockboy**
3. Click the gear icon ⚙️ next to "Project Overview"
4. Select **Project settings**
5. Scroll down to **Your apps** section
6. If you don't have a web app yet:
   - Click **Add app** → Select **Web** (</> icon)
   - Register your app with a nickname (e.g., "stockboy-web")
   - Click **Register app**
7. Copy the Firebase configuration object that looks like this:

```javascript
const firebaseConfig = {
  apiKey: "AIzaSy...",
  authDomain: "stockboy-5e03a.firebaseapp.com",
  projectId: "stockboy-5e03a",
  storageBucket: "stockboy-5e03a.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abcdef"
};
```

## Step 2: Set Environment Variables for Web Config

Set these environment variables with the values from your Firebase config:

```bash
# Windows PowerShell
$env:FIREBASE_API_KEY="AIzaSy..."
$env:FIREBASE_AUTH_DOMAIN="stockboy-5e03a.firebaseapp.com"
$env:FIREBASE_PROJECT_ID="stockboy-5e03a"
$env:FIREBASE_STORAGE_BUCKET="stockboy-5e03a.appspot.com"
$env:FIREBASE_MESSAGING_SENDER_ID="123456789"
$env:FIREBASE_APP_ID="1:123456789:web:abcdef"
```

Or create a `.env` file in your project root (if using python-dotenv):

```
FIREBASE_API_KEY=AIzaSy...
FIREBASE_AUTH_DOMAIN=stockboy-5e03a.firebaseapp.com
FIREBASE_PROJECT_ID=stockboy-5e03a
FIREBASE_STORAGE_BUCKET=stockboy-5e03a.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789
FIREBASE_APP_ID=1:123456789:web:abcdef
```

## Step 3: Get Service Account Credentials (for Backend Verification)

1. In Firebase Console, go to **Project settings** (gear icon)
2. Go to **Service accounts** tab
3. Click **Generate new private key**
4. Click **Generate key** in the confirmation dialog
5. A JSON file will be downloaded (e.g., `stockboy-5e03a-firebase-adminsdk-xxxxx.json`)

## Step 4: Set FIREBASE_CREDENTIALS Environment Variable

You need to set the entire JSON content as an environment variable. 

**Option A: Set as JSON string (recommended for production)**

```bash
# Windows PowerShell - Read the JSON file and set it
$credJson = Get-Content "path\to\your\firebase-credentials.json" -Raw
$env:FIREBASE_CREDENTIALS=$credJson
```

**Option B: For local development, you can also use a file path**

Modify `app.py` to support reading from a file path if `FIREBASE_CREDENTIALS` is not set:

```python
# Add this after line 148 in app.py if you want file-based credentials
if not FIREBASE_CREDENTIALS and os.path.exists("firebase-credentials.json"):
    with open("firebase-credentials.json", "r") as f:
        FIREBASE_CREDENTIALS = f.read()
```

## Step 5: Verify Email/Password Authentication is Enabled

✅ You've already done this! Email/Password authentication is enabled in your Firebase console.

## Step 6: Test the Setup

1. Start your Flask app:
   ```bash
   python app.py
   ```

2. Check the console output:
   - You should see: `✅ Firebase Admin SDK initialized successfully`
   - If you see warnings, check your environment variables

3. Visit `http://localhost:5000`
4. Try registering a new user with email and password
5. Try logging in with the same credentials

## Troubleshooting

### "Firebase authentication not configured"
- Check that `FIREBASE_CREDENTIALS` environment variable is set correctly
- Verify the JSON is valid (no extra quotes or escaping issues)

### "Missing Firebase ID token"
- Check browser console for JavaScript errors
- Verify Firebase web config environment variables are set
- Check that Firebase SDK is loading correctly

### "Invalid authentication token"
- Token may have expired - try logging in again
- Check that Firebase Admin SDK initialized successfully
- Verify service account credentials are correct

## For Production Deployment (Render, Heroku, etc.)

Set all environment variables in your hosting platform's dashboard:

1. **FIREBASE_API_KEY**
2. **FIREBASE_AUTH_DOMAIN**
3. **FIREBASE_PROJECT_ID**
4. **FIREBASE_STORAGE_BUCKET**
5. **FIREBASE_MESSAGING_SENDER_ID**
6. **FIREBASE_APP_ID**
7. **FIREBASE_CREDENTIALS** (the entire JSON as a string - be careful with quotes!)

Note: For `FIREBASE_CREDENTIALS`, you may need to escape quotes properly or use the hosting platform's JSON environment variable feature if available.


