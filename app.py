from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import requests, json, os, threading, time, re
import mysql.connector
from datetime import timedelta, datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
# Read secret key from environment variable, fallback to default for local dev
app.secret_key = os.getenv("SECRET_KEY", "change_this_secret_key")
app.permanent_session_lifetime = timedelta(days=7)

# -------------------------------------------------
# MAINTENANCE MODE SWITCH
# -------------------------------------------------
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"

@app.before_request
def maintenance_blocker():
    allowed_routes = ["maintenance", "admin_login", "telegram_update"]  # admin & bots allowed

    if MAINTENANCE_MODE:
        # allow access ONLY to /maintenance and /admin-login
        if request.endpoint not in allowed_routes:
            return redirect("/maintenance")

@app.before_request
def require_login():
    """Require login for all pages except login, register, static files, and admin"""
    # Skip for static files
    if request.endpoint == "static":
        return None
    
    # Pages that don't require login (public routes - only login/register and admin)
    public_routes = ["home", "auth_page", "login", "register", "admin_login", "maintenance", 
                     "telegram_update"]
    
    # Skip authentication check for public routes
    if request.endpoint in public_routes:
        return None
    
    # Check if user is logged in for all other pages
    if not (session.get("logged_in") or session.get("user_id")):
        return redirect(url_for("home"))

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

DATA_FILE = "payments.json"
LIKES_FILE = "likes.json"
USERS_FILE = "users.json"  # JSON fallback for user storage
UPLOAD_FOLDER = "static/uploads"  # For course materials (PDFs, videos)
PAYMENT_SS_FOLDER = "payment_ss"   # For payment screenshots only

# Read from environment variables (set in Render dashboard)
BOT_TOKEN = os.getenv("BOT_TOKEN", "7581428285:AAF6qwxQYniDoZnhiwERUP_k0Vlf-k6MVSQ")
CHAT_ID = os.getenv("CHAT_ID", "1924050423")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
BOT_LISTENER_ENABLED = os.getenv("ENABLE_BOT_LISTENER", "true").lower() == "true"
BOT_POLL_TIMEOUT = int(os.getenv("BOT_POLL_TIMEOUT", "10"))

# MySQL Configuration - Auto-detects if MySQL is available, falls back to JSON if not
# To use MySQL, set environment variables:
# USE_MYSQL=true (optional, will auto-detect if MySQL credentials are provided)
# MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
USE_MYSQL_ENV = os.getenv("USE_MYSQL", "").lower()
# Auto-enable MySQL if credentials are provided, or explicitly set via env var
USE_MYSQL = USE_MYSQL_ENV == "true" or (USE_MYSQL_ENV == "" and os.getenv("MYSQL_HOST") and os.getenv("MYSQL_PASSWORD"))

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "stockboy"),
}

PASSWORD_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%?&])[A-Za-z\d@$!%?&]{6,}$"
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

PRODUCT_DETAILS = {
    "product1": {
        "title": "Stockboy Starter Kit",
        "tagline": "Market basics + first profitable trades",
        "price": "₹1,499",
        "level": "Beginner"
    },
    "product2": {
        "title": "Price Action Accelerator",
        "tagline": "Institutional price-action systems",
        "price": "₹3,499",
        "level": "Intermediate"
    },
    "product3": {
        "title": "Pro Options Lab",
        "tagline": "Elite options flow + psychology",
        "price": "₹4,999",
        "level": "Advanced"
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


def handle_telegram_callback(payload):
    """Shared handler for Telegram callback queries."""
    if not payload or "callback_query" not in payload:
        return False

    try:
        cb = payload["callback_query"]
        action = cb["data"]
        callback_id = cb["id"]
        message_id = cb["message"]["message_id"]
        chat_id = cb["message"]["chat"]["id"]

        answer_url = f"{API_URL}/answerCallbackQuery"
        requests.post(answer_url, json={"callback_query_id": callback_id})

        payments = load_data()
        processed = False

        if action.startswith("approve_"):
            txn_id = action.replace("approve_", "")
            for i, entry in enumerate(payments):
                if entry["txn_id"] == txn_id and entry["status"] == "pending":
                    payments[i]["status"] = "approved"
                    save_data(payments)

                    edit_url = f"{API_URL}/editMessageCaption"
                    new_caption = (
                        f"✅ *Payment Approved*\n\n"
                        f"👤 *Name:* {entry['user']}\n"
                        f"💳 *Txn ID:* `{txn_id}`\n"
                        f"🔓 *Status:* Dashboard Unlocked"
                    )
                    requests.post(edit_url, json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "caption": new_caption,
                        "parse_mode": "Markdown"
                    })
                    send_telegram(f"✅ *Approved*\n\n👤 {entry['user']}\n💳 `{txn_id}`\n🔓 Dashboard Unlocked")
                    processed = True
                    break

        elif action.startswith("reject_"):
            txn_id = action.replace("reject_", "")
            for i, entry in enumerate(payments):
                if entry["txn_id"] == txn_id and entry["status"] == "pending":
                    payments[i]["status"] = "rejected"
                    save_data(payments)

                    edit_url = f"{API_URL}/editMessageCaption"
                    new_caption = (
                        f"❌ *Payment Rejected*\n\n"
                        f"👤 *Name:* {entry['user']}\n"
                        f"💳 *Txn ID:* `{txn_id}`\n"
                        f"🚫 *Status:* Access Denied"
                    )
                    requests.post(edit_url, json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "caption": new_caption,
                        "parse_mode": "Markdown"
                    })
                    send_telegram(f"❌ *Rejected*\n\n👤 {entry['user']}\n💳 `{txn_id}`\n🚫 Access Denied")
                    processed = True
                    break

        if not processed:
            requests.post(answer_url, json={
                "callback_query_id": callback_id,
                "text": "This payment has already been processed",
                "show_alert": False
            })

        return True
    except Exception as exc:
        print(f"Telegram callback error: {exc}")
        return False

# -------------------------------------------------
# FOLDER CHECK
# -------------------------------------------------
def ensure_folders():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

ensure_folders()


# -------------------------------------------------
# DATABASE HELPERS (MySQL + JSON Fallback)
# -------------------------------------------------
_db_available = None  # Cache for database availability check

def check_db_available():
    """Check if MySQL database is available and enabled."""
    global _db_available
    if _db_available is not None:
        return _db_available
    
    # If MySQL is explicitly disabled, don't try
    if USE_MYSQL_ENV == "false":
        _db_available = False
        return False
    
    # If no MySQL credentials provided, use JSON
    if not MYSQL_CONFIG.get("host") or not MYSQL_CONFIG.get("password"):
        _db_available = False
        return False
    
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        conn.close()
        _db_available = True
        print("✅ MySQL database connection successful - using MySQL for user storage")
        return True
    except Exception as e:
        print(f"⚠️ MySQL connection failed, using JSON storage: {e}")
        _db_available = False
        return False


def get_db_connection():
    """Create a new MySQL connection using env config."""
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")
        raise


def init_database():
    """Initialize database - Try MySQL first if credentials available, otherwise JSON."""
    # Try MySQL first if credentials are provided
    if check_db_available():
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                mobile VARCHAR(15) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                registration_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            cur.execute(create_table_sql)
            conn.commit()
            print("✅ MySQL database initialized successfully - user data will be stored in database")
            cur.close()
        except mysql.connector.Error as e:
            print(f"❌ MySQL initialization failed: {e}")
            print(f"   Falling back to JSON file storage (users.json)")
            init_json_storage()
        finally:
            if conn and conn.is_connected():
                conn.close()
    else:
        # No MySQL credentials or MySQL disabled - use JSON
        init_json_storage()


def init_json_storage():
    """Initialize JSON file storage for users."""
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump([], f)
    print("✅ JSON file storage ready - using users.json")


# User storage functions
def load_users_json():
    """Load users from JSON file."""
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading users.json: {e}")
        return []


def save_users_json(users):
    """Save users to JSON file."""
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)
    except Exception as e:
        print(f"Error saving users.json: {e}")
        raise


# Initialize storage on startup
try:
    init_database()
except Exception as e:
    print(f"⚠️ Storage initialization error: {e}")
    init_json_storage()


def is_valid_password(password):
    """Enforce at least one lower/upper/number/special, min 6 chars."""
    return bool(password and re.match(PASSWORD_REGEX, password))


def get_product_catalog():
    """Build public product listing from configured folders."""
    catalog = []
    for slug, meta in PRODUCT_DETAILS.items():
        folder = os.path.join(UPLOAD_FOLDER, slug)
        files = []
        if os.path.isdir(folder):
            for name in os.listdir(folder):
                ext = name.rsplit(".", 1)[-1].lower()
                if ext in COURSE_EXTENSIONS:
                    files.append(name)

        catalog.append({
            "slug": slug,
            "title": meta["title"],
            "tagline": meta["tagline"],
            "price": meta["price"],
            "level": meta["level"],
            "file_count": len(files),
            "preview": files[0] if files else None,
        })
    return catalog


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
    """Homepage - Show login/register page"""
    # Only redirect if user is approved and logged in
    if session.get("approved"):
        return redirect(url_for("dashboard"))
    # For logged-in users without approval, show products page or auth page
    if session.get("logged_in") or session.get("user_id"):
        return redirect(url_for("products_page"))
    return render_template("auth.html")

@app.route("/products")
def products_page():
    """Product catalog page - requires login"""
    # Authentication is handled by before_request
    if not (session.get("logged_in") or session.get("user_id")):
        return redirect(url_for("home"))
    return render_template("products.html", products=get_product_catalog())

@app.route("/about")
def about_page():
    """About page - requires login"""
    # Authentication is handled by before_request
    if not (session.get("logged_in") or session.get("user_id")):
        return redirect(url_for("home"))
    return render_template("about.html")

@app.route("/payment")
def payment_page():
    """Payment page - requires login"""
    # Authentication is handled by before_request
    if not (session.get("logged_in") or session.get("user_id")):
        return redirect(url_for("home"))
    return render_template("index.html")

@app.route("/auth")
def auth_page():
    """Auth page (alias for homepage)"""
    # Redirect if user is already logged in
    if session.get("logged_in") or session.get("user_id"):
        # If approved, go to dashboard; otherwise go to products page
        if session.get("approved"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("products_page"))
    return render_template("auth.html")

import os
from werkzeug.utils import secure_filename

# Ensure payment screenshot folder exists
if not os.path.exists(PAYMENT_SS_FOLDER):
    os.makedirs(PAYMENT_SS_FOLDER)

@app.route("/submit_payment", methods=["POST"])
def submit_payment():
    try:
        user_name = request.form.get("user_name")
        txn_id = request.form.get("txn_id")
        screenshot = request.files.get("screenshot")

        if not user_name or not txn_id:
            return jsonify({"message": "⚠️ Please enter name and transaction ID."}), 400

        if not screenshot:
            return jsonify({"message": "⚠️ Please upload payment screenshot."}), 400

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
    except Exception as e:
        print(f"Payment submission error: {e}")
        return jsonify({"message": "❌ Error submitting payment. Please try again."}), 500


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
# USER REGISTRATION & LOGIN (Hybrid: MySQL or JSON)
# -------------------------------------------------
@app.route("/register", methods=["POST"])
def register_user():
    try:
        payload = request.get_json(silent=True) or request.form
        username = (payload.get("username") or "").strip()
        mobile = (payload.get("mobile") or "").strip()
        password = payload.get("password") or ""

        if not username or not mobile or not password:
            return jsonify({"error": "Missing username, mobile, or password"}), 400

        if not is_valid_password(password):
            return jsonify({"error": "Weak password. Include A, a, 1, @ and min 6 chars"}), 400

        # Try MySQL first if available
        if check_db_available():
            conn = None
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                # Hash password before storing
                hashed_password = generate_password_hash(password)
                sql = """
                    INSERT INTO users (username, mobile, password, registration_date)
                    VALUES (%s, %s, %s, %s)
                """
                cur.execute(sql, (username, mobile, hashed_password, datetime.now()))
                user_id = cur.lastrowid
                conn.commit()
                cur.close()
                
                # Registration successful - redirect to login page (no auto-login)
                return jsonify({"message": "User registered successfully! Please login.", "redirect": url_for("home")}), 201
            except mysql.connector.IntegrityError:
                return jsonify({"error": "Mobile number already registered. Please login instead."}), 409
            except Exception as e:
                print(f"MySQL register error, falling back to JSON: {e}")
                import traceback
                traceback.print_exc()
                # Fall through to JSON storage
            finally:
                if conn and conn.is_connected():
                    conn.close()

        # Use JSON storage (fallback or default)
        users = load_users_json()
        
        # Check if mobile already exists
        if any(u.get("mobile") == mobile for u in users):
            return jsonify({"error": "Mobile number already registered. Please login instead."}), 409
        
        # Hash password before storing
        hashed_password = generate_password_hash(password)
        # Create new user
        new_user = {
            "id": len(users) + 1,
            "username": username,
            "mobile": mobile,
            "password": hashed_password,
            "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        users.append(new_user)
        save_users_json(users)
        
        # Registration successful - redirect to login page (no auto-login)
        return jsonify({"message": "User registered successfully! Please login.", "redirect": url_for("home")}), 201
    except Exception as e:
        print(f"Register route error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Registration failed. Please try again."}), 500


@app.route("/login", methods=["POST"])
def login_user():
    try:
        payload = request.get_json(silent=True) or request.form
        mobile = (payload.get("mobile") or "").strip()
        password = payload.get("password") or ""

        if not mobile or not password:
            return jsonify({"error": "Missing mobile or password"}), 400

        # Try MySQL first if available
        if check_db_available():
            conn = None
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                sql = """
                    SELECT id, username, password, registration_date
                    FROM users WHERE mobile=%s
                """
                cur.execute(sql, (mobile,))
                row = cur.fetchone()
                cur.close()
                
                # Check password using hash comparison (supports both hashed and plain text for migration)
                if not row:
                    return jsonify({"error": "Invalid mobile number or password"}), 401
                
                stored_password = row[2]
                # Try checking hashed password first, then plain text (for backwards compatibility)
                password_valid = False
                if stored_password.startswith("$2b$") or stored_password.startswith("$2a$") or stored_password.startswith("pbkdf2:"):
                    # It's a hashed password
                    password_valid = check_password_hash(stored_password, password)
                else:
                    # Plain text password (legacy support)
                    password_valid = (stored_password == password)
                
                if not password_valid:
                    return jsonify({"error": "Invalid mobile number or password"}), 401

                session["user_id"] = row[0]
                session["username"] = row[1]
                session["logged_in"] = True
                reg_date = row[3]
                session["reg_date"] = reg_date.strftime("%Y-%m-%d %H:%M:%S") if reg_date else ""

                return jsonify({"message": "Login successful!", "redirect": url_for("products_page"), "registration_date": session["reg_date"]})
            except Exception as e:
                print(f"MySQL login error, falling back to JSON: {e}")
                import traceback
                traceback.print_exc()
                # Fall through to JSON storage
            finally:
                if conn and conn.is_connected():
                    conn.close()

        # Use JSON storage (fallback or default)
        users = load_users_json()
        user = None
        for u in users:
            if u.get("mobile") == mobile:
                stored_password = u.get("password", "")
                # Try checking hashed password first, then plain text (for backwards compatibility)
                password_valid = False
                if stored_password.startswith("$2b$") or stored_password.startswith("$2a$") or stored_password.startswith("pbkdf2:"):
                    # It's a hashed password
                    password_valid = check_password_hash(stored_password, password)
                else:
                    # Plain text password (legacy support)
                    password_valid = (stored_password == password)
                
                if password_valid:
                    user = u
                    break
        
        if not user:
            return jsonify({"error": "Invalid mobile number or password"}), 401

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["logged_in"] = True
        session["reg_date"] = user.get("registration_date", "")
        
        return jsonify({"message": "Login successful!", "redirect": url_for("products_page"), "registration_date": session["reg_date"]})
    except Exception as e:
        print(f"Login route error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Login failed. Please try again."}), 500


@app.route("/logout")
def logout():
    """Clear user session and logout"""
    session.clear()
    return redirect(url_for("home"))


@app.route("/check-subscription")
def check_subscription():
    reg_date_str = session.get("reg_date")
    if not reg_date_str:
        return jsonify({"status": "unknown", "message": "Login required"}), 401

    try:
        reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return jsonify({"status": "unknown", "message": "Registration date invalid"}), 400

    if datetime.now() - reg_date > timedelta(days=30):
        return jsonify({"status": "expired", "message": "Your Premium expired!"})

    return jsonify({"status": "active", "message": "Premium active!"})


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
    # Only allow access if user has approved payment (dashboard is premium only)
    if not session.get("approved"):
        return redirect(url_for("products_page"))

    modules = {}

    for root, _, files in os.walk(UPLOAD_FOLDER):
        rel_dir = os.path.relpath(root, UPLOAD_FOLDER)
        rel_dir = "" if rel_dir == "." else rel_dir.replace("\\", "/")

        for filename in files:
            ext = filename.rsplit(".", 1)[-1].lower()
            if ext not in COURSE_EXTENSIONS:
                continue

            kind = COURSE_EXTENSIONS.get(ext, "File")

            module_name = "General"
            if rel_dir:
                module_name = rel_dir.title()
            else:
                tag = filename.split("_")[0]
                if tag.lower().startswith("m") and tag[1:].isdigit():
                    module_name = tag.upper()

            rel_path = filename if not rel_dir else f"{rel_dir}/{filename}"
            modules.setdefault(module_name, []).append({
                "name": filename,
                "url": f"/static/uploads/{rel_path}",
                "path": rel_path,  # Relative path for PDF/Video viewer
                "kind": kind
            })

    # Get username from session - check both payment-based and login-based sessions
    user_name = session.get("user_name") or session.get("username") or "User"
    return render_template("dashboard.html", name=user_name, modules=modules)


# -------------------------------------------------
# TELEGRAM CALLBACK (APPROVE/REJECT) - OPTIMIZED
# -------------------------------------------------
@app.route("/telegram-update", methods=["POST"])
def telegram_update():
    data = request.get_json()
    if not handle_telegram_callback(data):
        return "OK", 200
    return "OK", 200


# -------------------------------------------------
# TELEGRAM BOT LISTENER (LONG POLLING)
# -------------------------------------------------
_listener_thread = None


def bot_listener_loop():
    """Continuously poll Telegram for callback updates."""
    last_update_id = None
    print("Telegram listener thread started")

    while True:
        try:
            response = requests.get(
                f"{API_URL}/getUpdates",
                params={"offset": last_update_id, "timeout": BOT_POLL_TIMEOUT},
                timeout=BOT_POLL_TIMEOUT + 5,
            )
            response.raise_for_status()
            data = response.json()

            if "result" not in data:
                time.sleep(1)
                continue

            for update in data.get("result", []):
                last_update_id = update["update_id"] + 1
                if "callback_query" in update:
                    handle_telegram_callback(update)

        except Exception as exc:
            print(f"Telegram listener error: {exc}")
            time.sleep(5)


def start_bot_listener():
    """Start the listener thread exactly once."""
    global _listener_thread
    if not BOT_LISTENER_ENABLED:
        return

    if _listener_thread and _listener_thread.is_alive():
        return

    _listener_thread = threading.Thread(target=bot_listener_loop, daemon=True)
    _listener_thread.start()


def bootstrap_bot_listener():
    """Handle dev-server reloads and production workers."""
    if not BOT_LISTENER_ENABLED:
        return

    if app.debug:
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            start_bot_listener()
    else:
        start_bot_listener()


# -------------------------------------------------
# VIEW PDF AND VIDEO
# -------------------------------------------------
@app.route("/view_pdf/<path:filepath>")
def view_pdf(filepath):
    # Check if user has approved access
    if not session.get("approved"):
        return redirect(url_for("products_page"))
    
    # Ensure the filepath is safe and exists
    # Replace any directory traversal attempts
    safe_path = filepath.replace("..", "").replace("\\", "/").lstrip("/")
    
    # Construct full path
    full_path = os.path.join(UPLOAD_FOLDER, safe_path)
    
    # Verify file exists
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        # Try searching in subdirectories if just filename provided
        found = False
        for root, _, files in os.walk(UPLOAD_FOLDER):
            if os.path.basename(safe_path) in files:
                safe_path = os.path.relpath(os.path.join(root, os.path.basename(safe_path)), UPLOAD_FOLDER).replace("\\", "/")
                found = True
                break
        
        if not found:
            return "File not found. Please check your spelling and try again.", 404
    
    # Pass the relative path to template
    return render_template("view_pdf.html", filename=safe_path)

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
bootstrap_bot_listener()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

