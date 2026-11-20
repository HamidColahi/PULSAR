
# =============================================
# File:
# backend/core/component_data.py
#
# Description:
# Dynamic CRUD and binary file routes for Pulsar dynamic components
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
#
# Modified: 2026-11-21 01:00 (Asia/Baku)
# =============================================
"""
Dynamic CRUD and binary file routes for Pulsar dynamic components.

Purpose:
    Provide metadata-driven CRUD and binary file operations.

Important:
    Values received from the frontend are converted according to the
    reflected SQLAlchemy column type before being assigned to ORM objects
    or used as query parameters.

    Binary uploads are accepted only for reflected binary columns.

    Primary-key semantics belong exclusively to component_key.py.

    where_clause semantics belong exclusively to component_where.py.

    Basic component metadata access belongs to component_base.py.

    Query/database errors are delegated to query_error.py.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict
from urllib.parse import quote
import json
import re
import traceback
import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response
)
from sqlalchemy import (
    MetaData,
    func,
    inspect,
    update
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import registry
from sqlalchemy.sql import text as sql_text
from sqlalchemy.sql.sqltypes import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    LargeBinary,
    Numeric,
    String
)
from starlette.datastructures import UploadFile

from core.database import get_async_session
from core.component_base import get_component_base
from core.component_key import (
    resolve_primary_key_identity_values
)
from core.component_where import (
    resolve_where_request_scope
)
from core.query_error import (
    handle_query_error
)


# -------------------------------
# Error Codes
# -------------------------------

QUERY_COMPONENT_DATA_LIST = (
    "QUERY_COMPONENT_DATA_LIST"
)
QUERY_COMPONENT_DATA_VIEW = (
    "QUERY_COMPONENT_DATA_VIEW"
)
QUERY_COMPONENT_DATA_INSERT = (
    "QUERY_COMPONENT_DATA_INSERT"
)
QUERY_COMPONENT_DATA_UPDATE = (
    "QUERY_COMPONENT_DATA_UPDATE"
)
QUERY_COMPONENT_DATA_DELETE = (
    "QUERY_COMPONENT_DATA_DELETE"
)
QUERY_COMPONENT_DATA_DELETE_HAS_CHILD = (
    "QUERY_COMPONENT_DATA_DELETE_HAS_CHILD"
)
QUERY_COMPONENT_MODEL_REFLECT = (
    "QUERY_COMPONENT_MODEL_REFLECT"
)
QUERY_COMPONENT_FILE_DOWNLOAD = (
    "QUERY_COMPONENT_FILE_DOWNLOAD"
)

DEFAULT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


# -------------------------------
# Binary Helpers
# -------------------------------

def _is_binary_column(
    column
) -> bool:
    """
    Identify binary columns from reflected SQLAlchemy metadata.
    """
    return isinstance(
        column.type,
        LargeBinary
    )


def _binary_value_to_bytes(
    value: Any,
    column_name: str
) -> bytes:
    """
    Normalize supported binary runtime values.
    """
    if isinstance(
        value,
        bytes
    ):
        return value

    if isinstance(
        value,
        (bytearray, memoryview)
    ):
        return bytes(value)

    raise HTTPException(
        status_code=422,
        detail=(
            f"Column '{column_name}' requires "
            "binary file content."
        )
    )


# -------------------------------
# File Field Metadata
# -------------------------------

async def _load_file_field_configs(
    session: AsyncSession,
    component_name: str,
    field_mode: str,
) -> dict:
    """Load file restrictions from the active component field metadata."""
    result = await session.execute(
        sql_text(
            """
            SELECT
                field_name,
                accepted_mime_types,
                max_file_size_bytes
            FROM pulsar.components_config
            WHERE component_name = :component_name
              AND field_mode = :field_mode
              AND LOWER(COALESCE(control_type, '')) = 'file'
            """
        ),
        {
            "component_name": component_name,
            "field_mode": field_mode,
        },
    )

    return {
        row["field_name"]: {
            "accepted_mime_types": row["accepted_mime_types"] or [],
            "max_file_size_bytes": row["max_file_size_bytes"],
        }
        for row in result.mappings().all()
    }


# -------------------------------
# Request Data Parsing
# -------------------------------

async def _parse_request_data(
    request: Request,
    columns: dict,
    file_configs: dict | None = None,
) -> dict:
    """
    Parse JSON or multipart request data.

    Multipart file fields are accepted only when the corresponding
    reflected database column is binary.

    Empty file selections are omitted from the returned dictionary.
    This allows UPDATE operations to preserve existing file content.
    """
    content_type = (
        request.headers.get(
            "content-type",
            ""
        )
        .lower()
    )

    if content_type.startswith(
        "application/json"
    ):
        try:
            data = await request.json()

        except (
            ValueError,
            json.JSONDecodeError
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON request body."
            )

        if not isinstance(
            data,
            dict
        ):
            raise HTTPException(
                status_code=422,
                detail="Request body must be a JSON object."
            )

        return data

    if content_type.startswith(
        "multipart/form-data"
    ):
        try:
            form = await request.form()

        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid multipart request."
            )

        data = {}

        try:
            for key, value in form.multi_items():
                column = columns.get(
                    key
                )

                if column is None:
                    continue

                if isinstance(
                    value,
                    UploadFile
                ):
                    if not _is_binary_column(
                        column
                    ):
                        raise HTTPException(
                            status_code=422,
                            detail=(
                                f"File upload is not supported "
                                f"for non-binary column '{key}'."
                            )
                        )

                    if not value.filename:
                        continue

                    file_config = (file_configs or {}).get(key)
                    if not file_config:
                        raise HTTPException(
                            status_code=422,
                            detail=f"File upload is not enabled by metadata for '{key}'.",
                        )

                    max_file_size = int(
                        file_config.get("max_file_size_bytes")
                        or DEFAULT_MAX_UPLOAD_BYTES
                    )
                    file_content = await value.read(max_file_size + 1)

                    if len(file_content) > max_file_size:
                        raise HTTPException(
                            status_code=413,
                            detail=f"The uploaded file for '{key}' exceeds the configured size limit.",
                        )

                    accepted_types = [
                        str(item).strip().lower()
                        for item in file_config.get("accepted_mime_types", [])
                        if str(item).strip()
                    ]
                    if accepted_types:
                        filename = str(value.filename).lower()
                        mime_type = str(value.content_type or "").lower()
                        accepted = any(
                            (
                                item.startswith(".")
                                and filename.endswith(item)
                            )
                            or (
                                item.endswith("/*")
                                and mime_type.startswith(item[:-1])
                            )
                            or mime_type == item
                            for item in accepted_types
                        )
                        if not accepted:
                            raise HTTPException(
                                status_code=415,
                                detail=f"The uploaded file type is not allowed for '{key}'.",
                            )

                    if "application/pdf" in accepted_types:
                        pdf_header = file_content[:1024].lstrip()
                        if not pdf_header.startswith(b"%PDF-"):
                            raise HTTPException(
                                status_code=415,
                                detail=f"The uploaded file for '{key}' is not a valid PDF document.",
                            )

                    data[key] = file_content

                else:
                    if _is_binary_column(
                        column
                    ):
                        raise HTTPException(
                            status_code=422,
                            detail=(
                                f"Column '{key}' requires "
                                "a file upload."
                            )
                        )

                    data[key] = value

        finally:
            await form.close()

        return data

    raise HTTPException(
        status_code=415,
        detail=(
            "Unsupported content type. "
            "Use application/json or multipart/form-data."
        )
    )


# -------------------------------
# Value Helpers
# -------------------------------

def _strip_placeholder(
    value: Any
) -> Any:
    """
    Remove placeholder wrappers such as ${...}.

    If value is a list/tuple, use its first element.
    """
    if isinstance(
        value,
        (list, tuple)
    ):
        value = (
            value[0]
            if value
            else None
        )

    if not isinstance(
        value,
        str
    ):
        return value

    value = re.sub(
        r"\$\{([^}]+)\}",
        r"\1",
        value
    )

    return value.strip()


def _convert_value_for_column(
    column,
    value: Any
) -> Any:
    """
    Convert a runtime value according to the reflected
    SQLAlchemy column type.

    The reflected database type is the single source of truth.
    """
    if value is None:
        return None

    column_type = column.type

    if _is_binary_column(
        column
    ):
        return _binary_value_to_bytes(
            value,
            column.name
        )

    value = _strip_placeholder(
        value
    )

    if value == "":
        return None

    try:
        if isinstance(
            column_type,
            DateTime
        ):
            if isinstance(
                value,
                datetime
            ):
                return value

            if isinstance(
                value,
                date
            ):
                return datetime.combine(
                    value,
                    datetime.min.time()
                )

            return datetime.fromisoformat(
                str(value).replace(
                    "Z",
                    "+00:00"
                )
            )

        if isinstance(
            column_type,
            Date
        ):
            if isinstance(
                value,
                datetime
            ):
                return value.date()

            if isinstance(
                value,
                date
            ):
                return value

            return date.fromisoformat(
                str(value)
            )

        if isinstance(
            column_type,
            PGUUID
        ):
            if isinstance(
                value,
                uuid.UUID
            ):
                return value

            return uuid.UUID(
                str(value)
            )

        if isinstance(
            column_type,
            Boolean
        ):
            if isinstance(
                value,
                bool
            ):
                return value

            normalized = (
                str(value)
                .strip()
                .lower()
            )

            if normalized in (
                "true",
                "1",
                "yes",
                "y",
                "on"
            ):
                return True

            if normalized in (
                "false",
                "0",
                "no",
                "n",
                "off"
            ):
                return False

            raise ValueError(
                f"Unsupported boolean value '{value}'"
            )

        if isinstance(
            column_type,
            Integer
        ):
            return int(value)

        if isinstance(
            column_type,
            Float
        ):
            return float(value)

        if isinstance(
            column_type,
            Numeric
        ):
            return Decimal(
                str(value)
            )

        if isinstance(
            column_type,
            String
        ):
            return str(value)

        return value

    except (
        ValueError,
        TypeError,
        OverflowError
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid value '{value}' for column "
                f"'{column.name}' of type "
                f"'{column_type}': {exc}"
            )
        )


# -------------------------------
# Serialization Helpers
# -------------------------------

def _sanitize_for_log(
    value: Any
) -> Any:
    """
    Sanitize request values before error logging.

    Binary content is represented by its size and is never
    copied into the error log.
    """
    if isinstance(
        value,
        (bytes, bytearray, memoryview)
    ):
        return {
            "binary": True,
            "size_bytes": len(value)
        }

    if isinstance(
        value,
        dict
    ):
        return {
            str(key): _sanitize_for_log(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        (list, tuple)
    ):
        return [
            _sanitize_for_log(item)
            for item in value
        ]

    if isinstance(
        value,
        (date, datetime, Decimal, uuid.UUID)
    ):
        return str(value)

    try:
        json.dumps(value)
        return value

    except (
        TypeError,
        ValueError
    ):
        return str(value)


def _json_safe(
    value: Any
) -> Any:
    """
    Convert runtime values to JSON-safe values for
    t_error_log.parameters.
    """
    try:
        return json.loads(
            json.dumps(
                _sanitize_for_log(value),
                default=str
            )
        )

    except (
        TypeError,
        ValueError
    ):
        return str(
            _sanitize_for_log(value)
        )


def row_to_dict(
    row
):
    """
    Convert an ORM object to a JSON-safe dictionary.

    Binary column values are excluded from the response.
    Their availability and size are returned through __file_fields.
    """
    if not row:
        return None

    result = {}
    file_fields = {}

    for column in row.__table__.columns:
        value = getattr(
            row,
            column.name
        )

        if _is_binary_column(
            column
        ):
            binary_size = (
                len(value)
                if value is not None
                else 0
            )

            file_fields[column.name] = {
                "available": binary_size > 0,
                "file_size_bytes": binary_size
            }

            continue

        result[column.name] = value

    if file_fields:
        result["__file_fields"] = file_fields

    return result


def _build_read_projection(
    Model
):
    """
    Build a database projection that excludes binary content.

    Normal columns are selected directly.
    Binary columns are represented only by their byte length.
    """
    selected_columns = []
    normal_fields = []
    binary_fields = {}

    for index, column in enumerate(
        Model.__table__.columns
    ):
        if _is_binary_column(
            column
        ):
            size_alias = (
                f"__pulsar_file_size_{index}"
            )

            selected_columns.append(
                func.octet_length(
                    getattr(
                        Model,
                        column.name
                    )
                ).label(
                    size_alias
                )
            )

            binary_fields[column.name] = size_alias

        else:
            selected_columns.append(
                getattr(
                    Model,
                    column.name
                )
            )

            normal_fields.append(
                column.name
            )

    return (
        selected_columns,
        normal_fields,
        binary_fields
    )


def _projection_row_to_dict(
    row,
    normal_fields,
    binary_fields
):
    """
    Convert a projected database row into the standard
    dynamic component response format.

    Binary content is never selected or transferred.
    """
    if row is None:
        return None

    result = {
        field: row[field]
        for field in normal_fields
    }

    file_fields = {}

    for field_name, size_alias in binary_fields.items():
        binary_size = row[size_alias] or 0

        file_fields[field_name] = {
            "available": binary_size > 0,
            "file_size_bytes": binary_size
        }

    if file_fields:
        result["__file_fields"] = file_fields

    return result


# -------------------------------
# Query Error Context
# -------------------------------

async def _handle_database_error(
    session: AsyncSession,
    exc: Exception,
    *,
    error_code: str,
    component_name: str,
    operation_name: str,
    base: dict | None = None,
    request: Request | None = None,
    parameters: Any = None,
    function_name: str | None = None
):
    """
    Roll back the failed transaction and register the database error
    through the central query error handler.
    """
    await handle_query_error(
        session,
        exc,
        error_code=error_code,
        schema_name=(
            base.get("schm_name")
            if base
            else None
        ),
        table_name=(
            base.get("tbl_name")
            if base
            else None
        ),
        component_name=component_name,
        file_name="backend/core/component_data.py",
        function_name=function_name,
        operation_name=operation_name,
        parameters=_json_safe(
            parameters
        ),
        stack_trace=traceback.format_exc(),
        request_method=(
            request.method
            if request
            else None
        ),
        request_path=(
            str(request.url.path)
            if request
            else None
        )
    )


# -------------------------------
# Query Scope
# -------------------------------

def apply_scope_query(
    query,
    Model,
    scope_dict: Dict[str, Any]
):
    """
    Apply resolved equality filters to a SQLAlchemy query.

    Values are converted according to reflected column types.
    """
    if not scope_dict:
        return query

    columns = {
        column.name: column
        for column in Model.__table__.columns
    }

    for field, value in scope_dict.items():
        column = columns.get(
            field
        )

        if column is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid scope column: "
                    f"{field}"
                )
            )

        clean_value = _convert_value_for_column(
            column,
            value
        )

        query = query.where(
            getattr(
                Model,
                field
            ) == clean_value
        )

    return query


# -------------------------------
# Primary Key Execution
# -------------------------------

def _build_primary_key_filters(
    primary_key,
    identity: str,
    Model
):
    """
    Resolve an opaque primary-key identity through
    component_key.py.

    This function only performs database-column type conversion
    after primary-key semantics have already been resolved.
    """
    values = resolve_primary_key_identity_values(
        primary_key,
        identity
    )

    columns = {
        column.name: column
        for column in Model.__table__.columns
    }

    filters: Dict[str, Any] = {}

    for field, value in values.items():
        column = columns.get(
            field
        )

        if column is None:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Primary key column not found: "
                    f"{field}"
                )
            )

        filters[field] = _convert_value_for_column(
            column,
            value
        )

    return filters


def _apply_primary_key_filters(
    query,
    Model,
    primary_key_filters: Dict[str, Any]
):
    """
    Apply already-resolved primary-key filters.

    Primary-key meaning is not interpreted here.
    """
    for field, value in primary_key_filters.items():
        query = query.where(
            getattr(
                Model,
                field
            ) == value
        )

    return query


# -------------------------------
# Dynamic Router Factory
# -------------------------------

def create_component_data_router(
    component_name: str,
    field_mode: str
):
    """
    Create the dynamic CRUD router for one component.

    field_mode is retained by the factory because route discovery
    is metadata-driven. It is not part of components_base lookup.
    """
    router = APIRouter(
        prefix=f"/dw/{component_name}",
        tags=["Dynamic-data"]
    )

    # ---------------------------------------------
    # LIST
    # ---------------------------------------------

    @router.get(
        "/list/data"
    )
    async def list_records(
        request: Request,
        session: AsyncSession =
            Depends(
                get_async_session
            )
    ):
        base = await _load_base(
            session,
            component_name,
            "list"
        )

        Model = await _build_model(
            session,
            base,
            component_name,
            request,
            "list"
        )

        scope_dict, raw_sql = (
            await _resolve_request_scope(
                request,
                base,
                component_name,
                session,
                Model
            )
        )

        (
            selected_columns,
            normal_fields,
            binary_fields
        ) = _build_read_projection(
            Model
        )

        query = select(
            *selected_columns
        )

        if scope_dict:
            query = apply_scope_query(
                query,
                Model,
                scope_dict
            )

        elif raw_sql:
            query = query.where(
                sql_text(raw_sql)
            )

        try:
            result = await session.execute(
                query
            )

        except SQLAlchemyError as exc:
            await _handle_database_error(
                session,
                exc,
                error_code=QUERY_COMPONENT_DATA_LIST,
                component_name=component_name,
                operation_name="LIST",
                base=base,
                request=request,
                parameters={
                    "where_scope": scope_dict,
                    "raw_sql": raw_sql
                },
                function_name="list_records"
            )
            raise

        rows = result.mappings().all()

        return [
            _projection_row_to_dict(
                row,
                normal_fields,
                binary_fields
            )
            for row in rows
        ]

    # ---------------------------------------------
    # VIEW
    # ---------------------------------------------

    @router.get(
        "/view/data/{pk}"
    )
    async def view_record(
        pk: str,
        request: Request,
        session: AsyncSession =
            Depends(
                get_async_session
            )
    ):
        base = await _load_base(
            session,
            component_name,
            "view"
        )

        Model = await _build_model(
            session,
            base,
            component_name,
            request,
            "view"
        )

        primary_key = base["primary_key"]

        primary_key_filters = (
            _build_primary_key_filters(
                primary_key,
                pk,
                Model
            )
        )

        scope_dict, raw_sql = (
            await _resolve_request_scope(
                request,
                base,
                component_name,
                session,
                Model
            )
        )

        (
            selected_columns,
            normal_fields,
            binary_fields
        ) = _build_read_projection(
            Model
        )

        query = select(
            *selected_columns
        )

        query = _apply_primary_key_filters(
            query,
            Model,
            primary_key_filters
        )

        if scope_dict:
            query = apply_scope_query(
                query,
                Model,
                scope_dict
            )

        elif raw_sql:
            query = query.where(
                sql_text(raw_sql)
            )

        try:
            result = await session.execute(
                query
            )

        except SQLAlchemyError as exc:
            await _handle_database_error(
                session,
                exc,
                error_code=QUERY_COMPONENT_DATA_VIEW,
                component_name=component_name,
                operation_name="VIEW",
                base=base,
                request=request,
                parameters={
                    "primary_key": pk,
                    "primary_key_filters": primary_key_filters,
                    "where_scope": scope_dict,
                    "raw_sql": raw_sql
                },
                function_name="view_record"
            )
            raise

        row = result.mappings().one_or_none()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Record not found within scope"
            )

        return _projection_row_to_dict(
            row,
            normal_fields,
            binary_fields
        )

    # ---------------------------------------------
    # FILE DOWNLOAD
    # ---------------------------------------------

    @router.get(
        "/file/{pk}/{field_name}"
    )
    async def download_file(
        pk: str,
        field_name: str,
        request: Request,
        session: AsyncSession =
            Depends(
                get_async_session
            )
    ):
        """
        Download a binary field from a scoped dynamic record.

        The requested field must exist and must be a reflected
        SQLAlchemy binary column.
        """
        base = await _load_base(
            session,
            component_name,
            "view"
        )

        Model = await _build_model(
            session,
            base,
            component_name,
            request,
            "file_download"
        )

        columns = {
            column.name: column
            for column in Model.__table__.columns
        }

        column = columns.get(
            field_name
        )

        if column is None:
            raise HTTPException(
                status_code=404,
                detail="File field not found."
            )

        if not _is_binary_column(
            column
        ):
            raise HTTPException(
                status_code=400,
                detail="Requested field is not a binary column."
            )

        primary_key_filters = (
            _build_primary_key_filters(
                base["primary_key"],
                pk,
                Model
            )
        )

        scope_dict, raw_sql = (
            await _resolve_request_scope(
                request,
                base,
                component_name,
                session,
                Model
            )
        )

        query = select(
            getattr(
                Model,
                field_name
            )
        )

        query = _apply_primary_key_filters(
            query,
            Model,
            primary_key_filters
        )

        if scope_dict:
            query = apply_scope_query(
                query,
                Model,
                scope_dict
            )

        elif raw_sql:
            query = query.where(
                sql_text(raw_sql)
            )

        try:
            result = await session.execute(
                query
            )

        except SQLAlchemyError as exc:
            await _handle_database_error(
                session,
                exc,
                error_code=QUERY_COMPONENT_FILE_DOWNLOAD,
                component_name=component_name,
                operation_name="FILE_DOWNLOAD",
                base=base,
                request=request,
                parameters={
                    "primary_key": pk,
                    "field_name": field_name,
                    "where_scope": scope_dict,
                    "raw_sql": raw_sql
                },
                function_name="download_file"
            )
            raise

        content = result.scalar_one_or_none()

        if content is None or len(content) == 0:
            raise HTTPException(
                status_code=404,
                detail="File content not found."
            )

        safe_filename = re.sub(
            r"[^A-Za-z0-9._-]",
            "_",
            field_name
        ) or "download"

        file_configs = await _load_file_field_configs(
            session,
            component_name,
            "view",
        )
        file_config = file_configs.get(field_name, {})
        accepted_types = [
            str(item).strip().lower()
            for item in file_config.get("accepted_mime_types", [])
            if str(item).strip()
        ]

        extension = next(
            (
                item for item in accepted_types
                if item.startswith(".")
                and re.fullmatch(r"\.[a-z0-9]{1,10}", item)
            ),
            None,
        )
        if extension is None and "application/pdf" in accepted_types:
            extension = ".pdf"

        if extension and not safe_filename.lower().endswith(extension):
            safe_filename = f"{safe_filename}{extension}"

        media_type = next(
            (
                item for item in accepted_types
                if "/" in item and not item.endswith("/*")
            ),
            "application/octet-stream",
        )

        encoded_filename = quote(
            safe_filename
        )

        return Response(
            content=bytes(content),
            media_type=media_type,
            headers={
                "Content-Disposition": (
                    f"attachment; filename=\"{safe_filename}\"; "
                    f"filename*=UTF-8''{encoded_filename}"
                ),
                "Content-Length": str(len(content)),
                "Cache-Control": "no-store"
            }
        )

    # ---------------------------------------------
    # INSERT
    # ---------------------------------------------

    @router.post(
        "/insert/data/"
    )
    async def insert_record(
        request: Request,
        session: AsyncSession =
            Depends(
                get_async_session
            )
    ):
        base = await _load_base(
            session,
            component_name,
            "insert"
        )

        Model = await _build_model(
            session,
            base,
            component_name,
            request,
            "insert"
        )

        columns = {
            column.name: column
            for column in Model.__table__.columns
        }

        file_configs = await _load_file_field_configs(
            session,
            component_name,
            "insert",
        )

        data = await _parse_request_data(
            request,
            columns,
            file_configs,
        )

        clean_data = {}

        for key, value in data.items():
            column = columns.get(
                key
            )

            if column is None:
                continue

            clean_data[key] = (
                _convert_value_for_column(
                    column,
                    value
                )
            )

        obj = Model(
            **clean_data
        )

        try:
            session.add(
                obj
            )

            await session.flush()

            identity = inspect(obj).identity

            if identity is None:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Unable to resolve inserted record identity."
                    )
                )

            primary_key_columns = (
                Model.__table__.primary_key.columns
            )

            if len(identity) != len(primary_key_columns):
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Inserted record identity is incomplete."
                    )
                )

            (
                selected_columns,
                normal_fields,
                binary_fields
            ) = _build_read_projection(
                Model
            )

            query = select(
                *selected_columns
            )

            for column, value in zip(
                primary_key_columns,
                identity
            ):
                query = query.where(
                    column == value
                )

            result = await session.execute(
                query
            )

            row = result.mappings().one_or_none()

            if row is None:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Inserted record could not be retrieved."
                    )
                )

            response_data = _projection_row_to_dict(
                row,
                normal_fields,
                binary_fields
            )

            await session.commit()

            return response_data

        except HTTPException:
            await session.rollback()
            raise

        except SQLAlchemyError as exc:
            await _handle_database_error(
                session,
                exc,
                error_code=QUERY_COMPONENT_DATA_INSERT,
                component_name=component_name,
                operation_name="INSERT",
                base=base,
                request=request,
                parameters={
                    "data": clean_data_for_log(
                        clean_data
                    )
                },
                function_name="insert_record"
            )
            raise

    # ---------------------------------------------
    # UPDATE
    # ---------------------------------------------

    @router.put(
        "/update/data/{pk}"
    )
    async def update_record(
        pk: str,
        request: Request,
        session: AsyncSession =
            Depends(
                get_async_session
            )
    ):
        base = await _load_base(
            session,
            component_name,
            "update"
        )

        Model = await _build_model(
            session,
            base,
            component_name,
            request,
            "update"
        )

        columns = {
            column.name: column
            for column in Model.__table__.columns
        }

        file_configs = await _load_file_field_configs(
            session,
            component_name,
            "update",
        )

        data = await _parse_request_data(
            request,
            columns,
            file_configs,
        )

        clean_data = {}

        for key, value in data.items():
            column = columns.get(
                key
            )

            if column is None:
                continue

            clean_data[key] = (
                _convert_value_for_column(
                    column,
                    value
                )
            )

        primary_key = base["primary_key"]

        primary_key_filters = (
            _build_primary_key_filters(
                primary_key,
                pk,
                Model
            )
        )

        scope_dict, raw_sql = (
            await _resolve_request_scope(
                request,
                base,
                component_name,
                session,
                Model
            )
        )

        (
            selected_columns,
            normal_fields,
            binary_fields
        ) = _build_read_projection(
            Model
        )

        if clean_data:
            query = update(
                Model
            ).values(
                **clean_data
            )

        else:
            query = select(
                *selected_columns
            )

        query = _apply_primary_key_filters(
            query,
            Model,
            primary_key_filters
        )

        if scope_dict:
            query = apply_scope_query(
                query,
                Model,
                scope_dict
            )

        elif raw_sql:
            query = query.where(
                sql_text(raw_sql)
            )

        if clean_data:
            query = query.returning(
                *selected_columns
            )

        try:
            result = await session.execute(
                query
            )

            row = result.mappings().one_or_none()

            if row is None:
                await session.rollback()

                raise HTTPException(
                    status_code=404,
                    detail="Record not found"
                )

            response_data = _projection_row_to_dict(
                row,
                normal_fields,
                binary_fields
            )

            await session.commit()

            return response_data

        except HTTPException:
            await session.rollback()
            raise

        except SQLAlchemyError as exc:
            await _handle_database_error(
                session,
                exc,
                error_code=QUERY_COMPONENT_DATA_UPDATE,
                component_name=component_name,
                operation_name="UPDATE",
                base=base,
                request=request,
                parameters={
                    "primary_key": pk,
                    "primary_key_filters": primary_key_filters,
                    "data": clean_data_for_log(
                        clean_data
                    ),
                    "where_scope": scope_dict,
                    "raw_sql": raw_sql
                },
                function_name="update_record"
            )
            raise

    # ---------------------------------------------
    # DELETE
    # ---------------------------------------------

    @router.delete(
        "/delete/data/{pk}"
    )
    async def delete_record(
        pk: str,
        request: Request,
        session: AsyncSession =
            Depends(
                get_async_session
            )
    ):
        base = await _load_base(
            session,
            component_name,
            "delete"
        )

        Model = await _build_model(
            session,
            base,
            component_name,
            request,
            "delete"
        )

        primary_key = base["primary_key"]

        primary_key_filters = (
            _build_primary_key_filters(
                primary_key,
                pk,
                Model
            )
        )

        scope_dict, raw_sql = (
            await _resolve_request_scope(
                request,
                base,
                component_name,
                session,
                Model
            )
        )

        query = select(
            Model
        )

        query = _apply_primary_key_filters(
            query,
            Model,
            primary_key_filters
        )

        if scope_dict:
            query = apply_scope_query(
                query,
                Model,
                scope_dict
            )

        elif raw_sql:
            query = query.where(
                sql_text(raw_sql)
            )

        try:
            result = await session.execute(
                query
            )

        except SQLAlchemyError as exc:
            await _handle_database_error(
                session,
                exc,
                error_code=QUERY_COMPONENT_DATA_DELETE,
                component_name=component_name,
                operation_name="DELETE_SELECT",
                base=base,
                request=request,
                parameters={
                    "primary_key": pk,
                    "primary_key_filters": primary_key_filters,
                    "where_scope": scope_dict,
                    "raw_sql": raw_sql
                },
                function_name="delete_record"
            )
            raise

        obj = result.scalar_one_or_none()

        if not obj:
            raise HTTPException(
                status_code=404,
                detail="Record not found"
            )

        # ---------------------------------------------
        # Child Record Guard
        # ---------------------------------------------

        primary_key_values = json.dumps(
            _json_safe(
                primary_key_filters
            )
        )

        try:
            child_result = await session.execute(
                sql_text(
                    """
                    SELECT pulsar.fn_has_child(
                        :p_schema_name,
                        :p_table_name,
                        :p_primary_key,
                        CAST(:p_primary_key_values AS jsonb)
                    )
                    """
                ),
                {
                    "p_schema_name": base["schm_name"],
                    "p_table_name": base["tbl_name"],
                    "p_primary_key": primary_key,
                    "p_primary_key_values": primary_key_values
                }
            )

        except SQLAlchemyError as exc:
            await _handle_database_error(
                session,
                exc,
                error_code=QUERY_COMPONENT_DATA_DELETE_HAS_CHILD,
                component_name=component_name,
                operation_name="DELETE_HAS_CHILD",
                base=base,
                request=request,
                parameters={
                    "primary_key": pk,
                    "primary_key_filters": primary_key_filters
                },
                function_name="delete_record"
            )
            raise

        has_child = bool(
            child_result.scalar()
        )

        if has_child:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "RECORD_HAS_CHILD",
                    "message_key": "record_has_child"
                }
            )

        await session.delete(
            obj
        )

        try:
            await session.commit()

        except SQLAlchemyError as exc:
            await _handle_database_error(
                session,
                exc,
                error_code=QUERY_COMPONENT_DATA_DELETE,
                component_name=component_name,
                operation_name="DELETE_COMMIT",
                base=base,
                request=request,
                parameters={
                    "primary_key": pk
                },
                function_name="delete_record"
            )
            raise

        return {
            "status": "deleted",
            "id": pk
        }

    return router


# -------------------------------
# Request Scope
# -------------------------------

async def _resolve_request_scope(
    request: Request,
    base: dict,
    component_name: str,
    session: AsyncSession,
    Model
):
    """
    Delegate all where_clause semantics to component_where.py.

    component_data.py only transports the explicit
    where_clause[field] request values and supplies the reflected
    Model for database-type conversion.
    """
    base_where = (
        base.get(
            "where_clause"
        ) or ""
    ).strip()

    resolver: Dict[str, Any] = {}

    for key, value in request.query_params.items():
        match = re.match(
            r"^where_clause\[(?P<key>[^\]]+)\]$",
            key
        )

        if not match:
            continue

        resolver[
            match.group("key")
        ] = _strip_placeholder(
            value
        )

    return await resolve_where_request_scope(
        where_clause=base_where,
        component_name=component_name,
        resolver=resolver,
        model=Model,
        converter=_convert_value_for_column
    )


# -------------------------------
# Internal Helpers
# -------------------------------

async def _load_base(
    session: AsyncSession,
    component_name: str,
    field_mode: str
):
    """
    Load basic component metadata through the centralized
    component_base layer.

    field_mode is retained at the caller boundary for now,
    but it is not part of components_base metadata lookup.
    """
    try:
        return await get_component_base(
            session,
            component_name
        )

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )


async def _build_model(
    session: AsyncSession,
    base_meta: dict,
    component_name: str,
    request: Request | None,
    operation_name: str
):
    """
    Reflect the physical database table and dynamically
    build an ORM model.

    No table-specific fields or types are hard-coded here.
    """
    metadata = MetaData()
    mapper_registry = registry()

    schm_name = base_meta["schm_name"]
    tbl_name = base_meta["tbl_name"]

    try:
        async with session.bind.connect() as conn:
            await conn.run_sync(
                metadata.reflect,
                schema=schm_name,
                only=[tbl_name]
            )

            table = metadata.tables[
                f"{schm_name}.{tbl_name}"
            ]

        model_cls = type(
            tbl_name.capitalize(),
            (),
            {}
        )

        mapper_registry.map_imperatively(
            model_cls,
            table
        )

        return model_cls

    except SQLAlchemyError as exc:
        await _handle_database_error(
            session,
            exc,
            error_code=QUERY_COMPONENT_MODEL_REFLECT,
            component_name=component_name,
            operation_name=f"{operation_name}_REFLECT",
            base=base_meta,
            request=request,
            parameters={
                "schema_name": schm_name,
                "table_name": tbl_name
            },
            function_name="_build_model"
        )
        raise


# -------------------------------
# Logging Helper
# -------------------------------

def clean_data_for_log(
    data: Any
) -> Any:
    """
    Convert request data into JSON-safe values
    before sending them to the error logger.

    Binary content is represented by its size only.
    """
    return _json_safe(
        data
    )


# -------------------------------
# Important Learning Points
# -------------------------------
#
# 1. component_data.py is the CRUD/query execution layer.
#
# 2. Basic component metadata is loaded through component_base.py.
#
# 3. Primary-key semantics belong exclusively to component_key.py.
#
# 4. Composite primary-key identity parsing belongs exclusively to
#    component_key.py.
#
# 5. component_data.py treats record identity as an opaque value until
#    component_key.py resolves it.
#
# 6. where_clause semantics belong exclusively to component_where.py.
#
# 7. component_data.py delegates where_clause resolution to
#    component_where.py.
#
# 8. component_data.py does not create parm[n].
#
# 9. component_data.py does not map profile_id to parm[n].
#
# 10. Type conversion remains here because it depends on the reflected
#     SQLAlchemy column type.
#
# 11. INSERT and UPDATE accept JSON and multipart/form-data.
#
# 12. Binary uploads are accepted only for reflected binary columns.
#
# 13. Binary data is excluded from normal CRUD responses.
#
# 14. Binary availability is exposed through __file_fields.
#
# 15. File downloads use the same primary-key and where-clause scope.
#
# 16. An omitted file during UPDATE preserves the existing binary value.
#
# 17. Binary content is never copied into query error logs.
#
# 18. Database/query errors are delegated to query_error.py.
#
# 19. Failed transactions are rolled back before error logging.
#
# 20. HTTPException is not treated as a database query error.
#
# 21. No table-specific field, primary-key, or parm mapping is hard-coded.
#
# 22. field_mode is not part of components_base metadata.
#
# 23. INSERT uses flush and a projected SELECT instead of refreshing
#     the complete ORM object.
#
# 24. UPDATE uses SQLAlchemy Core UPDATE RETURNING instead of loading
#     the complete ORM object.
#
# 25. LIST, VIEW, INSERT, and UPDATE retrieve binary sizes without
#     transferring binary content to the application.
#
# 26. DELETE checks pulsar.fn_has_child before deleting the record.
#
# 27. fn_has_child receives the reflected and type-converted primary-key
#     values as a JSONB object, supporting single and composite keys.
#
# 28. A record with child records is rejected with the stable business
#     error code RECORD_HAS_CHILD.
