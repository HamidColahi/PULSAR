# ===============================================
# File: Pulsar/backend/ai_avatar/resource_access.py
#
# Description:
# Metadata-authorized retrieval of Function output resources
# for AI Avatar analysis.
#
# Change Date: 2026-11-21 04:00
# Timezone: Asia/Baku
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

from __future__ import annotations

import io
import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from pypdf import PdfReader
except ImportError:  # The runtime reports a controlled dependency error.
    PdfReader = None


logger = logging.getLogger(__name__)


class FunctionOutputResourceError(Exception):
    """Represent a controlled Function output resource access failure."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class FunctionOutputResourceService:
    """Resolve only resources explicitly granted to an output configuration."""

    RESOURCE_MODES = {
        "COLONY_TABLE_1": "READ",
        "COLONY_GUIDANCE_PDF": "READ",
        "COLONY_RULE_SEARCH": "SEARCH",
        "COLONY_RELATED_RULES": "SEARCH",
    }

    SEARCH_FIELDS = {
        "row_no",
        "pbi_sbi",
        "rp",
        "backlog",
        "final_state",
        "start_state",
        "action",
        "inquiry",
        "reaction",
        "event",
    }

    RULE_COLUMNS = """
        row_no,
        pbi_sbi,
        rp,
        backlog,
        final_state,
        start_state,
        action,
        inquiry,
        reaction,
        event
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
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
    def _bounded_int(
        value: Any,
        default: int,
        minimum: int,
        maximum: int,
    ) -> int:
        if type(value) is not int:
            return default
        return max(minimum, min(value, maximum))

    async def _resolve_authorization(
        self,
        output_config_id: int,
        definition_code: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        config_result = await self.session.execute(
            text(
                """
                SELECT
                    output_config_id,
                    c_avatar_manager_id
                FROM pulsar.t_function_output_config
                WHERE output_config_id = :output_config_id
                  AND is_active = TRUE
                LIMIT 1
                """
            ),
            {"output_config_id": output_config_id},
        )
        config = config_result.mappings().first()

        if not config:
            raise FunctionOutputResourceError(
                "The requested Function output configuration is unavailable.",
                404,
            )

        definition_result = await self.session.execute(
            text(
                """
                SELECT
                    c_definition_code,
                    c_avatar_manager_id
                FROM pulsar.t_ai_definition
                WHERE c_definition_code = :definition_code
                  AND c_enabled = TRUE
                  AND upper(c_state) = 'ACTIVE'
                LIMIT 1
                """
            ),
            {"definition_code": definition_code},
        )
        definition = definition_result.mappings().first()

        if not definition:
            raise FunctionOutputResourceError(
                "The requested AI Avatar definition is unavailable.",
                404,
            )

        configured_manager_id = config["c_avatar_manager_id"]
        definition_manager_id = definition["c_avatar_manager_id"]

        if (
            configured_manager_id is None
            or definition_manager_id is None
            or int(configured_manager_id) != int(definition_manager_id)
        ):
            raise FunctionOutputResourceError(
                "The AI Avatar is not authorized for this output configuration.",
                403,
            )

        access_result = await self.session.execute(
            text(
                """
                SELECT
                    resource_code,
                    access_mode,
                    access_options,
                    priority
                FROM pulsar.t_function_output_access
                WHERE output_config_id = :output_config_id
                  AND is_active = TRUE
                ORDER BY priority, resource_code
                """
            ),
            {"output_config_id": output_config_id},
        )

        access_rows = [
            dict(row)
            for row in access_result.mappings().all()
        ]

        for access in access_rows:
            code = str(access["resource_code"] or "").strip().upper()
            mode = str(access["access_mode"] or "").strip().upper()
            expected_mode = self.RESOURCE_MODES.get(code)

            if expected_mode is None:
                raise FunctionOutputResourceError(
                    f"No backend provider is registered for resource '{code}'.",
                    409,
                )

            if mode != expected_mode:
                raise FunctionOutputResourceError(
                    f"Invalid access mode for resource '{code}'.",
                    409,
                )

            access["resource_code"] = code
            access["access_mode"] = mode
            access["access_options"] = self._as_dict(
                access["access_options"]
            )

        return dict(config), access_rows

    async def _load_table_1(
        self,
        options: dict[str, Any],
        row_numbers: list[int],
    ) -> tuple[list[dict[str, Any]], int]:
        limit = self._bounded_int(
            options.get("max_rows"),
            default=50,
            minimum=1,
            maximum=250,
        )

        count_result = await self.session.execute(
            text("SELECT COUNT(*) FROM pulsar.table_1")
        )
        total_count = int(count_result.scalar_one() or 0)

        if not row_numbers:
            return [], total_count

        result = await self.session.execute(
            text(
                f"""
                SELECT {self.RULE_COLUMNS}
                FROM pulsar.table_1
                WHERE row_no = ANY(:row_numbers)
                ORDER BY row_no
                LIMIT :row_limit
                """
            ),
            {
                "row_numbers": row_numbers[:limit],
                "row_limit": limit,
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ], total_count

    async def _search_rules(
        self,
        search_text: str,
        options: dict[str, Any],
    ) -> list[dict[str, Any]]:
        normalized_text = search_text.strip()

        if not normalized_text:
            return []

        configured_fields = options.get("search_fields")
        if not isinstance(configured_fields, list):
            configured_fields = [
                "inquiry",
                "reaction",
                "event",
                "action",
                "rp",
                "pbi_sbi",
            ]

        fields = [
            field for field in configured_fields
            if isinstance(field, str) and field in self.SEARCH_FIELDS
        ]

        if not fields:
            raise FunctionOutputResourceError(
                "The configured Colony search fields are invalid.",
                409,
            )

        limit = self._bounded_int(
            options.get("max_results"),
            default=20,
            minimum=1,
            maximum=100,
        )

        conditions = " OR ".join(
            f"COALESCE({field}::text, '') ILIKE :search_pattern"
            for field in fields
        )

        result = await self.session.execute(
            text(
                f"""
                SELECT {self.RULE_COLUMNS}
                FROM pulsar.table_1
                WHERE {conditions}
                ORDER BY row_no
                LIMIT :result_limit
                """
            ),
            {
                "search_pattern": f"%{normalized_text[:500]}%",
                "result_limit": limit,
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]

    async def _load_guidance_pdfs(
        self,
        row_numbers: list[int],
        options: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not row_numbers:
            return []

        if PdfReader is None:
            raise FunctionOutputResourceError(
                "PDF text extraction is unavailable. Install the configured pypdf dependency.",
                503,
            )

        max_pages = self._bounded_int(
            options.get("max_pages"),
            default=80,
            minimum=1,
            maximum=300,
        )
        max_text_chars = self._bounded_int(
            options.get("max_text_chars"),
            default=30000,
            minimum=1000,
            maximum=100000,
        )

        result = await self.session.execute(
            text(
                """
                SELECT row_no, guidance_pdf
                FROM pulsar.table_1
                WHERE row_no = ANY(:row_numbers)
                  AND guidance_pdf IS NOT NULL
                ORDER BY row_no
                """
            ),
            {"row_numbers": row_numbers[:50]},
        )

        documents: list[dict[str, Any]] = []
        remaining_chars = max_text_chars

        for row in result.mappings().all():
            pdf_bytes = row["guidance_pdf"]

            if not isinstance(pdf_bytes, (bytes, bytearray, memoryview)):
                continue

            try:
                reader = PdfReader(io.BytesIO(bytes(pdf_bytes)))
                metadata = reader.metadata
                title = (
                    str(metadata.title).strip()
                    if metadata and metadata.title
                    else f"Table 1 Rule {row['row_no']}"
                )

                pages: list[dict[str, Any]] = []
                for page_index, page in enumerate(reader.pages[:max_pages]):
                    if remaining_chars <= 0:
                        break

                    extracted = (page.extract_text() or "").strip()
                    if not extracted:
                        continue

                    page_text = extracted[:remaining_chars]
                    remaining_chars -= len(page_text)
                    pages.append({
                        "page_number": page_index + 1,
                        "text": page_text,
                    })

                documents.append({
                    "row_no": row["row_no"],
                    "document_title": title,
                    "page_count": len(reader.pages),
                    "status": "EXTRACTED" if pages else "OCR_REQUIRED",
                    "pages": pages,
                })

            except Exception:
                logger.exception(
                    "Colony guidance PDF extraction failed for Table 1 row %s.",
                    row["row_no"],
                )
                documents.append({
                    "row_no": row["row_no"],
                    "document_title": f"Table 1 Rule {row['row_no']}",
                    "status": "EXTRACTION_FAILED",
                    "pages": [],
                })

        return documents

    async def retrieve(
        self,
        output_config_id: int,
        definition_code: str,
        search_text: str = "",
        row_numbers: list[int] | None = None,
    ) -> dict[str, Any]:
        """Return bounded evidence from resources granted by output metadata."""

        if type(output_config_id) is not int or output_config_id < 1:
            raise FunctionOutputResourceError(
                "A valid output configuration ID is required.",
                422,
            )

        if not isinstance(definition_code, str) or not definition_code.strip():
            raise FunctionOutputResourceError(
                "An AI Avatar definition code is required.",
                422,
            )

        if not isinstance(search_text, str) or len(search_text) > 4000:
            raise FunctionOutputResourceError(
                "The resource search text is invalid.",
                422,
            )

        requested_rows = row_numbers or []
        if (
            not isinstance(requested_rows, list)
            or len(requested_rows) > 50
            or any(type(value) is not int or value < 1 for value in requested_rows)
        ):
            raise FunctionOutputResourceError(
                "The requested Table 1 row numbers are invalid.",
                422,
            )

        _, access_rows = await self._resolve_authorization(
            output_config_id=output_config_id,
            definition_code=definition_code.strip(),
        )

        access_by_code = {
            item["resource_code"]: item
            for item in access_rows
        }

        evidence: dict[str, Any] = {
            "contract": "PULSAR_FUNCTION_OUTPUT_RESOURCE_EVIDENCE",
            "output_config_id": output_config_id,
            "definition_code": definition_code.strip(),
            "resources": [],
            "table_1": None,
            "related_rules": [],
            "guidance_pdfs": [],
            "limitations": [],
        }

        search_results: list[dict[str, Any]] = []
        if "COLONY_RULE_SEARCH" in access_by_code:
            access = access_by_code["COLONY_RULE_SEARCH"]
            search_results = await self._search_rules(
                search_text,
                access["access_options"],
            )
            evidence["resources"].append("COLONY_RULE_SEARCH")

        if "COLONY_RELATED_RULES" in access_by_code:
            access = access_by_code["COLONY_RELATED_RULES"]
            related_results = await self._search_rules(
                search_text,
                access["access_options"],
            )
            evidence["related_rules"] = related_results
            evidence["resources"].append("COLONY_RELATED_RULES")

        if "COLONY_TABLE_1" in access_by_code:
            access = access_by_code["COLONY_TABLE_1"]
            rows, total_count = await self._load_table_1(
                access["access_options"],
                list(dict.fromkeys(
                    requested_rows
                    + [row["row_no"] for row in search_results]
                    + [row["row_no"] for row in evidence["related_rules"]]
                )),
            )
            evidence["table_1"] = {
                "rows": rows,
                "total_count": total_count,
                "returned_count": len(rows),
                "truncated": total_count > len(rows),
            }
            evidence["resources"].append("COLONY_TABLE_1")

        selected_row_numbers = list(dict.fromkeys(
            requested_rows
            + [row["row_no"] for row in search_results]
            + [row["row_no"] for row in evidence["related_rules"]]
        ))

        if "COLONY_GUIDANCE_PDF" in access_by_code:
            access = access_by_code["COLONY_GUIDANCE_PDF"]
            evidence["guidance_pdfs"] = await self._load_guidance_pdfs(
                selected_row_numbers,
                access["access_options"],
            )
            evidence["resources"].append("COLONY_GUIDANCE_PDF")

            if any(
                document["status"] == "OCR_REQUIRED"
                for document in evidence["guidance_pdfs"]
            ):
                evidence["limitations"].append(
                    "At least one guidance PDF contains no extractable text and requires OCR."
                )

        evidence["searched_row_numbers"] = selected_row_numbers
        return evidence
