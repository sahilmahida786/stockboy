# Firebase Quick Setup Guide

## ✅ Step 1: Get Firebase Web Config (Frontend Only)

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: **stockboy**
3. Click **⚙️ Project Settings**
4. Scroll to **Your apps** → Find your **Web app** (or create one)
5. Copy the `firebaseConfig` object

## ✅ Step 2: Update `templates/auth.html`

Replace the placeholder config in `auth.html` (around line 90):

```javascript
const firebaseConfig = {
    apiKey: "AIzaSyXXXX",  // Your actual API key
    authDomain: "stockboy-5e03a.firebaseapp.com",
    projectId: "stockboy-5e03a",
    storageBucket: "stockboy-5e03a.appspot.com",
    messagingSenderId: "123456789",
    appId: "1:123:web:abc"
};
```

⚠️ **This config is PUBLIC by design** - it's safe to include in frontend JavaScript.

## ✅ Step 3: Get Service Account Credentials (Backend)

1. Firebase Console → **⚙️ Project Settings** → **Service accounts** tab
2. Click **Generate new private key**
3. Download the JSON file (e.g., `stockboy-5e03a-firebase-adminsdk-xxxxx.json`)
4. Save it in your project root (or a secure location)

## ✅ Step 4: Set Environment Variable (File Path)

**Windows PowerShell:**
```powershell
$env:FIREBASE_CREDENTIALS="C:\Users\sahil\stockboy\firebase-service-account.json"
```

**Linux / Mac:**
```bash
export FIREBASE_CREDENTIALS="/path/to/firebase-service-account.json"
```

⚠️ **Use file path, NOT JSON content** (best practice for security)

## ✅ Step 5: Test the Setup

1. Start your Flask app:
   ```bash
   python app.py
   ```

2. Check console output:
   - Should see: `✅ Firebase Admin SDK initialized successfully`

3. Visit `http://localhost:5000`
4. Try registering with email/password
5. Try logging in

## 🔐 How It Works

### Frontend (JavaScript)
- User registers/logs in via Firebase Auth SDK
- Gets Firebase ID token
- Sends token in `Authorization: Bearer <token>` header to backend

### Backend (Flask)
- Receives token from Authorization header
- Verifies token using Firebase Admin SDK
- Creates session for authenticated user

## 📝 Example Protected Route

You can protect any route with the `@firebase_required` decorator:

```python
@app.route("/api/my-courses")
@firebase_required
def my_courses():
    uid = request.firebase_uid  # Available after decorator
    email = request.firebase_email
    return jsonify({"uid": uid, "email": email})
```

## 🚀 For Production

Set `FIREBASE_CREDENTIALS` environment variable in your hosting platform:
- Render: Environment → Add `FIREBASE_CREDENTIALS` = file path
- Heroku: Config Vars → Add `FIREBASE_CREDENTIALS` = file path
- VPS: Add to `.env` or system environment variables

## ✅ Done!

Your Firebase authentication is now properly configured:
- ✅ Frontend uses Firebase config directly (public, safe)
- ✅ Backend uses service account file path (secure)
- ✅ Tokens sent via Authorization header (best practice)
- ✅ Token verification decorator available for protected routes


