# ============================================================
#  HireReady — backend/auth.py
#  Password reset token logic + remember me helpers
#
#  How password reset works (no email server needed for dev):
#  1. User submits email on /forgot-password
#  2. We generate a secure token tied to that email + expiry
#  3. Reset link is printed to the terminal in dev mode
#  4. User clicks link → /reset-password/<token>
#  5. Token is verified — must exist and not be expired
#  6. User sets new password → bcrypt hash → saved to DB
# ============================================================

import secrets
from datetime import datetime, timedelta


# ── In-memory token store (dev only) ─────────────────────────
# Structure: { token_string: { "email": str, "expires_at": datetime } }
# TODO: move to a DB table called PasswordResetToken in production
_reset_tokens = {}


# ============================================================
#  TOKEN GENERATION + VERIFICATION
# ============================================================

def generate_reset_token(email):
    """
    Create a secure 32-byte URL-safe token for password reset.
    Expires in 30 minutes. Returns the token string.
    """
    token = secrets.token_urlsafe(32)   # cryptographically secure

    _reset_tokens[token] = {
        "email":      email.lower().strip(),
        "expires_at": datetime.utcnow() + timedelta(minutes=30)
    }

    return token


def verify_reset_token(token):
    """
    Validate a reset token.
    Returns the associated email if valid.
    Returns None if token doesn't exist or has expired.
    """
    data = _reset_tokens.get(token)

    if not data:
        return None  # token not found

    if datetime.utcnow() > data["expires_at"]:
        _reset_tokens.pop(token, None)  # clean up expired token
        return None

    return data["email"]


def consume_reset_token(token):
    """
    Delete a token after it has been used.
    Prevents the same link from being used twice.
    """
    _reset_tokens.pop(token, None)


# ============================================================
#  EMAIL SENDER
#  In dev: prints the reset link to the terminal
#  In production: swap print() for Flask-Mail or SendGrid
# ============================================================

def send_reset_email(email, token, base_url="http://localhost:5000"):
    """
    Send (or simulate sending) a password reset email.
    """
    reset_link = f"{base_url}/reset-password/{token}"

    # ── DEV MODE — print link to terminal so you can test ────
    print("\n" + "=" * 58)
    print(f"  📧  Password reset requested for : {email}")
    print(f"  🔗  Reset link : {reset_link}")
    print(f"  ⏱️   Expires in : 30 minutes")
    print("=" * 58 + "\n")
    # ─────────────────────────────────────────────────────────

    # ── PRODUCTION — uncomment when ready ────────────────────
    # pip install flask-mail, then add to app.py:
    # app.config["MAIL_SERVER"]   = "smtp.gmail.com"
    # app.config["MAIL_PORT"]     = 587
    # app.config["MAIL_USE_TLS"]  = True
    # app.config["MAIL_USERNAME"] = "your@gmail.com"
    # app.config["MAIL_PASSWORD"] = "your-app-password"
    # from flask_mail import Mail, Message
    # mail = Mail(app)
    #
    # msg = Message(
    #     subject    = "Reset your HireReady password",
    #     sender     = "noreply@hireready.com",
    #     recipients = [email]
    # )
    # msg.body = f"Click the link to reset your password:\n{reset_link}\n\nExpires in 30 minutes."
    # mail.send(msg)
    # ─────────────────────────────────────────────────────────

    return reset_link


# ============================================================
#  REMEMBER ME — session lifetime
# ============================================================

SESSION_LIFETIME_REMEMBER = timedelta(days=30)   # checked "remember me"
SESSION_LIFETIME_DEFAULT  = timedelta(hours=24)  # did not check


def apply_session_lifetime(app, remember=False):
    """
    Call this right after a successful login.
    Sets how long the session cookie lasts.

    remember=True  → 30 days  (user ticked "remember me")
    remember=False → 24 hours (default, safer on shared devices)
    """
    if remember:
        app.permanent_session_lifetime = SESSION_LIFETIME_REMEMBER
    else:
        app.permanent_session_lifetime = SESSION_LIFETIME_DEFAULT