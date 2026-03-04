import json
import os
import time
import requests
import uuid

def _load_api_url() -> str:
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)["api_url"]
    except Exception:
        return "https://script.google.com/macros/s/AKfycbyoTGSLxFNEFkhwfYLDUrOwGrIHKWsIQ1SKOPu8AvNlSUYMlm9h7yK0kGYWD45a1Loa/exec"

API_URL = _load_api_url()

class CourseClient:

    def __init__(self, name, lesson_id):
        self.name = name
        self.lesson_id = lesson_id
        self.token = self._start_session()

    def _start_session(self):
        r = requests.get(API_URL, params={
            "name": self.name,
            "lesson_id": self.lesson_id,
        }, timeout=15)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"Cannot start session: {data.get('error', data)}")
        return data["token"]

    def submit(self, task_id, result, progress=None):
        payload = {
            "token": self.token,
            "task_id": task_id,
            "result": result,
            "progress": progress or {},
            "client_ts": int(time.time() * 1000),
            "nonce": str(uuid.uuid4()),
        }
        r = requests.post(API_URL, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()


def get_all_scores(lesson_id, admin_key=None):
    """Fetch all submissions for a lesson (requires backend all_scores action)."""
    params = {"action": "all_scores", "lesson_id": lesson_id}
    if admin_key:
        params["key"] = admin_key
    r = requests.get(API_URL, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

