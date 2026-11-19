# ===============================================
#  File: Pulsar/backend/general/auth/dependencies.py
#  Purpose: Dependency for JWT authentication in FastAPI
#  Verifies JWT and returns the current logged-in user
# ===============================================

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.database import get_async_session 
from general.user.models.user import User
from general.user.schemas.user import UserProfileResponse  #  Output schema
import os
from dotenv import load_dotenv 

#  Load environment variables 
load_dotenv()   

#  JWT config
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

#  Get token from Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

#  Dependency: extract user from JWT token
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_session)
) -> UserProfileResponse:
    """
    Extract user info from JWT and return UserProfileResponse.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="❌ Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try: 
        # 🔓 Decode JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    #  Find user by email
    query = select(User).where(User.c_user_email == email)
    result = await db.execute(query)
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    
    #  Return in format expected by /auth/me
    return UserProfileResponse(        
        id=user.c_user_id,
        email=user.c_user_email,
        profile_id=user.profile_id,
        is_active=user.c_user_active
    )
