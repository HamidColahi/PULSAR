# ===============================================
# File: Pulsar/backend/source_trace/analysis_service.py
#
# Description:
# Persistent interactive analysis sessions for P-ATVT Source Trace
#
# Change Date: 2026-11-20 18:55
# Timezone: Asia/Baku
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ai_avatar.service import AIAvatarService, AIAvatarServiceError


MAX_SECTION_CHARS = 18000
MAX_ANALYSIS_CHARS = 30000
MAX_STATE_CHARS = 12000

VALID_PALI_STATUSES = {
    "FINDING",
    "QUESTION",
    "CONFLICT",
    "ROOT_CAUSE",
    "CONTINUE",
}

VALID_DECISIONS = {
    "CONTINUE",
    "REVISE",
    "STOP",
    "RESUME",
}


class SourceTraceAnalysisError(Exception):
    """Represent a controlled interactive analysis session error."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _json_size(value: Any) -> int:
    return len(
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


def _chunk_items(items: list[dict], maximum_chars: int) -> list[list[dict]]:
    chunks: list[list[dict]] = []
    current: list[dict] = []
    current_size = 2

    for item in items:
        item_size = _json_size(item) + (1 if current else 0)

        if item_size > maximum_chars:
            raise SourceTraceAnalysisError(
                "A Source Trace item exceeds the analysis section size limit.",
                413,
            )

        if current and current_size + item_size > maximum_chars:
            chunks.append(current)
            current = []
            current_size = 2
            item_size = _json_size(item)

        current.append(item)
        current_size += item_size

    if current:
        chunks.append(current)

    return chunks


def build_analysis_sections(report: dict) -> list[dict]:
    """Split a complete trace report into evidence-preserving logical sections."""

    if not isinstance(report, dict):
        raise SourceTraceAnalysisError("A valid Source Trace report is required.")

    required = {
        "version",
        "topic",
        "options",
        "summary",
        "seeds",
        "files",
        "nodes",
        "edges",
        "limitations",
    }
    missing = required - report.keys()

    if missing:
        raise SourceTraceAnalysisError(
            "The Source Trace report is missing required sections: "
            + ", ".join(sorted(missing))
        )

    sections: list[dict] = []

    def add_section(section_type: str, title: str, content: dict) -> None:
        sections.append({
            "section_id": f"{section_type}-{len(sections) + 1:04d}",
            "section_type": section_type,
            "title": title,
            "content": content,
            "status": "PENDING",
            "analysis": None,
            "pali_status": None,
            "decision": None,
            "note": None,
        })

    add_section(
        "overview",
        "Trace Overview and Constraints",
        {
            "version": report.get("version"),
            "topic": report.get("topic"),
            "repository": report.get("repository"),
            "options": report.get("options", {}),
            "summary": report.get("summary", {}),
            "plain_language_summary": report.get("plain_language_summary", {}),
            "limitations": report.get("limitations", []),
        },
    )

    seed_items = report.get("seeds") or []
    if seed_items:
        for index, chunk in enumerate(_chunk_items(seed_items, MAX_SECTION_CHARS), 1):
            add_section(
                "seeds",
                f"Selected Seeds · Part {index}",
                {"items": chunk},
            )

    candidate_items = report.get("matched_candidates") or []
    if candidate_items:
        for index, chunk in enumerate(
            _chunk_items(candidate_items, MAX_SECTION_CHARS),
            1,
        ):
            add_section(
                "matched_candidates",
                f"Matched Candidates · Part {index}",
                {"items": chunk},
            )

    deferred_items = report.get("deferred_seeds") or []
    if deferred_items:
        for index, chunk in enumerate(
            _chunk_items(deferred_items, MAX_SECTION_CHARS),
            1,
        ):
            add_section(
                "deferred_seeds",
                f"Deferred Seeds · Part {index}",
                {"items": chunk},
            )

    file_items = [
        {"file": item}
        for item in (report.get("files") or [])
    ]
    if file_items:
        for index, chunk in enumerate(
            _chunk_items(file_items, MAX_SECTION_CHARS),
            1,
        ):
            add_section(
                "files",
                f"Related File Inventory · Part {index}",
                {"items": chunk},
            )

    nodes_by_file: dict[str, list[dict]] = {}
    for node in report.get("nodes") or []:
        file_name = str(node.get("file") or "Unknown file")
        nodes_by_file.setdefault(file_name, []).append(node)

    for file_name in sorted(nodes_by_file):
        chunks = _chunk_items(
            nodes_by_file[file_name],
            MAX_SECTION_CHARS - len(file_name) - 100,
        )
        for index, chunk in enumerate(chunks, 1):
            add_section(
                "nodes",
                f"Source Nodes · {file_name} · Part {index}",
                {
                    "file": file_name,
                    "part": index,
                    "parts_for_file": len(chunks),
                    "nodes": chunk,
                },
            )

    edge_items = report.get("edges") or []
    if edge_items:
        for index, chunk in enumerate(
            _chunk_items(edge_items, MAX_SECTION_CHARS),
            1,
        ):
            add_section(
                "edges",
                f"Relationship Evidence · Part {index}",
                {"items": chunk},
            )

    # Category indexes duplicate node tags and are intentionally omitted
    # from the AI stream to avoid repeating large arrays of node identifiers.

    if not sections:
        add_section("overview", "Trace Overview", {"topic": report.get("topic")})

    total = len(sections)
    for index, section in enumerate(sections):
        section["order"] = index
        section["total"] = total

    return sections


class SourceTraceAnalysisService:
    """Persist and resume user-owned P-ATVT analysis sessions."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.avatar_service = AIAvatarService(session)

    @staticmethod
    def _uuid(value: str, label: str) -> str:
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError, AttributeError) as exc:
            raise SourceTraceAnalysisError(
                f"A valid {label} is required.",
                422,
            ) from exc

    def _encrypt_payload(
        self,
        payload: dict,
        user_id: str,
        definition_id: str,
        session_id: str,
    ) -> dict[str, bytes | str]:
        try:
            return self.avatar_service._encrypt_content(
                content=json.dumps(payload, ensure_ascii=False),
                user_id=user_id,
                definition_id=definition_id,
                conversation_id=session_id,
                role="source_trace_analysis_session",
            )
        except AIAvatarServiceError as exc:
            raise SourceTraceAnalysisError(
                exc.message,
                exc.status_code,
            ) from exc

    @staticmethod
    def _decrypt_payload(row: Any) -> dict:
        encrypted_row = {
            "c_user_id": row["c_user_id"],
            "c_ai_definition_id": row["c_ai_definition_id"],
            "c_conversation_id": row["c_analysis_session_id"],
            "c_role": "source_trace_analysis_session",
            "c_content_ciphertext": row["c_payload_ciphertext"],
            "c_encryption_nonce": row["c_encryption_nonce"],
            "c_encryption_tag": row["c_encryption_tag"],
            "c_encryption_key_ref": row["c_encryption_key_ref"],
            "c_encryption_key_version": row["c_encryption_key_version"],
        }

        try:
            decoded = AIAvatarService._decrypt_content(encrypted_row)
            payload = json.loads(decoded)
        except AIAvatarServiceError as exc:
            raise SourceTraceAnalysisError(
                exc.message,
                exc.status_code,
            ) from exc
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise SourceTraceAnalysisError(
                "The stored Source Trace analysis payload is invalid.",
                500,
            ) from exc

        if not isinstance(payload, dict):
            raise SourceTraceAnalysisError(
                "The stored Source Trace analysis payload is invalid.",
                500,
            )

        return payload

    def _serialize(self, row: Any) -> dict:
        payload = self._decrypt_payload(row)

        return {
            "analysis_session_id": str(row["c_analysis_session_id"]),
            "topic": row["c_topic"],
            "report": payload.get("report", {}),
            "sections": payload.get("sections", []),
            "analysis_state": payload.get("analysis_state", {}),
            "current_section_index": row["c_current_section_index"],
            "status": row["c_status"],
            "definition_code": row["c_definition_code"],
            "conversation_id": (
                str(row["c_conversation_id"])
                if row["c_conversation_id"]
                else None
            ),
            "created_at": row["c_created_at"].isoformat(),
            "updated_at": row["c_updated_at"].isoformat(),
            "expires_at": row["c_expires_at"].isoformat(),
        }

    async def create_session(
        self,
        user_id: str,
        topic: str,
        report: dict,
        definition_code: str,
    ) -> dict:
        owner_id = self._uuid(user_id, "authenticated user ID")
        normalized_topic = topic.strip() if isinstance(topic, str) else ""

        if not normalized_topic or len(normalized_topic) > 200:
            raise SourceTraceAnalysisError("A valid trace topic is required.", 422)

        if report.get("topic") != normalized_topic:
            raise SourceTraceAnalysisError(
                "The session topic does not match the Source Trace report.",
                422,
            )

        if not isinstance(definition_code, str) or not definition_code.strip():
            raise SourceTraceAnalysisError(
                "The Pali Tracer definition code is required.",
                422,
            )

        try:
            resolved = await self.avatar_service.resolve(definition_code.strip())
        except AIAvatarServiceError as exc:
            raise SourceTraceAnalysisError(
                exc.message,
                exc.status_code,
            ) from exc

        definition = resolved["definition"]
        if int(definition["c_avatar_manager_id"]) != 4:
            raise SourceTraceAnalysisError(
                "Interactive Source Trace analysis requires an AI Avatar assigned to Manager 4.",
                409,
            )

        definition_id = str(definition["c_ai_definition_id"])
        sections = build_analysis_sections(report)
        session_id = str(uuid.uuid4())
        payload = {
            "report": report,
            "sections": sections,
            "analysis_state": {},
        }
        encrypted = self._encrypt_payload(
            payload,
            owner_id,
            definition_id,
            session_id,
        )

        await self.session.execute(
            text(
                """
                INSERT INTO pulsar.t_source_trace_analysis_session (
                    c_analysis_session_id,
                    c_user_id,
                    c_ai_definition_id,
                    c_definition_code,
                    c_topic,
                    c_payload_ciphertext,
                    c_encryption_nonce,
                    c_encryption_tag,
                    c_encryption_key_ref,
                    c_encryption_key_version,
                    c_current_section_index,
                    c_status,
                    c_expires_at
                )
                VALUES (
                    CAST(:session_id AS uuid),
                    CAST(:user_id AS uuid),
                    CAST(:definition_id AS uuid),
                    :definition_code,
                    :topic,
                    :ciphertext,
                    :nonce,
                    :tag,
                    :key_ref,
                    :key_version,
                    0,
                    'READY',
                    CURRENT_TIMESTAMP + INTERVAL '30 days'
                )
                """
            ),
            {
                "session_id": session_id,
                "user_id": owner_id,
                "definition_id": definition_id,
                "definition_code": definition_code.strip(),
                "topic": normalized_topic,
                "ciphertext": encrypted["ciphertext"],
                "nonce": encrypted["nonce"],
                "tag": encrypted["tag"],
                "key_ref": encrypted["key_ref"],
                "key_version": encrypted["key_version"],
            },
        )
        await self.session.commit()

        return await self.get_session(owner_id, session_id)

    async def get_session(self, user_id: str, session_id: str) -> dict:
        owner_id = self._uuid(user_id, "authenticated user ID")
        normalized_id = self._uuid(session_id, "analysis session ID")

        result = await self.session.execute(
            text(
                """
                SELECT *
                FROM pulsar.t_source_trace_analysis_session
                WHERE c_analysis_session_id = CAST(:session_id AS uuid)
                  AND c_user_id = CAST(:user_id AS uuid)
                  AND c_expires_at > CURRENT_TIMESTAMP
                LIMIT 1
                """
            ),
            {
                "session_id": normalized_id,
                "user_id": owner_id,
            },
        )
        row = result.mappings().first()

        if not row:
            raise SourceTraceAnalysisError(
                "The Source Trace analysis session was not found or has expired.",
                404,
            )

        return self._serialize(row)

    async def save_checkpoint(
        self,
        user_id: str,
        session_id: str,
        section_index: int,
        analysis: str | None = None,
        pali_status: str | None = None,
        decision: str | None = None,
        note: str | None = None,
        analysis_state: dict | None = None,
        definition_code: str | None = None,
        conversation_id: str | None = None,
    ) -> dict:
        owner_id = self._uuid(user_id, "authenticated user ID")
        normalized_id = self._uuid(session_id, "analysis session ID")

        if type(section_index) is not int or section_index < 0:
            raise SourceTraceAnalysisError("Invalid analysis section index.", 422)

        if analysis is not None and (
            not isinstance(analysis, str)
            or not analysis.strip()
            or len(analysis) > MAX_ANALYSIS_CHARS
        ):
            raise SourceTraceAnalysisError("Invalid Pali analysis content.", 422)

        if pali_status is not None:
            pali_status = pali_status.upper()
            if pali_status not in VALID_PALI_STATUSES:
                raise SourceTraceAnalysisError("Invalid Pali analysis status.", 422)

        if decision is not None:
            decision = decision.upper()
            if decision not in VALID_DECISIONS:
                raise SourceTraceAnalysisError("Invalid programmer decision.", 422)

        if note is not None and (
            not isinstance(note, str) or len(note) > 4000
        ):
            raise SourceTraceAnalysisError("The review note is too long.", 422)

        if analysis_state is not None:
            if not isinstance(analysis_state, dict) or _json_size(analysis_state) > MAX_STATE_CHARS:
                raise SourceTraceAnalysisError("Invalid analysis checkpoint state.", 422)

        if definition_code is not None and (
            not isinstance(definition_code, str)
            or not definition_code.strip()
            or len(definition_code) > 100
        ):
            raise SourceTraceAnalysisError("Invalid AI Avatar definition code.", 422)

        if conversation_id is not None:
            conversation_id = self._uuid(
                conversation_id,
                "AI Avatar conversation ID",
            )

        result = await self.session.execute(
            text(
                """
                SELECT *
                FROM pulsar.t_source_trace_analysis_session
                WHERE c_analysis_session_id = CAST(:session_id AS uuid)
                  AND c_user_id = CAST(:user_id AS uuid)
                  AND c_expires_at > CURRENT_TIMESTAMP
                FOR UPDATE
                """
            ),
            {
                "session_id": normalized_id,
                "user_id": owner_id,
            },
        )
        row = result.mappings().first()

        if not row:
            raise SourceTraceAnalysisError(
                "The Source Trace analysis session was not found or has expired.",
                404,
            )

        payload = self._decrypt_payload(row)
        sections = payload.get("sections", [])
        state = payload.get("analysis_state", {})
        current_index = row["c_current_section_index"]
        status = row["c_status"]

        if section_index != current_index or section_index >= len(sections):
            raise SourceTraceAnalysisError(
                "The requested section is not the active analysis checkpoint.",
                409,
            )

        section = sections[section_index]

        if analysis is not None:
            section["analysis"] = analysis.strip()
            section["pali_status"] = pali_status or "CONTINUE"
            section["status"] = "ANALYZED"
            section["decision"] = None
            section["note"] = None
            status = "PAUSED"

        if note is not None:
            section["note"] = note.strip() or None

        if decision == "CONTINUE":
            if not section.get("analysis"):
                raise SourceTraceAnalysisError(
                    "The active section must be analyzed before continuing.",
                    409,
                )
            section["decision"] = decision
            section["status"] = "APPROVED"
            current_index += 1
            status = (
                "COMPLETED"
                if current_index >= len(sections)
                else "READY"
            )

        elif decision == "REVISE":
            section["decision"] = decision
            section["status"] = "PENDING"
            section["analysis"] = None
            section["pali_status"] = None
            current_index = section_index
            status = "READY"

        elif decision == "STOP":
            section["decision"] = decision
            section["status"] = "STOPPED"
            status = "STOPPED"

        elif decision == "RESUME":
            section["decision"] = decision
            if section.get("analysis"):
                section["status"] = "ANALYZED"
                status = "PAUSED"
            else:
                section["status"] = "PENDING"
                status = "READY"

        if analysis_state is not None:
            state = analysis_state

        payload["sections"] = sections
        payload["analysis_state"] = state
        encrypted = self._encrypt_payload(
            payload,
            owner_id,
            str(row["c_ai_definition_id"]),
            normalized_id,
        )

        await self.session.execute(
            text(
                """
                UPDATE pulsar.t_source_trace_analysis_session
                SET c_payload_ciphertext = :ciphertext,
                    c_encryption_nonce = :nonce,
                    c_encryption_tag = :tag,
                    c_encryption_key_ref = :key_ref,
                    c_encryption_key_version = :key_version,
                    c_current_section_index = :current_index,
                    c_status = :status,
                    c_definition_code = COALESCE(:definition_code, c_definition_code),
                    c_conversation_id = COALESCE(
                        CAST(:conversation_id AS uuid),
                        c_conversation_id
                    ),
                    c_updated_at = CURRENT_TIMESTAMP
                WHERE c_analysis_session_id = CAST(:session_id AS uuid)
                  AND c_user_id = CAST(:user_id AS uuid)
                """
            ),
            {
                "ciphertext": encrypted["ciphertext"],
                "nonce": encrypted["nonce"],
                "tag": encrypted["tag"],
                "key_ref": encrypted["key_ref"],
                "key_version": encrypted["key_version"],
                "current_index": current_index,
                "status": status,
                "definition_code": definition_code,
                "conversation_id": conversation_id,
                "session_id": normalized_id,
                "user_id": owner_id,
            },
        )
        await self.session.commit()

        return await self.get_session(owner_id, normalized_id)
