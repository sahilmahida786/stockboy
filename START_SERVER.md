# 🚀 How to Start the Flask Server

## Quick Start

### Method 1: Double-click the batch file
1. Double-click `start_server.bat` in your project folder
2. Wait for the server to start
3. You'll see: `Running on http://127.0.0.1:5000`

### Method 2: Using PowerShell/Command Prompt

1. **Open PowerShell or Command Prompt**

2. **Navigate to your project folder:**
   ```powershell
   cd C:\Users\sahil\stockboy
   ```

3. **Start the server:**
   ```powershell
   python app.py
   ```

4. **Keep the window open!** The server runs in this window.

## ✅ What You Should See

When the server starts successfully, you'll see:
```
✅ JSON file storage ready - using users.json
📁 Auto-detected Firebase credentials: stockboy-5e03a-firebase-adminsdk-fbsvc-0ecab1a414.json
✅ Loading Firebase credentials from file: stockboy-5e03a-firebase-adminsdk-fbsvc-0ecab1a414.json
✅ Firebase Admin SDK initialized successfully
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server...
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.31.23:5000
Press CTRL+C to quit
```

## 🌐 Access Your Application

Once the server is running:

- **Admin Login:** http://127.0.0.1:5000/admin-login
  - Username: `stockboy`
  - Password: `stockboy@123`

- **User Login/Register:** http://127.0.0.1:5000

- **Admin Panel:** http://127.0.0.1:5000/admin (after admin login)

## ⚠️ Important Notes

1. **Keep the terminal window open** - Closing it stops the server
2. **Don't close the window** while using the app
3. **Press CTRL+C** to stop the server when done

## 🔧 Troubleshooting

### "Port 5000 already in use"
If you see this error, another process is using port 5000:
```powershell
# Find what's using port 5000
netstat -ano | findstr :5000

# Kill the process (replace PID with the number from above)
taskkill /PID <PID> /F
```

### "Python not found"
Make sure Python is installed and in your PATH:
```powershell
python --version
```

### "Module not found"
Install dependencies:
```powershell
pip install -r requirements.txt
```


