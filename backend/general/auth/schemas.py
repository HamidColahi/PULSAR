# ===============================
#  File: Pulsar/backend/general/auth/schemas.py
#  Purpose: Pydantic models for authentication endpoints
# Updated based on new database design (CDM-aligned)
# ===============================

from pydantic import BaseModel, EmailStr, Field
from uuid import UUID

# -------------------------------
#  Model for new user registration
# -------------------------------
class RegisterRequest(BaseModel):
    email: EmailStr                     # User email (unique)
    password: str                       # Plain password
    profile_id: UUID                    # Foreign key to profile (t_profile)

class RegisterResponse(BaseModel):
    message: str


# -------------------------------
#  Model for user login
# -------------------------------
class LoginRequest(BaseModel):
    email: EmailStr                   
    password: str

class LoginResponse(BaseModel):
    access_token: str


# -------------------------------
# 📤 Model for the current user profile response
# -------------------------------
class UserProfileResponse(BaseModel):
    id: UUID                            # Maps to c_user_id
    email: EmailStr                     # Maps to c_user_email
    profile_id: UUID        # Maps to profile_id

#    # Enable ORM support (for SQLAlchemy)
#     model_config = {
#         "from_attributes": True
#     }

class UserCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=50, description="Unique email")
    password: str = Field(..., min_length=6, max_length=128, description="User password")

class UserLogin(BaseModel):
    email: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)

class UserRead(BaseModel):
    id: str
    email: str
    profile_id: str

    class Config:
        orm_mode = True
