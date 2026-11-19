# =============================================================
# File:
# Pulsar/backend/general/translation/routes.py
#
# Description:
# Translation API based on item_code and language metadata
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# =============================================================
from fastapi import (
    APIRouter,
    Depends,
    Query
)
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from general.translation.models import (
    TranslationDictionary
)

router = APIRouter(
    prefix="/utils",
    tags=["translation"]
)

# =============================================================
# Translation Response
# =============================================================
class TranslationResponse(BaseModel):
    translated_text: str

# =============================================================
# Manual Translation Test
# =============================================================
@router.get(
    "/test-translation"
)
async def test_translation(
    db: AsyncSession = Depends(
        get_async_session
    )
):
    stmt = (
        select(
            TranslationDictionary.translated_text
        )
        .where(
            TranslationDictionary.item_code ==
            "login.title",
            TranslationDictionary.language_code ==
            "en"
        )
        .limit(1)
    )

    result = await db.execute(
        stmt
    )

    translated_text = (
        result.scalar_one_or_none()
    )

    return {
        "status":
            (
                "Found"
                if translated_text
                else "Not Found"
            ),
        "translated_text":
            translated_text or None
    }

# =============================================================
# Translation API
# =============================================================
@router.get(
    "/translate",
    response_model=TranslationResponse
)
async def get_translation(
    item_code: str = Query(
        ...,
        description="Translation item code"
    ),
    language_code: str = Query(
        "en",
        description="Language code"
    ),
    db: AsyncSession = Depends(
        get_async_session
    )
):
    stmt = (
        select(
            TranslationDictionary.translated_text
        )
        .where(
            TranslationDictionary.item_code ==
            item_code,
            TranslationDictionary.language_code ==
            language_code
        )
        .limit(1)
    )

    result = await db.execute(
        stmt
    )

    translated_text = (
        result.scalar_one_or_none()
    )

    return {
        "translated_text":
            (
                translated_text
                if translated_text
                else item_code
            )
    }

# =============================================================
# Important Learning Points
# =============================================================
# 1. Translation lookup is driven by item_code + language_code.
# 2. TranslationDictionary remains the source of translated text.
# 3. Language behavior is defined independently by language metadata.
# 4. Missing translations fall back to item_code.
# 5. No language-specific UI behavior is implemented here.
# 6. This route does not interpret primary_key.
# 7. This route does not interpret where_clause.
# 8. This route does not create or resolve parm[n].