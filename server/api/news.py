"""
FastAPI router for news & injury flag endpoints — per D-09, D-10.

GET /api/players/{player_id}/news — full alert details (news items, sources, timestamps, alert type, severity, raw headline/URL)
No separate /api/news top-level endpoint per D-10.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from server.core.config import NEWS_STALE_WARNING_HOURS
from server.pipeline.db.connection import get_connection
from server.pipeline.db.queries import get_news_items, get_player_alerts
from server.services.news_service import NewsService
from server.services.player_service import get_player_by_id

router = APIRouter(prefix="/api", tags=["news"])


def _compute_updated_ago(last_updated_at: str) -> str:
    """Compute 'Updated X min/hours ago' from a timestamp string."""
    try:
        last_updated = datetime.fromisoformat(last_updated_at.replace('Z', '+00:00'))
    except Exception:
        try:
            last_updated = datetime.fromisoformat(last_updated_at)
        except Exception:
            return "unknown"

    if last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    age_delta = now - last_updated
    total_seconds = age_delta.total_seconds()

    if total_seconds < 0:
        return "just now"
    elif total_seconds < 3600:
        return f"{int(total_seconds / 60)} min ago"
    else:
        return f"{int(total_seconds / 3600)} hours ago"


@router.get("/players/{player_id}/news")
def get_player_news(player_id: int, refresh: bool = False):
    """Full news and alerts for a player.

    Per D-09: dedicated endpoint returning full alert details.
    Per D-07: includes "Updated X min/hours ago" timestamps.
    Per D-08: includes stale data warning if alerts are older than 24 hours.

    Query params:
    - refresh: if True, force re-fetch news from sources before returning
    """
    try:
        player = get_player_by_id(player_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Player not found")

    news_service = NewsService()

    is_fresh, stale_sources = news_service.is_cache_fresh()

    if refresh or not is_fresh:
        try:
            news_service.process_all()
        except Exception:
            pass

    conn = get_connection()
    try:
        alerts = get_player_alerts(conn, player_id)
        news_items = get_news_items(conn, player_id, limit=50)
    finally:
        conn.close()

    now = datetime.now(timezone.utc)
    formatted_alerts = []
    for alert in alerts:
        last_updated = alert["last_updated_at"]
        updated_ago = _compute_updated_ago(last_updated)
        formatted_alerts.append({
            "alert_type": alert["alert_type"],
            "subcategory": alert.get("subcategory"),
            "severity": alert["severity"],
            "source": alert["source"],
            "source_url": alert.get("source_url"),
            "headline": alert.get("headline"),
            "first_seen_at": alert["first_seen_at"],
            "last_updated_at": last_updated,
            "updated_ago": updated_ago,
        })

    formatted_news = []
    for item in news_items:
        published_at = item.get("published_at", "")
        fetched_at = item.get("fetched_at", "")
        formatted_news.append({
            "source": item["source"],
            "source_url": item.get("source_url"),
            "headline": item["headline"],
            "raw_content": item.get("raw_content"),
            "published_at": published_at,
            "fetched_at": fetched_at,
            "alert_keywords": item.get("alert_keywords"),
            "updated_ago": _compute_updated_ago(fetched_at),
        })

    stale_warning = None
    for alert in formatted_alerts:
        try:
            last_updated = datetime.fromisoformat(alert["last_updated_at"].replace('Z', '+00:00'))
        except Exception:
            try:
                last_updated = datetime.fromisoformat(alert["last_updated_at"])
            except Exception:
                continue

        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)

        age_hours = (now - last_updated).total_seconds() / 3600
        if age_hours > NEWS_STALE_WARNING_HOURS:
            stale_warning = f"News data may be outdated. Last updated more than {NEWS_STALE_WARNING_HOURS} hours ago."
            break

    return {
        "player_id": player_id,
        "alerts": formatted_alerts,
        "news_items": formatted_news,
        "stale_warning": stale_warning,
    }
