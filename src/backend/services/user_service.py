"""Resolve user identity from verified Supabase bearer tokens.

A DEV_MODE bypass is available only for explicitly isolated local development.
"""
import os

from fastapi import HTTPException, Request, status
from src.backend.utils.supabase_client import supabase
from src.backend.utils.logger import setup_logger

logger = setup_logger(__name__)
DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


class UserService:
    @staticmethod
    def get_user_id(request: Request) -> str:
        auth_header = (request.headers.get("Authorization") or "").strip()
        dev_mode = (
            os.getenv("DEV_MODE", "false").lower() == "true"
            and os.getenv("ENV", "production").lower() in {"development", "local", "test"}
        )

        if not auth_header and dev_mode:
            user_id = (request.headers.get("X-User-ID") or "").strip()
            logger.warning("DEV_MODE authentication bypass in use; disable for deployment")
            return user_id or DEV_USER_ID

        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token",
            )

        scheme, separator, token = auth_header.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Expected Authorization: Bearer <token>",
            )

        try:
            response = supabase.auth.get_user(token.strip())
            user = getattr(response, "user", None)
            if user is None or not getattr(user, "id", None):
                raise ValueError("Supabase did not return a valid user")
            return str(user.id)
        except Exception:
            logger.warning("Supabase token verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token",
            ) from None
