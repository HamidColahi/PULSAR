
# ===============================================
# File: Pulsar/backend/ai_avatar/routes.py
#
# Description:
# Metadata-registered AI Avatar API routes with authenticated chat access
#
# Change Date: 2026-11-21 04:00
# Timezone: Asia/Baku
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from general.auth.dependencies import get_current_user
from general.user.schemas.user import UserProfileResponse
from ai_avatar.api_registry import (
    API_REGISTRY,
    validate_api_registry,
)
from ai_avatar.service import (
    AIAvatarService,
    AIAvatarServiceError,
)
from ai_avatar.resource_access import (
    FunctionOutputResourceError,
    FunctionOutputResourceService,
)
from ai_avatar.function_output_analysis_service import (
    PaliAnalystAnalysisError,
    PaliAnalystAnalysisService,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["AI Avatar"],
)


class AvatarChatRequest(BaseModel):
    """Validate an incoming Avatar chat request."""

    definition_code: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=100000,
    )
    context_variables: dict[str, Any] = Field(
        default_factory=dict,
    )
    conversation_id: str | None = Field(
        default=None,
        max_length=36,
    )
    new_conversation: bool = False
    include_history: bool = True


class AvatarChatResponse(BaseModel):
    """Represent a successful Avatar chat response."""

    definition_code: str
    operation_code: str
    model_code: str
    presentation_code: str
    response: Any
    conversation_id: str | None = None


class FunctionOutputResourceRequest(BaseModel):
    """Validate a metadata-authorized Function output resource request."""

    output_config_id: int = Field(..., ge=1)
    definition_code: str = Field(..., min_length=1, max_length=100)
    schema_name: str = Field(..., min_length=1, max_length=128)
    function_name: str = Field(..., min_length=1, max_length=255)
    search_text: str = Field(default="", max_length=4000)
    row_numbers: list[int] = Field(default_factory=list, max_length=50)


class FunctionOutputAnalysisSessionRequest(BaseModel):
    """Validate a Function output submitted for interactive Pali Analyst review."""

    output_config_id: int = Field(..., ge=1)
    definition_code: str = Field(..., min_length=1, max_length=100)
    report: dict[str, Any] = Field(...)


class FunctionOutputAnalysisCheckpointRequest(BaseModel):
    """Validate one Pali Analyst result or programmer checkpoint decision."""

    section_index: int = Field(..., ge=0)
    analysis: str | None = Field(default=None, max_length=30000)
    pali_status: str | None = Field(default=None, max_length=20)
    decision: str | None = Field(default=None, max_length=20)
    note: str | None = Field(default=None, max_length=4000)
    analysis_state: dict[str, Any] | None = None
    definition_code: str | None = Field(default=None, max_length=100)
    conversation_id: str | None = Field(default=None, max_length=36)
    interaction: dict[str, Any] | None = None


class AvatarDefinitionResponse(BaseModel):
    """Represent the selected active Avatar definition and presentation."""

    definition_code: str
    title: str
    description: str | None = None
    default_language: str | None = None
    avatar_manager_id: int
    presentation_code: str
    presentation_type: str
    presentation_definition: dict[str, Any]


class AvatarIntroductionRequest(BaseModel):
    """Validate a request for the first-time Avatar introduction."""

    definition_code: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    language_code: str | None = Field(
        default=None,
        max_length=12,
    )


class AvatarIntroductionResponse(BaseModel):
    """Represent the first-time Avatar introduction response."""

    definition_code: str
    show_introduction: bool
    message: str | None = None


def _validate_definition_code(value: str) -> str:
    """Accept only safe metadata identifiers."""

    value = value.strip()

    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise HTTPException(
            status_code=422,
            detail="Invalid AI Avatar definition code.",
        )

    return value


@router.get(
    API_REGISTRY["AI_AVATAR_DEFAULT"].path,
    response_model=AvatarDefinitionResponse,
)
async def get_default_avatar(
    avatar_manager_id: int = Query(
        default=3,
        ge=1,
    ),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Return the unique active Avatar definition and its default presentation
    for the requested Avatar Manager.
    """

    service = AIAvatarService(session)

    try:
        definition = await service.get_active_definition(
            avatar_manager_id=avatar_manager_id
        )

        resolved = await service.resolve(
            definition["c_definition_code"]
        )
        presentation = resolved["presentation"]

        return AvatarDefinitionResponse(
            definition_code=definition["c_definition_code"],
            title=definition["c_title"],
            description=definition["c_description"],
            default_language=definition["c_default_language"],
            avatar_manager_id=definition["c_avatar_manager_id"],
            presentation_code=presentation["c_presentation_code"],
            presentation_type=presentation["c_presentation_type"],
            presentation_definition=service._as_dict(
                presentation["c_definition"]
            ),
        )

    except AIAvatarServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected AI Avatar definition lookup failure."
        )

        raise HTTPException(
            status_code=500,
            detail="The AI Avatar definition could not be retrieved.",
        ) from exc


@router.post(
    API_REGISTRY["AI_AVATAR_INTRODUCTION"].path,
    response_model=AvatarIntroductionResponse,
)
async def get_avatar_introduction(
    payload: AvatarIntroductionRequest,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Return the configured first-time introduction for an
    authenticated user and active Avatar definition.
    """

    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive.",
        )

    definition_code = _validate_definition_code(
        payload.definition_code
    )

    language_code = payload.language_code

    if language_code is not None:
        language_code = language_code.strip().lower()

        if language_code and not re.fullmatch(
            r"[A-Za-z0-9_-]+",
            language_code,
        ):
            raise HTTPException(
                status_code=422,
                detail="Invalid language code.",
            )

        if not language_code:
            language_code = None

    service = AIAvatarService(session)

    try:
        result = await service.get_first_introduction(
            user_id=str(current_user.id),
            definition_code=definition_code,
            language_code=language_code,
        )

        return AvatarIntroductionResponse(**result)

    except AIAvatarServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected AI Avatar introduction lookup failure."
        )

        raise HTTPException(
            status_code=500,
            detail="The AI Avatar introduction could not be retrieved.",
        ) from exc


@router.post(
    API_REGISTRY["AI_AVATAR_CHAT"].path,
    response_model=AvatarChatResponse,
)
async def chat_with_avatar(
    payload: AvatarChatRequest,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Execute a chat request using an active metadata-defined Avatar.

    An authenticated, active user is required.
    Provider, model, operation, context, policy, and presentation
    are resolved by the AI Avatar service.
    """

    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive.",
        )

    definition_code = _validate_definition_code(
        payload.definition_code
    )

    service = AIAvatarService(session)

    try:
        result = await service.chat(
            definition_code=definition_code,
            user_message=payload.message,
            user_id=str(current_user.id),
            context_variables=payload.context_variables,
            conversation_id=payload.conversation_id,
            interaction=payload.interaction,
            new_conversation=payload.new_conversation,
            include_history=payload.include_history,
        )

        return AvatarChatResponse(**result)

    except AIAvatarServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected AI Avatar runtime failure."
        )

        raise HTTPException(
            status_code=500,
            detail="The AI Avatar request could not be completed.",
        ) from exc


@router.post(
    API_REGISTRY["AI_AVATAR_FUNCTION_OUTPUT_RESOURCES"].path,
)
async def get_function_output_resources(
    payload: FunctionOutputResourceRequest,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve only the resources granted to the selected output configuration."""

    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive.",
        )

    service = FunctionOutputResourceService(session)

    try:
        result = await service.retrieve(
            output_config_id=payload.output_config_id,
            definition_code=_validate_definition_code(payload.definition_code),
            schema_name=payload.schema_name,
            function_name=payload.function_name,
            search_text=payload.search_text,
            row_numbers=payload.row_numbers,
        )
        await session.commit()
        return result
    except FunctionOutputResourceError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        await session.rollback()
        logger.exception(
            "Function output resource retrieval failed for output config %s.",
            payload.output_config_id,
        )
        raise HTTPException(
            status_code=500,
            detail="The authorized Function output resources could not be retrieved. Verify that function_output_access_schema.sql has been applied.",
        ) from exc


@router.post(
    API_REGISTRY["AI_AVATAR_FUNCTION_OUTPUT_ANALYSIS_CREATE"].path,
)
async def create_function_output_analysis_session(
    payload: FunctionOutputAnalysisSessionRequest,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create an encrypted, user-owned Pali Analyst session."""

    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive.",
        )

    service = PaliAnalystAnalysisService(session)

    try:
        return await service.create_session(
            user_id=str(current_user.id),
            report=payload.report,
            definition_code=_validate_definition_code(payload.definition_code),
            output_config_id=payload.output_config_id,
        )
    except PaliAnalystAnalysisError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        logger.exception("Pali Analyst session creation failed.")
        raise HTTPException(
            status_code=500,
            detail="The Pali Analyst session could not be saved. Verify that function_output_analysis_schema.sql has been applied.",
        ) from exc


@router.get(
    API_REGISTRY["AI_AVATAR_FUNCTION_OUTPUT_ANALYSIS_GET"].path,
)
async def get_function_output_analysis_session(
    session_id: str,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve an encrypted Pali Analyst session owned by the current user."""

    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive.",
        )

    service = PaliAnalystAnalysisService(session)

    try:
        return await service.get_session(
            user_id=str(current_user.id),
            session_id=session_id,
        )
    except PaliAnalystAnalysisError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        logger.exception("Pali Analyst session retrieval failed.")
        raise HTTPException(
            status_code=500,
            detail="The saved Pali Analyst session could not be retrieved.",
        ) from exc


@router.patch(
    API_REGISTRY["AI_AVATAR_FUNCTION_OUTPUT_ANALYSIS_CHECKPOINT"].path,
)
async def save_function_output_analysis_checkpoint(
    session_id: str,
    payload: FunctionOutputAnalysisCheckpointRequest,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Persist Pali Analyst findings and programmer review decisions."""

    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive.",
        )

    service = PaliAnalystAnalysisService(session)

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
    except PaliAnalystAnalysisError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        logger.exception("Pali Analyst checkpoint update failed.")
        raise HTTPException(
            status_code=500,
            detail="The Pali Analyst checkpoint could not be saved.",
        ) from exc


validate_api_registry(router)
