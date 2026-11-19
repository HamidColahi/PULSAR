
# ===============================================
# File:
# backend/datawindows/common/utils/datawindow.py
#
# Description:
# Universal DataWindow-like router for dynamic metadata access
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query
)
from fastapi.responses import JSONResponse
from sqlalchemy import (
    delete as sql_delete,
    select,
    text,
    update as sql_update
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from general.auth.dependencies import get_current_user
from general.user.models.user import User


router = APIRouter(
    tags=["Dynamic Metadata DataWindow"]
)


# =================================================
# Languages
# =================================================
@router.get("/languages")
async def get_languages(
    session: AsyncSession = Depends(
        get_async_session
    )
):
    """
    Fetch active language metadata for the application runtime.
    """
    query = text(
        """
        SELECT
            language_code,
            language_name,
            native_name,
            locale_code,
            is_rtl,
            calendar_code,
            date_format,
            datetime_format,
            first_day_of_week,
            decimal_separator,
            thousands_separator,
            digit_system,
            is_active,
            display_order
        FROM pulsar.t_language
        WHERE is_active = TRUE
        ORDER BY
            display_order,
            language_code
        """
    )

    try:
        result = await session.execute(query)
        return result.mappings().all()

    except SQLAlchemyError as exc:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Database error: {str(exc)}"
            }
        )


# =================================================
# User Access
# =================================================
@router.get("/user_access")
async def get_user_access(
    context_id: str = Query(
        ...,
        description="User context identifier"
    ),
    session: AsyncSession = Depends(
        get_async_session
    )
):
    """
    Fetch page access and CRUD permissions
    for a user context.
    """
    query = text(
        """
        SELECT
            c_user_id,
            page_key,
            c_page_state,
            pulsar.get_page_level(page_key) AS page_level,
            c_page_acc_start,
            c_page_acc_end,
            pulsar.get_page_type(page_key) AS page_type,
            c_page_view,
            c_page_insert,
            c_page_update,
            c_page_delete,
            c_page_renderer,
            log_time,
            log_state,
            log_user,
            log_ip
        FROM pulsar.t_page_usracc
        WHERE pulsar.get_page_type(page_key) = 'O'
          AND c_user_id = :context_id
        ORDER BY page_key
        """
    )

    try:
        result = await session.execute(
            query,
            {"context_id": context_id}
        )
        return result.mappings().all()

    except SQLAlchemyError as exc:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Database error: {str(exc)}"
            }
        )


# =================================================
# Renderer Types
# =================================================
@router.get("/renderer_types")
async def get_renderer_types(
    context_id: str = Query(
        ...,
        description="User context identifier"
    ),
    pagekey: str = Query(
        ...,
        description="Page key"
    ),
    session: AsyncSession = Depends(
        get_async_session
    )
):
    """
    Fetch Renderer types available to a user
    on a specific page.

    Availability is controlled by:
        1. User page access in t_page_usracc.
        2. Renderer permission in c_page_renderer.
        3. Renderer allow-list in t_page_usracc_renderer.
        4. Active Renderer definition in t_renderer_type.
    """
    query = text(
        """
        SELECT
            rt.c_renderer_type,
            rt.c_title,
            rt.c_handler_name,
            rt.c_description
        FROM pulsar.t_page_usracc_renderer ur
        INNER JOIN pulsar.t_page_usracc ua
            ON ua.c_user_id = ur.c_user_id
           AND ua.page_key = ur.page_key
        INNER JOIN pulsar.t_renderer_type rt
            ON rt.c_renderer_type = ur.c_renderer_type
        WHERE ur.c_user_id = :context_id
          AND ur.page_key = :pagekey
          AND pulsar.get_page_type(ua.page_key) = 'O'
          AND ua.c_page_state = 'active'
          AND ua.c_page_renderer = TRUE
          AND rt.c_state = 'active'
        ORDER BY
            rt.c_title,
            rt.c_renderer_type
        """
    )

    try:
        result = await session.execute(
            query,
            {
                "context_id": context_id,
                "pagekey": pagekey
            }
        )
        return result.mappings().all()

    except SQLAlchemyError as exc:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Database error: {str(exc)}"
            }
        )


# =================================================
# Cartable Panels
# =================================================
@router.get("/cartable_panels")
async def get_cartable_panels(
    cartable_key: str = Query(
        ...,
        description="Cartable component key"
    ),
    current_user: User = Depends(
        get_current_user
    ),
    session: AsyncSession = Depends(
        get_async_session
    )
):
    """
    Fetch active Cartable Panels authorized
    for the current authenticated user.

    PAGE panels are authorized against the target
    page's access metadata.

    FUNCTION panels are authorized against the
    host Cartable page's access metadata.

    Function execution is handled separately by
    the Panel Function Runtime.
    """
    if not cartable_key:
        raise HTTPException(
            status_code=400,
            detail="Cartable key is required"
        )

    query = text(
        """
        SELECT
            cp.c_cartable_key AS cartable_key,
            cp.c_panel_key AS panel_key,
            cp.c_panel_type AS panel_type,
            CASE
                WHEN cp.c_panel_type = 'PAGE' THEN (
                    SELECT NULLIF(BTRIM(dp."Page_desc"::text), '')
                    FROM pulsar.dynamic_page AS dp
                    WHERE dp.page_key = cp.c_panel_key
                    LIMIT 1
                )
                WHEN cp.c_panel_type = 'FUNCTION' THEN (
                    SELECT COALESCE(
                        NULLIF(BTRIM(fd.description), ''),
                        NULLIF(BTRIM(fd.documentation), '')
                    )
                    FROM pulsar.t_function_definition AS fd
                    WHERE fd.function_name = cp.c_panel_key
                      AND fd.is_active IS TRUE
                    ORDER BY fd.version DESC NULLS LAST
                    LIMIT 1
                )
                ELSE NULL
            END AS panel_description,
            CASE
                WHEN cp.c_panel_type = 'PAGE' AND EXISTS (
                    SELECT 1 FROM pulsar.dynamic_page AS dp
                    WHERE dp.page_key = cp.c_panel_key
                      AND NULLIF(BTRIM(dp."Page_desc"::text), '') IS NOT NULL
                ) THEN 'pulsar.dynamic_page.Page_desc'
                WHEN cp.c_panel_type = 'FUNCTION' AND EXISTS (
                    SELECT 1 FROM pulsar.t_function_definition AS fd
                    WHERE fd.function_name = cp.c_panel_key
                      AND fd.is_active IS TRUE
                      AND COALESCE(
                          NULLIF(BTRIM(fd.description), ''),
                          NULLIF(BTRIM(fd.documentation), '')
                      ) IS NOT NULL
                ) THEN 'pulsar.t_function_definition.description_or_documentation'
                ELSE NULL
            END AS description_source,
            cp.c_panel_state AS state,
            cp.c_panel_acc_level AS acc_level
        FROM pulsar.t_cartable_panel cp
        WHERE cp.c_cartable_key = :cartable_key
        AND cp.c_panel_state = 'active'
        AND (
                (
                    cp.c_panel_type = 'PAGE'
                    AND EXISTS (
                        SELECT 1
                        FROM pulsar.t_page_usracc ua
                        WHERE ua.page_key = cp.c_panel_key
                        AND ua.c_user_id = :user_id
                        AND ua.c_page_state = 'active'
                        AND ua.c_page_view = TRUE
                        AND CURRENT_TIMESTAMP >= ua.c_page_acc_start
                        AND CURRENT_TIMESTAMP <= ua.c_page_acc_end
                        AND pulsar.get_page_type(ua.page_key) = 'S'
                    )
                )
                OR
                (
                    cp.c_panel_type = 'FUNCTION'
                    AND EXISTS (
                        SELECT 1
                        FROM pulsar.t_function_usracc fa
                        WHERE fa.function_name = cp.c_panel_key
                        AND fa.c_user_id = :user_id
                        AND fa.c_func_state = 'active'
                        AND fa.c_func_renderer = TRUE
                        AND CURRENT_TIMESTAMP >= fa.c_func_acc_start
                        AND CURRENT_TIMESTAMP <= fa.c_func_acc_end
                    )
                )
        )
        ORDER BY cp.c_panel_key;
        """
    )

    try:
        result = await session.execute(
            query,
            {
                "cartable_key": cartable_key,
                "user_id": current_user.id
            }
        )
        return result.mappings().all()

    except SQLAlchemyError as exc:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Database error: {str(exc)}"
            }
        )


# =================================================
# Generic DataWindow Manager
# =================================================
class DataWindowManager:
    """
    Generic DataWindow helper.

    This class intentionally does not interpret:
        - primary_key metadata
        - where_clause metadata
        - parm[n]
        - table-specific field names

    Such semantics belong to their dedicated
    metadata/runtime layers.
    """

    def __init__(
        self,
        model,
        db_session
    ):
        self.model = model
        self.db = db_session

    async def retrieve_all(
        self,
        filters: dict[str, Any] | None = None
    ):
        """
        Retrieve records with optional equality filters.

        A WHERE clause is always applied when filters
        are supplied; unrestricted retrieval remains
        available explicitly for generic legacy use.
        """
        try:
            query = select(self.model)

            if filters:
                columns = {
                    column.name: column
                    for column in self.model.__table__.columns
                }

                for field, value in filters.items():
                    column = columns.get(field)

                    if column is None:
                        raise ValueError(
                            f"Invalid filter field: {field}"
                        )

                    query = query.where(column == value)

            result = await self.db.execute(query)
            return result.scalars().all()

        except (SQLAlchemyError, ValueError) as exc:
            raise Exception(
                f"Retrieve all failed: {str(exc)}"
            )

    async def retrieve_by_filters(
        self,
        filters: dict[str, Any]
    ):
        """
        Retrieve records using explicit metadata-driven
        field/value filters.
        """
        if not filters:
            raise ValueError(
                "Retrieve filters are required"
            )

        return await self.retrieve_all(filters=filters)

    async def retrieve_by_id(
        self,
        record_id
    ):
        """
        Legacy helper retained for compatibility.

        Generic dynamic runtime code should prefer
        centralized primary-key resolution instead of
        assuming a physical field named 'id'.
        """
        raise NotImplementedError(
            "Use centralized primary-key resolution "
            "for dynamic record retrieval"
        )

    async def insert(
        self,
        data: dict[str, Any]
    ):
        try:
            new_record = self.model(**data)
            self.db.add(new_record)
            await self.db.commit()
            await self.db.refresh(new_record)
            return new_record

        except SQLAlchemyError as exc:
            await self.db.rollback()
            raise Exception(
                f"Insert failed: {str(exc)}"
            )

    async def update(
        self,
        filters: dict[str, Any],
        data: dict[str, Any]
    ):
        """
        Update records using explicit field/value filters.

        Dynamic callers must supply filters resolved by
        the appropriate metadata layer.
        """
        if not filters:
            raise ValueError(
                "Update filters are required"
            )

        try:
            query = sql_update(self.model)

            columns = {
                column.name: column
                for column in self.model.__table__.columns
            }

            for field, value in filters.items():
                column = columns.get(field)

                if column is None:
                    raise ValueError(
                        f"Invalid filter field: {field}"
                    )

                query = query.where(column == value)

            query = query.values(**data)
            await self.db.execute(query)
            await self.db.commit()

            return {"message": "Update successful"}

        except (SQLAlchemyError, ValueError) as exc:
            await self.db.rollback()
            raise Exception(
                f"Update failed: {str(exc)}"
            )

    async def delete(
        self,
        filters: dict[str, Any]
    ):
        """
        Delete records using explicit field/value filters.
        """
        if not filters:
            raise ValueError(
                "Delete filters are required"
            )

        try:
            query = sql_delete(self.model)

            columns = {
                column.name: column
                for column in self.model.__table__.columns
            }

            for field, value in filters.items():
                column = columns.get(field)

                if column is None:
                    raise ValueError(
                        f"Invalid filter field: {field}"
                    )

                query = query.where(column == value)

            await self.db.execute(query)
            await self.db.commit()

            return {"message": "Delete successful"}

        except (SQLAlchemyError, ValueError) as exc:
            await self.db.rollback()
            raise Exception(
                f"Delete failed: {str(exc)}"
            )


# =================================================
# Important Learning Points
# =================================================
# 1. Active application languages are defined by pulsar.t_language.
# 2. User access remains metadata-driven through t_page_usracc.
# 3. Renderer availability is controlled by access metadata and
#    active renderer definitions.
# 4. Cartable panel existence is determined by t_cartable_panel.
# 5. Cartable PAGE panels use target-page access metadata.
# 6. Cartable FUNCTION panels use host-page access metadata.
# 7. Function execution belongs to a separate Panel Function Runtime.
# 8. Runtime context remains separate from panel authorization.
# 9. DataWindowManager no longer assumes a physical field named 'id'.
# 10. Dynamic record identity belongs to component_key.py.
# 11. where_clause resolution belongs to component_where.py.
# 12. parm[n] is not interpreted by the DataWindow layer.
# 13. No table-specific primary-key or where-clause mapping is hard-coded.
# 14. Generic update/delete operations require explicit filters.
