# Matrix / MentorMetrics — security and reliability changes

An independently maintained edition of MentorMetrics, originally co-created by Aadhar Gupta and Shreshth Behal and republished with permission.

## Improvements

1. Verified Supabase bearer authentication is the default. Development user impersonation is only possible with both `DEV_MODE=true` and an explicitly local/development/test environment. Invalid tokens never silently fall back to a mock identity.
2. Administrator audit logs now require a server-managed `ADMIN_USER_IDS` allowlist and bounded pagination.
3. Session status and listing enforce verified user ownership.
4. Video uploads validate file extension and MIME type, reject empty uploads and impose a configurable maximum size (`MAX_VIDEO_SIZE_MB`).
5. The sensitive debug API is disabled by default (`ENABLE_DEBUG_API=false`); live frame analysis requires authentication and limits encoded payload size.
6. Removed client-supplied `X-User-ID` from normal authenticated requests, restored intended login redirects and handled unknown upload progress totals.
7. Corrected frontend API environment setting and backend dependency install instructions.
8. AWS deployment is opt-in through GitHub Actions `workflow_dispatch` instead of automatic deployment on every push.
9. Added CI checks for frontend build and focused security tests.

## Setup

Configure real credentials in a local `.env` (do not commit it). Use `.env.example` as a guide.

Frontend:
```bash
npm ci
npm run dev
```

Backend (requires Python 3.10+, FFmpeg, and AI dependencies):
```bash
python -m venv .venv
# Activate your virtual environment
pip install -r requirements-backend.txt
uvicorn src.backend.main:app --reload
```

Run tests:
```bash
python -m pip install pytest fastapi
python -m pytest -q tests/security/test_upgrade_security.py
npm run build
```

## Important release precautions

- Video objects in the original implementation have **public storage URLs**. Migrate to a private bucket and signed URLs before handling real recordings.
- Audit *all* API routes, analytics, media processing, and Supabase RLS for ownership. The focused tests don't establish end-to-end isolation.
- Use a reverse-proxy request-body limit in addition to the application size limit.
- Unit tests do not validate production hosting, connected Supabase credentials, AI/FFmpeg processing, database migrations, or real user flows.
- Keep `DEV_MODE=false` and `ENABLE_DEBUG_API=false` in hosted environments. Only use a server-held Supabase key in backend deployments.
- This repo already contained a LICENSE when the source was imported; verify that its chosen terms are agreed upon by the co-creators.
