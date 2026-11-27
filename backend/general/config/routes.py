
# ===============================================
# File: Pulsar/backend/general/config/routes.py
#
# Description:
# Component configuration API routes
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# Last Modified: 2026-11-27 10:20 (Asia/Baku)
# ===============================================

from typing import Any, List, Literal
import json

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from pydantic import BaseModel, ConfigDict, Field

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from core.audit_context import get_audited_session
from core.component_base import get_component_base

from general.config.models import (
    ComponentsConfig,
    ComponentsBase,
    FieldDomainConfig,
)

from general.translation.models import TranslationDictionary
from general.auth.dependencies import get_current_user
from general.permissions.service import has_permission, require_permission

 
router = APIRouter(
    prefix="/config",
    tags=["component-config"],
)


# ===============================================
# Field Config Response Model
# ===============================================

class ComponentFieldConfig(BaseModel):
    field_name: str
    field_sort: int = 0
    field_sort_order: int | None = None
    aggregate_enabled: bool = False
    grid_width_px: int | None = None
    grid_min_width_px: int | None = None
    grid_max_width_px: int | None = None

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
                field_sort=int(config.field_sort or 0),
                field_sort_order=config.field_sort_order,
                aggregate_enabled=bool(config.aggregate_enabled),
                grid_width_px=config.grid_width_px,
                grid_min_width_px=config.grid_min_width_px,
                grid_max_width_px=config.grid_max_width_px,

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
# User Grid Sort Preferences
# ===============================================

class GridSortTerm(BaseModel):
    field: str
    direction: Literal["asc", "desc"]
    field_sort_order: int


class GridSortPreferenceUpdate(BaseModel):
    component_name: str
    field_mode: str = "list"
    sort_spec: List[GridSortTerm]


@router.get("/grid_sort")
async def read_grid_sort_preference(
    component_name: str = Query(...),
    field_mode: str = Query("list"),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
):
    """Return forced sorting metadata and the authenticated user's ordered preferences."""
    config_result = await db.execute(
        select(
            ComponentsConfig.field_name,
            ComponentsConfig.field_sort,
            ComponentsConfig.field_sort_order,
        ).where(
            ComponentsConfig.component_name == component_name,
            ComponentsConfig.field_mode == field_mode,
        )
    )
    field_configs = config_result.all()

    forced_sort_spec = []
    user_sortable_fields = set()

    for field_name, sort_mode, sort_order in field_configs:
        mode = int(sort_mode or 0)
        if mode == 1:
            user_sortable_fields.add(field_name)
        elif mode in (2, 3):
            if sort_order is None or int(sort_order) < 1:
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid forced sort order for field '{field_name}'.",
                )
            forced_sort_spec.append({
                "field": field_name,
                "direction": "desc" if mode == 2 else "asc",
                "field_sort_order": int(sort_order),
            })

    forced_sort_spec.sort(key=lambda item: item["field_sort_order"])

    user_result = await db.execute(
        text("""
            SELECT field_name, direction, field_sort_order
            FROM pulsar.t_user_grid_sort
            WHERE c_user_id = :user_id
              AND component_name = :component_name
              AND field_mode = :field_mode
            ORDER BY field_sort_order, field_name
        """),
        {
            "user_id": str(current_user.id),
            "component_name": component_name,
            "field_mode": field_mode,
        },
    )

    user_sort_spec = [
        {
            "field": row["field_name"],
            "direction": row["direction"],
            "field_sort_order": int(row["field_sort_order"]),
        }
        for row in user_result.mappings().all()
        if row["field_name"] in user_sortable_fields
        and row["direction"] in ("asc", "desc")
    ]

    return {
        "component_name": component_name,
        "field_mode": field_mode,
        "forced_sort_spec": forced_sort_spec,
        "user_sort_spec": user_sort_spec,
        "sort_spec": forced_sort_spec + user_sort_spec,
    }


@router.put("/grid_sort")
async def save_grid_sort_preference(
    payload: GridSortPreferenceUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
):
    """Persist ordered user-controlled sorting without changing forced metadata."""
    config_result = await db.execute(
        select(
            ComponentsConfig.field_name,
            ComponentsConfig.field_sort,
        ).where(
            ComponentsConfig.component_name == payload.component_name,
            ComponentsConfig.field_mode == payload.field_mode,
        )
    )
    modes = {
        field_name: int(sort_mode or 0)
        for field_name, sort_mode in config_result.all()
    }
    allowed_fields = {
        field_name for field_name, mode in modes.items()
        if mode == 1
    }

    requested_fields = [item.field for item in payload.sort_spec]
    if len(requested_fields) != len(set(requested_fields)):
        raise HTTPException(
            status_code=422,
            detail="A sort field can appear only once.",
        )

    invalid_fields = set(requested_fields) - allowed_fields
    if invalid_fields:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Sorting is not enabled for one or more fields.",
                "fields": sorted(invalid_fields),
            },
        )

    orders = [item.field_sort_order for item in payload.sort_spec]
    if any(order < 1 for order in orders) or len(orders) != len(set(orders)):
        raise HTTPException(
            status_code=422,
            detail="User sort orders must be unique positive integers.",
        )

    await db.execute(
        text("""
            DELETE FROM pulsar.t_user_grid_sort
            WHERE c_user_id = :user_id
              AND component_name = :component_name
              AND field_mode = :field_mode
        """),
        {
            "user_id": str(current_user.id),
            "component_name": payload.component_name,
            "field_mode": payload.field_mode,
        },
    )

    for item in payload.sort_spec:
        await db.execute(
            text("""
                INSERT INTO pulsar.t_user_grid_sort
                    (c_user_id, component_name, field_mode,
                     field_name, direction, field_sort_order, updated_at)
                VALUES
                    (:user_id, :component_name, :field_mode,
                     :field_name, :direction, :field_sort_order, CURRENT_TIMESTAMP)
            """),
            {
                "user_id": str(current_user.id),
                "component_name": payload.component_name,
                "field_mode": payload.field_mode,
                "field_name": item.field,
                "direction": item.direction,
                "field_sort_order": item.field_sort_order,
            },
        )

    await db.commit()

    return {
        "component_name": payload.component_name,
        "field_mode": payload.field_mode,
        "sort_spec": [
            item.model_dump()
            for item in payload.sort_spec
        ],
    }


# ===============================================
# User Grid Personalization
# ===============================================

GRID_LAYOUT_PERMISSION = "GRID.PERSONALIZATION.SAVE"


class GridLayoutUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_name: str = Field(min_length=1, max_length=255)
    field_mode: str = Field(default="list", min_length=1, max_length=80)
    layout: dict[str, Any]


class GridRuntimeStateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_name: str = Field(min_length=1, max_length=255)
    field_mode: str = Field(default="list", min_length=1, max_length=80)
    search_panel_open: bool
    search_filters: dict[str, Any] = Field(default_factory=dict)


async def _grid_field_metadata(
    db: AsyncSession,
    component_name: str,
    field_mode: str,
) -> dict[str, dict[str, Any]]:
    result = await db.execute(
        select(
            ComponentsConfig.field_name,
            ComponentsConfig.visible_in_grid,
            ComponentsConfig.visible_in_search,
        ).where(
            ComponentsConfig.component_name == component_name,
            ComponentsConfig.field_mode == field_mode,
        )
    )
    return {
        row.field_name: {
            "visible_in_grid": row.visible_in_grid is not False,
            "visible_in_search": row.visible_in_search is not False,
        }
        for row in result.all()
    }


def _validate_grid_layout(
    layout: dict[str, Any],
    field_metadata: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    allowed_fields = {
        field for field, metadata in field_metadata.items()
        if metadata["visible_in_grid"]
    }

    order = layout.get("column_order", [])
    widths = layout.get("column_widths", {})
    hidden = layout.get("hidden_columns", [])
    header_height = layout.get("header_height_px", 44)

    if not isinstance(order, list) or not all(isinstance(item, str) for item in order):
        raise HTTPException(status_code=422, detail="column_order must be a list of field names.")
    if len(order) != len(set(order)) or set(order) - allowed_fields:
        raise HTTPException(status_code=422, detail="column_order contains duplicate or unavailable fields.")

    if not isinstance(widths, dict) or set(widths) - allowed_fields:
        raise HTTPException(status_code=422, detail="column_widths contains unavailable fields.")
    normalized_widths = {}
    for field, width in widths.items():
        if isinstance(width, bool) or not isinstance(width, int) or not 48 <= width <= 2000:
            raise HTTPException(status_code=422, detail=f"Invalid width for field '{field}'.")
        normalized_widths[field] = width

    if not isinstance(hidden, list) or not all(isinstance(item, str) for item in hidden):
        raise HTTPException(status_code=422, detail="hidden_columns must be a list of field names.")
    if len(hidden) != len(set(hidden)) or set(hidden) - allowed_fields:
        raise HTTPException(status_code=422, detail="hidden_columns contains duplicate or unavailable fields.")
    if allowed_fields and allowed_fields.issubset(set(hidden)):
        raise HTTPException(status_code=422, detail="At least one Grid column must remain visible.")

    if isinstance(header_height, bool) or not isinstance(header_height, int) or not 28 <= header_height <= 240:
        raise HTTPException(status_code=422, detail="header_height_px must be between 28 and 240.")

    return {
        "column_order": order,
        "column_widths": normalized_widths,
        "hidden_columns": hidden,
        "header_height_px": header_height,
    }


def _validate_grid_search_filters(
    filters: dict[str, Any],
    field_metadata: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if len(filters) > 100:
        raise HTTPException(status_code=422, detail="At most 100 search fields can be saved.")

    normalized = {}
    for field, value in filters.items():
        metadata = field_metadata.get(field)
        if not metadata or not metadata["visible_in_search"]:
            raise HTTPException(
                status_code=422,
                detail=f"Search is not enabled for field '{field}'.",
            )
        if not isinstance(value, dict) or set(value) - {"from", "to"}:
            raise HTTPException(status_code=422, detail=f"Invalid search range for field '{field}'.")
        for bound in ("from", "to"):
            item = value.get(bound)
            if item is not None and not isinstance(item, (str, int, float, bool)):
                raise HTTPException(status_code=422, detail=f"Invalid {bound} value for field '{field}'.")
            if isinstance(item, str) and len(item) > 2000:
                raise HTTPException(status_code=422, detail=f"Search value for field '{field}' is too long.")
        if any(value.get(bound) not in (None, "") for bound in ("from", "to")):
            normalized[field] = {
                "from": value.get("from", ""),
                "to": value.get("to", ""),
            }
    return normalized


async def _record_grid_personalization_event(
    db: AsyncSession,
    user_id: str,
    component_name: str,
    field_mode: str,
    event_type: str,
    field_name: str | None = None,
    event_value: dict[str, Any] | None = None,
) -> None:
    await db.execute(
        text("""
            INSERT INTO pulsar.t_grid_personalization_event
                (c_user_id, component_name, field_mode,
                 event_type, field_name, event_value, occurred_at)
            VALUES
                (:user_id, :component_name, :field_mode,
                 :event_type, :field_name, CAST(:event_value AS JSONB), CURRENT_TIMESTAMP)
        """),
        {
            "user_id": user_id,
            "component_name": component_name,
            "field_mode": field_mode,
            "event_type": event_type,
            "field_name": field_name,
            "event_value": json.dumps(event_value or {}),
        },
    )


@router.get("/grid_preferences")
async def read_grid_preferences(
    component_name: str = Query(..., min_length=1, max_length=255),
    field_mode: str = Query("list", min_length=1, max_length=80),
    db: AsyncSession = Depends(get_audited_session),
    current_user = Depends(get_current_user),
):
    """Load the authenticated user's layout and runtime state for one Grid."""
    metadata = await _grid_field_metadata(db, component_name, field_mode)
    if not metadata:
        raise HTTPException(status_code=404, detail="Grid configuration was not found.")

    result = await db.execute(
        text("""
            SELECT layout, search_panel_open, search_filters
            FROM pulsar.t_user_grid_preference
            WHERE c_user_id = :user_id
              AND component_name = :component_name
              AND field_mode = :field_mode
        """),
        {
            "user_id": str(current_user.id),
            "component_name": component_name,
            "field_mode": field_mode,
        },
    )
    row = result.mappings().first()
    can_save_layout = await has_permission(
        db,
        str(current_user.id),
        GRID_LAYOUT_PERMISSION,
    )

    layout = {}
    filters = {}

    if row and row["layout"]:
        try:
            layout = _validate_grid_layout(
                dict(row["layout"]),
                metadata,
            )
        except HTTPException:
            layout = {}

    if row and row["search_filters"]:
        try:
            filters = _validate_grid_search_filters(
                dict(row["search_filters"]),
                metadata,
            )
        except HTTPException:
            filters = {}

    return {
        "component_name": component_name,
        "field_mode": field_mode,
        "layout": layout,
        "search_panel_open": row["search_panel_open"] if row else True,
        "search_filters": filters,
        "can_save_layout": can_save_layout,
    }


@router.put("/grid_preferences/layout")
async def save_grid_layout(
    payload: GridLayoutUpdate,
    db: AsyncSession = Depends(get_audited_session),
    current_user = Depends(get_current_user),
):
    """Save explicit personal column layout after checking the dedicated permission."""
    await require_permission(
        db,
        str(current_user.id),
        GRID_LAYOUT_PERMISSION,
    )
    metadata = await _grid_field_metadata(
        db,
        payload.component_name,
        payload.field_mode,
    )
    if not metadata:
        raise HTTPException(status_code=404, detail="Grid configuration was not found.")

    layout = _validate_grid_layout(payload.layout, metadata)

    previous_result = await db.execute(
        text("""
            SELECT layout
            FROM pulsar.t_user_grid_preference
            WHERE c_user_id = :user_id
              AND component_name = :component_name
              AND field_mode = :field_mode
        """),
        {
            "user_id": str(current_user.id),
            "component_name": payload.component_name,
            "field_mode": payload.field_mode,
        },
    )
    previous_row = previous_result.mappings().first()
    previous_layout = dict(previous_row["layout"] or {}) if previous_row else {}
    previous_hidden = set(previous_layout.get("hidden_columns", []))
    current_hidden = set(layout["hidden_columns"])

    await db.execute(
        text("""
            INSERT INTO pulsar.t_user_grid_preference
                (c_user_id, component_name, field_mode, layout, updated_at)
            VALUES
                (:user_id, :component_name, :field_mode, CAST(:layout AS JSONB), CURRENT_TIMESTAMP)
            ON CONFLICT (c_user_id, component_name, field_mode)
            DO UPDATE SET
                layout = EXCLUDED.layout,
                updated_at = CURRENT_TIMESTAMP
        """),
        {
            "user_id": str(current_user.id),
            "component_name": payload.component_name,
            "field_mode": payload.field_mode,
            "layout": json.dumps(layout),
        },
    )
    user_id = str(current_user.id)
    await _record_grid_personalization_event(
        db,
        user_id,
        payload.component_name,
        payload.field_mode,
        "LAYOUT_SAVED",
    )

    for field, field_config in metadata.items():
        if not field_config["visible_in_grid"]:
            continue
        was_visible = field not in previous_hidden
        is_visible = field not in current_hidden
        if was_visible != is_visible:
            await _record_grid_personalization_event(
                db,
                user_id,
                payload.component_name,
                payload.field_mode,
                "COLUMN_VISIBILITY",
                field,
                {"visible": is_visible},
            )

    for position, field in enumerate(layout["column_order"], start=1):
        await _record_grid_personalization_event(
            db,
            user_id,
            payload.component_name,
            payload.field_mode,
            "COLUMN_POSITION",
            field,
            {"position": position},
        )

    await db.commit()
    return {"layout": layout, "saved": True}


@router.patch("/grid_preferences/state")
async def save_grid_runtime_state(
    payload: GridRuntimeStateUpdate,
    db: AsyncSession = Depends(get_audited_session),
    current_user = Depends(get_current_user),
):
    """Auto-save the user's search panel state and last search filters."""
    metadata = await _grid_field_metadata(
        db,
        payload.component_name,
        payload.field_mode,
    )
    if not metadata:
        raise HTTPException(status_code=404, detail="Grid configuration was not found.")

    filters = _validate_grid_search_filters(payload.search_filters, metadata)
    await db.execute(
        text("""
            INSERT INTO pulsar.t_user_grid_preference
                (c_user_id, component_name, field_mode, search_panel_open, search_filters, updated_at)
            VALUES
                (:user_id, :component_name, :field_mode, :search_panel_open,
                 CAST(:search_filters AS JSONB), CURRENT_TIMESTAMP)
            ON CONFLICT (c_user_id, component_name, field_mode)
            DO UPDATE SET
                search_panel_open = EXCLUDED.search_panel_open,
                search_filters = EXCLUDED.search_filters,
                updated_at = CURRENT_TIMESTAMP
        """),
        {
            "user_id": str(current_user.id),
            "component_name": payload.component_name,
            "field_mode": payload.field_mode,
            "search_panel_open": payload.search_panel_open,
            "search_filters": json.dumps(filters),
        },
    )
    await db.commit()
    return {
        "search_panel_open": payload.search_panel_open,
        "search_filters": filters,
        "saved": True,
    }


@router.delete("/grid_preferences/layout")
async def reset_grid_layout(
    component_name: str = Query(..., min_length=1, max_length=255),
    field_mode: str = Query("list", min_length=1, max_length=80),
    db: AsyncSession = Depends(get_audited_session),
    current_user = Depends(get_current_user),
):
    """Remove only the personal layout; retain auto-saved search state."""
    await require_permission(
        db,
        str(current_user.id),
        GRID_LAYOUT_PERMISSION,
    )
    previous_result = await db.execute(
        text("""
            SELECT layout
            FROM pulsar.t_user_grid_preference
            WHERE c_user_id = :user_id
              AND component_name = :component_name
              AND field_mode = :field_mode
        """),
        {
            "user_id": str(current_user.id),
            "component_name": component_name,
            "field_mode": field_mode,
        },
    )
    previous_row = previous_result.mappings().first()
    previous_layout = dict(previous_row["layout"] or {}) if previous_row else {}
    previous_hidden = set(previous_layout.get("hidden_columns", []))

    default_fields_result = await db.execute(
        select(ComponentsConfig.field_name).where(
            ComponentsConfig.component_name == component_name,
            ComponentsConfig.field_mode == field_mode,
            ComponentsConfig.visible_in_grid.is_not(False),
        ).order_by(
            ComponentsConfig.ordering_index,
            ComponentsConfig.field_name,
        )
    )
    default_fields = [row[0] for row in default_fields_result.all()]

    await db.execute(
        text("""
            UPDATE pulsar.t_user_grid_preference
            SET layout = '{}'::JSONB,
                updated_at = CURRENT_TIMESTAMP
            WHERE c_user_id = :user_id
              AND component_name = :component_name
              AND field_mode = :field_mode
        """),
        {
            "user_id": str(current_user.id),
            "component_name": component_name,
            "field_mode": field_mode,
        },
    )
    user_id = str(current_user.id)
    await _record_grid_personalization_event(
        db,
        user_id,
        component_name,
        field_mode,
        "LAYOUT_RESET",
    )

    for field in previous_hidden.intersection(default_fields):
        await _record_grid_personalization_event(
            db,
            user_id,
            component_name,
            field_mode,
            "COLUMN_VISIBILITY",
            field,
            {"visible": True},
        )

    for position, field in enumerate(default_fields, start=1):
        await _record_grid_personalization_event(
            db,
            user_id,
            component_name,
            field_mode,
            "COLUMN_POSITION",
            field,
            {"position": position},
        )
    await db.commit()
    return {"reset": True}


@router.get("/grid_personalization/analytics")
async def read_grid_personalization_analytics(
    component_name: str | None = Query(default=None, max_length=255),
    db: AsyncSession = Depends(get_audited_session),
    current_user = Depends(get_current_user),
):
    """Return aggregate Grid usage metrics for authorized system optimization."""
    await require_permission(
        db,
        str(current_user.id),
        "GRID.PERSONALIZATION.ANALYTICS",
    )

    layout_result = await db.execute(
        text("""
            SELECT
                component_name,
                field_mode,
                COUNT(*) FILTER (
                    WHERE event_type = 'LAYOUT_SAVED'
                ) AS layout_save_count,
                COUNT(*) FILTER (
                    WHERE event_type = 'LAYOUT_RESET'
                ) AS layout_reset_count,
                COUNT(DISTINCT c_user_id) AS participating_users,
                MAX(occurred_at) AS last_customized_at
            FROM pulsar.t_grid_personalization_event
            WHERE event_type IN ('LAYOUT_SAVED', 'LAYOUT_RESET')
              AND (:component_name IS NULL OR component_name = :component_name)
            GROUP BY component_name, field_mode
            ORDER BY layout_save_count DESC, component_name, field_mode
        """),
        {"component_name": component_name},
    )

    column_result = await db.execute(
        text("""
            SELECT
                component_name,
                field_mode,
                field_name,
                COUNT(*) FILTER (
                    WHERE event_type = 'COLUMN_VISIBILITY'
                      AND event_value ->> 'visible' = 'false'
                ) AS hide_count,
                COUNT(*) FILTER (
                    WHERE event_type = 'COLUMN_VISIBILITY'
                      AND event_value ->> 'visible' = 'true'
                ) AS show_count,
                COUNT(DISTINCT c_user_id) FILTER (
                    WHERE event_type = 'COLUMN_VISIBILITY'
                      AND event_value ->> 'visible' = 'false'
                ) AS users_who_hid_column,
                AVG((event_value ->> 'position')::NUMERIC) FILTER (
                    WHERE event_type = 'COLUMN_POSITION'
                ) AS average_position,
                COUNT(*) FILTER (
                    WHERE event_type = 'COLUMN_POSITION'
                ) AS position_samples
            FROM pulsar.t_grid_personalization_event
            WHERE field_name IS NOT NULL
              AND (:component_name IS NULL OR component_name = :component_name)
            GROUP BY component_name, field_mode, field_name
            ORDER BY component_name, field_mode, field_name
        """),
        {"component_name": component_name},
    )

    position_result = await db.execute(
        text("""
            SELECT
                component_name,
                field_mode,
                field_name,
                (event_value ->> 'position')::INTEGER AS display_position,
                COUNT(*) AS sample_count
            FROM pulsar.t_grid_personalization_event
            WHERE event_type = 'COLUMN_POSITION'
              AND (:component_name IS NULL OR component_name = :component_name)
            GROUP BY
                component_name,
                field_mode,
                field_name,
                (event_value ->> 'position')::INTEGER
            ORDER BY component_name, field_mode, field_name, display_position
        """),
        {"component_name": component_name},
    )

    return {
        "layout_customization": [
            dict(row) for row in layout_result.mappings().all()
        ],
        "column_usage": [
            dict(row) for row in column_result.mappings().all()
        ],
        "position_distribution": [
            dict(row) for row in position_result.mappings().all()
        ],
        "interpretation_note": (
            "Visibility and position metrics describe user behavior; "
            "they are not standalone measures of business importance."
        ),
    }


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
# 14. Personal Grid layouts are scoped by user, component, and field mode.
# 15. Layout mutations require GRID.PERSONALIZATION.SAVE.
# 16. Search panel state and search filters are saved independently of layout permission.
# 17. Personal preferences never update canonical component metadata.
# 18. Saved layout and filters are revalidated against current component metadata.
#
# ===============================================
