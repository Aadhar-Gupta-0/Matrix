"""Session listing and status endpoints with enforced tenant ownership."""
from fastapi import APIRouter, HTTPException, Request
from src.backend.services.user_service import UserService
from src.backend.utils.supabase_client import supabase
from src.backend.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


@router.get("/list")
def list_sessions(request: Request):
    user_id = UserService.get_user_id(request)
    try:
        response = (
            supabase.table("sessions")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return [
            {
                "id": session["id"],
                "filename": session["filename"],
                "status": session["status"],
                "created_at": session["created_at"],
                "mentor_score": (session.get("completion_metadata") or {}).get("mentor_score"),
                "file_url": session["file_url"],
            }
            for session in (response.data or [])
        ]
    except Exception:
        logger.exception("Failed to list sessions")
        raise HTTPException(status_code=500, detail="Unable to list sessions") from None


@router.get("/{session_id}")
def get_session_status(session_id: str, request: Request):
    user_id = UserService.get_user_id(request)
    try:
        response = (
            supabase.table("sessions")
            .select("*")
            .eq("id", session_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Session not found")
        session = response.data[0]
        return {
            "id": session["id"],
            "filename": session["filename"],
            "status": session["status"],
            "file_url": session["file_url"],
            "has_transcript": session.get("has_transcript", False),
            "stages_completed": session.get("stages_completed", []),
            "last_successful_stage": session.get("last_successful_stage"),
            "created_at": session["created_at"],
            "updated_at": session.get("updated_at"),
            "completed_at": session.get("completed_at"),
            "completion_metadata": session.get("completion_metadata") or {},
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get session status")
        raise HTTPException(status_code=500, detail="Unable to fetch session status") from None
