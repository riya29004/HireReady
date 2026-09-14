
from datetime import datetime, timedelta
from collections import Counter
from database.extensions import db
from database.models import User, Doubt, TopicStrength, InterviewSession, Question


# ════════════════════════════════════════════════════════════
#  A. USER QUERIES
# ════════════════════════════════════════════════════════════

def get_user_by_email(email: str):
    """Find a user by email. Returns User object or None."""
    return User.query.filter_by(email=email.lower().strip()).first()


def create_user(name: str, email: str, hashed_password: str):
    """
    Insert a new user. Password must be bcrypt-hashed before calling.
    Returns the new User object (with .id set).
    """
    user = User(
        name     = name.strip(),
        email    = email.lower().strip(),
        password = hashed_password,
    )
    db.session.add(user)
    db.session.commit()
    return user


def email_exists(email: str) -> bool:
    """True if an account with this email already exists."""
    return User.query.filter_by(email=email.lower().strip()).count() > 0


# ════════════════════════════════════════════════════════════
#  B. DOUBT QUERIES
# ════════════════════════════════════════════════════════════

def save_doubt(user_id: int, subject: str, question: str,
               answer: str, topic: str = None):
    """
    Save a doubt and automatically update topic_strengths.
    Called by agents/__init__.py after every AI reply.

    Flow:
      1. Save doubt row
      2. Decrease topic strength score (student needed help = weak signal)
    """
    doubt = Doubt(
        user_id  = user_id,
        subject  = subject.upper(),
        topic    = topic,
        question = question[:2000],   # guard against huge pastes
        answer   = answer[:5000],
    )
    db.session.add(doubt)
    db.session.commit()

    # Auto-update topic strength if topic is tagged
    if topic:
        _on_doubt_recorded(user_id, subject.upper(), topic)

    return doubt


def get_recent_doubts(user_id: int, limit: int = 10, subject: str = None):
    """
    Most recent doubts for a user.
    Optionally filter by subject ("DSA", "DBMS", etc.).
    Returns list of Doubt objects.
    """
    q = Doubt.query.filter_by(user_id=user_id)
    if subject:
        q = q.filter_by(subject=subject.upper())
    return q.order_by(Doubt.asked_at.desc()).limit(limit).all()


def get_doubts_last_7_days(user_id: int):
    """All doubts in the last 7 days — core of weak topic detection."""
    cutoff = datetime.utcnow() - timedelta(days=7)
    return (
        Doubt.query
        .filter(Doubt.user_id == user_id, Doubt.asked_at >= cutoff)
        .order_by(Doubt.asked_at.desc())
        .all()
    )


def get_doubts_last_n_days(user_id: int, days: int = 7):
    """All doubts in the last N days — used by progress report."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    return (
        Doubt.query
        .filter(Doubt.user_id == user_id, Doubt.asked_at >= cutoff)
        .order_by(Doubt.asked_at.desc())
        .all()
    )


def get_weak_topics(user_id: int, min_doubts: int = 2):
    """
    Analyse last 7 days of doubts → find weak topics.
    Returns sorted list (highest doubt count first):
    [{"name": "Dynamic Programming", "doubt_count": 8, "pct": 80}, ...]
    """
    # recent = get_doubts_last_7_days(user_id)
    # tagged = [d.topic for d in recent if d.topic]
    # if not tagged:
    #     return []
    #
    # counts   = Counter(tagged)
    # max_cnt  = max(counts.values())
    # return [
    #     {"name": topic, "doubt_count": cnt, "pct": round((cnt / max_cnt) * 100)}
    #     for topic, cnt in counts.most_common()
    #     if cnt >= min_doubts
    # ]

    # Changed: weak topics now come from actual topic strength evidence from doubts + mock interviews.
    interview_rows = (
        db.session.query(
            Question.topic.label("topic"),
            db.func.count(Question.id).label("interview_count"),
            db.func.avg(Question.score).label("avg_score"),
        )
        .join(InterviewSession, InterviewSession.id == Question.session_id)
        .filter(
            InterviewSession.user_id == user_id,
            InterviewSession.completed_at.isnot(None),
            Question.score.isnot(None),
        )
        .group_by(Question.topic)
        .all()
    )
    interview_map = {
        row.topic: {
            "interview_count": int(row.interview_count or 0),
            "avg_score": float(row.avg_score or 0.0),
        }
        for row in interview_rows
    }

    rows = (
        TopicStrength.query
        .filter_by(user_id=user_id)
        .filter(
            (TopicStrength.doubt_count > 0) |
            (TopicStrength.correct_count > 0) |
            (TopicStrength.score != 50.0)
        )
        .order_by(TopicStrength.score.asc(), TopicStrength.updated_at.desc())
        .all()
    )

    weak = []
    for ts in rows:
        interview_info = interview_map.get(ts.topic, {"interview_count": 0, "avg_score": 0.0})
        interview_count = interview_info["interview_count"]
        avg_score = interview_info["avg_score"]

        if not (ts.doubt_count >= min_doubts or (interview_count > 0 and avg_score < 7.0) or ts.score < 55):
            continue

        evidence_count = max(ts.doubt_count, interview_count)
        weak.append({
            "name": ts.topic,
            "doubt_count": evidence_count,
            "pct": round(100 - ts.score),
        })

    return weak[:6]


def get_total_doubts_this_week(user_id: int) -> int:
    """Count of doubts in the last 7 days."""
    return len(get_doubts_last_7_days(user_id))


def get_subject_doubt_counts(user_id: int, days: int = 7) -> dict:
    """
    Returns {subject: count} for the last N days.
    e.g. {"DSA": 5, "DBMS": 3, "OS": 2, "CN": 2}
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.session.query(Doubt.subject, db.func.count(Doubt.id))
        .filter(Doubt.user_id == user_id, Doubt.asked_at >= cutoff)
        .group_by(Doubt.subject)
        .all()
    )
    base = {"DSA": 0, "DBMS": 0, "OS": 0, "CN": 0}
    for subject, cnt in rows:
        base[subject] = cnt
    return base


def get_daily_activity(user_id: int, days: int = 7) -> list:
    """
    Returns [{"date": "15 Jan", "count": 3}, ...] for heatmap.
    Includes days with zero activity.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.session.query(
            db.func.date(Doubt.asked_at).label("day"),
            db.func.count(Doubt.id).label("cnt")
        )
        .filter(Doubt.user_id == user_id, Doubt.asked_at >= cutoff)
        .group_by(db.func.date(Doubt.asked_at))
        .all()
    )
    by_date = {str(r.day): r.cnt for r in rows}

    result = []
    for i in range(days - 1, -1, -1):
        d     = (datetime.utcnow() - timedelta(days=i)).date()
        label = d.strftime("%d %b")
        result.append({"date": label, "count": by_date.get(str(d), 0)})
    return result


def delete_old_doubts(user_id: int):
    """Delete doubts older than 7 days. Call periodically for cleanup."""
    cutoff = datetime.utcnow() - timedelta(days=7)
    Doubt.query.filter(
        Doubt.user_id == user_id,
        Doubt.asked_at < cutoff
    ).delete()
    db.session.commit()


# ════════════════════════════════════════════════════════════
#  C. TOPIC STRENGTH QUERIES
#  These are called INTERNALLY by save_doubt() and submit_answer().
#  app.py does NOT call these directly.
# ════════════════════════════════════════════════════════════

def _get_or_create_strength(user_id: int, subject: str, topic: str) -> TopicStrength:
    """
    Get existing TopicStrength row, or create one at score=50.
    Internal helper — not called from app.py.
    """
    ts = TopicStrength.query.filter_by(
        user_id=user_id, subject=subject, topic=topic
    ).first()

    if not ts:
        ts = TopicStrength(
            user_id = user_id,
            subject = subject,
            topic   = topic,
            score   = 50.0,   # neutral starting point
        )
        db.session.add(ts)
        db.session.flush()   # get ID without full commit
    return ts


def _on_doubt_recorded(user_id: int, subject: str, topic: str):
    """
    Called automatically after save_doubt().
    Logic: student needed help → score drops by 5.
    Score is always clamped to [0, 100].
    """
    ts = _get_or_create_strength(user_id, subject, topic)
    ts.doubt_count += 1
    ts.score        = max(0.0, ts.score - 5.0)
    ts.updated_at   = datetime.utcnow()
    db.session.commit()


def _on_interview_answer(user_id: int, subject: str, topic: str,
                         interview_score: float):
    """
    Called automatically after submit_answer().
    Logic:
      - Good answer (≥7/10)  → score +8  (student showed understanding)
      - Weak answer (<7/10)  → score −3  (still struggling)
    Score always clamped to [0, 100].
    """
    ts = _get_or_create_strength(user_id, subject, topic)
    if interview_score >= 7.0:
        ts.score        = min(100.0, ts.score + 8.0)
        ts.correct_count += 1
    else:
        ts.score        = max(0.0, ts.score - 3.0)
    ts.updated_at = datetime.utcnow()
    db.session.commit()


def get_all_topic_strengths(user_id: int, subject: str = None) -> list:
    """
    Return all TopicStrength rows for a user.
    Optionally filter by subject.
    Used by progress report gap analysis.
    """
    q = TopicStrength.query.filter_by(user_id=user_id)
    if subject:
        q = q.filter_by(subject=subject.upper())
    return q.order_by(TopicStrength.score.asc()).all()


def get_gap_topics(user_id: int, top_n: int = 6) -> list:
    """
    Return weakest topics for gap analysis using both doubts and mock interview results.
    Returns:
    [{"name": "Dynamic Programming", "subject": "DSA",
      "doubt_count": 2, "interview_count": 3, "pct": 80, "severity": "high", "score": 35.0}, ...]
    """
    rows = (
        TopicStrength.query
        .filter_by(user_id=user_id)
        # Changed: ignore placeholder rows with no doubt history and no interview evidence.
        .filter(
            (TopicStrength.doubt_count > 0) |
            (TopicStrength.correct_count > 0) |
            (TopicStrength.score != 50.0)
        )
        .order_by(TopicStrength.score.asc())
        .all()
    )

    interview_rows = (
        db.session.query(
            Question.topic.label("topic"),
            Question.subject.label("subject"),
            db.func.count(Question.id).label("interview_count"),
            db.func.avg(Question.score).label("avg_score"),
        )
        .join(InterviewSession, InterviewSession.id == Question.session_id)
        .filter(
            InterviewSession.user_id == user_id,
            InterviewSession.completed_at.isnot(None),
            Question.score.isnot(None),
        )
        .group_by(Question.topic, Question.subject)
        .all()
    )

    interview_map = {
        (row.subject, row.topic): {
            "interview_count": int(row.interview_count or 0),
            "avg_score": float(row.avg_score or 0.0),
        }
        for row in interview_rows
    }

    result = []
    for ts in rows:
        interview_info = interview_map.get((ts.subject, ts.topic), {"interview_count": 0, "avg_score": 0.0})
        interview_count = interview_info["interview_count"]
        avg_score = interview_info["avg_score"]

        # Changed: severity is now driven by actual weakness evidence from doubts + mock interview performance.
        if ts.doubt_count >= 3 or (interview_count > 0 and avg_score < 4.0):
            severity = "high"
        elif ts.doubt_count >= 1 or (interview_count > 0 and avg_score < 7.0):
            severity = "medium"
        else:
            severity = "low"

        # Changed: gap percentage now reflects lower score = higher need for improvement.
        gap_pct = round(100 - ts.score)

        result.append({
            "name":        ts.topic,
            "subject":     ts.subject.lower(),
            "doubt_count": ts.doubt_count,
            "interview_count": interview_count,
            "avg_interview_score": round(avg_score, 1) if interview_count else None,
            "pct":         gap_pct,
            "score":       round(ts.score, 1),
            "severity":    severity,
        })

    # Changed: highest-priority weak topics come first based on severity, then score, then evidence count.
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    result.sort(
        key=lambda item: (
            severity_rank.get(item["severity"], 3),
            item["score"],
            -(item["doubt_count"] + item.get("interview_count", 0)),
        )
    )
    return result[:top_n]


# Changed: provide a subject-wise topic strength table for the progress page.
def get_subject_strength_rows(user_id: int) -> list:
    rows = (
        TopicStrength.query
        .filter_by(user_id=user_id)
        .filter(
            (TopicStrength.doubt_count > 0) |
            (TopicStrength.correct_count > 0) |
            (TopicStrength.score != 50.0)
        )
        .order_by(TopicStrength.subject.asc(), TopicStrength.score.asc(), TopicStrength.topic.asc())
        .all()
    )

    result = []
    for ts in rows:
        if ts.score >= 75:
            status = "Strong"
        elif ts.score >= 55:
            status = "Learning"
        elif ts.score >= 35:
            status = "Weak"
        else:
            status = "Very Weak"

        result.append({
            "subject": ts.subject,
            "topic": ts.topic,
            "recent_doubts": ts.doubt_count,
            "status": status,
            "score": round(ts.score, 1),
        })

    return result


def get_subject_coverage(user_id: int) -> dict:
    """
    Returns estimated coverage % per subject based on
    unique topics in topic_strengths with score >= 40.
    """
    # Total known topics per subject (estimate)
    TOPIC_TOTALS = {"DSA": 10, "DBMS": 8, "OS": 10, "CN": 9}

    result = {}
    for sub, total in TOPIC_TOTALS.items():
        covered = (
            TopicStrength.query
            .filter_by(user_id=user_id, subject=sub)
            .filter(TopicStrength.score >= 40)
            .count()
        )
        pct = min(100, round((covered / total) * 100))
        result[sub.lower()] = {
            "pct":   pct,
            "label": f"{covered} topic{'s' if covered != 1 else ''} covered",
        }
    return result


# ════════════════════════════════════════════════════════════
#  D. INTERVIEW SESSION QUERIES
# ════════════════════════════════════════════════════════════

def create_interview_session(user_id: int, session_type: str = "mixed"):
    """
    Start a new interview session row.
    Returns the InterviewSession object (with .id set).
    """
    iv = InterviewSession(
        user_id      = user_id,
        session_type = session_type,
    )
    db.session.add(iv)
    db.session.commit()
    return iv


def complete_interview_session(session_id: int, avg_score: float):
    """
    Mark a session as complete and store the average score.
    Called after the last question is answered.
    """
    iv = InterviewSession.query.get(session_id)
    if iv:
        iv.completed_at = datetime.utcnow()
        iv.score        = round(avg_score, 2)
        db.session.commit()
    return iv


def get_interviews_done(user_id: int) -> int:
    """Total completed interviews for a user."""
    return (
        InterviewSession.query
        .filter_by(user_id=user_id)
        .filter(InterviewSession.completed_at.isnot(None))
        .count()
    )


def get_interview_history(user_id: int, limit: int = 7) -> list:
    """
    Recent completed interviews as list of dicts.
    Used by the score history chart on the progress page.
    """
    rows = (
        InterviewSession.query
        .filter_by(user_id=user_id)
        .filter(InterviewSession.completed_at.isnot(None))
        .order_by(InterviewSession.started_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "score":    round(iv.score, 1) if iv.score else 0,
            "subjects": iv.session_type.replace("_", " + ").upper(),
            "date":     iv.started_at.strftime("%d %b") if iv.started_at else "",
        }
        for iv in rows
    ]


def get_avg_interview_score(user_id: int, days: int = 7) -> float:
    """Average interview score over the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = (
        db.session.query(db.func.avg(InterviewSession.score))
        .filter(
            InterviewSession.user_id == user_id,
            InterviewSession.completed_at.isnot(None),
            InterviewSession.started_at >= cutoff,
        )
        .scalar()
    )
    return round(float(result), 1) if result else 0.0


# ════════════════════════════════════════════════════════════
#  E. QUESTION QUERIES
# ════════════════════════════════════════════════════════════

def save_question(session_id: int, subject: str,
                  topic: str, question_text: str):
    """
    Save one interview question row.
    Returns the Question object (with .id set).
    Called when each question is displayed to the student.
    """
    q = Question(
        session_id = session_id,
        subject    = subject.upper(),
        topic      = topic,
        question   = question_text,
    )
    db.session.add(q)
    db.session.commit()
    return q


def submit_answer(question_id: int, user_answer: str,
                  score: float, feedback: str):
    """
    Save student's answer + AI score + AI feedback for one question.
    Automatically updates topic_strengths after saving.
    Called after every /api/interview/evaluate response.
    """
    q = Question.query.get(question_id)
    if not q:
        return None

    q.user_answer = user_answer[:4000]
    q.score       = round(score, 2)
    q.feedback    = feedback[:3000]
    db.session.commit()

    # Auto-update topic strength for this question's topic
    iv = InterviewSession.query.get(q.session_id)
    if iv:
        _on_interview_answer(iv.user_id, q.subject, q.topic, score)

    return q


# ════════════════════════════════════════════════════════════
#  F. DASHBOARD SUMMARY
#  Single call — returns everything dashboard.html needs.
#  app.py calls this once in the /dashboard route.
# ════════════════════════════════════════════════════════════

def get_dashboard_data(user_id: int) -> dict:
    """
    Returns all data needed for dashboard in one call.

    Keys returned:
      recent_doubts   → list of dicts (subject, question, time_ago)
      weak_topics     → list of dicts (name, doubt_count, pct)
      weak_count      → int
      total_doubts    → int (last 7 days)
      interviews_done → int (all time)
      subjects_active → int (distinct subjects asked in last 7 days)
    """
    recent_doubts   = get_recent_doubts(user_id, limit=5)
    weak_topics     = get_weak_topics(user_id)
    interviews_done = get_interviews_done(user_id)
    total_doubts    = get_total_doubts_this_week(user_id)

    # Distinct subjects from the recent doubts
    subjects_active = len(set(d.subject for d in recent_doubts)) or 0

    formatted_doubts = [
        {
            "subject":  d.subject,
            "question": d.question,
            "time_ago": d.time_ago,
        }
        for d in recent_doubts
    ]

    return {
        "recent_doubts":   formatted_doubts,
        "weak_topics":     weak_topics,
        "weak_count":      len(weak_topics),
        "total_doubts":    total_doubts,
        "interviews_done": interviews_done,
        "subjects_active": subjects_active,
    }


# ════════════════════════════════════════════════════════════
#  G. PROGRESS REPORT SUMMARY
#  Single call for /api/progress — returns everything
#  progress.js needs to render the full analytics page.
# ════════════════════════════════════════════════════════════

def get_progress_data(user_id: int, days: int = 7) -> dict:
    """
    Returns all data for the progress report page.
    Called by the /api/progress Flask route.
    """
    subject_counts  = get_subject_doubt_counts(user_id, days)
    recent_doubts   = get_recent_doubts(user_id, limit=10)
    score_history   = get_interview_history(user_id, limit=7)
    avg_score       = get_avg_interview_score(user_id, days)
    interviews_done = InterviewSession.query.filter(
        InterviewSession.user_id == user_id,
        InterviewSession.completed_at.isnot(None),
        InterviewSession.started_at >= datetime.utcnow() - timedelta(days=days)
    ).count()
    activity        = get_daily_activity(user_id, days)
    streak          = get_streak(user_id)
    gap_topics      = get_gap_topics(user_id, top_n=6)
    strength_rows   = get_subject_strength_rows(user_id)
    coverage        = get_subject_coverage(user_id)
    total_doubts    = sum(subject_counts.values())

    return {
        "total_doubts":    total_doubts,
        "interviews_done": interviews_done,
        "avg_score":       avg_score,
        "streak":          streak,
        "subject_doubts":  {k.lower(): v for k, v in subject_counts.items()},
        "score_history":   score_history,
        "gap_topics":      gap_topics,
        "recent_doubts": [
            {
                "subject":  d.subject,
                "question": d.question,
                "time_ago": d.time_ago,
            }
            for d in recent_doubts
        ],
        "strength_rows": strength_rows,
        "coverage":  coverage,
        "activity":  activity,
    }


# ════════════════════════════════════════════════════════════
#  H. STREAK CALCULATOR
#  Counts consecutive days the user asked at least one doubt.
# ════════════════════════════════════════════════════════════

def get_streak(user_id: int) -> int:
    """
    Returns current consecutive-day study streak.

    Logic:
      - Walk backwards from today
      - If the user asked ≥1 doubt that day → streak continues
      - First day with no doubts → streak ends
      - Allows "today" to count even if the day isn't over yet
    """
    rows = (
        db.session.query(db.func.date(Doubt.asked_at).label("day"))
        .filter(Doubt.user_id == user_id)
        .group_by(db.func.date(Doubt.asked_at))
        .order_by(db.text("day DESC"))
        .limit(60)   # look back up to 60 days max
        .all()
    )

    if not rows:
        return 0

    # Convert to a set of date objects for fast lookup
    active_days = set()
    for row in rows:
        if isinstance(row.day, str):
            active_days.add(datetime.strptime(row.day, "%Y-%m-%d").date())
        else:
            active_days.add(row.day)

    today   = datetime.utcnow().date()
    streak  = 0
    current = today

    while True:
        if current in active_days:
            streak  += 1
            current  = current - timedelta(days=1)
        elif current == today:
            # Haven't asked anything today yet — check yesterday to not break streak
            current = current - timedelta(days=1)
            if current not in active_days:
                break
        else:
            break

    return streak
