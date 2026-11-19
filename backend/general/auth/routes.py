# ================================================
#  File: Pulsar/backend/general/auth/routes.py
#  Purpose: Manage routes related to user authentication
#  Includes: Registration, Login, Get Profile of the logged in user
#  Depends on: SQLAlchemy AsyncSession + JWT Token Auth
#  Extensible for roles and permissions in the future
# ================================================
 
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Internal imports
from core.database import get_async_session
from general.user.models.user import User
from general.auth.schemas import ( 
    RegisterRequest, RegisterResponse,
    LoginRequest, LoginResponse, 
    UserProfileResponse, 
)

from general.auth.dependencies import get_current_user
from general.auth.security import get_password_hash, verify_password,create_access_token

# Define the main router for authentication
router = APIRouter(prefix="/auth", tags=["Auth"])

# ================================================
#  POST /auth/register 
# 📝 Description: Register a new user 
#  Input: email, password, profile_id
#  Output: Success message or 400 if email exists
# ================================================
@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_async_session)
):
    # Check for existing user by email
    query = select(User).where(User.c_user_email == data.email)
    result = await db.execute(query)
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash the user's password
    hashed_password = get_password_hash(data.password)

    # Create new user instance
    new_user = User(
        c_user_email=data.email,
        c_user_password=hashed_password,
        profile_id=data.profile_id,
        c_user_active=True
    )

    # Save to database
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return RegisterResponse(message="User registered successfully")


# ================================================
#  POST /auth/login
# 📝 Description: Log in an existing user using email & password
#  Input: email, password
#  Output: JWT access token or 401 on failure
# ================================================
@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_async_session)
):
    # Find user by email
    query = select(User).where(User.c_user_email == data.email)
    result = await db.execute(query)
    user = result.scalars().first()

    # Verify user and password
    if not user or not verify_password(data.password, user.c_user_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Create token payload
    token_data = {
        "sub": user.c_user_email,
        "uid": str(user.c_user_id),
        "pid": str(user.profile_id)
    } 
    
    # Generate JWT access token
    access_token = create_access_token(data=token_data)

    return LoginResponse(access_token=access_token)

#import logging 
#logger = logging.getLogger(__name__)
# ================================================
#  GET /auth/me
# 📝 Description: Get the currently logged-in user's profile
#  Requires: Bearer token
#  Output: User object
# ================================================
@router.get("/me", response_model=UserProfileResponse)
async def read_profile( 
    current_user: User = Depends(get_current_user)
    ):
    #logger.info(f" /auth/me called, current_user: {current_user}")
    return current_user
  