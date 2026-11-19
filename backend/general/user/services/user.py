# Pulsar/backend/general/user/services/user.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from general.user.models.user import User

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()
