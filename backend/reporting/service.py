# ===============================================
# File: backend/reporting/service.py
# Description: Report definition, access, and metadata-driven runtime services
# Modified: 2026-11-24 (Asia/Baku)
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID
import json

from fastapi import HTTPException, Request
from sqlalchemy import and_, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.sqltypes import String

from core.component_data import (
    _build_model,
    _convert_value_for_column,
    apply_scope_query,
)
from core.component_where import (
    analyze_where_clause,
    resolve_runtime_parameters,
    resolve_where_request_scope,
)
from general.permissions.service import (
    has_permission,
    require_page_view_access,
)


FILTER_OPERATORS = {
    "EQ",
    "NE",
    "CONTAINS",
    "STARTS_WITH",
    "ENDS_WITH",
    "GT",
    "GTE",
    "LT",
    "LTE",
    "IN",
    "NOT_IN",
    "BETWEEN",
    "NOT_BETWEEN",
    "IS_NULL",
    "IS_NOT_NULL",
}

DYNAMIC_PARAMETERS = {
    "TODAY",
    "NOW",
    "CURRENT_USER",
    "CURRENT_PROFILE",
    "CURRENT_MONTH",
    "CURRENT_YEAR",
}


def json_safe(value: Any) -> Any:
    """Convert database values to JSON-compatible values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return str(value)


async def load_report(
    session: AsyncSession,
    report_id: UUID,
    *,
    for_update: bool = False,
) -> dict[str, Any]:
    """Load one report definition."""
    query = """
        SELECT
            report_id,
            page_key,
            source_component_name,
            owner_user_id,
            report_title,
            report_desc,
            sharing_policy,
            is_active,
            current_version,
            created_at,
            updated_at
        FROM pulsar.t_report
        WHERE report_id = :report_id
    """
    if for_update:
        query += " FOR UPDATE"

    result = await session.execute(
        text(query),
        {"report_id": str(report_id)},
    )
    report = result.mappings().first()

    if report is None:
        raise HTTPException(status_code=404, detail="Report was not found.")

    if not report["is_active"]:
        raise HTTPException(status_code=404, detail="Report is inactive.")

    return dict(report)


async def require_report_view_access(
    session: AsyncSession,
    report: dict[str, Any],
    user_id: str,
) -> None:
    """Require ownership, an active share, or public visibility."""
    if str(report["owner_user_id"]) == str(user_id):
        return

    if report["sharing_policy"] == "PUBLIC":
        return

    result = await session.execute(
        text(
            """
            SELECT 1
            FROM pulsar.t_report_share
            WHERE report_id = :report_id
              AND target_user_id = :user_id
              AND is_active IS TRUE
              AND permission_level IN ('VIEW', 'EDIT')
            LIMIT 1
            """
        ),
        {
            "report_id": str(report["report_id"]),
            "user_id": str(user_id),
        },
    )

    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this report.",
        )


async def can_edit_report(
    session: AsyncSession,
    report: dict[str, Any],
    user_id: str,
) -> bool:
    if str(report["owner_user_id"]) == str(user_id):
        return True

    share_result = await session.execute(
        text(
            """
            SELECT 1
            FROM pulsar.t_report_share
            WHERE report_id = :report_id
              AND target_user_id = :user_id
              AND is_active IS TRUE
              AND permission_level = 'EDIT'
            LIMIT 1
            """
        ),
        {
            "report_id": str(report["report_id"]),
            "user_id": str(user_id),
        },
    )

    if share_result.scalar_one_or_none() is not None:
        return True

    return await has_permission(
        session,
        user_id,
        "REPORT.DESIGN.EDIT",
        report["page_key"],
    )


async def require_report_edit_access(
    session: AsyncSession,
    report: dict[str, Any],
    user_id: str,
) -> None:
    if not await can_edit_report(session, report, user_id):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to edit this report.",
        )


async def require_report_delete_access(
    session: AsyncSession,
    report: dict[str, Any],
    user_id: str,
) -> None:
    if str(report["owner_user_id"]) == str(user_id):
        return

    if not await has_permission(
        session,
        user_id,
        "REPORT.DESIGN.DELETE",
        report["page_key"],
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to delete this report.",
        )


async def validate_report_page(
    session: AsyncSession,
    user_id: str,
    page_key: str,
    source_component_name: str,
) -> dict[str, Any]:
    """Validate Report.Gen metadata, page access, and the selected list component."""
    await require_page_view_access(
        session,
        user_id,
        page_key,
    )

    page_result = await session.execute(
        text(
            """
            SELECT page_key, page_level
            FROM pulsar.dynamic_page
            WHERE page_key = :page_key
            LIMIT 1
            """
        ),
        {"page_key": page_key},
    )
    page = page_result.mappings().first()

    if page is None or page["page_level"] != "Report.Gen":
        raise HTTPException(
            status_code=403,
            detail="Report Generator is not enabled for this page.",
        )

    component_result = await session.execute(
        text(
            """
            SELECT component_name
            FROM pulsar.dynamic_components
            WHERE page_key = :page_key
              AND component_name = :component_name
              AND field_mode = 'list'
            LIMIT 1
            """
        ),
        {
            "page_key": page_key,
            "component_name": source_component_name,
        },
    )

    if component_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=422,
            detail="The selected source component is not a list component of this page.",
        )

    base_result = await session.execute(
        text(
            """
            SELECT
                component_name,
                schm_name,
                tbl_name,
                primary_key,
                where_clause
            FROM pulsar.components_base
            WHERE component_name = :component_name
            LIMIT 1
            """
        ),
        {"component_name": source_component_name},
    )
    base = base_result.mappings().first()

    if base is None:
        raise HTTPException(
            status_code=422,
            detail="The selected source component has no base metadata.",
        )

    return dict(base)


async def load_report_definition(
    session: AsyncSession,
    report_id: UUID,
) -> dict[str, Any]:
    """Load report columns and reconstruct the normalized filter tree."""
    column_result = await session.execute(
        text(
            """
            SELECT
                field_name,
                display_order,
                width_px,
                is_visible,
                sort_direction,
                sort_order
            FROM pulsar.t_report_column
            WHERE report_id = :report_id
            ORDER BY display_order, field_name
            """
        ),
        {"report_id": str(report_id)},
    )

    filter_result = await session.execute(
        text(
            """
            SELECT
                filter_id,
                parent_filter_id,
                node_type,
                logical_operator,
                field_name,
                operator_code,
                value_json,
                parameter_code,
                display_order
            FROM pulsar.t_report_filter
            WHERE report_id = :report_id
            ORDER BY display_order, filter_id
            """
        ),
        {"report_id": str(report_id)},
    )

    nodes: dict[str, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []

    for row in filter_result.mappings().all():
        node_id = str(row["filter_id"])
        node = {
            "filter_id": node_id,
            "node_type": row["node_type"],
            "logical_operator": row["logical_operator"],
            "field_name": row["field_name"],
            "operator_code": row["operator_code"],
            "value": row["value_json"],
            "parameter_code": row["parameter_code"],
            "display_order": row["display_order"],
            "children": [],
        }
        nodes[node_id] = node

    for row in filter_result.mappings().all():
        node_id = str(row["filter_id"])
        parent_id = (
            str(row["parent_filter_id"])
            if row["parent_filter_id"] is not None
            else None
        )
        if parent_id and parent_id in nodes:
            nodes[parent_id]["children"].append(nodes[node_id])
        else:
            roots.append(nodes[node_id])

    return {
        "columns": [dict(row) for row in column_result.mappings().all()],
        "filters": roots,
    }


async def replace_report_definition(
    session: AsyncSession,
    report_id: UUID,
    columns: list[dict[str, Any]],
    filters: list[dict[str, Any]],
    *,
    user_id: str,
) -> dict[str, Any]:
    """Replace report layout and filter nodes after metadata validation."""
    await session.execute(
        text(
            "DELETE FROM pulsar.t_report_column WHERE report_id = :report_id"
        ),
        {"report_id": str(report_id)},
    )
    await session.execute(
        text(
            "DELETE FROM pulsar.t_report_filter WHERE report_id = :report_id"
        ),
        {"report_id": str(report_id)},
    )

    for index, column in enumerate(columns, start=1):
        await session.execute(
            text(
                """
                INSERT INTO pulsar.t_report_column
                (
                    report_id,
                    field_name,
                    display_order,
                    width_px,
                    is_visible,
                    sort_direction,
                    sort_order
                )
                VALUES
                (
                    :report_id,
                    :field_name,
                    :display_order,
                    :width_px,
                    :is_visible,
                    :sort_direction,
                    :sort_order
                )
                """
            ),
            {
                "report_id": str(report_id),
                "field_name": column["field_name"],
                "display_order": column.get("display_order", index),
                "width_px": column.get("width_px"),
                "is_visible": column.get("is_visible", True),
                "sort_direction": column.get("sort_direction"),
                "sort_order": column.get("sort_order"),
            },
        )

    async def insert_node(
        node: dict[str, Any],
        parent_id: str | None,
        order_index: int,
        depth: int,
    ) -> None:
        if depth > 12:
            raise HTTPException(
                status_code=422,
                detail="Report filter nesting exceeds the supported depth.",
            )

        node_type = node["node_type"]
        node_id = str(UUID(node["filter_id"])) if node.get("filter_id") else None

        result = await session.execute(
            text(
                """
                INSERT INTO pulsar.t_report_filter
                (
                    report_id,
                    parent_filter_id,
                    node_type,
                    logical_operator,
                    field_name,
                    operator_code,
                    value_json,
                    parameter_code,
                    display_order
                )
                VALUES
                (
                    :report_id,
                    :parent_filter_id,
                    :node_type,
                    :logical_operator,
                    :field_name,
                    :operator_code,
                    CAST(:value_json AS JSONB),
                    :parameter_code,
                    :display_order
                )
                RETURNING filter_id
                """
            ),
            {
                "report_id": str(report_id),
                "parent_filter_id": parent_id,
                "node_type": node_type,
                "logical_operator": node.get("logical_operator"),
                "field_name": node.get("field_name"),
                "operator_code": node.get("operator_code"),
                "value_json": (
                    json.dumps(node.get("value"), default=str)
                    if node.get("value") is not None
                    else None
                ),
                "parameter_code": node.get("parameter_code"),
                "display_order": node.get("display_order", order_index),
            },
        )

        inserted_id = str(result.scalar_one())

        for child_index, child in enumerate(node.get("children", []), start=1):
            await insert_node(
                child,
                inserted_id,
                child_index,
                depth + 1,
            )

    for index, node in enumerate(filters, start=1):
        await insert_node(node, None, index, 1)

    definition = await load_report_definition(
        session,
        report_id,
    )

    return definition


def _resolve_dynamic_parameter(
    parameter_code: str,
    user_id: str,
    profile_id: str,
) -> Any:
    code = (parameter_code or "").strip().upper()
    now = datetime.now(timezone.utc)

    if code == "TODAY":
        return date.today()
    if code == "NOW":
        return now
    if code == "CURRENT_USER":
        return user_id
    if code == "CURRENT_PROFILE":
        return profile_id
    if code == "CURRENT_MONTH":
        return date.today().replace(day=1)
    if code == "CURRENT_YEAR":
        return date.today().replace(month=1, day=1)

    raise HTTPException(
        status_code=422,
        detail=f"Unsupported report parameter: {parameter_code}",
    )


def _build_filter_expression(
    node: dict[str, Any],
    Model,
    field_configs: dict[str, dict[str, Any]],
    user_id: str,
    profile_id: str,
    depth: int = 1,
):
    if depth > 12:
        raise HTTPException(
            status_code=422,
            detail="Report filter nesting exceeds the supported depth.",
        )

    if node["node_type"] == "GROUP":
        children = [
            _build_filter_expression(
                child,
                Model,
                field_configs,
                user_id,
                profile_id,
                depth + 1,
            )
            for child in node.get("children", [])
        ]

        if not children:
            raise HTTPException(
                status_code=422,
                detail="A report filter group must contain at least one condition.",
            )

        return (
            and_(*children)
            if node["logical_operator"] == "AND"
            else or_(*children)
        )

    field_name = node["field_name"]
    metadata = field_configs.get(field_name)

    if metadata is None or metadata.get("visible_in_search") is not True:
        raise HTTPException(
            status_code=403,
            detail=f"Filtering is not enabled for field '{field_name}'.",
        )

    column = Model.__table__.columns.get(field_name)

    if column is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown report field '{field_name}'.",
        )

    operator_code = str(node["operator_code"]).upper()

    if operator_code not in FILTER_OPERATORS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported report filter operator '{operator_code}'.",
        )

    if operator_code == "IS_NULL":
        return getattr(Model, field_name).is_(None)

    if operator_code == "IS_NOT_NULL":
        return getattr(Model, field_name).is_not(None)

    if node.get("parameter_code"):
        if node["parameter_code"].upper() not in DYNAMIC_PARAMETERS:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported report parameter '{node['parameter_code']}'.",
            )
        value = _resolve_dynamic_parameter(
            node["parameter_code"],
            user_id,
            profile_id,
        )
    else:
        value = node.get("value")

    if value is None:
        raise HTTPException(
            status_code=422,
            detail="A value or dynamic parameter is required for this filter.",
        )

    if operator_code in {"IN", "NOT_IN"}:
        if not isinstance(value, list) or not value or len(value) > 500:
            raise HTTPException(
                status_code=422,
                detail="IN filters require a non-empty list of at most 500 values.",
            )
        values = [
            _convert_value_for_column(column, item)
            for item in value
        ]
        expression = getattr(Model, field_name).in_(values)
        return ~expression if operator_code == "NOT_IN" else expression

    if operator_code in {"BETWEEN", "NOT_BETWEEN"}:
        if not isinstance(value, list) or len(value) != 2:
            raise HTTPException(
                status_code=422,
                detail="BETWEEN filters require exactly two values.",
            )
        lower = _convert_value_for_column(column, value[0])
        upper = _convert_value_for_column(column, value[1])
        expression = getattr(Model, field_name).between(lower, upper)
        return ~expression if operator_code == "NOT_BETWEEN" else expression

    if operator_code in {"CONTAINS", "STARTS_WITH", "ENDS_WITH"}:
        if not isinstance(column.type, String):
            raise HTTPException(
                status_code=422,
                detail=f"Text matching is not supported for field '{field_name}'.",
            )
        pattern = str(value)
        if operator_code == "CONTAINS":
            pattern = f"%{pattern}%"
        elif operator_code == "STARTS_WITH":
            pattern = f"{pattern}%"
        else:
            pattern = f"%{pattern}"
        return getattr(Model, field_name).ilike(pattern)

    clean_value = _convert_value_for_column(column, value)
    target = getattr(Model, field_name)

    expressions = {
        "EQ": lambda: target == clean_value,
        "NE": lambda: target != clean_value,
        "GT": lambda: target > clean_value,
        "GTE": lambda: target >= clean_value,
        "LT": lambda: target < clean_value,
        "LTE": lambda: target <= clean_value,
    }

    return expressions[operator_code]()


async def execute_report(
    session: AsyncSession,
    request: Request,
    report: dict[str, Any],
    definition: dict[str, Any],
    *,
    user_id: str,
    profile_id: str,
    selected_record: dict[str, Any] | None = None,
    runtime_context: dict[str, Any] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Execute a report against the current user's page and component scope."""
    page_key = report["page_key"]
    component_name = report["source_component_name"]

    base_result = await session.execute(
        text(
            """
            SELECT
                component_name,
                schm_name,
                tbl_name,
                primary_key,
                where_clause
            FROM pulsar.components_base
            WHERE component_name = :component_name
            LIMIT 1
            """
        ),
        {"component_name": component_name},
    )
    base_row = base_result.mappings().first()

    if base_row is None:
        raise HTTPException(status_code=422, detail="Report source metadata was not found.")

    base = dict(base_row)

    Model = await _build_model(
        session,
        base,
        component_name,
        request,
        "report_runtime",
    )

    config_result = await session.execute(
        text(
            """
            SELECT
                field_name,
                visible_in_grid,
                visible_in_search,
                field_sort,
                field_sort_order
            FROM pulsar.components_config
            WHERE component_name = :component_name
              AND field_mode = 'list'
            """
        ),
        {"component_name": component_name},
    )

    field_configs = {
        row["field_name"]: dict(row)
        for row in config_result.mappings().all()
    }

    available_fields = {
        field_name
        for field_name, metadata in field_configs.items()
        if metadata.get("visible_in_grid") is True
        and field_name in Model.__table__.columns
    }

    selected_columns = [
        column
        for column in definition["columns"]
        if column["is_visible"] is True
    ]

    requested_fields = [
        column["field_name"]
        for column in selected_columns
    ]

    if not requested_fields:
        raise HTTPException(
            status_code=422,
            detail="At least one report column must be visible.",
        )

    invalid_fields = set(requested_fields) - available_fields
    if invalid_fields:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "One or more report columns are not visible in the source component.",
                "fields": sorted(invalid_fields),
            },
        )

    resolver = dict(runtime_context or {})
    resolver.update({
        "user_id": user_id,
        "c_user_id": user_id,
        "profile_id": profile_id,
        "current_user": user_id,
        "current_profile": profile_id,
    })

    definitions = analyze_where_clause(base.get("where_clause"))
    selected_scope_record = dict(selected_record or {})

    for definition in definitions:
        field_name = str(definition.get("field", "")).lower()
        if field_name == "profile_id":
            selected_scope_record[definition["field"]] = profile_id
        elif field_name in {"c_user_id", "user_id"}:
            selected_scope_record[definition["field"]] = user_id

    parameters, _ = resolve_runtime_parameters(
        definitions,
        selected_scope_record,
    )
    resolver.update(parameters)

    scope_filters, raw_sql = await resolve_where_request_scope(
        where_clause=base.get("where_clause"),
        component_name=component_name,
        resolver=resolver,
        model=Model,
        converter=_convert_value_for_column,
    )

    if raw_sql:
        raise HTTPException(
            status_code=500,
            detail=(
                "Report execution requires a structured metadata where_clause. "
                "Unstructured SQL scope expressions are not accepted."
            ),
        )

    query = select(
        *[
            getattr(Model, field_name)
            for field_name in requested_fields
        ]
    )

    count_query = select(func.count()).select_from(Model)

    if scope_filters:
        query = apply_scope_query(query, Model, scope_filters)
        count_query = apply_scope_query(count_query, Model, scope_filters)
    elif raw_sql:
        query = query.where(text(raw_sql))
        count_query = count_query.where(text(raw_sql))

    filter_expressions = [
        _build_filter_expression(
            node,
            Model,
            field_configs,
            user_id,
            profile_id,
        )
        for node in definition["filters"]
    ]

    if filter_expressions:
        combined_filter = and_(*filter_expressions)
        query = query.where(combined_filter)
        count_query = count_query.where(combined_filter)

    forced_sort = []
    user_sort = []

    for field_name, metadata in field_configs.items():
        sort_mode = int(metadata.get("field_sort") or 0)
        if sort_mode in (2, 3):
            if field_name not in Model.__table__.columns:
                continue
            forced_sort.append((
                int(metadata.get("field_sort_order") or 0),
                field_name,
                "desc" if sort_mode == 2 else "asc",
            ))

    forced_sort.sort(key=lambda item: item[0])
    forced_fields = {item[1] for item in forced_sort}

    for column in definition["columns"]:
        field_name = column["field_name"]
        direction = column.get("sort_direction")
        sort_order = column.get("sort_order")

        if (
            direction in ("asc", "desc")
            and int(field_configs.get(field_name, {}).get("field_sort") or 0) == 1
            and field_name not in forced_fields
            and sort_order is not None
        ):
            user_sort.append((
                int(sort_order),
                field_name,
                direction,
            ))

    user_sort.sort(key=lambda item: item[0])

    order_terms = []
    for _, field_name, direction in forced_sort + user_sort:
        column = getattr(Model, field_name)
        order_terms.append(
            column.asc() if direction == "asc" else column.desc()
        )

    if order_terms:
        query = query.order_by(*order_terms)

    count_result = await session.execute(count_query)
    total = int(count_result.scalar_one())

    result = await session.execute(
        query.limit(limit).offset(offset)
    )

    rows = [
        {
            key: json_safe(value)
            for key, value in dict(row).items()
        }
        for row in result.mappings().all()
    ]

    return {
        "report_id": str(report["report_id"]),
        "page_key": page_key,
        "source_component_name": component_name,
        "total": total,
        "limit": limit,
        "offset": offset,
        "columns": selected_columns,
        "rows": rows,
        "sort": [
            {
                "field": field_name,
                "direction": direction,
                "forced": True,
            }
            for _, field_name, direction in forced_sort
        ] + [
            {
                "field": field_name,
                "direction": direction,
                "forced": False,
            }
            for _, field_name, direction in user_sort
        ],
    }
