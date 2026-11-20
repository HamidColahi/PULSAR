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

import hashlib
import io
import json
import logging
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from pypdf import PdfReader
except ImportError:  # The runtime reports a controlled dependency error.
    PdfReader = None


logger = logging.getLogger(__name__)

PDF_EXTRACTOR_VERSION = "PYPDF_1"


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
        schema_name: str,
        function_name: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        config_result = await self.session.execute(
            text(
                """
                SELECT
                    oc.output_config_id,
                    oc.schema_name,
                    oc.function_name,
                    oc.c_avatar_manager_id
                FROM pulsar.t_function_output_config oc
                JOIN pulsar.t_function_definition fd
                  ON fd.schema_name = oc.schema_name
                 AND fd.function_name = oc.function_name
                WHERE oc.output_config_id = :output_config_id
                  AND oc.is_active = TRUE
                  AND fd.is_active = TRUE
                  AND fd.state = 'ACTIVE'
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

        if (
            config["schema_name"] != schema_name
            or config["function_name"] != function_name
        ):
            raise FunctionOutputResourceError(
                "The output configuration does not belong to the requested Function.",
                403,
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
                WHERE row_no = ANY(CAST(:row_numbers AS integer[]))
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

        tokens = [
            cleaned
            for token in re.split(r"\s+", normalized_text)
            if len(cleaned := re.sub(r"[^\w-]", "", token, flags=re.UNICODE)) >= 2
        ][:12]

        if not tokens:
            return []

        conditions = []
        bind_values: dict[str, Any] = {"result_limit": limit}

        for index, token in enumerate(tokens):
            bind_key = f"search_{index}"
            bind_values[bind_key] = f"%{token[:100]}%"
            conditions.append(
                "(" + " OR ".join(
                    f"COALESCE({field}::text, '') ILIKE :{bind_key}"
                    for field in fields
                ) + ")"
            )

        result = await self.session.execute(
            text(
                f"""
                SELECT {self.RULE_COLUMNS}
                FROM pulsar.table_1
                WHERE {" OR ".join(conditions)}
                ORDER BY row_no
                LIMIT :result_limit
                """
            ),
            bind_values,
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]

    async def _find_related_rules(
        self,
        seed_rows: list[dict[str, Any]],
        options: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not seed_rows:
            return []

        rp_values = list(dict.fromkeys(
            str(row["rp"]).strip()
            for row in seed_rows
            if row.get("rp") is not None and str(row["rp"]).strip()
        ))
        pbi_values = list(dict.fromkeys(
            str(row["pbi_sbi"]).strip()
            for row in seed_rows
            if row.get("pbi_sbi") is not None and str(row["pbi_sbi"]).strip()
        ))
        event_values = list(dict.fromkeys(
            str(row["event"]).strip()
            for row in seed_rows
            if row.get("event") is not None and str(row["event"]).strip()
        ))
        excluded_rows = list(dict.fromkeys(
            int(row["row_no"])
            for row in seed_rows
            if row.get("row_no") is not None
        ))

        conditions = []
        bind_values: dict[str, Any] = {
            "excluded_rows": excluded_rows,
            "result_limit": self._bounded_int(
                options.get("max_results"),
                default=20,
                minimum=1,
                maximum=100,
            ),
        }

        if rp_values:
            conditions.append("rp = ANY(CAST(:rp_values AS text[]))")
            bind_values["rp_values"] = rp_values
        if pbi_values:
            conditions.append("pbi_sbi = ANY(CAST(:pbi_values AS text[]))")
            bind_values["pbi_values"] = pbi_values
        if event_values:
            conditions.append("event = ANY(CAST(:event_values AS text[]))")
            bind_values["event_values"] = event_values

        if not conditions:
            return []

        result = await self.session.execute(
            text(
                f"""
                SELECT {self.RULE_COLUMNS}
                FROM pulsar.table_1
                WHERE ({" OR ".join(conditions)})
                  AND NOT (row_no = ANY(CAST(:excluded_rows AS integer[])))
                ORDER BY row_no
                LIMIT :result_limit
                """
            ),
            bind_values,
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
                WHERE row_no = ANY(CAST(:row_numbers AS integer[]))
                  AND guidance_pdf IS NOT NULL
                ORDER BY row_no
                """
            ),
            {"row_numbers": row_numbers[:50]},
        )

        pdf_rows = result.mappings().all()
        if not pdf_rows:
            return []

        cache_result = await self.session.execute(
            text(
                """
                SELECT
                    row_no,
                    content_sha256,
                    document_title,
                    page_count,
                    extraction_status,
                    extracted_pages,
                    extractor_version
                FROM pulsar.t_colony_guidance_pdf_index
                WHERE row_no = ANY(CAST(:row_numbers AS integer[]))
                """
            ),
            {"row_numbers": [row["row_no"] for row in pdf_rows]},
        )
        cache_by_row = {
            row["row_no"]: dict(row)
            for row in cache_result.mappings().all()
        }

        documents: list[dict[str, Any]] = []
        remaining_chars = max_text_chars

        for row in pdf_rows:
            pdf_bytes = row["guidance_pdf"]

            if not isinstance(pdf_bytes, (bytes, bytearray, memoryview)):
                continue

            raw_pdf = bytes(pdf_bytes)
            content_hash = hashlib.sha256(raw_pdf).hexdigest()
            cached = cache_by_row.get(row["row_no"])

            cache_is_current = bool(
                cached
                and cached["content_sha256"] == content_hash
                and cached["extractor_version"] == PDF_EXTRACTOR_VERSION
            )

            if cache_is_current:
                document_title = cached["document_title"]
                page_count = int(cached["page_count"] or 0)
                extraction_status = cached["extraction_status"]
                extracted_pages = cached["extracted_pages"]
                if isinstance(extracted_pages, str):
                    try:
                        extracted_pages = json.loads(extracted_pages)
                    except (TypeError, ValueError):
                        extracted_pages = []
                if not isinstance(extracted_pages, list):
                    extracted_pages = []
            else:
                if PdfReader is None:
                    raise FunctionOutputResourceError(
                        "PDF text extraction is unavailable. Install the configured pypdf dependency.",
                        503,
                    )

                try:
                    reader = PdfReader(io.BytesIO(raw_pdf))
                    metadata = reader.metadata
                    document_title = (
                        str(metadata.title).strip()
                        if metadata and metadata.title
                        else f"Table 1 Rule {row['row_no']}"
                    )
                    page_count = len(reader.pages)
                    extracted_pages = []
                    cache_remaining_chars = 500000

                    for page_index, page in enumerate(reader.pages[:300]):
                        if cache_remaining_chars <= 0:
                            break

                        extracted = (page.extract_text() or "").strip()
                        if not extracted:
                            continue

                        page_text = extracted[:cache_remaining_chars]
                        cache_remaining_chars -= len(page_text)
                        extracted_pages.append({
                            "page_number": page_index + 1,
                            "text": page_text,
                        })

                    extraction_status = (
                        "EXTRACTED" if extracted_pages else "OCR_REQUIRED"
                    )

                except Exception:
                    logger.exception(
                        "Colony guidance PDF extraction failed for Table 1 row %s.",
                        row["row_no"],
                    )
                    document_title = f"Table 1 Rule {row['row_no']}"
                    page_count = 0
                    extraction_status = "EXTRACTION_FAILED"
                    extracted_pages = []

                await self.session.execute(
                    text(
                        """
                        INSERT INTO pulsar.t_colony_guidance_pdf_index (
                            row_no,
                            content_sha256,
                            document_title,
                            page_count,
                            extraction_status,
                            extracted_pages,
                            extractor_version,
                            extracted_at,
                            updated_at
                        )
                        VALUES (
                            :row_no,
                            :content_sha256,
                            :document_title,
                            :page_count,
                            :extraction_status,
                            CAST(:extracted_pages AS jsonb),
                            :extractor_version,
                            CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP
                        )
                        ON CONFLICT (row_no)
                        DO UPDATE SET
                            content_sha256 = EXCLUDED.content_sha256,
                            document_title = EXCLUDED.document_title,
                            page_count = EXCLUDED.page_count,
                            extraction_status = EXCLUDED.extraction_status,
                            extracted_pages = EXCLUDED.extracted_pages,
                            extractor_version = EXCLUDED.extractor_version,
                            extracted_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        """
                    ),
                    {
                        "row_no": row["row_no"],
                        "content_sha256": content_hash,
                        "document_title": document_title,
                        "page_count": page_count,
                        "extraction_status": extraction_status,
                        "extracted_pages": json.dumps(
                            extracted_pages,
                            ensure_ascii=False,
                        ),
                        "extractor_version": PDF_EXTRACTOR_VERSION,
                    },
                )

            output_pages: list[dict[str, Any]] = []
            for page in extracted_pages[:max_pages]:
                if remaining_chars <= 0:
                    break
                if not isinstance(page, dict):
                    continue

                page_text = str(page.get("text") or "")
                if not page_text:
                    continue

                bounded_text = page_text[:remaining_chars]
                remaining_chars -= len(bounded_text)
                output_pages.append({
                    "page_number": page.get("page_number"),
                    "text": bounded_text,
                })

            documents.append({
                "row_no": row["row_no"],
                "document_title": document_title,
                "page_count": page_count,
                "status": extraction_status,
                "pages": output_pages,
                "cached": cache_is_current,
            })

        return documents

    async def retrieve(
        self,
        output_config_id: int,
        definition_code: str,
        schema_name: str,
        function_name: str,
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

        if (
            not isinstance(schema_name, str)
            or not schema_name.strip()
            or not isinstance(function_name, str)
            or not function_name.strip()
        ):
            raise FunctionOutputResourceError(
                "The Function schema and name are required.",
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
            schema_name=schema_name.strip(),
            function_name=function_name.strip(),
        )

        access_by_code = {
            item["resource_code"]: item
            for item in access_rows
        }

        evidence: dict[str, Any] = {
            "contract": "PULSAR_FUNCTION_OUTPUT_RESOURCE_EVIDENCE",
            "output_config_id": output_config_id,
            "definition_code": definition_code.strip(),
            "schema_name": schema_name.strip(),
            "function_name": function_name.strip(),
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

        related_seed_rows = list(search_results)
        if requested_rows and "COLONY_TABLE_1" in access_by_code:
            table_access = access_by_code["COLONY_TABLE_1"]
            explicit_rows, _ = await self._load_table_1(
                table_access["access_options"],
                requested_rows,
            )
            known_seed_rows = {
                row["row_no"] for row in related_seed_rows
            }
            related_seed_rows.extend(
                row for row in explicit_rows
                if row["row_no"] not in known_seed_rows
            )

        if "COLONY_RELATED_RULES" in access_by_code:
            access = access_by_code["COLONY_RELATED_RULES"]
            evidence["related_rules"] = await self._find_related_rules(
                related_seed_rows,
                access["access_options"],
            )
            evidence["resources"].append("COLONY_RELATED_RULES")

        selected_row_numbers = list(dict.fromkeys(
            requested_rows
            + [row["row_no"] for row in search_results]
            + [row["row_no"] for row in evidence["related_rules"]]
        ))

        if "COLONY_TABLE_1" in access_by_code:
            access = access_by_code["COLONY_TABLE_1"]
            rows, total_count = await self._load_table_1(
                access["access_options"],
                selected_row_numbers,
            )
            evidence["table_1"] = {
                "rows": rows,
                "total_count": total_count,
                "returned_count": len(rows),
                "truncated": len(selected_row_numbers) > len(rows),
            }
            evidence["resources"].append("COLONY_TABLE_1")

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
