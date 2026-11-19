
# =======================================================
# File: Pulsar/backend/core/database.py
# Description: Async SQLAlchemy database setup for FastAPI
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# Last Modified: 2026-11-16 13:10 (Asia/Baku)
# =======================================================

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.config import settings


# -------------------------------------------------------
# Async SQLAlchemy Engine
# -------------------------------------------------------
# Example:
# postgresql+asyncpg://user:pass@localhost/dbname
# Reads from: .env -> DATABASE_URL

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    future=True,
)


# -------------------------------------------------------
# Async Session Factory
# -------------------------------------------------------
# Do not use directly; always use get_async_session.

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# -------------------------------------------------------
# Dependency Injection: Async DB Session
# Usage: Depends(get_async_session)
# -------------------------------------------------------

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
