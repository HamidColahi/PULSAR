"""Canonical, privacy-bounded Context contract for the PULSAR AI Avatar.

This module is deliberately independent from FastAPI/SQLAlchemy so its
validation rules can be unit-tested. It accepts legacy v1 input but emits the
normalized v2 shape. UI labels are observations; only explicitly supplied
PULSAR metadata descriptions can describe operation semantics.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any


MAX_CONTEXT_BYTES = 65_536
MAX_ITEMS = 100
MAX_TEXT = 512
MAX_RECORD_FIELDS = 100
MAX_PARENT_CONTEXT = 20

FIELD_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
SENSITIVE_KEY_RE = re.compile(
    r"password|passwd|secret|token|authorization|cookie|session|api[_-]?key|"
    r"credit.?card|card.?number|ssn|national.?id|phone|mobile|e.?mail|"
    r"access.?key|refresh.?token",
    re.IGNORECASE,
)
ALLOWED_DESCRIPTION_SOURCES = {
    "pulsar.t_function_definition.description",
    "pulsar.t_function_definition.documentation",
    "pulsar.t_function_definition.description_or_documentation",
}
VALID_FORM_MODES = {"view", "insert", "update", "delete"}
VALID_TARGET_TYPES = {"PAGE", "FUNCTION"}


class ContextContractError(ValueError):
    """A supplied Context does not satisfy the PULSAR Context contract."""


def _object(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ContextContractError(f"Canonical Context section must be an object: {name}.")
    return value


def _text(value: Any, name: str, maximum: int = MAX_TEXT) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContextContractError(f"Invalid Canonical Context text field: {name}.")
    result = value.strip()
    if len(result) > maximum:
        raise ContextContractError(f"Canonical Context text field is too long: {name}.")
    return result or None


def _identifier(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ContextContractError(f"Invalid Canonical Context identifier: {name}.")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and len(value) <= 256:
        return value.strip() or None
    raise ContextContractError(f"Invalid Canonical Context identifier: {name}.")


def _boolean(value: Any, name: str, default: bool = False) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ContextContractError(f"Invalid Canonical Context boolean field: {name}.")
    return value


def _nonnegative_int(value: Any, name: str, default: int | None = 0) -> int | None:
    if value is None:
        return default
    if type(value) is not int or value < 0:
        raise ContextContractError(f"Invalid Canonical Context integer field: {name}.")
    return value


def _string_list(value: Any, name: str, *, maximum_items: int = MAX_ITEMS,
                 maximum_text: int = 256, filter_sensitive: bool = False) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > maximum_items:
        raise ContextContractError(f"Invalid Canonical Context list: {name}.")
    result: list[str] = []
    for item in value:
        text_value = _text(item, name, maximum_text)
        if not text_value:
            continue
        if filter_sensitive and SENSITIVE_KEY_RE.search(text_value):
            continue
        result.append(text_value)
    return result


def _selected_record(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ContextContractError("Canonical Context selected_record must be an object or null.")
    if len(value) > MAX_RECORD_FIELDS:
        raise ContextContractError("Canonical Context selected_record has too many fields.")

    safe: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not FIELD_NAME_RE.fullmatch(key):
            raise ContextContractError("Canonical Context selected_record contains an invalid field name.")
        # Defense in depth: sensitive values are never sent to the language model.
        if SENSITIVE_KEY_RE.search(key):
            continue
        if item is None or isinstance(item, (bool, int)):
            safe[key] = item
        elif isinstance(item, float):
            if not math.isfinite(item):
                raise ContextContractError("Canonical Context selected_record contains an invalid numeric value.")
            safe[key] = item
        elif isinstance(item, str):
            if len(item) > 2_000:
                raise ContextContractError("Canonical Context selected_record contains an oversized field value.")
            safe[key] = item
        else:
            raise ContextContractError("Canonical Context selected_record may contain only scalar field values.")
    return safe


def _field_labels(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict) or len(value) > MAX_ITEMS:
        raise ContextContractError("Invalid Canonical Context field_labels metadata.")
    result: dict[str, str] = {}
    for key, label in value.items():
        if not isinstance(key, str) or not FIELD_NAME_RE.fullmatch(key) or SENSITIVE_KEY_RE.search(key):
            continue
        safe_label = _text(label, "field_labels", 200)
        if safe_label:
            result[key] = safe_label
    return result


def _safe_rows(value: Any, name: str, fields: dict[str, tuple[str, int] | str]) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_ITEMS:
        raise ContextContractError(f"Invalid Canonical Context list: {name}.")
    output: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, dict):
            raise ContextContractError(f"Invalid Canonical Context entry: {name}.")
        item: dict[str, Any] = {}
        for field, spec in fields.items():
            if isinstance(spec, tuple):
                kind, limit = spec
            else:
                kind, limit = spec, MAX_TEXT
            raw = row.get(field)
            key_path = f"{name}.{field}"
            if kind == "text":
                item[field] = _text(raw, key_path, limit)
            elif kind == "bool":
                item[field] = _boolean(raw, key_path, False)
            elif kind == "index":
                if raw is None:
                    item[field] = None
                elif type(raw) is not int or not 0 <= raw <= 100_000:
                    raise ContextContractError(f"Invalid Canonical Context index: {key_path}.")
                else:
                    item[field] = raw
            elif kind == "string_list":
                item[field] = _string_list(raw, key_path, maximum_items=MAX_ITEMS, maximum_text=200)
            else:
                raise AssertionError(f"Unknown contract type: {kind}")
        output.append(item)
    return output


def _description(value: Any, source: Any, path: str) -> tuple[str | None, str | None, str]:
    description = _text(value, path, 1_000)
    source_text = _text(source, f"{path}_source", 160)
    if source_text not in ALLOWED_DESCRIPTION_SOURCES:
        source_text = None
    # A label or a technical key is not a description and does not count as evidence.
    if description and source_text:
        return description, source_text, "documented"
    return None, None, "missing"


def validate_context_variables(value: Any) -> dict[str, Any]:
    """Validate, bound and normalize PULSAR AI Avatar Context v2.

    v1 inputs are accepted for rollout compatibility. The returned contract is
    always v2, with explicit missing-description status and no executable or
    unbounded DOM payloads.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ContextContractError("Canonical Context must be a JSON object.")

    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ContextContractError("Canonical Context must contain valid JSON values.") from exc
    if len(encoded.encode("utf-8")) > MAX_CONTEXT_BYTES:
        raise ContextContractError("Canonical Context exceeds the maximum allowed size.")
    if not value:
        return {}

    version = value.get("schema_version")
    if type(version) is not int or version not in {1, 2}:
        raise ContextContractError("Unsupported Canonical Context schema version.")

    page = _object(value.get("page"), "page")
    navigation = _object(value.get("navigation"), "navigation")
    ui_source = value.get("ui_state")
    if ui_source is None:
        ui_source = value.get("runtime_state")
    ui_state = _object(ui_source, "ui_state/runtime_state")
    grid = _object(value.get("grid"), "grid")
    data_context = _object(value.get("data_context"), "data_context")

    page_description, page_description_source, page_description_status = _description(
        page.get("description", page.get("page_description")),
        page.get("description_source", page.get("page_description_source")),
        "page.description",
    )
    safe_page = {
        "technical_key": _text(page.get("technical_key"), "page.technical_key", 256),
        "page_key": _text(page.get("page_key"), "page.page_key", 256),
        "page_title_key": _text(page.get("page_title_key"), "page.page_title_key", 256),
        "visible_title": _text(page.get("visible_title", page.get("title")), "page.visible_title", 300),
        "language": _text(page.get("language"), "page.language", 24),
        "grid_component": _text(page.get("grid_component"), "page.grid_component", 256),
        "form_component": _text(page.get("form_component"), "page.form_component", 256),
        "context_id": _identifier(page.get("context_id"), "page.context_id"),
        "description": page_description,
        "description_source": page_description_source,
        "description_status": page_description_status,
    }

    parents = navigation.get("parent_record_context", [])
    if not isinstance(parents, list) or len(parents) > MAX_PARENT_CONTEXT:
        raise ContextContractError("Invalid Canonical Context parent navigation metadata.")
    safe_parents: list[dict[str, Any]] = []
    for parent in parents:
        if not isinstance(parent, dict):
            raise ContextContractError("Invalid Canonical Context parent navigation entry.")
        safe_parents.append({
            "component_name": _text(parent.get("component_name"), "navigation.parent_record_context.component_name", 256),
            "fields": _string_list(parent.get("fields"), "navigation.parent_record_context.fields", maximum_items=MAX_ITEMS, maximum_text=128, filter_sensitive=True),
            "field_labels": _field_labels(parent.get("field_labels", parent.get("fieldLabels"))),
        })

    form_mode = ui_state.get("form_mode", "view")
    if form_mode is not None and (not isinstance(form_mode, str) or form_mode not in VALID_FORM_MODES):
        raise ContextContractError("Invalid Canonical Context field: ui_state.form_mode.")

    safe_ui_state = {
        "page_loading": _boolean(ui_state.get("page_loading"), "ui_state.page_loading"),
        "page_error": _boolean(ui_state.get("page_error"), "ui_state.page_error"),
        "grid_loading": _boolean(ui_state.get("grid_loading"), "ui_state.grid_loading"),
        "grid_error": _boolean(ui_state.get("grid_error"), "ui_state.grid_error"),
        "form_visible": _boolean(ui_state.get("form_visible"), "ui_state.form_visible"),
        "has_selection": _boolean(ui_state.get("has_selection"), "ui_state.has_selection"),
        "form_mode": form_mode,
    }

    raw_count = grid.get("record_count", data_context.get("record_count", 0))
    record_count = _nonnegative_int(raw_count, "grid.record_count", 0)
    if record_count is None:
        record_count = 0
    safe_grid = {
        "component": _text(grid.get("component", page.get("grid_component")), "grid.component", 256),
        "field_mode": _text(grid.get("field_mode"), "grid.field_mode", 80),
        "configuration_available": _boolean(grid.get("configuration_available"), "grid.configuration_available"),
        "record_count": record_count,
    }

    safe_components = _safe_rows(value.get("components"), "components", {
        "index": "index", "technical_key": ("text", 256), "technical_type": ("text", 100),
        "visible_label": ("text", 240), "role": ("text", 80), "landmark": ("text", 100),
    })
    safe_fields = _safe_rows(value.get("fields"), "fields", {
        "index": "index", "label": ("text", 240), "name": ("text", 200), "id": ("text", 200),
        "element_type": ("text", 80), "input_type": ("text", 80), "role": ("text", 80),
        "placeholder": ("text", 240), "required": "bool", "disabled": "bool", "read_only": "bool",
        "selected_option_label": ("text", 240),
    })
    for row in safe_fields:
        if row.get("name") and SENSITIVE_KEY_RE.search(row["name"]):
            row["name"] = None
        if row.get("id") and SENSITIVE_KEY_RE.search(row["id"]):
            row["id"] = None

    actions_raw = value.get("actions")
    if actions_raw is None:
        actions_raw = []
    if not isinstance(actions_raw, list) or len(actions_raw) > MAX_ITEMS:
        raise ContextContractError("Invalid Canonical Context list: actions.")
    safe_actions: list[dict[str, Any]] = []
    for row in actions_raw:
        if not isinstance(row, dict):
            raise ContextContractError("Invalid Canonical Context action entry.")
        description, description_source, description_status = _description(
            row.get("description"), row.get("description_source"), "actions.description"
        )
        target_type = _text(row.get("target_type"), "actions.target_type", 20)
        if target_type not in VALID_TARGET_TYPES:
            target_type = None
        safe_actions.append({
            "index": _nonnegative_int(row.get("index"), "actions.index", None),
            "label": _text(row.get("label"), "actions.label", 240),
            "element_type": _text(row.get("element_type"), "actions.element_type", 80),
            "role": _text(row.get("role"), "actions.role", 80),
            "action_type": _text(row.get("action_type"), "actions.action_type", 80),
            "component_key": _text(row.get("component_key"), "actions.component_key", 256),
            "disabled": _boolean(row.get("disabled"), "actions.disabled"),
            "title": _text(row.get("title"), "actions.title", 240),
            "action_code": _text(row.get("action_code"), "actions.action_code", 100),
            "target_key": _text(row.get("target_key"), "actions.target_key", 256),
            "target_type": target_type,
            "description": description,
            "description_source": description_source,
            "description_status": description_status,
        })

    safe_tables = _safe_rows(value.get("tables"), "tables", {
        "index": "index", "label": ("text", 240), "role": ("text", 80),
        "component_key": ("text", 256), "column_labels": "string_list",
        "visible_row_count": "index",
    })
    safe_runtime = {
        **safe_ui_state,
        "headings": _string_list(ui_state.get("headings", value.get("runtime_state", {}).get("headings") if isinstance(value.get("runtime_state"), dict) else []), "runtime_state.headings", maximum_items=30, maximum_text=240),
        "visible_alerts": _string_list(ui_state.get("visible_alerts", value.get("runtime_state", {}).get("visible_alerts") if isinstance(value.get("runtime_state"), dict) else []), "runtime_state.visible_alerts", maximum_items=30, maximum_text=300),
        "visible_dialogs": _string_list(ui_state.get("visible_dialogs", value.get("runtime_state", {}).get("visible_dialogs") if isinstance(value.get("runtime_state"), dict) else []), "runtime_state.visible_dialogs", maximum_items=30, maximum_text=300),
    }

    # PALI_CONTEXT_V2_3_SELECTED_RECORD_CONSISTENCY
    # The top-level selected_record is canonical when present. If it is null,
    # fall back to the nested data_context record rather than trusting a stale
    # availability flag or field-name list from the client.
    raw_selected_record = value.get("selected_record")
    if raw_selected_record is None:
        raw_selected_record = data_context.get("selected_record")
    safe_selected = _selected_record(raw_selected_record)

    # Derive selection status and field names from the validated record itself.
    # This prevents contradictions such as available=true with no record values.
    has_selected_record = bool(safe_selected)
    safe_ui_state["has_selection"] = has_selected_record
    safe_runtime["has_selection"] = has_selected_record

    safe_data_context = {
        "selected_record_available": has_selected_record,
        "selected_record_fields": list(safe_selected.keys()) if safe_selected else [],
        "record_count": record_count,
    }
    context_panels = [
        action for action in safe_actions
        if action.get("target_type") in VALID_TARGET_TYPES
    ]
    documented_action_count = sum(action["description_status"] == "documented" for action in safe_actions)

    return {
        "contract": "PULSAR_AI_AVATAR_CONTEXT",
        "schema_version": 2,
        "collected_at": _text(value.get("collected_at"), "collected_at", 80),
        "page": safe_page,
        "navigation": {
            "parent_component": _text(navigation.get("parent_component"), "navigation.parent_component", 256),
            "parent_record_context": safe_parents,
        },
        "selected_record": safe_selected,
        "ui_state": safe_ui_state,
        "runtime_state": safe_runtime,
        "grid": safe_grid,
        "components": safe_components,
        "fields": safe_fields,
        "actions": safe_actions,
        "context_panels": context_panels,
        "tables": safe_tables,
        "data_context": safe_data_context,
        "semantic_status": {
            "page_description_status": page_description_status,
            "actions_with_documented_descriptions": documented_action_count,
            "actions_without_documented_descriptions": len(safe_actions) - documented_action_count,
            "rule": "Visible labels and technical keys are observations, not proof of an operation's business semantics.",
        },
    }
