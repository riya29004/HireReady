# # ============================================================
# #  HireReady — app.py  (MASTER / FINAL VERSION)
# #  Location: project root
# #
# #  Project structure:
# #  HIRER.../
# #  ├── app.py                 ← YOU ARE HERE
# #  ├── static/
# #  │   ├── css/
# #  │   └── js/
# #  ├── templates/
# #  ├── database/
# #  │   ├── __init__.py
# #  │   ├── extensions.py      ← db instance
# #  │   ├── models.py          ← table definitions
# #  │   └── queries.py         ← all DB helper functions
# #  ├── backend/
# #  │   └── auth.py            ← password reset + session helpers
# #  └── agents/
# #      └── __init__.py        ← AI agent blueprints (Phase 4)
# #
# #  First time setup:
# #      pip install flask flask-sqlalchemy flask-bcrypt
# #      python app.py
# #
# #  Run: python app.py
# # ============================================================

# import os
# from datetime import datetime

# from flask import (
#     Flask, render_template, request,
#     redirect, url_for, session, flash
# )
# from flask_bcrypt import Bcrypt

# # ── Database ─────────────────────────────────────────────────
# from database.extensions import db
# from database.models     import User, Doubt, InterviewSession, Question
# from database.queries    import (
#     get_user_by_email,
#     create_user,
#     email_exists,
#     get_dashboard_data,
#     save_doubt,
#     get_weak_topics,
# )

# # ── Auth helpers (password reset, remember me) ───────────────
# from backend.auth import (
#     generate_reset_token,
#     verify_reset_token,
#     consume_reset_token,
#     send_reset_email,
#     apply_session_lifetime,
# )

# # ============================================================
# #  APP SETUP
# # ============================================================

# BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
# TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
# STATIC_DIR   = os.path.join(BASE_DIR, "static")
# DB_PATH points to the local SQLite database file.

# app = Flask(
#     __name__,
#     template_folder = TEMPLATE_DIR,
#     static_folder   = STATIC_DIR
# )

# app.config["SECRET_KEY"]                     = os.environ.get("SECRET_KEY", "change-this-in-production")
# app.config["SQLALCHEMY_DATABASE_URI"]        = f"sqlite:///{DB_PATH}"
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# # ── Init extensions ──────────────────────────────────────────
# db.init_app(app)
# bcrypt = Bcrypt(app)

# # ── Auto-create all DB tables on first run ───────────────────
# with app.app_context():
#     db.create_all()
#     print(f"\n✅  Database ready : {DB_PATH}\n")

# # ── Register AI agent blueprints (Phase 4) ───────────────────
# # Uncomment these lines once you have built the agents/ folder
# # from agents import agents_bp
# # app.register_blueprint(agents_bp)

# # Uncomment once interview API is built
# # from interview_api import interview_bp
# # app.register_blueprint(interview_bp)


# # ============================================================
# #  HELPER — login guard
# # ============================================================

# def login_required(f):
#     """
#     Decorator — redirects to /login if user is not in session.
#     Use on any route that requires authentication.
#     """
#     from functools import wraps
#     @wraps(f)
#     def decorated(*args, **kwargs):
#         if "user_id" not in session:
#             flash("Please log in to continue.", "error")
#             return redirect(url_for("login"))
#         return f(*args, **kwargs)
#     return decorated


# # ============================================================
# #  AUTH ROUTES
# # ============================================================

# @app.route("/login", methods=["GET"])
# def login():
#     """Show the login/signup page."""
#     return render_template("login.html")


# @app.route("/auth/login", methods=["POST"])
# def auth_login():
#     """Handle login form submission."""
#     email    = request.form.get("email",    "").strip().lower()
#     password = request.form.get("password", "")
#     remember = bool(request.form.get("remember"))

#     user = get_user_by_email(email)

#     if user and bcrypt.check_password_hash(user.password, password):
#         # Set session lifetime based on remember me checkbox
#         apply_session_lifetime(app, remember=remember)

#         session.permanent    = True
#         session["user_id"]   = user.id
#         session["user_email"] = user.email
#         session["user_name"]  = user.name
#         return redirect(url_for("dashboard"))

#     flash("Invalid email or password.", "error")
#     return redirect(url_for("login"))


# @app.route("/auth/signup", methods=["POST"])
# def auth_signup():
#     """Handle signup form submission."""
#     name     = request.form.get("name",     "").strip()
#     email    = request.form.get("email",    "").strip().lower()
#     password = request.form.get("password", "")

#     # Validate
#     if not name or not email or not password:
#         flash("All fields are required.", "error")
#         return redirect(url_for("login") + "?tab=signup")

#     if len(password) < 8:
#         flash("Password must be at least 8 characters.", "error")
#         return redirect(url_for("login") + "?tab=signup")

#     if email_exists(email):
#         flash("An account with this email already exists.", "error")
#         return redirect(url_for("login") + "?tab=signup")

#     # Hash password and create user
#     hashed = bcrypt.generate_password_hash(password).decode("utf-8")
#     user   = create_user(name, email, hashed)

#     # Log in immediately after signup
#     apply_session_lifetime(app, remember=False)
#     session.permanent     = True
#     session["user_id"]    = user.id
#     session["user_email"] = user.email
#     session["user_name"]  = user.name
#     return redirect(url_for("dashboard"))


# @app.route("/logout")
# def logout():
#     """Clear session and redirect to login."""
#     session.clear()
#     response = redirect(url_for("login"))
#     # Prevent browser back button from restoring session
#     response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
#     response.headers["Pragma"]        = "no-cache"
#     return response


# # ── Forgot / Reset password ───────────────────────────────────

# @app.route("/forgot-password", methods=["GET"])
# def forgot_password():
#     return render_template("forgot_password.html", email_sent=False)


# @app.route("/auth/forgot-password", methods=["POST"])
# def auth_forgot_password():
#     email = request.form.get("email", "").strip().lower()
#     user  = get_user_by_email(email)

#     if user:
#         token = generate_reset_token(email)
#         send_reset_email(email, token)   # prints link to terminal in dev

#     # Always show success — never reveal if the email exists (security)
#     return render_template(
#         "forgot_password.html",
#         email_sent      = True,
#         submitted_email = email
#     )


# @app.route("/reset-password/<token>", methods=["GET"])
# def reset_password(token):
#     email = verify_reset_token(token)
#     if not email:
#         return render_template("reset_password.html", token_invalid=True, token=token)
#     return render_template("reset_password.html", token_invalid=False, token=token)


# @app.route("/auth/reset-password/<token>", methods=["POST"])
# def auth_reset_password(token):
#     email = verify_reset_token(token)

#     if not email:
#         flash("This reset link has expired. Please request a new one.", "error")
#         return redirect(url_for("forgot_password"))

#     password = request.form.get("password", "")
#     confirm  = request.form.get("confirm",  "")

#     if len(password) < 8:
#         flash("Password must be at least 8 characters.", "error")
#         return redirect(url_for("reset_password", token=token))

#     if password != confirm:
#         flash("Passwords do not match.", "error")
#         return redirect(url_for("reset_password", token=token))

#     # Save new hashed password
#     user = get_user_by_email(email)
#     if user:
#         user.password = bcrypt.generate_password_hash(password).decode("utf-8")
#         db.session.commit()

#     consume_reset_token(token)   # invalidate link so it can't be reused

#     flash("Password reset successfully. Please log in.", "success")
#     return redirect(url_for("login"))


# # ============================================================
# #  PAGE ROUTES
# # ============================================================

# @app.route("/")
# def index():
#     return render_template("Index.html")


# @app.route("/dashboard")
# @login_required
# def dashboard():
#     hour = datetime.now().hour
#     if   hour < 12: time_of_day = "morning"
#     elif hour < 17: time_of_day = "afternoon"
#     else:           time_of_day = "evening"

#     data = get_dashboard_data(session["user_id"])

#     return render_template(
#         "dashboard.html",
#         time_of_day     = time_of_day,
#         streak          = 1,                    # TODO: real streak — Phase 5
#         total_doubts    = data["total_doubts"],
#         interviews_done = data["interviews_done"],
#         subjects_active = data["subjects_active"],
#         weak_count      = data["weak_count"],
#         recent_doubts   = data["recent_doubts"],
#         weak_topics     = data["weak_topics"],
#     )


# @app.route("/dsa")
# @login_required
# def dsa():
#     return render_template("dsa.html")


# @app.route("/dbms")
# @login_required
# def dbms():
#     return render_template("dbms.html")


# @app.route("/os")
# @login_required
# def operating_systems():
#     return render_template("os.html")


# @app.route("/cn")
# @login_required
# def computer_networks():
#     return render_template("cn.html")


# @app.route("/interview")
# @login_required
# def interview():
#     return render_template("interview.html")


# @app.route("/progress")
# @login_required
# def progress():
#     return render_template("progress.html")


# @app.route("/planner")
# @login_required
# def planner():
#     return render_template("planner.html")


# # ============================================================
# #  RUN
# # ============================================================

# if __name__ == "__main__":
#     app.run(debug=True, port=5000)
# ============================================================
#  HireReady — app.py  (Phase 4 ready)
#  Location: project root
#
#  Structure:
#  HIRER.../
#  ├── app.py
#  ├── static/css/ & js/
#  ├── templates/
#  ├── database/
#  │   ├── __init__.py
#  │   ├── extensions.py
#  │   ├── models.py
#  │   └── queries.py
#  ├── backend/
#  │   └── auth.py
#  └── agents/
#      └── __init__.py        ← uncomment below when ready
#
#  Run: python app.py
# ============================================================

# ============================================================
#  HireReady — app.py
#  Run: python app.py
# ============================================================
from dotenv import load_dotenv

load_dotenv()   # ← MUST be first — loads .env before anything else

import os
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash, jsonify
)
from flask_bcrypt import Bcrypt

# ── Database ─────────────────────────────────────────────────
from database.extensions import db
from database.models     import User, Doubt, InterviewSession, Question, TopicStrength
from database.queries    import (
    get_user_by_email,
    create_user,
    email_exists,
    get_dashboard_data,
    save_doubt,
    get_weak_topics,
    get_streak,
    get_progress_data,
    create_interview_session,
    complete_interview_session,
    save_question,
    submit_answer,
)

# ── Auth helpers ─────────────────────────────────────────────
from backend.auth import (
    generate_reset_token,
    verify_reset_token,
    consume_reset_token,
    send_reset_email,
    apply_session_lifetime,
)

# ── AI Blueprints ─────────────────────────────────────────────
from agents        import agents_bp
from interview_api import interview_bp

# ============================================================
#  APP SETUP
# ============================================================

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR   = os.path.join(BASE_DIR, "static")
DB_PATH      = os.path.join(BASE_DIR, "database", "hireready.db")

# Database: local SQLite, accessed through SQLAlchemy.

app = Flask(
    __name__,
    template_folder = TEMPLATE_DIR,
    static_folder   = STATIC_DIR
)

app.config["SECRET_KEY"]                     = os.environ.get("SECRET_KEY", "change-this-in-production")
app.config["SQLALCHEMY_DATABASE_URI"]        = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

GUEST_NAME = "Guest User"
GUEST_EMAIL = "guest@hireready.demo"


# ── Init extensions ──────────────────────────────────────────
db.init_app(app)
bcrypt = Bcrypt(app)

# ── Register blueprints ───────────────────────────────────────
app.register_blueprint(agents_bp)
app.register_blueprint(interview_bp)

# ── Auto-create all tables on first run ──────────────────────
with app.app_context():
    db.create_all()
    print(f"\nDatabase ready : {DB_PATH}\n")


# ============================================================
#  HELPER — login guard
# ============================================================

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ============================================================
#  AUTH ROUTES
# ============================================================

@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@app.route("/auth/login", methods=["POST"])
def auth_login():
    email    = request.form.get("email",    "").strip().lower()
    password = request.form.get("password", "")
    remember = bool(request.form.get("remember"))

    user = get_user_by_email(email)

    if user and bcrypt.check_password_hash(user.password, password):
        apply_session_lifetime(app, remember=remember)
        session.permanent     = True
        session["user_id"]    = user.id
        session["user_email"] = user.email
        session["user_name"]  = user.name
        session["is_guest"]   = False
        return redirect(url_for("dashboard"))

    flash("Invalid email or password.", "error")
    return redirect(url_for("login"))


@app.route("/auth/signup", methods=["POST"])
def auth_signup():
    name     = request.form.get("name",     "").strip()
    email    = request.form.get("email",    "").strip().lower()
    password = request.form.get("password", "")

    if not name or not email or not password:
        flash("All fields are required.", "error")
        return redirect(url_for("login") + "?tab=signup")

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for("login") + "?tab=signup")

    if email_exists(email):
        flash("An account with this email already exists.", "error")
        return redirect(url_for("login") + "?tab=signup")

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    user   = create_user(name, email, hashed)

    apply_session_lifetime(app, remember=False)
    session.permanent     = True
    session["user_id"]    = user.id
    session["user_email"] = user.email
    session["user_name"]  = user.name
    session["is_guest"]   = False
    return redirect(url_for("dashboard"))


def seed_guest_demo_data(user):
    """
    Create recruiter-friendly sample data for the shared guest account.
    Existing records are checked before insert, so guest login stays idempotent.
    """
    now = datetime.utcnow()

    demo_doubts = [
        ("DSA",  "Dynamic Programming", "Why do we use memoization in dynamic programming?", "Memoization stores results of overlapping subproblems so repeated recursive calls become faster.", 0),
        ("DSA",  "Graphs", "When should I use BFS instead of DFS in graph questions?", "Use BFS for shortest path in unweighted graphs and level-order style exploration.", 1),
        ("DBMS", "SQL Joins", "What is the difference between inner join and left join?", "Inner join returns matching rows only, while left join keeps all rows from the left table.", 2),
        ("DBMS", "Normalization", "Why is normalization important in database design?", "Normalization reduces redundancy and avoids insertion, update, and deletion anomalies.", 3),
        ("OS",   "Deadlocks", "What are the four conditions required for deadlock?", "Mutual exclusion, hold and wait, no preemption, and circular wait must occur together.", 4),
        ("OS",   "Paging", "How does paging help in memory management?", "Paging divides memory into fixed-size pages and frames so processes can use non-contiguous physical memory.", 5),
        ("CN",   "TCP Handshake", "Explain the TCP three-way handshake.", "TCP establishes a connection using SYN, SYN-ACK, and ACK before reliable data transfer.", 6),
        ("CN",   "DNS", "What happens when we type a URL in the browser?", "The browser resolves the domain through DNS, connects to the server, and then requests the resource.", 6),
    ]

    # Demo-only cleanup: keep one seeded doubt per question if guest mode is clicked repeatedly.
    for _, _, question, _, _ in demo_doubts:
        seeded_doubts = (
            Doubt.query
            .filter_by(user_id=user.id, question=question)
            .order_by(Doubt.asked_at.asc(), Doubt.id.asc())
            .all()
        )
        for duplicate_doubt in seeded_doubts[1:]:
            db.session.delete(duplicate_doubt)

    db.session.commit()

    for subject, topic, question, answer, days_ago in demo_doubts:
        existing = Doubt.query.filter_by(user_id=user.id, question=question).first()
        if existing:
            continue

        doubt = save_doubt(user.id, subject, question, answer, topic)
        doubt.asked_at = now - timedelta(days=days_ago, hours=days_ago % 3)
        db.session.commit()

    demo_interviews = [
        {
            "session_type": "mixed",
            "days_ago": 5,
            "questions": [
                ("DSA", "Dynamic Programming", "Explain overlapping subproblems in dynamic programming.", "Overlapping subproblems means the same smaller problems are solved repeatedly, so we store results using memoization or tabulation.", 8.0, "Strong explanation with correct DP terminology."),
                ("DBMS", "SQL Joins", "Explain inner join, left join, and right join.", "Inner join returns common rows, left join keeps all rows from left table, and right join keeps all rows from right table.", 7.5, "Good answer with clear comparison."),
                ("OS", "Deadlocks", "How can deadlocks be prevented?", "Deadlocks can be prevented by breaking one Coffman condition, such as avoiding circular wait or allowing preemption.", 7.0, "Correct but could include more examples."),
            ],
        },
        {
            "session_type": "weak",
            "days_ago": 2,
            "questions": [
                ("DSA", "Graphs", "When is BFS preferred over DFS?", "BFS is preferred for level-wise traversal and shortest path in unweighted graphs.", 8.2, "Clear, interview-ready answer."),
                ("CN", "TCP Handshake", "Walk through the TCP three-way handshake.", "Client sends SYN, server replies SYN-ACK, and client sends ACK to establish the connection.", 7.8, "Accurate answer with the required sequence."),
                ("OS", "Paging", "What is paging and why is it useful?", "Paging maps virtual pages to physical frames and helps avoid external fragmentation.", 6.5, "Mostly correct, but could mention page tables and TLB."),
            ],
        },
        {
            "session_type": "practical",
            "days_ago": 1,
            "questions": [
                ("DBMS", "Normalization", "Explain 1NF, 2NF, and 3NF with purpose.", "1NF removes repeating groups, 2NF removes partial dependency, and 3NF removes transitive dependency.", 7.2, "Good concise answer, examples would make it stronger."),
                ("CN", "DNS", "Explain how DNS resolution works.", "The browser checks cache, then resolver queries DNS servers to find the IP address for the domain.", 6.8, "Good flow, but missing recursive/authoritative server detail."),
                ("DSA", "Binary Search", "What condition is required for binary search?", "The data must be sorted because binary search discards half of the search space each step.", 8.6, "Strong and precise answer."),
            ],
        },
    ]

    # Demo-only cleanup: keep one seeded interview per type if the guest route is clicked repeatedly.
    for demo in demo_interviews:
        first_question = demo["questions"][0][2]
        seeded_sessions = []
        rows = (
            InterviewSession.query
            .filter_by(user_id=user.id, session_type=demo["session_type"])
            .order_by(InterviewSession.started_at.asc(), InterviewSession.id.asc())
            .all()
        )

        for iv in rows:
            if any(q.question == first_question for q in iv.questions):
                seeded_sessions.append(iv)

        for duplicate_iv in seeded_sessions[1:]:
            db.session.delete(duplicate_iv)

    db.session.commit()

    for demo in demo_interviews:
        first_question = demo["questions"][0][2]
        already_seeded = (
            InterviewSession.query
            .filter_by(user_id=user.id, session_type=demo["session_type"])
            .filter(InterviewSession.completed_at.isnot(None))
            .all()
        )
        already_seeded = any(
            any(q.question == first_question for q in iv.questions)
            for iv in already_seeded
        )
        if already_seeded:
            continue

        iv = create_interview_session(user.id, demo["session_type"])
        iv.started_at = now - timedelta(days=demo["days_ago"], minutes=18)
        db.session.commit()

        scores = []
        for subject, topic, question_text, user_answer, score, feedback in demo["questions"]:
            q = save_question(iv.id, subject, topic, question_text)
            q.asked_at = iv.started_at
            db.session.commit()
            submit_answer(q.id, user_answer, score, feedback)
            scores.append(score)

        avg_score = sum(scores) / len(scores)
        complete_interview_session(iv.id, avg_score)
        iv.completed_at = iv.started_at + timedelta(minutes=18)
        iv.score = round(avg_score, 2)
        db.session.commit()

    demo_strengths = {
        ("DSA", "Dynamic Programming"): 53.0,
        ("DSA", "Graphs"): 69.0,
        ("DSA", "Binary Search"): 74.0,
        ("DBMS", "SQL Joins"): 53.0,
        ("DBMS", "Normalization"): 69.0,
        ("OS", "Deadlocks"): 53.0,
        ("OS", "Paging"): 36.0,
        ("CN", "TCP Handshake"): 69.0,
        ("CN", "DNS"): 36.0,
    }

    for (subject, topic), score in demo_strengths.items():
        ts = TopicStrength.query.filter_by(
            user_id=user.id,
            subject=subject,
            topic=topic,
        ).first()

        if not ts:
            ts = TopicStrength(user_id=user.id, subject=subject, topic=topic)
            db.session.add(ts)

        ts.score = score
        ts.doubt_count = Doubt.query.filter_by(
            user_id=user.id,
            subject=subject,
            topic=topic,
        ).count()
        ts.correct_count = (
            db.session.query(Question)
            .join(InterviewSession, InterviewSession.id == Question.session_id)
            .filter(
                InterviewSession.user_id == user.id,
                Question.subject == subject,
                Question.topic == topic,
                Question.score >= 7.0,
            )
            .count()
        )
        ts.updated_at = now

    db.session.commit()


@app.route("/auth/guest", methods=["POST"])
def auth_guest():
    """
    Start a demo session using the shared guest account in the local SQLite database.
    Guest mode reuses normal authenticated routes so the demo behaves like the real app.
    """
    user = get_user_by_email(GUEST_EMAIL)

    if not user:
        guest_password = bcrypt.generate_password_hash(os.urandom(32).hex()).decode("utf-8")
        user = create_user(GUEST_NAME, GUEST_EMAIL, guest_password)

    seed_guest_demo_data(user)

    # Old normal login session fields are kept; guest mode only adds an is_guest marker.
    # Old guest flow before demo seeding:
    # session.permanent     = False
    # session["user_id"]    = user.id
    # session["user_email"] = user.email
    # session["user_name"]  = user.name
    # session["is_guest"]   = True
    session.permanent     = False
    session["user_id"]    = user.id
    session["user_email"] = user.email
    session["user_name"]  = user.name
    session["is_guest"]   = True
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    response = redirect(url_for("login"))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"]        = "no-cache"
    return response


# ── Forgot / Reset password ───────────────────────────────────

@app.route("/forgot-password", methods=["GET"])
def forgot_password():
    return render_template("forgot_password.html", email_sent=False)


@app.route("/auth/forgot-password", methods=["POST"])
def auth_forgot_password():
    email = request.form.get("email", "").strip().lower()
    user  = get_user_by_email(email)
    if user:
        token = generate_reset_token(email)
        send_reset_email(email, token)
    return render_template(
        "forgot_password.html",
        email_sent      = True,
        submitted_email = email
    )


@app.route("/reset-password/<token>", methods=["GET"])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        return render_template("reset_password.html", token_invalid=True, token=token)
    return render_template("reset_password.html", token_invalid=False, token=token)


@app.route("/auth/reset-password/<token>", methods=["POST"])
def auth_reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash("This reset link has expired. Please request a new one.", "error")
        return redirect(url_for("forgot_password"))

    password = request.form.get("password", "")
    confirm  = request.form.get("confirm",  "")

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for("reset_password", token=token))

    if password != confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for("reset_password", token=token))

    user = get_user_by_email(email)
    if user:
        user.password = bcrypt.generate_password_hash(password).decode("utf-8")
        db.session.commit()

    consume_reset_token(token)
    flash("Password reset successfully. Please log in.", "success")
    return redirect(url_for("login"))


# ============================================================
#  PAGE ROUTES
# ============================================================

@app.route("/")
def index():
    return render_template("Index.html")


@app.route("/dashboard")
@login_required
def dashboard():
    hour = datetime.now().hour
    if   hour < 12: time_of_day = "morning"
    elif hour < 17: time_of_day = "afternoon"
    else:           time_of_day = "evening"

    data   = get_dashboard_data(session["user_id"])
    streak = get_streak(session["user_id"])

    return render_template(
        "dashboard.html",
        time_of_day     = time_of_day,
        streak          = streak,
        total_doubts    = data["total_doubts"],
        interviews_done = data["interviews_done"],
        subjects_active = data["subjects_active"],
        weak_count      = data["weak_count"],
        recent_doubts   = data["recent_doubts"],
        weak_topics     = data["weak_topics"],
    )


@app.route("/dsa")
@login_required
def dsa():
    return render_template("dsa.html")


@app.route("/dbms")
@login_required
def dbms():
    return render_template("dbms.html")


@app.route("/os")
@login_required
def operating_systems():
    return render_template("os.html")


@app.route("/cn")
@login_required
def computer_networks():
    return render_template("cn.html")


@app.route("/interview")
@login_required
def interview():
    return render_template("interview.html")


@app.route("/progress")
@login_required
def progress():
    return render_template("progress.html")


@app.route("/planner")
@login_required
def planner():
    return render_template("planner.html")


# ============================================================
#  INTERVIEW SESSION ROUTES
#  These are called by interview.js
# ============================================================

@app.route("/api/interview/start", methods=["POST"])
@login_required
def interview_start():
    """
    POST /api/interview/start
    Body: { "session_type": "mixed"|"theory"|"practical", "subjects": [...] }
    Returns: { "session_id": 123 }
    Creates a DB session row so questions can be linked to it.
    """
    data         = request.get_json(force=True)
    session_type = data.get("session_type", "mixed")

    iv = create_interview_session(
        user_id      = session["user_id"],
        session_type = session_type,
    )
    return jsonify({"session_id": iv.id})


@app.route("/api/interview/complete", methods=["POST"])
@login_required
def interview_complete():
    """
    POST /api/interview/complete
    Body: { "session_id": 123, "scores": [7.5, 8.0, 6.0, ...] }
    Calculates average and marks the session as complete.
    """
    data       = request.get_json(force=True)
    session_id = data.get("session_id")
    # Changed: accept the current frontend camelCase key too.
    if not session_id:
        session_id = data.get("sessionId")
    scores     = data.get("scores", [])

    if not session_id or not scores:
        return jsonify({"ok": False, "error": "Missing session_id or scores"}), 400

    avg_score = sum(scores) / len(scores)
    complete_interview_session(session_id, avg_score)
    return jsonify({"ok": True, "avg_score": round(avg_score, 2)})


# ============================================================
#  PROGRESS DATA API
# ============================================================

@app.route("/api/progress")
@login_required
def progress_api():
    """Returns all progress report data as JSON."""
    days = int(request.args.get("days", 7))
    days = max(7, min(30, days))

    try:
        data = get_progress_data(session["user_id"], days)
        return jsonify(data)
    except Exception as e:
        print(f"[/api/progress] Error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================
#  RUN
# ============================================================

if __name__ == "__main__":
    app.run(debug=True, port=5000)
