"""Per-user rate limiting (Prompt 12).

Generation makes four LLM calls per document against a free Gemini tier, so a
public demo needs a ceiling. slowapi keys limits by a string we choose: here,
the authenticated Supabase user id (from the verified JWT), falling back to the
client IP for unauthenticated requests. Keeping the key logic in one place lets
every generation route share the same 10/hour/user budget.
"""

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from configs.settings import get_settings

GENERATION_RATE_LIMIT = "10/hour"


def user_id_key(request: Request) -> str:
    """Rate-limit bucket key: the JWT subject, else the client IP.

    We decode WITHOUT verifying the signature — this is only a bucket label,
    not an auth decision (the endpoint's CurrentUserId dependency still fully
    verifies the token). An attacker forging a `sub` only rate-limits himself.
    """
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ").strip()
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except jwt.PyJWTError:
            pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=user_id_key, default_limits=[])


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """429 with a clear, demo-friendly message."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": (
                "Generation rate limit reached (10 per hour on the free demo "
                "tier). Please try again later."
            )
        },
    )


# settings import kept so misconfiguration surfaces at import, not first request
_ = get_settings
