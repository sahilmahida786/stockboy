from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import requests, json, os
from datetime import timedelta, datetime
import hashlib
import random
import string

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.secret_key = os.getenv("SECRET_KEY", "change_this_secret_key")

# -------------------------------------------------
# MAINTENANCE MODE SWITCH
# -------------------------------------------------
MAINTENANCE_MODE = False   # ⛔ Website OFF
# MAINTENANCE_MODE = False  # ✅ Website ON

@app.before_request
def maintenance_blocker():
    allowed_routes = ["maintenance", "admin_login", "register", "login", "forgot_password", "request_otp"]  # Allow auth routes

    if MAINTENANCE_MODE:
        # allow access ONLY to /maintenance, /admin-login, and auth routes
        if request.endpoint not in allowed_routes:
            return redirect("/maintenance")

@app.route("/maintenance")
def maintenance():
    return """
    <html>
    <head>
        <title>Maintenance</title>
        <style>
            body {
                background:#101010;
                color:white;
                text-align:center;
                padding-top:120px;
                font-family: Arial;
            }
            h1 { font-size:40px; color:#ffcc00; }
            p { font-size:20px; }
        </style>
    </head>
    <body>
        <h1>🚧 Website Under Maintenance</h1>
        <p>We’ll be back soon.</p>
    </body>
    </html>
    """


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
# Read secret key from environment variable, fallback to default for local dev
app.secret_key = os.getenv("SECRET_KEY", "change_this_secret_key")
app.permanent_session_lifetime = timedelta(days=7)

DATA_FILE = "payments.json"
LIKES_FILE = "likes.json"
USERS_FILE = "users.json"
OTP_STORAGE = {}  # In-memory OTP storage (in production, use Redis or database)
ACTIVE_SESSIONS = {}  # Track active user sessions
UPLOAD_FOLDER = "static/uploads"  # For course materials (PDFs, videos)
PAYMENT_SS_FOLDER = "payment_ss"   # For payment screenshots only

# Read from environment variables (set in Render dashboard)
BOT_TOKEN = os.getenv("BOT_TOKEN", "7581428285:AAF6qwxQYniDoZnhiwERUP_k0Vlf-k6MVSQ")
CHAT_ID = os.getenv("CHAT_ID", "1924050423")

# -------------------------------------------------
# PRODUCT DEFINITIONS
# -------------------------------------------------
PRODUCTS = {
    "1": {
        "name": "Stock Market Basics PDF",
        "price_offer": 99,  # Offer price
        "price_mrp": 149,    # MRP (Maximum Retail Price)
        "type": "PDF",
        "folder": "product1",  # Files for this product should be in static/uploads/product1/
        "description": "Learn the fundamentals of stock market trading"
    },
    "2": {
        "name": "Candlestick Patterns PDF",
        "price_offer": 149,  # Offer price
        "price_mrp": 199,    # MRP
        "type": "PDF",
        "folder": "product2",  # Files for this product should be in static/uploads/product2/
        "description": "Master candlestick patterns for better trading decisions"
    },
    "3": {
        "name": "Small Beginner Course (Video Lessons)",
        "price_offer": 299,  # Offer price
        "price_mrp": 499,    # MRP
        "type": "Video",
        "folder": "product3",  # Files for this product should be in static/uploads/product3/
        "description": "Complete video course for beginners"
    }
}


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
# USER MANAGEMENT SYSTEM
# -------------------------------------------------
def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    """Load users from JSON file"""
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump([], f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    """Save users to JSON file"""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def username_exists(username):
    """Check if username already exists"""
    users = load_users()
    return any(user["username"].lower() == username.lower() for user in users)

def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def generate_captcha():
    """Generate simple math captcha"""
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    answer = a + b
    return {"question": f"{a} + {b}", "answer": answer}

def get_active_users():
    """Get list of currently logged-in users"""
    active = []
    current_time = datetime.now()
    for username, session_data in ACTIVE_SESSIONS.items():
        # Session expires after 24 hours of inactivity
        if (current_time - session_data["last_activity"]).total_seconds() < 86400:
            active.append({
                "username": username,
                "login_time": session_data["login_time"].isoformat(),
                "last_activity": session_data["last_activity"].isoformat()
            })
    return active

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
    # If user is logged in, redirect to main website
    if session.get("user_logged_in"):
        return redirect("/home")
    # If not logged in, show login/register page
    return render_template("landing.html")

@app.route("/home")
def main_website():
    # Require login to access main website
    if not session.get("user_logged_in"):
        return redirect("/")
    return render_template("index.html", products=PRODUCTS, username=session.get("username"))

# -------------------------------------------------
# USER AUTHENTICATION ROUTES
# -------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        # Validate inputs
        if not username or not password or not mobile:
            return jsonify({"success": False, "message": "Username, mobile number, and password are required"})
        
        if len(username) < 3:
            return jsonify({"success": False, "message": "Username must be at least 3 characters"})
        
        if len(mobile) != 10 or not mobile.isdigit():
            return jsonify({"success": False, "message": "Mobile number must be 10 digits"})
        
        if password != confirm_password:
            return jsonify({"success": False, "message": "Passwords do not match"})
        
        if len(password) < 6:
            return jsonify({"success": False, "message": "Password must be at least 6 characters"})
        
        # Check if username exists
        if username_exists(username):
            return jsonify({"success": False, "message": "Username already exists. Please choose another."})
        
        # Create user
        users = load_users()
        users.append({
            "username": username,
            "mobile": mobile,
            "password": hash_password(password),
            "created_at": datetime.now().isoformat(),
            "purchased_products": []
        })
        save_users(users)
        
        return jsonify({"success": True, "message": "Registration successful! Redirecting to login...", "redirect": "/login"})
    
    # GET request - show registration form
    return render_template("register.html")

@app.route("/check-username", methods=["POST"])
def check_username():
    """Check if username exists"""
    data = request.get_json()
    username = data.get("username", "").strip()
    
    if not username:
        return jsonify({"exists": False})
    
    return jsonify({"exists": username_exists(username)})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            return jsonify({"success": False, "message": "Username and password are required"})
        
        users = load_users()
        user = None
        for u in users:
            if u["username"].lower() == username.lower() and u["password"] == hash_password(password):
                user = u
                break
        
        if not user:
            return jsonify({"success": False, "message": "Invalid username or password"})
        
        # Create session
        session["user_logged_in"] = True
        session["username"] = user["username"]
        session["user_id"] = user["username"]
        
        # Track active session
        ACTIVE_SESSIONS[user["username"]] = {
            "login_time": datetime.now(),
            "last_activity": datetime.now()
        }
        
        return jsonify({"success": True, "message": "Login successful!", "redirect": "/home"})
    
    return render_template("login.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        otp = request.form.get("otp", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not username:
            return jsonify({"success": False, "message": "Username is required"})
        
        users = load_users()
        user = None
        for u in users:
            if u["username"].lower() == username.lower():
                user = u
                break
        
        if not user:
            return jsonify({"success": False, "message": "Username not found"})
        
        # If OTP not provided, send OTP
        if not otp:
            otp_code = generate_otp()
            otp_key = f"reset_{username}"
            OTP_STORAGE[otp_key] = {
                "otp": otp_code,
                "time": datetime.now()
            }
            # In production, send OTP via email/SMS
            return jsonify({"success": True, "otp_sent": True, "otp": otp_code, "message": f"OTP sent! (For testing: {otp_code})"})
        
        # Verify OTP and reset password
        otp_key = f"reset_{username}"
        if otp_key not in OTP_STORAGE:
            return jsonify({"success": False, "message": "OTP not sent. Please request OTP first."})
        
        stored_otp_data = OTP_STORAGE[otp_key]
        if stored_otp_data["otp"] != otp:
            return jsonify({"success": False, "message": "Invalid OTP"})
        
        # Check OTP expiry
        if (datetime.now() - stored_otp_data["time"]).total_seconds() > 300:
            del OTP_STORAGE[otp_key]
            return jsonify({"success": False, "message": "OTP expired. Please request a new one."})
        
        # Validate new password
        if not new_password or len(new_password) < 6:
            return jsonify({"success": False, "message": "Password must be at least 6 characters"})
        
        if new_password != confirm_password:
            return jsonify({"success": False, "message": "Passwords do not match"})
        
        # Update password
        for i, u in enumerate(users):
            if u["username"].lower() == username.lower():
                users[i]["password"] = hash_password(new_password)
                break
        
        save_users(users)
        del OTP_STORAGE[otp_key]
        
        return jsonify({"success": True, "message": "Password reset successful! You can now login."})
    
    return render_template("forgot_password.html")

@app.route("/logout")
def logout():
    username = session.get("username")
    if username and username in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[username]
    session.clear()
    return redirect(url_for("home"))

import os
from werkzeug.utils import secure_filename

# Ensure payment screenshot folder exists
if not os.path.exists(PAYMENT_SS_FOLDER):
    os.makedirs(PAYMENT_SS_FOLDER)

@app.route("/submit_payment", methods=["POST"])
def submit_payment():
    # Require login
    if not session.get("user_logged_in"):
        return jsonify({"message": "⚠️ Please login to submit payment."}), 401
    
    user_name = request.form.get("user_name") or session.get("username", "User")
    txn_id = request.form.get("txn_id")
    screenshot = request.files.get("screenshot")
    product_id = request.form.get("product_id", "1")  # Default to product 1

    # Validate product_id
    if product_id not in PRODUCTS:
        return jsonify({"message": "⚠️ Invalid product selected!"})

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

    product = PRODUCTS[product_id]
    
    # Save new data with product information
    data.append({
        "user": user_name,
        "txn_id": txn_id,
        "status": "pending",
        "ss_path": filepath,
        "product_id": product_id,
        "product_name": product["name"],
        "product_price": f"₹{product['price_offer']} (MRP: ₹{product['price_mrp']})"
    })
    save_data(data)

    # Send Telegram message with inline buttons (use relative path for Telegram)
    send_telegram_photo(
        filepath,
        f"📩 *New Payment Request*\n\n👤 *Name:* {user_name}\n💳 *Txn ID:* `{txn_id}`\n📦 *Product:* {product['name']}\n💰 *Price:* ₹{product['price_offer']} (MRP: ₹{product['price_mrp']})\n⏳ *Status:* Pending Approval",
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
    approved_entry = None
    for x in data:
        if x["txn_id"] == txn_id and x["status"] == "approved":
            approved_entry = x
            break

    if not approved_entry:
        return jsonify({"ok": False})

    # Store approved status and purchased products in session
    session["approved"] = True
    session["user_name"] = user_name
    
    # Get all approved products for this user (by txn_id)
    purchased_products = []
    for entry in data:
        if entry.get("txn_id") == txn_id and entry.get("status") == "approved":
            product_id = entry.get("product_id", "1")
            if product_id not in purchased_products:
                purchased_products.append(product_id)
    
    # Also check by user_name for all their purchases
    user_purchases = []
    for entry in data:
        if entry.get("user") == user_name and entry.get("status") == "approved":
            product_id = entry.get("product_id", "1")
            if product_id not in user_purchases:
                user_purchases.append(product_id)
    
    # Combine both lists
    all_purchased = list(set(purchased_products + user_purchases))
    session["purchased_products"] = all_purchased
    
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
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "Mahida")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Sahil786@")


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
    users = load_users()
    active_users = get_active_users()
    return render_template("admin_panel.html", data=data, users=users, active_users=active_users)

@app.route("/admin/remove-user/<username>")
def remove_user(username):
    if not session.get("admin"):
        return redirect("/admin-login")
    
    users = load_users()
    users = [u for u in users if u["username"].lower() != username.lower()]
    save_users(users)
    
    # Remove from active sessions
    if username in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[username]
    
    return redirect("/admin")

@app.route("/admin/add-user", methods=["POST"])
def admin_add_user():
    if not session.get("admin"):
        return jsonify({"success": False, "message": "Unauthorized"})
    
    username = request.json.get("username", "").strip()
    password = request.json.get("password", "")
    
    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"})
    
    if username_exists(username):
        return jsonify({"success": False, "message": "Username already exists"})
    
    users = load_users()
    users.append({
        "username": username,
        "password": hash_password(password),
        "created_at": datetime.now().isoformat(),
        "purchased_products": [],
        "created_by": "admin"
    })
    save_users(users)
    
    return jsonify({"success": True, "message": "User created successfully"})


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
    # Require login
    if not session.get("user_logged_in"):
        return redirect("/")
    
    if not session.get("approved") and not session.get("user_logged_in"):
        return redirect("/home")
    
    # Update last activity for logged-in users
    username = session.get("username")
    if username and username in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS[username]["last_activity"] = datetime.now()

    # Get purchased products from session
    purchased_products = session.get("purchased_products", [])
    
    # If no purchased products in session, check from payments.json
    if not purchased_products:
        user_name = session.get("user_name", "")
        data = load_data()
        purchased_products = []
        for entry in data:
            if entry.get("user") == user_name and entry.get("status") == "approved":
                product_id = entry.get("product_id", "1")
                if product_id not in purchased_products:
                    purchased_products.append(product_id)
        session["purchased_products"] = purchased_products

    # Only get course materials from purchased products
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

    # For each purchased product, get files from its folder
    for product_id in purchased_products:
        if product_id not in PRODUCTS:
            continue
            
        product = PRODUCTS[product_id]
        product_folder = os.path.join(UPLOAD_FOLDER, product["folder"])
        
        # Check if product folder exists
        if not os.path.exists(product_folder):
            continue
            
        files = os.listdir(product_folder)
        
        for f in files:
            ext = f.lower().split('.')[-1]
            
            # Only include course materials
            if ext not in COURSE_EXTENSIONS:
                continue
            
            # Skip image files
            if ext in ["png", "jpg", "jpeg", "gif", "webp"]:
                continue
            
            kind = COURSE_EXTENSIONS.get(ext, "File")
            
            # Use product name as module name
            mod = product["name"]
            
            modules.setdefault(mod, []).append({
                "name": f,
                "url": f"/static/uploads/{product['folder']}/{f}",
                "kind": kind,
                "product_id": product_id
            })

    return render_template("dashboard.html", name=session.get("user_name"), modules=modules, products=PRODUCTS, purchased_products=purchased_products)


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
                    product_name = entry.get("product_name", "Product")
                    edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageCaption"
                    new_caption = f"✅ *Payment Approved*\n\n👤 *Name:* {entry['user']}\n💳 *Txn ID:* `{txn_id}`\n📦 *Product:* {product_name}\n🔓 *Status:* Product Unlocked"
                    requests.post(edit_url, json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "caption": new_caption,
                        "parse_mode": "Markdown"
                    })
                    
                    # Send confirmation
                    send_telegram(f"✅ *Approved*\n\n👤 {entry['user']}\n💳 `{txn_id}`\n📦 {product_name}\n🔓 Product Unlocked")
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
# SERVE PRODUCT FILES
# -------------------------------------------------
@app.route("/static/uploads/<product_folder>/<filename>")
def serve_product_file(product_folder, filename):
    """Serve product files from their respective folders"""
    if not session.get("approved"):
        return "Unauthorized", 403
    
    # Check if user has access to this product
    purchased_products = session.get("purchased_products", [])
    user_name = session.get("user_name", "")
    
    # If no purchased products in session, check from payments.json
    if not purchased_products:
        data = load_data()
        for entry in data:
            if entry.get("user") == user_name and entry.get("status") == "approved":
                product_id = entry.get("product_id", "1")
                if product_id not in purchased_products:
                    purchased_products.append(product_id)
    
    # Find which product this folder belongs to
    product_id = None
    for pid, product in PRODUCTS.items():
        if product["folder"] == product_folder:
            product_id = pid
            break
    
    # Check if user has purchased this product
    if product_id and product_id in purchased_products:
        file_path = os.path.join(UPLOAD_FOLDER, product_folder, filename)
        if os.path.exists(file_path):
            return send_from_directory(os.path.join(UPLOAD_FOLDER, product_folder), filename)
    
    return "Access Denied", 403


# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

