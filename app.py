from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import requests, json, os
from datetime import timedelta

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
# Read secret key from environment variable, fallback to default for local dev
app.secret_key = os.getenv("SECRET_KEY", "change_this_secret_key")
app.permanent_session_lifetime = timedelta(days=7)

DATA_FILE = "payments.json"
LIKES_FILE = "likes.json"
UPLOAD_FOLDER = "static/uploads"  # For course materials (PDFs, videos)
PAYMENT_SS_FOLDER = "payment_ss"   # For payment screenshots only

# Read from environment variables (set in Render dashboard)
BOT_TOKEN = os.getenv("BOT_TOKEN", "7581428285:AAF6qwxQYniDoZnhiwERUP_k0Vlf-k6MVSQ")
CHAT_ID = os.getenv("CHAT_ID", "1924050423")


# -------------------------------------------------
# TELEGRAM SENDER (CLEAN + NO DUPLICATION)
# -------------------------------------------------
def send_telegram(message, txn_id=None, parse_mode="Markdown"):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    if txn_id:
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve", "callback_data": f"approve_{txn_id}"},
                    {"text": "❌ Reject", "callback_data": f"reject_{txn_id}"}
                ]
            ]
        }
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "reply_markup": json.dumps(keyboard),
            "parse_mode": parse_mode
        }
    else:
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": parse_mode
        }

    requests.post(url, json=payload)

def send_telegram_photo(photo_path, caption, txn_id=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    
    with open(photo_path, "rb") as photo_file:
        files = {"photo": photo_file}
        data = {
            "chat_id": CHAT_ID, 
            "caption": caption,
            "parse_mode": "Markdown"
        }
        
        # Add inline keyboard buttons if txn_id is provided
        if txn_id:
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Approve", "callback_data": f"approve_{txn_id}"},
                        {"text": "❌ Reject", "callback_data": f"reject_{txn_id}"}
                    ]
                ]
            }
            data["reply_markup"] = json.dumps(keyboard)
        
        requests.post(url, files=files, data=data)

# -------------------------------------------------
# FOLDER CHECK
# -------------------------------------------------
def ensure_folders():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

ensure_folders()


# -------------------------------------------------
# PAYMENT SYSTEM
# -------------------------------------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump([], f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/")
def home():
    return render_template("index.html")

import os
from werkzeug.utils import secure_filename

# Ensure payment screenshot folder exists
if not os.path.exists(PAYMENT_SS_FOLDER):
    os.makedirs(PAYMENT_SS_FOLDER)

@app.route("/submit_payment", methods=["POST"])
def submit_payment():
    user_name = request.form.get("user_name")
    txn_id = request.form.get("txn_id")
    screenshot = request.files.get("screenshot")

    # Load old data
    data = load_data()

    # 🔥 STOP MULTIPLE SUBMISSIONS (IMPORTANT)
    for entry in data:
        if entry["txn_id"] == txn_id:
            return jsonify({"message": "⚠️ This payment is already submitted!"})

    # Save screenshot to payment_ss folder (NOT in course uploads)
    filename = secure_filename(f"{txn_id}.png")
    filepath = os.path.join(PAYMENT_SS_FOLDER, filename)
    screenshot.save(filepath)

    # Save new data
    data.append({
        "user": user_name,
        "txn_id": txn_id,
        "status": "pending",
        "ss_path": filepath
    })
    save_data(data)

    # Send Telegram message with inline buttons (use relative path for Telegram)
    send_telegram_photo(
        filepath,
        f"📩 *New Payment Request*\n\n👤 *Name:* {user_name}\n💳 *Txn ID:* `{txn_id}`\n⏳ *Status:* Pending Approval",
        txn_id=txn_id
    )
    
    # Update ss_path to be relative for web access
    data[-1]["ss_path"] = filepath  # Keep full path for file access

    return jsonify({"message": "✅ Payment Submitted! Wait for approval."})


@app.route("/check_approval", methods=["POST"])
def check_approval():
    txn_id = request.form.get("txn_id")

    data = load_data()
    for x in data:
        if x["txn_id"] == txn_id:
            return jsonify({"status": x["status"]})

    return jsonify({"status": "not_found"})


@app.route("/start_session", methods=["POST"])
def start_session():
    txn_id = request.form.get("txn_id")
    user_name = request.form.get("user_name", "User")

    data = load_data()
    approved = any(x["txn_id"] == txn_id and x["status"] == "approved" for x in data)

    if not approved:
        return jsonify({"ok": False})

    session["approved"] = True
    session["user_name"] = user_name
    return jsonify({"ok": True, "redirect": url_for("dashboard")})


# -------------------------------------------------
# LIKES SYSTEM
# -------------------------------------------------
def load_likes():
    if not os.path.exists(LIKES_FILE):
        with open(LIKES_FILE, "w") as f:
            json.dump({"likes": 0}, f)
    with open(LIKES_FILE, "r") as f:
        return json.load(f)


def save_likes(data):
    with open(LIKES_FILE, "w") as f:
        json.dump(data, f, indent=4)


@app.route("/like", methods=["POST"])
def like_site():
    data = load_likes()
    data["likes"] += 1
    save_likes(data)
    return jsonify(data)


@app.route("/get_likes")
def get_likes():
    return jsonify(load_likes())


# -------------------------------------------------
# ADMIN LOGIN + PANEL
# -------------------------------------------------
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "stockboy")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "stockboy@123")


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user = request.form.get("username")
        pwd = request.form.get("password")

        if user == ADMIN_USERNAME and pwd == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")

        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Admin Login – Stockboy</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <script>
          tailwind.config = {
            theme: {
              extend: {
                colors: {
                  gold: { light: '#f6d67c', DEFAULT: '#d9a520' },
                  dark: { bg1: '#0f2027', bg2: '#203a43', bg3: '#2c5364' }
                },
                fontFamily: { sans: ['Poppins', 'sans-serif'] }
              }
            }
          }
        </script>
        <style>
          .bg-gradient-dark { background: linear-gradient(160deg, #0f2027, #203a43, #2c5364); }
          .text-gradient-gold {
            background: linear-gradient(90deg, #f6d67c, #d9a520);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
          }
        </style>
        </head>
        <body class="bg-gradient-dark text-white font-sans min-h-screen flex items-center justify-center px-4">
        <div class="bg-black/40 backdrop-blur-md rounded-2xl p-8 border border-white/10 shadow-2xl max-w-md w-full">
          <div class="text-center mb-6">
            <h2 class="text-2xl font-bold text-gradient-gold mb-2">Admin Login</h2>
            <p class="text-red-400 text-sm">Invalid Credentials</p>
          </div>
          <form method="POST" class="space-y-4">
            <input name='username' placeholder='Username' 
                   class='w-full px-4 py-3 bg-white/10 backdrop-blur-md border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gold-DEFAULT'>
            <input name='password' type='password' placeholder='Password' 
                   class='w-full px-4 py-3 bg-white/10 backdrop-blur-md border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gold-DEFAULT'>
            <button type='submit' 
                    class='w-full bg-gradient-to-r from-gold-light to-gold-DEFAULT text-gray-900 font-bold py-3 px-6 rounded-xl shadow-lg shadow-yellow-500/50 hover:shadow-yellow-500/70 transition-all duration-300 active:scale-95'>
              Login
            </button>
          </form>
        </div>
        </body>
        </html>
        """

    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Admin Login – Stockboy</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <script>
      tailwind.config = {
        theme: {
          extend: {
            colors: {
              gold: { light: '#f6d67c', DEFAULT: '#d9a520' },
              dark: { bg1: '#0f2027', bg2: '#203a43', bg3: '#2c5364' }
            },
            fontFamily: { sans: ['Poppins', 'sans-serif'] }
          }
        }
      }
    </script>
    <style>
      .bg-gradient-dark { background: linear-gradient(160deg, #0f2027, #203a43, #2c5364); }
      .text-gradient-gold {
        background: linear-gradient(90deg, #f6d67c, #d9a520);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }
    </style>
    </head>
    <body class="bg-gradient-dark text-white font-sans min-h-screen flex items-center justify-center px-4">
    <div class="bg-black/40 backdrop-blur-md rounded-2xl p-8 border border-white/10 shadow-2xl max-w-md w-full">
      <div class="text-center mb-6">
        <img src="/static/logo.png" alt="Logo" class="w-16 h-16 mx-auto mb-4 rounded-full shadow-lg shadow-yellow-500/45">
        <h2 class="text-2xl font-bold text-gradient-gold mb-2">Admin Login</h2>
        <p class="text-gray-400 text-sm">Enter your credentials to access the admin panel</p>
      </div>
      <form method="POST" class="space-y-4">
        <input name='username' placeholder='Username' 
               class='w-full px-4 py-3 bg-white/10 backdrop-blur-md border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gold-DEFAULT'>
        <input name='password' type='password' placeholder='Password' 
               class='w-full px-4 py-3 bg-white/10 backdrop-blur-md border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gold-DEFAULT'>
        <button type='submit' 
                class='w-full bg-gradient-to-r from-gold-light to-gold-DEFAULT text-gray-900 font-bold py-3 px-6 rounded-xl shadow-lg shadow-yellow-500/50 hover:shadow-yellow-500/70 transition-all duration-300 active:scale-95'>
          Login
        </button>
      </form>
    </div>
    </body>
    </html>
    """


@app.route("/admin")
def admin_panel():
    if not session.get("admin"):
        return redirect("/admin-login")

    data = load_data()
    return render_template("admin_panel.html", data=data)


@app.route("/approve/<int:index>")
def approve(index):
    data = load_data()
    user = data[index]["user"]
    txn_id = data[index]["txn_id"]

    data[index]["status"] = "approved"
    save_data(data)

    send_telegram(f"✅ Payment Approved\n\n👤 {user}\n💳 {txn_id}\n🔓 Dashboard Access Granted")

    return redirect("/admin")


@app.route("/reject/<int:index>")
def reject(index):
    data = load_data()
    user = data[index]["user"]
    txn_id = data[index]["txn_id"]

    data[index]["status"] = "rejected"
    save_data(data)

    send_telegram(f"❌ Payment Rejected\n\n👤 {user}\n💳 {txn_id}\n🚫 Access Denied")

    return redirect("/admin")


# -------------------------------------------------
# FILE UPLOAD
# -------------------------------------------------
@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        f = request.files["file"]
        f.save(os.path.join(UPLOAD_FOLDER, f.filename))
        return redirect("/upload")

    files = os.listdir(UPLOAD_FOLDER)
    return render_template("upload.html", files=files)


# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------
@app.route("/dashboard")
def dashboard():
    if not session.get("approved"):
        return redirect(url_for("home"))

    # Only get course materials from uploads folder
    files = os.listdir(UPLOAD_FOLDER)
    modules = {}

    # Allowed course file extensions
    COURSE_EXTENSIONS = {
        "pdf": "PDF",
        "mp4": "Video",
        "mkv": "Video",
        "webm": "Video",
        "avi": "Video",
        "mov": "Video",
        "mp3": "Audio",
        "wav": "Audio"
    }

    for f in files:
        # Skip payment screenshots and non-course files
        ext = f.lower().split('.')[-1]
        
        # Only include course materials (PDFs, videos, audio)
        if ext not in COURSE_EXTENSIONS:
            continue
        
        # Skip PNG/JPG files (these are payment screenshots, not course materials)
        if ext in ["png", "jpg", "jpeg", "gif", "webp"]:
            continue
        
        kind = COURSE_EXTENSIONS.get(ext, "File")

        # Extract module number from filename (e.g., M1_filename.pdf)
        mod = "M1"  # Default module
        if "_" in f:
            tag = f.split("_")[0]
            if tag.lower().startswith("m") and tag[1:].isdigit():
                mod = tag.upper()

        modules.setdefault(mod, []).append({
            "name": f,
            "url": f"/static/uploads/{f}",
            "kind": kind
        })

    return render_template("dashboard.html", name=session.get("user_name"), modules=modules)


# -------------------------------------------------
# TELEGRAM CALLBACK (APPROVE/REJECT) - OPTIMIZED
# -------------------------------------------------
@app.route("/telegram-update", methods=["POST"])
def telegram_update():
    try:
        data = request.get_json()
        if not data or "callback_query" not in data:
            return "OK", 200

        cb = data["callback_query"]
        action = cb["data"]
        callback_id = cb["id"]
        message_id = cb["message"]["message_id"]
        chat_id = cb["message"]["chat"]["id"]

        # Answer callback immediately to show button was clicked
        answer_url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
        requests.post(answer_url, json={"callback_query_id": callback_id})

        payments = load_data()
        processed = False

        if action.startswith("approve_"):
            txn_id = action.replace("approve_", "")
            for i, entry in enumerate(payments):
                if entry["txn_id"] == txn_id and entry["status"] == "pending":
                    payments[i]["status"] = "approved"
                    save_data(payments)
                    
                    # Update message with approved status
                    edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageCaption"
                    new_caption = f"✅ *Payment Approved*\n\n👤 *Name:* {entry['user']}\n💳 *Txn ID:* `{txn_id}`\n🔓 *Status:* Dashboard Unlocked"
                    requests.post(edit_url, json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "caption": new_caption,
                        "parse_mode": "Markdown"
                    })
                    
                    # Send confirmation
                    send_telegram(f"✅ *Approved*\n\n👤 {entry['user']}\n💳 `{txn_id}`\n🔓 Dashboard Unlocked")
                    processed = True
                    break

        elif action.startswith("reject_"):
            txn_id = action.replace("reject_", "")
            for i, entry in enumerate(payments):
                if entry["txn_id"] == txn_id and entry["status"] == "pending":
                    payments[i]["status"] = "rejected"
                    save_data(payments)
                    
                    # Update message with rejected status
                    edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageCaption"
                    new_caption = f"❌ *Payment Rejected*\n\n👤 *Name:* {entry['user']}\n💳 *Txn ID:* `{txn_id}`\n🚫 *Status:* Access Denied"
                    requests.post(edit_url, json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "caption": new_caption,
                        "parse_mode": "Markdown"
                    })
                    
                    # Send confirmation
                    send_telegram(f"❌ *Rejected*\n\n👤 {entry['user']}\n💳 `{txn_id}`\n🚫 Access Denied")
                    processed = True
                    break

        if not processed:
            # If already processed, show alert
            requests.post(answer_url, json={
                "callback_query_id": callback_id,
                "text": "This payment has already been processed",
                "show_alert": False
            })

    except Exception as e:
        print(f"Telegram update error: {e}")
        return "OK", 200

    return "OK", 200


# -------------------------------------------------
# VIEW PDF AND VIDEO
# -------------------------------------------------
@app.route("/view_pdf/<filename>")
def view_pdf(filename):
    return render_template("view_pdf.html", filename=filename)

@app.route("/view_video/<filename>")
def view_video(filename):
    return render_template("view_video.html", filename=filename)

# -------------------------------------------------
# SERVE PAYMENT SCREENSHOTS
# -------------------------------------------------
@app.route("/payment_ss/<filename>")
def serve_payment_ss(filename):
    """Serve payment screenshots from payment_ss folder"""
    return send_from_directory(PAYMENT_SS_FOLDER, filename)


# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

