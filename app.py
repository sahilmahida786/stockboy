from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import requests, json, os, threading, time, re
import mysql.connector
from datetime import timedelta, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

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
    allowed_routes = ["maintenance", "admin_login"]  # admin allowed

    if MAINTENANCE_MODE:
        # allow access ONLY to /maintenance and /admin-login
        if request.endpoint not in allowed_routes:
            return redirect("/maintenance")

@app.before_request
def allow_register_api():
    """Allow POST requests to /register without authentication"""
    if request.path == "/register" and request.method == "POST":
        return None

@app.before_request
def require_login():
    """Require login for all pages except login, register, static files, and admin"""
    # Skip for static files
    if request.endpoint == "static":
        return None
    
    # Pages that don't require login (public routes - only login/register and admin)
    public_routes = ["home", "auth_page", "login", "login_user", "register", "register_user", "admin_login", "maintenance", "telegram_update"]
    
    # Skip authentication check for public routes
    if request.endpoint in public_routes:
        return None
    
    # Check if user is logged in for all other pages
    if not (session.get("logged_in") or session.get("user_id")):
        return redirect(url_for("home"))

@app.errorhandler(500)
def handle_500_error(error):
    """Handle 500 errors and return JSON for API routes"""
    # For login/register routes, always return JSON
    if request.path in ["/login", "/register"]:
        import traceback
        error_msg = str(error) if hasattr(error, '__str__') else "Internal server error"
        print(f"500 Error in {request.path}: {error_msg}")
        traceback.print_exc()
        response = jsonify({"error": "Server error. Please try again."})
        response.status_code = 500
        return response
    # For other requests, return default Flask error handling
    return error, 500

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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")  # Persistent file storage for users
UPLOAD_FOLDER = "static/uploads"  # For course materials (PDFs, videos)
PAYMENT_SS_FOLDER = "payment_ss"   # For payment screenshots only

# Initialize users.json file
def init_json_storage():
    """Initialize JSON file storage for users."""
    try:
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, "w") as f:
                f.write("[]")
            print("⚠️ users.json created fresh on startup")
        print("✅ JSON file storage ready - using users.json")
    except Exception as e:
        print(f"⚠️ Error initializing users.json: {e}")

def load_users_json():
    """Load users from JSON file."""
    try:
        if not os.path.exists(USERS_FILE):
            return []
        with open(USERS_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"⚠️ Error loading users.json: {e}")
        return []

def save_users_json(users):
    """Save users to JSON file."""
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)
        print(f"✅ Saved {len(users)} users to users.json")
    except Exception as e:
        print(f"❌ Error saving users.json: {e}")
        raise

# Initialize storage on startup
init_json_storage()

# Firebase Configuration
try:
    import firebase_admin
    from firebase_admin import credentials, auth
    FIREBASE_AVAILABLE = True
except ImportError:
    print("⚠️ firebase-admin not installed - install with: pip install firebase-admin")
    FIREBASE_AVAILABLE = False
    firebase_admin = None
    auth = None

# Initialize Firebase Admin SDK
if FIREBASE_AVAILABLE:
    import glob
    FIREBASE_CREDENTIALS_PATH = None
    
    # First, try environment variable
    env_path = os.getenv("FIREBASE_CREDENTIALS")
    if env_path:
        # Check if it's a JSON string
        if env_path.strip().startswith("{"):
            FIREBASE_CREDENTIALS_PATH = env_path
        # Check if it's a valid file path
        elif os.path.exists(env_path):
            FIREBASE_CREDENTIALS_PATH = env_path
            print(f"📄 Using FIREBASE_CREDENTIALS from environment variable")
    
    # If env var didn't work, auto-detect from current directory
    if not FIREBASE_CREDENTIALS_PATH:
        firebase_files = glob.glob(os.path.join(BASE_DIR, "*-firebase-adminsdk-*.json"))
        if firebase_files:
            FIREBASE_CREDENTIALS_PATH = firebase_files[0]
            print(f"📁 Auto-detected Firebase credentials: {os.path.basename(FIREBASE_CREDENTIALS_PATH)}")
    
    if FIREBASE_CREDENTIALS_PATH:
        try:
            # Check if it's a file path
            if os.path.exists(FIREBASE_CREDENTIALS_PATH):
                cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
                print(f"✅ Loading Firebase credentials from file: {os.path.basename(FIREBASE_CREDENTIALS_PATH)}")
            # Check if it's a JSON string
            elif FIREBASE_CREDENTIALS_PATH.strip().startswith("{"):
                cred_dict = json.loads(FIREBASE_CREDENTIALS_PATH)
                cred = credentials.Certificate(cred_dict)
                print("✅ Loading Firebase credentials from JSON string")
            else:
                raise ValueError(f"Invalid FIREBASE_CREDENTIALS: not a file path or JSON string")
            
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin SDK initialized successfully")
        except Exception as e:
            print(f"⚠️ Firebase initialization error: {e}")
            print("   Continuing without Firebase - using fallback authentication")
            FIREBASE_AVAILABLE = False
    else:
        print("⚠️ FIREBASE_CREDENTIALS not set and no Firebase credentials file found")
        print("   Place a Firebase service account JSON file in the project directory")
        print("   Continuing without Firebase - using fallback authentication")
        FIREBASE_AVAILABLE = False

# Telegram Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else None

# Print bot status on startup
if BOT_TOKEN:
    print(f"✅ Telegram Bot Token configured (length: {len(BOT_TOKEN)})")
    if CHAT_ID:
        print(f"✅ Telegram Chat ID configured: {CHAT_ID}")
    else:
        print("⚠️ Telegram Chat ID not set - payment notifications will not be sent")
        print("   Set CHAT_ID environment variable to receive notifications")
else:
    print("⚠️ Telegram Bot Token not set - payment notifications disabled")

# Telegram Bot Functions
def send_telegram_photo(photo_path, caption, txn_id=None):
    """Send photo to Telegram with inline approve/reject buttons."""
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not set - cannot send notification")
        return False
    
    if not CHAT_ID:
        print("❌ CHAT_ID not set - cannot send notification")
        print("   Please set CHAT_ID in start_server.bat or environment variable")
        return False
    
    if not os.path.exists(photo_path):
        print(f"❌ Screenshot file not found: {photo_path}")
        return False
    
    url = f"{API_URL}/sendPhoto"
    
    try:
        print(f"📤 Sending to Telegram...")
        print(f"   URL: {url}")
        print(f"   Chat ID: {CHAT_ID}")
        print(f"   Photo: {photo_path}")
        
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
            
            response = requests.post(url, files=files, data=data, timeout=10)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("ok"):
                print(f"✅ Telegram notification sent successfully for Txn ID: {txn_id}")
                return True
            else:
                error_msg = response_data.get("description", response.text)
                print(f"❌ Telegram API error: {error_msg}")
                print(f"   Full response: {response_data}")
                return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error sending Telegram notification: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error sending Telegram notification: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_telegram_message(chat_id, text, parse_mode="Markdown"):
    """Send a text message to Telegram."""
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not set - cannot send message")
        return False
    
    url = f"{API_URL}/sendMessage"
    try:
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }, timeout=10)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get("ok"):
            print(f"✅ Telegram message sent successfully to chat {chat_id}")
            return True
        else:
            error_msg = response_data.get("description", response.text)
            print(f"❌ Telegram API error: {error_msg}")
            return False
    except Exception as e:
        print(f"❌ Error sending Telegram message: {e}")
        return False

def handle_telegram_message(payload):
    """Handle incoming Telegram messages from users."""
    if not payload or "message" not in payload:
        return False
    
    try:
        message = payload["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        username = message["from"].get("username", "Unknown")
        first_name = message["from"].get("first_name", "User")
        text = message.get("text", "").strip()
        
        print(f"📨 Received message from {first_name} (@{username}): {text}")
        
        # Handle /start command
        if text == "/start" or text.lower().startswith("/start"):
            welcome_message = (
                f"👋 *Welcome to Stockboy Bot!*\n\n"
                f"Hello {first_name}! 👋\n\n"
                f"I'm here to help you with:\n"
                f"• Payment notifications\n"
                f"• Course access updates\n"
                f"• Support inquiries\n\n"
                f"Send /help to see available commands."
            )
            send_telegram_message(chat_id, welcome_message)
            return True
        
        # Handle /help command
        elif text == "/help" or text.lower().startswith("/help"):
            help_message = (
                f"📚 *Stockboy Bot Commands*\n\n"
                f"/start - Start the bot\n"
                f"/help - Show this help message\n"
                f"/status - Check your payment status\n\n"
                f"💡 *Need Support?*\n"
                f"Visit our website or contact support for assistance."
            )
            send_telegram_message(chat_id, help_message)
            return True
        
        # Handle /status command
        elif text == "/status" or text.lower().startswith("/status"):
            # Try to find user's payment status
            payments = load_data()
            user_payments = []
            for entry in payments:
                # Match by username or try to find by other identifiers
                if entry.get("user") == first_name or entry.get("user") == username:
                    user_payments.append(entry)
            
            if user_payments:
                status_message = f"📊 *Your Payment Status*\n\n"
                for payment in user_payments[-5:]:  # Show last 5 payments
                    status_emoji = "✅" if payment["status"] == "approved" else "⏳" if payment["status"] == "pending" else "❌"
                    status_message += (
                        f"{status_emoji} *{payment.get('course_name', 'Course')}*\n"
                        f"Txn ID: `{payment['txn_id']}`\n"
                        f"Status: {payment['status'].title()}\n"
                        f"Amount: {payment.get('amount', 'N/A')}\n\n"
                    )
                send_telegram_message(chat_id, status_message)
            else:
                send_telegram_message(chat_id, "📭 No payment records found. Submit a payment on our website to get started!")
            return True
        
        # Handle general greetings
        elif text.lower() in ["hello", "hi", "hey", "hey there"]:
            greeting_message = (
                f"Hello {first_name}! 👋\n\n"
                f"How can I help you today? Send /help to see available commands."
            )
            send_telegram_message(chat_id, greeting_message)
            return True
        
        # Handle unknown messages
        else:
            response_message = (
                f"Hi {first_name}! 👋\n\n"
                f"I received your message: \"{text}\"\n\n"
                f"Send /help to see what I can do for you!"
            )
            send_telegram_message(chat_id, response_message)
            return True
            
    except Exception as exc:
        print(f"❌ Telegram message handling error: {exc}")
        import traceback
        traceback.print_exc()
        return False

def handle_telegram_callback(payload):
    """Handle Telegram callback queries for approve/reject."""
    if not payload or "callback_query" not in payload:
        return False

    try:
        cb = payload["callback_query"]
        action = cb["data"]
        callback_id = cb["id"]
        message_id = cb["message"]["message_id"]
        chat_id = cb["message"]["chat"]["id"]

        # Answer callback query
        answer_url = f"{API_URL}/answerCallbackQuery"
        requests.post(answer_url, json={"callback_query_id": callback_id})

        payments = load_data()
        processed = False

        if action.startswith("approve_"):
            txn_id = action.replace("approve_", "")
            print(f"✅ Approval request for Txn ID: {txn_id}")
            for i, entry in enumerate(payments):
                if entry["txn_id"] == txn_id and entry["status"] == "pending":
                    payments[i]["status"] = "approved"
                    save_data(payments)
                    print(f"✅ Payment approved: {txn_id} for user: {entry['user']}")

                    # Update Telegram message
                    edit_url = f"{API_URL}/editMessageCaption"
                    new_caption = (
                        f"✅ *Payment Approved*\n\n"
                        f"👤 *User:* {entry['user']}\n"
                        f"💳 *Txn ID:* `{txn_id}`\n"
                        f"📦 *Course:* {entry.get('course_name', 'N/A')}\n"
                        f"💰 *Amount:* {entry.get('amount', 'N/A')}\n"
                        f"🔓 *Status:* Access Granted"
                    )
                    requests.post(edit_url, json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "caption": new_caption,
                        "parse_mode": "Markdown"
                    })
                    processed = True
                    break

        elif action.startswith("reject_"):
            txn_id = action.replace("reject_", "")
            print(f"❌ Rejection request for Txn ID: {txn_id}")
            for i, entry in enumerate(payments):
                if entry["txn_id"] == txn_id and entry["status"] == "pending":
                    payments[i]["status"] = "rejected"
                    save_data(payments)
                    print(f"❌ Payment rejected: {txn_id} for user: {entry['user']}")

                    # Update Telegram message
                    edit_url = f"{API_URL}/editMessageCaption"
                    new_caption = (
                        f"❌ *Payment Rejected*\n\n"
                        f"👤 *User:* {entry['user']}\n"
                        f"💳 *Txn ID:* `{txn_id}`\n"
                        f"📦 *Course:* {entry.get('course_name', 'N/A')}\n"
                        f"💰 *Amount:* {entry.get('amount', 'N/A')}\n"
                        f"🚫 *Status:* Access Denied"
                    )
                    requests.post(edit_url, json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "caption": new_caption,
                        "parse_mode": "Markdown"
                    })
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
        print(f"❌ Telegram callback error: {exc}")
        return False

@app.route("/telegram-update", methods=["POST"])
def telegram_update():
    """Handle Telegram webhook updates (both messages and callbacks)."""
    data = request.get_json()
    if not data:
        return "OK", 200
    
    print(f"📥 Received Telegram update: {json.dumps(data, indent=2)}")
    
    # Handle callback queries (approve/reject buttons)
    if "callback_query" in data:
        handle_telegram_callback(data)
    # Handle regular messages
    elif "message" in data:
        handle_telegram_message(data)
    
    return "OK", 200

# Firebase token verification decorator
def firebase_required(f):
    """Decorator to verify Firebase ID token from Authorization header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not FIREBASE_AVAILABLE or not auth:
            return jsonify({"error": "Firebase authentication not configured"}), 500
        
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Missing authorization token"}), 401
        
        # Extract token from "Bearer <token>" format
        try:
            token = auth_header.split("Bearer ")[-1] if "Bearer " in auth_header else auth_header
            decoded_token = auth.verify_id_token(token)
            request.firebase_uid = decoded_token["uid"]
            request.firebase_email = decoded_token.get("email", "")
            request.firebase_name = decoded_token.get("name", "")
        except Exception as e:
            print(f"❌ Token verification error: {e}")
            return jsonify({"error": "Invalid or expired token"}), 401
        
        return f(*args, **kwargs)
    return decorated

# MySQL Configuration - Force disabled (using JSON storage)
# To use MySQL, set environment variables:
# USE_MYSQL=true (optional, will auto-detect if MySQL credentials are provided)
# MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
USE_MYSQL_ENV = "false"  # Force disable MySQL - always use JSON storage
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
# FOLDER CHECK
# -------------------------------------------------
def ensure_folders():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

ensure_folders()


# -------------------------------------------------
# DATABASE HELPERS (MySQL + JSON Fallback)
# -------------------------------------------------
_db_available = False  # Force disabled - always use JSON storage

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
        # Test if we can actually query the database (checks if database exists)
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            _db_available = True
            print("✅ MySQL database connection successful - using MySQL for user storage")
            conn.close()
            return True
        except mysql.connector.Error as db_error:
            conn.close()
            print(f"⚠️ MySQL database not accessible: {db_error} - using JSON storage")
            _db_available = False
            return False
    except mysql.connector.Error as e:
        error_msg = str(e).lower()
        # Handle common MySQL connection errors
        if "unknown database" in error_msg or "1049" in str(e.args[0] if e.args else ""):
            print(f"⚠️ MySQL database '{MYSQL_CONFIG.get('database')}' does not exist - using JSON storage")
        elif "access denied" in error_msg or "1045" in str(e.args[0] if e.args else ""):
            print(f"⚠️ MySQL access denied - check credentials - using JSON storage")
        else:
            print(f"⚠️ MySQL connection failed: {e} - using JSON storage")
        _db_available = False
        return False
    except Exception as e:
        print(f"⚠️ MySQL connection failed: {e} - using JSON storage")
        _db_available = False
        return False


def get_db_connection():
    """Create a new MySQL connection using env config."""
    global _db_available
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")
        # Reset cache on connection failure so we can retry or fallback
        _db_available = None
        raise


def init_database():
    """Initialize database - Try MySQL first if credentials available, otherwise JSON."""
    global _db_available
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
            error_msg = str(e).lower()
            if "unknown database" in error_msg or "1049" in str(e.args[0] if e.args else ""):
                print(f"❌ MySQL database '{MYSQL_CONFIG.get('database')}' does not exist")
            elif "access denied" in error_msg or "1045" in str(e.args[0] if e.args else ""):
                print(f"❌ MySQL access denied - check credentials")
            else:
                print(f"❌ MySQL initialization failed: {e}")
            print(f"   Falling back to JSON file storage (users.json)")
            # Reset cache so we don't try MySQL again
            _db_available = False
            init_json_storage()
        except Exception as e:
            print(f"❌ Unexpected error during MySQL initialization: {e}")
            print(f"   Falling back to JSON file storage (users.json)")
            _db_available = False
            init_json_storage()
        finally:
            if conn and conn.is_connected():
                conn.close()
    else:
        # No MySQL credentials or MySQL disabled - use JSON file storage
        init_json_storage()


# User storage functions are defined above (load_users_json, save_users_json)


# Initialize storage on startup
try:
    init_database()
except Exception as e:
    print(f"⚠️ Storage initialization error: {e}")
    import traceback
    traceback.print_exc()
    # Ensure JSON storage is initialized as fallback
    try:
        init_json_storage()
    except Exception as json_err:
        print(f"⚠️ JSON storage initialization also failed: {json_err}")


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
    username = session.get("username", "User")
    mobile = session.get("mobile", "")
    email = session.get("email", "")
    return render_template("products.html", products=get_product_catalog(), username=username, mobile=mobile, email=email, logged_in=True)

@app.route("/product/<product_slug>")
def product_detail(product_slug):
    """Individual product page with download options - requires payment approval"""
    if not (session.get("logged_in") or session.get("user_id")):
        return redirect(url_for("home"))
    
    if product_slug not in PRODUCT_DETAILS:
        return "Product not found", 404
    
    product_info = PRODUCT_DETAILS[product_slug]
    username = session.get("username", "User")
    email = session.get("email", "")
    user_id = session.get("user_id") or session.get("email", "")
    
    # Check payment approval status for this product
    payments = load_data()
    payment_status = "not_submitted"  # not_submitted, pending, approved, rejected
    payment_entry = None
    
    # Check if user has approved access for this product (from session)
    approved_products = session.get("approved_products", [])
    if product_slug in approved_products:
        payment_status = "approved"
    else:
        # Find payment for this user and product
        for entry in payments:
            if (entry.get("user") == username or entry.get("user_email") == email) and entry.get("product_slug") == product_slug:
                payment_entry = entry
                payment_status = entry.get("status", "pending")
                # If approved, add to session
                if payment_status == "approved" and product_slug not in approved_products:
                    if "approved_products" not in session:
                        session["approved_products"] = []
                    session["approved_products"].append(product_slug)
                break
    
    # Get files for this product (only if approved)
    product_folder = os.path.join(UPLOAD_FOLDER, product_slug)
    files = []
    if payment_status == "approved":
        if os.path.isdir(product_folder):
            for filename in os.listdir(product_folder):
                ext = filename.rsplit(".", 1)[-1].lower()
                if ext in COURSE_EXTENSIONS:
                    file_path = os.path.join(product_folder, filename)
                    file_size = os.path.getsize(file_path)
                    # Format file size
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    else:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    
                    files.append({
                        "name": filename,
                        "url": f"/static/uploads/{product_slug}/{filename}",
                        "download_url": f"/download/{product_slug}/{filename}",
                        "type": COURSE_EXTENSIONS.get(ext, "File"),
                        "size": size_str
                    })
    
    return render_template("product_detail.html", 
                         product_slug=product_slug,
                         product=product_info,
                         files=files,
                         username=username,
                         email=email,
                         payment_status=payment_status,
                         payment_entry=payment_entry,
                         logged_in=True)

@app.route("/about")
def about_page():
    """About page - requires login"""
    # Authentication is handled by before_request
    if not (session.get("logged_in") or session.get("user_id")):
        return redirect(url_for("home"))
    username = session.get("username", "User")
    mobile = session.get("mobile", "")
    return render_template("about.html", username=username, mobile=mobile, logged_in=True)

@app.route("/payment")
def payment_page():
    """Payment page - requires login"""
    # Authentication is handled by before_request
    if not (session.get("logged_in") or session.get("user_id")):
        return redirect(url_for("home"))
    username = session.get("username", "User")
    mobile = session.get("mobile", "")
    return render_template("index.html", username=username, mobile=mobile, logged_in=True)

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

from werkzeug.utils import secure_filename

# Ensure payment screenshot folder exists
if not os.path.exists(PAYMENT_SS_FOLDER):
    os.makedirs(PAYMENT_SS_FOLDER)

@app.route("/submit_payment", methods=["POST"])
def submit_payment():
    try:
        print(f"💳 Payment submission request received")
        user_name = request.form.get("user_name")
        txn_id = request.form.get("txn_id")
        product_slug = request.form.get("product_slug", "product1")  # Default to product1
        screenshot = request.files.get("screenshot")
        
        print(f"💳 Received - Name: {user_name}, Txn ID: {txn_id}, Product: {product_slug}, Screenshot: {screenshot.filename if screenshot else 'None'}")

        if not user_name or not txn_id:
            print(f"❌ Missing fields - Name: {bool(user_name)}, Txn ID: {bool(txn_id)}")
            return jsonify({"message": "⚠️ Please enter name and transaction ID."}), 400

        if not screenshot:
            print(f"❌ No screenshot file uploaded")
            return jsonify({"message": "⚠️ Please upload payment screenshot."}), 400

        # Get product info
        product_info = PRODUCT_DETAILS.get(product_slug, PRODUCT_DETAILS["product1"])
        course_name = product_info.get("title", "Unknown Course")
        amount = product_info.get("price", "₹0")

        # Load old data
        try:
            data = load_data()
            print(f"✅ Loaded {len(data)} existing payment entries")
        except Exception as e:
            print(f"❌ Error loading payment data: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"message": "❌ Error loading payment data. Please try again."}), 500

        # 🔥 STOP MULTIPLE SUBMISSIONS (IMPORTANT)
        for entry in data:
            if entry["txn_id"] == txn_id:
                print(f"⚠️ Duplicate transaction ID: {txn_id}")
                return jsonify({"message": "⚠️ This payment is already submitted!"})

        # Ensure payment_ss folder exists
        try:
            if not os.path.exists(PAYMENT_SS_FOLDER):
                os.makedirs(PAYMENT_SS_FOLDER)
                print(f"✅ Created payment_ss folder: {PAYMENT_SS_FOLDER}")
        except Exception as e:
            print(f"❌ Error creating payment_ss folder: {e}")
            import traceback
            traceback.print_exc()

        # Save screenshot to payment_ss folder (NOT in course uploads)
        try:
            filename = secure_filename(f"{txn_id}.png")
            filepath = os.path.join(PAYMENT_SS_FOLDER, filename)
            screenshot.save(filepath)
            print(f"✅ Screenshot saved: {filepath}")
        except Exception as e:
            print(f"❌ Error saving screenshot: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"message": "❌ Error saving screenshot. Please try again."}), 500

        # Save new data with product info
        try:
            payment_entry = {
                "user": user_name,
                "txn_id": txn_id,
                "status": "pending",
                "ss_path": filepath,
                "product_slug": product_slug,
                "course_name": course_name,
                "amount": amount,
                "user_email": session.get("email", ""),
                "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            data.append(payment_entry)
            save_data(data)
            print(f"✅ Payment data saved - Total entries: {len(data)}")
        except Exception as e:
            print(f"❌ Error saving payment data: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"message": "❌ Error saving payment data. Please try again."}), 500

        # Send Telegram notification with product info
        print(f"📱 Attempting to send Telegram notification...")
        print(f"   BOT_TOKEN: {'Set' if BOT_TOKEN else 'NOT SET'}")
        print(f"   CHAT_ID: {'Set' if CHAT_ID else 'NOT SET'}")
        print(f"   File path: {filepath}")
        print(f"   File exists: {os.path.exists(filepath)}")
        
        try:
            caption = (
                f"📩 *New Payment Request*\n\n"
                f"👤 *User:* {user_name}\n"
                f"💳 *Txn ID:* `{txn_id}`\n"
                f"📦 *Course:* {course_name}\n"
                f"💰 *Amount:* {amount}\n"
                f"⏳ *Status:* Pending Approval"
            )
            send_telegram_photo(filepath, caption, txn_id=txn_id)
            print(f"✅ Telegram notification sent successfully")
        except Exception as e:
            print(f"❌ ERROR: Telegram notification failed: {e}")
            import traceback
            traceback.print_exc()
            print(f"⚠️ Payment still saved - notification can be sent manually from admin panel")

        # Payment saved successfully
        print(f"✅ Payment submission completed for {user_name} with Txn ID: {txn_id}")

        return jsonify({"message": "✅ Payment Submitted! Wait for approval."})
    except Exception as e:
        print(f"❌ Payment submission error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": "❌ Error submitting payment. Please try again."}), 500


@app.route("/check_approval", methods=["POST"])
def check_approval():
    txn_id = request.form.get("txn_id")
    product_slug = request.form.get("product_slug", "")
    print(f"🔍 Checking approval status for Txn ID: {txn_id}, Product: {product_slug}")

    data = load_data()
    for x in data:
        if x["txn_id"] == txn_id:
            status = x["status"]
            product = x.get("product_slug", "")
            print(f"📋 Found payment - Txn ID: {txn_id}, Status: {status}, Product: {product}")
            
            # If approved, add to session
            if status == "approved" and product:
                if "approved_products" not in session:
                    session["approved_products"] = []
                if product not in session["approved_products"]:
                    session["approved_products"].append(product)
            
            return jsonify({
                "status": status,
                "product_slug": product
            })

    print(f"⚠️ Payment not found for Txn ID: {txn_id}")
    return jsonify({"status": "not_found"})


@app.route("/start_session", methods=["POST"])
def start_session():
    txn_id = request.form.get("txn_id")
    user_name = request.form.get("user_name", "User")
    product_slug = request.form.get("product_slug", "")
    print(f"🚀 Starting session for Txn ID: {txn_id}, User: {user_name}, Product: {product_slug}")

    data = load_data()
    payment_entry = None
    for x in data:
        if x["txn_id"] == txn_id:
            payment_entry = x
            break
    
    if not payment_entry:
        print(f"❌ Payment not found for Txn ID: {txn_id}")
        return jsonify({"ok": False, "error": "Payment not found"})
    
    if payment_entry["status"] != "approved":
        print(f"❌ Payment not approved yet for Txn ID: {txn_id}, Status: {payment_entry['status']}")
        return jsonify({"ok": False, "error": f"Payment {payment_entry['status']}"})

    # Store approved products in session
    if "approved_products" not in session:
        session["approved_products"] = []
    
    product_slug = payment_entry.get("product_slug", product_slug)
    if product_slug and product_slug not in session["approved_products"]:
        session["approved_products"].append(product_slug)
    
    session["approved"] = True
    session["user_name"] = user_name
    print(f"✅ Session started - User: {user_name}, Approved: True, Product: {product_slug}")
    
    # Redirect to product page if product specified, otherwise dashboard
    if product_slug:
        return jsonify({"ok": True, "redirect": url_for("product_detail", product_slug=product_slug)})
    else:
        return jsonify({"ok": True, "redirect": url_for("dashboard")})


# -------------------------------------------------
# USER REGISTRATION & LOGIN (Firebase Authentication)
# -------------------------------------------------
@app.route("/register", methods=["POST"])
def register_user():
    try:
        print(f"📝 Registration request received - Method: {request.method}, Path: {request.path}")
        
        # Get token from Authorization header first (preferred), then from body
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split("Bearer ")[-1] if "Bearer " in auth_header else auth_header
        else:
            payload = request.get_json(silent=True) or request.form
            token = payload.get("idToken") or payload.get("token")
        
        if not token:
            response = jsonify({"error": "Missing Firebase ID token"})
            response.headers["Content-Type"] = "application/json"
            return response, 400

        # Verify Firebase ID token
        if FIREBASE_AVAILABLE and auth:
            try:
                decoded_token = auth.verify_id_token(token)
                uid = decoded_token['uid']
                email = decoded_token.get('email', '')
                name = decoded_token.get('name', email.split('@')[0] if email else 'User')
                
                # Store user info in session
                session["user_id"] = uid
                session["username"] = name
                session["email"] = email
                session["logged_in"] = True
                session["reg_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                print(f"✅ User registered successfully: {email} (UID: {uid})")
                response = jsonify({
                    "message": "Registration successful!",
                    "redirect": url_for("products_page"),
                    "registration_date": session["reg_date"]
                })
                response.headers["Content-Type"] = "application/json"
                return response, 201
            except Exception as e:
                print(f"❌ Firebase token verification error: {e}")
                response = jsonify({"error": "Invalid authentication token"})
                response.headers["Content-Type"] = "application/json"
                return response, 401
        else:
            response = jsonify({"error": "Firebase authentication not configured"})
            response.headers["Content-Type"] = "application/json"
            return response, 500
    except Exception as e:
        print(f"❌ Register route error: {e}")
        import traceback
        traceback.print_exc()
        response = jsonify({"error": "Registration failed. Please try again."})
        response.headers["Content-Type"] = "application/json"
        return response, 500



@app.route("/login", methods=["POST"])
def login_user():
    try:
        print(f"🔐 Login request received - Method: {request.method}, Path: {request.path}")
        
        # Get token from Authorization header or request body
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split("Bearer ")[-1] if "Bearer " in auth_header else auth_header
        else:
            payload = request.get_json(silent=True) or request.form
            token = payload.get("idToken") or payload.get("token")
        
        if not token:
            response = jsonify({"error": "Missing Firebase ID token"})
            response.headers["Content-Type"] = "application/json"
            return response, 400

        # Verify Firebase ID token
        if FIREBASE_AVAILABLE and auth:
            try:
                decoded_token = auth.verify_id_token(token)
                uid = decoded_token['uid']
                email = decoded_token.get('email', '')
                name = decoded_token.get('name', email.split('@')[0] if email else 'User')
                
                # Store user info in session
                session["user_id"] = uid
                session["username"] = name
                session["email"] = email
                session["logged_in"] = True
                
                # Try to get registration date from token (if available)
                if 'auth_time' in decoded_token:
                    reg_date = datetime.fromtimestamp(decoded_token['auth_time']).strftime("%Y-%m-%d %H:%M:%S")
                    session["reg_date"] = reg_date
                else:
                    session["reg_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                print(f"✅ User logged in successfully: {email} (UID: {uid})")
                response = jsonify({
                    "message": "Login successful!",
                    "redirect": url_for("products_page"),
                    "registration_date": session["reg_date"]
                })
                response.headers["Content-Type"] = "application/json"
                return response
            except Exception as e:
                print(f"❌ Firebase token verification error: {e}")
                response = jsonify({"error": "Invalid authentication token"})
                response.headers["Content-Type"] = "application/json"
                return response, 401
        else:
            response = jsonify({"error": "Firebase authentication not configured"})
            response.headers["Content-Type"] = "application/json"
            return response, 500
    except Exception as e:
        print(f"❌ Login route error: {e}")
        import traceback
        traceback.print_exc()
        response = jsonify({"error": "Login failed. Please try again."})
        response.headers["Content-Type"] = "application/json"
        return response, 500


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

    print(f"✅ Payment approved: {txn_id} for user: {user}")

    return redirect("/admin")


@app.route("/reject/<int:index>")
def reject(index):
    data = load_data()
    user = data[index]["user"]
    txn_id = data[index]["txn_id"]

    data[index]["status"] = "rejected"
    save_data(data)

    print(f"❌ Payment rejected: {txn_id} for user: {user}")

    return redirect("/admin")


# -------------------------------------------------
# FILE UPLOAD
# -------------------------------------------------
@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    """Upload files to specific product folders"""
    if not session.get("admin"):
        return redirect("/admin-login")
    
    if request.method == "POST":
        product_slug = request.form.get("product", "product1")
        f = request.files.get("file")
        
        if not f or f.filename == "":
            return redirect("/upload?error=No file selected")
        
        # Ensure product folder exists
        product_folder = os.path.join(UPLOAD_FOLDER, product_slug)
        if not os.path.exists(product_folder):
            os.makedirs(product_folder)
        
        # Save file to product folder
        filename = secure_filename(f.filename)
        filepath = os.path.join(product_folder, filename)
        f.save(filepath)
        
        return redirect(f"/upload?success=File uploaded to {PRODUCT_DETAILS.get(product_slug, {}).get('title', product_slug)}")

    # Get files from all products
    all_files = {}
    for product_slug in PRODUCT_DETAILS.keys():
        product_folder = os.path.join(UPLOAD_FOLDER, product_slug)
        if os.path.isdir(product_folder):
            all_files[product_slug] = os.listdir(product_folder)
        else:
            all_files[product_slug] = []
    
    return render_template("upload.html", files=all_files, products=PRODUCT_DETAILS)

@app.route("/download/<product_slug>/<filename>")
def download_file(product_slug, filename):
    """Download file from product folder"""
    if not (session.get("logged_in") or session.get("user_id")):
        return redirect(url_for("home"))
    
    # Security: prevent directory traversal
    filename = secure_filename(filename)
    if product_slug not in PRODUCT_DETAILS:
        return "Product not found", 404
    
    file_path = os.path.join(UPLOAD_FOLDER, product_slug, filename)
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return "File not found", 404
    
    return send_from_directory(
        os.path.join(UPLOAD_FOLDER, product_slug),
        filename,
        as_attachment=True
    )


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
# TELEGRAM POLLING (Alternative to Webhook)
# -------------------------------------------------
_last_update_id = 0

def poll_telegram_updates():
    """Poll Telegram API for updates (runs in background thread)."""
    global _last_update_id
    
    if not BOT_TOKEN:
        print("⚠️ BOT_TOKEN not set - skipping Telegram polling")
        return
    
    print("🔄 Starting Telegram polling...")
    
    while True:
        try:
            url = f"{API_URL}/getUpdates"
            params = {
                "offset": _last_update_id + 1,
                "timeout": 10,
                "allowed_updates": ["message", "callback_query"]
            }
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if data.get("ok") and data.get("result"):
                updates = data["result"]
                for update in updates:
                    update_id = update.get("update_id", 0)
                    _last_update_id = max(_last_update_id, update_id)
                    
                    # Process the update
                    if "callback_query" in update:
                        handle_telegram_callback(update)
                    elif "message" in update:
                        handle_telegram_message(update)
            
            time.sleep(1)  # Small delay between polls
            
        except requests.exceptions.Timeout:
            # Timeout is normal, continue polling
            continue
        except Exception as e:
            print(f"❌ Error in Telegram polling: {e}")
            time.sleep(5)  # Wait longer on error

def start_telegram_polling():
    """Start Telegram polling in a background thread."""
    if not BOT_TOKEN:
        return
    
    # Check if webhook is set (if webhook is set, don't poll)
    try:
        webhook_url = f"{API_URL}/getWebhookInfo"
        response = requests.get(webhook_url, timeout=5)
        webhook_info = response.json()
        
        if webhook_info.get("ok") and webhook_info.get("result", {}).get("url"):
            webhook_url_set = webhook_info["result"]["url"]
            print(f"✅ Webhook is set: {webhook_url_set}")
            print("   Using webhook mode - polling disabled")
            return
    except:
        pass
    
    # Start polling in background thread
    polling_thread = threading.Thread(target=poll_telegram_updates, daemon=True)
    polling_thread.start()
    print("✅ Telegram polling started in background thread")

# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------
if __name__ == "__main__":
    # Start Telegram polling if bot token is configured
    start_telegram_polling()
    
    # Get port from environment variable (Render requirement) or default to 5000
    port = int(os.getenv("PORT", 5000))
    # Disable debug mode in production (Render sets FLASK_ENV or similar)
    debug_mode = os.getenv("FLASK_ENV", "production").lower() != "production"
    
    app.run(host="0.0.0.0", port=port, debug=debug_mode)

