# ===============================================
# File: backend/general/permissions/service.py
# Description: Scoped PULSAR permission authorization
# Modified: 2026-11-26 (Asia/Baku)
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def require_page_view_access(
    session: AsyncSession,
    user_id: str,
    page_key: str,
) -> dict[str, Any]:
    """Require active, time-valid page view access for the authenticated user."""
    result = await session.execute(
        text(
            """
            SELECT
                page_key,
                c_page_view,
                c_page_insert,
                c_page_update,
                c_page_delete
            FROM pulsar.t_page_usracc
            WHERE c_user_id = :user_id
              AND page_key = :page_key
              AND c_page_state = 'active'
              AND c_page_view IS TRUE
              AND CURRENT_TIMESTAMP >= COALESCE(
                    c_page_acc_start,
                    '-infinity'::timestamptz
                  )
              AND CURRENT_TIMESTAMP <= COALESCE(
                    c_page_acc_end,
                    'infinity'::timestamptz
                  )
            LIMIT 1
            """
        ),
        {
            "user_id": str(user_id),
            "page_key": page_key,
        },
    )

    access = result.mappings().first()

    if access is None:
        raise HTTPException(
            status_code=403,
            detail="You do not have active view access to this page.",
        )

    return dict(access)


async def has_permission(
    session: AsyncSession,
    user_id: str,
    permission_code: str,
    page_key: str | None = None,
) -> bool:
    """Resolve an effective permission using the authenticated user's grants."""
    result = await session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pulsar.t_permit_usracc grant_row
                INNER JOIN pulsar.t_permission permission_row
                    ON permission_row.permission_id = grant_row.permission_id
                   AND permission_row.permission_code = grant_row.permission_code
                WHERE grant_row.c_user_id = :user_id
                  AND permission_row.permission_code = :permission_code
                  AND permission_row.is_active IS TRUE
                  AND grant_row.is_active IS TRUE
                  AND grant_row.valid_from <= CURRENT_TIMESTAMP
                  AND (
                        grant_row.valid_until IS NULL
                        OR CURRENT_TIMESTAMP < grant_row.valid_until
                  )
                  AND (
                        permission_row.scope_type = 'SYSTEM'
                        OR (
                            permission_row.scope_type = 'PAGE'
                            AND CAST(:page_key AS text) IS NOT NULL
                            AND permission_row.page_key = CAST(:page_key AS text)
                        )
                        OR (
                            permission_row.scope_type = 'SUBSYSTEM'
                            AND CAST(:page_key AS text) IS NOT NULL
                            AND EXISTS (
                                SELECT 1
                                FROM pulsar.t_permission page_definition
                                WHERE page_definition.permission_code = permission_row.permission_code
                                  AND page_definition.scope_type = 'PAGE'
                                  AND page_definition.page_key = CAST(:page_key AS text)
                                  AND page_definition.subsystem_key = COALESCE(
                                      permission_row.subsystem_key,
                                      permission_row.scope_key
                                  )
                                  AND page_definition.is_active IS TRUE
                            )
                        )
                  )
            )
            """
        ),
        {
            "user_id": str(user_id),
            "permission_code": permission_code,
            "page_key": page_key,
        },
    )

    return bool(result.scalar())


async def require_permission(
    session: AsyncSession,
    user_id: str,
    permission_code: str,
    page_key: str | None = None,
) -> None:
    """Raise HTTP 403 unless the user holds the requested effective permission."""
    if not await has_permission(
        session=session,
        user_id=user_id,
        permission_code=permission_code,
        page_key=page_key,
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Required permission is not assigned or is not currently valid.",
                "permission_code": permission_code,
                "page_key": page_key,
            },
        )


async def load_permission(
    session: AsyncSession,
    permission_id: int,
    *,
    for_update: bool = False,
) -> dict[str, Any]:
    """Load one permission definition by its stable catalog identity."""
    query = """
        SELECT
            permission_id,
            permission_code,
            permission_title,
            page_key,
            scope_type,
            scope_key,
            subsystem_key,
            is_active
        FROM pulsar.t_permission
        WHERE permission_id = :permission_id
    """

    if for_update:
        query += " FOR UPDATE"

    result = await session.execute(
        text(query),
        {"permission_id": permission_id},
    )

    permission = result.mappings().first()

    if permission is None:
        raise HTTPException(
            status_code=404,
            detail="Permission definition was not found.",
        )

    if not permission["is_active"]:
        raise HTTPException(
            status_code=409,
            detail="The permission definition is inactive.",
        )

    return dict(permission)


async def require_grant_authority(
    session: AsyncSession,
    grantor_user_id: str,
    target_permission: dict[str, Any],
) -> None:
    """
    Require SECURITY.PERMISSION.GRANT in a scope that covers the target definition.

    SYSTEM administrators can manage every scope.
    SUBSYSTEM administrators can manage definitions assigned to their subsystem_key.
    PAGE administrators can manage definitions for their exact page_key.
    """
    result = await session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pulsar.t_permit_usracc grant_row
                INNER JOIN pulsar.t_permission admin_permission
                    ON admin_permission.permission_id = grant_row.permission_id
                   AND admin_permission.permission_code = grant_row.permission_code
                WHERE grant_row.c_user_id = :grantor_user_id
                  AND admin_permission.permission_code = 'SECURITY.PERMISSION.GRANT'
                  AND admin_permission.is_active IS TRUE
                  AND grant_row.is_active IS TRUE
                  AND grant_row.valid_from <= CURRENT_TIMESTAMP
                  AND (
                        grant_row.valid_until IS NULL
                        OR CURRENT_TIMESTAMP < grant_row.valid_until
                  )
                  AND (
                        admin_permission.scope_type = 'SYSTEM'
                        OR (
                            admin_permission.scope_type = 'SUBSYSTEM'
                            AND (
                                :target_subsystem_key = admin_permission.scope_key
                                OR (
                                    :target_scope_type = 'SUBSYSTEM'
                                    AND :target_scope_key = admin_permission.scope_key
                                )
                            )
                        )
                        OR (
                            admin_permission.scope_type = 'PAGE'
                            AND :target_page_key IS NOT NULL
                            AND admin_permission.page_key = :target_page_key
                        )
                  )
            )
            """
        ),
        {
            "grantor_user_id": str(grantor_user_id),
            "target_subsystem_key": target_permission.get("subsystem_key"),
            "target_scope_type": target_permission.get("scope_type"),
            "target_scope_key": target_permission.get("scope_key"),
            "target_page_key": target_permission.get("page_key"),
        },
    )

    if not bool(result.scalar()):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to manage permissions in this scope.",
        )
