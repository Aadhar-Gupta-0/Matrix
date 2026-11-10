"""Focused tests for MentorMetrics security controls. No live credentials needed."""
import asyncio
import importlib.util
import io
import sys
import types
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

SOURCE = Path(__file__).resolve().parents[2]


def load_module(monkeypatch, module_name, relative_path, **stub_modules):
    for name, value in stub_modules.items():
        monkeypatch.setitem(sys.modules, name, value)
    spec = importlib.util.spec_from_file_location(module_name, SOURCE / relative_path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def stubs(monkeypatch):
    logger = types.ModuleType("src.backend.utils.logger")
    logger.setup_logger = lambda name: Mock()
    db = types.ModuleType("src.backend.utils.supabase_client")
    db.supabase = Mock()
    monkeypatch.setitem(sys.modules, "src.backend.utils.logger", logger)
    monkeypatch.setitem(sys.modules, "src.backend.utils.supabase_client", db)
    return db.supabase


def load_users(monkeypatch):
    backend = stubs(monkeypatch)
    users = load_module(monkeypatch, "upgrade_user_service", "src/backend/services/user_service.py")
    return users, backend


def request(**headers):
    return types.SimpleNamespace(headers=headers)


def test_production_rejects_forged_user_id(monkeypatch):
    monkeypatch.delenv("DEV_MODE", raising=False)
    users, db = load_users(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        users.UserService.get_user_id(request(**{"X-User-ID": "victim"}))
    assert exc.value.status_code == 401
    db.auth.get_user.assert_not_called()


def test_valid_verified_bearer_token(monkeypatch):
    monkeypatch.delenv("DEV_MODE", raising=False)
    users, db = load_users(monkeypatch)
    db.auth.get_user.return_value = types.SimpleNamespace(user=types.SimpleNamespace(id="user-123"))
    assert users.UserService.get_user_id(request(Authorization="Bearer verified-token")) == "user-123"
    db.auth.get_user.assert_called_once_with("verified-token")


def test_bad_token_never_falls_back_even_in_dev_mode(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("ENV", "development")
    users, db = load_users(monkeypatch)
    db.auth.get_user.side_effect = RuntimeError("invalid token")
    with pytest.raises(HTTPException) as exc:
        users.UserService.get_user_id(request(Authorization="Bearer fake", **{"X-User-ID": "victim"}))
    assert exc.value.status_code == 401


def test_dev_bypass_requires_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("ENV", "development")
    users, _ = load_users(monkeypatch)
    assert users.UserService.get_user_id(request(**{"X-User-ID": "local-user"})) == "local-user"


def test_admin_is_fail_closed(monkeypatch):
    stubs(monkeypatch)
    user_mod = types.ModuleType("src.backend.services.user_service")
    user_mod.UserService = types.SimpleNamespace(get_user_id=lambda req: "regular-user")
    monkeypatch.setitem(sys.modules, "src.backend.services.user_service", user_mod)
    admin = load_module(monkeypatch, "upgrade_admin_api", "src/backend/api/admin_api.py")
    monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
    with pytest.raises(HTTPException) as exc:
        admin.require_admin(request())
    assert exc.value.status_code == 403
    monkeypatch.setenv("ADMIN_USER_IDS", "admin-1, regular-user")
    assert admin.require_admin(request()) == "regular-user"


def test_session_status_filters_by_authenticated_owner(monkeypatch):
    db = stubs(monkeypatch)
    user_mod = types.ModuleType("src.backend.services.user_service")
    user_mod.UserService = types.SimpleNamespace(get_user_id=lambda req: "user-a")
    monkeypatch.setitem(sys.modules, "src.backend.services.user_service", user_mod)
    api = load_module(monkeypatch, "upgrade_sessions_api", "src/backend/api/sessions_api.py")
    query = db.table.return_value
    for name in ("select", "eq", "order", "limit"):
        getattr(query, name).return_value = query
    query.execute.return_value.data = []
    with pytest.raises(HTTPException) as exc:
        api.get_session_status("session-b", request())
    assert exc.value.status_code == 404
    assert any(call.args == ("user_id", "user-a") for call in query.eq.call_args_list)


class FakeUpload:
    def __init__(self, data, name="lesson.mp4", content_type="video/mp4", size=None):
        self.filename = name
        self.content_type = content_type
        self.size = size
        self.stream = io.BytesIO(data)

    async def read(self, n):
        return self.stream.read(n)


def test_upload_limit_and_format(monkeypatch):
    fm = load_module(monkeypatch, "upgrade_file_manager", "src/backend/utils/file_manager.py")
    monkeypatch.setenv("MAX_VIDEO_SIZE_MB", "1")
    assert asyncio.run(fm.FileManager.read_video_file(FakeUpload(b"x" * 1024))) == b"x" * 1024
    with pytest.raises(ValueError, match="size limit"):
        asyncio.run(fm.FileManager.read_video_file(FakeUpload(b"x" * (1024 * 1024 + 1))))
    with pytest.raises(ValueError, match="Unsupported"):
        asyncio.run(fm.FileManager.validate_video_file(FakeUpload(b"z", "lesson.exe", "video/mp4")))


def test_empty_upload_rejected(monkeypatch):
    fm = load_module(monkeypatch, "upgrade_file_manager_empty", "src/backend/utils/file_manager.py")
    with pytest.raises(ValueError, match="empty"):
        asyncio.run(fm.FileManager.read_video_file(FakeUpload(b"")))


def test_dev_bypass_is_disabled_in_production_even_if_misconfigured(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("ENV", "production")
    users, _ = load_users(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        users.UserService.get_user_id(request(**{"X-User-ID": "victim"}))
    assert exc.value.status_code == 401
