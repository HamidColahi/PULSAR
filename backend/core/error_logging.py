# ===============================================
# File: backend/core/error_logging.py
#
# Description:
# Central application runtime error logging
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# Last Modified: 2026-11-27 (Asia/Baku)
# ===============================================

import json
from typing import Any

from sqlalchemy import text

from core.database import AsyncSessionLocal


async def log_runtime_error(
    *,
    error_code: str,
    user_message: str,
    error_text: str,
    severity: str = "WARNING",
    error_type: str | None = None,
    user_action: str | None = None,
    application_name: str = "PULSAR",
    module_name: str | None = None,
    component_name: str | None = None,
    file_name: str | None = None,
    function_name: str | None = None,
    operation_name: str | None = None,
    request_method: str | None = None,
    request_path: str | None = None,
    schema_name: str | None = None,
    table_name: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> int | None:
    """
    Register an application-level runtime issue.

    The canonical message is created once. Each occurrence receives
    its own t_error_log record. Logging failures never interrupt the
    application operation being monitored.
    """
    try:
        serialized_parameters = (
            json.dumps(
                parameters,
                default=str,
                ensure_ascii=False
            )
            if parameters is not None
            else None
        )

        async with AsyncSessionLocal() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO pulsar.t_error_message (
                        error_code,
                        user_message,
                        user_action,
                        c_state
                    )
                    VALUES (
                        :error_code,
                        :user_message,
                        :user_action,
                        'ACTIVE'
                    )
                    ON CONFLICT (error_code) DO NOTHING
                    """
                ),
                {
                    "error_code": error_code,
                    "user_message": user_message,
                    "user_action": user_action,
                }
            )

            result = await session.execute(
                text(
                    """
                    INSERT INTO pulsar.t_error_log (
                        error_code,
                        severity,
                        error_type,
                        application_name,
                        module_name,
                        component_name,
                        file_name,
                        function_name,
                        operation_name,
                        request_method,
                        request_path,
                        schema_name,
                        table_name,
                        error_text,
                        parameters,
                        c_state,
                        log_state
                    )
                    VALUES (
                        :error_code,
                        :severity,
                        :error_type,
                        :application_name,
                        :module_name,
                        :component_name,
                        :file_name,
                        :function_name,
                        :operation_name,
                        :request_method,
                        :request_path,
                        :schema_name,
                        :table_name,
                        :error_text,
                        CAST(:parameters AS JSONB),
                        'NEW',
                        'INSERT'
                    )
                    RETURNING error_id
                    """
                ),
                {
                    "error_code": error_code,
                    "severity": severity,
                    "error_type": error_type,
                    "application_name": application_name,
                    "module_name": module_name,
                    "component_name": component_name,
                    "file_name": file_name,
                    "function_name": function_name,
                    "operation_name": operation_name,
                    "request_method": request_method,
                    "request_path": request_path,
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "error_text": error_text,
                    "parameters": serialized_parameters,
                }
            )

            error_id = result.scalar_one()
            await session.commit()
            return error_id

    except Exception:
        # Diagnostic logging must never break the primary operation.
        return None


# -----------------------------------------------
# Important Learning Points
# -----------------------------------------------
# 1. t_error_message stores one canonical definition per error code.
# 2. t_error_log stores every runtime occurrence independently.
# 3. Application issues use WARNING when normal processing can continue.
# 4. Developer investigation and resolution are recorded in t_error_action.
# 5. A separate session isolates logging from the primary transaction.
# 6. Logging failures never interrupt the monitored application operation.
# 7. Runtime parameters are serialized for JSONB storage.
