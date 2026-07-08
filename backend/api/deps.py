"""Shared FastAPI dependencies. user_id ALWAYS comes from the verified JWT,
never from the request body (CLAUDE.md security rule)."""

from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status

from configs.settings import get_settings


def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Verify the Supabase JWT (HS256, aud=authenticated) and return sub."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    token = authorization.removeprefix("Bearer ").strip()
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has no subject",
        )
    return str(user_id)


CurrentUserId = Annotated[str, Depends(get_current_user_id)]
