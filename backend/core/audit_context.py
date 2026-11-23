# ===============================================
# File: backend/core/audit_context.py
# Description: Authenticated request context for database audit triggers
# Modified: 2026-11-24 (Asia/Baku)
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from general.auth.dependencies import get_current_user
from general.user.schemas.user import UserProfileResponse


async def set_audit_context(
    session: AsyncSession,
    user_id: str,
    client_ip: str | None,
) -> None:
    """Set transaction-local identity values consumed by PostgreSQL audit triggers."""
    await session.execute(
        text(
            """
            SELECT
                set_config('pulsar.log_user', :user_id, TRUE),
                set_config('pulsar.log_ip', :client_ip, TRUE)
            """
        ),
        {
            "user_id": str(user_id),
            "client_ip": client_ip or "",
        },
    )


async def get_audited_session(
    request: Request,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an authenticated database session with transaction-local audit identity.

    The user identity comes only from the verified JWT-backed user record.
    The client IP comes from the ASGI connection, never from request payloads
    or an untrusted forwarding header.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive.",
        )

    if current_user.id is None:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user identity is not available.",
        )

    client_ip = (
        request.client.host
        if request.client is not None
        else None
    )

    await set_audit_context(
        session=session,
        user_id=str(current_user.id),
        client_ip=client_ip,
    )

    yield session
