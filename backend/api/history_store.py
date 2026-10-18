"""In-memory query history store (replace with DB persistence for production)."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from threading import Lock

_store: dict[str, dict] = {}
_lock = Lock()


def save_query(data: dict) -> str:
    query_id = str(uuid.uuid4())
    with _lock:
        _store[query_id] = {**data, "query_id": query_id, "timestamp": datetime.now(timezone.utc).isoformat()}
    return query_id


def get_query(query_id: str) -> dict | None:
    return _store.get(query_id)


def get_all_queries(limit: int = 50) -> list[dict]:
    with _lock:
        items = sorted(_store.values(), key=lambda x: x.get("timestamp", ""), reverse=True)
    return items[:limit]


def update_feedback(query_id: str, feedback: str, note: str | None = None) -> bool:
    with _lock:
        if query_id not in _store:
            return False
        _store[query_id]["feedback"] = feedback
        if note:
            _store[query_id]["feedback_note"] = note
    return True


def get_verified_few_shots(limit: int = 3) -> list[dict]:
    """Retrieve user-verified 'correct' queries to inject as dynamic few-shot examples."""
    with _lock:
        correct_items = [
            item for item in _store.values()
            if item.get("feedback") == "correct" and item.get("sql") and item.get("question")
        ]
    return correct_items[:limit]


def get_eval_feedback_cases() -> list[dict]:
    """Retrieve queries marked 'incorrect' to serve as regression cases in the eval suite."""
    with _lock:
        incorrect_items = [
            {
                "id": f"feedback_{item['query_id'][:8]}",
                "category": "user_reported_anomaly",
                "question": item.get("question"),
                "generated_sql": item.get("sql"),
                "user_note": item.get("feedback_note", "User marked result as incorrect"),
                "timestamp": item.get("timestamp"),
            }
            for item in _store.values()
            if item.get("feedback") == "incorrect" and item.get("question")
        ]
    return incorrect_items


def get_flywheel_summary() -> dict:
    """Return summary of the feedback flywheel loop."""
    few_shots = get_verified_few_shots(limit=10)
    eval_cases = get_eval_feedback_cases()
    return {
        "verified_few_shot_count": len(few_shots),
        "new_eval_case_count": len(eval_cases),
        "few_shots": few_shots,
        "eval_cases": eval_cases,
    }

