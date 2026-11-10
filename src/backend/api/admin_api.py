"""Administrator-only audit log access."""
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from src.backend.services.user_service import UserService
from src.backend.utils.supabase_client import supabase
from src.backend.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


def require_admin(request: Request) -> str:
    """Use verified identities and a server-side allowlist; fail closed."""
    user_id = UserService.get_user_id(request)
    allowed_ids = {
        value.strip()
        for value in os.getenv("ADMIN_USER_IDS", "").split(",")
        if value.strip()
    }
    if not allowed_ids or user_id not in allowed_ids:
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user_id


@router.get("/logs")
def get_admin_logs(
    request: Request,
    event_type: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    admin_user_id = require_admin(request)
    logger.info("[Admin] Audit logs requested by %s", admin_user_id)

    try:
        query = supabase.table("analytics_events").select("*").order("timestamp", desc=True)
        if event_type:
            query = query.eq("event_name", event_type)
        if session_id:
            query = query.eq("session_id", session_id)
        if user_id:
            query = query.eq("user_id", user_id)
        result = query.range(offset, offset + limit - 1).execute()
        rows = result.data or []
        return {"data": rows, "count": len(rows), "limit": limit, "offset": offset}
    except Exception:
        logger.exception("[Admin] Failed to fetch audit logs")
        raise HTTPException(status_code=500, detail="Unable to retrieve audit logs") from None
