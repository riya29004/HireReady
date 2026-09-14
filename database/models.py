from datetime import datetime, timedelta
from database.extensions import db


# ============================================================
#  TABLE 1 — USERS
#  Created when: student signs up
# ============================================================

class User(db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer,     primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(150), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)   # bcrypt hash, never plain text
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    # Relationships — cascade delete removes child rows when user is deleted
    doubts            = db.relationship("Doubt",            backref="user", lazy=True, cascade="all, delete-orphan")
    interviews        = db.relationship("InterviewSession", backref="user", lazy=True, cascade="all, delete-orphan")
    topic_strengths   = db.relationship("TopicStrength",   backref="user", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


# ============================================================
#  TABLE 2 — DOUBTS
#  Created when: student sends any message to an AI agent
#  One row per message. Stores question + AI answer.
#  Core of the 7-day tracking system.
# ============================================================

class Doubt(db.Model):
    __tablename__ = "doubts"

    id       = db.Column(db.Integer,     primary_key=True)
    user_id  = db.Column(db.Integer,     db.ForeignKey("users.id"), nullable=False)
    subject  = db.Column(db.String(20),  nullable=False)   # "DSA" | "DBMS" | "OS" | "CN"
    topic    = db.Column(db.String(100), nullable=True)    # e.g. "Dynamic Programming"
    question = db.Column(db.Text,        nullable=False)   # what the student asked
    answer   = db.Column(db.Text,        nullable=True)    # AI's response
    asked_at = db.Column(db.DateTime,    default=datetime.utcnow)

    @property
    def is_expired(self):
        """True if this doubt is older than 7 days."""
        return datetime.utcnow() > self.asked_at + timedelta(days=7)

    @property
    def time_ago(self):
        """Human-readable time: '2h ago', '3d ago', 'just now'."""
        diff    = datetime.utcnow() - self.asked_at
        seconds = diff.total_seconds()
        if seconds < 60:      return "just now"
        if seconds < 3600:    return f"{int(seconds // 60)}m ago"
        if seconds < 86400:   return f"{int(seconds // 3600)}h ago"
        if seconds < 604800:  return f"{int(seconds // 86400)}d ago"
        return self.asked_at.strftime("%d %b")

    def __repr__(self):
        return f"<Doubt [{self.subject}] user={self.user_id}>"


# ============================================================
#  TABLE 3 — TOPIC STRENGTHS
#  Created when: a doubt is saved (auto-created if missing)
#  Updated when: a doubt is saved OR an interview answer is scored
#
#  Score logic (0–100 scale):
#    Every doubt  → score −5  (student needed help, topic is weak)
#    Every correct interview answer (≥7/10) → score +8
#    Every wrong   interview answer (<7/10) → score −3
#    Score clamped to 0–100 always.
#
#  Strength labels:
#    0–39   → "weak"     (🔴 lots of doubts, low interview scores)
#    40–69  → "learning" (🟡 improving but not consistent yet)
#    70–100 → "strong"   (🟢 confident, few doubts, high scores)
# ============================================================

class TopicStrength(db.Model):
    __tablename__ = "topic_strengths"

    id         = db.Column(db.Integer,     primary_key=True)
    user_id    = db.Column(db.Integer,     db.ForeignKey("users.id"), nullable=False)
    subject    = db.Column(db.String(20),  nullable=False)   # "DSA" | "DBMS" | "OS" | "CN"
    topic      = db.Column(db.String(100), nullable=False)   # e.g. "Dynamic Programming"
    score      = db.Column(db.Float,       default=50.0)     # starts neutral at 50
    doubt_count = db.Column(db.Integer,    default=0)        # total doubts on this topic
    correct_count = db.Column(db.Integer,  default=0)        # interview Q's answered well
    updated_at = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint — one row per user+subject+topic combination
    __table_args__ = (
        db.UniqueConstraint("user_id", "subject", "topic", name="uq_user_subject_topic"),
    )

    @property
    def strength(self):
        """Returns 'weak', 'learning', or 'strong' based on score."""
        if self.score >= 70:  return "strong"
        if self.score >= 40:  return "learning"
        return "weak"

    @property
    def strength_emoji(self):
        return {"strong": "🟢", "learning": "🟡", "weak": "🔴"}[self.strength]

    @property
    def pct(self):
        """Score as integer percentage — used for progress bars."""
        return int(self.score)

    def __repr__(self):
        return f"<TopicStrength [{self.subject}/{self.topic}] score={self.score:.1f} user={self.user_id}>"


# ============================================================
#  TABLE 4 — INTERVIEW SESSIONS
#  Created when: student clicks "Generate Interview"
#  Updated when: student finishes — completed_at + score set
# ============================================================

class InterviewSession(db.Model):
    __tablename__ = "interview_sessions"

    id           = db.Column(db.Integer,    primary_key=True)
    user_id      = db.Column(db.Integer,    db.ForeignKey("users.id"), nullable=False)
    session_type = db.Column(db.String(20), nullable=False)   # "weak" | "mixed" | "theory" | "practical"
    score        = db.Column(db.Float,      nullable=True)    # average score 0–10 after completion
    started_at   = db.Column(db.DateTime,   default=datetime.utcnow)
    completed_at = db.Column(db.DateTime,   nullable=True)    # None = not finished yet

    # One session → many questions
    questions = db.relationship("Question", backref="session", lazy=True, cascade="all, delete-orphan")

    @property
    def is_completed(self):
        return self.completed_at is not None

    @property
    def duration_minutes(self):
        """How long the interview took, in minutes."""
        if self.completed_at:
            diff = self.completed_at - self.started_at
            return round(diff.total_seconds() / 60, 1)
        return None

    @property
    def formatted_score(self):
        return f"{self.score:.1f}/10" if self.score is not None else "—"

    def __repr__(self):
        return f"<InterviewSession [{self.session_type}] user={self.user_id} score={self.score}>"


# ============================================================
#  TABLE 5 — QUESTIONS
#  Created when: each question is shown during a mock interview
#  Updated when: student submits answer — user_answer, score, feedback set
#  Also updates topic_strengths after scoring.
# ============================================================

class Question(db.Model):
    __tablename__ = "questions"

    id          = db.Column(db.Integer,     primary_key=True)
    session_id  = db.Column(db.Integer,     db.ForeignKey("interview_sessions.id"), nullable=False)
    subject     = db.Column(db.String(20),  nullable=False)   # "DSA" | "DBMS" | "OS" | "CN"
    topic       = db.Column(db.String(100), nullable=False)   # e.g. "Binary Trees"
    question    = db.Column(db.Text,        nullable=False)   # full question text
    user_answer = db.Column(db.Text,        nullable=True)    # what student typed
    score       = db.Column(db.Float,       nullable=True)    # AI score 0–10
    feedback    = db.Column(db.Text,        nullable=True)    # AI feedback text
    asked_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    @property
    def is_answered(self):
        return self.user_answer is not None

    @property
    def is_correct(self):
        """Score ≥ 7 is considered a correct/strong answer."""
        return self.score is not None and self.score >= 7.0

    def __repr__(self):
        return f"<Question [{self.subject}/{self.topic}] session={self.session_id} score={self.score}>"