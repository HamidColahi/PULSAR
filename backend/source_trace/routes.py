# ===============================================
# File: Pulsar/backend/source_trace/routes.py
#
# Description:
# Metadata-registered API routes for PULSAR Source Trace
#
# Change Date: 2026-11-19 00:35
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

from general.auth.dependencies import get_current_user
from general.user.schemas.user import UserProfileResponse
from source_trace.api_registry import (
    API_REGISTRY,
    validate_api_registry,
)
from source_trace.service import (
    source_trace_service,
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


validate_api_registry(router)
