# ===============================================
# File:
# backend/core/page_runtime.py
#
# Description:
# Resolve dynamic page runtime from metadata and authenticated user permissions
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# Last Modified: 2026-11-24 (Asia/Baku)
# ===============================================
from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from general.auth.dependencies import get_current_user
from general.user.models.user import User

router = APIRouter()

# -----------------------------------------------
# Page Runtime
# -----------------------------------------------
@router.get(
    "/runtime/{page_key}"
)
async def get_page_runtime(
    page_key: str,
    current_user: User = Depends(
        get_current_user
    ),
    session: AsyncSession = Depends(
        get_async_session
    )
):
    """
    Resolve dynamic page runtime for the authenticated user.

    The authenticated JWT identity is the source of the user context.
    The client does not supply or select another user context.
    """
    if not page_key:
        raise HTTPException(
            status_code=400,
            detail="Page key is required"
        )

    user_id = current_user.id

    if (
        user_id is None or
        str(user_id).strip() == ""
    ):
        raise HTTPException(
            status_code=401,
            detail="Authenticated user identity is not available"
        )

    # -----------------------------------------
    # Resolve access and CRUD permissions
    # -----------------------------------------
    access_sql = text(
        """
        SELECT
            access_row.page_key,
            access_row.c_page_view,
            access_row.c_page_insert,
            access_row.c_page_update,
            access_row.c_page_delete,
            page_row.page_level
        FROM pulsar.t_page_usracc AS access_row
        INNER JOIN pulsar.dynamic_page AS page_row
            ON page_row.page_key = access_row.page_key
        WHERE access_row.c_user_id = :user_id
          AND access_row.page_key = :page_key
          AND access_row.c_page_state = 'active'
        LIMIT 1
        """
    )

    result = await session.execute(
        access_sql,
        {
            "user_id":
                user_id,
            "page_key":
                page_key
        }
    )

    access = (
        result
        .mappings()
        .first()
    )

    if not access:
        raise HTTPException(
            status_code=403,
            detail=(
                "Authenticated user has no access "
                "to this page"
            )
        )

    # -----------------------------------------
    # Resolve components belonging to page
    # -----------------------------------------
    component_sql = text(
        """
        SELECT
            component_name,
            field_mode
        FROM pulsar.dynamic_components
        WHERE page_key = :page_key
        ORDER BY
            component_name,
            field_mode
        """
    )

    result = await session.execute(
        component_sql,
        {
            "page_key":
                page_key
        }
    )

    rows = (
        result
        .mappings()
        .all()
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=(
                "No components found "
                "for this page"
            )
        )

    # -----------------------------------------
    # Group component modes
    # -----------------------------------------
    components = {}

    for row in rows:
        component_name = (
            row["component_name"]
        )

        field_mode = (
            row["field_mode"]
        )

        if (
            component_name not in
            components
        ):
            components[
                component_name
            ] = {
                "component_name":
                    component_name,
                "modes":
                    []
            }

        if (
            field_mode not in
            components[
                component_name
            ]["modes"]
        ):
            components[
                component_name
            ]["modes"].append(
                field_mode
            )

    return {
        "page_key":
            page_key,
        "page_level":
            access["page_level"],
        "context_id":
            str(user_id),
        "permissions": {
            "view":
                bool(
                    access[
                        "c_page_view"
                    ]
                ),
            "insert":
                bool(
                    access[
                        "c_page_insert"
                    ]
                ),
            "update":
                bool(
                    access[
                        "c_page_update"
                    ]
                ),
            "delete":
                bool(
                    access[
                        "c_page_delete"
                    ]
                )
        },
        "components":
            list(
                components.values()
            )
    }

# -----------------------------------------------
# Important Learning Points
# -----------------------------------------------
# 1. Page runtime is resolved from metadata.
# 2. The authenticated JWT user is the only user context.
# 3. The client cannot select another user's context_id.
# 4. Page access and CRUD permissions come from t_page_usracc.
# 5. dynamic_components determines page components and field modes.
# 6. component_name + field_mode remain the component runtime identity.
# 7. This module does not interpret primary_key.
# 8. This module does not interpret where_clause.
# 9. This module does not create or resolve parm[n].
# 10. Selected-record data is not part of page runtime metadata.
# 11. CRUD mutation endpoints must enforce permissions independently.
# 12. No table-specific component names are hard-coded.