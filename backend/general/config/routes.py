
# ===============================================
# File: Pulsar/backend/general/config/routes.py
#
# Description:
# Component configuration API routes
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from pydantic import BaseModel

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from core.component_base import get_component_base

from general.config.models import (
    ComponentsConfig,
    ComponentsBase,
    FieldDomainConfig,
)

from general.translation.models import TranslationDictionary

 
router = APIRouter(
    prefix="/config",
    tags=["component-config"],
)


# ===============================================
# Field Config Response Model
# ===============================================

class ComponentFieldConfig(BaseModel):
    field_name: str

    label: str | None = None

    # Physical component identity.
    schema_name: str | None = None
    table_name: str | None = None

    # UI control metadata.
    control_type: str | None = None
    accepted_mime_types: List[str] | None = None
    max_file_size_bytes: int | None = None
    search_mode: str | None = None

    visible_in_grid: bool | None = None
    visible_in_form: bool | None = None
    visible_in_search: bool | None = None

    is_readonly: bool | None = None

    default_value: str | None = None
    label_color: str | None = None
    ordering_index: int | None = None

    # Domain metadata derived from field_domain_config.
    domain_control_type: str | None = None

    # Compatibility fields derived from domain_control_type.
    is_ddlistbox: bool = False
    is_dddw: bool = False

    # Available only for DDDW fields.
    dddw_select_sql: str | None = None

    field_mode: str | None = None

    null_able: bool | None = None
    required: bool = False

    # Reserved for backward compatibility.
    max_length: int | None = None


# ===============================================
# Component Base Response Model
# ===============================================

class ComponentBaseConfig(BaseModel):
    component_name: str | None = None

    tbl_name: str
    schm_name: str

    primary_key: str
    where_clause: str | None = None


# ===============================================
# Component Config Endpoint
# ===============================================

@router.get(
    "/component_config",
    response_model=List[ComponentFieldConfig],
)
async def read_component_config(
    component_name: str = Query(...),
    field_mode: str = Query(...),
    language_code: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Return component field metadata and domain configuration.

    Component presentation metadata is read from components_config.

    Physical component identity is read from components_base.

    Domain configuration is resolved through:
        components_config
            -> components_base
            -> field_domain_config

    DDLB values are provided by the dedicated domain options API.
    """

    stmt = (
        select(
            ComponentsConfig,

            FieldDomainConfig.control_type.label(
                "domain_control_type"
            ),

            FieldDomainConfig.dddw_select_sql.label(
                "domain_dddw_select_sql"
            ),

            ComponentsBase.schm_name.label(
                "schema_name"
            ),

            ComponentsBase.tbl_name.label(
                "table_name"
            ),
        )
        .select_from(ComponentsConfig)

        .outerjoin(
            ComponentsBase,
            ComponentsBase.component_name
            == ComponentsConfig.component_name,
        )

        .outerjoin(
            FieldDomainConfig,
            and_(
                FieldDomainConfig.schema_name
                == ComponentsBase.schm_name,

                FieldDomainConfig.table_name
                == ComponentsBase.tbl_name,

                FieldDomainConfig.field_name
                == ComponentsConfig.field_name,
            ),
        )

        .where(
            ComponentsConfig.component_name == component_name,
            ComponentsConfig.field_mode == field_mode,
        )

        .order_by(
            ComponentsConfig.ordering_index,
            ComponentsConfig.field_name,
        )
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=(
                "No component config found for "
                f"{component_name}:{field_mode}"
            ),
        )

    # Resolve field labels when a language is provided.
    labels_by_item_code = {}

    if language_code:
        item_codes = [
            f"{row[0].component_name}.{row[0].field_name}"
            for row in rows
        ]

        label_stmt = (
            select(
                TranslationDictionary.item_code,
                TranslationDictionary.translated_text,
            )

            .where(
                TranslationDictionary.item_code.in_(item_codes),

                TranslationDictionary.language_code
                == language_code,
            )
        )

        label_result = await db.execute(label_stmt)

        labels_by_item_code = dict(
            label_result.all()
        )

    configs = []

    for row in rows:
        config = row[0]

        raw_domain_control_type = (
            row.domain_control_type
        )

        domain_control_type = (
            raw_domain_control_type.upper()
            if raw_domain_control_type
            else None
        )

        is_ddlistbox = (
            domain_control_type == "DDLB"
        )

        is_dddw = (
            domain_control_type == "DDDW"
        )

        item_code = (
            f"{config.component_name}."
            f"{config.field_name}"
        )

        label = (
            labels_by_item_code.get(item_code)
            if language_code
            else None
        )

        if not label:
            label = config.field_name

        configs.append(
            ComponentFieldConfig(
                field_name=config.field_name,
                label=label,

                # Physical component identity.
                schema_name=row.schema_name,
                table_name=row.table_name,

                # UI control metadata.
                control_type=config.control_type,
                accepted_mime_types=config.accepted_mime_types,
                max_file_size_bytes=config.max_file_size_bytes,
                search_mode=config.search_mode,

                visible_in_grid=config.visible_in_grid,
                visible_in_form=config.visible_in_form,
                visible_in_search=config.visible_in_search,

                is_readonly=config.is_readonly,

                default_value=config.default_value,
                label_color=config.label_color,
                ordering_index=config.ordering_index,

                # Domain metadata.
                domain_control_type=domain_control_type,

                is_ddlistbox=is_ddlistbox,
                is_dddw=is_dddw,

                dddw_select_sql=(
                    row.domain_dddw_select_sql
                    if is_dddw
                    else None
                ),

                field_mode=config.field_mode,

                null_able=config.null_able,
                required=config.null_able is False,
            )
        )

    return configs


# ===============================================
# Component Base Endpoint
# ===============================================

@router.get(
    "/component_base",
    response_model=ComponentBaseConfig,
)
async def read_component_base(
    component_name: str = Query(...),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Return intrinsic component metadata.

    primary_key and where_clause are returned as metadata.
    Their runtime semantics belong to their dedicated resolvers.

    field_mode is not accepted because it is not part of
    components_base.
    """

    try:
        config = await get_component_base(
            db,
            component_name,
        )

        return ComponentBaseConfig(**config)

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


# ===============================================
# Important Learning Points
# ===============================================
#
# 1. components_config is the source of presentation metadata.
# 2. component_name + field_mode identify component configuration.
# 3. Field ordering is metadata-driven.
# 4. Physical component identity comes from components_base.
# 5. UI control_type is independent from domain_control_type.
# 6. DDLB/DDDW metadata comes from field_domain_config.
# 7. DDLB values come from the dedicated domain options API.
# 8. DDDW SQL comes from field_domain_config.dddw_select_sql.
# 9. primary_key semantics belong to component_key.py.
# 10. where_clause semantics belong to component_where.py.
# 11. parm[n] is not created or resolved here.
# 12. Field labels use the translation dictionary.
# 13. Nullable database booleans remain nullable in the API.
#
# ===============================================
