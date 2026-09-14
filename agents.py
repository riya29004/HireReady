import os
from groq import Groq
from flask import Blueprint, request, jsonify, session
from database.queries import save_doubt

agents_bp = Blueprint('agents', __name__)

# ── API config ────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '').strip()
# Groq retired the previous Llama model; keep the model configurable through
# GROQ_MODEL while using the current supported model by default.
MODEL        = os.environ.get('GROQ_MODEL', 'openai/gpt-oss-20b').strip()
MAX_TOKENS   = 1024


# ============================================================
#  AGENT SYSTEM PROMPTS
#  Each prompt defines the agent's role, style, and focus area.
# ============================================================

AGENT_PROMPTS = {

    'dsa': """You are the DSA Agent for HireReady — an expert Data Structures & Algorithms tutor
specialising in placement and technical interview preparation for CS students.

Your personality: patient, encouraging, precise, and interview-focused.

Your responsibilities:
- Explain data structures (arrays, linked lists, stacks, queues, trees, graphs, heaps, tries, hash maps).
- Explain algorithm paradigms: sorting, searching, dynamic programming, greedy, backtracking, divide & conquer.
- Walk through problems step-by-step: understand → approach → code → complexity analysis.
- Always state Time Complexity and Space Complexity using Big-O notation.
- Write clean pseudocode or Python/Java/C++ code snippets when helpful.
- For DP problems: define subproblem, recurrence, base case, and optimisation.
- Give interview tips: when to use which data structure, common patterns (sliding window, two-pointer, BFS/DFS templates).

Formatting rules:
- Use **bold** for key terms.
- Use ``` code blocks ``` for code.
- Use numbered steps for walkthroughs.
- Be concise but complete — interview answers should be 2-3 minutes spoken.
- Never give off-topic answers. If asked about non-DSA topics, politely redirect.
""",

    'dbms': """You are the DBMS Agent for HireReady — a Database Management Systems expert for CS placement preparation.

Your personality: precise, structured, and example-driven.

Your responsibilities:
- Explain relational database concepts: tables, keys, constraints, ER diagrams.
- Cover SQL thoroughly: SELECT, JOIN (all types), GROUP BY, HAVING, subqueries, window functions, indexes.
- Explain normalisation: 1NF, 2NF, 3NF, BCNF — with examples of anomalies and how to fix them.
- Cover transactions: ACID properties, isolation levels (Read Uncommitted → Serializable), concurrency issues (dirty read, phantom read, lost update).
- Explain indexing: B-tree, hash index, clustered vs non-clustered.
- Cover NoSQL briefly: document, key-value, column, graph databases vs RDBMS.
- Give interview tips: commonly asked SQL puzzles, how to explain normalisation, ACID in simple terms.

Formatting rules:
- Use **bold** for key terms.
- Use ``` SQL code blocks ``` for queries.
- Always show example data when explaining concepts.
- Keep answers interview-focused — practical, clear, with real-world analogies.
- Stay strictly on DBMS topics.
""",

    'os': """You are the OS Agent for HireReady — an Operating Systems expert for CS placement interviews.

Your personality: methodical, thorough, and analogy-friendly.

Your responsibilities:
- Explain process management: process vs thread, PCB, process states (New → Ready → Running → Waiting → Terminated).
- Cover CPU scheduling: FCFS, SJF, Priority, Round Robin, MLFQ — with examples and Gantt charts in text form.
- Explain synchronisation: race conditions, critical sections, mutex, semaphore, monitors, deadlock (Coffman conditions + prevention/avoidance/detection).
- Cover memory management: paging, segmentation, page tables, TLB, virtual memory, page replacement (FIFO, LRU, Optimal).
- Explain file systems: inodes, directory structure, file allocation (contiguous, linked, indexed).
- Cover I/O: disk scheduling (FCFS, SSTF, SCAN, C-SCAN), interrupt handling, DMA.
- Give interview tips: how to answer deadlock questions, how to explain virtual memory simply.

Formatting rules:
- Use **bold** for key terms.
- Use step-by-step numbered lists for processes and algorithms.
- Use analogies (e.g. mutex = single-key locker, semaphore = counting permits).
- Stay strictly on OS topics.
""",

    'cn': """You are the CN Agent for HireReady — a Computer Networks expert for CS placement interviews.

Your personality: clear, layered (like the OSI model!), and diagram-friendly.

Your responsibilities:
- Explain the OSI model (all 7 layers) and TCP/IP model (4 layers) — functions, protocols, PDUs at each layer.
- Cover the Transport layer: TCP vs UDP, TCP 3-way handshake, 4-way termination, flow control (sliding window), congestion control (slow start, AIMD).
- Explain the Network layer: IP addressing (IPv4/IPv6), subnetting, CIDR, routing algorithms (Dijkstra / link-state, distance vector / Bellman-Ford).
- Cover Application layer protocols: HTTP/HTTPS, DNS, DHCP, FTP, SMTP.
- Explain the Data Link layer: MAC addressing, ARP, Ethernet, framing, error detection (CRC, checksum).
- Cover network security basics: SSL/TLS handshake, firewalls, VPN, symmetric vs asymmetric encryption.
- Give interview tips: how to walk through "what happens when you type a URL", common TCP/IP questions.

Formatting rules:
- Use **bold** for protocols and key terms.
- Use numbered lists for multi-step processes (handshakes, URL resolution).
- Use analogies where helpful (TCP = certified mail, UDP = postcards).
- Stay strictly on Computer Networks topics.
"""
}

# Changed: add keyword guardrails so each subject bot redirects clearly when the question belongs elsewhere.
SUBJECT_KEYWORDS = {
    'dsa': [
        'array', 'linked list', 'stack', 'queue', 'tree', 'graph', 'heap', 'hash',
        'dynamic programming', 'dp', 'recursion', 'backtracking', 'greedy',
        'binary search', 'bfs', 'dfs', 'trie', 'segment tree', 'sliding window',
        'two pointer', 'kruskal', 'prim', 'dijkstra', 'sort', 'search',
    ],
    'dbms': [
        'sql', 'join', 'normalisation', 'normalization', 'acid', 'transaction',
        'index', 'schema', 'primary key', 'foreign key', 'er diagram', 'bcnf',
        '1nf', '2nf', '3nf', 'query', 'rollback', 'commit', 'nosql',
    ],
    'os': [
        'process', 'thread', 'cpu scheduling', 'round robin', 'fcfs', 'sjf',
        'mutex', 'semaphore', 'deadlock', 'paging', 'segmentation',
        'virtual memory', 'page fault', 'context switch', 'pcb', 'thrashing',
        'file system', 'inode', 'interrupt',
    ],
    'cn': [
        'tcp', 'udp', 'osi', 'tcp/ip', 'dns', 'http', 'https', 'routing',
        'subnet', 'subnetting', 'ip address', 'ipv4', 'ipv6', 'arp', 'icmp',
        'tls', 'ssl', 'handshake', 'socket', 'port', 'packet', 'frame',
    ],
}

# Changed: map common question keywords to dashboard-friendly topic labels for weak-topic tracking.
TOPIC_LABELS = {
    'dsa': [
        ('dynamic programming', 'Dynamic Programming'),
        ('binary search', 'Binary Search'),
        ('sliding window', 'Sliding Window'),
        ('two pointer', 'Two Pointer Technique'),
        ('linked list', 'Linked Lists'),
        ('stack', 'Stacks'),
        ('queue', 'Queues'),
        ('tree', 'Trees'),
        ('graph', 'Graphs'),
        ('heap', 'Heaps'),
        ('hash', 'Hashing'),
        ('recursion', 'Recursion'),
        ('greedy', 'Greedy Algorithms'),
        ('dfs', 'DFS'),
        ('bfs', 'BFS'),
        ('sort', 'Sorting'),
        ('search', 'Searching'),
    ],
    'dbms': [
        ('sql', 'SQL'),
        ('join', 'SQL Joins'),
        ('normalisation', 'Normalization'),
        ('normalization', 'Normalization'),
        ('acid', 'ACID Properties'),
        ('transaction', 'Transactions'),
        ('index', 'Indexing'),
        ('schema', 'Schema Design'),
        ('primary key', 'Keys and Constraints'),
        ('foreign key', 'Keys and Constraints'),
        ('bcnf', 'Normalization'),
    ],
    'os': [
        ('process', 'Processes'),
        ('thread', 'Threads'),
        ('deadlock', 'Deadlocks'),
        ('semaphore', 'Semaphores'),
        ('mutex', 'Mutex'),
        ('paging', 'Paging'),
        ('segmentation', 'Segmentation'),
        ('virtual memory', 'Virtual Memory'),
        ('page fault', 'Page Faults'),
        ('scheduling', 'CPU Scheduling'),
        ('context switch', 'Context Switching'),
        ('file system', 'File Systems'),
    ],
    'cn': [
        ('tcp', 'TCP'),
        ('udp', 'UDP'),
        ('dns', 'DNS'),
        ('http', 'HTTP/HTTPS'),
        ('https', 'HTTP/HTTPS'),
        ('osi', 'OSI Model'),
        ('routing', 'Routing'),
        ('subnet', 'Subnetting'),
        ('ip', 'IP Addressing'),
        ('tls', 'TLS/SSL'),
        ('ssl', 'TLS/SSL'),
        ('handshake', 'TCP Handshake'),
    ],
}

# Changed: central coordinator prompt used to classify the user's latest question before any bot answers.
COORDINATOR_PROMPT = """You are the central coordinator for HireReady.
Your job is to classify a student's latest question into exactly one subject:
- dsa
- dbms
- os
- cn
- unclear

Rules:
- Return only one lowercase token from this list: dsa, dbms, os, cn, unclear
- Choose dsa for algorithms, data structures, coding problem solving, complexity
- Choose dbms for SQL, normalization, transactions, indexes, ER models
- Choose os for processes, threads, scheduling, deadlocks, memory management, file systems
- Choose cn for TCP/IP, OSI, DNS, routing, subnetting, HTTP/HTTPS, networking protocols
- If the question is too vague or mixed across subjects, return unclear
"""


# Changed: return the better-matching subject when the current bot should redirect.
def _detect_subject_mismatch(subject, user_text):
    text = (user_text or '').lower()
    if not text:
        return None

    scores = {
        sub: sum(1 for kw in keywords if kw in text)
        for sub, keywords in SUBJECT_KEYWORDS.items()
    }

    current_score = scores.get(subject, 0)
    best_subject = max(scores, key=scores.get)
    best_score = scores.get(best_subject, 0)
    other_scores = {
        sub: score
        for sub, score in scores.items()
        if sub != subject and score > 0
    }

    # If the question mixes the current subject with another subject, keep the
    # current bot strict instead of letting the model answer the off-topic part.
    if current_score > 0 and other_scores:
        return max(other_scores, key=other_scores.get)

    if best_subject != subject and best_score > 0 and current_score == 0:
        return best_subject

    return None


# Changed: center coordinator decides whether the requested bot should answer or redirect.
def _coordinator_route_subject(client, requested_subject, user_text):
    keyword_mismatch = _detect_subject_mismatch(requested_subject, user_text)
    if keyword_mismatch:
        return keyword_mismatch

    text = (user_text or '').lower()
    requested_subject_score = sum(
        1 for kw in SUBJECT_KEYWORDS.get(requested_subject, [])
        if kw in text
    )
    other_subject_score = sum(
        1
        for sub, keywords in SUBJECT_KEYWORDS.items()
        if sub != requested_subject
        for kw in keywords
        if kw in text
    )

    if requested_subject_score > 0 and other_subject_score == 0:
        return None

    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=8,
            temperature=0,
            messages=[
                {"role": "system", "content": COORDINATOR_PROMPT},
                {"role": "user", "content": user_text},
            ],
        )
        decision = (response.choices[0].message.content or '').strip().lower()
        if decision in AGENT_PROMPTS and decision != requested_subject:
            return decision
    except Exception:
        # If coordinator classification fails, fall back to the current bot instead of breaking chat.
        pass

    return None


# Changed: infer a topic label from the user's question so weak-topic cards can populate on the dashboard.
def _infer_topic_label(subject, user_text):
    text = (user_text or '').lower()
    for keyword, label in TOPIC_LABELS.get(subject, []):
        if keyword in text:
            return label
    return SUBJECT_KEYWORDS and {
        'dsa': 'DSA Practice',
        'dbms': 'DBMS Practice',
        'os': 'OS Practice',
        'cn': 'CN Practice',
    }.get(subject)


# ============================================================
#  API ROUTE
# ============================================================

@agents_bp.route('/api/chat', methods=['POST'])
def chat():
    """
    POST /api/chat
    Body: { "subject": "dsa"|"dbms"|"os"|"cn", "history": [{role, content}] }
    Returns: { "reply": "..." }
    """

    # ── Auth check ────────────────────────────────────────────
    if 'user_email' not in session:
        return jsonify({'error': 'Unauthorised'}), 401

    # ── Parse request ─────────────────────────────────────────
    data    = request.get_json(force=True)
    subject = data.get('subject', '').lower().strip()
    history = data.get('history', [])

    if subject not in AGENT_PROMPTS:
        return jsonify({'error': f'Unknown subject: {subject}'}), 400

    if not history:
        return jsonify({'error': 'Empty history'}), 400

    # ── Validate history format ───────────────────────────────
    messages = []
    for msg in history:
        role    = msg.get('role', '')
        content = msg.get('content', '').strip()
        if role in ('user', 'assistant') and content:
            messages.append({'role': role, 'content': content})

    if not messages:
        return jsonify({'error': 'No valid messages'}), 400

    # Changed: central coordinator checks the latest question before the subject bot answers.
    latest_user_message = messages[-1]['content']
    mismatch_subject = _detect_subject_mismatch(subject, latest_user_message)
    if mismatch_subject:
        friendly_names = {
            'dsa': 'DSA Agent',
            'dbms': 'DBMS Agent',
            'os': 'OS Agent',
            'cn': 'CN Agent',
        }
        return jsonify({
            'reply': (
                f"I am the {friendly_names.get(subject, 'current bot')} and I should stay focused on that subject only. "
                f"Your question looks more suited for the {friendly_names.get(mismatch_subject, 'correct bot')}. "
                f"Please switch to that bot and ask it there."
            )
        }), 200

    # ── Call Groq API ─────────────────────────────────────────
    try:
        client = Groq(api_key=GROQ_API_KEY)

        # Changed: use the center coordinator after client creation so routing can use the same API.
        mismatch_subject = _coordinator_route_subject(client, subject, latest_user_message)
        if mismatch_subject:
            friendly_names = {
                'dsa': 'DSA Agent',
                'dbms': 'DBMS Agent',
                'os': 'OS Agent',
                'cn': 'CN Agent',
            }
            return jsonify({
                'reply': (
                    f"I am the {friendly_names.get(subject, 'current bot')} and I should stay focused on that subject only. "
                    f"Your question looks more suited for the {friendly_names.get(mismatch_subject, 'correct bot')}. "
                    f"Please switch to that bot and ask it there."
                )
            }), 200

        response = client.chat.completions.create(
            model      = MODEL,
            max_tokens = MAX_TOKENS,
            messages   = [{"role": "system", "content": AGENT_PROMPTS[subject]}] + messages,
        )

        reply = response.choices[0].message.content

    except Exception as e:
        error_msg = str(e)

        if 'invalid_api_key' in error_msg.lower() or '401' in error_msg:
            return jsonify({'reply': '🔑 API key is invalid or missing. Please check your GROQ_API_KEY in .env'}), 200
        elif 'rate_limit' in error_msg.lower() or '429' in error_msg:
            return jsonify({'reply': '⚠️ Rate limit reached. Please wait a moment and try again.'}), 200
        elif 'timeout' in error_msg.lower():
            return jsonify({'reply': '⏱ The request timed out. Please try again.'}), 200
        else:
            return jsonify({'reply': f'⚠️ Unexpected error: {error_msg}'}), 200

    # ── Save doubt to DB ──────────────────────────────────────
    try:
        user_id  = session.get('user_id')
        question = messages[-1]['content']   # last user message is the question
        # Changed: infer a concrete topic label so dashboard weak-topic tracking works.
        inferred_topic = _infer_topic_label(subject, question)
        save_doubt(
            user_id  = user_id,
            subject  = subject.upper(),
            question = question,
            answer   = reply,
            # topic    = None,   # topic auto-tagging can be added later
            topic    = inferred_topic,
        )
    except Exception as db_error:
        # Don't crash the response if DB write fails — just log it
        print(f"[save_doubt] DB error: {db_error}")

    return jsonify({'reply': reply})
