# =================================================
# File: backend/general/functions/function_result_formatter.py
#
# Description:
# Generic formatter for PostgreSQL function results.
# Normalizes values for metadata-selected JSON, table,
# chart, text, value, and tree presentation.
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# Modified: 2026-10-09 01:00 (Asia/Baku)
# =================================================

import json
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any


SUPPORTED_DISPLAY_TYPES = frozenset({
    "json",
    "table",
    "chart",
    "text",
    "value",
    "tree",
})


def _json_safe(value: Any) -> Any:
    """Convert database values into JSON-compatible Python values."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    if hasattr(value, "model_dump") and callable(value.model_dump):
        return _json_safe(value.model_dump())

    if hasattr(value, "_asdict") and callable(value._asdict):
        return _json_safe(value._asdict())

    return str(value)


def _detect_display_type(
    result: Any,
    result_kind: str | None,
) -> str:
    """Infer a display type for automatic presentation selection."""

    normalized_kind = (
        result_kind.strip().lower()
        if isinstance(result_kind, str)
        else None
    )

    if normalized_kind in {"rows", "collection", "table"}:
        return "table"

    if normalized_kind in {"json", "document", "record"}:
        return "json"

    if isinstance(result, (dict, list)):
        return "json"

    return "value"


def _build_columns(
    rows: list[dict[str, Any]],
    configured_columns: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build or normalize table columns."""

    if configured_columns is not None:
        columns = []

        for column in configured_columns:
            if not isinstance(column, dict):
                raise ValueError(
                    "Each configured table column must be an object."
                )

            field = column.get("field")

            if not isinstance(field, str) or not field:
                raise ValueError(
                    "Each configured table column requires a field."
                )

            columns.append({
                **column,
                "field": field,
                "title": column.get("title", field),
            })

        return columns

    columns = []
    seen: set[str] = set()

    for row in rows:
        for key in row:
            name = str(key)

            if name in seen:
                continue

            seen.add(name)
            columns.append({
                "field": name,
                "title": name,
            })

    return columns


def _build_chart_data(
    result: Any,
    options: dict[str, Any],
) -> dict[str, Any]:
    """Prepare chart data using metadata-supplied field mappings."""

    rows = result if isinstance(result, list) else [result]

    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(
            "Chart rendering requires an object or a list of objects."
        )

    category_field = options.get("category_field")
    value_field = options.get("value_field")
    series_field = options.get("series_field")

    if not rows:
        return {
            "category_field": category_field,
            "value_field": value_field,
            "series_field": series_field,
            "data": [],
        }

    available_fields = list(
        dict.fromkeys(
            key
            for row in rows
            for key in row
        )
    )

    if category_field is None and available_fields:
        category_field = available_fields[0]

    if value_field is None:
        value_field = next(
            (
                key
                for key in available_fields
                if key != category_field
                and all(
                    isinstance(row.get(key), (int, float, Decimal))
                    and not isinstance(row.get(key), bool)
                    for row in rows
                )
            ),
            None,
        )

    if category_field not in available_fields:
        raise ValueError(
            "The configured chart category field does not exist."
        )

    if value_field not in available_fields:
        raise ValueError(
            "A valid numeric chart value field could not be determined."
        )

    if series_field is not None and series_field not in available_fields:
        raise ValueError(
            "The configured chart series field does not exist."
        )

    return {
        "category_field": category_field,
        "value_field": value_field,
        "series_field": series_field,
        "data": rows,
        "chart_type": options.get("chart_type", "bar"),
    }


def _build_tree_data(
    result: Any,
    options: dict[str, Any],
) -> dict[str, Any]:
    """Prepare hierarchical data using metadata-supplied field mappings."""

    if not isinstance(result, (dict, list)):
        raise ValueError(
            "Tree rendering requires an object or a list of objects."
        )

    children_field = options.get("children_field", "children")
    label_field = options.get("label_field", "label")
    key_field = options.get("key_field", "key")
    root_label_field = options.get("root_label_field")

    for option_name, option_value in (
        ("children_field", children_field),
        ("label_field", label_field),
        ("key_field", key_field),
    ):
        if not isinstance(option_value, str) or not option_value:
            raise ValueError(
                f"A valid {option_name} is required for tree rendering."
            )

    if root_label_field is not None and (
        not isinstance(root_label_field, str) or not root_label_field
    ):
        raise ValueError(
            "A valid root_label_field is required."
        )

    return {
        "key_field": key_field,
        "label_field": label_field,
        "children_field": children_field,
        "root_label_field": root_label_field,
        "expand_all": bool(options.get("expand_all", False)),
        "show_root": bool(options.get("show_root", True)),
        "data": result,
    }


def _resolve_display_type(
    requested_type: str,
    normalized_result: Any,
    result_kind: str | None,
    allowed_types: set[str],
) -> str:
    """Resolve a requested or inferred type against active metadata."""

    if requested_type != "auto":
        if requested_type not in allowed_types:
            raise ValueError(
                "The requested display type is not configured for this function."
            )

        return requested_type

    inferred_type = _detect_display_type(
        normalized_result,
        result_kind,
    )

    if inferred_type in allowed_types:
        return inferred_type

    for fallback_type in ("json", "table", "text", "value"):
        if fallback_type in allowed_types:
            return fallback_type

    raise ValueError(
        "Automatic display selection could not find a compatible configured type."
    )


def format_function_result(
    result: Any,
    result_kind: str | None = None,
    display_options: dict[str, Any] | None = None,
    allowed_display_types: set[str] | list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """
    Normalize a PostgreSQL function result for frontend rendering.

    Display permissions and options must originate from active,
    matching function output metadata.
    """

    options = display_options or {}

    if not isinstance(options, dict):
        raise ValueError(
            "Display options must be a JSON object."
        )

    if allowed_display_types is None:
        raise ValueError(
            "Allowed display types must be supplied from function output metadata."
        )

    allowed_types = {
        value.strip().lower()
        for value in allowed_display_types
        if isinstance(value, str) and value.strip()
    }

    unsupported_types = allowed_types - SUPPORTED_DISPLAY_TYPES

    if unsupported_types:
        raise ValueError(
            "One or more configured display types have no formatter implementation."
        )

    if not allowed_types:
        raise ValueError(
            "No active display types are configured for this function."
        )

    requested_type = str(
        options.get("display_type", "auto")
    ).strip().lower()

    normalized_result = _json_safe(result)

    display_type = _resolve_display_type(
        requested_type=requested_type,
        normalized_result=normalized_result,
        result_kind=result_kind,
        allowed_types=allowed_types,
    )

    payload: dict[str, Any] = {
        "display_type": display_type,
        "title": options.get("title"),
        "data": normalized_result,
        "columns": [],
        "chart": None,
        "tree": None,
        "metadata": {
            "result_kind": result_kind,
            "allowed_display_types": sorted(allowed_types),
        },
    }

    if display_type == "table":
        if isinstance(normalized_result, list):
            rows = normalized_result
        elif isinstance(normalized_result, dict):
            rows = [normalized_result]
        else:
            rows = []

        if not all(isinstance(row, dict) for row in rows):
            raise ValueError(
                "Table rendering requires an object or a list of objects."
            )

        payload["data"] = rows
        payload["columns"] = _build_columns(
            rows,
            options.get("columns")
            if isinstance(options.get("columns"), list)
            else None,
        )

    elif display_type == "chart":
        payload["chart"] = _build_chart_data(
            normalized_result,
            options,
        )

    elif display_type == "tree":
        payload["tree"] = _build_tree_data(
            normalized_result,
            options,
        )

    elif display_type == "text":
        payload["data"] = (
            normalized_result
            if isinstance(normalized_result, str)
            else json.dumps(
                normalized_result,
                ensure_ascii=False,
                indent=2,
            )
        )

    return payload