
"""
===============================================
File:
Pulsar/backend/core/dynamic_routes.py

Description:
Register metadata-driven dynamic component routes

Last Modified: 2026-11-16 12:33 (Asia/Baku)

Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
===============================================
"""

from typing import Dict, List
import logging

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.component_base import (
    create_component_base_router
)
from core.component_data import (
    create_component_data_router
)

logger = logging.getLogger(__name__)


# ============================================================
# Load Dynamic Components
# ============================================================
async def load_dynamic_components(
    session: AsyncSession
) -> List[Dict[str, str]]:
    """
    Load component_name + field_mode definitions from
    pulsar.dynamic_components.

    Duplicate metadata rows are removed before route registration.
    """
    sql = text(
        """
        SELECT DISTINCT
            component_name,
            field_mode
        FROM pulsar.dynamic_components
        WHERE component_name IS NOT NULL
          AND field_mode IS NOT NULL
        ORDER BY
            component_name,
            field_mode
        """
    )

    result = await session.execute(
        sql
    )

    rows = result.mappings().all()

    return [
        {
            "component_name": row["component_name"],
            "field_mode": row["field_mode"]
        }
        for row in rows
    ]


# ============================================================
# Register Dynamic Routes
# ============================================================
async def register_dynamic_routes(
    app: FastAPI,
    session: AsyncSession
):
    """
    Register dynamic routers from database metadata.

    Base routers are registered once per component.

    Data routers are registered once per component.
    """
    try:
        components = (
            await load_dynamic_components(
                session
            )
        )

        registered_base_routes = set()
        registered_data_components = set()

        for component in components:
            component_name = (
                component["component_name"]
            )

            field_mode = (
                component["field_mode"]
            )

            # ------------------------------------------------
            # Base Router
            # ------------------------------------------------
            if component_name not in (
                registered_base_routes
            ):
                base_router = (
                    create_component_base_router(
                        component_name
                    )
                )

                app.include_router(
                    base_router,
                    prefix="/dw",
                    tags=["Dynamic-Base"]
                )

                registered_base_routes.add(
                    component_name
                )

            # ------------------------------------------------
            # Data Router
            # ------------------------------------------------
            if component_name not in (
                registered_data_components
            ):
                data_router = (
                    create_component_data_router(
                        component_name,
                        field_mode
                    )
                )

                app.include_router(
                    data_router
                )

                registered_data_components.add(
                    component_name
                )

        logger.info(
            "Registered dynamic routes: "
            f"{len(registered_base_routes)} base, "
            f"{len(registered_data_components)} data"
        )

    except Exception as exc:
        logger.error(
            "Failed to register dynamic data routes: "
            f"{exc}",
            exc_info=True
        )
        raise


# ============================================================
# Important Learning Points
# ============================================================
# 1. dynamic_components is the source of truth for dynamic route discovery.
# 2. Base routes are unique by component_name.
# 3. Data routes are unique by component_name.
# 4. field_mode remains part of dynamic component metadata.
# 5. field_mode is not part of components_base.
# 6. Component configuration is retrieved through the general config API.
# 7. No table-specific component names are hard-coded.
# 8. No primary_key interpretation exists in this registration layer.
# 9. No where_clause interpretation exists in this registration layer.
# 10. No parm[n] creation or resolution exists in this registration layer.
