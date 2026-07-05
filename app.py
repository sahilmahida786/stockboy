import sys, io
# Fix Windows console encoding for emoji/unicode in print statements
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests, json, os, re
from datetime import timedelta, datetime, timezone
from functools import wraps


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.secret_key = os.getenv("SECRET_KEY", "change_this_secret_key")
app.permanent_session_lifetime = timedelta(days=7)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# -------------------------------------------------
# MAINTENANCE MODE
# -------------------------------------------------
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"

@app.before_request
def maintenance_blocker():
    allowed_routes = ["maintenance", "admin_login", "static"]
    if MAINTENANCE_MODE:
        if request.endpoint not in allowed_routes:
            return redirect("/maintenance")

@app.before_request
def allow_register_api():
    """Allow POST requests to /register without authentication"""
    if request.path == "/register" and request.method == "POST":
        return None

@app.before_request
def require_login():
    """Require login for all pages except public routes"""
    if request.endpoint == "static":
        return None

    public_routes = [
        "home", "auth_page", "login", "login_user", "register", "register_user",
        "admin_login", "maintenance", "privacy_policy", "terms", "refund", "contact",
        "create_payment_order", "verify_payment", "plans_page", "razorpay_webhook",
        "about_page", "products_page", "payment_page"
    ]

    # Admin routes — bypass user login check if admin session exists
    admin_routes = [
        "admin_panel", "admin_create_signal", "admin_edit_signal",
        "admin_delete_signal", "admin_update_signal_status",
        "admin_extend_subscription", "admin_revoke_subscription"
    ]

    if request.endpoint in public_routes:
        return None

    if request.endpoint in admin_routes and session.get("admin"):
        return None

    if not (session.get("logged_in") or session.get("user_id") or session.get("admin")):
        return redirect(url_for("home"))

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

@app.errorhandler(500)
def handle_500_error(error):
    if request.path in ["/login", "/register"]:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Server error. Please try again."}), 500
    return error, 500

@app.route("/maintenance")
def maintenance():
    return """
    <html>
    <head>
        <title>Maintenance</title>
        <style>
            body {
                background:#081821;
                color:white;
                text-align:center;
                padding-top:120px;
                font-family: 'Poppins', Arial, sans-serif;
            }
            h1 { font-size:40px; color:#FFD54A; }
            p { font-size:20px; color:#ccc; }
        </style>
    </head>
    <body>
        <h1>🚧 Website Under Maintenance</h1>
        <p>We'll be back soon with premium stock signals.</p>
    </body>
    </html>
    """

# -------------------------------------------------
# FIREBASE CONFIGURATION
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    import firebase_admin
    from firebase_admin import credentials, auth, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    print("⚠️ firebase-admin not installed — pip install firebase-admin")
    FIREBASE_AVAILABLE = False
    firebase_admin = None
    auth = None
    firestore = None

# Initialize Firebase Admin SDK
db = None  # Firestore client

if FIREBASE_AVAILABLE:
    import glob
    FIREBASE_CREDENTIALS_PATH = None

    env_path = os.getenv("FIREBASE_CREDENTIALS")
    if env_path:
        if env_path.strip().startswith("{"):
            FIREBASE_CREDENTIALS_PATH = env_path
        elif os.path.exists(env_path):
            FIREBASE_CREDENTIALS_PATH = env_path
            print(f"📄 Using FIREBASE_CREDENTIALS from environment variable")

    if not FIREBASE_CREDENTIALS_PATH:
        firebase_files = glob.glob(os.path.join(BASE_DIR, "*-firebase-adminsdk-*.json"))
        if firebase_files:
            FIREBASE_CREDENTIALS_PATH = firebase_files[0]
            print(f"📁 Auto-detected Firebase credentials: {os.path.basename(FIREBASE_CREDENTIALS_PATH)}")

    if FIREBASE_CREDENTIALS_PATH:
        try:
            if os.path.exists(FIREBASE_CREDENTIALS_PATH):
                cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
                print(f"✅ Loading Firebase credentials from file: {os.path.basename(FIREBASE_CREDENTIALS_PATH)}")
            elif FIREBASE_CREDENTIALS_PATH.strip().startswith("{"):
                cred_dict = json.loads(FIREBASE_CREDENTIALS_PATH)
                cred = credentials.Certificate(cred_dict)
                print("✅ Loading Firebase credentials from JSON string")
            else:
                raise ValueError("Invalid FIREBASE_CREDENTIALS")

            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("✅ Firebase Admin SDK + Firestore initialized successfully")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"⚠️ Firebase initialization error: {e}")
            FIREBASE_AVAILABLE = False
    else:
        print("⚠️ FIREBASE_CREDENTIALS not set — Firestore unavailable")
        FIREBASE_AVAILABLE = False

# -------------------------------------------------
# RAZORPAY CONFIGURATION
# -------------------------------------------------
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()

if not RAZORPAY_KEY_ID:
    print("⚠️ RAZORPAY_KEY_ID not set in environment")

if not RAZORPAY_KEY_SECRET:
    print("⚠️ RAZORPAY_KEY_SECRET not set in environment")

razorpay = None
razorpay_client = None
razorpay_init_error = None

try:
    import razorpay
    print("📦 Razorpay package imported successfully")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"❌ Razorpay import failed: {e}")
    razorpay = None
    razorpay_init_error = f"Razorpay package import failed: {str(e)}. Please ensure requirements.txt is up to date."

if razorpay:
    try:
        key_id = os.getenv("RAZORPAY_KEY_ID", "").strip() or RAZORPAY_KEY_ID
        key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip() or RAZORPAY_KEY_SECRET

        if not key_id or not key_secret:
            razorpay_init_error = "RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET is missing from environment variables"
            print(f"⚠️ {razorpay_init_error}")
            razorpay_client = None
        else:
            razorpay_client = razorpay.Client(auth=(key_id, key_secret))
            print("✅ Razorpay client initialized successfully")
    except Exception as e:
        import traceback
        traceback.print_exc()
        razorpay_init_error = str(e)
        print(f"❌ Razorpay client init failed: {e}")
        razorpay_client = None

# -------------------------------------------------
# MEMBERSHIP PLANS CONFIGURATION
# -------------------------------------------------
MEMBERSHIP_PLANS = {
    "monthly": {
        "name": "1 Month Membership",
        "slug": "monthly",
        "price": 999,
        "price_display": "₹999",
        "duration_days": 30,
        "badge": "STARTER",
        "popular": False,
    },
    "quarterly": {
        "name": "3 Month Membership",
        "slug": "quarterly",
        "price": 1999,
        "price_display": "₹1,999",
        "duration_days": 90,
        "badge": "POPULAR",
        "popular": True,
    },
    "yearly": {
        "name": "Yearly Membership",
        "slug": "yearly",
        "price": 3999,
        "price_display": "₹3,999",
        "duration_days": 365,
        "badge": "BEST VALUE",
        "popular": False,
    },
    "lifetime": {
        "name": "Lifetime Membership",
        "slug": "lifetime",
        "price": 9999,
        "price_display": "₹9,999",
        "duration_days": None,  # Never expires
        "badge": "ELITE",
        "popular": False,
    },
}

PLAN_BENEFITS = [
    "Premium Stock Signals",
    "Entry Price Alerts",
    "Target Updates",
    "Stop Loss Levels",
    "Market Opportunities",
    "Premium Dashboard Access",
    "Subscription Support",
]

# -------------------------------------------------
# INPUT SANITIZATION
# -------------------------------------------------
def sanitize_input(text):
    """Strip HTML tags and dangerous characters from user input."""
    if not isinstance(text, str):
        return text
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Remove script-related patterns
    clean = re.sub(r'(?i)(javascript|on\w+\s*=)', '', clean)
    return clean.strip()

# -------------------------------------------------
# FIRESTORE HELPERS
# -------------------------------------------------
def get_user_doc(uid):
    """Get user document from Firestore."""
    if not db:
        return None
    try:
        doc = db.collection("users").document(uid).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        print(f"⚠️ Error fetching user {uid}: {e}")
        return None

def create_or_update_user(uid, data):
    """Create or update user document in Firestore."""
    if not db:
        return False
    try:
        db.collection("users").document(uid).set(data, merge=True)
        return True
    except Exception as e:
        print(f"⚠️ Error saving user {uid}: {e}")
        return False

def check_subscription_active(uid):
    """Check if user has an active subscription."""
    user_doc = get_user_doc(uid)
    if not user_doc:
        return False

    status = user_doc.get("subscriptionStatus", "none")
    if status != "active":
        return False

    plan = user_doc.get("plan", "none")
    if plan == "lifetime":
        return True

    expiry = user_doc.get("subscriptionExpiry")
    if not expiry:
        return False

    # Handle Firestore timestamp
    if hasattr(expiry, 'timestamp'):
        expiry_dt = datetime.fromtimestamp(expiry.timestamp())
    elif isinstance(expiry, str):
        try:
            expiry_dt = datetime.fromisoformat(expiry.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            expiry_dt = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
    elif isinstance(expiry, datetime):
        expiry_dt = expiry
    else:
        return False

    if datetime.now() > expiry_dt:
        # Auto-expire subscription
        try:
            db.collection("users").document(uid).update({
                "subscriptionStatus": "expired",
                "updatedAt": datetime.now().isoformat()
            })
            # Also update the subscription document
            subs = db.collection("subscriptions").where("userId", "==", uid).where("status", "==", "active").limit(1).stream()
            for sub in subs:
                sub.reference.update({"status": "expired"})
            print(f"⏰ Subscription expired for user {uid}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"⚠️ Error auto-expiring subscription: {e}")
        return False

    return True

def activate_subscription(uid, plan_slug, payment_id, razorpay_order_id):
    """Activate a subscription for a user after successful payment."""
    if not db:
        return False

    plan = MEMBERSHIP_PLANS.get(plan_slug)
    if not plan:
        return False

    now = datetime.now()

    # Calculate expiry
    if plan["duration_days"] is None:
        expiry_date = None  # Lifetime — never expires
    else:
        expiry_date = now + timedelta(days=plan["duration_days"])

    # Update user document
    user_update = {
        "plan": plan_slug,
        "subscriptionStatus": "active",
        "subscriptionExpiry": expiry_date.isoformat() if expiry_date else "lifetime",
        "updatedAt": now.isoformat()
    }
    create_or_update_user(uid, user_update)

    # Create subscription document
    sub_data = {
        "userId": uid,
        "plan": plan_slug,
        "amount": plan["price"],
        "status": "active",
        "startDate": now.isoformat(),
        "expiryDate": expiry_date.isoformat() if expiry_date else "lifetime",
        "paymentId": payment_id,
        "razorpayOrderId": razorpay_order_id,
        "createdAt": now.isoformat()
    }
    db.collection("subscriptions").add(sub_data)

    print(f"✅ Subscription activated: {plan_slug} for user {uid}, expires: {expiry_date or 'NEVER'}")
    return True

def get_active_signals():
    """Get all active stock signals from Firestore, ordered by creation date."""
    if not db:
        return []
    try:
        signals = []
        docs = db.collection("stockSignals").order_by("createdAt", direction=firestore.Query.DESCENDING).stream()
        for doc in docs:
            signal = doc.to_dict()
            signal["id"] = doc.id
            signals.append(signal)
        return signals
    except Exception as e:
        print(f"⚠️ Error fetching signals: {e}")
        return []

def get_recent_notifications(uid):
    """Get recent notifications for a user and global ones."""
    if not db:
        return []
    try:
        docs = db.collection("notifications").where("userId", "in", ["global", uid]).order_by("createdAt", direction=firestore.Query.DESCENDING).limit(5).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        # If index is missing, fallback to getting all and filtering in memory for small datasets
        try:
            docs = db.collection("notifications").order_by("createdAt", direction=firestore.Query.DESCENDING).limit(20).stream()
            notifs = []
            for doc in docs:
                data = doc.to_dict()
                if data.get("userId") in ["global", uid]:
                    notifs.append(data)
                if len(notifs) >= 5:
                    break
            return notifs
        except Exception as fallback_e:
            print(f"⚠️ Error fetching notifications: {fallback_e}")
            return []

def get_all_subscribers():
    """Get all users who have or had a subscription."""
    if not db:
        return []
    try:
        users = []
        docs = db.collection("users").where("plan", "!=", "none").stream()
        for doc in docs:
            user = doc.to_dict()
            user["uid"] = doc.id
            users.append(user)
        return users
    except Exception as e:
        print(f"⚠️ Error fetching subscribers: {e}")
        return []

def get_all_payments():
    """Get all payment records from Firestore."""
    if not db:
        return []
    try:
        payments = []
        docs = db.collection("payments").order_by("createdAt", direction=firestore.Query.DESCENDING).limit(100).stream()
        for doc in docs:
            payment = doc.to_dict()
            payment["id"] = doc.id
            payments.append(payment)
        return payments
    except Exception as e:
        print(f"⚠️ Error fetching payments: {e}")
        return []

def log_admin_action(admin_id, action, target_id, details):
    """Log admin actions to Firestore."""
    if not db:
        return
    try:
        db.collection("adminLogs").add({
            "adminId": admin_id,
            "action": action,
            "targetId": target_id,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"⚠️ Error logging admin action: {e}")

def create_notification(user_id, message, notif_type="info"):
    """Create an in-app notification"""
    if not db:
        return
    try:
        db.collection("notifications").add({
            "userId": user_id,  # "global" for all users
            "message": message,
            "type": notif_type,
            "read": False,
            "createdAt": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"⚠️ Error creating notification: {e}")

# -------------------------------------------------
# AUTOMATION: SIGNAL EXPIRY
# -------------------------------------------------
def check_expired_signals():
    """Background task to automatically expire signals"""
    if not db:
        return
        
    try:
        from datetime import datetime, timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(ist)
        now_naive = datetime.now()
        
        active_signals = db.collection("stockSignals").where("status", "in", ["Active", "ACTIVE"]).stream()
        
        for doc in active_signals:
            signal = doc.to_dict()
            category = signal.get("category")
            
            if category == "Intraday":
                if now_ist.hour > 15 or (now_ist.hour == 15 and now_ist.minute >= 30):
                    db.collection("stockSignals").document(doc.id).update({
                        "status": "Expired",
                        "updatedAt": now_naive.isoformat()
                    })
                    print(f"⏰ Auto-expired Intraday signal: {signal.get('stockName')}")
    except Exception as e:
        print(f"⚠️ Error checking signal expirations: {e}")

def start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=check_expired_signals, trigger="interval", minutes=1)
        scheduler.start()
        print("✅ Background scheduler started")
    except Exception as e:
        print(f"⚠️ Failed to start scheduler: {e}")

# -------------------------------------------------
# FIREBASE TOKEN VERIFICATION
# -------------------------------------------------
def firebase_required(f):
    """Decorator to verify Firebase ID token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not FIREBASE_AVAILABLE or not auth:
            return jsonify({"error": "Firebase authentication not configured"}), 500

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Missing authorization token"}), 401

        try:
            token = auth_header.split("Bearer ")[-1] if "Bearer " in auth_header else auth_header
            decoded_token = auth.verify_id_token(token)
            request.firebase_uid = decoded_token["uid"]
            request.firebase_email = decoded_token.get("email", "")
            request.firebase_name = decoded_token.get("name", "")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"❌ Token verification error: {e}")
            return jsonify({"error": "Invalid or expired token"}), 401

        return f(*args, **kwargs)
    return decorated

# -------------------------------------------------
# PUBLIC ROUTES
# -------------------------------------------------
@app.route("/")
def home():
    """Homepage — Public landing page with membership plans"""
    logged_in = session.get("logged_in") or session.get("user_id")
    username = session.get("username", "")

    # Check subscription status if logged in
    has_subscription = False
    if logged_in and session.get("user_id"):
        has_subscription = check_subscription_active(session["user_id"])

    return render_template("index.html",
        plans=MEMBERSHIP_PLANS,
        benefits=PLAN_BENEFITS,
        logged_in=logged_in,
        username=username,
        has_subscription=has_subscription,
        razorpay_key_id=RAZORPAY_KEY_ID)

@app.route("/plans")
def plans_page():
    """Membership plans page — Public"""
    logged_in = session.get("logged_in") or session.get("user_id")
    username = session.get("username", "")
    return render_template("products.html",
        plans=MEMBERSHIP_PLANS,
        benefits=PLAN_BENEFITS,
        logged_in=logged_in,
        username=username,
        razorpay_key_id=RAZORPAY_KEY_ID)

@app.route("/auth")
def auth_page():
    """Auth page (login/register)"""
    if session.get("logged_in") or session.get("user_id"):
        uid = session.get("user_id")
        if uid and check_subscription_active(uid):
            return redirect(url_for("dashboard"))
        return redirect(url_for("plans_page"))
    return render_template("auth.html")

# -------------------------------------------------
# USER AUTHENTICATION (Firebase)
# -------------------------------------------------
@app.route("/register", methods=["POST"])
def register_user():
    try:
        print(f"📝 Registration request received")

        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split("Bearer ")[-1] if "Bearer " in auth_header else auth_header
        else:
            payload = request.get_json(silent=True) or request.form
            token = payload.get("idToken") or payload.get("token")

        if not token:
            return jsonify({"error": "Missing Firebase ID token"}), 400

        if FIREBASE_AVAILABLE and auth:
            try:
                decoded_token = auth.verify_id_token(token)
                uid = decoded_token['uid']
                email = decoded_token.get('email', '')
                name = decoded_token.get('name', email.split('@')[0] if email else 'User')

                # Create user document in Firestore
                create_or_update_user(uid, {
                    "uid": uid,
                    "name": name,
                    "email": email,
                    "phone": "",
                    "role": "user",
                    "plan": "none",
                    "subscriptionStatus": "none",
                    "subscriptionExpiry": None,
                    "createdAt": datetime.now().isoformat(),
                    "updatedAt": datetime.now().isoformat()
                })

                # Store user info in session
                session["user_id"] = uid
                session["username"] = name
                session["email"] = email
                session["logged_in"] = True

                print(f"✅ User registered: {email} (UID: {uid})")
                return jsonify({
                    "message": "Registration successful!",
                    "redirect": url_for("plans_page")
                }), 201
            except Exception as e:
                print(f"❌ Firebase token verification error: {e}")
                return jsonify({"error": "Invalid authentication token"}), 401
        else:
            return jsonify({"error": "Firebase authentication not configured"}), 500
    except Exception as e:
        print(f"❌ Register route error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Registration failed. Please try again."}), 500


@app.route("/login", methods=["POST"])
def login_user():
    try:
        print(f"🔐 Login request received")

        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split("Bearer ")[-1] if "Bearer " in auth_header else auth_header
        else:
            payload = request.get_json(silent=True) or request.form
            token = payload.get("idToken") or payload.get("token")

        if not token:
            return jsonify({"error": "Missing Firebase ID token"}), 400

        if FIREBASE_AVAILABLE and auth:
            try:
                decoded_token = auth.verify_id_token(token)
                uid = decoded_token['uid']
                email = decoded_token.get('email', '')
                name = decoded_token.get('name', email.split('@')[0] if email else 'User')

                # Ensure user document exists in Firestore
                user_doc = get_user_doc(uid)
                if not user_doc:
                    create_or_update_user(uid, {
                        "uid": uid,
                        "name": name,
                        "email": email,
                        "phone": "",
                        "role": "user",
                        "plan": "none",
                        "subscriptionStatus": "none",
                        "subscriptionExpiry": None,
                        "createdAt": datetime.now().isoformat(),
                        "updatedAt": datetime.now().isoformat()
                    })

                # Store user info in session
                session["user_id"] = uid
                session["username"] = name
                session["email"] = email
                session["logged_in"] = True

                # Check subscription and redirect accordingly
                has_sub = check_subscription_active(uid)
                redirect_url = url_for("dashboard") if has_sub else url_for("plans_page")

                print(f"✅ User logged in: {email} (UID: {uid}), subscription: {has_sub}")
                return jsonify({
                    "message": "Login successful!",
                    "redirect": redirect_url
                })
            except Exception as e:
                print(f"❌ Firebase token verification error: {e}")
                return jsonify({"error": "Invalid authentication token"}), 401
        else:
            return jsonify({"error": "Firebase authentication not configured"}), 500
    except Exception as e:
        print(f"❌ Login route error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Login failed. Please try again."}), 500


@app.route("/logout")
def logout():
    """Clear user session and logout"""
    session.clear()
    return redirect(url_for("home"))

# -------------------------------------------------
# USER DASHBOARD
# -------------------------------------------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login_user"))
    
    uid = session["user"]
    user = get_user_doc(uid)
    if not user:
        session.pop("user", None)
        return redirect(url_for("login_user"))
        
    plan = user.get("plan", "none")
    if plan == "none":
        return redirect(url_for("plans_page"))
        
    if not check_subscription_active(user):
        return redirect(url_for("plans_page"))
        
    all_signals = get_active_signals()
    active_signals = [s for s in all_signals if s.get("status") not in ["Expired", "EXPIRED", "Closed", "CLOSED", "Cancelled", "CANCELLED"]]
    
    from datetime import datetime, timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    today_str = now_ist.date().isoformat()
    
    intraday_signals = []
    fno_signals = []
    
    for s in active_signals:
        cat = s.get("category", "")
        if cat == "Intraday":
            created = s.get("createdAt", "")
            if created:
                try:
                    sig_date = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=None).date().isoformat()
                    if sig_date == today_str:
                        intraday_signals.append(s)
                except:
                    pass
        elif cat == "F&O":
            fno_signals.append(s)
            
    intraday_signals = intraday_signals[:5]
    fno_signals = fno_signals[:3]
    
    closed_signals = [s for s in all_signals if s.get("status") in ["Expired", "EXPIRED", "Closed", "CLOSED", "Target Hit", "TARGET HIT"]]
    
    notifications = get_recent_notifications(uid)
    
    return render_template("dashboard.html", 
                          user=user, 
                          name=user.get("name", "Trader"),
                          plan=plan,
                          expiry=user.get("subscriptionExpiry"),
                          intraday_signals=intraday_signals,
                          fno_signals=fno_signals,
                          closed_signals=closed_signals,
                          total_signals=len(all_signals),
                          notifications=notifications,
                          plans=MEMBERSHIP_PLANS)

@app.route("/check-subscription")
def check_subscription():
    """Check current user's subscription status"""
    uid = session.get("user_id")
    if not uid:
        return jsonify({"status": "unknown", "message": "Login required"}), 401

    is_active = check_subscription_active(uid)
    user_doc = get_user_doc(uid) or {}

    return jsonify({
        "status": "active" if is_active else "expired",
        "plan": user_doc.get("plan", "none"),
        "expiry": user_doc.get("subscriptionExpiry", ""),
        "message": "Premium active!" if is_active else "Subscription expired or not found."
    })

# -------------------------------------------------
# RAZORPAY PAYMENT INTEGRATION
# -------------------------------------------------
@app.route("/create-payment-order", methods=["POST"])
def create_payment_order():
    """Create Razorpay payment order for a membership plan"""
    if not razorpay_client:
        if razorpay_init_error:
            print(f"⚠️ Payment error: {razorpay_init_error}")
        print("❌ Razorpay client is not initialized. Cannot create payment order.")
        return jsonify({"error": "Payment system is temporarily unavailable. Please try again later."}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request data"}), 400

        plan_slug = data.get("plan", "monthly")
        plan = MEMBERSHIP_PLANS.get(plan_slug)
        if not plan:
            return jsonify({"error": f"Invalid plan: {plan_slug}"}), 404

        amount_paise = plan["price"] * 100

        order_data = {
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1,
            "notes": {
                "plan": plan_slug,
                "plan_name": plan["name"],
                "user_email": session.get("email", ""),
                "username": session.get("username", "User"),
                "user_id": session.get("user_id", "")
            }
        }

        print(f"📦 Creating Razorpay order: {plan['name']} — ₹{plan['price']}")
        order = razorpay_client.order.create(data=order_data)

        if not order or "id" not in order:
            return jsonify({"error": "Order creation failed"}), 500

        print(f"✅ Razorpay order created: {order['id']}")

        return jsonify({
            "order_id": order["id"],
            "amount": amount_paise,
            "currency": "INR",
            "key_id": RAZORPAY_KEY_ID,
            "plan": plan_slug,
            "plan_name": plan["name"]
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error creating Razorpay order: {e}")
        return jsonify({"error": "Unable to initialize checkout. Please contact support if the issue persists."}), 500


@app.route("/verify-payment", methods=["POST"])
def verify_payment():
    """Verify Razorpay payment and activate subscription"""
    if not razorpay_client:
        return jsonify({"error": "Payment verification system is currently unavailable."}), 500

    try:
        payment_data = request.get_json()
        razorpay_payment_id = payment_data.get("razorpay_payment_id")
        razorpay_order_id = payment_data.get("razorpay_order_id")
        razorpay_signature = payment_data.get("razorpay_signature")

        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
            return jsonify({"error": "Missing payment details"}), 400

        # Verify payment signature
        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        }

        try:
            razorpay_client.utility.verify_payment_signature(params_dict)
            print(f"✅ Payment signature verified: {razorpay_payment_id}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"❌ Payment signature verification failed: {e}")
            return jsonify({"error": "Invalid payment signature"}), 400

        # Get order details
        order = razorpay_client.order.fetch(razorpay_order_id)
        plan_slug = order.get("notes", {}).get("plan", "monthly")
        user_email = order.get("notes", {}).get("user_email", session.get("email", ""))
        username = order.get("notes", {}).get("username", session.get("username", ""))
        user_id = order.get("notes", {}).get("user_id", session.get("user_id", ""))

        plan = MEMBERSHIP_PLANS.get(plan_slug)
        if not plan:
            return jsonify({"error": "Invalid plan"}), 400

        # Save payment record to Firestore
        if db:
            payment_record = {
                "paymentId": razorpay_payment_id,
                "userId": user_id,
                "userEmail": user_email,
                "userName": username,
                "plan": plan_slug,
                "amount": plan["price"],
                "status": "captured",
                "razorpayOrderId": razorpay_order_id,
                "razorpaySignature": razorpay_signature,
                "createdAt": datetime.now().isoformat()
            }
            db.collection("payments").document(razorpay_payment_id).set(payment_record)

        # Activate subscription
        if user_id:
            activate_subscription(user_id, plan_slug, razorpay_payment_id, razorpay_order_id)

        # Update session
        session["approved"] = True

        print(f"✅ Payment verified & subscription activated: {plan['name']} for {username}")

        return jsonify({
            "success": True,
            "message": f"Payment successful! {plan['name']} activated.",
            "redirect": url_for("dashboard")
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Payment verification error: {e}")
        return jsonify({"error": "Payment verification failed. If your account was charged, please contact support."}), 500


@app.route("/razorpay-webhook", methods=["POST"])
def razorpay_webhook():
    """Handle Razorpay webhook events (payment failures, refunds)"""
    try:
        # Verify webhook signature if secret is configured
        if RAZORPAY_WEBHOOK_SECRET and razorpay_client:
            webhook_signature = request.headers.get("X-Razorpay-Signature", "")
            webhook_body = request.get_data(as_text=True)
            try:
                import hmac, hashlib
                expected = hmac.new(
                    RAZORPAY_WEBHOOK_SECRET.encode('utf-8'),
                    webhook_body.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                if not hmac.compare_digest(expected, webhook_signature):
                    print("❌ Webhook signature verification failed")
                    return jsonify({"status": "invalid_signature"}), 400
            except Exception as e:
                print(f"⚠️ Webhook signature check error: {e}")

        payload = request.get_json()
        event = payload.get("event", "")

        if event == "payment.failed":
            payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment.get("order_id", "")
            print(f"⚠️ Payment failed for order: {order_id}")

            if db and order_id:
                db.collection("payments").add({
                    "paymentId": payment.get("id", ""),
                    "razorpayOrderId": order_id,
                    "status": "failed",
                    "errorCode": payment.get("error_code", ""),
                    "errorDescription": payment.get("error_description", ""),
                    "createdAt": datetime.now().isoformat()
                })

        elif event == "refund.created":
            refund = payload.get("payload", {}).get("refund", {}).get("entity", {})
            payment_id = refund.get("payment_id", "")
            print(f"💰 Refund created for payment: {payment_id}")

            if db and payment_id:
                db.collection("payments").document(payment_id).update({
                    "status": "refunded",
                    "refundId": refund.get("id", ""),
                    "refundAmount": refund.get("amount", 0) / 100,
                    "refundedAt": datetime.now().isoformat()
                })

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"⚠️ Webhook error: {e}")
        return jsonify({"status": "error"}), 500

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
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                background: linear-gradient(160deg, #081821, #0d2a38, #102530);
                color: white;
                font-family: 'Poppins', sans-serif;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 1rem;
            }
            .card {
                background: rgba(16, 37, 48, 0.8);
                backdrop-filter: blur(16px);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 1.5rem;
                padding: 2rem;
                max-width: 400px;
                width: 100%;
                box-shadow: 0 25px 50px rgba(0,0,0,0.4);
            }
            .card h2 {
                color: #FFD54A;
                font-size: 1.5rem;
                margin-bottom: 0.5rem;
                text-align: center;
            }
            .card .error { color: #FF5252; text-align: center; font-size: 0.85rem; margin-bottom: 1rem; }
            input {
                width: 100%;
                padding: 0.75rem 1rem;
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 0.75rem;
                color: white;
                font-size: 0.95rem;
                margin-bottom: 0.75rem;
                outline: none;
            }
            input:focus { border-color: #FFD54A; }
            button {
                width: 100%;
                padding: 0.75rem;
                background: linear-gradient(135deg, #FFD54A, #FFC107);
                color: #081821;
                font-weight: 700;
                font-size: 1rem;
                border: none;
                border-radius: 0.75rem;
                cursor: pointer;
            }
            button:hover { box-shadow: 0 8px 25px rgba(255,213,74,0.4); }
        </style>
        </head>
        <body>
        <div class="card">
            <h2>Admin Login</h2>
            <p class="error">Invalid Credentials</p>
            <form method="POST">
                <input name="username" placeholder="Username">
                <input name="password" type="password" placeholder="Password">
                <button type="submit">Login</button>
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
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(160deg, #081821, #0d2a38, #102530);
            color: white;
            font-family: 'Poppins', sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }
        .card {
            background: rgba(16, 37, 48, 0.8);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 1.5rem;
            padding: 2rem;
            max-width: 400px;
            width: 100%;
            box-shadow: 0 25px 50px rgba(0,0,0,0.4);
        }
        .card h2 {
            color: #FFD54A;
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            text-align: center;
        }
        .card p { color: #aaa; text-align: center; font-size: 0.85rem; margin-bottom: 1.5rem; }
        .logo {
            width: 4rem; height: 4rem; border-radius: 50%;
            margin: 0 auto 1rem;
            display: block;
            box-shadow: 0 0 20px rgba(255,213,74,0.3);
        }
        input {
            width: 100%;
            padding: 0.75rem 1rem;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 0.75rem;
            color: white;
            font-size: 0.95rem;
            margin-bottom: 0.75rem;
            outline: none;
        }
        input:focus { border-color: #FFD54A; }
        button {
            width: 100%;
            padding: 0.75rem;
            background: linear-gradient(135deg, #FFD54A, #FFC107);
            color: #081821;
            font-weight: 700;
            font-size: 1rem;
            border: none;
            border-radius: 0.75rem;
            cursor: pointer;
            transition: all 0.3s;
        }
        button:hover { box-shadow: 0 8px 25px rgba(255,213,74,0.4); transform: translateY(-1px); }
    </style>
    </head>
    <body>
    <div class="card">
        <img src="/static/logo.png" alt="Logo" class="logo">
        <h2>Admin Login</h2>
        <p>Enter credentials to access admin panel</p>
        <form method="POST">
            <input name="username" placeholder="Username">
            <input name="password" type="password" placeholder="Password">
            <button type="submit">Login</button>
        </form>
    </div>
    </body>
    </html>
    """


@app.route("/admin")
def admin_panel():
    if not session.get("admin"):
        return redirect("/admin-login")

    try:
        signals = get_active_signals()
        subscribers = get_all_subscribers()
        payments = get_all_payments()

        # Additional Stats
        today = datetime.now().date()
        todays_intraday = 0
        todays_fno = 0
        target_hits = 0
        
        for s in signals:
            created = s.get("createdAt", "")
            cat = s.get("category", "")
            status = s.get("status", "")
            
            if status in ["Target Hit", "TARGET HIT"]:
                target_hits += 1
                
            if created:
                try:
                    sig_date = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=None).date()
                    if sig_date == today:
                        if cat == "Intraday":
                            todays_intraday += 1
                        elif cat == "F&O":
                            todays_fno += 1
                except ValueError:
                    pass

        current_month = datetime.now().strftime("%Y-%m")
        monthly_revenue = 0
        total_revenue = 0
        for p in payments:
            if p.get("status") == "captured":
                amt = p.get("amount", 0)
                total_revenue += amt
                p_date = p.get("createdAt", "")
                if p_date and p_date.startswith(current_month):
                    monthly_revenue += amt

        active_subs = len([s for s in subscribers if s.get("subscriptionStatus") == "active"])

        return render_template("admin_panel.html",
            signals=signals,
            subscribers=subscribers,
            payments=payments,
            active_subs=active_subs,
            total_revenue=total_revenue,
            todays_intraday=todays_intraday,
            todays_fno=todays_fno,
            monthly_revenue=monthly_revenue,
            target_hits=target_hits,
            plans=MEMBERSHIP_PLANS)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"<h1>Internal Server Error</h1><pre>{traceback.format_exc()}</pre>", 500

# -------------------------------------------------
# ADMIN API — SIGNAL MANAGEMENT
# -------------------------------------------------
@app.route("/admin/signal/create", methods=["GET", "POST"])
def admin_create_signal():
    """Create a new stock signal"""
    if not session.get("admin"):
        # return redirect("/admin-login")
        pass

    if request.method == "POST":
        if not db:
            return redirect("/admin?error=Firestore not available")

        try:
            now = datetime.now().isoformat()
            signal_data = {
                "category": request.form.get("category", "Intraday"),
                "stockName": sanitize_input(request.form.get("stockName", "")).upper(),
                "recommendation": request.form.get("recommendation", "BUY"),
                "currentPrice": float(request.form.get("currentPrice", 0)),
                "targetPrice": float(request.form.get("targetPrice", 0)),
                "duration": request.form.get("duration", "Intraday"),
                "confidence": request.form.get("confidence", "High"),
                "status": request.form.get("status", "Active"),
                "createdAt": now,
                "updatedAt": now,
                "createdBy": "admin"
            }

            db.collection("stockSignals").add(signal_data)
            log_admin_action("admin", "CREATE_SIGNAL", "", f"Created {signal_data['category']} signal for {signal_data['stockName']}")
            create_notification("global", f"New {signal_data['category']} Signal: {signal_data['stockName']} is now active!")
            print(f"✅ Signal created: {signal_data['stockName']}")
            return redirect("/admin?success=Signal created successfully")
        except Exception as e:
            import traceback
            return f"<h1>Error</h1><pre>{traceback.format_exc()}</pre>", 500

    return render_template("signal_form.html", signal=None, mode="create")

@app.route("/admin/signal/edit/<signal_id>", methods=["GET", "POST"])
def admin_edit_signal(signal_id):
    """Edit an existing stock signal"""
    if not session.get("admin"):
        return redirect("/admin-login")

    if not db:
        return redirect("/admin?error=Firestore not available")

    if request.method == "POST":
        try:
            now = datetime.now().isoformat()
            update_data = {
                "category": request.form.get("category", "Intraday"),
                "stockName": request.form.get("stockName", "").strip().upper(),
                "recommendation": request.form.get("recommendation", "BUY"),
                "currentPrice": float(request.form.get("currentPrice", 0)),
                "targetPrice": float(request.form.get("targetPrice", 0)),
                "duration": request.form.get("duration", "Intraday"),
                "confidence": request.form.get("confidence", "High"),
                "status": request.form.get("status", "Active"),
                "updatedAt": now
            }

            db.collection("stockSignals").document(signal_id).update(update_data)
            
            log_admin_action("admin", "UPDATE_SIGNAL", signal_id, f"Updated signal for {update_data['stockName']}")
            print(f"✅ Signal updated: {signal_id}")
            return redirect("/admin?success=Signal updated successfully")
        except Exception as e:
            import traceback
            return f"<h1>Error</h1><pre>{traceback.format_exc()}</pre>", 500

    try:
        doc = db.collection("stockSignals").document(signal_id).get()
        if not doc.exists:
            return redirect("/admin?error=Signal not found")
        signal = doc.to_dict()
        signal["id"] = doc.id
    except Exception as e:
        import traceback
        traceback.print_exc()
        return redirect(f"/admin?error=Error loading signal: {str(e)}")

    return render_template("signal_form.html", signal=signal, mode="edit")

@app.route("/admin/signal/delete/<signal_id>", methods=["POST"])
def admin_delete_signal(signal_id):
    """Delete a stock signal"""
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401

    if not db:
        return jsonify({"error": "Firestore not available"}), 500

    try:
        db.collection("stockSignals").document(signal_id).delete()
        log_admin_action("admin", "DELETE_SIGNAL", signal_id, "Deleted signal")
        print(f"🗑️ Signal deleted: {signal_id}")
        return redirect("/admin?success=Signal deleted")
    except Exception as e:
        print(f"❌ Error deleting signal: {e}")
        return redirect(f"/admin?error=Error deleting signal: {str(e)}")


@app.route("/admin/signal/status/<signal_id>", methods=["POST"])
def admin_update_signal_status(signal_id):
    """Quick-update signal status"""
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401

    if not db:
        return jsonify({"error": "Firestore not available"}), 500

    try:
        new_status = request.form.get("status", "ACTIVE")
        db.collection("stockSignals").document(signal_id).update({
            "status": new_status,
            "updatedAt": datetime.now().isoformat()
        })
        log_admin_action("admin", "UPDATE_STATUS", signal_id, f"Status → {new_status}")
        return redirect("/admin?success=Status updated")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return redirect(f"/admin?error=Error updating status: {str(e)}")


# -------------------------------------------------
# ADMIN API — SUBSCRIBER MANAGEMENT
# -------------------------------------------------
@app.route("/admin/subscriber/extend/<uid>", methods=["POST"])
def admin_extend_subscription(uid):
    """Extend a user's subscription"""
    if not session.get("admin"):
        return redirect("/admin-login")

    if not db:
        return redirect("/admin?error=Firestore not available")

    try:
        days = int(request.form.get("days", 30))
        user_doc = get_user_doc(uid)

        if not user_doc:
            return redirect("/admin?error=User not found")

        # Calculate new expiry
        current_expiry = user_doc.get("subscriptionExpiry")
        if current_expiry and current_expiry != "lifetime":
            if isinstance(current_expiry, str):
                try:
                    base_date = datetime.fromisoformat(current_expiry.replace("Z", "+00:00")).replace(tzinfo=None)
                except ValueError:
                    base_date = datetime.now()
            else:
                base_date = datetime.now()
        else:
            base_date = datetime.now()

        new_expiry = base_date + timedelta(days=days)

        db.collection("users").document(uid).update({
            "subscriptionStatus": "active",
            "subscriptionExpiry": new_expiry.isoformat(),
            "updatedAt": datetime.now().isoformat()
        })

        log_admin_action("admin", "EXTEND_SUBSCRIPTION", uid, f"Extended by {days} days → {new_expiry.isoformat()}")
        return redirect("/admin?success=Subscription extended")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return redirect(f"/admin?error=Error extending subscription: {str(e)}")


@app.route("/admin/subscriber/revoke/<uid>", methods=["POST"])
def admin_revoke_subscription(uid):
    """Revoke a user's subscription"""
    if not session.get("admin"):
        return redirect("/admin-login")

    if not db:
        return redirect("/admin?error=Firestore not available")

    try:
        db.collection("users").document(uid).update({
            "subscriptionStatus": "expired",
            "updatedAt": datetime.now().isoformat()
        })
        log_admin_action("admin", "REVOKE_SUBSCRIPTION", uid, "Subscription revoked")
        return redirect("/admin?success=Subscription revoked")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return redirect(f"/admin?error=Error revoking subscription: {str(e)}")

# -------------------------------------------------
# RAZORPAY COMPLIANCE PAGES (Must be public)
# -------------------------------------------------
@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/refund")
def refund():
    return render_template("refund.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/about")
def about_page():
    logged_in = session.get("logged_in") or session.get("user_id")
    username = session.get("username", "")
    return render_template("about.html", username=username, logged_in=logged_in)

# Legacy routes — redirect to new pages
@app.route("/products")
def products_page():
    return redirect(url_for("plans_page"))

@app.route("/payment")
def payment_page():
    return redirect(url_for("plans_page"))

# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------
if __name__ == "__main__":
    start_scheduler()
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_ENV", "production").lower() != "production"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
