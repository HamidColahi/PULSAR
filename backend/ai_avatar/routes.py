
# ===============================================
# File: Pulsar/backend/ai_avatar/routes.py
#
# Description:
# Metadata-registered AI Avatar API routes with authenticated chat access
#
# Change Date: 2026-11-20 16:18
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


validate_api_registry(router)
