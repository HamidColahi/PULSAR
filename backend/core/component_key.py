# =============================================
# File:
# backend/core/component_key.py
# 
# Description:
# Metadata driven primary-key analyzer and resolver
#
# Responsibilities:
#   1. Read primary_key metadata
#   2. Analyze simple and composite primary keys
#   3. Extract primary-key values from a record
#   4. Resolve primary-key identity values
#   5. Build canonical record identity
#   6. Build primary-key filters
#   7. Provide the runtime API for primary-key resolution
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# =============================================
import traceback
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_async_session
from core.component_base import get_component_base
from core.query_error import handle_query_error

QUERY_COMPONENT_KEY_RESOLVE = "QUERY_COMPONENT_KEY_RESOLVE"

# ---------------------------------------------
# Request / Response Models
# ---------------------------------------------
class ResolveKeyRequest(BaseModel):
    component_name: str
    record: dict[str, Any] = Field(
        default_factory=dict
    )

class ResolveKeyResponse(BaseModel):
    component_name: str
    primary_key: str
    fields: list[str]
    values: dict[str, Any]
    identity: str

# ---------------------------------------------
# Primary Key Analyzer
# ---------------------------------------------
def analyze_primary_key(
    primary_key: str | list | tuple | None
) -> list[str]:
    """
    Extract primary-key field names from metadata.

    """
    if primary_key is None:
        raise HTTPException(
            status_code=500,
            detail="Primary key metadata is empty"
        )

    if isinstance(
        primary_key,
        (list, tuple)
    ):
        names = [
            str(name).strip()
            for name in primary_key
            if str(name).strip()
        ]
    else:
        names = [
            name.strip()
            for name in str(
                primary_key
            ).split(",")
            if name.strip()
        ]

    if not names:
        raise HTTPException(
            status_code=500,
            detail="Primary key metadata is invalid"
        )

    if len(names) != len(set(names)):
        raise HTTPException(
            status_code=500,
            detail="Primary key metadata contains duplicate fields"
        )

    return names

# ---------------------------------------------
# Canonical Primary Key Metadata
# ---------------------------------------------
def canonical_primary_key(
    primary_key: str | list | tuple | None
) -> str:
    """
    Return the canonical string representation of
    primary_key metadata.
    """
    return ",".join(
        analyze_primary_key(primary_key)
    )

# ---------------------------------------------
# Primary Key Value Resolver
# ---------------------------------------------
def resolve_primary_key_values(
    primary_key: str | list | tuple | None,
    record: dict[str, Any]
) -> dict[str, Any]:
    """
    Read primary-key values from a complete record
    using primary_key metadata.
    """
    if not isinstance(
        record,
        dict
    ):
        raise HTTPException(
            status_code=400,
            detail="Record must be an object"
        )

    fields = analyze_primary_key(
        primary_key
    )

    values = {}
    missing = []

    for field in fields:
        if field not in record:
            missing.append(field)
            continue

        value = record.get(field)

        if (
            value is None or
            value == ""
        ):
            missing.append(field)
            continue

        values[field] = value

    if missing:
        raise HTTPException(
            status_code=400,
            detail=(
                "Primary key value is missing for "
                "field(s): " +
                ", ".join(missing)
            )
        )

    return values

# ---------------------------------------------
# Primary Key Identity Parser
# ---------------------------------------------
def resolve_primary_key_identity_values(
    primary_key: str | list | tuple | None,
    identity: str
) -> dict[str, Any]:
    """
    Resolve a canonical primary-key identity into
    primary-key field/value pairs.

    Single PK:
        primary_key = parm[1]
        identity = UUID

    Composite PK:
        primary_key = parm[1],parm[2]
        identity = UUID,VERSION

    Identity parsing belongs exclusively to this module.
    """
    if (
        identity is None or
        str(identity).strip() == ""
    ):
        raise HTTPException(
            status_code=400,
            detail="Primary key identity is empty"
        )

    fields = analyze_primary_key(
        primary_key
    )

    raw_values = [
        value.strip()
        for value in str(
            identity
        ).split(",")
    ]

    if len(raw_values) != len(fields):
        raise HTTPException(
            status_code=400,
            detail=(
                "Primary key identity does not match "
                "primary key definition: expected "
                f"{len(fields)} value(s), received "
                f"{len(raw_values)}"
            )
        )

    values = {}

    for field, value in zip(
        fields,
        raw_values
    ):
        if value == "":
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Primary key value is empty "
                    f"for field '{field}'"
                )
            )

        values[field] = value

    return values

# ---------------------------------------------
# Primary Key Identity Builder
# ---------------------------------------------
def build_primary_key_identity(
    primary_key: str | list | tuple | None,
    record: dict[str, Any]
) -> str:
    """
    Build the canonical runtime identity for a record.

    Single PK:
        parm[1] -> UUID

    Composite PK:
        parm[1],parm[2] -> UUID,version
    """
    values = resolve_primary_key_values(
        primary_key,
        record
    )

    fields = analyze_primary_key(
        primary_key
    )

    return ",".join(
        str(values[field])
        for field in fields
    )

# ---------------------------------------------
# Primary Key Filters
# ---------------------------------------------
def build_primary_key_filters(
    primary_key: str | list | tuple | None,
    record: dict[str, Any]
) -> dict[str, Any]:
    """
    Return primary-key field/value pairs for
    query filtering.
    """
    return resolve_primary_key_values(
        primary_key,
        record
    )

# ---------------------------------------------
# Runtime Router
# ---------------------------------------------
router = APIRouter(
    prefix="/runtime",
    tags=["Runtime-Key"]
)

@router.post(
    "/resolve_component_key",
    response_model=ResolveKeyResponse
)
async def resolve_component_key_api(
    request: ResolveKeyRequest,
    http_request: Request,
    session: AsyncSession = Depends(
        get_async_session
    )
):
    try:
        component = await get_component_base(
            session,
            request.component_name
        )
    except SQLAlchemyError as exc:
        await handle_query_error(
            session,
            exc,
            error_code=QUERY_COMPONENT_KEY_RESOLVE,
            component_name=request.component_name,
            file_name="backend/core/component_key.py",
            function_name="resolve_component_key_api",
            operation_name="GET_COMPONENT_BASE",
            parameters={
                "component_name": request.component_name
            },
            stack_trace=traceback.format_exc(),
            request_method=http_request.method,
            request_path=str(http_request.url.path)
        )
        raise

    primary_key = component.get(
        "primary_key"
    )

    fields = analyze_primary_key(
        primary_key
    )

    values = resolve_primary_key_values(
        primary_key,
        request.record
    )

    identity = build_primary_key_identity(
        primary_key,
        request.record
    )

    return {
        "component_name":
            request.component_name,
        "primary_key":
            canonical_primary_key(
                primary_key
            ),
        "fields":
            fields,
        "values":
            values,
        "identity":
            identity
    }

# ---------------------------------------------
# Important Learning Points
# ---------------------------------------------
# 1. Primary-key semantics belong exclusively to this module.
# 2. Simple and composite primary keys use the same resolver.
# 3. Metadata defines the primary-key fields.
# 4. UI layers do not interpret primary_key metadata.
# 5. Composite-key identity construction is centralized here.
# 6. Composite-key identity parsing is also centralized here.
# 7. component_data.py never splits the primary_key or identity itself.
# 8. resolve_primary_key_identity_values() converts an opaque identity
#    into field/value pairs for data execution.
# 9. canonical_primary_key() provides one canonical metadata representation.
# 10. Duplicate primary-key fields are rejected as invalid metadata.
# 11. No table-specific primary-key names are hard-coded.
# 12. Runtime primary-key resolution is exposed through:
#       POST /runtime/resolve_component_key
# 13. field_mode does not belong to primary-key metadata resolution.
# 14. Database query failures are delegated to query_error.py.
# 15. Failed query transactions are rolled back before error logging.