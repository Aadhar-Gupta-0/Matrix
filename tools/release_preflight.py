"""Read-only, secret-safe release configuration audit for Matrix.

Never prints configured credentials; does not connect to databases or services.
"""
from __future__ import annotations
import os
from collections.abc import Mapping


def inspect_environment(env: Mapping[str, str]) -> list[dict[str, str]]:
    issues = []
    def issue(code: str, severity: str, message: str) -> None:
        issues.append({"code": code, "severity": severity, "message": message})
    production = env.get("ENV", "").lower() in {"production", "prod"} or env.get("NODE_ENV", "").lower() == "production"
    if production:
        if env.get("DEV_MODE", "").lower() in {"1", "true", "yes"}:
            issue("DEVELOPMENT_BYPASS", "critical", "Development authentication bypass must be disabled.")
        if env.get("ENABLE_DEBUG_API", "").lower() in {"1", "true", "yes"}:
            issue("DEBUG_ENDPOINT", "high", "Disable debug endpoints in production.")
        if not env.get("ADMIN_USER_IDS", "").strip():
            issue("NO_ADMINS", "high", "Configure explicit admin identities for production.")
        if not env.get("SUPABASE_URL", "").strip():
            issue("NO_SUPABASE", "high", "Production Supabase URL has not been configured.")
    raw_size = env.get("MAX_VIDEO_SIZE_MB", "100").strip()
    try:
        size = int(raw_size)
        if size < 1 or size > 1024:
            issue("UPLOAD_LIMIT", "high", "Video upload limit must be between 1 and 1024 MB.")
    except (TypeError, ValueError):
        issue("UPLOAD_LIMIT", "high", "Video upload limit must be an integer.")
    return issues


if __name__ == "__main__":
    import json
    result = inspect_environment(os.environ)
    print(json.dumps({"status": "needs_attention" if result else "no_findings",
                      "issues": result}, indent=2))
    raise SystemExit(1 if result else 0)
