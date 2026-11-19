# =============================================
# File:
# backend/core/component_base.py
#
# Description:
# Metadata-driven access to basic component metadata
#
# Responsibilities:
#   1. Read basic metadata from pulsar.components_base
#   2. Provide table and schema information
#   3. Provide primary_key metadata without interpreting it
#   4. Provide where_clause metadata without interpreting it
#   5. Cache component base metadata
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# =============================================
import traceback
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from core.query_error import handle_query_error

QUERY_COMPONENT_BASE_READ = "QUERY_COMPONENT_BASE_READ"

# ---------------------------------------------
# Component Base Cache
# ---------------------------------------------
_cache: dict[
    str,
    dict[str, Any]
] = {}

# ---------------------------------------------
# Pydantic Model
# ---------------------------------------------
class ComponentBaseConfig(BaseModel):
    component_name: str | None = None
    tbl_name: str
    schm_name: str
    primary_key: str
    where_clause: str | None = None

# ---------------------------------------------
# Reading Config Base from DB
# ---------------------------------------------
async def get_component_base(
    session: AsyncSession,
    component_name: str
) -> dict[str, Any]:
    """
    Fetch basic component metadata from
    pulsar.components_base.

    This function only retrieves metadata.
    It does not interpret primary_key or where_clause.
    """
    if not component_name:
        raise HTTPException(
            status_code=400,
            detail="Component name is required"
        )

    cache_key = component_name

    if cache_key in _cache:
        return _cache[cache_key]

    sql = text(
        """
        SELECT
            component_name,
            tbl_name,
            schm_name,
            primary_key,
            where_clause
        FROM pulsar.components_base
        WHERE component_name = :component_name
        LIMIT 1
        """
    )

    try:
        result = await session.execute(
            sql,
            {
                "component_name":
                    component_name
            }
        )
    except SQLAlchemyError as exc:
        await handle_query_error(
            session,
            exc,
            error_code=QUERY_COMPONENT_BASE_READ,
            schema_name="pulsar",
            table_name="components_base",
            component_name=component_name,
            file_name="backend/core/component_base.py",
            function_name="get_component_base",
            operation_name="SELECT_COMPONENT_BASE",
            parameters={
                "component_name": component_name
            },
            stack_trace=traceback.format_exc()
        )
        raise

    row = result.mappings().first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=(
                "No component base configuration found "
                f"for component '{component_name}'"
            )
        )

    config = dict(row)

    _cache[cache_key] = config

    return config

# ---------------------------------------------
# Cache Management
# ---------------------------------------------
def clear_component_base_cache(
    component_name: str | None = None
):
    """
    Clear cached component base metadata.

    When component_name is supplied, only that
    component is removed.

    When component_name is not supplied, the
    complete cache is cleared.
    """
    if component_name is None:
        _cache.clear()
        return

    _cache.pop(
        component_name,
        None
    )

# ---------------------------------------------
# Create Router for Each Component
# ---------------------------------------------
def create_component_base_router(
    component_name: str
) -> APIRouter:
    """
    Create FastAPI router for fetching
    base configuration of a component.
    """
    router = APIRouter(
        prefix=f"/{component_name}",
        tags=["Dynamic-Base"]
    )

    @router.get(
        "/base",
        response_model=ComponentBaseConfig
    )
    async def fetch_base(
        session: AsyncSession =
            Depends(get_async_session)
    ):
        return await get_component_base(
            session,
            component_name
        )

    return router

# ---------------------------------------------
# Important Learning Points
# ---------------------------------------------
# 1. components_base is the source of truth for basic component metadata.
# 2. component_base.py only retrieves metadata.
# 3. primary_key semantics belong exclusively to component_key.py.
# 4. where_clause semantics belong exclusively to component_where.py.
# 5. component_base.py does not resolve parm[n].
# 6. component_base.py does not construct record identity.
# 7. component_name is the identity of the component base metadata.
# 8. The cache is keyed only by component_name.
# 9. Cache invalidation is centralized in clear_component_base_cache().
# 10. field_mode belongs to component usage and field configuration,
#     not to components_base.
# 11. No table-specific component logic is hard-coded.
# 12. Database query failures are delegated to query_error.py.
# 13. Failed component-base queries are rolled back before error logging.
# 14. HTTP 404 for missing metadata is a business/runtime response,
#     not a database query error.