from tools.release_preflight import inspect_environment


def codes(values):
    return {item["code"] for item in inspect_environment(values)}


def test_rejects_production_dev_bypass_and_debug_routes():
    issues = codes({"ENV": "production", "DEV_MODE": "true", "ENABLE_DEBUG_API": "true",
                    "MAX_VIDEO_SIZE_MB": "100"})
    assert {"DEVELOPMENT_BYPASS", "DEBUG_ENDPOINT", "NO_ADMINS", "NO_SUPABASE"} <= issues


def test_accepts_safe_configuration():
    assert inspect_environment({"ENV": "production", "DEV_MODE": "false",
                               "ENABLE_DEBUG_API": "false", "ADMIN_USER_IDS": "admin-id",
                               "SUPABASE_URL": "https://project.supabase.co",
                               "MAX_VIDEO_SIZE_MB": "100"}) == []


def test_limits_upload_range_and_type():
    for limit in ("0", "-1", "abc", "2048"):
        assert "UPLOAD_LIMIT" in codes({"MAX_VIDEO_SIZE_MB": limit})


def test_does_not_echo_secret_values():
    data = str(inspect_environment({"ENV": "production", "SUPABASE_KEY": "sensitive-secret"}))
    assert "sensitive-secret" not in data
