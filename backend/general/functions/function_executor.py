# =================================================
# File: backend/general/functions/function_executor.py
#
# Description:
# Metadata-driven PostgreSQL Panel Function executor.
# Resolves function parameters and output presentation
# from registered function metadata and output configuration.
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# Modified: 2026-11-22 23:26 (Asia/Baku)
# =================================================

import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from general.functions.function_result_formatter import (
    SUPPORTED_DISPLAY_TYPES,
    format_function_result,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Panel Functions"])

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


class PanelFunctionRequest(BaseModel):
    function_name: str = Field(min_length=1, max_length=255)
    cartable_key: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    selected_record: dict[str, Any] | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    display_options: dict[str, Any] = Field(default_factory=dict)


def _validate_identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_PATTERN.fullmatch(value):
        raise HTTPException(
            status_code=500,
            detail=f"Invalid {label} in function metadata.",
        )
    return value


def _quote_identifier(value: str) -> str:
    return f'"{value}"'


def _parameter_candidates(name: str) -> list[str]:
    candidates = [name]

    if name.lower().startswith("p_") and len(name) > 2:
        candidates.append(name[2:])

    return list(dict.fromkeys(candidates))


def _parameter_sources(
    request: PanelFunctionRequest,
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []

    if request.selected_record is not None:
        sources.append(request.selected_record)

    sources.append(request.context)

    for container_key in (
        "parent_record_context",
        "parentRecordContext",
        "params",
        "parameters",
    ):
        nested = request.context.get(container_key)
        if isinstance(nested, dict):
            sources.append(nested)

    return sources


def _resolve_parameter(
    name: str,
    request: PanelFunctionRequest,
    sources: list[dict[str, Any]],
) -> tuple[bool, Any]:
    candidates = _parameter_candidates(name)

    for candidate in candidates:
        if candidate in request.parameters:
            return True, request.parameters[candidate]

    for source in sources:
        for candidate in candidates:
            if candidate in source:
                return True, source[candidate]

    return False, None


def _returns_rows(return_type: str | None) -> bool:
    normalized_type = (return_type or "").strip().lower()

    return (
        normalized_type.startswith("setof ")
        or normalized_type.startswith("table")
        or normalized_type.startswith("record")
    )


def _get_result_kind(
    return_type: str | None,
    returns_rows: bool,
) -> str:
    normalized_type = (return_type or "").strip().lower()

    if returns_rows:
        return "rows"

    if normalized_type in {"json", "jsonb"}:
        return "json"

    if normalized_type == "void":
        return "none"

    return "value"


async def _load_output_configuration(
    session: AsyncSession,
    schema_name: str,
    function_name: str,
) -> tuple[set[str], dict[str, Any]]:
    """
    Load active output configurations for a registered function.

    output_type_code identifies the output category.
    renderer_key identifies the frontend renderer.
    presentation_code identifies the presentation mode.
    display_options supplies renderer-specific metadata.
    """

    query = text(
        """
        SELECT
            oc.output_config_id,
            oc.output_type_code,
            oc.renderer_key,
            oc.presentation_code,
            oc.display_options,
            oc.is_default,
            oc.priority,
            oc.config_code,
            oc.c_avatar_manager_id,
            am.c_avatar_manager_desc
        FROM pulsar.t_function_output_config oc
        LEFT JOIN pulsar.t_avatar_manager am
          ON am.c_avatar_manager_id = oc.c_avatar_manager_id
        WHERE oc.schema_name = :schema_name
          AND oc.function_name = :function_name
          AND oc.is_active = TRUE
        ORDER BY
            is_default DESC,
            priority ASC,
            config_code ASC
        """
    )

    result = await session.execute(
        query,
        {
            "schema_name": schema_name,
            "function_name": function_name,
        },
    )

    configurations = result.mappings().all()

    if not configurations:
        raise HTTPException(
            status_code=422,
            detail=(
                "No active output configuration exists "
                "for this function."
            ),
        )

    allowed_types: set[str] = set()
    normalized_configs: list[dict[str, Any]] = []

    for config in configurations:
        output_type = str(
            config["output_type_code"] or ""
        ).strip().lower()

        renderer_key = str(
            config["renderer_key"] or ""
        ).strip().lower()

        presentation_code = str(
            config["presentation_code"] or ""
        ).strip().lower()

        options = config["display_options"] or {}

        if not isinstance(options, dict):
            raise HTTPException(
                status_code=500,
                detail=(
                    "Invalid display_options in function output metadata."
                ),
            )

        if output_type not in SUPPORTED_DISPLAY_TYPES:
            continue

        allowed_types.add(output_type)

        configured_display_type = str(
            options.get("display_type", "")
        ).strip().lower()

        if configured_display_type in SUPPORTED_DISPLAY_TYPES:
            allowed_types.add(configured_display_type)

        normalized_configs.append({
            "output_config_id": config["output_config_id"],
            "output_type_code": output_type,
            "renderer_key": renderer_key,
            "presentation_code": presentation_code,
            "display_options": options,
            "is_default": bool(config["is_default"]),
            "priority": config["priority"],
            "config_code": config["config_code"],
            "avatar_manager_id": config["c_avatar_manager_id"],
            "avatar_manager_desc": config["c_avatar_manager_desc"],
        })

    if not allowed_types:
        raise HTTPException(
            status_code=422,
            detail=(
                "No supported output types are configured "
                "for this function."
            ),
        )

    selected_options: dict[str, Any] = {}

    for config in normalized_configs:
        if config["is_default"]:
            selected_options = dict(config["display_options"])
            selected_options.setdefault(
                "display_type",
                config["output_type_code"],
            )
            selected_options["renderer_key"] = config["renderer_key"]
            selected_options["presentation_code"] = (
                config["presentation_code"]
            )
            selected_options["config_code"] = config["config_code"]
            selected_options["output_config_id"] = config["output_config_id"]
            selected_options["avatar_manager_id"] = config["avatar_manager_id"]
            selected_options["avatar_manager_desc"] = config["avatar_manager_desc"]
            break

    if not selected_options:
        first_config = normalized_configs[0]
        selected_options = dict(first_config["display_options"])
        selected_options.setdefault(
            "display_type",
            first_config["output_type_code"],
        )
        selected_options["renderer_key"] = first_config["renderer_key"]
        selected_options["presentation_code"] = (
            first_config["presentation_code"]
        )
        selected_options["config_code"] = first_config["config_code"]
        selected_options["output_config_id"] = first_config["output_config_id"]
        selected_options["avatar_manager_id"] = first_config["avatar_manager_id"]
        selected_options["avatar_manager_desc"] = first_config["avatar_manager_desc"]

    return allowed_types, selected_options


@router.post("/functions/execute")
async def execute_panel_function(
    request: PanelFunctionRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Execute an active PostgreSQL function and format its result.

    Function arguments are resolved from explicit parameters, the
    selected record, and the supplied context. Output presentation
    is constrained by active function output configuration metadata.
    """

    function_name = request.function_name.strip()

    if not function_name:
        raise HTTPException(
            status_code=400,
            detail="Function name is required.",
        )

    try:
        metadata_result = await session.execute(
            text(
                """
                SELECT
                    function_name,
                    schema_name,
                    parameter_definition,
                    output_definition,
                    return_type,
                    state,
                    is_active
                FROM pulsar.t_function_definition
                WHERE function_name = :function_name
                """
            ),
            {"function_name": function_name},
        )

        definition = metadata_result.mappings().first()

        if definition is None:
            raise HTTPException(
                status_code=404,
                detail="Function metadata was not found.",
            )

        if (
            not definition["is_active"]
            or definition["state"] != "ACTIVE"
        ):
            raise HTTPException(
                status_code=403,
                detail="Function is not active.",
            )

        schema_name = _validate_identifier(
            definition["schema_name"],
            "schema name",
        )
        db_function_name = _validate_identifier(
            definition["function_name"],
            "function name",
        )

        parameter_definition = definition["parameter_definition"]

        if not isinstance(parameter_definition, list):
            raise HTTPException(
                status_code=500,
                detail="Invalid function parameter metadata.",
            )

        sources = _parameter_sources(request)
        call_arguments: list[str] = []
        bind_values: dict[str, Any] = {}
        parameter_names: set[str] = set()
        variadic_seen = False
        optional_omitted = False

        for parameter in parameter_definition:
            if not isinstance(parameter, dict):
                raise HTTPException(
                    status_code=500,
                    detail="Invalid parameter entry in function metadata.",
                )

            parameter_name = _validate_identifier(
                parameter.get("name", ""),
                "parameter name",
            )

            if parameter_name in parameter_names:
                raise HTTPException(
                    status_code=500,
                    detail="Duplicate parameter name in function metadata.",
                )

            parameter_names.add(parameter_name)

            parameter_mode = str(
                parameter.get("mode", "IN")
            ).upper()

            if parameter_mode not in ("IN", "VARIADIC"):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Only IN and VARIADIC function parameters "
                        "are supported."
                    ),
                )

            if variadic_seen:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "A VARIADIC parameter must be the final "
                        "parameter in function metadata."
                    ),
                )

            found, value = _resolve_parameter(
                parameter_name,
                request,
                sources,
            )

            if not found:
                if parameter.get("required", True):
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"Required parameter '{parameter_name}' "
                            "was not supplied by the request context."
                        ),
                    )

                if parameter_mode == "VARIADIC":
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "A VARIADIC parameter must be supplied "
                            "explicitly."
                        ),
                    )

                optional_omitted = True
                continue

            if optional_omitted:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "An optional parameter was omitted before a "
                        "later parameter. Supply all preceding optional "
                        "parameters explicitly."
                    ),
                )

            bind_key = f"arg_{len(bind_values)}"
            bind_values[bind_key] = value

            if parameter_mode == "VARIADIC":
                call_arguments.append(f"VARIADIC :{bind_key}")
                variadic_seen = True
            else:
                call_arguments.append(
                    f"{_quote_identifier(parameter_name)} => :{bind_key}"
                )

        qualified_function = (
            f"{_quote_identifier(schema_name)}."
            f"{_quote_identifier(db_function_name)}"
        )

        call_sql = (
            f"SELECT {qualified_function}"
            f"({', '.join(call_arguments)})"
        )

        result = await session.execute(
            text(call_sql),
            bind_values,
        )

        return_type = definition["return_type"]
        returns_rows = _returns_rows(return_type)

        if returns_rows:
            output = [
                dict(row)
                for row in result.mappings().all()
            ]
        elif (return_type or "").strip().lower() == "void":
            output = None
        else:
            output = result.scalar_one_or_none()

        result_kind = _get_result_kind(
            return_type,
            returns_rows,
        )

        allowed_display_types, configured_options = (
            await _load_output_configuration(
                session=session,
                schema_name=schema_name,
                function_name=db_function_name,
            )
        )

        effective_options = dict(configured_options)
        effective_options.update(request.display_options)

        # Output configuration identity and Avatar assignment are trusted
        # database metadata and cannot be overridden by request options.
        effective_options["output_config_id"] = configured_options.get(
            "output_config_id"
        )
        effective_options["avatar_manager_id"] = configured_options.get(
            "avatar_manager_id"
        )
        effective_options["avatar_manager_desc"] = configured_options.get(
            "avatar_manager_desc"
        )

        formatted_result = format_function_result(
            result=output,
            result_kind=result_kind,
            display_options=effective_options,
            allowed_display_types=allowed_display_types,
        )

        formatted_result["metadata"].update({
            "schema_name": schema_name,
            "function_name": db_function_name,
            "return_type": return_type,
            "result_kind": result_kind,
            "output_definition": definition["output_definition"],
            "renderer_key": effective_options.get("renderer_key"),
            "presentation_code": effective_options.get(
                "presentation_code"
            ),
            "config_code": effective_options.get("config_code"),
            "output_config_id": effective_options.get("output_config_id"),
            "avatar_manager_id": effective_options.get("avatar_manager_id"),
            "avatar_manager_desc": effective_options.get("avatar_manager_desc"),
        })

        response_payload = {
            "status": "SUCCESS",
            "function_name": function_name,
            "return_type": return_type,
            "result_kind": result_kind,
            "result": output,
            "display": formatted_result,
        }

        # Commit the transaction only after execution and formatting succeed.
        await session.commit()

        return response_payload
    
    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except SQLAlchemyError as exc:
        await session.rollback()
        logger.exception(
            "Panel function execution failed: %s",
            function_name,
        )
        raise HTTPException(
            status_code=500,
            detail="Database error while executing Panel Function.",
        ) from exc

    except Exception as exc:
        await session.rollback()
        logger.exception(
            "Unexpected Panel function execution error: %s",
            function_name,
        )
        raise HTTPException(
            status_code=500,
            detail="Unexpected error while executing Panel Function.",
        ) from exc