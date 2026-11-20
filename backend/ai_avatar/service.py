# ===============================================
# File: Pulsar/backend/ai_avatar/service.py
#
# Description:
# Metadata-driven AI Avatar runtime with encrypted conversation persistence
#
# Change Date: 2026-11-20 16:10
# Timezone: Asia/Baku
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

import asyncio
import base64
import json
import os
import re
import uuid
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse, urlunparse

import logging

from tomlkit import item

logger = logging.getLogger(__name__)

import httpx
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from .context_contract import ContextContractError, validate_context_variables


class AIAvatarServiceError(Exception):
    """Represent a controlled AI Avatar runtime error."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AIAvatarService:
    """
    Resolve AI behavior from database metadata and persist encrypted history.

    Supported transports:
        HTTP_JSON
        WEBSOCKET_JSON

    Conversation content is encrypted with AES-256-GCM.
    Encryption keys must be supplied outside the database.
    """

    GLOBAL_AVATAR_MANAGER_ID = 3

    ENCRYPTION_KEY_ENV = "PULSAR_AI_AVATAR_ENCRYPTION_KEY"
    ENCRYPTION_KEY_REF_ENV = "PULSAR_AI_AVATAR_ENCRYPTION_KEY_REF"
    ENCRYPTION_KEY_VERSION_ENV = "PULSAR_AI_AVATAR_ENCRYPTION_KEY_VERSION"

    _TEMPLATE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")
    _HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
    _SUPPORTED_TRANSPORTS = {"HTTP_JSON", "WEBSOCKET_JSON"}

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------
    # Generic data helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _as_dict(value: Any) -> dict:
        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except (TypeError, ValueError):
                return {}

        return {}

    @staticmethod
    def _as_list(value: Any) -> list:
        if isinstance(value, list):
            return value

        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except (TypeError, ValueError):
                return []

        return []

    @staticmethod
    def _normalize_uuid(value: Any, field_name: str) -> str:
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError, AttributeError):
            raise AIAvatarServiceError(f"Invalid {field_name}.", 400)

    async def _fetch_one(
        self,
        statement: str,
        parameters: dict[str, Any],
    ) -> dict | None:
        result = await self.session.execute(text(statement), parameters)
        row = result.mappings().first()
        return dict(row) if row else None

    async def _fetch_all(
        self,
        statement: str,
        parameters: dict[str, Any],
    ) -> list[dict]:
        result = await self.session.execute(text(statement), parameters)
        return [dict(row) for row in result.mappings().all()]

    # ------------------------------------------------------------------
    # Canonical Context validation
    # ------------------------------------------------------------------

    @staticmethod
    def _context_string(value: Any, field_name: str) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str) or len(value) > 256:
            raise AIAvatarServiceError(
                f"Invalid Canonical Context field: {field_name}.",
                400,
            )

        return value

    @staticmethod
    def _context_identifier(value: Any, field_name: str) -> str | None:
        if value is None:
            return None

        if isinstance(value, bool):
            raise AIAvatarServiceError(
                f"Invalid Canonical Context field: {field_name}.",
                400,
            )

        if isinstance(value, str):
            if len(value) > 256:
                raise AIAvatarServiceError(
                    f"Invalid Canonical Context field: {field_name}.",
                    400,
                )
            return value

        if isinstance(value, int):
            return str(value)

        raise AIAvatarServiceError(
            f"Invalid Canonical Context field: {field_name}.",
            400,
        )

    @classmethod
    def _validate_selected_record(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None

        if not isinstance(value, dict):
            raise AIAvatarServiceError(
                "Canonical Context selected_record must be an object or null.",
                400,
            )

        if len(value) > 100:
            raise AIAvatarServiceError(
                "Canonical Context selected_record has too many fields.",
                400,
            )

        safe_record: dict[str, Any] = {}

        for field_name, field_value in value.items():
            if (
                not isinstance(field_name, str)
                or not re.fullmatch(
                    r"[A-Za-z][A-Za-z0-9_.-]{0,127}",
                    field_name,
                )
            ):
                raise AIAvatarServiceError(
                    "Canonical Context selected_record contains an invalid field name.",
                    400,
                )

            if field_value is None or isinstance(field_value, (bool, int)):
                safe_record[field_name] = field_value
            elif isinstance(field_value, float):
                if not (
                    float("-inf") < field_value < float("inf")
                ):
                    raise AIAvatarServiceError(
                        "Canonical Context selected_record contains an invalid numeric value.",
                        400,
                    )
                safe_record[field_name] = field_value
            elif isinstance(field_value, str):
                if len(field_value) > 2000:
                    raise AIAvatarServiceError(
                        "Canonical Context selected_record contains an oversized field value.",
                        413,
                    )
                safe_record[field_name] = field_value
            else:
                raise AIAvatarServiceError(
                    "Canonical Context selected_record may contain only scalar field values.",
                    400,
                )

        return safe_record

    @classmethod
    def _validate_context_variables(
        cls,
        value: Any,
    ) -> dict[str, Any]:
        """Validate and normalize PULSAR AI Avatar Context v1/v2."""
        try:
            return validate_context_variables(value)
        except ContextContractError as exc:
            raise AIAvatarServiceError(str(exc), 400) from exc

    @staticmethod
    def _get_path(data: Any, path: str) -> Any:
        if not path:
            return data

        current = data

        for part in path.split("."):
            if isinstance(current, dict):
                if part not in current:
                    raise AIAvatarServiceError(
                        f"Configured response path not found: {path}",
                        502,
                    )
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                index = int(part)

                if index >= len(current):
                    raise AIAvatarServiceError(
                        f"Configured response path is out of range: {path}",
                        502,
                    )

                current = current[index]
            else:
                raise AIAvatarServiceError(
                    f"Cannot resolve configured response path: {path}",
                    502,
                )

        return current

    @staticmethod
    def _try_get_path(data: Any, path: str) -> tuple[bool, Any]:
        try:
            return True, AIAvatarService._get_path(data, path)
        except AIAvatarServiceError:
            return False, None

    @classmethod
    def _render_string(cls, template: str, values: dict[str, Any]) -> str:
        def replace(match: re.Match) -> str:
            value = cls._get_path(values, match.group(1))

            if value is None:
                return ""

            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)

            return str(value)

        return cls._TEMPLATE_PATTERN.sub(replace, template)

    @classmethod
    def _render_value(cls, template: Any, values: dict[str, Any]) -> Any:
        if isinstance(template, dict):
            return {
                key: cls._render_value(value, values)
                for key, value in template.items()
            }

        if isinstance(template, list):
            return [
                cls._render_value(value, values)
                for value in template
            ]

        if isinstance(template, str):
            match = cls._TEMPLATE_PATTERN.fullmatch(template.strip())

            if match:
                return cls._get_path(values, match.group(1))

            return cls._render_string(template, values)

        return template

    @staticmethod
    def _merge_dicts(*values: dict) -> dict:
        result = {}

        for value in values:
            result.update(value)

        return result

    @staticmethod
    def _as_positive_timeout(value: Any) -> float:
        try:
            timeout = float(value)

            if not 1 <= timeout <= 300:
                raise ValueError

            return timeout
        except (TypeError, ValueError):
            raise AIAvatarServiceError(
                "timeout_seconds must be between 1 and 300.",
                409,
            )

    # ------------------------------------------------------------------
    # Provider URL and endpoint helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_base_url(base_url: Any):
        if not isinstance(base_url, str) or not base_url.strip():
            raise AIAvatarServiceError(
                "A provider base URL must be configured in metadata.",
                409,
            )

        parsed = urlparse(base_url)

        if (
            parsed.scheme not in {"http", "https", "ws", "wss"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise AIAvatarServiceError(
                "The configured provider base URL is invalid.",
                409,
            )

        return parsed

    @classmethod
    def _build_endpoint(
        cls,
        base_url: str,
        api_path: Any,
        transport: str,
    ) -> str:
        if not isinstance(api_path, str) or not api_path.strip():
            raise AIAvatarServiceError(
                "An API path must be configured in metadata.",
                409,
            )

        parsed_base = cls._validate_base_url(base_url)

        if transport == "HTTP_JSON" and parsed_base.scheme not in {"http", "https"}:
            raise AIAvatarServiceError(
                "HTTP_JSON requires an HTTP or HTTPS provider URL.",
                409,
            )

        endpoint = urljoin(
            base_url.rstrip("/") + "/",
            api_path.lstrip("/"),
        )

        parsed_endpoint = urlparse(endpoint)

        if (
            parsed_endpoint.netloc != parsed_base.netloc
            or parsed_endpoint.username
            or parsed_endpoint.password
        ):
            raise AIAvatarServiceError(
                "The API path must remain within the configured provider origin.",
                409,
            )

        if transport == "WEBSOCKET_JSON":
            scheme_map = {
                "http": "ws",
                "https": "wss",
                "ws": "ws",
                "wss": "wss",
            }

            endpoint = urlunparse(
                parsed_endpoint._replace(
                    scheme=scheme_map[parsed_endpoint.scheme]
                )
            )

        return endpoint

    # ------------------------------------------------------------------
    # Metadata resolution
    # ------------------------------------------------------------------

    async def get_active_definition(
        self,
        avatar_manager_id: int = GLOBAL_AVATAR_MANAGER_ID,
    ) -> dict[str, Any]:
        definitions = await self._fetch_all(
            """
            SELECT
                d.c_ai_definition_id,
                d.c_definition_code,
                d.c_title,
                d.c_description,
                d.c_default_language,
                d.c_avatar_manager_id
            FROM pulsar.t_ai_definition d
            WHERE d.c_avatar_manager_id = :avatar_manager_id
              AND d.c_enabled = TRUE
              AND upper(d.c_state) = 'ACTIVE'
            ORDER BY d.c_definition_code
            """,
            {"avatar_manager_id": avatar_manager_id},
        )

        if not definitions:
            raise AIAvatarServiceError(
                "No active AI Avatar definition was found for the Avatar Manager.",
                404,
            )

        if len(definitions) > 1:
            raise AIAvatarServiceError(
                "Multiple active AI Avatar definitions were found for the Avatar Manager.",
                409,
            )

        return definitions[0]

    # ------------------------------------------------------------------
    # First-time Avatar introduction
    # ------------------------------------------------------------------

    async def get_first_introduction(
        self,
        user_id: str,
        definition_code: str,
        language_code: str | None = None,
    ) -> dict[str, Any]:
        """Return the introduction only once per user and Avatar definition."""

        user_id = self._normalize_uuid(
            user_id,
            "authenticated user ID",
        )

        definition = await self._fetch_one(
            """
            SELECT
                d.c_ai_definition_id,
                d.c_avatar_manager_id,
                d.c_definition_code,
                d.c_default_language,
                d.c_introduction_enabled,
                d.c_introduction_translation_key
            FROM pulsar.t_ai_definition d
            WHERE d.c_definition_code = :definition_code
              AND d.c_enabled = TRUE
              AND upper(d.c_state) = 'ACTIVE'
            """,
            {"definition_code": definition_code},
        )

        if not definition:
            raise AIAvatarServiceError(
                "AI Avatar definition was not found or is inactive.",
                404,
            )

        if not definition["c_introduction_enabled"]:
            return {
                "definition_code": definition["c_definition_code"],
                "show_introduction": False,
                "message": None,
            }

        translation_key = definition[
            "c_introduction_translation_key"
        ]

        if not translation_key:
            raise AIAvatarServiceError(
                "The AI Avatar introduction translation key is not configured.",
                409,
            )

        requested_language = (
            language_code.strip().lower()
            if isinstance(language_code, str) and language_code.strip()
            else None
        )
        default_language = (
            str(definition["c_default_language"]).strip().lower()
            if definition["c_default_language"]
            else None
        )

        language_preferences = []

        for candidate in (
            requested_language,
            default_language,
            "en",
        ):
            if candidate and candidate not in language_preferences:
                language_preferences.append(candidate)

        translation = await self._fetch_one(
            """
            SELECT
                td.language_code,
                td.translated_text
            FROM pulsar.translation_dictionary td
            WHERE td.item_code = :translation_key
              AND lower(td.language_code) IN :language_codes
            ORDER BY array_position(
                CAST(:language_codes AS varchar[]),
                lower(td.language_code)
            )
            LIMIT 1
            """.replace(
                "IN :language_codes",
                "= ANY(CAST(:language_codes AS varchar[]))",
            ),
            {
                "translation_key": translation_key,
                "language_codes": language_preferences,
            },
        )

        if not translation or not translation["translated_text"]:
            raise AIAvatarServiceError(
                "No translation is available for the AI Avatar introduction.",
                409,
            )

        definition_id = str(definition["c_ai_definition_id"])

        try:
            await self.session.execute(
                text(
                    """
                    INSERT INTO pulsar.t_ai_avatar_assignment (
                        c_assignment_id,
                        c_user_id,
                        c_ai_definition_id,
                        c_avatar_manager_id,
                        c_state
                    )
                    VALUES (
                        gen_random_uuid(),
                        CAST(:user_id AS uuid),
                        CAST(:definition_id AS uuid),
                        :avatar_manager_id,
                        'active'
                    )
                    ON CONFLICT (c_user_id, c_ai_definition_id)
                    DO NOTHING
                    """
                ),
                {
                    "user_id": user_id,
                    "definition_id": definition_id,
                    "avatar_manager_id": definition["c_avatar_manager_id"],
                },
            )

            claimed = await self._fetch_one(
                """
                UPDATE pulsar.t_ai_avatar_assignment
                SET c_introduction_shown_at = CURRENT_TIMESTAMP,
                    c_updated_at = CURRENT_TIMESTAMP
                WHERE c_user_id = CAST(:user_id AS uuid)
                  AND c_ai_definition_id = CAST(:definition_id AS uuid)
                  AND c_introduction_shown_at IS NULL
                RETURNING c_introduction_shown_at
                """,
                {
                    "user_id": user_id,
                    "definition_id": definition_id,
                },
            )

            if not claimed:
                await self.session.rollback()

                return {
                    "definition_code": definition["c_definition_code"],
                    "show_introduction": False,
                    "message": None,
                }

            await self.session.commit()

        except Exception:
            await self.session.rollback()
            raise

        return {
            "definition_code": definition["c_definition_code"],
            "show_introduction": True,
            "message": translation["translated_text"],
        }

    async def resolve(self, definition_code: str) -> dict[str, Any]:
        definition = await self._fetch_one(
            """
            SELECT
                d.c_ai_definition_id,
                d.c_definition_code,
                d.c_title,
                d.c_description,
                d.c_default_language,
                d.c_avatar_manager_id,
                d.c_enabled,
                d.c_state
            FROM pulsar.t_ai_definition d
            WHERE d.c_definition_code = :definition_code
              AND d.c_enabled = TRUE
              AND upper(d.c_state) = 'ACTIVE'
            """,
            {"definition_code": definition_code},
        )

        if not definition:
            raise AIAvatarServiceError(
                "AI Avatar definition was not found or is inactive.",
                404,
            )

        definition_id = definition["c_ai_definition_id"]

        models = await self._fetch_all(
            """
            SELECT
                a.c_ai_definition_model_id,
                a.c_is_default AS association_is_default,
                a.c_priority AS association_priority,
                m.c_ai_model_id,
                m.c_model_code,
                m.c_model_name,
                m.c_title AS model_title,
                m.c_input_enabled,
                m.c_output_enabled,
                m.c_tool_calling_enabled,
                m.c_context_window,
                m.c_parameters AS model_parameters,
                p.c_ai_provider_id,
                p.c_provider_code,
                p.c_title AS provider_title,
                p.c_api_base_url,
                p.c_api_key_ref
            FROM pulsar.t_ai_definition_model a
            JOIN pulsar.t_ai_model m
              ON m.c_ai_model_id = a.c_ai_model_id
            JOIN pulsar.t_ai_provider p
              ON p.c_ai_provider_id = m.c_ai_provider_id
            WHERE a.c_ai_definition_id = :definition_id
              AND upper(a.c_state) = 'ACTIVE'
              AND upper(m.c_state) = 'ACTIVE'
              AND upper(p.c_state) = 'ACTIVE'
            ORDER BY a.c_priority, m.c_model_code
            """,
            {"definition_id": definition_id},
        )

        default_models = [
            row for row in models if row["association_is_default"]
        ]

        if len(default_models) != 1:
            raise AIAvatarServiceError(
                "Exactly one active default model is required.",
                409,
            )

        model = default_models[0]

        if not model["c_input_enabled"] or not model["c_output_enabled"]:
            raise AIAvatarServiceError(
                "The default model does not support input and output.",
                409,
            )

        operations = await self._fetch_all(
            """
            SELECT
                a.c_is_default AS association_is_default,
                a.c_priority AS association_priority,
                o.c_ai_operation_id,
                o.c_operation_code,
                o.c_title AS operation_title,
                o.c_ai_model_id,
                o.c_system_prompt,
                o.c_user_prompt_template,
                o.c_output_schema,
                o.c_parameters AS operation_parameters
            FROM pulsar.t_ai_definition_operation a
            JOIN pulsar.t_ai_operation o
              ON o.c_ai_operation_id = a.c_ai_operation_id
            WHERE a.c_ai_definition_id = :definition_id
              AND upper(a.c_state) = 'ACTIVE'
              AND upper(o.c_state) = 'ACTIVE'
              AND o.c_ai_model_id = :model_id
            ORDER BY a.c_priority, o.c_operation_code
            """,
            {
                "definition_id": definition_id,
                "model_id": model["c_ai_model_id"],
            },
        )

        default_operations = [
            row for row in operations if row["association_is_default"]
        ]

        if len(default_operations) != 1:
            raise AIAvatarServiceError(
                "Exactly one active default operation for the default model is required.",
                409,
            )

        operation = default_operations[0]

        contexts = await self._fetch_all(
            """
            SELECT
                a.c_required,
                a.c_priority,
                c.c_ai_context_id,
                c.c_context_code,
                c.c_title,
                c.c_context_type,
                c.c_definition
            FROM pulsar.t_ai_definition_context a
            JOIN pulsar.t_ai_context c
              ON c.c_ai_context_id = a.c_ai_context_id
            WHERE a.c_ai_definition_id = :definition_id
              AND upper(a.c_state) = 'ACTIVE'
              AND upper(c.c_state) = 'ACTIVE'
            ORDER BY a.c_priority, c.c_context_code
            """,
            {"definition_id": definition_id},
        )

        policies = await self._fetch_all(
            """
            SELECT
                a.c_required,
                a.c_priority,
                p.c_ai_policy_id,
                p.c_policy_code,
                p.c_policy_type,
                p.c_definition
            FROM pulsar.t_ai_definition_policy a
            JOIN pulsar.t_ai_policy p
              ON p.c_ai_policy_id = a.c_ai_policy_id
            WHERE a.c_ai_definition_id = :definition_id
              AND upper(a.c_state) = 'ACTIVE'
              AND upper(p.c_state) = 'ACTIVE'
            ORDER BY a.c_priority, p.c_policy_code
            """,
            {"definition_id": definition_id},
        )

        presentations = await self._fetch_all(
            """
            SELECT
                a.c_is_default AS association_is_default,
                a.c_priority,
                p.c_ai_presentation_id,
                p.c_presentation_code,
                p.c_presentation_type,
                p.c_definition
            FROM pulsar.t_ai_definition_presentation a
            JOIN pulsar.t_ai_presentation p
              ON p.c_ai_presentation_id = a.c_ai_presentation_id
            WHERE a.c_ai_definition_id = :definition_id
              AND upper(a.c_state) = 'ACTIVE'
              AND upper(p.c_state) = 'ACTIVE'
            ORDER BY a.c_priority, p.c_presentation_code
            """,
            {"definition_id": definition_id},
        )

        for presentation in presentations:
            presentation_definition = presentation.get("c_definition")

            if isinstance(presentation_definition, str):
                try:
                    presentation_definition = json.loads(
                        presentation_definition
                    )
                except (TypeError, ValueError):
                    pass

            visual = (
                presentation_definition.get("visual")
                if isinstance(presentation_definition, dict)
                else None
            )
            
            logger.info(
                "PT-05.3 | Presentation data fetched | "
                "presentation_code=%s | visual.enabled=%r",
                presentation.get("c_presentation_code"),
                visual.get("enabled") if isinstance(visual, dict) else None,
            )


        default_presentations = [
            row for row in presentations if row["association_is_default"]
        ]

        if len(default_presentations) != 1:
            raise AIAvatarServiceError(
                "Exactly one active default presentation is required.",
                409,
            )

        if not policies or not any(row["c_required"] for row in policies):
            raise AIAvatarServiceError(
                "At least one active required policy is required.",
                409,
            )

        policy_definitions = [
            self._as_dict(row["c_definition"]) for row in policies
        ]

        if any(
            policy.get("allow_external_api_calls") is False
            for policy in policy_definitions
        ):
            raise AIAvatarServiceError(
                "An active policy prohibits external API calls.",
                403,
            )

        return {
            "definition": definition,
            "model": model,
            "operation": operation,
            "contexts": contexts,
            "policies": policies,
            "presentation": default_presentations[0],
        }

    # ------------------------------------------------------------------
    # Runtime configuration and authentication
    # ------------------------------------------------------------------

    def _resolve_runtime_config(
        self,
        model: dict[str, Any],
        operation: dict[str, Any],
    ) -> dict[str, Any]:
        model_parameters = self._as_dict(model["model_parameters"])
        operation_parameters = self._as_dict(operation["operation_parameters"])

        transport = str(
            operation_parameters.get(
                "transport",
                model_parameters.get("transport", "HTTP_JSON"),
            )
        ).strip().upper()

        if transport not in self._SUPPORTED_TRANSPORTS:
            raise AIAvatarServiceError(
                "The configured transport is not supported by this runtime.",
                409,
            )

        config = self._merge_dicts(model_parameters, operation_parameters)
        config["transport"] = transport
        config["model_parameters"] = model_parameters
        config["operation_parameters"] = operation_parameters

        return config

    def _resolve_auth(
        self,
        model: dict[str, Any],
        config: dict[str, Any],
    ) -> tuple[dict, dict]:
        model_parameters = config["model_parameters"]
        operation_parameters = config["operation_parameters"]

        headers = self._merge_dicts(
            self._as_dict(model_parameters.get("headers")),
            self._as_dict(operation_parameters.get("headers")),
        )

        query_params = self._merge_dicts(
            self._as_dict(model_parameters.get("query_params")),
            self._as_dict(operation_parameters.get("query_params")),
        )

        auth_config = self._merge_dicts(
            self._as_dict(model_parameters.get("auth")),
            self._as_dict(operation_parameters.get("auth")),
        )

        api_key_ref = model.get("c_api_key_ref")
        api_key = os.environ.get(api_key_ref) if api_key_ref else None

        if api_key_ref and not api_key:
            raise AIAvatarServiceError(
                "The provider credential is not configured in the runtime environment.",
                503,
            )

        auth_type = str(auth_config.get("type", "none")).lower()

        if auth_type == "bearer":
            if not api_key:
                raise AIAvatarServiceError(
                    "Bearer authentication requires a configured provider credential.",
                    503,
                )

            header_name = auth_config.get("header_name", "Authorization")
            prefix = auth_config.get("prefix", "Bearer")
            headers[header_name] = f"{prefix} {api_key}".strip()

        elif auth_type == "header":
            if not api_key:
                raise AIAvatarServiceError(
                    "Header authentication requires a configured provider credential.",
                    503,
                )

            header_name = auth_config.get("header_name")

            if not header_name:
                raise AIAvatarServiceError(
                    "Authentication header_name is required.",
                    409,
                )

            headers[header_name] = api_key

        elif auth_type == "query":
            if not api_key:
                raise AIAvatarServiceError(
                    "Query authentication requires a configured provider credential.",
                    503,
                )

            parameter_name = auth_config.get("parameter_name")

            if not parameter_name:
                raise AIAvatarServiceError(
                    "Authentication parameter_name is required.",
                    409,
                )

            query_params[parameter_name] = api_key

        elif auth_type != "none":
            raise AIAvatarServiceError(
                "The configured authentication type is not supported.",
                409,
            )

        return headers, query_params

    # ------------------------------------------------------------------
    # Encrypted conversation persistence
    # ------------------------------------------------------------------

    @classmethod
    def _get_encryption_key(cls) -> bytes:
        encoded_key = os.environ.get(cls.ENCRYPTION_KEY_ENV)

        if not encoded_key:
            raise AIAvatarServiceError(
                "AI Avatar encryption is not configured.",
                503,
            )

        try:
            key = base64.b64decode(encoded_key, validate=True)
        except (ValueError, TypeError):
            raise AIAvatarServiceError(
                "AI Avatar encryption configuration is invalid.",
                503,
            )

        if len(key) != 32:
            raise AIAvatarServiceError(
                "AI Avatar encryption requires a 256-bit key.",
                503,
            )

        return key

    @classmethod
    def _encrypt_content(
        cls,
        content: str,
        user_id: str,
        definition_id: str,
        conversation_id: str,
        role: str,
    ) -> dict[str, bytes | str]:
        key_ref = os.environ.get(
            cls.ENCRYPTION_KEY_REF_ENV,
            cls.ENCRYPTION_KEY_ENV,
        )
        key_version = os.environ.get(
            cls.ENCRYPTION_KEY_VERSION_ENV,
            "1",
        )

        if not key_ref.strip() or not key_version.strip():
            raise AIAvatarServiceError(
                "AI Avatar encryption key metadata is invalid.",
                503,
            )

        nonce = os.urandom(12)
        associated_data = "|".join(
            (user_id, definition_id, conversation_id, role)
        ).encode("utf-8")

        encrypted = AESGCM(cls._get_encryption_key()).encrypt(
            nonce,
            content.encode("utf-8"),
            associated_data,
        )

        return {
            "ciphertext": encrypted[:-16],
            "nonce": nonce,
            "tag": encrypted[-16:],
            "key_ref": key_ref,
            "key_version": key_version,
        }

    @classmethod
    def _decrypt_content(cls, row: dict[str, Any]) -> str:
        key_ref = row["c_encryption_key_ref"]
        key_version = row["c_encryption_key_version"]

        configured_ref = os.environ.get(
            cls.ENCRYPTION_KEY_REF_ENV,
            cls.ENCRYPTION_KEY_ENV,
        )
        configured_version = os.environ.get(
            cls.ENCRYPTION_KEY_VERSION_ENV,
            "1",
        )

        if key_ref != configured_ref or key_version != configured_version:
            raise AIAvatarServiceError(
                "The encryption key required for this conversation is unavailable.",
                503,
            )

        associated_data = "|".join(
            (
                str(row["c_user_id"]),
                str(row["c_ai_definition_id"]),
                str(row["c_conversation_id"]),
                str(row["c_role"]),
            )
        ).encode("utf-8")

        try:
            ciphertext = (
                bytes(row["c_content_ciphertext"])
                + bytes(row["c_encryption_tag"])
            )

            plaintext = AESGCM(cls._get_encryption_key()).decrypt(
                bytes(row["c_encryption_nonce"]),
                ciphertext,
                associated_data,
            )

            return plaintext.decode("utf-8")

        except AIAvatarServiceError:
            raise
        except (InvalidTag, ValueError, UnicodeDecodeError) as exc:
            raise AIAvatarServiceError(
                "Stored AI Avatar content could not be authenticated or decrypted.",
                500,
            ) from exc

    async def _get_memory_policy(
        self,
        definition_id: str,
    ) -> dict[str, Any]:
        """Load and validate the active Avatar memory policy."""

        policy = await self._fetch_one(
            """
            SELECT
                c_history_retention_days,
                c_memory_retention_days,
                c_max_history_messages,
                c_max_memory_items,
                c_max_memory_bytes
            FROM pulsar.t_ai_avatar_memory_policy
            WHERE c_ai_definition_id = CAST(:definition_id AS uuid)
              AND upper(c_state) = 'ACTIVE'
            ORDER BY c_updated_at DESC, c_policy_id
            LIMIT 1
            """,
            {"definition_id": definition_id},
        )

        if not policy:
            raise AIAvatarServiceError(
                "An active AI Avatar memory policy is required.",
                409,
            )

        limits = {
            "c_history_retention_days": (1, 36500),
            "c_memory_retention_days": (1, 36500),
            "c_max_history_messages": (1, 100000),
            "c_max_memory_items": (1, 100000),
            "c_max_memory_bytes": (1, 1073741824),
        }

        for field_name, (minimum, maximum) in limits.items():
            value = policy[field_name]

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not minimum <= value <= maximum
            ):
                raise AIAvatarServiceError(
                    "The active AI Avatar memory policy contains an invalid limit.",
                    409,
                )

        return policy
    
    async def _get_or_create_conversation(
        self,
        user_id: str,
        definition_id: str,
        avatar_manager_id: int,
        history_retention_days: int,
        conversation_id: str | None = None,
        force_new: bool = False,
    ) -> str:
        await self.session.execute(
            text(
                """
                INSERT INTO pulsar.t_ai_avatar_assignment (
                    c_assignment_id,
                    c_user_id,
                    c_ai_definition_id,
                    c_avatar_manager_id,
                    c_state
                )
                VALUES (
                    gen_random_uuid(),
                    CAST(:user_id AS uuid),
                    CAST(:definition_id AS uuid),
                    :avatar_manager_id,
                    'active'
                )
                ON CONFLICT (c_user_id, c_ai_definition_id)
                DO UPDATE SET c_updated_at = CURRENT_TIMESTAMP
                """
            ),
            {
                "user_id": user_id,
                "definition_id": definition_id,
                "avatar_manager_id": avatar_manager_id,
            },
        )

        if conversation_id is not None:
            conversation = await self._fetch_one(
                """
                SELECT c_conversation_id
                FROM pulsar.t_ai_avatar_conversation
                WHERE c_conversation_id = CAST(:conversation_id AS uuid)
                  AND c_user_id = CAST(:user_id AS uuid)
                  AND c_ai_definition_id = CAST(:definition_id AS uuid)
                  AND upper(c_state) = 'ACTIVE'
                  AND c_expires_at > CURRENT_TIMESTAMP
                LIMIT 1
                """,
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "definition_id": definition_id,
                },
            )

            if not conversation:
                raise AIAvatarServiceError(
                    "The requested AI Avatar conversation is unavailable.",
                    404,
                )

            return str(conversation["c_conversation_id"])

        conversation = None

        if not force_new:
            conversation = await self._fetch_one(
                """
                SELECT c_conversation_id
                FROM pulsar.t_ai_avatar_conversation
            WHERE c_user_id = CAST(:user_id AS uuid)
              AND c_ai_definition_id = CAST(:definition_id AS uuid)
              AND upper(c_state) = 'ACTIVE'
              AND c_expires_at > CURRENT_TIMESTAMP
            ORDER BY c_last_message_at DESC
            LIMIT 1
            """,
                {
                    "user_id": user_id,
                    "definition_id": definition_id,
                },
            )

        if conversation:
            return str(conversation["c_conversation_id"])

        conversation_id = str(uuid.uuid4())

        await self.session.execute(
            text(
                """
                INSERT INTO pulsar.t_ai_avatar_conversation (
                    c_conversation_id,
                    c_user_id,
                    c_ai_definition_id,
                    c_state,
                    c_expires_at
                )
                VALUES (
                    CAST(:conversation_id AS uuid),
                    CAST(:user_id AS uuid),
                    CAST(:definition_id AS uuid),
                    'active',
                    CURRENT_TIMESTAMP + make_interval(days => :retention_days)
                )
                """
            ),
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "definition_id": definition_id,
                "retention_days": history_retention_days,
            },
        )

        return conversation_id

    async def _load_conversation_history(
        self,
        user_id: str,
        definition_id: str,
        conversation_id: str,
        max_messages: int,
    ) -> list[dict[str, str]]:
        rows = await self._fetch_all(
            """
            SELECT *
            FROM (
                SELECT
                    m.c_message_id,
                    m.c_conversation_id,
                    m.c_user_id,
                    m.c_ai_definition_id,
                    m.c_role,
                    m.c_content_ciphertext,
                    m.c_encryption_nonce,
                    m.c_encryption_tag,
                    m.c_encryption_key_ref,
                    m.c_encryption_key_version,
                    m.c_created_at
                FROM pulsar.t_ai_avatar_message m
                JOIN pulsar.t_ai_avatar_conversation c
                  ON c.c_conversation_id = m.c_conversation_id
                WHERE m.c_user_id = CAST(:user_id AS uuid)
                  AND m.c_ai_definition_id = CAST(:definition_id AS uuid)
                  AND m.c_conversation_id = CAST(:conversation_id AS uuid)
                  AND c.c_user_id = m.c_user_id
                  AND c.c_ai_definition_id = m.c_ai_definition_id
                  AND upper(c.c_state) = 'ACTIVE'
                ORDER BY m.c_created_at DESC, m.c_message_id DESC
                LIMIT :max_messages
            ) history
            ORDER BY c_created_at, c_message_id
            """,
            {
                "user_id": user_id,
                "definition_id": definition_id,
                "conversation_id": conversation_id,
                "max_messages": max_messages,
            },
        )

        return [
            {
                "role": row["c_role"],
                "content": self._decrypt_content(row),
            }
            for row in rows
        ]

    async def _save_message(
        self,
        user_id: str,
        definition_id: str,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:
        if role not in {"user", "assistant"}:
            raise AIAvatarServiceError(
                "Unsupported conversation message role.",
                500,
            )

        encrypted = self._encrypt_content(
            content=content,
            user_id=user_id,
            definition_id=definition_id,
            conversation_id=conversation_id,
            role=role,
        )
        
        await self.session.execute(
            text(
                """
                INSERT INTO pulsar.t_ai_avatar_message (
                    c_message_id,
                    c_conversation_id,
                    c_user_id,
                    c_ai_definition_id,
                    c_role,
                    c_content_ciphertext,
                    c_encryption_nonce,
                    c_encryption_tag,
                    c_encryption_key_ref,
                    c_encryption_key_version
                )
                VALUES (
                    gen_random_uuid(),
                    CAST(:conversation_id AS uuid),
                    CAST(:user_id AS uuid),
                    CAST(:definition_id AS uuid),
                    :role,
                    :ciphertext,
                    :nonce,
                    :tag,
                    :key_ref,
                    :key_version
                )
                """
            ),
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "definition_id": definition_id,
                "role": role,
                "ciphertext": encrypted["ciphertext"],
                "nonce": encrypted["nonce"],
                "tag": encrypted["tag"],
                "key_ref": encrypted["key_ref"],
                "key_version": encrypted["key_version"],
            },
        )

        await self.session.execute(
            text(
                """
                UPDATE pulsar.t_ai_avatar_conversation
                SET c_last_message_at = CURRENT_TIMESTAMP,
                    c_updated_at = CURRENT_TIMESTAMP
                WHERE c_conversation_id = CAST(:conversation_id AS uuid)
                  AND c_user_id = CAST(:user_id AS uuid)
                  AND c_ai_definition_id = CAST(:definition_id AS uuid)
                """
            ),
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "definition_id": definition_id,
            },
        )


    # ------------------------------------------------------------------
    # Persistent memory and retention
    # ------------------------------------------------------------------

    async def _cleanup_expired_records(
        self,
        user_id: str,
        definition_id: str,
    ) -> None:
        """Delete expired private memory and conversation records."""

        parameters = {
            "user_id": user_id,
            "definition_id": definition_id,
        }

        await self.session.execute(
            text("""
                DELETE FROM pulsar.t_ai_avatar_memory
                WHERE c_user_id = CAST(:user_id AS uuid)
                  AND c_ai_definition_id = CAST(:definition_id AS uuid)
                  AND c_expires_at <= CURRENT_TIMESTAMP
            """),
            parameters,
        )

        await self.session.execute(
            text("""
                DELETE FROM pulsar.t_ai_avatar_message AS m
                USING pulsar.t_ai_avatar_conversation AS c
                WHERE m.c_conversation_id = c.c_conversation_id
                  AND m.c_user_id = CAST(:user_id AS uuid)
                  AND m.c_ai_definition_id = CAST(:definition_id AS uuid)
                  AND c.c_user_id = m.c_user_id
                  AND c.c_ai_definition_id = m.c_ai_definition_id
                  AND (
                      c.c_expires_at <= CURRENT_TIMESTAMP
                      OR upper(c.c_state) <> 'ACTIVE'
                  )
            """),
            parameters,
        )

        await self.session.execute(
            text("""
                DELETE FROM pulsar.t_ai_avatar_conversation
                WHERE c_user_id = CAST(:user_id AS uuid)
                  AND c_ai_definition_id = CAST(:definition_id AS uuid)
                  AND (
                      c_expires_at <= CURRENT_TIMESTAMP
                      OR upper(c_state) <> 'ACTIVE'
                  )
            """),
            parameters,
        )

    async def _load_long_term_memories(
        self,
        user_id: str,
        definition_id: str,
        max_items: int,
    ) -> list[dict[str, str]]:
        """Load only unexpired memories owned by this user and Avatar."""

        rows = await self._fetch_all(
            """
            SELECT
                c_memory_id,
                c_memory_type,
                c_content_ciphertext,
                c_encryption_nonce,
                c_encryption_tag,
                c_encryption_key_ref,
                c_encryption_key_version
            FROM pulsar.t_ai_avatar_memory
            WHERE c_user_id = CAST(:user_id AS uuid)
              AND c_ai_definition_id = CAST(:definition_id AS uuid)
              AND c_expires_at > CURRENT_TIMESTAMP
            ORDER BY c_updated_at DESC, c_memory_id DESC
            LIMIT :max_items
            """,
            {
                "user_id": user_id,
                "definition_id": definition_id,
                "max_items": max_items,
            },
        )

        memories = []

        for row in rows:
            # Memory records use a distinct authenticated-encryption context.
            key_ref = row["c_encryption_key_ref"]
            key_version = row["c_encryption_key_version"]

            configured_ref = os.environ.get(
                self.ENCRYPTION_KEY_REF_ENV,
                self.ENCRYPTION_KEY_ENV,
            )
            configured_version = os.environ.get(
                self.ENCRYPTION_KEY_VERSION_ENV,
                "1",
            )

            if (
                key_ref != configured_ref
                or key_version != configured_version
            ):
                raise AIAvatarServiceError(
                    "The encryption key required for stored Avatar memory is unavailable.",
                    503,
                )

            memory_id = str(row["c_memory_id"])
            memory_type = str(row["c_memory_type"])

            associated_data = "|".join(
                (
                    "pulsar-ai-avatar-memory-v1",
                    user_id,
                    definition_id,
                    memory_id,
                    memory_type,
                )
            ).encode("utf-8")

            try:
                ciphertext = (
                    bytes(row["c_content_ciphertext"])
                    + bytes(row["c_encryption_tag"])
                )

                plaintext = AESGCM(self._get_encryption_key()).decrypt(
                    bytes(row["c_encryption_nonce"]),
                    ciphertext,
                    associated_data,
                ).decode("utf-8")

            except (InvalidTag, ValueError, UnicodeDecodeError) as exc:
                raise AIAvatarServiceError(
                    "Stored AI Avatar memory could not be authenticated or decrypted.",
                    500,
                ) from exc

            memories.append({
                "memory_type": memory_type,
                "content": plaintext,
            })

        return memories

    async def _save_long_term_memory(
        self,
        user_id: str,
        definition_id: str,
        source_message_id: str,
        memory_type: str,
        content: str,
        retention_days: int,
        max_items: int,
        max_bytes: int,
    ) -> str:
        """Encrypt and save one memory item with owner-bound authenticated data."""

        if not content or not content.strip():
            raise AIAvatarServiceError(
                "Memory content must not be empty.",
                400,
            )

        if len(content.encode("utf-8")) > max_bytes:
            raise AIAvatarServiceError(
                "Memory content exceeds the configured size limit.",
                413,
            )

        if not memory_type or len(memory_type) > 100:
            raise AIAvatarServiceError(
                "Memory type is invalid.",
                400,
            )

        source = await self._fetch_one(
            """
            SELECT c_message_id
            FROM pulsar.t_ai_avatar_message
            WHERE c_message_id = CAST(:source_message_id AS uuid)
              AND c_user_id = CAST(:user_id AS uuid)
              AND c_ai_definition_id = CAST(:definition_id AS uuid)
            """,
            {
                "source_message_id": source_message_id,
                "user_id": user_id,
                "definition_id": definition_id,
            },
        )

        if not source:
            raise AIAvatarServiceError(
                "The source message is not available to this user and Avatar.",
                403,
            )

        memory_id = str(uuid.uuid4())
        key_ref = os.environ.get(
            self.ENCRYPTION_KEY_REF_ENV,
            self.ENCRYPTION_KEY_ENV,
        )
        key_version = os.environ.get(
            self.ENCRYPTION_KEY_VERSION_ENV,
            "1",
        )

        associated_data = "|".join(
            (
                "pulsar-ai-avatar-memory-v1",
                user_id,
                definition_id,
                memory_id,
                memory_type,
            )
        ).encode("utf-8")

        nonce = os.urandom(12)
        encrypted = AESGCM(self._get_encryption_key()).encrypt(
            nonce,
            content.encode("utf-8"),
            associated_data,
        )

        await self.session.execute(
            text("""
                INSERT INTO pulsar.t_ai_avatar_memory (
                    c_memory_id,
                    c_user_id,
                    c_ai_definition_id,
                    c_source_message_id,
                    c_memory_type,
                    c_content_ciphertext,
                    c_encryption_nonce,
                    c_encryption_tag,
                    c_encryption_key_ref,
                    c_encryption_key_version,
                    c_expires_at
                )
                VALUES (
                    CAST(:memory_id AS uuid),
                    CAST(:user_id AS uuid),
                    CAST(:definition_id AS uuid),
                    CAST(:source_message_id AS uuid),
                    :memory_type,
                    :ciphertext,
                    :nonce,
                    :tag,
                    :key_ref,
                    :key_version,
                    CURRENT_TIMESTAMP + make_interval(days => :retention_days)
                )
            """),
            {
                "memory_id": memory_id,
                "user_id": user_id,
                "definition_id": definition_id,
                "source_message_id": source_message_id,
                "memory_type": memory_type,
                "ciphertext": encrypted[:-16],
                "nonce": nonce,
                "tag": encrypted[-16:],
                "key_ref": key_ref,
                "key_version": key_version,
                "retention_days": retention_days,
            },
        )

        await self.session.execute(
            text("""
                DELETE FROM pulsar.t_ai_avatar_memory
                WHERE c_user_id = CAST(:user_id AS uuid)
                  AND c_ai_definition_id = CAST(:definition_id AS uuid)
                  AND c_memory_id IN (
                      SELECT c_memory_id
                      FROM pulsar.t_ai_avatar_memory
                      WHERE c_user_id = CAST(:user_id AS uuid)
                        AND c_ai_definition_id = CAST(:definition_id AS uuid)
                      ORDER BY c_updated_at DESC, c_memory_id DESC
                      OFFSET :max_items
                  )
            """),
            {
                "user_id": user_id,
                "definition_id": definition_id,
                "max_items": max_items,
            },
        )

        return memory_id

    # ------------------------------------------------------------------
    # HTTP JSON transport
    # ------------------------------------------------------------------

    async def _execute_http_json(
        self,
        endpoint_url: str,
        config: dict[str, Any],
        headers: dict,
        query_params: dict,
        request_values: dict[str, Any],
    ) -> Any:
        method = str(config.get("http_method", "")).upper()

        if method not in self._HTTP_METHODS:
            raise AIAvatarServiceError(
                "A supported HTTP method must be configured in metadata.",
                409,
            )

        request_template = config.get("request_template")
        response_path = config.get("response_path")

        if not isinstance(request_template, (dict, list)):
            raise AIAvatarServiceError(
                "A JSON request_template must be configured in metadata.",
                409,
            )

        if not isinstance(response_path, str) or not response_path:
            raise AIAvatarServiceError(
                "A response_path must be configured in metadata.",
                409,
            )

        request_body = self._render_value(request_template, request_values)

        # Temporary Pali request diagnostics.
        # Do not log the full runtime context or conversation content.
# LOG---
        messages = (
            request_body.get("messages", [])
            if isinstance(request_body, dict)
            else []
        )

        valid_messages = [
            message for message in messages
            if isinstance(message, dict)
        ]

        contents = [
            str(message.get("content", ""))
            for message in valid_messages
        ]

        logger.warning(
            "PALI_REQUEST_DIAGNOSTIC | model=%r | roles=%s | "
            "content_lengths=%s | unresolved_template=%s | "
            "history_section=%s | runtime_context_section=%s",
            request_body.get("model")
            if isinstance(request_body, dict)
            else None,
            [message.get("role") for message in valid_messages],
            [len(content) for content in contents],
            any(
                re.search(r"\{\{[^{}]+\}\}", content)
                for content in contents
            ),
            any("RECENT CONVERSATION HISTORY" in content for content in contents),
            any("CURRENT PULSAR RUNTIME CONTEXT" in content for content in contents),
        ) 

        # Temporary diagnostics: inspect prompt sections without logging content.

        messages = request_body.get("messages", [])

        user_content = next(
            (
                str(message.get("content", ""))
                for message in messages
                if isinstance(message, dict)
                and message.get("role") == "user"
            ),
            "",
        )


        def section_length(
            start_marker: str,
            end_marker: str | None = None,
        ) -> int | None:
            start = user_content.find(start_marker)

            if start < 0:
                return None

            start += len(start_marker)

            if end_marker is None:
                end = len(user_content)
            else:
                end = user_content.find(end_marker, start)

                if end < 0:
                    end = len(user_content)

            return len(user_content[start:end].strip())


        section_lengths = {
            "latest_user_message": section_length(
                "LATEST USER MESSAGE",
                "CONFIGURED DEFAULT LANGUAGE",
            ),
            "default_language": section_length(
                "CONFIGURED DEFAULT LANGUAGE",
                "PULSAR CONTEXT DEFINITIONS",
            ),
            "context_definitions": section_length(
                "PULSAR CONTEXT DEFINITIONS",
                "CURRENT PULSAR RUNTIME CONTEXT",
            ),
            "runtime_context": section_length(
                "CURRENT PULSAR RUNTIME CONTEXT",
                "RECENT CONVERSATION HISTORY",
            ),
            "conversation_history": section_length(
                "RECENT CONVERSATION HISTORY",
                "RELEVANT LONG-TERM MEMORY",
            ),
            "long_term_memory": section_length(
                "RELEVANT LONG-TERM MEMORY",
                "RESPONSE REQUIREMENTS",
            ),
            "response_requirements": section_length(
                "RESPONSE REQUIREMENTS",
            ),
        }

        logger.warning(
            "PALI_PROMPT_SECTIONS | model=%r | think=%r | stream=%r | "
            "user_content_length=%d | sections=%s",
            request_body.get("model"),
            request_body.get("think"),
            request_body.get("stream"),
            len(user_content),
            section_lengths,
        )

# LOG---      
        timeout = self._as_positive_timeout(config.get("timeout_seconds", 60))

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=False,
            ) as client:
                response = await client.request(
                    method=method,
                    url=endpoint_url,
                    headers=headers,
                    params=query_params,
                    json=request_body,
                )

                response.raise_for_status()

                try:
                    response_data = response.json()
                except ValueError:
                    raise AIAvatarServiceError(
                        "The configured API returned a non-JSON response.",
                        502,
                    )

        except AIAvatarServiceError:
            raise
        except httpx.TimeoutException:
            raise AIAvatarServiceError(
                "The AI provider request timed out.",
                504,
            )
        except httpx.HTTPStatusError as exc:
            raise AIAvatarServiceError(
                f"The AI provider returned HTTP {exc.response.status_code}.",
                502,
            )
        except httpx.RequestError:
            raise AIAvatarServiceError(
                "The AI provider could not be reached.",
                502,
            )

        return self._get_path(response_data, response_path)

    # ------------------------------------------------------------------
    # WebSocket JSON transport
    # ------------------------------------------------------------------

    @classmethod
    def _extract_response_fragments(
        cls,
        value: Any,
        item_path: str | None,
    ) -> list[str]:
        if isinstance(value, list):
            fragments = []

            for item in value:
                if item_path:
                    found, item_value = cls._try_get_path(item, item_path)

                    if not found:
                        continue
                else:
                    item_value = item

                if isinstance(item_value, str) and item_value:
                    fragments.append(item_value)

            return fragments

        if isinstance(value, str) and value:
            return [value]

        if isinstance(value, dict) and item_path:
            found, item_value = cls._try_get_path(value, item_path)

            if found and isinstance(item_value, str) and item_value:
                return [item_value]

        return []

    async def _execute_websocket_json(
        self,
        endpoint_url: str,
        config: dict[str, Any],
        headers: dict,
        query_params: dict,
        request_values: dict[str, Any],
    ) -> Any:
        try:
            from websockets.exceptions import (
                ConnectionClosed,
                WebSocketException,
            )
            from websockets.legacy.client import connect
        except ImportError as exc:
            raise AIAvatarServiceError(
                "WebSocket transport requires the websockets package.",
                503,
            ) from exc

        request_template = config.get("request_template")
        response_path = config.get("response_path")

        if not isinstance(request_template, (dict, list)):
            raise AIAvatarServiceError(
                "A JSON request_template must be configured in metadata.",
                409,
            )

        if not isinstance(response_path, str) or not response_path:
            raise AIAvatarServiceError(
                "A response_path must be configured in metadata.",
                409,
            )

        response_mode = str(config.get("response_mode", "first")).strip().lower()

        if response_mode not in {"first", "collect"}:
            raise AIAvatarServiceError(
                "response_mode must be first or collect.",
                409,
            )

        response_item_path = config.get("response_item_path")

        if response_item_path is not None and not isinstance(response_item_path, str):
            raise AIAvatarServiceError(
                "response_item_path must be a string when configured.",
                409,
            )

        completion_path = config.get("completion_path")
        completion_value = config.get("completion_value")

        if response_mode == "collect":
            if not isinstance(completion_path, str) or not completion_path:
                raise AIAvatarServiceError(
                    "completion_path is required when response_mode is collect.",
                    409,
                )

            if "completion_value" not in config:
                raise AIAvatarServiceError(
                    "completion_value is required when response_mode is collect.",
                    409,
                )

        timeout = self._as_positive_timeout(config.get("timeout_seconds", 60))

        try:
            max_messages = int(config.get("max_receive_messages", 50))

            if not 1 <= max_messages <= 500:
                raise ValueError
        except (TypeError, ValueError):
            raise AIAvatarServiceError(
                "max_receive_messages must be between 1 and 500.",
                409,
            )

        query_string = urlencode(query_params, doseq=True)

        if query_string:
            separator = "&" if urlparse(endpoint_url).query else "?"
            endpoint_url = f"{endpoint_url}{separator}{query_string}"

        initial_messages = self._as_list(config.get("initial_messages"))
        receive_until = self._as_dict(config.get("receive_until"))

        try:
            async with connect(
                endpoint_url,
                extra_headers=headers,
                open_timeout=timeout,
                close_timeout=5,
                max_size=2 * 1024 * 1024,
            ) as websocket:
                for initial_message in initial_messages:
                    rendered = self._render_value(
                        initial_message,
                        request_values,
                    )

                    await websocket.send(
                        json.dumps(rendered, ensure_ascii=False)
                    )

                    if receive_until:
                        expected_path = receive_until.get("path")

                        if not isinstance(expected_path, str) or not expected_path:
                            raise AIAvatarServiceError(
                                "receive_until.path must be configured in metadata.",
                                409,
                            )

                        has_expected_value = "equals" in receive_until
                        expected_value = receive_until.get("equals")
                        matched = False

                        for _ in range(max_messages):
                            raw_message = await asyncio.wait_for(
                                websocket.recv(),
                                timeout=timeout,
                            )

                            try:
                                received = json.loads(raw_message)
                            except (TypeError, ValueError):
                                continue

                            found, actual = self._try_get_path(
                                received,
                                expected_path,
                            )

                            if found and (
                                not has_expected_value
                                or actual == expected_value
                            ):
                                matched = True
                                break

                        if not matched:
                            raise AIAvatarServiceError(
                                "The WebSocket setup acknowledgement was not received.",
                                502,
                            )

                request_body = self._render_value(
                    request_template,
                    request_values,
                )

                await websocket.send(
                    json.dumps(request_body, ensure_ascii=False)
                )

                collected_fragments = []

                for _ in range(max_messages):
                    raw_message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=timeout,
                    )

                    try:
                        received = json.loads(raw_message)
                    except (TypeError, ValueError):
                        continue

                    found, value = self._try_get_path(
                        received,
                        response_path,
                    )

                    if response_mode == "first":
                        if found:
                            return value
                        continue

                    if found:
                        collected_fragments.extend(
                            self._extract_response_fragments(
                                value,
                                response_item_path,
                            )
                        )

                    completion_found, actual_completion = self._try_get_path(
                        received,
                        completion_path,
                    )

                    if completion_found and actual_completion == completion_value:
                        if collected_fragments:
                            return "".join(collected_fragments)

                        raise AIAvatarServiceError(
                            "The WebSocket response completed without a configured text response.",
                            502,
                        )

            raise AIAvatarServiceError(
                "The WebSocket connection closed before a configured response was received.",
                502,
            )

        except AIAvatarServiceError:
            raise
        except (asyncio.TimeoutError, TimeoutError):
            raise AIAvatarServiceError(
                "The AI provider WebSocket request timed out.",
                504,
            )
        except ConnectionClosed:
            raise AIAvatarServiceError(
                "The AI provider closed the WebSocket connection unexpectedly.",
                502,
            )
        except WebSocketException:
            raise AIAvatarServiceError(
                "The AI provider WebSocket connection failed.",
                502,
            )
        except OSError:
            raise AIAvatarServiceError(
                "The AI provider WebSocket could not be reached.",
                502,
            )

    # ------------------------------------------------------------------
    # Main chat operation
    # ------------------------------------------------------------------

    async def chat(
        self,
        definition_code: str,
        user_message: str,
        user_id: str,
        context_variables: dict[str, Any] | None = None,
        conversation_id: str | None = None,
        new_conversation: bool = False,
        include_history: bool = True,
    ) -> dict[str, Any]:
        """Execute a metadata-defined Avatar conversation with persisted history."""

        if not isinstance(user_message, str) or not user_message.strip():
            raise AIAvatarServiceError(
                "A non-empty user message is required.",
                400,
            )

        if len(user_message) > 100000:
            raise AIAvatarServiceError(
                "The user message exceeds the maximum allowed size.",
                413,
            )

        user_id = self._normalize_uuid(
            user_id,
            "authenticated user ID",
        )

        if type(new_conversation) is not bool or type(include_history) is not bool:
            raise AIAvatarServiceError(
                "Invalid AI Avatar conversation options.",
                400,
            )

        if conversation_id is not None and new_conversation:
            raise AIAvatarServiceError(
                "A conversation ID cannot be combined with new_conversation.",
                400,
            )

        if conversation_id is not None:
            conversation_id = self._normalize_uuid(
                conversation_id,
                "AI Avatar conversation ID",
            )

        safe_context_variables = self._validate_context_variables(
            context_variables
        )

        resolved = await self.resolve(definition_code)

        definition = resolved["definition"]
        model = resolved["model"]
        operation = resolved["operation"]

        definition_id = str(definition["c_ai_definition_id"])

        memory_policy = await self._get_memory_policy(definition_id)

        await self._cleanup_expired_records(
            user_id=user_id,
            definition_id=definition_id,
        )

        history_retention_days = memory_policy["c_history_retention_days"]
        max_history_messages = memory_policy["c_max_history_messages"]

        if (
            type(history_retention_days) is not int
            or history_retention_days < 1
            or type(max_history_messages) is not int
            or max_history_messages < 1
        ):
            raise AIAvatarServiceError(
                "The active AI Avatar history policy is invalid.",
                409,
            )

        conversation_id = await self._get_or_create_conversation(
            user_id=user_id,
            definition_id=definition_id,
            avatar_manager_id=definition["c_avatar_manager_id"],
            history_retention_days=history_retention_days,
            conversation_id=conversation_id,
            force_new=new_conversation,
        )

        history = (
            await self._load_conversation_history(
                user_id=user_id,
                definition_id=definition_id,
                conversation_id=conversation_id,
                max_messages=max_history_messages,
            )
            if include_history
            else []
        )

        memories = await self._load_long_term_memories(
            user_id=user_id,
            definition_id=definition_id,
            max_items=memory_policy["c_max_memory_items"],
        )

        memory_context = "\n".join(
            f'- {item["memory_type"]}: {item["content"]}'
            for item in memories
        )

        config = self._resolve_runtime_config(model, operation)
        transport = config["transport"]

        base_url = model.get("c_api_base_url")

        if not base_url:
            raise AIAvatarServiceError(
                "A provider base URL must be configured in metadata.",
                409,
            )

        endpoint_url = self._build_endpoint(
            base_url=base_url,
            api_path=config.get("api_path"),
            transport=transport,
        )

        context_definitions = {
            row["c_context_code"]: row["c_definition"]
            for row in resolved["contexts"]
        }

        conversation_history = "\n".join(
            f'{item["role"]}: {item["content"]}'
            for item in history
        )

        prompt_values = {
            "user_message": user_message,
            "system_prompt": operation["c_system_prompt"],
            "model_name": model["c_model_name"],
            "model_code": model["c_model_code"],
            "operation_code": operation["c_operation_code"],
            "definition_code": definition["c_definition_code"],
            "default_language": definition["c_default_language"],
            "operation_parameters": config["operation_parameters"],
            "model_parameters": config["model_parameters"],
            "contexts": context_definitions,
            "context_variables": safe_context_variables,
            "conversation_history": conversation_history,
            "long_term_memory": memory_context,
        }

        user_prompt_template = (
            operation["c_user_prompt_template"] or "{{user_message}}"
        )

        rendered_user_prompt = self._render_string(
            user_prompt_template,
            prompt_values,
        )

        request_values = {
            **prompt_values,
            "user_prompt": rendered_user_prompt,
        }

        headers, query_params = self._resolve_auth(model, config)

        if transport == "HTTP_JSON":
            response_value = await self._execute_http_json(
                endpoint_url=endpoint_url,
                config=config,
                headers=headers,
                query_params=query_params,
                request_values=request_values,
            )
        elif transport == "WEBSOCKET_JSON":
            response_value = await self._execute_websocket_json(
                endpoint_url=endpoint_url,
                config=config,
                headers=headers,
                query_params=query_params,
                request_values=request_values,
            )
        else:
            raise AIAvatarServiceError(
                "The configured transport is not supported by this runtime.",
                409,
            )

        if response_value is None:
            raise AIAvatarServiceError(
                "The AI provider returned an empty response.",
                502,
            )

        response_text = (
            response_value
            if isinstance(response_value, str)
            else json.dumps(response_value, ensure_ascii=False)
        )

        try:
            await self._save_message(
                user_id=user_id,
                definition_id=definition_id,
                conversation_id=conversation_id,
                role="user",
                content=user_message,
            )

            await self._save_message(
                user_id=user_id,
                definition_id=definition_id,
                conversation_id=conversation_id,
                role="assistant",
                content=response_text,
            )

            await self.session.commit()

        except Exception:
            await self.session.rollback()
            raise

        return {
            "definition_code": definition["c_definition_code"],
            "operation_code": operation["c_operation_code"],
            "model_code": model["c_model_code"],
            "presentation_code": resolved["presentation"]["c_presentation_code"],
            "conversation_id": conversation_id,
            "response": response_value,
        }
    