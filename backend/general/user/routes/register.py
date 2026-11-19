# ===============================================
#  File: Pulsar/backend/general/user/routes/register.py
#  Description: User registration route using DataWindowManager abstraction.
# ===============================================

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, Field
from passlib.context import CryptContext

# 🔗 Internal imports
from core.database import get_async_session
from general.user.models.user import User
from datawindows.common.utils.datawindow import DataWindowManager

router = APIRouter()

#  Password hashing config
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ✨ Function to hash password
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

#  Input schema for user registration
class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=50, example="mhk@example.com")
    password: str = Field(..., min_length=6, example="strongpassword")
    profile_id: str = Field(..., example="uuid-profile-id")

# ===============================================
#  POST /auth/register
# 📝 Description: Register a new user and store in pulsar.t_user
# ===============================================
@router.post("/register")
async def register_user(
    register_req: RegisterRequest,
    db: AsyncSession = Depends(get_async_session)
):
    try: 
        # 1️⃣ Check for duplicate email
        query = select(User).where(User.c_user_email == register_req.email)
        result = await db.execute(query)
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered."
            )

        # 2️⃣ Prepare user data
        hashed_pw = hash_password(register_req.password)
        user_data = {
            "c_user_email": register_req.email,
            "c_user_password": hashed_pw,
            "profile_id": register_req.profile_id,
            "c_user_active": True,
        }

        # 3️⃣ Insert into DB using DataWindowManager
        dw = DataWindowManager(User, db)
        user_obj = await dw.insert(user_data)

        return {
            "message": " User registered successfully",
            "user_id": str(user_obj.c_user_id),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
