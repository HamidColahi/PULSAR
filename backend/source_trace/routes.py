# ===============================================
# File: Pulsar/backend/source_trace/routes.py
#
# Description:
# Metadata-registered API routes for PULSAR Source Trace
#
# Change Date: 2026-11-20 19:05
# Timezone: Asia/Baku
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session

from general.auth.dependencies import get_current_user
from general.user.schemas.user import UserProfileResponse
from source_trace.api_registry import (
    API_REGISTRY,
    validate_api_registry,
)
from source_trace.service import (
    source_trace_service,
)
from source_trace.analysis_service import (
    SourceTraceAnalysisError,
    SourceTraceAnalysisService,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Source Trace"],
)


SourceScope = Literal["frontend", "backend", "database"]
SourceRelation = Literal[
    "calls",
    "imports",
    "api",
    "references",
    "sql",
]


class SourceTraceAnalysisSessionRequest(BaseModel):
    """Validate a complete report submitted for interactive analysis."""

    topic: str = Field(..., min_length=1, max_length=200)
    definition_code: str = Field(..., min_length=1, max_length=100)
    report: dict = Field(...)

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Topic must not be empty.")
        return value


class SourceTraceAnalysisCheckpointRequest(BaseModel):
    """Validate one Pali result or programmer checkpoint decision."""

    section_index: int = Field(..., ge=0)
    analysis: str | None = Field(default=None, max_length=30000)
    pali_status: Literal[
        "FINDING",
        "QUESTION",
        "CONFLICT",
        "ROOT_CAUSE",
        "CONTINUE",
    ] | None = None
    decision: Literal["CONTINUE", "REVISE", "STOP", "RESUME"] | None = None
    note: str | None = Field(default=None, max_length=4000)
    analysis_state: dict | None = None
    definition_code: str | None = Field(default=None, max_length=100)
    conversation_id: str | None = Field(default=None, max_length=36)


class SourceTraceRequest(BaseModel):
    """Validate a static source trace request."""

    topic: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Topic, symbol, field, API, or workflow to trace.",
    )
    max_nodes: int = Field(
        default=160,
        ge=1,
        le=5000,
    )
    scope: list[SourceScope] = Field(
        default_factory=lambda: ["frontend", "backend", "database"],
        min_length=1,
    )
    relations: list[SourceRelation] = Field(
        default_factory=lambda: [
            "calls",
            "imports",
            "api",
            "references",
            "sql",
        ],
        min_length=1,
    )
    depth: int = Field(
        default=3,
        ge=1,
        le=20,
    )

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Topic must not be empty.")

        return value

    @field_validator("scope", "relations")
    @classmethod
    def remove_duplicate_values(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))


@router.post(
    API_REGISTRY["SOURCE_TRACE_TOPIC"].path,
)
async def run_source_trace(
    payload: SourceTraceRequest,
    current_user: UserProfileResponse = Depends(get_current_user),
):
    """Execute a source trace for an authenticated, active PULSAR user."""

    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive.",
        )

    try:
        return await source_trace_service.trace_topic(
            topic=payload.topic,
            max_nodes=payload.max_nodes,
            scope=payload.scope,
            relations=payload.relations,
            depth=payload.depth,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected Source Trace request failure for topic '%s' "
            "and user '%s'.",
            payload.topic,
            current_user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="The Source Trace request could not be completed.",
        ) from exc


@router.post(
    API_REGISTRY["SOURCE_TRACE_ANALYSIS_SESSION_CREATE"].path,
)
async def create_source_trace_analysis_session(
    payload: SourceTraceAnalysisSessionRequest,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a durable, user-owned analysis session for a complete trace report."""

    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive.",
        )

    service = SourceTraceAnalysisService(session)

    try:
        return await service.create_session(
            user_id=str(current_user.id),
            topic=payload.topic,
            report=payload.report,
            definition_code=payload.definition_code,
        )
    except SourceTraceAnalysisError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        logger.exception("Source Trace analysis session creation failed.")
        raise HTTPException(
            status_code=500,
            detail="The analysis session could not be saved. Verify that source_trace_analysis_schema.sql has been applied.",
        ) from exc


@router.get(
    API_REGISTRY["SOURCE_TRACE_ANALYSIS_SESSION_GET"].path,
)
async def get_source_trace_analysis_session(
    session_id: str,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Load an analysis session owned by the authenticated user."""

    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive.",
        )

    service = SourceTraceAnalysisService(session)

    try:
        return await service.get_session(
            user_id=str(current_user.id),
            session_id=session_id,
        )
    except SourceTraceAnalysisError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        logger.exception("Source Trace analysis session retrieval failed.")
        raise HTTPException(
            status_code=500,
            detail="The saved Source Trace analysis session could not be retrieved.",
        ) from exc


@router.patch(
    API_REGISTRY["SOURCE_TRACE_ANALYSIS_CHECKPOINT"].path,
)
async def save_source_trace_analysis_checkpoint(
    session_id: str,
    payload: SourceTraceAnalysisCheckpointRequest,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Save Pali findings, compact analysis state, and programmer decisions."""

    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive.",
        )

    service = SourceTraceAnalysisService(session)

    try:
        return await service.save_checkpoint(
            user_id=str(current_user.id),
            session_id=session_id,
            section_index=payload.section_index,
            analysis=payload.analysis,
            pali_status=payload.pali_status,
            decision=payload.decision,
            note=payload.note,
            analysis_state=payload.analysis_state,
            definition_code=payload.definition_code,
            conversation_id=payload.conversation_id,
        )
    except SourceTraceAnalysisError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        logger.exception("Source Trace analysis checkpoint update failed.")
        raise HTTPException(
            status_code=500,
            detail="The Source Trace analysis checkpoint could not be saved.",
        ) from exc


validate_api_registry(router)
