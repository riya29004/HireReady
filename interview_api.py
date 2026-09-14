import json
import os
import re

import requests
from flask import Blueprint, jsonify, request, session

from database.queries import get_weak_topics, save_question, submit_answer


interview_bp = Blueprint("interview", __name__)

API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b").strip()
MAX_TOKENS = 2048


SUBJECT_LABELS = {
    "dsa": "Data Structures & Algorithms",
    "dbms": "Database Management Systems",
    "os": "Operating Systems",
    "cn": "Computer Networks",
}


FALLBACK_QUESTIONS = {
    "dsa": [
        "Explain the difference between BFS and DFS with a use case for each.",
        "What is dynamic programming? Explain with an example.",
        "How does QuickSort work? What is its best, average, and worst case complexity?",
        "Explain the two-pointer technique and when you would use it.",
        "What is a hash table and how does it handle collisions?",
    ],
    "dbms": [
        "What are the ACID properties of a transaction?",
        "Explain the difference between clustered and non-clustered indexes.",
        "What is normalisation? Explain 1NF, 2NF, and 3NF.",
        "Describe the different types of SQL JOINs with examples.",
        "What is a deadlock in databases? How can it be prevented?",
    ],
    "os": [
        "Explain the difference between a process and a thread.",
        "What are the four necessary conditions for a deadlock?",
        "How does paging work in memory management?",
        "What is a semaphore? How does it differ from a mutex?",
        "Explain the Round Robin CPU scheduling algorithm.",
    ],
    "cn": [
        "Explain the TCP 3-way handshake in detail.",
        "What is the difference between TCP and UDP?",
        "Describe the OSI model and the function of each layer.",
        "How does DNS work? Walk through a URL resolution.",
        "What is subnetting and why is it used?",
    ],
}


# Changed: infer a concrete topic label from an interview question so progress/gap analysis can use real weak topics.
INTERVIEW_TOPIC_LABELS = {
    "dsa": [
        ("binary search", "Binary Search"),
        ("bst", "Binary Search Trees"),
        ("binary search tree", "Binary Search Trees"),
        ("dynamic programming", "Dynamic Programming"),
        ("linked list", "Linked Lists"),
        ("tree", "Trees"),
        ("graph", "Graphs"),
        ("heap", "Heaps"),
        ("hash", "Hashing"),
        ("dfs", "DFS"),
        ("bfs", "BFS"),
        ("sort", "Sorting"),
        ("search", "Searching"),
        ("recursion", "Recursion"),
    ],
    "dbms": [
        ("join", "SQL Joins"),
        ("sql", "SQL"),
        ("acid", "ACID Properties"),
        ("transaction", "Transactions"),
        ("index", "Indexing"),
        ("normalisation", "Normalization"),
        ("normalization", "Normalization"),
        ("deadlock", "Deadlocks"),
    ],
    "os": [
        ("deadlock", "Deadlocks"),
        ("semaphore", "Semaphores"),
        ("mutex", "Mutex"),
        ("paging", "Paging"),
        ("segmentation", "Segmentation"),
        ("virtual memory", "Virtual Memory"),
        ("process", "Processes"),
        ("thread", "Threads"),
        ("scheduling", "CPU Scheduling"),
    ],
    "cn": [
        ("tcp", "TCP"),
        ("udp", "UDP"),
        ("dns", "DNS"),
        ("osi", "OSI Model"),
        ("subnet", "Subnetting"),
        ("routing", "Routing"),
        ("http", "HTTP/HTTPS"),
        ("https", "HTTP/HTTPS"),
        ("handshake", "TCP Handshake"),
    ],
}


def _strip_code_fences(text):
    text = (text or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1].strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return text.strip()


# Changed: derive a topic name from the interview question instead of storing only the generic subject label.
def _infer_interview_topic(subject, question):
    text = (question or "").lower()
    for keyword, label in INTERVIEW_TOPIC_LABELS.get(subject, []):
        if keyword in text:
            return label
    return SUBJECT_LABELS.get(subject, subject.upper())


def _call_groq(prompt, max_tokens):
    if not API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set.")

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "max_tokens": max_tokens,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return _strip_code_fences(data["choices"][0]["message"]["content"])


def get_fallback_questions(subjects, count):
    subjects = subjects or ["dsa", "dbms", "os", "cn"]
    clean_subjects = [str(sub).lower() for sub in subjects if str(sub).lower() in SUBJECT_LABELS]
    if not clean_subjects:
        clean_subjects = ["dsa", "dbms", "os", "cn"]

    questions = []
    per_subject = max(1, count // len(clean_subjects))

    # Changed: restore the full fallback builder that had been truncated.
    for sub in clean_subjects:
        qs = FALLBACK_QUESTIONS.get(sub, FALLBACK_QUESTIONS["dsa"])
        for q in qs[:per_subject]:
            questions.append({"subject": sub, "question": q})
            if len(questions) >= count:
                return questions[:count]

    # Changed: fill remaining slots round-robin so we always return the requested count.
    idx = 0
    while len(questions) < count:
        sub = clean_subjects[idx % len(clean_subjects)]
        pool = FALLBACK_QUESTIONS.get(sub, FALLBACK_QUESTIONS["dsa"])
        q = pool[(len(questions) // len(clean_subjects)) % len(pool)]
        questions.append({"subject": sub, "question": q})
        idx += 1

    return questions[:count]


# Changed: helper to support weak-topic based interviews while still allowing subject customisation.
def _resolve_interview_subjects(raw_subjects, iv_type):
    subjects = [str(sub).lower() for sub in (raw_subjects or []) if str(sub).lower() in SUBJECT_LABELS]
    if subjects:
        return subjects

    if iv_type == "weak" and "user_id" in session:
        weak_topics = get_weak_topics(session["user_id"])
        weak_subjects = []
        for item in weak_topics:
            name = str(item.get("name", "")).lower()
            for sub in SUBJECT_LABELS:
                if sub in name and sub not in weak_subjects:
                    weak_subjects.append(sub)
        if weak_subjects:
            return weak_subjects

    return ["dsa", "dbms", "os", "cn"]


# Changed: add strict guardrails so obviously weak answers cannot receive inflated scores.
def _apply_strict_score_guardrails(user_answer, score):
    answer = (user_answer or "").strip().lower()

    very_weak_phrases = {
        "idk", "i dont know", "i don't know", "dont know", "don't know",
        "no idea", "not sure", "skip", "pass", "n/a", "na", "maybe",
    }

    if not answer:
        return 0.0

    if answer in very_weak_phrases:
        return min(score, 1.0)

    if len(answer.split()) <= 2 and any(phrase in answer for phrase in very_weak_phrases):
        return min(score, 1.0)

    if len(answer.split()) < 6:
        return min(score, 3.0)

    return score


# Changed: extract simple meaningful tokens from text for relevance checks.
def _tokenize_meaningful_words(text):
    words = re.findall(r"[a-zA-Z]{3,}", (text or "").lower())
    stop_words = {
        "the", "and", "for", "that", "this", "with", "from", "into", "your", "you",
        "are", "was", "were", "have", "has", "had", "what", "when", "where", "which",
        "write", "function", "check", "given", "valid", "they", "them", "then", "than",
        "there", "their", "about", "would", "should", "could", "explain", "using",
    }
    return {word for word in words if word not in stop_words}


# Changed: force zero for irrelevant or random answers that do not match the question/topic.
def _apply_relevance_guardrails(question, user_answer, subject, score):
    answer = (user_answer or "").strip().lower()
    if not answer:
        return 0.0

    # Random/noise-like short answers should be zero.
    if len(answer) <= 4:
        return 0.0

    answer_words = _tokenize_meaningful_words(answer)
    question_words = _tokenize_meaningful_words(question)

    subject_keywords = {
        "dsa": {"array", "linked", "list", "stack", "queue", "tree", "graph", "heap", "hash", "binary", "bst", "node", "search", "sort", "dfs", "bfs", "recursion"},
        "dbms": {"sql", "table", "query", "join", "index", "transaction", "acid", "normalization", "normalisation", "schema", "database", "key"},
        "os": {"process", "thread", "memory", "paging", "deadlock", "mutex", "semaphore", "scheduler", "scheduling", "cpu", "virtual"},
        "cn": {"tcp", "udp", "dns", "ip", "routing", "subnet", "packet", "frame", "http", "https", "socket", "network"},
    }.get(subject, set())

    overlap = answer_words.intersection(question_words.union(subject_keywords))

    # If the answer has no meaningful overlap with the question/topic, treat it as irrelevant.
    if answer_words and not overlap:
        return 0.0

    # Very tiny overlap with a longer random answer should still be heavily penalized.
    if len(answer_words) >= 3 and len(overlap) == 1:
        return min(score, 1.0)

    return score


# Changed: restore the generate route that had gone missing from this file.
@interview_bp.route("/api/interview/generate", methods=["POST"])
def generate_questions():
    if "user_email" not in session:
        return jsonify({"error": "Unauthorised"}), 401

    data = request.get_json(silent=True) or {}
    difficulty = str(data.get("difficulty", "medium")).lower()
    iv_type = str(data.get("type", "mixed")).lower()

    try:
        count = min(15, max(3, int(data.get("count", 5))))
    except (TypeError, ValueError):
        count = 5

    subjects = _resolve_interview_subjects(data.get("subjects"), iv_type)
    subject_names = ", ".join(SUBJECT_LABELS.get(sub, sub.upper()) for sub in subjects)
    type_guidance = {
        "mixed": "Mix of theoretical concept questions and practical problem-solving questions.",
        "theory": "Focus only on theoretical conceptual questions, definitions, comparisons, and explanations.",
        "practical": "Focus only on practical questions, coding problems, scenarios, and applied reasoning.",
        "weak": "Focus more on the user's weaker areas and ask targeted placement-style questions.",
    }.get(iv_type, "Mix of theoretical and practical questions.")

    prompt = f"""You are generating interview questions for a {difficulty}-level CS placement interview.
Subjects to cover: {subject_names}
Total questions needed: {count}
Question type: {type_guidance}

Rules:
- Distribute questions evenly across the selected subjects.
- Each question must be clear, specific, and interview-appropriate.
- Difficulty: {difficulty} (easy=basic definitions/concepts, medium=application/comparison, hard=deep internals/edge cases).
- Do not number the questions.
- Return only a valid JSON array. No explanation, no markdown, no extra text.

Return format:
[
  {{"subject": "dsa", "question": "Explain the difference between BFS and DFS."}},
  {{"subject": "dbms", "question": "What are the ACID properties of a transaction?"}}
]

Generate exactly {count} questions now."""

    try:
        raw = _call_groq(prompt, MAX_TOKENS)
        questions = json.loads(raw)

        valid = [
            {
                "subject": str(q.get("subject", "dsa")).lower(),
                "question": str(q.get("question", "")).strip(),
            }
            for q in questions
            if isinstance(q, dict) and str(q.get("question", "")).strip()
        ]

        for item in valid:
            if item["subject"] not in SUBJECT_LABELS:
                item["subject"] = subjects[0] if subjects else "dsa"

        if not valid:
            return jsonify({"questions": get_fallback_questions(subjects, count)})

        return jsonify({"questions": valid[:count]})

    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
        return jsonify({"questions": get_fallback_questions(subjects, count)})
    except requests.exceptions.Timeout:
        return jsonify({"questions": get_fallback_questions(subjects, count)})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# Changed: restore the evaluate route that had gone missing from this file.
@interview_bp.route("/api/interview/evaluate", methods=["POST"])
def evaluate_answer():
    if "user_email" not in session:
        return jsonify({"error": "Unauthorised"}), 401

    data = request.get_json(silent=True) or {}
    subject = str(data.get("subject", "dsa")).lower()
    question = str(data.get("question", "")).strip()
    user_answer = str(data.get("userAnswer", "")).strip()
    difficulty = str(data.get("difficulty", "medium")).lower()
    session_id = data.get("sessionId")

    if subject not in SUBJECT_LABELS:
        subject = "dsa"

    subject_label = SUBJECT_LABELS.get(subject, subject.upper())

    # Changed: make the evaluator behave like a strict real interviewer instead of a generous helper.
    prompt = f"""You are an expert {subject_label} interviewer evaluating a candidate's answer.

Question ({difficulty} difficulty): {question}

Candidate's answer:
{user_answer}

Your task:
1. Score the answer from 0 to 10 as a strict interviewer.
2. Write 2 to 3 sentences of constructive feedback: what was correct, what was missing, and what could be improved.
3. Write a concise model answer of 3 to 6 sentences.

Strict scoring rubric:
- 0 to 1: blank answer, "I don't know", irrelevant answer, or clearly wrong answer.
- 2 to 3: very weak answer with only a vague idea and no real explanation.
- 4 to 5: partially correct answer but missing key concepts, depth, or accuracy.
- 6 to 7: mostly correct answer with decent understanding but some gaps.
- 8 to 9: strong, accurate, interview-ready answer with good clarity.
- 10: exceptional answer with complete correctness, clarity, and strong depth.

Important scoring rules:
- Do not reward confidence if the content is weak.
- Do not give high marks for short or generic answers.
- If the candidate says "I don't know", "idk", "not sure", or gives an almost empty answer, the score must be between 0 and 1.
- If the answer misses core concepts required by the question, keep the score below 6.
- Be tough but fair.

Return only valid JSON:
{{
  "score": 7.5,
  "feedback": "Your feedback here.",
  "model_answer": "The ideal answer here."
}}"""

    try:
        raw = _call_groq(prompt, 1024)
        result = json.loads(raw)

        score = float(result.get("score", 5))
        score = max(0.0, min(10.0, score))
        # score = _apply_strict_score_guardrails(user_answer, score)
        score = _apply_strict_score_guardrails(user_answer, score)
        score = _apply_relevance_guardrails(question, user_answer, subject, score)
        feedback = str(result.get("feedback", "No feedback available.")).strip()
        model_answer = str(result.get("model_answer", "No model answer available.")).strip()

        if session_id:
            inferred_topic = _infer_interview_topic(subject, question)
            saved_q = save_question(
                session_id=int(session_id),
                subject=subject,
                # topic=SUBJECT_LABELS.get(subject, subject.upper()),
                topic=inferred_topic,
                question_text=question or "Interview question",
            )
            submit_answer(saved_q.id, user_answer, score, feedback)

        return jsonify(
            {
                "score": score,
                "feedback": feedback,
                "model_answer": model_answer,
            }
        )

    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
        return jsonify(
            {
                "score": 5.0,
                "feedback": "Could not parse evaluation. Your answer has been recorded.",
                "model_answer": "Model answer unavailable for this question.",
            }
        )
    except requests.exceptions.Timeout:
        return jsonify(
            {
                "score": 5.0,
                "feedback": "Evaluation timed out. Please try again.",
                "model_answer": "",
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
