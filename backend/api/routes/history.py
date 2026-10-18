"""History endpoint."""
from fastapi import APIRouter
from api.history_store import get_all_queries
from api.models import HistoryItem

router = APIRouter()


@router.get("/history", response_model=list[HistoryItem])
async def get_history(limit: int = 50):
    """Return recent query history."""
    items = get_all_queries(limit=limit)
    return [
        HistoryItem(
            query_id=item.get("query_id", ""),
            question=item.get("question", ""),
            sql=item.get("sql"),
            status=item.get("status", "unknown"),
            confidence_percentage=item.get("confidence_percentage"),
            row_count=item.get("row_count"),
            timestamp=item.get("timestamp", ""),
            feedback=item.get("feedback"),
        )
        for item in items
    ]


@router.get("/history/flywheel")
async def get_feedback_flywheel():
    """Return feedback flywheel data: verified few-shots and regression eval cases."""
    from api.history_store import get_flywheel_summary
    return get_flywheel_summary()

