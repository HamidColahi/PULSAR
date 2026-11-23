# ===============================================
# File: backend/general/permissions/routes.py
# Description: PULSAR permission catalog and user grant APIs
# Modified: 2026-11-24 (Asia/Baku)
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit_context import get_audited_session
from general.auth.dependencies import get_current_user
from general.user.schemas.user import UserProfileResponse
from general.permissions.service import (
    load_permission,
    require_grant_authority,
)


router = APIRouter(
    prefix="/permissions",
    tags=["Permission Management"],
)


class PermissionGrantCreate(BaseModel):
    c_user_id: UUID
    permission_id: int = Field(ge=1)
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: datetime | None = None
    grant_reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_period(self):
        if self.valid_from.tzinfo is None:
            raise ValueError("valid_from must include a timezone.")

        if self.valid_until is not None:
            if self.valid_until.tzinfo is None:
                raise ValueError("valid_until must include a timezone.")
            if self.valid_until <= self.valid_from:
                raise ValueError("valid_until must be later than valid_from.")

        return self


class PermissionGrantUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool | None = None
    grant_reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_period(self):
        if self.valid_from is not None and self.valid_from.tzinfo is None:
            raise ValueError("valid_from must include a timezone.")

        if self.valid_until is not None and self.valid_until.tzinfo is None:
            raise ValueError("valid_until must include a timezone.")

        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_until <= self.valid_from
        ):
            raise ValueError("valid_until must be later than valid_from.")

        return self


async def _ensure_active_target_user(
    session: AsyncSession,
    user_id: UUID,
) -> None:
    result = await session.execute(
        text(
            """
            SELECT c_user_id
            FROM pulsar.t_user
            WHERE c_user_id = :user_id
              AND c_user_active IS TRUE
            """
        ),
        {"user_id": str(user_id)},
    )

    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=404,
            detail="The target user does not exist or is inactive.",
        )


@router.get("/catalog")
async def read_permission_catalog(
    page_key: str | None = Query(default=None),
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    """Return active permission definitions; only the catalog is exposed, not grant authority."""
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Your account is inactive.")

    result = await session.execute(
        text(
            """
            SELECT
                permission_id,
                permission_code,
                permission_title,
                page_key,
                scope_type,
                scope_key,
                subsystem_key,
                permission_desc
            FROM pulsar.t_permission
            WHERE is_active IS TRUE
              AND (
                    :page_key IS NULL
                    OR page_key = :page_key
                    OR page_key IS NULL
              )
            ORDER BY
                permission_code,
                scope_type,
                scope_key NULLS FIRST,
                page_key NULLS FIRST
            """
        ),
        {"page_key": page_key},
    )

    return [dict(row) for row in result.mappings().all()]


@router.get("/me")
async def read_my_permission_history(
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    """Return the authenticated user's complete permission grant history."""
    result = await session.execute(
        text(
            """
            SELECT
                grant_row.permit_id,
                grant_row.permission_id,
                grant_row.permission_code,
                permission_row.permission_title,
                permission_row.page_key,
                permission_row.scope_type,
                permission_row.scope_key,
                permission_row.subsystem_key,
                grant_row.valid_from,
                grant_row.valid_until,
                grant_row.is_active,
                grant_row.granted_by,
                grantor_user.c_user_full_name AS granted_by_name,
                grantor_user.c_user_email AS granted_by_email,
                grant_row.granted_at,
                grant_row.revoked_by,
                revoker_user.c_user_full_name AS revoked_by_name,
                revoker_user.c_user_email AS revoked_by_email,
                grant_row.revoked_at,
                grant_row.grant_reason,
                (
                    permission_row.is_active IS TRUE
                    AND grant_row.is_active IS TRUE
                    AND grant_row.valid_from <= CURRENT_TIMESTAMP
                    AND (
                        grant_row.valid_until IS NULL
                        OR CURRENT_TIMESTAMP < grant_row.valid_until
                    )
                ) AS is_effective
            FROM pulsar.t_permit_usracc grant_row
            INNER JOIN pulsar.t_permission permission_row
                ON permission_row.permission_id = grant_row.permission_id
               AND permission_row.permission_code = grant_row.permission_code
            LEFT JOIN pulsar.t_user grantor_user
                ON grantor_user.c_user_id = grant_row.granted_by
            LEFT JOIN pulsar.t_user revoker_user
                ON revoker_user.c_user_id = grant_row.revoked_by
            WHERE grant_row.c_user_id = :user_id
            ORDER BY grant_row.granted_at DESC, grant_row.permit_id DESC
            """
        ),
        {"user_id": str(current_user.id)},
    )

    return [dict(row) for row in result.mappings().all()]


@router.get("/users/lookup")
async def lookup_permission_target_users(
    query: str = Query(min_length=2, max_length=120),
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    """Search active users for administrators without exposing the full user directory."""
    authority_result = await session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pulsar.t_permit_usracc grant_row
                INNER JOIN pulsar.t_permission permission_row
                    ON permission_row.permission_id = grant_row.permission_id
                   AND permission_row.permission_code = grant_row.permission_code
                WHERE grant_row.c_user_id = :user_id
                  AND permission_row.permission_code = 'SECURITY.PERMISSION.GRANT'
                  AND permission_row.is_active IS TRUE
                  AND grant_row.is_active IS TRUE
                  AND grant_row.valid_from <= CURRENT_TIMESTAMP
                  AND (
                        grant_row.valid_until IS NULL
                        OR CURRENT_TIMESTAMP < grant_row.valid_until
                  )
            )
            """
        ),
        {"user_id": str(current_user.id)},
    )

    if not bool(authority_result.scalar()):
        raise HTTPException(
            status_code=403,
            detail="Permission administration is not available to this user.",
        )

    result = await session.execute(
        text(
            """
            SELECT
                c_user_id,
                c_user_email,
                c_user_full_name
            FROM pulsar.t_user
            WHERE c_user_active IS TRUE
              AND (
                    c_user_email ILIKE :search
                    OR c_user_full_name ILIKE :search
              )
            ORDER BY c_user_full_name NULLS LAST, c_user_email
            LIMIT 20
            """
        ),
        {"search": "%" + query.strip() + "%"},
    )

    return [
        {
            "c_user_id": str(row["c_user_id"]),
            "c_user_email": row["c_user_email"],
            "c_user_full_name": row["c_user_full_name"],
        }
        for row in result.mappings().all()
    ]


@router.get("/users/{user_id}/grants")
async def read_user_permission_history(
    user_id: UUID,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    """Return only grant records within the caller's permission-administration scope."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Use /permissions/me to read your own permission history.",
        )

    authority_result = await session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pulsar.t_permit_usracc admin_grant
                INNER JOIN pulsar.t_permission admin_permission
                    ON admin_permission.permission_id = admin_grant.permission_id
                   AND admin_permission.permission_code = admin_grant.permission_code
                WHERE admin_grant.c_user_id = :admin_user_id
                  AND admin_permission.permission_code = 'SECURITY.PERMISSION.GRANT'
                  AND admin_permission.is_active IS TRUE
                  AND admin_grant.is_active IS TRUE
                  AND admin_grant.valid_from <= CURRENT_TIMESTAMP
                  AND (
                        admin_grant.valid_until IS NULL
                        OR CURRENT_TIMESTAMP < admin_grant.valid_until
                  )
            )
            """
        ),
        {"admin_user_id": str(current_user.id)},
    )

    if not bool(authority_result.scalar()):
        raise HTTPException(
            status_code=403,
            detail="Permission administration is not available to this user.",
        )

    result = await session.execute(
        text(
            """
            SELECT
                grant_row.permit_id,
                grant_row.permission_id,
                grant_row.permission_code,
                permission_row.permission_title,
                permission_row.page_key,
                permission_row.scope_type,
                permission_row.scope_key,
                permission_row.subsystem_key,
                grant_row.valid_from,
                grant_row.valid_until,
                grant_row.is_active,
                grant_row.granted_by,
                grantor_user.c_user_full_name AS granted_by_name,
                grantor_user.c_user_email AS granted_by_email,
                grant_row.granted_at,
                grant_row.revoked_by,
                revoker_user.c_user_full_name AS revoked_by_name,
                revoker_user.c_user_email AS revoked_by_email,
                grant_row.revoked_at,
                grant_row.grant_reason,
                (
                    permission_row.is_active IS TRUE
                    AND grant_row.is_active IS TRUE
                    AND grant_row.valid_from <= CURRENT_TIMESTAMP
                    AND (
                        grant_row.valid_until IS NULL
                        OR CURRENT_TIMESTAMP < grant_row.valid_until
                    )
                ) AS is_effective
            FROM pulsar.t_permit_usracc grant_row
            INNER JOIN pulsar.t_permission permission_row
                ON permission_row.permission_id = grant_row.permission_id
               AND permission_row.permission_code = grant_row.permission_code
            LEFT JOIN pulsar.t_user grantor_user
                ON grantor_user.c_user_id = grant_row.granted_by
            LEFT JOIN pulsar.t_user revoker_user
                ON revoker_user.c_user_id = grant_row.revoked_by
            WHERE grant_row.c_user_id = :user_id
              AND EXISTS (
                    SELECT 1
                    FROM pulsar.t_permit_usracc admin_grant
                    INNER JOIN pulsar.t_permission admin_permission
                        ON admin_permission.permission_id = admin_grant.permission_id
                       AND admin_permission.permission_code = admin_grant.permission_code
                    WHERE admin_grant.c_user_id = :admin_user_id
                      AND admin_permission.permission_code = 'SECURITY.PERMISSION.GRANT'
                      AND admin_permission.is_active IS TRUE
                      AND admin_grant.is_active IS TRUE
                      AND admin_grant.valid_from <= CURRENT_TIMESTAMP
                      AND (
                            admin_grant.valid_until IS NULL
                            OR CURRENT_TIMESTAMP < admin_grant.valid_until
                      )
                      AND (
                            admin_permission.scope_type = 'SYSTEM'
                            OR (
                                admin_permission.scope_type = 'SUBSYSTEM'
                                AND (
                                    permission_row.subsystem_key = admin_permission.scope_key
                                    OR (
                                        permission_row.scope_type = 'SUBSYSTEM'
                                        AND permission_row.scope_key = admin_permission.scope_key
                                    )
                                )
                            )
                            OR (
                                admin_permission.scope_type = 'PAGE'
                                AND permission_row.page_key = admin_permission.page_key
                            )
                      )
              )
            ORDER BY grant_row.granted_at DESC, grant_row.permit_id DESC
            """
        ),
        {
            "user_id": str(user_id),
            "admin_user_id": str(current_user.id),
        },
    )

    return [dict(row) for row in result.mappings().all()]


@router.post("/grants", status_code=201)
async def create_permission_grant(
    payload: PermissionGrantCreate,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    """Grant a catalog permission within the authenticated administrator's scope."""
    if payload.c_user_id == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Administrators cannot grant permissions to themselves.",
        )

    await _ensure_active_target_user(
        session,
        payload.c_user_id,
    )

    permission = await load_permission(
        session,
        payload.permission_id,
    )

    await require_grant_authority(
        session,
        str(current_user.id),
        permission,
    )

    result = await session.execute(
        text(
            """
            INSERT INTO pulsar.t_permit_usracc
            (
                c_user_id,
                permission_id,
                permission_code,
                valid_from,
                valid_until,
                is_active,
                granted_by,
                granted_at,
                grant_reason
            )
            VALUES
            (
                :c_user_id,
                :permission_id,
                :permission_code,
                :valid_from,
                :valid_until,
                TRUE,
                :granted_by,
                CURRENT_TIMESTAMP,
                :grant_reason
            )
            RETURNING permit_id
            """
        ),
        {
            "c_user_id": str(payload.c_user_id),
            "permission_id": permission["permission_id"],
            "permission_code": permission["permission_code"],
            "valid_from": payload.valid_from,
            "valid_until": payload.valid_until,
            "granted_by": str(current_user.id),
            "grant_reason": payload.grant_reason,
        },
    )

    permit_id = result.scalar_one()
    await session.commit()

    return {
        "permit_id": permit_id,
        "c_user_id": str(payload.c_user_id),
        "permission_id": permission["permission_id"],
        "permission_code": permission["permission_code"],
        "granted_by": str(current_user.id),
    }


@router.patch("/grants/{permit_id}")
async def update_permission_grant(
    permit_id: int,
    payload: PermissionGrantUpdate,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    """Change the validity or status of an existing grant without deleting its history."""
    result = await session.execute(
        text(
            """
            SELECT
                grant_row.permit_id,
                grant_row.c_user_id,
                grant_row.permission_id,
                grant_row.permission_code,
                grant_row.valid_from,
                grant_row.valid_until,
                grant_row.is_active,
                grant_row.revoked_by,
                grant_row.revoked_at,
                grant_row.grant_reason,
                permission_row.page_key,
                permission_row.scope_type,
                permission_row.scope_key,
                permission_row.subsystem_key
            FROM pulsar.t_permit_usracc grant_row
            INNER JOIN pulsar.t_permission permission_row
                ON permission_row.permission_id = grant_row.permission_id
               AND permission_row.permission_code = grant_row.permission_code
            WHERE grant_row.permit_id = :permit_id
            FOR UPDATE OF grant_row
            """
        ),
        {"permit_id": permit_id},
    )

    grant = result.mappings().first()

    if grant is None:
        raise HTTPException(status_code=404, detail="Permission grant was not found.")

    await require_grant_authority(
        session,
        str(current_user.id),
        dict(grant),
    )

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=422, detail="No grant changes were supplied.")

    valid_from = changes.get("valid_from", grant["valid_from"])
    valid_until = changes.get("valid_until", grant["valid_until"])

    if valid_from.tzinfo is None:
        raise HTTPException(status_code=422, detail="valid_from must include a timezone.")

    if valid_until is not None:
        if valid_until.tzinfo is None or valid_until <= valid_from:
            raise HTTPException(
                status_code=422,
                detail="valid_until must include a timezone and be later than valid_from.",
            )

    is_active = changes.get("is_active", grant["is_active"])
    if is_active is None:
        raise HTTPException(
            status_code=422,
            detail="is_active must be true or false.",
        )

    if "is_active" in changes:
        revoked_by = None if is_active else str(current_user.id)
        revoked_at = None if is_active else datetime.now(timezone.utc)
    else:
        revoked_by = grant["revoked_by"]
        revoked_at = grant["revoked_at"]

    await session.execute(
        text(
            """
            UPDATE pulsar.t_permit_usracc
            SET
                valid_from = :valid_from,
                valid_until = :valid_until,
                is_active = :is_active,
                grant_reason = :grant_reason,
                revoked_by = :revoked_by,
                revoked_at = :revoked_at
            WHERE permit_id = :permit_id
            """
        ),
        {
            "valid_from": valid_from,
            "valid_until": valid_until,
            "is_active": is_active,
            "grant_reason": changes.get("grant_reason", grant["grant_reason"]),
            "revoked_by": revoked_by,
            "revoked_at": revoked_at,
            "permit_id": permit_id,
        },
    )

    await session.commit()

    return {
        "permit_id": permit_id,
        "is_active": is_active,
        "revoked_by": revoked_by,
        "revoked_at": revoked_at,
    }


@router.delete("/grants/{permit_id}", status_code=200)
async def revoke_permission_grant(
    permit_id: int,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    """Revoke a grant by deactivating it; the source row remains available for audit."""
    result = await session.execute(
        text(
            """
            SELECT
                grant_row.permit_id,
                grant_row.c_user_id,
                permission_row.page_key,
                permission_row.scope_type,
                permission_row.scope_key,
                permission_row.subsystem_key
            FROM pulsar.t_permit_usracc grant_row
            INNER JOIN pulsar.t_permission permission_row
                ON permission_row.permission_id = grant_row.permission_id
               AND permission_row.permission_code = grant_row.permission_code
            WHERE grant_row.permit_id = :permit_id
            FOR UPDATE OF grant_row
            """
        ),
        {"permit_id": permit_id},
    )

    grant = result.mappings().first()

    if grant is None:
        raise HTTPException(status_code=404, detail="Permission grant was not found.")

    await require_grant_authority(
        session,
        str(current_user.id),
        dict(grant),
    )

    await session.execute(
        text(
            """
            UPDATE pulsar.t_permit_usracc
            SET
                is_active = FALSE,
                revoked_by = :revoked_by,
                revoked_at = CURRENT_TIMESTAMP
            WHERE permit_id = :permit_id
              AND is_active IS TRUE
            """
        ),
        {
            "revoked_by": str(current_user.id),
            "permit_id": permit_id,
        },
    )

    await session.commit()

    return {
        "permit_id": permit_id,
        "is_active": False,
        "revoked_by": str(current_user.id),
    }
