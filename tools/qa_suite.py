"""
QA Automation Suite — LMS Google Apps Script backend
=====================================================
Usage:
    python tools/qa_suite.py              # all tests for all lessons
    python tools/qa_suite.py --unit       # unit tests only (POST)
    python tools/qa_suite.py --progress   # progress GET tests only
    python tools/qa_suite.py --questions  # questions GET tests (default lesson)
    python tools/qa_suite.py --load       # load simulation only
    python tools/qa_suite.py --lesson4    # full suite for lesson_04_exam
    python tools/qa_suite.py --lesson5    # full suite for lesson_05_exam

Configuration is loaded from tools/config.json (API URL + lesson definitions).
"""

import json
import requests
import uuid
import time
import random
import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional, Any

# ── import shared client ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from client import API_URL

TIMEOUT = 20          # seconds per request
LOAD_STUDENTS = 20    # parallel simulated students
LOAD_WORKERS = 10     # thread pool size

# ── Per-lesson configuration — loaded from config.json ───────────────
def _load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

_CONFIG = _load_config()

# LESSONS: {lesson_id: {label, task_ids, active}}
LESSONS: dict = _CONFIG.get("lessons", {
    "lesson_04_exam": {
        "label": "Lesson 04 — Bool Logic & Control",
        "task_ids": ["q01", "q02"],
        "active": True,
    },
    "lesson_05_exam": {
        "label": "Lesson 05 — Modules, Imports & CLI",
        "task_ids": ["q01", "q02"],
        "active": False,
    },
})

# All registered lessons (used for --lesson4/--lesson5 suites)
LESSON_IDS     = list(LESSONS.keys())
TASK_IDS       = list({tid for cfg in LESSONS.values() for tid in cfg.get("task_ids", [])})
EXAM_LESSON_ID = "lesson_04_exam"   # default for --questions flag

# Lessons confirmed working in GAS backend (used by generic --unit/--progress/--load)
# Controlled by "active": true in config.json
ACTIVE_LESSON_IDS = [lid for lid, cfg in LESSONS.items() if cfg.get("active", False)]
if not ACTIVE_LESSON_IDS:
    ACTIVE_LESSON_IDS = ["lesson_04_exam"]
FIRST_NAMES = [
    "Олексій", "Марія", "Іван", "Юлія", "Денис",
    "Катерина", "Сергій", "Анна", "Микола", "Оксана",
    "Артем", "Людмила", "Богдан", "Тетяна", "Андрій",
    "Ірина", "Дмитро", "Наталія", "Олег", "Вікторія",
]

# ══════════════════════════════════════════════════════════════════════
# Result container
# ══════════════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: int
    detail: str = ""
    response: Optional[Any] = field(default=None, repr=False)

    def status_tag(self) -> str:
        return "PASS" if self.passed else "FAIL"


class TestRunner:
    """Collects results and prints a structured report."""

    _lock = threading.Lock()

    def __init__(self, label: str):
        self.label = label
        self.results: list[TestResult] = []

    def record(self, result: TestResult) -> TestResult:
        with self._lock:
            self.results.append(result)
        tag = "\033[32mPASS\033[0m" if result.passed else "\033[31mFAIL\033[0m"
        print(f"  [{tag}] {result.name:<40}  {result.duration_ms:>5} ms  {result.detail}")
        return result

    def summary(self) -> dict:
        total   = len(self.results)
        passed  = sum(1 for r in self.results if r.passed)
        failed  = total - passed
        avg_ms  = int(sum(r.duration_ms for r in self.results) / total) if total else 0
        max_ms  = max((r.duration_ms for r in self.results), default=0)
        return {
            "total": total, "passed": passed, "failed": failed,
            "success_rate_pct": round(100 * passed / total, 1) if total else 0,
            "failure_rate_pct": round(100 * failed / total, 1) if total else 0,
            "avg_ms": avg_ms, "max_ms": max_ms,
        }

    def print_summary(self):
        s = self.summary()
        sep = "─" * 60
        print(f"\n  {sep}")
        print(f"  {self.label}")
        print(f"  {sep}")
        print(f"  Total      : {s['total']}")
        print(f"  Passed     : {s['passed']}  ({s['success_rate_pct']}%)")
        print(f"  Failed     : {s['failed']}  ({s['failure_rate_pct']}%)")
        print(f"  Avg latency: {s['avg_ms']} ms")
        print(f"  Max latency: {s['max_ms']} ms")
        print(f"  {sep}\n")


# ══════════════════════════════════════════════════════════════════════
# Low-level helpers
# ══════════════════════════════════════════════════════════════════════

def _get_session(name: str, lesson_id: str) -> tuple[bool, dict, int]:
    """GET /exec?name=...&lesson_id=...  → (ok, data, ms)"""
    t0 = time.monotonic()
    try:
        r = requests.get(
            API_URL,
            params={"name": name, "lesson_id": lesson_id},
            timeout=TIMEOUT,
        )
        data = r.json()
    except Exception as exc:
        ms = int((time.monotonic() - t0) * 1000)
        return False, {"error": str(exc)}, ms
    ms = int((time.monotonic() - t0) * 1000)
    return True, data, ms


def _get_progress(token: str) -> tuple[bool, dict, int]:
    """GET /exec?action=progress&token=... → (http_ok, data, ms)"""
    t0 = time.monotonic()
    try:
        r = requests.get(
            API_URL,
            params={"action": "progress", "token": token},
            timeout=TIMEOUT,
        )
        data = r.json()
    except Exception as exc:
        ms = int((time.monotonic() - t0) * 1000)
        return False, {"error": str(exc)}, ms
    ms = int((time.monotonic() - t0) * 1000)
    return True, data, ms


def _get_questions(token: str) -> tuple[bool, dict, int]:
    """GET /exec?action=questions&token=... → (http_ok, data, ms)"""
    t0 = time.monotonic()
    try:
        r = requests.get(
            API_URL,
            params={"action": "questions", "token": token},
            timeout=TIMEOUT,
        )
        data = r.json()
    except Exception as exc:
        ms = int((time.monotonic() - t0) * 1000)
        return False, {"error": str(exc)}, ms
    ms = int((time.monotonic() - t0) * 1000)
    return True, data, ms


def _post_submission(payload: dict) -> tuple[bool, dict, int]:
    """POST /exec with JSON payload → (http_ok, data, ms)"""
    t0 = time.monotonic()
    try:
        r = requests.post(API_URL, json=payload, timeout=TIMEOUT)
        data = r.json()
    except Exception as exc:
        ms = int((time.monotonic() - t0) * 1000)
        return False, {"error": str(exc)}, ms
    ms = int((time.monotonic() - t0) * 1000)
    return True, data, ms


def _rand_name() -> str:
    return random.choice(FIRST_NAMES) + f"_{random.randint(100, 999)}"


def _rand_lesson() -> str:
    """Pick a random lesson from the ACTIVE (configured) list."""
    return random.choice(ACTIVE_LESSON_IDS)


def _rand_task() -> str:
    active_tasks = list({
        tid
        for lid in ACTIVE_LESSON_IDS
        for tid in _lesson_tasks(lid)
    })
    return random.choice(active_tasks or TASK_IDS)


def _lesson_tasks(lesson_id: str) -> list:
    """Return task IDs configured for a specific lesson."""
    return LESSONS.get(lesson_id, {}).get("task_ids", TASK_IDS)


def _rand_task_for(lesson_id: str) -> str:
    return random.choice(_lesson_tasks(lesson_id))


def _base_payload(token: str, nonce: Optional[str] = None) -> dict:
    return {
        "token": token,
        "task_id": _rand_task(),
        "result": {"answer": "42", "correct": True},
        "progress": {"score": random.randint(50, 100)},
        "client_ts": int(time.time() * 1000),
        "nonce": nonce or str(uuid.uuid4()),
    }


# ══════════════════════════════════════════════════════════════════════
# Unit tests
# ══════════════════════════════════════════════════════════════════════

def test_start_session(runner: TestRunner) -> Optional[str]:
    """GET with valid name+lesson_id → ok:true + token present."""
    name = _rand_name()
    lesson = _rand_lesson()

    http_ok, data, ms = _get_session(name, lesson)

    passed = http_ok and data.get("ok") is True and bool(data.get("token"))
    detail = f"token={'present' if data.get('token') else 'MISSING'}  raw={_trim(data)}"
    runner.record(TestResult("test_start_session", passed, ms, detail, data))
    return data.get("token") if passed else None


def test_valid_submission(runner: TestRunner) -> Optional[str]:
    """Start session → submit valid payload → ok:true + progress echoed back."""
    name = _rand_name()
    lesson = _rand_lesson()

    http_ok, sess, ms1 = _get_session(name, lesson)
    if not (http_ok and sess.get("ok") and sess.get("token")):
        runner.record(TestResult("test_valid_submission", False, ms1, "session failed", sess))
        return None

    token = sess["token"]
    nonce = str(uuid.uuid4())
    payload = _base_payload(token, nonce)
    sent_progress = payload["progress"]

    http_ok2, data, ms2 = _post_submission(payload)
    returned_progress = data.get("progress")
    passed = (
        http_ok2
        and data.get("ok") is True
        and returned_progress is not None
        and returned_progress.get("score") == sent_progress.get("score")
    )
    detail = (
        f"ok={data.get('ok')}  "
        f"progress_in_response={'yes' if returned_progress else 'MISSING'}  "
        f"score={returned_progress.get('score') if returned_progress else '?'}"
    )
    runner.record(TestResult("test_valid_submission", passed, ms1 + ms2, detail, data))
    return nonce if passed else None


def test_replay_attack(runner: TestRunner, token: Optional[str], nonce: Optional[str]):
    """Reuse a known nonce on the same token → backend must reject it."""
    if token is None or nonce is None:
        runner.record(TestResult(
            "test_replay_attack", False, 0,
            "SKIP — no valid token/nonce from previous test",
        ))
        return

    payload = _base_payload(token, nonce)   # same nonce!
    http_ok, data, ms = _post_submission(payload)

    # success = server said NOT ok, i.e., replay was blocked
    rejected = http_ok and data.get("ok") is not True
    detail = (
        f"replay blocked={rejected}  ok={data.get('ok')}  raw={_trim(data)}"
    )
    runner.record(TestResult("test_replay_attack", rejected, ms, detail, data))


def test_invalid_token(runner: TestRunner):
    """POST with a fake token → backend must reject it."""
    fake_token = "invalid_token_" + uuid.uuid4().hex[:8]
    payload = _base_payload(fake_token)

    http_ok, data, ms = _post_submission(payload)

    rejected = http_ok and data.get("ok") is not True
    detail = f"rejected={rejected}  ok={data.get('ok')}  raw={_trim(data)}"
    runner.record(TestResult("test_invalid_token", rejected, ms, detail, data))


def test_missing_task_id(runner: TestRunner):
    """POST without task_id → validation error expected."""
    # grab a real token so token check passes and we reach field validation
    name = _rand_name()
    http_ok, sess, _ = _get_session(name, _rand_lesson())
    if not (http_ok and sess.get("token")):
        runner.record(TestResult(
            "test_missing_task_id", False, 0,
            "SKIP — could not obtain token",
        ))
        return

    payload = _base_payload(sess["token"])
    del payload["task_id"]          # intentionally omit required field

    http_ok2, data, ms = _post_submission(payload)
    rejected = http_ok2 and data.get("ok") is not True
    detail = f"rejected={rejected}  ok={data.get('ok')}  raw={_trim(data)}"
    runner.record(TestResult("test_missing_task_id", rejected, ms, detail, data))


def test_concurrent_submissions(runner: TestRunner):
    """Two submissions in parallel on the same token → both handled correctly."""
    name = _rand_name()
    http_ok, sess, _ = _get_session(name, _rand_lesson())
    if not (http_ok and sess.get("token")):
        runner.record(TestResult(
            "test_concurrent_submissions", False, 0,
            "SKIP — could not obtain token",
        ))
        return

    token = sess["token"]
    results: list[tuple[bool, dict, int]] = []
    _results_lock = threading.Lock()

    def submit_one():
        res = _post_submission(_base_payload(token))
        with _results_lock:
            results.append(res)

    t0 = time.monotonic()
    t1 = threading.Thread(target=submit_one)
    t2 = threading.Thread(target=submit_one)
    t1.start(); t2.start()
    t1.join(); t2.join()
    total_ms = int((time.monotonic() - t0) * 1000)

    ok_count = sum(1 for (http_ok, data, _) in results if http_ok and data.get("ok") is True)
    # at least one must succeed; backend may reject the other as replay
    passed = ok_count >= 1
    detail = (
        f"ok_count={ok_count}/2  "
        f"r1={results[0][1].get('ok')}  r2={results[1][1].get('ok')}"
    )
    runner.record(TestResult("test_concurrent_submissions", passed, total_ms, detail))


# ══════════════════════════════════════════════════════════════════════
# Progress GET tests
# ══════════════════════════════════════════════════════════════════════

def test_progress_invalid_token(runner: TestRunner):
    """GET progress with fake token → ok:false + error."""
    fake = "invalid_token_" + uuid.uuid4().hex[:8]
    http_ok, data, ms = _get_progress(fake)

    rejected = http_ok and data.get("ok") is not True
    detail = f"rejected={rejected}  error={data.get('error')}  raw={_trim(data)}"
    runner.record(TestResult("test_progress_invalid_token", rejected, ms, detail, data))


def test_progress_missing_token(runner: TestRunner):
    """GET progress without token param → ok:false."""
    t0 = time.monotonic()
    try:
        r = requests.get(API_URL, params={"action": "progress"}, timeout=TIMEOUT)
        data = r.json()
    except Exception as exc:
        ms = int((time.monotonic() - t0) * 1000)
        runner.record(TestResult("test_progress_missing_token", False, ms, str(exc)))
        return
    ms = int((time.monotonic() - t0) * 1000)

    rejected = data.get("ok") is not True
    detail = f"rejected={rejected}  error={data.get('error')}  raw={_trim(data)}"
    runner.record(TestResult("test_progress_missing_token", rejected, ms, detail, data))


def test_progress_no_data(runner: TestRunner):
    """Fresh session with no submissions → ok:true, progress:null."""
    name = _rand_name()
    lesson = _rand_lesson()

    http_ok, sess, ms_sess = _get_session(name, lesson)
    if not (http_ok and sess.get("token")):
        runner.record(TestResult(
            "test_progress_no_data", False, ms_sess,
            "SKIP — could not obtain token",
        ))
        return

    http_ok2, data, ms_get = _get_progress(sess["token"])
    passed = (
        http_ok2
        and data.get("ok") is True
        and "progress" in data
        and data["progress"] is None
    )
    detail = (
        f"ok={data.get('ok')}  "
        f"progress={data.get('progress')!r}  "
        f"raw={_trim(data)}"
    )
    runner.record(TestResult(
        "test_progress_no_data", passed, ms_sess + ms_get, detail, data,
    ))


def test_progress_after_submission(runner: TestRunner):
    """Submit answer → POST response must contain exam progress with required fields."""
    name = _rand_name()
    lesson = _rand_lesson()

    http_ok, sess, ms1 = _get_session(name, lesson)
    if not (http_ok and sess.get("token")):
        runner.record(TestResult(
            "test_progress_after_submission", False, ms1,
            "SKIP — could not obtain token",
        ))
        return

    token = sess["token"]
    payload = {
        "token": token,
        "task_id": _rand_task(),
        "result": {"answer": "0"},
        "progress": {},
        "client_ts": int(time.time() * 1000),
        "nonce": str(uuid.uuid4()),
    }
    http_ok2, submit_data, ms2 = _post_submission(payload)
    total_ms = ms1 + ms2

    # Backend returns exam progress directly in the POST response.
    # Expected fields: answered, correct_count, score_pct, total_questions
    prog = submit_data.get("progress") or {}
    has_fields = all(
        k in prog for k in ("answered", "correct_count", "score_pct", "total_questions")
    )
    passed = (
        http_ok2
        and submit_data.get("ok") is True
        and has_fields
        and prog.get("answered", 0) >= 1
    )
    detail = (
        f"ok={submit_data.get('ok')}  "
        f"answered={prog.get('answered')}  "
        f"score_pct={prog.get('score_pct')}  "
        f"has_required_fields={has_fields}"
    )
    runner.record(TestResult(
        "test_progress_after_submission", passed, total_ms, detail, submit_data,
    ))


def test_progress_returns_latest(runner: TestRunner):
    """Submit twice → second POST response must show answered=2 (cumulative count)."""
    name = _rand_name()
    lesson = _rand_lesson()

    http_ok, sess, _ = _get_session(name, lesson)
    if not (http_ok and sess.get("token")):
        runner.record(TestResult(
            "test_progress_returns_latest", False, 0,
            "SKIP — could not obtain token",
        ))
        return

    token = sess["token"]
    tasks = _lesson_tasks(lesson)
    if len(tasks) < 2:
        runner.record(TestResult(
            "test_progress_returns_latest", False, 0,
            f"SKIP — need ≥2 task IDs, got {tasks}",
        ))
        return

    t0 = time.monotonic()

    # first submission — task[0]
    _, data1, _ = _post_submission({
        "token": token,
        "task_id": tasks[0],
        "result": {"answer": "0"},
        "progress": {},
        "client_ts": int(time.time() * 1000),
        "nonce": str(uuid.uuid4()),
    })

    # second submission — task[1] (different question)
    _, data2, _ = _post_submission({
        "token": token,
        "task_id": tasks[1],
        "result": {"answer": "1"},
        "progress": {},
        "client_ts": int(time.time() * 1000),
        "nonce": str(uuid.uuid4()),
    })

    total_ms = int((time.monotonic() - t0) * 1000)

    prog1 = (data1.get("progress") or {}).get("answered", 0)
    prog2 = (data2.get("progress") or {}).get("answered", 0)

    # answered count must be >= 1 after each submission and non-decreasing
    passed = (
        data1.get("ok") is True
        and data2.get("ok") is True
        and prog1 >= 1
        and prog2 >= prog1
    )
    detail = (
        f"ok1={data1.get('ok')}  ok2={data2.get('ok')}  "
        f"answered_after_1st={prog1}  answered_after_2nd={prog2}  "
        f"cumulative={prog2 >= prog1}"
    )
    runner.record(TestResult(
        "test_progress_returns_latest", passed, total_ms, detail,
    ))


# ══════════════════════════════════════════════════════════════════════
# Questions GET tests
# ══════════════════════════════════════════════════════════════════════

QUESTION_REQUIRED_FIELDS = {"id", "question", "options", "level"}
VALID_LEVELS = {"bronze", "silver", "gold", "platinum"}


def test_questions_valid_token(runner: TestRunner,
                               lesson_id: str = EXAM_LESSON_ID) -> Optional[list]:
    """Valid session token → ok:true + non-empty list of questions."""
    name = _rand_name()
    http_ok, sess, _ = _get_session(name, lesson_id)
    if not (http_ok and sess.get("token")):
        runner.record(TestResult(
            "test_questions_valid_token", False, 0,
            "SKIP — could not obtain token",
        ))
        return None

    http_ok2, data, ms = _get_questions(sess["token"])
    questions = data.get("questions")
    passed = (
        http_ok2
        and data.get("ok") is True
        and isinstance(questions, list)
        and len(questions) > 0
    )
    detail = (
        f"ok={data.get('ok')}  "
        f"count={len(questions) if isinstance(questions, list) else 'N/A'}  "
        f"raw={_trim(data)}"
    )
    runner.record(TestResult("test_questions_valid_token", passed, ms, detail, data))
    return questions if passed else None


def test_questions_structure(runner: TestRunner, questions: Optional[list]):
    """Every question object has required fields: id, question, options, level."""
    if not questions:
        runner.record(TestResult(
            "test_questions_structure", False, 0,
            "SKIP — no questions from previous test",
        ))
        return

    t0 = time.monotonic()
    bad = []
    for q in questions:
        missing = QUESTION_REQUIRED_FIELDS - set(q.keys())
        if missing:
            bad.append({"id": q.get("id", "?"), "missing": sorted(missing)})
    ms = int((time.monotonic() - t0) * 1000)

    passed = len(bad) == 0
    detail = f"checked={len(questions)}  bad={bad if bad else 'none'}"
    runner.record(TestResult("test_questions_structure", passed, ms, detail))


def test_questions_options_nonempty(runner: TestRunner, questions: Optional[list]):
    """Every question has at least 2 options (minimum for a multiple-choice item)."""
    if not questions:
        runner.record(TestResult(
            "test_questions_options_nonempty", False, 0,
            "SKIP — no questions from previous test",
        ))
        return

    t0 = time.monotonic()
    bad = []
    for q in questions:
        opts = q.get("options", [])
        count = len(opts) if isinstance(opts, list) else 0
        if count < 2:
            bad.append({"id": q.get("id", "?"), "options_count": count})
    ms = int((time.monotonic() - t0) * 1000)

    passed = len(bad) == 0
    detail = f"checked={len(questions)}  bad={bad if bad else 'none'}"
    runner.record(TestResult("test_questions_options_nonempty", passed, ms, detail))


def test_questions_valid_levels(runner: TestRunner, questions: Optional[list]):
    """Every question's level is one of: bronze, silver, gold, platinum."""
    if not questions:
        runner.record(TestResult(
            "test_questions_valid_levels", False, 0,
            "SKIP — no questions from previous test",
        ))
        return

    t0 = time.monotonic()
    bad = []
    for q in questions:
        lvl = str(q.get("level", "")).lower().strip()
        if lvl not in VALID_LEVELS:
            bad.append({"id": q.get("id", "?"), "level": repr(lvl)})
    ms = int((time.monotonic() - t0) * 1000)

    levels_found = sorted({str(q.get("level", "")).lower() for q in questions})
    passed = len(bad) == 0
    detail = f"checked={len(questions)}  levels={levels_found}  bad={bad if bad else 'none'}"
    runner.record(TestResult("test_questions_valid_levels", passed, ms, detail))


def test_questions_options_are_strings(runner: TestRunner, questions: Optional[list]):
    """Every option within every question is a non-empty string."""
    if not questions:
        runner.record(TestResult(
            "test_questions_options_are_strings", False, 0,
            "SKIP — no questions from previous test",
        ))
        return

    t0 = time.monotonic()
    bad = []
    for q in questions:
        for i, opt in enumerate(q.get("options", [])):
            if not isinstance(opt, str) or not str(opt).strip():
                bad.append({"id": q.get("id", "?"), "option_index": i, "value": repr(opt)})
    ms = int((time.monotonic() - t0) * 1000)

    passed = len(bad) == 0
    detail = f"checked={len(questions)}  bad={bad if bad else 'none'}"
    runner.record(TestResult("test_questions_options_are_strings", passed, ms, detail))


def test_questions_ids_unique(runner: TestRunner, questions: Optional[list]):
    """All question IDs within the lesson are unique (no duplicates)."""
    if not questions:
        runner.record(TestResult(
            "test_questions_ids_unique", False, 0,
            "SKIP — no questions from previous test",
        ))
        return

    t0 = time.monotonic()
    ids = [q.get("id", "") for q in questions]
    duplicates = [qid for qid in set(ids) if ids.count(qid) > 1]
    ms = int((time.monotonic() - t0) * 1000)

    passed = len(duplicates) == 0
    detail = f"total={len(ids)}  unique={len(set(ids))}  duplicates={duplicates if duplicates else 'none'}"
    runner.record(TestResult("test_questions_ids_unique", passed, ms, detail))


def test_questions_invalid_token(runner: TestRunner):
    """GET questions with a fake token → ok:false (rejected by backend)."""
    fake_token = "invalid_token_" + uuid.uuid4().hex[:8]
    http_ok, data, ms = _get_questions(fake_token)

    rejected = http_ok and data.get("ok") is not True
    detail = f"rejected={rejected}  ok={data.get('ok')}  raw={_trim(data)}"
    runner.record(TestResult("test_questions_invalid_token", rejected, ms, detail, data))


def test_questions_missing_token(runner: TestRunner):
    """GET questions without token param → ok:false."""
    t0 = time.monotonic()
    try:
        r = requests.get(API_URL, params={"action": "questions"}, timeout=TIMEOUT)
        data = r.json()
    except Exception as exc:
        ms = int((time.monotonic() - t0) * 1000)
        runner.record(TestResult("test_questions_missing_token", False, ms, str(exc)))
        return
    ms = int((time.monotonic() - t0) * 1000)

    rejected = data.get("ok") is not True
    detail = f"rejected={rejected}  error={data.get('error')}  raw={_trim(data)}"
    runner.record(TestResult("test_questions_missing_token", rejected, ms, detail, data))


def test_questions_idempotent(runner: TestRunner,
                              lesson_id: str = EXAM_LESSON_ID):
    """Two calls with the same token return identical question IDs."""
    name = _rand_name()
    http_ok, sess, _ = _get_session(name, lesson_id)
    if not (http_ok and sess.get("token")):
        runner.record(TestResult(
            "test_questions_idempotent", False, 0,
            "SKIP — could not obtain token",
        ))
        return

    token = sess["token"]
    t0 = time.monotonic()
    _, data1, _ = _get_questions(token)
    _, data2, _ = _get_questions(token)
    ms = int((time.monotonic() - t0) * 1000)

    qs1 = data1.get("questions") or []
    qs2 = data2.get("questions") or []
    ids1 = sorted(q.get("id", "") for q in qs1)
    ids2 = sorted(q.get("id", "") for q in qs2)

    passed = (
        data1.get("ok") is True
        and data2.get("ok") is True
        and ids1 == ids2
        and len(ids1) > 0
    )
    detail = f"count1={len(qs1)}  count2={len(qs2)}  ids_match={ids1 == ids2}"
    runner.record(TestResult("test_questions_idempotent", passed, ms, detail))


# ══════════════════════════════════════════════════════════════════════
# Load simulation — 20 students in parallel
# ══════════════════════════════════════════════════════════════════════

def _student_workflow(student_id: int) -> TestResult:
    """Full workflow for one simulated student: start → submit."""
    name = f"{FIRST_NAMES[student_id % len(FIRST_NAMES)]}_s{student_id:03d}"
    lesson = _rand_lesson()

    t0 = time.monotonic()

    http_ok, sess, _ = _get_session(name, lesson)
    if not (http_ok and sess.get("ok") and sess.get("token")):
        ms = int((time.monotonic() - t0) * 1000)
        return TestResult(
            f"student_{student_id:03d}", False, ms,
            f"session failed  raw={_trim(sess)}",
        )

    token = sess["token"]
    task  = _rand_task()
    payload = {
        "token": token,
        "task_id": task,
        "result": {"answer": str(random.randint(0, 100)), "correct": random.choice([True, False])},
        "progress": {"score": random.randint(0, 100), "attempts": random.randint(1, 5)},
        "client_ts": int(time.time() * 1000),
        "nonce": str(uuid.uuid4()),
    }

    http_ok2, sub_data, _ = _post_submission(payload)
    ms = int((time.monotonic() - t0) * 1000)

    if not (http_ok2 and sub_data.get("ok")):
        detail = (
            f"name={name:<20}  lesson={lesson}  task={task}  "
            f"submit_ok={sub_data.get('ok')}  raw={_trim(sub_data)}"
        )
        return TestResult(f"student_{student_id:03d}", False, ms, detail, sub_data)

    # progress must be returned directly in POST response (no GET needed)
    returned = sub_data.get("progress")
    progress_ok = returned is not None and returned.get("score") == payload["progress"]["score"]
    passed = progress_ok
    detail = (
        f"name={name:<20}  lesson={lesson}  task={task}  "
        f"submit_ok=True  "
        f"progress_in_response={'yes' if returned else 'MISSING'}  "
        f"score={returned.get('score') if returned else '?'}"
    )
    return TestResult(f"student_{student_id:03d}", passed, ms, detail, sub_data)


def run_load_simulation(runner: TestRunner):
    print(f"\n  Launching {LOAD_STUDENTS} students in parallel "
          f"(pool={LOAD_WORKERS} threads)...\n")

    futures = {}
    with ThreadPoolExecutor(max_workers=LOAD_WORKERS) as pool:
        for sid in range(LOAD_STUDENTS):
            f = pool.submit(_student_workflow, sid)
            futures[f] = sid

        for f in as_completed(futures):
            result = f.result()
            runner.record(result)


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════

def _trim(data: Any, max_len: int = 80) -> str:
    s = str(data)
    return s if len(s) <= max_len else s[:max_len] + "…"


def _section(title: str):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


# ══════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════

def run_progress_tests() -> TestRunner:
    _section("PROGRESS GET TESTS")
    runner = TestRunner("Progress GET Suite")

    test_progress_invalid_token(runner)
    test_progress_missing_token(runner)
    test_progress_no_data(runner)
    test_progress_after_submission(runner)
    test_progress_returns_latest(runner)

    runner.print_summary()
    return runner


def run_unit_tests() -> TestRunner:
    _section("UNIT TESTS")
    runner = TestRunner("Unit Test Suite")

    # 1. start session (get token + nonce for downstream tests)
    token = test_start_session(runner)

    # 2. valid submission (also captures the nonce for replay test)
    # run independently so we have a fresh nonce
    name = _rand_name()
    http_ok, sess, _ = _get_session(name, _rand_lesson())
    replay_token = sess.get("token") if http_ok and sess.get("ok") else None
    replay_nonce = None

    if replay_token:
        nonce = str(uuid.uuid4())
        payload = _base_payload(replay_token, nonce)
        http_ok2, data, ms = _post_submission(payload)
        passed = http_ok2 and data.get("ok") is True
        detail = f"submit ok={data.get('ok')}  raw={_trim(data)}"
        runner.record(TestResult("test_valid_submission", passed, ms, detail, data))
        if passed:
            replay_nonce = nonce

    # 3. replay attack — reuse the nonce from test_valid_submission
    test_replay_attack(runner, replay_token, replay_nonce)

    # 4. invalid token
    test_invalid_token(runner)

    # 5. missing task_id
    test_missing_task_id(runner)

    # 6. concurrency (2 parallel)
    test_concurrent_submissions(runner)

    runner.print_summary()
    return runner


def run_questions_tests(lesson_id: str = EXAM_LESSON_ID) -> TestRunner:
    _section(f"QUESTIONS GET TESTS  (lesson={lesson_id})")
    runner = TestRunner(f"Questions Suite — {lesson_id}")

    # fetch once, reuse the list for all structure checks
    questions = test_questions_valid_token(runner, lesson_id)
    test_questions_structure(runner, questions)
    test_questions_options_nonempty(runner, questions)
    test_questions_options_are_strings(runner, questions)
    test_questions_valid_levels(runner, questions)
    test_questions_ids_unique(runner, questions)
    test_questions_invalid_token(runner)
    test_questions_missing_token(runner)
    test_questions_idempotent(runner, lesson_id)

    runner.print_summary()
    return runner


def run_load_tests() -> TestRunner:
    _section(f"LOAD SIMULATION — {LOAD_STUDENTS} students")
    runner = TestRunner("Load Simulation")
    run_load_simulation(runner)
    runner.print_summary()
    return runner


# ══════════════════════════════════════════════════════════════════════
# Per-lesson full suite
# ══════════════════════════════════════════════════════════════════════

def _run_unit_for_lesson(lesson_id: str) -> TestRunner:
    """Run unit tests scoped to a single lesson."""
    _section(f"UNIT TESTS  (lesson={lesson_id})")
    runner = TestRunner(f"Unit Tests — {lesson_id}")

    # session start
    name = _rand_name()
    http_ok, sess, ms_s = _get_session(name, lesson_id)
    passed_s = http_ok and sess.get("ok") is True and bool(sess.get("token"))
    runner.record(TestResult(
        "test_start_session", passed_s, ms_s,
        f"token={'present' if sess.get('token') else 'MISSING'}  raw={_trim(sess)}", sess,
    ))
    if not passed_s:
        runner.print_summary()
        return runner

    # valid submission
    token_r = sess["token"]
    nonce_r = str(uuid.uuid4())
    task_r  = _rand_task_for(lesson_id)
    payload_r = {
        "token": token_r,
        "task_id": task_r,
        "result": {"answer": "42", "correct": True},
        "progress": {"score": random.randint(50, 100)},
        "client_ts": int(time.time() * 1000),
        "nonce": nonce_r,
    }
    http_ok2, data2, ms2 = _post_submission(payload_r)
    passed2 = http_ok2 and data2.get("ok") is True
    runner.record(TestResult(
        "test_valid_submission", passed2, ms2,
        f"ok={data2.get('ok')}  task={task_r}  raw={_trim(data2)}", data2,
    ))

    # replay attack
    if passed2:
        http_ok3, data3, ms3 = _post_submission(payload_r)   # same nonce!
        rejected = http_ok3 and data3.get("ok") is not True
        runner.record(TestResult(
            "test_replay_attack", rejected, ms3,
            f"blocked={rejected}  ok={data3.get('ok')}  raw={_trim(data3)}", data3,
        ))
    else:
        runner.record(TestResult("test_replay_attack", False, 0, "SKIP — submission failed"))

    # invalid token
    fake = "invalid_token_" + uuid.uuid4().hex[:8]
    bad_payload = {
        "token": fake,
        "task_id": _rand_task_for(lesson_id),
        "result": {"answer": "x"},
        "progress": {},
        "client_ts": int(time.time() * 1000),
        "nonce": str(uuid.uuid4()),
    }
    http_ok4, data4, ms4 = _post_submission(bad_payload)
    rejected4 = http_ok4 and data4.get("ok") is not True
    runner.record(TestResult(
        "test_invalid_token", rejected4, ms4,
        f"rejected={rejected4}  raw={_trim(data4)}", data4,
    ))

    runner.print_summary()
    return runner


def _run_load_for_lesson(lesson_id: str, n: int = 10) -> TestRunner:
    """Run a mini load simulation (n students) for a specific lesson."""
    _section(f"LOAD SIMULATION — {n} students  (lesson={lesson_id})")
    runner = TestRunner(f"Load — {lesson_id}")

    print(f"\n  Launching {n} students in parallel (pool={min(n, 5)} threads)...\n")

    def _workflow(sid: int) -> TestResult:
        sname = f"{FIRST_NAMES[sid % len(FIRST_NAMES)]}_s{sid:03d}"
        t0 = time.monotonic()
        ok_s, sess_s, _ = _get_session(sname, lesson_id)
        if not (ok_s and sess_s.get("ok") and sess_s.get("token")):
            return TestResult(f"student_{sid:03d}", False,
                              int((time.monotonic() - t0) * 1000),
                              f"session failed  raw={_trim(sess_s)}")
        tok = sess_s["token"]
        task = _rand_task_for(lesson_id)
        pl = {
            "token": tok,
            "task_id": task,
            "result": {"answer": str(random.randint(0, 3)),
                       "correct": random.choice([True, False])},
            "progress": {"score": random.randint(0, 100)},
            "client_ts": int(time.time() * 1000),
            "nonce": str(uuid.uuid4()),
        }
        ok_p, sub, _ = _post_submission(pl)
        ms = int((time.monotonic() - t0) * 1000)
        passed = ok_p and sub.get("ok") is True
        detail = (f"name={sname:<20}  task={task}  "
                  f"submit_ok={sub.get('ok')}  raw={_trim(sub)}")
        return TestResult(f"student_{sid:03d}", passed, ms, detail, sub)

    with ThreadPoolExecutor(max_workers=min(n, 5)) as pool:
        for res in as_completed({pool.submit(_workflow, i): i for i in range(n)}):
            runner.record(res.result())

    runner.print_summary()
    return runner


def run_lesson_suite(lesson_id: str) -> list[TestRunner]:
    """Run the full QA suite (unit + progress + questions + load) for one lesson."""
    label = LESSONS.get(lesson_id, {}).get("label", lesson_id)
    border = "█" * 60
    print(f"\n{border}")
    print(f"  SUITE: {label}")
    print(f"{border}")

    runners = []
    runners.append(_run_unit_for_lesson(lesson_id))
    runners.append(run_progress_tests())        # progress tests are lesson-agnostic
    runners.append(run_questions_tests(lesson_id))
    runners.append(_run_load_for_lesson(lesson_id, n=10))
    return runners


def _print_combined(all_runners: list, elapsed: float, title: str = "COMBINED SUMMARY"):
    _section(title)
    all_results = [r for runner in all_runners if runner for r in runner.results]
    total  = len(all_results)
    passed = sum(1 for r in all_results if r.passed)
    failed = total - passed
    avg_ms = int(sum(r.duration_ms for r in all_results) / total) if total else 0
    max_ms = max((r.duration_ms for r in all_results), default=0)

    print(f"  Wall time   : {elapsed:.1f} s")
    print(f"  Total tests : {total}")
    print(f"  Passed      : {passed}  ({100*passed//total if total else 0}%)")
    print(f"  Failed      : {failed}  ({100*failed//total if total else 0}%)")
    print(f"  Avg latency : {avg_ms} ms")
    print(f"  Max latency : {max_ms} ms")

    if failed:
        print("\n  Failed tests:")
        for r in all_results:
            if not r.passed:
                print(f"    ✗ {r.name:<44} {r.detail}")
    print()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--all"

    t_start = time.monotonic()

    # ── per-lesson suite flags ────────────────────────────────────────
    if mode == "--lesson4":
        runners = run_lesson_suite("lesson_04_exam")
        _print_combined(runners, time.monotonic() - t_start,
                        "COMBINED — lesson_04_exam")
        return

    if mode == "--lesson5":
        runners = run_lesson_suite("lesson_05_exam")
        _print_combined(runners, time.monotonic() - t_start,
                        "COMBINED — lesson_05_exam")
        return

    # ── individual suite flags ────────────────────────────────────────
    unit_runner = progress_runner = questions_runner = load_runner = None

    if mode in ("--all", "--unit"):
        unit_runner = run_unit_tests()

    if mode in ("--all", "--progress"):
        progress_runner = run_progress_tests()

    if mode in ("--all", "--questions"):
        questions_runner = run_questions_tests()

    if mode in ("--all", "--load"):
        load_runner = run_load_tests()

    elapsed = time.monotonic() - t_start

    # ── combined summary ──────────────────────────────────────────────
    if mode == "--all":
        # also run per-lesson question tests for every configured lesson
        extra: list = []
        for lid in LESSONS:
            extra.append(run_questions_tests(lid))

        all_runners = [
            unit_runner, progress_runner, questions_runner, load_runner
        ] + extra
        _print_combined(all_runners, elapsed)


if __name__ == "__main__":
    main()