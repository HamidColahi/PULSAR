# =============================================
# File:
# backend/core/component_where.py
#
# Description:
# Metadata driven where_clause analyzer and resolver
#
# Responsibilities:
#   1. Read where_clause from components_base
#   2. Analyze ${parm[n]} parameters
#   3. Determine source fields directly from where_clause
#   4. Resolve parm[n] from selected_record or request resolver
#   5. Resolve normal runtime placeholders from runtime_context
#   6. Build resolved filters
#   7. Provide reusable where_clause resolution for component_data.py
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# =============================================
import re
from typing import Any, Callable, Dict, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)
from pydantic import (
    BaseModel,
    Field
)
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from core.component_base import get_component_base

# ---------------------------------------------
# Request Model
# ---------------------------------------------
class ResolveWhereRequest(BaseModel):
    component_name: str
    selected_record: dict = Field(
        default_factory=dict
    )
    runtime_context: dict = Field(
        default_factory=dict
    )

# ---------------------------------------------
# Response Model
# ---------------------------------------------
class ResolveWhereResponse(BaseModel):
    component_name: str
    source_where_clause: str | None
    resolved_where_clause: str | None
    filters: dict
    parameters: dict
    source_fields: dict

# ---------------------------------------------
# Where Clause Analyzer
# ---------------------------------------------
def analyze_where_clause(
    where_clause: str | None
) -> list[dict[str, Any]]:
    """
    Analyze where_clause and discover parm[n] definitions.

    Example:
        parm[1]: ${parm[1]}

    Result:
        [
            {
                "field": "parm[1]",
                "parameter": "parm[1]",
                "index": 1
            }
        ]

    The field-to-parameter relationship is derived
    exclusively from where_clause metadata.
    """
    if not where_clause:
        return []

    pattern = re.compile(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*\$\{parm\[(\d+)\]\}"
    )

    definitions = []
    seen = set()

    for match in pattern.finditer(
        where_clause
    ):
        field_name = (
            match.group(1).strip()
        )

        index = int(
            match.group(2)
        )

        parameter_name = (
            f"parm[{index}]"
        )

        key = (
            field_name,
            parameter_name
        )

        if key in seen:
            continue

        seen.add(key)

        definitions.append(
            {
                "field":
                    field_name,
                "parameter":
                    parameter_name,
                "index":
                    index
            }
        )

    return definitions

# ---------------------------------------------
# Parameter Resolver
# ---------------------------------------------
def resolve_runtime_parameters(
    definitions: list[dict[str, Any]],
    selected_record: dict
) -> tuple[dict, dict]:
    """
    Resolve parm[n] from selected_record.

    The mapping is determined exclusively by
    where_clause metadata.

    Example:
        where_clause:
            parm[1]: ${parm[1]}

        selected_record:
            {
                "parm[1]":
                    "5204ea97-afed-4815-aebc-7b92c3c9620d"
            }

        result:
            {
                "parm[1]":
                    "5204ea97-afed-4815-aebc-7b92c3c9620d"
            }
    """
    if not isinstance(
        selected_record,
        dict
    ):
        selected_record = {}
    
    parameters = {}
    source_fields = {} 

    for definition in definitions:
        field_name = (
            definition["field"]
        )

        parameter_name = (
            definition["parameter"]
        )
        print(f"Resolving parameter '{parameter_name}' from field '{field_name}'")
        print(f"Selected record: {selected_record}")
        if field_name not in selected_record:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Required field '{field_name}' for "
                    f"parameter '{parameter_name}' was not found "
                    f"in selected record"
                )
            )

        value = selected_record.get(
            field_name
        )

        if (
            value is None or
            value == ""
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Required field '{field_name}' for "
                    f"parameter '{parameter_name}' has no value"
                )
            )

        parameters[
            parameter_name
        ] = value

        source_fields[
            parameter_name
        ] = field_name

    return (
        parameters,
        source_fields
    )

# ---------------------------------------------
# Placeholder Resolver
# ---------------------------------------------
def _resolve_placeholder(
    placeholder: str,
    parameters: dict,
    runtime_context: dict,
    resolver: Optional[
        Dict[str, Any]
    ] = None,
    column_name: Optional[str] = None
):
    """
    Resolve one where_clause placeholder.

    Resolution order:
        1. parm[n] from parameters
        2. normal runtime placeholder from runtime_context
        3. exact request resolver key
        4. exact request resolver column name
    """
    placeholder = (
        placeholder or ""
    ).strip()

    if not isinstance(
        parameters,
        dict
    ):
        parameters = {}

    if not isinstance(
        runtime_context,
        dict
    ):
        runtime_context = {}

    value = parameters.get(
        placeholder
    )

    if value is not None:
        return value

    value = runtime_context.get(
        placeholder
    )

    if value is not None:
        return value

    if isinstance(
        resolver,
        dict
    ):
        if placeholder in resolver:
            return resolver[
                placeholder
            ]

        if (
            column_name and
            column_name in resolver
        ):
            return resolver[
                column_name
            ]

    return None

# ---------------------------------------------
# Where Clause Parser
# ---------------------------------------------
async def resolve_where_request_scope(
    where_clause: str | None,
    component_name: str,
    resolver: Optional[
        Dict[str, Any]
    ] = None,
    model=None,
    converter: Optional[
        Callable[[Any, Any], Any]
    ] = None
):
    """
    Resolve a metadata where_clause for data execution.

    Returns:
        (filters, raw_sql)

    The resolver is supplied by the request transport layer.

    Example:
        where_clause:
            parm[1]: ${parm[1]}

        resolver:
            {
                "parm[1]":
                    "5204ea97-afed-4815-aebc-7b92c3c9620d"
            }

    Result:
        {
            "parm[1]":
                "5204ea97-afed-4815-aebc-7b92c3c9620d"
        }

    When model and converter are supplied, values are
    converted according to reflected SQLAlchemy column types.
    """
    filters: Dict[str, Any] = {}
    raw_sql: Optional[str] = None

    if (
        not where_clause or
        not str(
            where_clause
        ).strip()
    ):
        return (
            filters,
            raw_sql
        )

    if not isinstance(
        resolver,
        dict
    ):
        resolver = {}

    columns = {}

    if model is not None:
        columns = {
            column.name: column
            for column in
            model.__table__.columns
        }

    parts = re.split(
        r"\s*(?:,|AND|and)\s*",
        str(
            where_clause
        ).strip()
    )

    pattern = re.compile(
        r"([A-Za-z_][A-Za-z0-9_]*)"
        r"\s*(?::|=)\s*"
        r"(.+)"
    )

    for token in parts:
        token = token.strip()

        if not token:
            continue

        match = pattern.match(
            token
        )

        if not match:
            raw_sql = where_clause
            return (
                filters,
                raw_sql
            )

        column_name = (
            match.group(1).strip()
        )

        raw_value = (
            match.group(2).strip()
        )

        raw_value = (
            raw_value.strip(
                "'\""
            )
        )

        placeholder_match = re.match(
            r"^\$\{(.+)\}$",
            raw_value
        )

        if placeholder_match:
            placeholder = (
                placeholder_match
                .group(1)
                .strip()
            )

            value = (
                _resolve_placeholder(
                    placeholder=placeholder,
                    parameters={},
                    runtime_context={},
                    resolver=resolver,
                    column_name=column_name
                )
            )
        else:
            value = raw_value

        if value is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unable to resolve where_clause "
                    f"parameter for column "
                    f"'{column_name}' in component "
                    f"'{component_name}'"
                )
            )

        if model is not None:
            column = columns.get(
                column_name
            )

            if column is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Invalid where_clause column: "
                        f"{column_name}"
                    )
                )

            if converter is not None:
                value = converter(
                    column,
                    value
                )

        filters[
            column_name
        ] = value

    return (
        filters,
        raw_sql
    )

# ---------------------------------------------
# Where Clause Builder
# ---------------------------------------------
def build_where_clause(
    where_clause: str | None,
    parameters: dict,
    runtime_context: dict
):
    """
    Convert metadata where_clause into resolved filters.

    Supports:
        parm[1]: ${parm[1]}
        profile_id: ${profile_id}
    """
    if not where_clause:
        return (
            None,
            {}
        )

    if not isinstance(
        parameters,
        dict
    ):
        parameters = {}

    if not isinstance(
        runtime_context,
        dict
    ):
        runtime_context = {}

    filters = {}

    pattern = re.compile(
        r"([A-Za-z_][A-Za-z0-9_]*)"
        r"\s*:\s*"
        r"\$\{([^}]+)\}"
    )

    for match in pattern.finditer(
        where_clause
    ):
        column_name = (
            match.group(1).strip()
        )

        placeholder = (
            match.group(2).strip()
        )

        value = (
            _resolve_placeholder(
                placeholder=placeholder,
                parameters=parameters,
                runtime_context=runtime_context,
                column_name=column_name
            )
        )

        if (
            value is None or
            value == ""
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unable to resolve where_clause "
                    f"parameter '{placeholder}' "
                    f"for column '{column_name}'"
                )
            )

        filters[
            column_name
        ] = value

    return (
        where_clause,
        filters
    )

# ---------------------------------------------
# Complete Resolver
# ---------------------------------------------
def resolve_component_where(
    where_clause: str | None,
    selected_record: dict,
    runtime_context: dict
):
    """
    Complete metadata-driven where_clause resolution.

    parm[n]:
        resolved from selected_record according to
        the relationship declared by where_clause.

    Other placeholders:
        resolved from runtime_context.
    """
    definitions = (
        analyze_where_clause(
            where_clause
        )
    )

    parameters, source_fields = (
        resolve_runtime_parameters(
            definitions,
            selected_record
        )
    )

    resolved_clause, filters = (
        build_where_clause(
            where_clause,
            parameters,
            runtime_context
        )
    )

    return {
        "resolved_where_clause":
            resolved_clause,
        "filters":
            filters,
        "parameters":
            parameters,
        "source_fields":
            source_fields
    }

# ---------------------------------------------
# Router
# ---------------------------------------------
router = APIRouter(
    prefix="/runtime",
    tags=["Runtime-Resolver"]
)

@router.post(
    "/resolve_where_clause",
    response_model=ResolveWhereResponse
)
async def resolve_component_where_api(
    request: ResolveWhereRequest,
    session: AsyncSession = Depends(
        get_async_session
    )
):
    component = await get_component_base(
        session,
        request.component_name
    )

    source_where_clause = (
        component.get(
            "where_clause"
        )
    )

    result = resolve_component_where(
        source_where_clause,
        request.selected_record,
        request.runtime_context
    )

    return {
        "component_name":
            request.component_name,
        "source_where_clause":
            source_where_clause,
        "resolved_where_clause":
            result[
                "resolved_where_clause"
            ],
        "filters":
            result["filters"],
        "parameters":
            result["parameters"],
        "source_fields":
            result["source_fields"]
    }

# ---------------------------------------------
# Important Learning Points
# ---------------------------------------------
#
# 1. where_clause semantics belong exclusively to this module.
#
# 2. parm[n] is determined directly from where_clause metadata.
#
# 3. parm[n] is resolved from selected_record using the exact
#    metadata field associated with that parm[n].
#
# 4. profile_id is resolved only when where_clause explicitly contains
#    ${profile_id}.
#
# 5. profile_id is never automatically converted into parm[n].
#
# 6. No c_profile_id -> profile_id normalization exists here.
#
# 7. component_data.py delegates where_clause semantics here.
#
# 8. Request-time resolver values use exact field/placeholder names.
#
# 9. SQLAlchemy type conversion is delegated to component_data.py.
#
# 10. No table-specific field or parm mapping is hard-coded.
#
# 11. selected_record and runtime_context remain separate contexts.
#
# 12. The runtime API exposes parameters and source_fields for traceability.
#
# 13. field_mode does not belong to components_base metadata resolution.