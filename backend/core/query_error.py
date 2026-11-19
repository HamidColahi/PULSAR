# =============================================
# File:
# backend/core/query_error.py
#
# Description:
# Central query error handling and database logging
#
# Responsibilities:
#   1. Capture SQLAlchemy query/database exceptions
#   2. Roll back the failed query transaction
#   3. Register the error through pulsar.fn_log_query_error
#   4. Use an independent database session for error logging
#   5. Preserve technical database error information
#   6. Never convert the original database exception into a silent success
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# =============================================

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal

# ---------------------------------------------
# Error Code
# ---------------------------------------------
DEFAULT_QUERY_ERROR_CODE = "QUERY_EXECUTION_FAILED"

# ---------------------------------------------
# PostgreSQL Error Extraction
# ---------------------------------------------
def _extract_db_error(
    exc: Exception
) -> dict[str, Any]:
    """
    Extract technical information from a SQLAlchemy
    database exception.

    The original exception remains untouched.
    """
    sql_state = None
    error_text = str(exc)
    error_detail = None
    error_hint = None

    original = getattr(
        exc,
        "orig",
        None
    )

    if original is not None:
        error_text = str(original)

        sql_state = getattr(
            original,
            "sqlstate",
            None
        )

        if sql_state is None:
            sql_state = getattr(
                original,
                "pgcode",
                None
            )

        error_detail = getattr(
            original,
            "detail",
            None
        )

        error_hint = getattr(
            original,
            "hint",
            None
        )

    return {
        "sql_state": sql_state,
        "error_text": error_text,
        "error_detail": error_detail,
        "error_hint": error_hint
    }

# ---------------------------------------------
# JSON Parameter Serialization
# ---------------------------------------------
def _serialize_parameters(
    parameters: dict[str, Any] | None
) -> str | None:
    """
    Serialize query parameters for PostgreSQL JSONB storage.

    The caller may provide values that are not directly JSON
    serializable. The fallback string conversion preserves
    diagnostic information without breaking error logging.
    """
    if parameters is None:
        return None

    return json.dumps(
        parameters,
        default=str,
        ensure_ascii=False
    )

# ---------------------------------------------
# Query Error Logger
# ---------------------------------------------
async def log_query_error(
    exc: Exception,
    *,
    error_code: str =
        DEFAULT_QUERY_ERROR_CODE,
    schema_name: str | None = None,
    table_name: str | None = None,
    component_name: str | None = None,
    file_name: str | None = None,
    function_name: str | None = None,
    operation_name: str | None = None,
    parameters: dict[str, Any] | None = None,
    stack_trace: str | None = None,
    application_name: str | None = None,
    request_method: str | None = None,
    request_path: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    user_id: int | None = None,
    profile_id: int | None = None,
    severity: str = "ERROR"
) -> int | None:
    """
    Register a query/database error in Pulsar.

    A completely independent database session is used so that
    the error logger remains operational even when the original
    transaction is in a failed state.

    Returns:
        Generated pulsar.t_error_log.error_id,
        or None if error logging itself fails.
    """
    error_info = _extract_db_error(
        exc
    )

    serialized_parameters = _serialize_parameters(
        parameters
    )

    try:
        async with AsyncSessionLocal() as log_session:
            result = await log_session.execute(
                text(
                    """
                    SELECT pulsar.fn_log_query_error(
                        CAST(:error_code AS VARCHAR),
                        CAST(:error_type AS VARCHAR),
                        CAST(:schema_name AS VARCHAR),
                        CAST(:table_name AS VARCHAR),
                        CAST(:component_name AS VARCHAR),
                        CAST(:file_name AS VARCHAR),
                        CAST(:function_name AS VARCHAR),
                        CAST(:operation_name AS VARCHAR),
                        CAST(:sql_state AS VARCHAR),
                        CAST(:error_text AS TEXT),
                        CAST(:error_detail AS TEXT),
                        CAST(:error_hint AS TEXT),
                        CAST(:parameters AS JSONB),
                        CAST(:stack_trace AS TEXT),
                        CAST(:application_name AS VARCHAR),
                        CAST(:request_method AS VARCHAR),
                        CAST(:request_path AS TEXT),
                        CAST(:request_id AS VARCHAR),
                        CAST(:trace_id AS VARCHAR),
                        CAST(:user_id AS BIGINT),
                        CAST(:profile_id AS BIGINT),
                        CAST(:severity AS VARCHAR)
                    )
                    """
                ),
                {
                    "error_code":
                        error_code,
                    "error_type":
                        "QUERY_ERROR",
                    "schema_name":
                        schema_name,
                    "table_name":
                        table_name,
                    "component_name":
                        component_name,
                    "file_name":
                        file_name,
                    "function_name":
                        function_name,
                    "operation_name":
                        operation_name,
                    "sql_state":
                        error_info["sql_state"],
                    "error_text":
                        error_info["error_text"],
                    "error_detail":
                        error_info["error_detail"],
                    "error_hint":
                        error_info["error_hint"],
                    "parameters":
                        serialized_parameters,
                    "stack_trace":
                        stack_trace,
                    "application_name":
                        application_name,
                    "request_method":
                        request_method,
                    "request_path":
                        request_path,
                    "request_id":
                        request_id,
                    "trace_id":
                        trace_id,
                    "user_id":
                        user_id,
                    "profile_id":
                        profile_id,
                    "severity":
                        severity
                }
            )

            error_id = result.scalar_one()

            await log_session.commit()

            return error_id

    except Exception:
        # Error logging must never hide the original query error.
        return None

# ---------------------------------------------
# Handle Query Error
# ---------------------------------------------
async def handle_query_error(
    session: AsyncSession,
    exc: Exception,
    *,
    error_code: str =
        DEFAULT_QUERY_ERROR_CODE,
    schema_name: str | None = None,
    table_name: str | None = None,
    component_name: str | None = None,
    file_name: str | None = None,
    function_name: str | None = None,
    operation_name: str | None = None,
    parameters: dict[str, Any] | None = None,
    stack_trace: str | None = None,
    application_name: str | None = None,
    request_method: str | None = None,
    request_path: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    user_id: int | None = None,
    profile_id: int | None = None,
    severity: str = "ERROR"
) -> int | None:
    """
    Roll back the failed transaction and register the query error.

    The original exception is not swallowed.
    """
    try:
        await session.rollback()
    except Exception:
        pass

    return await log_query_error(
        exc,
        error_code=error_code,
        schema_name=schema_name,
        table_name=table_name,
        component_name=component_name,
        file_name=file_name,
        function_name=function_name,
        operation_name=operation_name,
        parameters=parameters,
        stack_trace=stack_trace,
        application_name=application_name,
        request_method=request_method,
        request_path=request_path,
        request_id=request_id,
        trace_id=trace_id,
        user_id=user_id,
        profile_id=profile_id,
        severity=severity
    )

# ---------------------------------------------
# Important Learning Points
# ---------------------------------------------
# 1. Query errors are handled centrally.
# 2. Database error logging does not belong to individual components.
# 3. The failed application transaction is rolled back first.
# 4. Error logging uses AsyncSessionLocal independently.
# 5. PostgreSQL SQLSTATE is preserved when available.
# 6. PostgreSQL detail and hint are preserved when available.
# 7. Error logging failure must never hide the original query exception.
# 8. HTTPException is not handled here because it is not a database error.
# 9. Query parameters are serialized explicitly for JSONB storage.
# 10. All PostgreSQL function arguments are explicitly typed before
#     calling pulsar.fn_log_query_error.
# 11. The database function remains responsible for creating a missing
#     t_error_message definition before inserting t_error_log.
# 12. The original exception must be re-raised by the caller after this
#     handler completes.